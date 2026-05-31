"""
系统诊断模块

公理溯源：存续公理 - 自动故障诊断，快速定位问题

设计意图：
- 自动故障检测
- 诊断规则引擎
- 诊断报告生成
- 修复建议
- 零外部依赖
"""

import json
import os
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from exceptions import EternalAgentError


class DiagnosticError(EternalAgentError):
    """诊断异常"""
    pass


@dataclass
class DiagnosticIssue:
    """诊断问题"""
    severity: str  # info, warning, critical
    category: str  # performance, security, data, system, config
    title: str
    description: str
    recommendation: str = ""
    affected_component: str = ""
    auto_fixable: bool = False
    auto_fix_fn: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            Dict[str, Any]: 问题信息的字典表示
        """
        return {
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "affected_component": self.affected_component,
            "auto_fixable": self.auto_fixable,
        }


@dataclass
class DiagnosticReport:
    """诊断报告"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    issues: List[DiagnosticIssue] = field(default_factory=list)
    score: float = 100.0  # 健康评分
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            Dict[str, Any]: 报告信息的字典表示
        """
        return {
            "timestamp": self.timestamp,
            "score": round(self.score, 1),
            "summary": self.summary,
            "issues": [i.to_dict() for i in self.issues],
            "issue_count": len(self.issues),
            "critical_count": sum(1 for i in self.issues if i.severity == "critical"),
            "warning_count": sum(1 for i in self.issues if i.severity == "warning"),
            "info_count": sum(1 for i in self.issues if i.severity == "info"),
        }


class DiagnosticRule:
    """诊断规则基类"""
    def __init__(self, name: str, category: str = "system"):
        self.name = name
        self.category = category

    def diagnose(self) -> List[DiagnosticIssue]:
        """执行诊断检查
        
        Returns:
            List[DiagnosticIssue]: 发现的问题列表
        """
        raise NotImplementedError


class DiskSpaceRule(DiagnosticRule):
    """磁盘空间诊断"""
    def __init__(self, warning_percent: float = 80, critical_percent: float = 95):
        super().__init__("disk_space", "system")
        self.warning_percent = warning_percent
        self.critical_percent = critical_percent

    def diagnose(self) -> List[DiagnosticIssue]:
        """检查磁盘空间使用情况
        
        Returns:
            List[DiagnosticIssue]: 磁盘空间问题列表
        """
        issues = []
        try:
            usage = os.statvfs('/')
            total = usage.f_blocks * usage.f_frsize
            free = usage.f_bavail * usage.f_frsize
            used_percent = (1 - free / total) * 100 if total > 0 else 0

            if used_percent >= self.critical_percent:
                issues.append(DiagnosticIssue(
                    severity="critical",
                    category=self.category,
                    title="磁盘空间严重不足",
                    description=f"磁盘使用率 {used_percent:.1f}%，剩余 {free/1e9:.1f}GB",
                    recommendation="立即清理日志文件、旧备份和临时文件",
                    affected_component="disk",
                ))
            elif used_percent >= self.warning_percent:
                issues.append(DiagnosticIssue(
                    severity="warning",
                    category=self.category,
                    title="磁盘空间偏低",
                    description=f"磁盘使用率 {used_percent:.1f}%，剩余 {free/1e9:.1f}GB",
                    recommendation="建议清理不必要的文件",
                    affected_component="disk",
                ))
        except Exception:
            pass
        return issues


class MemoryUsageRule(DiagnosticRule):
    """内存使用诊断"""
    def __init__(self, warning_mb: float = 512, critical_mb: float = 1024):
        super().__init__("memory_usage", "performance")
        self.warning_mb = warning_mb
        self.critical_mb = critical_mb

    def diagnose(self) -> List[DiagnosticIssue]:
        """检查内存使用情况
        
        Returns:
            List[DiagnosticIssue]: 内存使用问题列表
        """
        issues = []
        try:
            status_file = "/proc/self/status"
            if not Path(status_file).exists():
                return issues

            rss_mb = 0
            with open(status_file, 'r') as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        rss_mb = int(line.split()[1]) / 1024
                        break

            if rss_mb >= self.critical_mb:
                issues.append(DiagnosticIssue(
                    severity="critical",
                    category=self.category,
                    title="内存使用过高",
                    description=f"RSS内存 {rss_mb:.1f}MB，超过阈值 {self.critical_mb}MB",
                    recommendation="检查内存泄漏，考虑重启系统或优化数据结构",
                    affected_component="memory",
                ))
            elif rss_mb >= self.warning_mb:
                issues.append(DiagnosticIssue(
                    severity="warning",
                    category=self.category,
                    title="内存使用偏高",
                    description=f"RSS内存 {rss_mb:.1f}MB",
                    recommendation="监控内存趋势，考虑优化",
                    affected_component="memory",
                ))
        except Exception:
            pass
        return issues


class DataConsistencyRule(DiagnosticRule):
    """数据一致性诊断"""
    def __init__(self, data_dir: Optional[Path] = None):
        super().__init__("data_consistency", "data")
        self._data_dir = data_dir or Path(__file__).parent.parent / "data"

    def diagnose(self) -> List[DiagnosticIssue]:
        """检查数据文件一致性
        
        Returns:
            List[DiagnosticIssue]: 数据一致性问题列表
        """
        issues = []
        if not self._data_dir.exists():
            return issues

        corrupted = []
        empty = []
        for f in self._data_dir.rglob("*.json"):
            if f.stat().st_size == 0:
                empty.append(f.name)
                continue
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    json.load(fh)
            except json.JSONDecodeError:
                corrupted.append(f.name)

        if corrupted:
            issues.append(DiagnosticIssue(
                severity="critical",
                category=self.category,
                title="数据文件损坏",
                description=f"{len(corrupted)} 个JSON文件损坏: {', '.join(corrupted[:5])}",
                recommendation="从备份恢复损坏的文件",
                affected_component="data",
            ))

        if empty:
            issues.append(DiagnosticIssue(
                severity="info",
                category=self.category,
                title="存在空数据文件",
                description=f"{len(empty)} 个空文件",
                recommendation="检查是否为预期行为，非预期则删除",
                affected_component="data",
            ))

        return issues


class LogHealthRule(DiagnosticRule):
    """日志健康诊断"""
    def __init__(self, log_dir: Optional[Path] = None):
        super().__init__("log_health", "system")
        self._log_dir = log_dir or Path(__file__).parent.parent / "data" / "logs"

    def diagnose(self) -> List[DiagnosticIssue]:
        """分析日志文件
        
        Returns:
            List[DiagnosticIssue]: 日志相关问题列表
        """
        issues = []
        if not self._log_dir.exists():
            return issues

        total_size = 0
        error_count = 0
        for f in self._log_dir.iterdir():
            if f.is_file():
                total_size += f.stat().st_size
                try:
                    with open(f, 'r', encoding='utf-8') as fh:
                        for line in fh:
                            if "ERROR" in line or "CRITICAL" in line:
                                error_count += 1
                except Exception:
                    pass

        if total_size > 50 * 1024 * 1024:  # 50MB
            issues.append(DiagnosticIssue(
                severity="warning",
                category=self.category,
                title="日志文件过大",
                description=f"日志总大小 {total_size/1024/1024:.1f}MB",
                recommendation="清理旧日志或减小日志级别",
                affected_component="logs",
            ))

        if error_count > 100:
            issues.append(DiagnosticIssue(
                severity="warning",
                category=self.category,
                title="日志错误过多",
                description=f"发现 {error_count} 条错误日志",
                recommendation="检查错误日志，修复潜在问题",
                affected_component="logs",
            ))

        return issues


class SystemDiagnostics:
    """
    系统诊断器

    职责：
    - 注册诊断规则
    - 执行全面诊断
    - 生成诊断报告
    - 自动修复建议
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._rules: List[DiagnosticRule] = []
        self._data_dir = data_dir

        # 注册默认规则
        self.register(DiskSpaceRule())
        self.register(MemoryUsageRule())
        self.register(DataConsistencyRule(data_dir))
        self.register(LogHealthRule())

    def register(self, rule: DiagnosticRule) -> None:
        """注册诊断规则"""
        self._rules.append(rule)

    def diagnose(self) -> DiagnosticReport:
        """执行全面诊断"""
        all_issues: List[DiagnosticIssue] = []

        for rule in self._rules:
            try:
                issues = rule.diagnose()
                all_issues.extend(issues)
            except Exception:
                pass

        # 计算评分
        score = 100.0
        for issue in all_issues:
            if issue.severity == "critical":
                score -= 20
            elif issue.severity == "warning":
                score -= 5
            elif issue.severity == "info":
                score -= 1
        score = max(0, score)

        # 生成摘要
        critical_count = sum(1 for i in all_issues if i.severity == "critical")
        warning_count = sum(1 for i in all_issues if i.severity == "warning")

        if critical_count > 0:
            summary = f"发现 {critical_count} 个严重问题，{warning_count} 个警告"
        elif warning_count > 0:
            summary = f"发现 {warning_count} 个警告，系统基本正常"
        elif all_issues:
            summary = f"发现 {len(all_issues)} 个提示信息"
        else:
            summary = "系统状态良好，未发现问题"

        return DiagnosticReport(
            issues=all_issues,
            score=score,
            summary=summary,
        )

    def quick_check(self) -> Dict[str, Any]:
        """快速检查（仅返回摘要）"""
        report = self.diagnose()
        return {
            "score": report.score,
            "status": "healthy" if report.score >= 80 else "degraded" if report.score >= 50 else "unhealthy",
            "summary": report.summary,
            "issue_count": len(report.issues),
        }
