"""
健康检查增强模块

公理溯源：存续公理 - 全面系统健康评估，防患于未然

设计意图：
- 多维度健康检查
- 健康评分（0-100）
- 检查项可插拔
- 健康趋势追踪
- 零外部依赖
"""

import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from exceptions import EternalAgentError


class HealthCheckError(EternalAgentError):
    """健康检查异常"""
    pass


@dataclass
class CheckResult:
    """检查结果"""
    name: str
    status: str  # healthy, degraded, unhealthy, unknown
    score: float  # 0-100
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HealthReport:
    """健康报告"""
    overall_status: str  # healthy, degraded, unhealthy
    overall_score: float  # 0-100
    checks: List[CheckResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "overall_score": round(self.overall_score, 1),
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "score": round(c.score, 1),
                    "message": c.message,
                    "details": c.details,
                    "duration_ms": round(c.duration_ms, 2),
                }
                for c in self.checks
            ],
            "timestamp": self.timestamp,
            "recommendations": self.recommendations,
        }


class HealthChecker:
    """健康检查器基类"""
    def __init__(self, name: str):
        self.name = name

    def check(self) -> CheckResult:
        raise NotImplementedError


class DiskSpaceChecker(HealthChecker):
    """磁盘空间检查"""
    def __init__(self, warning_percent: float = 80, critical_percent: float = 95):
        super().__init__("disk_space")
        self.warning_percent = warning_percent
        self.critical_percent = critical_percent

    def check(self) -> CheckResult:
        start = time.time()
        try:
            usage = os.statvfs('/')
            total = usage.f_blocks * usage.f_frsize
            free = usage.f_bavail * usage.f_frsize
            used_percent = (1 - free / total) * 100 if total > 0 else 0

            if used_percent >= self.critical_percent:
                status = "unhealthy"
                score = max(0, 100 - used_percent)
                msg = f"磁盘使用率 {used_percent:.1f}% — 严重不足"
            elif used_percent >= self.warning_percent:
                status = "degraded"
                score = max(20, 100 - used_percent)
                msg = f"磁盘使用率 {used_percent:.1f}% — 偏高"
            else:
                status = "healthy"
                score = 100 - (used_percent / self.warning_percent * 20)
                msg = f"磁盘使用率 {used_percent:.1f}% — 正常"

            return CheckResult(
                name=self.name,
                status=status,
                score=score,
                message=msg,
                details={"used_percent": round(used_percent, 1), "free_gb": round(free / 1e9, 2)},
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return CheckResult(name=self.name, status="unknown", score=50, message=str(e))


class MemoryChecker(HealthChecker):
    """内存检查"""
    def __init__(self, warning_mb: float = 512, critical_mb: float = 1024):
        super().__init__("memory")
        self.warning_mb = warning_mb
        self.critical_mb = critical_mb

    def check(self) -> CheckResult:
        start = time.time()
        try:
            # 读取 /proc/self/status
            status_file = "/proc/self/status"
            if not Path(status_file).exists():
                return CheckResult(name=self.name, status="unknown", score=50, message="无法读取内存信息")

            rss_mb = 0
            with open(status_file, 'r') as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        rss_mb = int(line.split()[1]) / 1024
                        break

            if rss_mb >= self.critical_mb:
                status = "unhealthy"
                score = max(0, 100 - (rss_mb / self.critical_mb * 100))
                msg = f"内存使用 {rss_mb:.1f}MB — 严重"
            elif rss_mb >= self.warning_mb:
                status = "degraded"
                score = max(30, 100 - (rss_mb / self.warning_mb * 30))
                msg = f"内存使用 {rss_mb:.1f}MB — 偏高"
            else:
                status = "healthy"
                score = 100 - (rss_mb / self.warning_mb * 15)
                msg = f"内存使用 {rss_mb:.1f}MB — 正常"

            return CheckResult(
                name=self.name,
                status=status,
                score=score,
                message=msg,
                details={"rss_mb": round(rss_mb, 1)},
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return CheckResult(name=self.name, status="unknown", score=50, message=str(e))


class FileIntegrityChecker(HealthChecker):
    """文件完整性检查"""
    def __init__(self, data_dir: Optional[Path] = None):
        super().__init__("file_integrity")
        self._data_dir = data_dir or Path(__file__).parent.parent / "data"

    def check(self) -> CheckResult:
        start = time.time()
        issues = []
        file_count = 0

        if not self._data_dir.exists():
            return CheckResult(
                name=self.name, status="healthy", score=100,
                message="数据目录不存在（新系统）"
            )

        for f in self._data_dir.rglob("*.json"):
            file_count += 1
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    json.load(fh)
            except json.JSONDecodeError:
                issues.append(f"文件损坏: {f.name}")
            except Exception:
                issues.append(f"无法读取: {f.name}")

        if len(issues) > 0:
            status = "unhealthy" if len(issues) > 3 else "degraded"
            score = max(0, 100 - len(issues) * 20)
            msg = f"发现 {len(issues)} 个文件问题"
        else:
            status = "healthy"
            score = 100
            msg = f"{file_count} 个文件全部正常"

        return CheckResult(
            name=self.name,
            status=status,
            score=score,
            message=msg,
            details={"files_checked": file_count, "issues": issues},
            duration_ms=(time.time() - start) * 1000,
        )


class DataFreshnessChecker(HealthChecker):
    """数据新鲜度检查"""
    def __init__(self, data_dir: Optional[Path] = None, stale_hours: float = 24):
        super().__init__("data_freshness")
        self._data_dir = data_dir or Path(__file__).parent.parent / "data"
        self._stale_hours = stale_hours

    def check(self) -> CheckResult:
        start = time.time()
        now = time.time()
        stale_threshold = self._stale_hours * 3600

        if not self._data_dir.exists():
            return CheckResult(name=self.name, status="healthy", score=100, message="无数据")

        files = list(self._data_dir.rglob("*.json"))
        if not files:
            return CheckResult(name=self.name, status="healthy", score=100, message="无数据文件")

        ages = []
        for f in files:
            mtime = f.stat().st_mtime
            ages.append(now - mtime)

        max_age = max(ages)
        avg_age = sum(ages) / len(ages)

        if max_age > stale_threshold * 2:
            status = "unhealthy"
            score = max(0, 100 - (max_age / stale_threshold * 25))
            msg = f"最旧数据 {max_age/3600:.1f} 小时前更新 — 严重过期"
        elif max_age > stale_threshold:
            status = "degraded"
            score = max(30, 100 - (max_age / stale_threshold * 30))
            msg = f"最旧数据 {max_age/3600:.1f} 小时前更新 — 偏旧"
        else:
            status = "healthy"
            score = 100 - (max_age / stale_threshold * 15)
            msg = f"数据新鲜（平均 {avg_age/3600:.1f} 小时前更新）"

        return CheckResult(
            name=self.name,
            status=status,
            score=score,
            message=msg,
            details={"max_age_hours": round(max_age / 3600, 1), "avg_age_hours": round(avg_age / 3600, 1)},
            duration_ms=(time.time() - start) * 1000,
        )


class HealthMonitor:
    """
    健康监控器

    职责：
    - 注册健康检查器
    - 执行全面健康检查
    - 计算综合健康评分
    - 生成健康报告
    - 健康趋势追踪
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._checkers: List[HealthChecker] = []
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

        # 注册默认检查器
        self.register(DiskSpaceChecker())
        self.register(MemoryChecker())
        self.register(FileIntegrityChecker(data_dir))
        self.register(DataFreshnessChecker(data_dir))

    def register(self, checker: HealthChecker) -> None:
        """注册检查器"""
        self._checkers.append(checker)

    def unregister(self, name: str) -> bool:
        """注销检查器"""
        for i, c in enumerate(self._checkers):
            if c.name == name:
                self._checkers.pop(i)
                return True
        return False

    def check_all(self) -> HealthReport:
        """执行全部健康检查"""
        results = []
        for checker in self._checkers:
            try:
                result = checker.check()
                results.append(result)
            except Exception as e:
                results.append(CheckResult(
                    name=checker.name,
                    status="unknown",
                    score=50,
                    message=f"检查异常: {e}",
                ))

        # 计算综合评分
        if results:
            overall_score = sum(r.score for r in results) / len(results)
        else:
            overall_score = 100

        # 确定整体状态
        statuses = [r.status for r in results]
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        elif "unknown" in statuses and all(s == "unknown" for s in statuses):
            overall_status = "unknown"
        else:
            overall_status = "healthy"

        # 生成建议
        recommendations = self._generate_recommendations(results)

        report = HealthReport(
            overall_status=overall_status,
            overall_score=overall_score,
            checks=results,
            recommendations=recommendations,
        )

        # 记录历史
        with self._lock:
            self._history.append({
                "status": overall_status,
                "score": round(overall_score, 1),
                "timestamp": report.timestamp,
            })
            if len(self._history) > 500:
                self._history = self._history[-500:]

        return report

    def check_single(self, name: str) -> Optional[CheckResult]:
        """执行单个检查"""
        for checker in self._checkers:
            if checker.name == name:
                return checker.check()
        return None

    def get_trend(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取健康趋势"""
        with self._lock:
            return self._history[-limit:]

    def _generate_recommendations(self, results: List[CheckResult]) -> List[str]:
        """生成建议"""
        recs = []
        for r in results:
            if r.status == "unhealthy":
                recs.append(f"[紧急] {r.name}: {r.message}")
            elif r.status == "degraded":
                recs.append(f"[注意] {r.name}: {r.message}")
        return recs
