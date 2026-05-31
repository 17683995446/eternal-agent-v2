"""
交互增强模块 — 知识浏览器、日志分析、监控面板、数据导入导出、系统面板

公理溯源：存续公理 — 系统可观测、可控制

设计意图：
- 知识图谱浏览器：文本可视化
- 任务执行追踪：状态追踪
- 日志分析：解析日志文件
- 性能监控面板：实时资源
- 告警通知：异常时通知
- 数据导入导出：JSON/CSV
- 系统信息面板：综合状态
"""

import json
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from logger import get_logger

logger = get_logger("Interaction")


# ============================================================
# 阶段73: 知识图谱浏览器
# ============================================================

class KnowledgeBrowser:
    """知识图谱文本浏览器"""

    def __init__(self, kg):
        self.kg = kg

    def display_node(self, name: str) -> str:
        """显示节点详情"""
        node = self.kg.get_node(name)
        if not node:
            return f"节点不存在: {name}"

        edges_from = self.kg.get_edges_from(name)
        edges_to = self.kg.get_edges_to(name)

        lines = [
            f"节点: {name}",
            f"  类型: {node.node_type}",
            f"  有效: {node.valid}",
            f"  创建: {node.created_at}",
            f"  更新: {node.updated_at}",
            f"  出边: {len(edges_from)}",
            f"  入边: {len(edges_to)}",
        ]

        if node.attributes:
            lines.append("  属性:")
            for k, v in node.attributes.items():
                lines.append(f"    {k}: {v}")

        return "\n".join(lines)

    def display_tree(self, root: str, max_depth: int = 3) -> str:
        """树形展示知识"""
        lines = [root]

        def _walk(node_name, prefix, depth):
            if depth >= max_depth:
                return
            edges = self.kg.get_edges_from(node_name)
            for i, edge in enumerate(edges):
                is_last = (i == len(edges) - 1)
                connector = "└── " if is_last else "├── "
                child_prefix = prefix + ("    " if is_last else "│   ")
                weight_str = f" ({edge.weight:.2f})" if edge.weight < 1.0 else ""
                lines.append(f"{prefix}{connector}{edge.target}{weight_str}")
                _walk(edge.target, child_prefix, depth + 1)

        _walk(root, "", 0)
        return "\n".join(lines)

    def search(self, keyword: str) -> List[str]:
        """搜索节点"""
        results = []
        for node in self.kg.get_all_nodes():
            if keyword.lower() in node.name.lower():
                results.append(node.name)
        return results


# ============================================================
# 阶段74: 任务执行追踪
# ============================================================

@dataclass
class TaskTrace:
    """任务追踪记录"""
    task_name: str
    state: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    retries: int = 0


class TaskTracker:
    """任务执行追踪器"""

    def __init__(self):
        self._traces: Dict[str, TaskTrace] = {}

    def start(self, task_name: str):
        """记录任务开始"""
        trace = TaskTrace(task_name=task_name, state="running",
                          started_at=datetime.now().isoformat())
        self._traces[task_name] = trace

    def complete(self, task_name: str, result: str = ""):
        """记录任务完成"""
        if task_name in self._traces:
            t = self._traces[task_name]
            t.state = "completed"
            t.completed_at = datetime.now().isoformat()
            t.result = result

    def fail(self, task_name: str, error: str = ""):
        """记录任务失败"""
        if task_name in self._traces:
            t = self._traces[task_name]
            t.state = "failed"
            t.completed_at = datetime.now().isoformat()
            t.error = error

    def get_trace(self, task_name: str) -> Optional[TaskTrace]:
        """获取追踪记录"""
        return self._traces.get(task_name)

    def get_all(self) -> List[TaskTrace]:
        """获取所有记录"""
        return list(self._traces.values())

    def get_failed(self) -> List[TaskTrace]:
        """获取失败记录"""
        return [t for t in self._traces.values() if t.state == "failed"]

    def summary(self) -> Dict:
        """摘要统计"""
        total = len(self._traces)
        completed = sum(1 for t in self._traces.values() if t.state == "completed")
        failed = sum(1 for t in self._traces.values() if t.state == "failed")
        running = sum(1 for t in self._traces.values() if t.state == "running")
        return {"total": total, "completed": completed, "failed": failed, "running": running}


# ============================================================
# 阶段75: 日志分析工具
# ============================================================

class LogAnalyzer:
    """日志分析器"""

    def __init__(self, log_path: Path):
        self.log_path = log_path

    def count_by_level(self) -> Dict[str, int]:
        """按级别统计"""
        counts = defaultdict(int)
        if not self.log_path.exists():
            return dict(counts)

        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                    level_prefix = f"| {level} "
                    if level_prefix in line or line.strip().startswith(level + ":"):
                        counts[level] += 1
                        break

        return dict(counts)

    def get_errors(self, limit: int = 50) -> List[str]:
        """获取错误日志"""
        errors = []
        if not self.log_path.exists():
            return errors

        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if "| ERROR " in line or "| CRITICAL " in line or line.strip().startswith("ERROR:") or line.strip().startswith("CRITICAL:"):
                    errors.append(line.strip())
                    if len(errors) >= limit:
                        break

        return errors

    def search(self, keyword: str, limit: int = 50) -> List[str]:
        """搜索日志"""
        results = []
        if not self.log_path.exists():
            return results

        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if keyword.lower() in line.lower():
                    results.append(line.strip())
                    if len(results) >= limit:
                        break

        return results


# ============================================================
# 阶段76: 性能监控面板
# ============================================================

