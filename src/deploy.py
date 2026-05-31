"""
部署脚本模块 — 部署与运维层

公理溯源：存续公理 - 系统需要可靠的部署和运维支持

设计意图：
- 自动化部署流程
- 环境检查和准备
- 配置验证
- 部署回滚支持
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from logger import get_logger
from utils import now_iso, ensure_dir
from constants import PROJECT_ROOT

logger = get_logger("Deploy")


class DeployEnvironment(Enum):
    """部署环境"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DeployStatus(Enum):
    """部署状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeployResult:
    """部署结果"""
    status: DeployStatus
    environment: DeployEnvironment
    version: str
    timestamp: str = field(default_factory=now_iso)
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class Deployer:
    """
    部署器
    
    自动化部署流程管理
    """
    
    def __init__(self, project_root: Path = None):
        self.project_root = Path(project_root) if project_root else PROJECT_ROOT
        self.current_deployment: Optional[DeployResult] = None
        self.deployment_history: List[DeployResult] = []
    
    def check_prerequisites(self) -> Tuple[bool, List[str]]:
        """
        检查部署前置条件
        
        Returns:
            (是否通过, 错误列表)
        """
        errors = []
        
        # 检查Python版本
        python_version = sys.version_info
        if python_version < (3, 8):
            errors.append(f"Python版本过低: {python_version.major}.{python_version.minor}，需要3.8+")
        
        # 检查必要文件
        required_files = [
            self.project_root / "src" / "main.py",
            self.project_root / "Dockerfile",
            self.project_root / "docker-compose.yml",
        ]
        
        for file_path in required_files:
            if not file_path.exists():
                errors.append(f"缺少必要文件: {file_path}")
        
        # 检查目录结构
        required_dirs = [
            self.project_root / "src",
            self.project_root / "data",
        ]
        
        for dir_path in required_dirs:
            if not dir_path.exists():
                errors.append(f"缺少必要目录: {dir_path}")
        
        # 检查Docker（可选）
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                errors.append("Docker未安装或不可用")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            errors.append("Docker未安装或不可用")
        
        is_passed = len(errors) == 0
        return is_passed, errors
    
    def prepare_environment(self, env: DeployEnvironment) -> Tuple[bool, List[str]]:
        """
        准备部署环境
        
        Args:
            env: 部署环境
            
        Returns:
            (是否成功, 日志列表)
        """
        logs = []
        
        # 创建必要目录
        dirs_to_create = [
            self.project_root / "data",
            self.project_root / "logs",
            self.project_root / "config",
            self.project_root / "backups",
        ]
        
        for dir_path in dirs_to_create:
            ensure_dir(dir_path)
            logs.append(f"创建目录: {dir_path}")
        
        # 复制配置文件
        config_source = self.project_root / "config"
        if config_source.exists():
            for config_file in config_source.glob("*.example"):
                target = config_source / config_file.stem
                if not target.exists():
                    shutil.copy(config_file, target)
                    logs.append(f"复制配置: {config_file} -> {target}")
        
        # 设置环境变量
        os.environ["DEPLOY_ENV"] = env.value
        logs.append(f"设置环境: {env.value}")
        
        return True, logs
    
    def deploy_docker(self, env: DeployEnvironment, version: str = "latest") -> DeployResult:
        """
        Docker部署
        
        Args:
            env: 部署环境
            version: 版本号
            
        Returns:
            部署结果
        """
        result = DeployResult(
            status=DeployStatus.RUNNING,
            environment=env,
            version=version
        )
        
        try:
            # 构建镜像
            result.logs.append("开始构建Docker镜像...")
            build_cmd = [
                "docker", "build",
                "-t", f"eternal-agent:{version}",
                "-t", "eternal-agent:latest",
                str(self.project_root)
            ]
            
            build_result = subprocess.run(
                build_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if build_result.returncode != 0:
                result.errors.append(f"构建失败: {build_result.stderr}")
                result.status = DeployStatus.FAILED
                return result
            
            result.logs.append(f"镜像构建成功: eternal-agent:{version}")
            
            # 停止旧容器
            result.logs.append("停止旧容器...")
            subprocess.run(
                ["docker", "compose", "down"],
                cwd=str(self.project_root),
                capture_output=True
            )
            
            # 启动新容器
            result.logs.append("启动新容器...")
            compose_cmd = ["docker", "compose", "up", "-d"]
            
            if env == DeployEnvironment.PRODUCTION:
                compose_cmd.append("--profile")
                compose_cmd.append("monitoring")
            
            up_result = subprocess.run(
                compose_cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if up_result.returncode != 0:
                result.errors.append(f"启动失败: {up_result.stderr}")
                result.status = DeployStatus.FAILED
                return result
            
            result.logs.append("容器启动成功")
            result.status = DeployStatus.SUCCESS
            
        except subprocess.TimeoutExpired:
            result.errors.append("部署超时")
            result.status = DeployStatus.FAILED
        except Exception as e:
            result.errors.append(f"部署异常: {e}")
            result.status = DeployStatus.FAILED
        
        self.current_deployment = result
        self.deployment_history.append(result)
        
        return result
    
    def rollback(self, version: str = None) -> DeployResult:
        """
        回滚部署
        
        Args:
            version: 回滚到的版本（可选）
            
        Returns:
            回滚结果
        """
        result = DeployResult(
            status=DeployStatus.RUNNING,
            environment=DeployEnvironment.PRODUCTION,
            version=version or "previous"
        )
        
        try:
            # 停止当前容器
            result.logs.append("停止当前容器...")
            subprocess.run(
                ["docker", "compose", "down"],
                cwd=str(self.project_root),
                capture_output=True
            )
            
            # 回滚到指定版本
            if version:
                result.logs.append(f"回滚到版本: {version}")
                subprocess.run(
                    ["docker", "compose", "up", "-d", f"eternal-agent:{version}"],
                    cwd=str(self.project_root),
                    capture_output=True
                )
            else:
                # 使用上一个镜像
                result.logs.append("回滚到上一版本...")
                subprocess.run(
                    ["docker", "compose", "up", "-d"],
                    cwd=str(self.project_root),
                    capture_output=True
                )
            
            result.logs.append("回滚完成")
            result.status = DeployStatus.ROLLED_BACK
            
        except Exception as e:
            result.errors.append(f"回滚失败: {e}")
            result.status = DeployStatus.FAILED
        
        return result
    
    def get_deployment_status(self) -> Dict:
        """获取部署状态"""
        status = {
            "current": None,
            "history_count": len(self.deployment_history),
            "last_success": None,
            "last_failure": None,
        }
        
        if self.current_deployment:
            status["current"] = {
                "status": self.current_deployment.status.value,
                "environment": self.current_deployment.environment.value,
                "version": self.current_deployment.version,
                "timestamp": self.current_deployment.timestamp,
            }
        
        for deploy in reversed(self.deployment_history):
            if deploy.status == DeployStatus.SUCCESS and not status["last_success"]:
                status["last_success"] = deploy.timestamp
            if deploy.status == DeployStatus.FAILED and not status["last_failure"]:
                status["last_failure"] = deploy.timestamp
        
        return status
    
    def health_check(self) -> Tuple[bool, Dict]:
        """
        部署后健康检查
        
        Returns:
            (是否健康, 检查结果)
        """
        checks = {
            "container_running": False,
            "api_responding": False,
            "data_accessible": False,
        }
        
        # 检查容器状态
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "-q"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=10
            )
            checks["container_running"] = bool(result.stdout.strip())
        except Exception:
            pass
        
        # 检查API响应
        try:
            import urllib.request
            with urllib.request.urlopen("http://localhost:8080/health", timeout=5) as response:
                checks["api_responding"] = response.status == 200
        except Exception:
            pass
        
        # 检查数据目录
        data_dir = self.project_root / "data"
        checks["data_accessible"] = data_dir.exists() and os.access(data_dir, os.W_OK)
        
        is_healthy = all(checks.values())
        return is_healthy, checks


def deploy(env: str = "development", version: str = "latest") -> DeployResult:
    """部署（便捷函数）"""
    deployer = Deployer()
    environment = DeployEnvironment(env)
    
    # 检查前置条件
    passed, errors = deployer.check_prerequisites()
    if not passed:
        return DeployResult(
            status=DeployStatus.FAILED,
            environment=environment,
            version=version,
            errors=errors
        )
    
    # 准备环境
    deployer.prepare_environment(environment)
    
    # 执行部署
    return deployer.deploy_docker(environment, version)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="永动知识图谱Agent部署工具")
    parser.add_argument("--env", default="development", choices=["development", "staging", "production"])
    parser.add_argument("--version", default="latest")
    parser.add_argument("--check", action="store_true", help="仅检查前置条件")
    parser.add_argument("--rollback", action="store_true", help="回滚部署")
    
    args = parser.parse_args()
    
    deployer = Deployer()
    
    if args.check:
        passed, errors = deployer.check_prerequisites()
        if passed:
            print("✓ 所有前置条件满足")
        else:
            print("✗ 前置条件检查失败:")
            for error in errors:
                print(f"  - {error}")
        sys.exit(0 if passed else 1)
    
    if args.rollback:
        result = deployer.rollback(args.version)
    else:
        result = deployer.deploy_docker(DeployEnvironment(args.env), args.version)
    
    print(f"部署状态: {result.status.value}")
    if result.errors:
        print("错误:")
        for error in result.errors:
            print(f"  - {error}")
