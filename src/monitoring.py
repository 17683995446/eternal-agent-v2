"""
监控集成模块 — 部署与运维层

公理溯源：存续公理 - 系统需要持续监控以保持稳定运行

设计意图：
- Prometheus格式指标导出
- 系统指标收集
- 自定义指标支持
- 指标聚合和暴露
"""

import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from logger import get_logger
from utils import now_iso

logger = get_logger("Monitoring")


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """指标"""
    name: str
    metric_type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    timestamp: float = field(default_factory=time.time)


class MetricsRegistry:
    """
    指标注册表
    
    管理所有监控指标
    """
    
    def __init__(self, namespace: str = "eternal_agent"):
        self.namespace = namespace
        self._metrics: Dict[str, Metric] = {}
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def register(self, name: str, metric_type: MetricType, 
                 description: str = "", labels: Dict[str, str] = None) -> Metric:
        """
        注册指标
        
        Args:
            name: 指标名称
            metric_type: 指标类型
            description: 描述
            labels: 标签
            
        Returns:
            指标对象
        """
        full_name = f"{self.namespace}_{name}"
        
        metric = Metric(
            name=full_name,
            metric_type=metric_type,
            value=0,
            labels=labels or {},
            description=description
        )
        
        with self._lock:
            self._metrics[full_name] = metric
        
        return metric
    
    def counter(self, name: str, value: float = 1, labels: Dict[str, str] = None):
        """
        递增计数器
        
        Args:
            name: 指标名称
            value: 增量值
            labels: 标签
        """
        full_name = f"{self.namespace}_{name}"
        
        with self._lock:
            self._counters[full_name] += value
    
    def gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """
        设置仪表值
        
        Args:
            name: 指标名称
            value: 值
            labels: 标签
        """
        full_name = f"{self.namespace}_{name}"
        
        with self._lock:
            self._gauges[full_name] = value
    
    def histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """
        记录直方图值
        
        Args:
            name: 指标名称
            value: 值
            labels: 标签
        """
        full_name = f"{self.namespace}_{name}"
        
        with self._lock:
            self._histograms[full_name].append(value)
            # 限制历史长度
            if len(self._histograms[full_name]) > 1000:
                self._histograms[full_name] = self._histograms[full_name][-1000:]
    
    def observe(self, name: str, value: float):
        """观察值（histogram别名）"""
        self.histogram(name, value)
    
    def get_counter(self, name: str) -> float:
        """获取计数器值"""
        full_name = f"{self.namespace}_{name}"
        return self._counters.get(full_name, 0)
    
    def get_gauge(self, name: str) -> float:
        """获取仪表值"""
        full_name = f"{self.namespace}_{name}"
        return self._gauges.get(full_name, 0)
    
    def get_histogram_stats(self, name: str) -> Dict:
        """获取直方图统计"""
        full_name = f"{self.namespace}_{name}"
        values = self._histograms.get(full_name, [])
        
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}
        
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }
    
    def export_prometheus(self) -> str:
        """
        导出Prometheus格式指标
        
        Returns:
            Prometheus格式文本
        """
        lines = []
        
        with self._lock:
            # 导出计数器
            for name, value in self._counters.items():
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {value}")
            
            # 导出仪表
            for name, value in self._gauges.items():
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {value}")
            
            # 导出直方图
            for name, values in self._histograms.items():
                if not values:
                    continue
                
                lines.append(f"# TYPE {name} histogram")
                
                sorted_values = sorted(values)
                count = len(sorted_values)
                total = sum(sorted_values)
                
                # 分位数
                quantiles = [0.5, 0.9, 0.95, 0.99]
                for q in quantiles:
                    idx = int(count * q) - 1
                    idx = max(0, min(idx, count - 1))
                    lines.append(f'{name}{{quantile="{q}"}} {sorted_values[idx]}')
                
                lines.append(f"{name}_count {count}")
                lines.append(f"{name}_sum {total}")
        
        return "\n".join(lines)
    
    def get_all_metrics(self) -> Dict:
        """获取所有指标"""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: self.get_histogram_stats(k.replace(f"{self.namespace}_", "")) 
                          for k in self._histograms}
        }


class SystemMetrics:
    """
    系统指标收集器
    
    收集系统运行指标
    """
    
    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
        
        # 注册系统指标
        self.registry.register("cpu_usage", MetricType.GAUGE, "CPU使用率")
        self.registry.register("memory_usage", MetricType.GAUGE, "内存使用率")
        self.registry.register("disk_usage", MetricType.GAUGE, "磁盘使用率")
        self.registry.register("requests_total", MetricType.COUNTER, "总请求数")
        self.registry.register("request_duration", MetricType.HISTOGRAM, "请求耗时")
        self.registry.register("errors_total", MetricType.COUNTER, "总错误数")
        self.registry.register("tasks_processed", MetricType.COUNTER, "处理任务数")
        self.registry.register("knowledge_nodes", MetricType.GAUGE, "知识节点数")
        self.registry.register("knowledge_edges", MetricType.GAUGE, "知识边数")
    
    def record_request(self, duration: float, success: bool = True):
        """
        记录请求
        
        Args:
            duration: 请求耗时（秒）
            success: 是否成功
        """
        self.registry.counter("requests_total")
        self.registry.histogram("request_duration", duration)
        
        if not success:
            self.registry.counter("errors_total")
    
    def record_task_processed(self, count: int = 1):
        """记录任务处理"""
        self.registry.counter("tasks_processed", count)
    
    def update_knowledge_stats(self, nodes: int, edges: int):
        """更新知识图谱统计"""
        self.registry.gauge("knowledge_nodes", nodes)
        self.registry.gauge("knowledge_edges", edges)
    
    def collect_system_metrics(self) -> Dict:
        """
        收集系统指标
        
        Returns:
            系统指标字典
        """
        import os
        import sys
        
        metrics = {}
        
        # 内存使用（简化）
        try:
            import resource
            mem_info = resource.getrusage(resource.RUSAGE_SELF)
            metrics["memory_mb"] = mem_info.ru_maxrss / 1024
        except Exception:
            metrics["memory_mb"] = 0
        
        # Python信息
        metrics["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}"
        metrics["platform"] = sys.platform
        
        # 进程ID
        metrics["pid"] = os.getpid()
        
        return metrics


# 全局注册表
_default_registry: Optional[MetricsRegistry] = None


def get_metrics_registry() -> MetricsRegistry:
    """获取全局指标注册表"""
    global _default_registry
    
    if _default_registry is None:
        _default_registry = MetricsRegistry()
    
    return _default_registry


def get_system_metrics() -> SystemMetrics:
    """获取系统指标收集器"""
    return SystemMetrics(get_metrics_registry())