class MonitorPanel:
    """性能监控面板"""

    def __init__(self):
        from monitor import monitor
        self.monitor = monitor

    def snapshot(self) -> Dict:
        """获取资源快照"""
        status = self.monitor.check_health()
        return {
            "cpu_percent": round(status.cpu_percent, 1),
            "memory_mb": round(status.memory_mb, 1),
            "disk_percent": round(status.disk_percent, 1),
            "is_healthy": status.is_healthy,
            "warnings": status.warnings,
            "timestamp": datetime.now().isoformat(),
        }

    def format_report(self) -> str:
        """格式化报告"""
        s = self.snapshot()
        lines = [
            "=== 性能监控 ===",
            f"CPU:    {s['cpu_percent']}%",
            f"内存:   {s['memory_mb']} MB",
            f"磁盘:   {s['disk_percent']}%",
            f"状态:   {'正常' if s['is_healthy'] else '异常'}",
        ]
        if s['warnings']:
            lines.append("告警:")
            for w in s['warnings']:
                lines.append(f"  - {w}")
        return "\n".join(lines)


# ============================================================
# 阶段77: 告警通知机制
# ============================================================

@dataclass
class Alert:
    """告警"""
    level: str       # info/warning/critical
    message: str
    source: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AlertManager:
    """告警管理器"""

    def __init__(self, max_alerts: int = 100):
        self._alerts: List[Alert] = []
        self._max_alerts = max_alerts
        self._handlers: List = []

    def add_handler(self, handler):
        """添加告警处理器（回调函数）"""
        self._handlers.append(handler)

    def send(self, level: str, message: str, source: str = ""):
        """发送告警"""
        alert = Alert(level=level, message=message, source=source)
        self._alerts.append(alert)

        # 限制数量
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]

        # 调用处理器
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.warning(f"告警处理器异常: {e}")

        logger.warning(f"告警 [{level}]: {message}")

    def get_recent(self, limit: int = 20) -> List[Alert]:
        """获取最近告警"""
        return self._alerts[-limit:]

    def get_by_level(self, level: str) -> List[Alert]:
        """按级别获取"""
        return [a for a in self._alerts if a.level == level]


# ============================================================
# 阶段78: 数据导入导出
# ============================================================

class DataImporterExporter:
    """数据导入导出器"""

    def __init__(self, kg):
        self.kg = kg

    def export_nodes_csv(self, path: Path) -> int:
        """导出节点为CSV"""
        nodes = self.kg.get_all_nodes()
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'type', 'valid', 'created_at', 'updated_at'])
            for node in nodes:
                writer.writerow([node.name, node.node_type, node.valid,
                                node.created_at, node.updated_at])
        return len(nodes)

    def export_edges_csv(self, path: Path) -> int:
        """导出边为CSV"""
        edges = self.kg.get_all_edges()
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['source', 'target', 'relation', 'weight'])
            for edge in edges:
                writer.writerow([edge.source, edge.target, edge.relation, edge.weight])
        return len(edges)

    def import_nodes_csv(self, path: Path) -> int:
        """从CSV导入节点"""
        count = 0
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.kg.add_node(
                    name=row['name'],
                    node_type=row.get('type', 'entity'),
                )
                count += 1
        return count

    def export_json(self, path: Path) -> bool:
        """导出为JSON"""
        data = {
            "nodes": [n.to_dict() for n in self.kg.get_all_nodes()],
            "edges": [e.to_dict() for e in self.kg.get_all_edges()],
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True

    def import_json(self, path: Path) -> Dict:
        """从JSON导入"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        count_nodes = 0
        count_edges = 0

        for node_data in data.get('nodes', []):
            self.kg.add_node(
                name=node_data['name'],
                node_type=node_data.get('node_type', 'entity'),
            )
            count_nodes += 1

        for edge_data in data.get('edges', []):
            self.kg.add_edge(
                source=edge_data['source'],
                target=edge_data['target'],
                relation=edge_data.get('relation', '关联'),
                weight=edge_data.get('weight', 0.5),
            )
            count_edges += 1

        return {"nodes": count_nodes, "edges": count_edges}


# ============================================================
# 阶段79: 系统信息面板
# ============================================================

class SystemPanel:
    """系统信息面板"""

    def __init__(self, agent):
        self.agent = agent

    def full_report(self) -> str:
        """生成完整报告"""
        lines = [
            "=" * 60,
            "  永恒自驱智能体 — 系统报告",
            "=" * 60,
            "",
        ]

        # 系统状态
        status = self.agent.get_status()
        lines.extend([
            "【系统状态】",
            f"  状态: {status.state}",
            f"  运行次数: {status.run_counter}",
            f"  完成任务: {status.total_tasks_completed}",
            f"  失败任务: {status.total_tasks_failed}",
            "",
        ])

        # 知识图谱
        kg_stats = self.agent.get_kg_stats()
        lines.extend([
            "【知识图谱】",
            f"  节点数: {kg_stats['node_count']}",
            f"  边数: {kg_stats['edge_count']}",
            f"  平均权重: {kg_stats['average_weight']}",
            f"  密度: {kg_stats['density']}",
            "",
        ])

        # 任务队列
        queue_stats = self.agent.task_queue.stats()
        lines.extend([
            "【任务队列】",
            f"  当前大小: {queue_stats['size']}/{queue_stats['max_size']}",
            f"  已丢弃: {queue_stats['discarded_count']}",
            "",
        ])

        # 资源
        monitor_panel = MonitorPanel()
        lines.extend([
            "【资源监控】",
            monitor_panel.format_report(),
            "",
        ])

        lines.append("=" * 60)
        return "\n".join(lines)
