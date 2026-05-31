"""
性能优化器模块 — 项目收尾层

公理溯源：存续公理 - 系统需要高效运行以长期存续

设计意图：
- LRU缓存管理
- 对象池复用
- 延迟加载
- 批量操作优化
- 零外部依赖，纯Python实现

大事做于细，难事成于易：
- 每个优化策略独立可用
- 渐进式应用，不破坏现有接口
- 可量化的性能提升
"""

import time
import threading
import functools
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from collections import OrderedDict
from enum import Enum

from logger import get_logger

logger = get_logger("PerfOptimizer")

T = TypeVar('T')


# ============================================================
# LRU缓存
# ============================================================

class LRUCache:
    """
    LRU缓存
    
    线程安全的最近最少使用缓存
    """
    
    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: Any) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self.hits += 1
                return self._cache[key]
            self.misses += 1
            return None
    
    def put(self, key: Any, value: Any):
        """设置缓存值"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = value
            else:
                if len(self._cache) >= self.maxsize:
                    self._cache.popitem(last=False)
                self._cache[key] = value
    
    def delete(self, key: Any):
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0
    
    def size(self) -> int:
        """缓存大小"""
        return len(self._cache)
    
    def stats(self) -> Dict:
        """缓存统计"""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        return {
            "size": self.size(),
            "maxsize": self.maxsize,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2%}"
        }


def lru_cache(maxsize: int = 128):
    """
    LRU缓存装饰器
    
    Args:
        maxsize: 最大缓存大小
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        cache = LRUCache(maxsize)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 构建缓存键
            key = (args, tuple(sorted(kwargs.items())))
            
            result = cache.get(key)
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            cache.put(key, result)
            return result
        
        wrapper.cache = cache
        wrapper.cache_clear = cache.clear
        wrapper.cache_info = cache.stats
        return wrapper
    
    return decorator


# ============================================================
# 对象池
# ============================================================

class ObjectPool:
    """
    对象池
    
    复用对象减少GC压力
    """
    
    def __init__(self, factory: Callable[[], T], reset: Callable[[T], None] = None,
                 maxsize: int = 50):
        self.factory = factory
        self.reset = reset or (lambda x: None)
        self.maxsize = maxsize
        self._pool: List[T] = []
        self._lock = threading.Lock()
        self.created = 0
        self.reused = 0
    
    def acquire(self) -> T:
        """获取对象"""
        with self._lock:
            if self._pool:
                obj = self._pool.pop()
                self.reused += 1
                return obj
        
        self.created += 1
        return self.factory()
    
    def release(self, obj: T):
        """释放对象"""
        with self._lock:
            if len(self._pool) < self.maxsize:
                self.reset(obj)
                self._pool.append(obj)
    
    def stats(self) -> Dict:
        """对象池统计"""
        return {
            "pool_size": len(self._pool),
            "maxsize": self.maxsize,
            "created": self.created,
            "reused": self.reused,
            "reuse_rate": f"{self.reused / max(1, self.created + self.reused):.2%}"
        }


# ============================================================
# 延迟加载
# ============================================================

class Lazy:
    """
    延迟加载器
    
    延迟计算直到首次访问
    """
    
    def __init__(self, factory: Callable[[], T]):
        self._factory = factory
        self._value: Optional[T] = None
        self._loaded = False
        self._lock = threading.Lock()
    
    def get(self) -> T:
        """获取值（首次访问时计算）"""
        if not self._loaded:
            with self._lock:
                if not self._loaded:
                    self._value = self._factory()
                    self._loaded = True
        return self._value
    
    def reset(self):
        """重置（下次访问重新计算）"""
        with self._lock:
            self._value = None
            self._loaded = False
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded


def lazy_property(func: Callable) -> property:
    """延迟加载属性装饰器"""
    attr_name = f"_lazy_{func.__name__}"
    
    @property
    def wrapper(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)
    
    return wrapper


# ============================================================
# 批量操作
# ============================================================

