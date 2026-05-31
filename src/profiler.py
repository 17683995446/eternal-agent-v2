"""
性能分析模块

公理溯源：存续公理 - 性能可观测，及时发现瓶颈

设计意图：
- 函数级耗时追踪
- 调用统计
- 性能快照
- 热点分析
- 零外部依赖
"""

import functools
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from exceptions import EternalAgentError


class ProfilerError(EternalAgentError):
    """性能分析异常"""
    pass


@dataclass
class FunctionStats:
    """函数统计"""
    name: str
    call_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    last_time_ms: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None

    def record(self, elapsed_ms: float, error: Optional[str] = None) -> None:
        self.call_count += 1
        self.total_time_ms += elapsed_ms
        self.min_time_ms = min(self.min_time_ms, elapsed_ms)
        self.max_time_ms = max(self.max_time_ms, elapsed_ms)
        self.avg_time_ms = self.total_time_ms / self.call_count
        self.last_time_ms = elapsed_ms
        if error:
            self.error_count += 1
            self.last_error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "call_count": self.call_count,
            "total_time_ms": round(self.total_time_ms, 2),
            "avg_time_ms": round(self.avg_time_ms, 2),
            "min_time_ms": round(self.min_time_ms, 2) if self.min_time_ms != float('inf') else 0,
            "max_time_ms": round(self.max_time_ms, 2),
            "last_time_ms": round(self.last_time_ms, 2),
            "error_count": self.error_count,
            "error_rate": round(self.error_count / max(self.call_count, 1) * 100, 1),
        }


@dataclass
class PerformanceSnapshot:
    """性能快照"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_functions: int = 0
    total_calls: int = 0
    total_time_ms: float = 0.0
    top_slowest: List[Dict[str, Any]] = field(default_factory=list)
    top_frequent: List[Dict[str, Any]] = field(default_factory=list)
    top_error_prone: List[Dict[str, Any]] = field(default_factory=list)


class Profiler:
    """
    性能分析器

    职责：
    - 函数耗时追踪
    - 调用频率统计
    - 错误率追踪
    - 性能热点分析
    - 性能快照
    """

    def __init__(self, enabled: bool = True, max_tracked: int = 500):
        self._enabled = enabled
        self._max_tracked = max_tracked
        self._stats: Dict[str, FunctionStats] = {}
        self._lock = threading.RLock()
        self._snapshots: List[PerformanceSnapshot] = []
        self._global_start_time = time.time()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._global_start_time

    def profile(self, func: Optional[Callable] = None, name: str = ""):
        """
        性能分析装饰器

        用法:
            @profiler.profile
            def my_function():
                ...

            @profiler.profile(name="custom_name")
            def my_function():
                ...
        """
        def decorator(fn):
            fn_name = name or f"{fn.__module__}.{fn.__qualname__}"

            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                if not self._enabled:
                    return fn(*args, **kwargs)

                start = time.time()
                error = None
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    error = f"{type(e).__name__}: {e}"
                    raise
                finally:
                    elapsed = (time.time() - start) * 1000
                    self._record(fn_name, elapsed, error)

            return wrapper

        if func is not None:
            return decorator(func)
        return decorator

    def track(self, name: str, elapsed_ms: float, error: Optional[str] = None) -> None:
        """手动记录性能数据"""
        if self._enabled:
            self._record(name, elapsed_ms, error)

    def get_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """获取函数统计"""
        with self._lock:
            stats = self._stats.get(name)
            return stats.to_dict() if stats else None

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有统计"""
        with self._lock:
            return {name: stats.to_dict() for name, stats in self._stats.items()}

    def get_top_slowest(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最慢的函数"""
        with self._lock:
            sorted_stats = sorted(
                self._stats.values(),
                key=lambda s: s.avg_time_ms,
                reverse=True,
            )
            return [s.to_dict() for s in sorted_stats[:limit]]

    def get_top_frequent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取调用最频繁的函数"""
        with self._lock:
            sorted_stats = sorted(
                self._stats.values(),
                key=lambda s: s.call_count,
                reverse=True,
            )
            return [s.to_dict() for s in sorted_stats[:limit]]

    def get_top_error_prone(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取错误率最高的函数"""
        with self._lock:
            sorted_stats = sorted(
                self._stats.values(),
                key=lambda s: s.error_count,
                reverse=True,
            )
            return [s.to_dict() for s in sorted_stats[:limit] if s.error_count > 0]

    def take_snapshot(self) -> PerformanceSnapshot:
        """获取性能快照"""
        with self._lock:
            all_stats = list(self._stats.values())
            total_calls = sum(s.call_count for s in all_stats)
            total_time = sum(s.total_time_ms for s in all_stats)

            snapshot = PerformanceSnapshot(
                total_functions=len(all_stats),
                total_calls=total_calls,
                total_time_ms=round(total_time, 2),
                top_slowest=self.get_top_slowest(5),
                top_frequent=self.get_top_frequent(5),
                top_error_prone=self.get_top_error_prone(5),
            )

            self._snapshots.append(snapshot)
            if len(self._snapshots) > 100:
                self._snapshots = self._snapshots[-100:]

            return snapshot

    def get_snapshots(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取历史快照"""
        snaps = self._snapshots[-limit:]
        return [
            {
                "timestamp": s.timestamp,
                "total_functions": s.total_functions,
                "total_calls": s.total_calls,
                "total_time_ms": s.total_time_ms,
            }
            for s in snaps
        ]

    def reset(self) -> None:
        """重置所有统计"""
        with self._lock:
            self._stats.clear()
            self._snapshots.clear()

    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        with self._lock:
            all_stats = list(self._stats.values())
            return {
                "enabled": self._enabled,
                "uptime_seconds": round(self.uptime_seconds, 1),
                "tracked_functions": len(all_stats),
                "total_calls": sum(s.call_count for s in all_stats),
                "total_time_ms": round(sum(s.total_time_ms for s in all_stats), 2),
                "total_errors": sum(s.error_count for s in all_stats),
                "snapshots_count": len(self._snapshots),
            }

    def _record(self, name: str, elapsed_ms: float, error: Optional[str] = None) -> None:
        """记录性能数据"""
        with self._lock:
            if name not in self._stats:
                self._stats[name] = FunctionStats(name=name)
            self._stats[name].record(elapsed_ms, error)

            # 限制追踪数量
            if len(self._stats) > self._max_tracked:
                # 移除调用次数最少的
                sorted_items = sorted(
                    self._stats.items(),
                    key=lambda x: x[1].call_count,
                )
                for k, _ in sorted_items[:len(self._stats) - self._max_tracked]:
                    del self._stats[k]


# 全局性能分析器
_global_profiler: Optional[Profiler] = None


def get_profiler() -> Profiler:
    """获取全局性能分析器"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = Profiler()
    return _global_profiler
