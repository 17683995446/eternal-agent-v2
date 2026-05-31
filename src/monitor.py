"""
资源监控模块

公理溯源：存续公理 - 资源熔断保护，确保系统稳态运行

设计意图：
- 监控CPU、内存、磁盘使用情况
- 提供资源告警能力
- 支持熔断判断
- 零外部依赖，仅使用Python标准库
"""

import os
import sys
import time
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from constants import (
    MEMORY_LIMIT_MB,
    CPU_LIMIT_PERCENT,
    DISK_LIMIT_PERCENT,
)
from logger import get_logger
from exceptions import (
    MemoryLimitExceededError,
    DiskLimitExceededError,
    SystemOverloadError,
)

logger = get_logger("Monitor")


@dataclass
class ResourceStatus:
    """
    资源状态数据结构
    
    属性：
        cpu_percent: CPU使用率
        memory_percent: 内存使用率
        memory_mb: 内存使用量（MB）
        disk_percent: 磁盘使用率
        is_healthy: 是否健康
        warnings: 警告信息列表
    """
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_mb: float = 0.0
    disk_percent: float = 0.0
    is_healthy: bool = True
    warnings: list = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class ResourceMonitor:
    """
    资源监控器
    
    公理溯源：存续公理 - 资源熔断保护
    
    特性：
    - 监控系统资源使用
    - 提供健康检查
    - 支持熔断判断
    """
    
    def __init__(
        self,
        memory_limit_mb: float = MEMORY_LIMIT_MB,
        cpu_limit_percent: float = CPU_LIMIT_PERCENT,
        disk_limit_percent: float = DISK_LIMIT_PERCENT,
    ):
        """
        初始化资源监控器
        
        Args:
            memory_limit_mb: 内存上限（MB）
            cpu_limit_percent: CPU使用率上限（%）
            disk_limit_percent: 磁盘使用率上限（%）
        """
        self.memory_limit_mb = memory_limit_mb
        self.cpu_limit_percent = cpu_limit_percent
        self.disk_limit_percent = disk_limit_percent
        
        # 用于CPU计算
        self._last_cpu_time = time.time()
        self._last_process_time = self._get_process_time()
    
    def _get_process_time(self) -> float:
        """获取进程CPU时间"""
        try:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_utime
        except Exception:
            return time.time()
    
    def get_memory_usage(self) -> tuple:
        """
        获取内存使用情况
        
        Returns:
            tuple: (使用量MB, 使用率%)
        """
        try:
            import resource
            # 获取进程内存使用（RSS）
            mem_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # Linux下单位是KB，macOS下单位是bytes
            if sys.platform == 'darwin':
                mem_mb = mem_bytes / (1024 * 1024)
            else:
                mem_mb = mem_bytes / 1024
            
            # 计算使用率（假设系统内存为8GB）
            total_mb = 8192
            percent = (mem_mb / total_mb) * 100
            
            return mem_mb, percent
        except Exception as e:
            logger.warning(f"获取内存使用失败: {e}")
            return 0.0, 0.0
    
    def get_cpu_usage(self) -> float:
        """
        获取CPU使用率
        
        Returns:
            float: CPU使用率（%）
        """
        try:
            current_time = time.time()
            current_process_time = self._get_process_time()
            
            time_delta = current_time - self._last_cpu_time
            process_delta = current_process_time - self._last_process_time
            
            # 计算CPU使用率
            if time_delta > 0:
                cpu_percent = (process_delta / time_delta) * 100
            else:
                cpu_percent = 0.0
            
            # 更新记录
            self._last_cpu_time = current_time
            self._last_process_time = current_process_time
            
            return min(cpu_percent, 100.0)
        except Exception as e:
            logger.warning(f"获取CPU使用率失败: {e}")
            return 0.0
    
    def get_disk_usage(self, path: str = "/") -> tuple:
        """
        获取磁盘使用情况
        
        Args:
            path: 磁盘路径
            
        Returns:
            tuple: (总量GB, 已用GB, 使用率%)
        """
        try:
            stat = os.statvfs(path)
            total = stat.f_blocks * stat.f_frsize
            used = (stat.f_blocks - stat.f_bfree) * stat.f_frsize
            
            total_gb = total / (1024 ** 3)
            used_gb = used / (1024 ** 3)
            percent = (used / total) * 100 if total > 0 else 0
            
            return total_gb, used_gb, percent
        except Exception as e:
            logger.warning(f"获取磁盘使用失败: {e}")
            return 0.0, 0.0, 0.0
    
    def check_health(self) -> ResourceStatus:
        """
        检查资源健康状态
        
        Returns:
            ResourceStatus: 资源状态
        """
        warnings = []
        is_healthy = True
        
        # 检查内存
        mem_mb, mem_percent = self.get_memory_usage()
        if mem_mb > self.memory_limit_mb:
            warnings.append(f"内存使用超限: {mem_mb:.1f}MB > {self.memory_limit_mb}MB")
            is_healthy = False
        
        # 检查CPU
        cpu_percent = self.get_cpu_usage()
        if cpu_percent > self.cpu_limit_percent:
            warnings.append(f"CPU使用超限: {cpu_percent:.1f}% > {self.cpu_limit_percent}%")
            is_healthy = False
        
        # 检查磁盘
        _, _, disk_percent = self.get_disk_usage()
        if disk_percent > self.disk_limit_percent:
            warnings.append(f"磁盘使用超限: {disk_percent:.1f}% > {self.disk_limit_percent}%")
            is_healthy = False
        
        return ResourceStatus(
            cpu_percent=cpu_percent,
            memory_percent=mem_percent,
            memory_mb=mem_mb,
            disk_percent=disk_percent,
            is_healthy=is_healthy,
            warnings=warnings,
        )
    
    def should_throttle(self) -> bool:
        """
        判断是否需要限流
        
        Returns:
            bool: 是否需要限流
        """
        status = self.check_health()
        return not status.is_healthy
    
    def check_and_raise(self) -> None:
        """
        检查资源并在超限时抛出异常
        
        Raises:
            MemoryLimitExceededError: 内存超限
            DiskLimitExceededError: 磁盘超限
            SystemOverloadError: 系统过载
        """
        status = self.check_health()
        
        if not status.is_healthy:
            for warning in status.warnings:
                if "内存" in warning:
                    raise MemoryLimitExceededError(warning)
                elif "磁盘" in warning:
                    raise DiskLimitExceededError(warning)
                elif "CPU" in warning:
                    raise SystemOverloadError(warning)
    
    def get_status_report(self) -> str:
        """
        获取状态报告
        
        Returns:
            str: 状态报告字符串
        """
        status = self.check_health()
        report = [
            "=== 资源状态报告 ===",
            f"CPU使用率: {status.cpu_percent:.1f}%",
            f"内存使用: {status.memory_mb:.1f}MB ({status.memory_percent:.1f}%)",
            f"磁盘使用: {status.disk_percent:.1f}%",
            f"健康状态: {'健康' if status.is_healthy else '异常'}",
        ]
        
        if status.warnings:
            report.append("警告:")
            for warning in status.warnings:
                report.append(f"  - {warning}")
        
        return "\n".join(report)


# 全局监控实例
monitor = ResourceMonitor()