class BatchProcessor:
    """
    批量处理器
    
    将多个小操作合并为批量操作
    """
    
    def __init__(self, handler: Callable[[List], Any], batch_size: int = 100,
                 flush_interval: float = 5.0):
        self.handler = handler
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer: List = []
        self._lock = threading.Lock()
        self._last_flush = time.time()
        self.total_batches = 0
        self.total_items = 0
    
    def add(self, item: Any):
        """添加项目到批处理"""
        should_flush = False
        
        with self._lock:
            self._buffer.append(item)
            
            if len(self._buffer) >= self.batch_size:
                should_flush = True
            elif time.time() - self._last_flush >= self.flush_interval:
                should_flush = True
        
        if should_flush:
            self.flush()
    
    def flush(self):
        """刷新缓冲区"""
        with self._lock:
            if not self._buffer:
                return
            batch = self._buffer[:]
            self._buffer = []
        
        try:
            self.handler(batch)
            self.total_batches += 1
            self.total_items += len(batch)
            self._last_flush = time.time()
        except Exception as e:
            logger.error(f"批处理失败: {e}")
            # 放回缓冲区
            with self._lock:
                self._buffer = batch + self._buffer
    
    def stats(self) -> Dict:
        """批处理统计"""
        return {
            "buffer_size": len(self._buffer),
            "batch_size": self.batch_size,
            "total_batches": self.total_batches,
            "total_items": self.total_items,
            "avg_batch_size": (
                self.total_items / self.total_batches
                if self.total_batches > 0 else 0
            )
        }


# ============================================================
# 性能计时器
# ============================================================

class Timer:
    """性能计时器"""
    
    def __init__(self, name: str = ""):
        self.name = name
        self._start_time = 0
        self._end_time = 0
        self._elapsed = 0
    
    def __enter__(self):
        self._start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self._end_time = time.perf_counter()
        self._elapsed = self._end_time - self._start_time
        
        if self.name:
            logger.debug(f"[Timer] {self.name}: {self._elapsed:.4f}s")
    
    @property
    def elapsed(self) -> float:
        return self._elapsed


class PerformanceTracker:
    """
    性能追踪器
    
    追踪函数调用耗时
    """
    
    def __init__(self, max_entries: int = 1000):
        self._timings: Dict[str, List[float]] = {}
        self.max_entries = max_entries
        self._lock = threading.Lock()
    
    def record(self, name: str, duration: float):
        """记录耗时"""
        with self._lock:
            if name not in self._timings:
                self._timings[name] = []
            self._timings[name].append(duration)
            if len(self._timings[name]) > self.max_entries:
                self._timings[name] = self._timings[name][-self.max_entries:]
    
    def get_stats(self, name: str) -> Dict:
        """获取统计"""
        timings = self._timings.get(name, [])
        if not timings:
            return {"count": 0, "avg": 0, "min": 0, "max": 0, "p99": 0}
        
        sorted_t = sorted(timings)
        return {
            "count": len(sorted_t),
            "avg": sum(sorted_t) / len(sorted_t),
            "min": sorted_t[0],
            "max": sorted_t[-1],
            "p99": sorted_t[int(len(sorted_t) * 0.99)]
        }
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """获取所有统计"""
        return {name: self.get_stats(name) for name in self._timings}
    
    def report(self) -> str:
        """生成报告"""
        lines = ["性能报告:", "=" * 50]
        for name in sorted(self._timings.keys()):
            stats = self.get_stats(name)
            lines.append(
                f"  {name}: "
                f"调用={stats['count']}, "
                f"平均={stats['avg']:.4f}s, "
                f"P99={stats['p99']:.4f}s"
            )
        return "\n".join(lines)


def track_performance(tracker: PerformanceTracker = None):
    """
    性能追踪装饰器
    
    Args:
        tracker: 性能追踪器（可选）
        
    Returns:
        装饰器函数
    """
    _tracker = tracker or PerformanceTracker()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start
                _tracker.record(func.__name__, duration)
        
        wrapper._perf_tracker = _tracker
        return wrapper
    
    return decorator


# 全局性能追踪器
_global_tracker = PerformanceTracker()


def get_performance_tracker() -> PerformanceTracker:
    """获取全局性能追踪器"""
    return _global_tracker
