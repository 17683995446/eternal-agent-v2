"""
性能基准测试模块

公理溯源：存续公理 - 性能可量化，瓶颈可定位

设计意图：
- 知识图谱操作基准
- 主循环性能基准
- 内存使用追踪
- 基准结果对比
- 零外部依赖
"""

import gc
import sys
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from exceptions import EternalAgentError


class BenchmarkError(EternalAgentError):
    """基准测试异常"""
    pass


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    iterations: int
    total_ms: float
    avg_ms: float
    min_ms: float
    max_ms: float
    ops_per_sec: float
    memory_delta_mb: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_ms": round(self.total_ms, 2),
            "avg_ms": round(self.avg_ms, 3),
            "min_ms": round(self.min_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "ops_per_sec": round(self.ops_per_sec, 1),
            "memory_delta_mb": round(self.memory_delta_mb, 2),
        }


class Benchmark:
    """
    性能基准测试器

    职责：
    - 执行性能基准
    - 内存追踪
    - 结果对比
    - 报告生成
    """

    def __init__(self):
        self._results: List[BenchmarkResult] = []

    def run(
        self,
        name: str,
        fn: Callable,
        iterations: int = 100,
        warmup: int = 10,
    ) -> BenchmarkResult:
        """
        执行基准测试

        Args:
            name: 测试名称
            fn: 测试函数
            iterations: 迭代次数
            warmup: 预热次数
        """
        # 预热
        for _ in range(warmup):
            try:
                fn()
            except Exception:
                pass

        gc.collect()
        mem_before = self._get_memory_mb()

        # 执行
        times = []
        errors = 0
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                fn()
            except Exception:
                errors += 1
                continue
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        gc.collect()
        mem_after = self._get_memory_mb()

        if not times:
            return BenchmarkResult(
                name=name, iterations=iterations, total_ms=0,
                avg_ms=0, min_ms=0, max_ms=0, ops_per_sec=0,
            )

        total = sum(times)
        avg = total / len(times)
        result = BenchmarkResult(
            name=name,
            iterations=len(times),
            total_ms=total,
            avg_ms=avg,
            min_ms=min(times),
            max_ms=max(times),
            ops_per_sec=len(times) / (total / 1000) if total > 0 else 0,
            memory_delta_mb=mem_after - mem_before,
        )

        self._results.append(result)
        return result

    def run_suite(self, knowledge_graph=None) -> Dict[str, BenchmarkResult]:
        """运行完整基准测试套件"""
        results = {}

        if knowledge_graph is not None:
            # 节点添加
            def bench_add_node():
                knowledge_graph.add_node(f"bench_node_{id(threading.current_thread())}", node_type="entity")
            results["add_node"] = self.run("add_node", bench_add_node, iterations=500, warmup=50)

            # 边添加
            def bench_add_edge():
                knowledge_graph.add_edge("A", "B", relation="test", weight=0.5)
            results["add_edge"] = self.run("add_edge", bench_add_edge, iterations=500, warmup=50)

            # 节点查询
            def bench_get_node():
                knowledge_graph._nodes.get("A")
            results["get_node"] = self.run("get_node", bench_get_node, iterations=1000, warmup=100)

            # 统计
            def bench_stats():
                knowledge_graph.stats()
            results["stats"] = self.run("stats", bench_stats, iterations=1000, warmup=100)

            # 健康检查
            def bench_health():
                knowledge_graph.health_check()
            results["health_check"] = self.run("health_check", bench_health, iterations=100, warmup=10)

        # 通用操作
        def bench_dict_operations():
            d = {}
            for i in range(100):
                d[f"key_{i}"] = f"value_{i}"
            for i in range(100):
                _ = d.get(f"key_{i}")
        results["dict_operations"] = self.run("dict_operations", bench_dict_operations, iterations=100, warmup=10)

        def bench_json_serialization():
            import json
            data = {f"k_{i}": {"v": i, "tags": ["a", "b"]} for i in range(100)}
            json.dumps(data, ensure_ascii=False)
        results["json_serialization"] = self.run("json_serialization", bench_json_serialization, iterations=100, warmup=10)

        return results

    def get_results(self) -> List[Dict[str, Any]]:
        """获取所有结果"""
        return [r.to_dict() for r in self._results]

    def compare(self, baseline: Dict[str, float]) -> Dict[str, Any]:
        """与基准线对比"""
        comparison = {}
        for result in self._results:
            if result.name in baseline:
                base = baseline[result.name]
                ratio = result.avg_ms / base if base > 0 else 0
                comparison[result.name] = {
                    "current_avg_ms": round(result.avg_ms, 3),
                    "baseline_avg_ms": round(base, 3),
                    "ratio": round(ratio, 2),
                    "regression": ratio > 1.5,
                }
        return comparison

    def generate_report(self) -> str:
        """生成报告"""
        lines = [
            "┌─ 性能基准测试报告 ─────────────────┐",
            f"│ 测试数量: {len(self._results):<23}│",
            "├───────────────────────────────────┤",
        ]

        for r in self._results:
            lines.append(f"│ {r.name:<20} {r.avg_ms:>8.3f}ms/op    │")
            lines.append(f"│   min={r.min_ms:.3f}ms max={r.max_ms:.3f}ms    │")
            lines.append(f"│   {r.ops_per_sec:>8.1f} ops/s              │")

        lines.append("└───────────────────────────────────┘")
        return "\n".join(lines)

    @staticmethod
    def _get_memory_mb() -> float:
        """获取当前进程内存（MB）"""
        try:
            status_file = "/proc/self/status"
            if not __import__('pathlib').Path(status_file).exists():
                return 0.0
            with open(status_file, 'r') as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024
        except Exception:
            pass
        return 0.0
