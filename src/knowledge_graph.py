"""
知识图谱模块 — 记忆层核心

公理溯源：记忆公理 — 智能 = 结构化、可沉淀、可关联、可检索、可推演的历史经验

设计意图：
- 节点(Node)：代表一次任务、一次认知、一个实体经验
- 边(Edge)：代表实体之间的关联逻辑，权重是智能经验积累的唯一量化
- 全本地文件持久化：断电、重启、崩溃不丢失记忆
- 零外部依赖

大事做于细，难事成于易：
- 每个操作独立方法，职责单一
- 自动保存机制，调用者无需关心持久化
- 幂等设计，重复添加不报错
"""

from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path
import os

from models import Node, Edge, Task
from constants import (
    KG_SAVE_PATH,
    NODE_DEFAULT_VALID,
    EDGE_DEFAULT_WEIGHT,
    KNOWLEDGE_TRIM_THRESHOLD,
    TASK_DERIVE_WEIGHT_THRESHOLD,
    NodeType,
    RelationType,
)
from exceptions import (
    KnowledgeGraphError,
    NodeNotFoundError,
    EdgeNotFoundError,
    PersistenceError,
)
from utils import read_json, write_json, now_iso
from logger import get_logger

logger = get_logger("KnowledgeGraph")


class KnowledgeGraph:
    """
    知识图谱 — 系统唯一长期记忆载体

    公理溯源：记忆公理 — 所有行为必须落盘结构化数据

    核心能力：
    - 节点CRUD：添加、查询、删除认知实体
    - 边CRUD：添加、查询、更新加权关系
    - 持久化：自动加载/保存，重启不丢经验
    - 推演：基于高权重关联生成新任务
    - 进化：自动淘汰低价值知识
    """

    def __init__(self, save_path: Optional[Path] = None):
        """
        初始化知识图谱

        Args:
            save_path: 持久化文件路径，默认使用 constants.KG_SAVE_PATH
        """
        self.save_path = save_path or KG_SAVE_PATH
        self._nodes: Dict[str, Node] = {}  # name -> Node
        self._edges: List[Edge] = []       # Edge列表
        self._modified = False             # 脏标记，避免不必要的保存

        # 自动加载已有记忆
        self.load()

    # ============================================================
    # 阶段21: 知识图谱类骨架 — 初始化与基础属性
    # ============================================================

    @property
    def node_count(self) -> int:
        """节点数量"""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """边数量"""
        return len(self._edges)

    def is_empty(self) -> bool:
        """图谱是否为空"""
        return len(self._nodes) == 0

    # ============================================================
    # 阶段22: 节点新增方法 — 添加认知实体
    # ============================================================

    def add_node(
        self,
        name: str,
        node_type: str = NodeType.ENTITY,
        attributes: Optional[Dict] = None
    ) -> Node:
        """
        添加节点（幂等：已存在则返回已有节点）

        Args:
            name: 节点名称（唯一标识）
            node_type: 节点类型
            attributes: 扩展属性

        Returns:
            Node: 节点对象
        """
        # 参数验证
        if name is None:
            raise ValueError("节点名称不能为None")
        if not isinstance(name, str):
            raise TypeError(f"节点名称必须是字符串，实际为 {type(name).__name__}")
        if not name.strip():
            raise ValueError("节点名称不能为空字符串")

        if name in self._nodes:
            logger.debug(f"节点已存在: {name}")
            return self._nodes[name]

        node = Node(
            name=name,
            node_type=node_type,
            attributes=attributes or {}
        )
        self._nodes[name] = node
        self._modified = True

        logger.debug(f"节点添加: {name} ({node_type})")
        self.save()
        return node

    def add_task_node(self, task: Task) -> Node:
        """
        从任务创建节点

        Args:
            task: 任务对象

        Returns:
            Node: 任务节点
        """
        return self.add_node(
            name=task.name,
            node_type=NodeType.TASK,
            attributes={
                "state": task.state,
                "priority": task.priority,
                "result": task.result,
                "error": task.error,
            }
        )

    # ============================================================
    # 阶段23: 边新增方法 — 添加加权关系
    # ============================================================

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str = RelationType.RELATED,
        weight: float = EDGE_DEFAULT_WEIGHT,
        attributes: Optional[Dict] = None
    ) -> Edge:
        """
        添加边（自动创建不存在的端点节点）

        Args:
            source: 源节点名称
            target: 目标节点名称
            relation: 关系类型
            weight: 权重值（0.0-1.0）
            attributes: 扩展属性

        Returns:
            Edge: 边对象
        """
        # 自动创建端点节点
        self.add_node(source)
        self.add_node(target)

        # 检查是否已存在相同边
        for edge in self._edges:
            if (edge.source == source and
                edge.target == target and
                edge.relation == relation):
                # 已存在，更新权重（使用验证后的值）
                from constants import EDGE_WEIGHT_MIN, EDGE_WEIGHT_MAX
                validated_weight = max(EDGE_WEIGHT_MIN, min(EDGE_WEIGHT_MAX, weight))
                edge.weight = validated_weight
                edge.updated_at = now_iso()
                self._modified = True
                logger.debug(f"边权重更新: {source} -> {target} = {edge.weight}")
                self.save()
                return edge

        # 创建新边
        edge = Edge(
            source=source,
            target=target,
            relation=relation,
            weight=weight,
            attributes=attributes or {}
        )
        self._edges.append(edge)
        self._modified = True

        logger.debug(f"边添加: {source} -[{relation}:{weight}]-> {target}")
        self.save()
        return edge

    def add_derived_edge(self, source_task: str, target_task: str, weight: float = 0.8) -> Edge:
        """
        添加任务衍生关系（自驱公理核心）

        Args:
            source_task: 源任务名称
            target_task: 目标任务名称
            weight: 衍生权重

        Returns:
            Edge: 衍生边
        """
        return self.add_edge(
            source=source_task,
            target=target_task,
            relation=RelationType.DERIVED,
            weight=weight
        )

    # ============================================================
    # 阶段24: 记忆加载 — 重启不丢失经验
    # ============================================================

    def load(self) -> bool:
        """
        从文件加载知识图谱

        Returns:
            bool: 是否成功加载
        """
        try:
            # 安全检查：文件大小限制（50MB）
            if self.save_path and self.save_path.exists():
                file_size = self.save_path.stat().st_size
                max_size = 50 * 1024 * 1024  # 50MB
                if file_size > max_size:
                    logger.error(f"知识图谱文件过大: {file_size} bytes > {max_size} bytes")
                    return False

            data = read_json(self.save_path, max_size=50*1024*1024)
            if data is None:
                logger.info("知识图谱文件不存在，创建新图谱")
                return False

            # 加载节点
            self._nodes = {}
            for node_data in data.get("nodes", []):
                node = Node.from_dict(node_data)
                self._nodes[node.name] = node

            # 加载边
            self._edges = []
            for edge_data in data.get("edges", []):
                edge = Edge.from_dict(edge_data)
                self._edges.append(edge)

            logger.info(f"知识图谱加载成功: {self.node_count} 节点, {self.edge_count} 边")
            return True

        except Exception as e:
            logger.error(f"知识图谱加载失败: {e}")
            self._nodes = {}
            self._edges = []
            return False

    # ============================================================
    # 阶段25: 记忆固化 — 所有行为落盘
    # ============================================================

    def save(self) -> bool:
        """
        保存知识图谱到文件

        Returns:
            bool: 是否成功保存
        """
        if not self._modified:
            return True  # 无修改，跳过保存

        try:
            # 创建副本防止并发修改导致迭代异常
            nodes_snapshot = list(self._nodes.values())
            edges_snapshot = list(self._edges)
            data = {
                "nodes": [node.to_dict() for node in nodes_snapshot],
                "edges": [edge.to_dict() for edge in edges_snapshot],
                "metadata": {
                    "saved_at": now_iso(),
                    "node_count": self.node_count,
                    "edge_count": self.edge_count,
                }
            }

            if write_json(self.save_path, data):
                self._modified = False
                logger.debug(f"知识图谱保存成功: {self.save_path}")
                return True
            logger.warning(f"知识图谱保存失败: write_json 返回 False (路径: {self.save_path})")
            return False

        except Exception as e:
            logger.error(f"知识图谱保存失败: {e}")
            raise PersistenceError(f"保存失败: {e}")

    def force_save(self) -> bool:
        """强制保存（忽略脏标记）"""
        self._modified = True
        return self.save()

    # ============================================================
    # 阶段26: 节点查询 — 按名称检索
    # ============================================================

    def get_node(self, name: str) -> Optional[Node]:
        """
        获取节点

        Args:
            name: 节点名称

        Returns:
            Optional[Node]: 节点对象，不存在返回None
        """
        if name is None:
            return None
        return self._nodes.get(name)

    def has_node(self, name: str) -> bool:
        """检查节点是否存在"""
        return name in self._nodes

    def get_all_nodes(self) -> List[Node]:
        """获取所有节点"""
        return list(self._nodes.values())

    def get_nodes_by_type(self, node_type: str) -> List[Node]:
        """按类型获取节点"""
        return [n for n in self._nodes.values() if n.node_type == node_type]

    # ============================================================
    # 阶段27: 边查询 — 按源/目标检索
    # ============================================================

    def get_edges_from(self, source: str) -> List[Edge]:
        """获取从指定节点出发的所有边"""
        return [e for e in self._edges if e.source == source]

    def get_edges_to(self, target: str) -> List[Edge]:
        """获取指向指定节点的所有边"""
        return [e for e in self._edges if e.target == target]

    def get_edges_between(self, source: str, target: str) -> List[Edge]:
        """获取两个节点之间的所有边"""
        return [e for e in self._edges if e.source == source and e.target == target]

    def get_related_nodes(self, node_name: str) -> Dict[str, List[Edge]]:
        """
        获取与指定节点相关的所有节点及其边

        Args:
            node_name: 节点名称

        Returns:
            dict: {邻居节点名: [Edge列表]}
        """
        result: Dict[str, List[Edge]] = {}
        for edge in self._edges:
            if edge.source == node_name:
                result.setdefault(edge.target, []).append(edge)
            elif edge.target == node_name:
                result.setdefault(edge.source, []).append(edge)
        return result

    def get_all_edges(self) -> List[Edge]:
        """获取所有边"""
        return self._edges.copy()

    # ============================================================
    # 阶段28: 节点删除 — 级联删除相关边
    # ============================================================

    def remove_node(self, name: str) -> bool:
        """
        删除节点（级联删除相关边）

        Args:
            name: 节点名称

        Returns:
            bool: 是否成功删除
        """
        if name not in self._nodes:
            return False

        # 删除节点
        del self._nodes[name]

        # 级联删除相关边
        original_count = len(self._edges)
        self._edges = [e for e in self._edges if e.source != name and e.target != name]
        removed_edges = original_count - len(self._edges)

        self._modified = True
        logger.info(f"节点删除: {name} (级联删除 {removed_edges} 条边)")
        self.save()
        return True

    def remove_edge(self, source: str, target: str, relation: str = None) -> bool:
        """
        删除边

        Args:
            source: 源节点
            target: 目标节点
            relation: 关系类型（可选，不指定则删除所有source->target的边）

        Returns:
            bool: 是否成功删除
        """
        original_count = len(self._edges)
        if relation:
            self._edges = [e for e in self._edges 
                          if not (e.source == source and e.target == target and e.relation == relation)]
        else:
            self._edges = [e for e in self._edges 
                          if not (e.source == source and e.target == target)]
        
        removed = original_count - len(self._edges)
        if removed > 0:
            self._modified = True
            logger.info(f"边删除: {source}->{target} ({removed}条)")
            self.save()
            return True
        return False

    # ============================================================
    # 阶段29: 边权重更新 — 智能迭代核心
    # ============================================================

    def update_edge_weight(self, source: str, target: str, delta: float) -> bool:
        """
        更新边权重

        Args:
            source: 源节点
            target: 目标节点
            delta: 权重变化量（可正可负）

        Returns:
            bool: 是否成功更新
        """
        for edge in self._edges:
            if edge.source == source and edge.target == target:
                old_weight = edge.weight
                edge.update_weight(delta)
                self._modified = True
                logger.debug(f"边权重更新: {source}->{target} {old_weight:.2f} -> {edge.weight:.2f}")
                self.save()
                return True
        return False

    def reinforce_edge(self, source: str, target: str, amount: float = 0.1) -> bool:
        """强化边权重（正向反馈）"""
        return self.update_edge_weight(source, target, amount)

    def weaken_edge(self, source: str, target: str, amount: float = 0.1) -> bool:
        """弱化边权重（负向反馈）"""
        return self.update_edge_weight(source, target, -amount)

    # ============================================================
    # 阶段30: 图谱统计 — 节点数/边数/平均权重
    # ============================================================

    def stats(self) -> Dict:
        """
        获取图谱统计信息

        Returns:
            Dict: 统计信息
        """
        if not self._edges:
            avg_weight = 0.0
        else:
            avg_weight = sum(e.weight for e in self._edges) / len(self._edges)

        # 按类型统计节点
        node_type_counts = {}
        for node in self._nodes.values():
            node_type_counts[node.node_type] = node_type_counts.get(node.node_type, 0) + 1

        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "average_weight": round(avg_weight, 3),
            "node_types": node_type_counts,
            "density": self._calculate_density(),
        }

    def _calculate_density(self) -> float:
        """计算图谱密度"""
        n = self.node_count
        if n <= 1:
            return 0.0
        max_edges = n * (n - 1)
        return round(self.edge_count / max_edges, 4) if max_edges > 0 else 0.0

    # ============================================================
    # 阶段31: 知识推演 — 高权重边生成新任务
    # ============================================================

    def derive_new_tasks(self, node_name: str, threshold: float = None) -> List[str]:
        """
        基于已有知识推演新任务

        公理溯源：自驱公理 — 知识关联自动推演新任务

        Args:
            node_name: 起始节点名称
            threshold: 权重阈值，默认使用 constants.TASK_DERIVE_WEIGHT_THRESHOLD

        Returns:
            List[str]: 推演出的新任务名称列表
        """
        threshold = threshold or TASK_DERIVE_WEIGHT_THRESHOLD

        if not self.has_node(node_name):
            return []

        new_tasks = []
        for edge in self.get_edges_from(node_name):
            # 只采信高价值、高权重关联
            if edge.weight > threshold:
                task_name = f"推演任务:{edge.target}"
                new_tasks.append(task_name)
                logger.debug(f"知识推演: {node_name} -> {task_name} (权重:{edge.weight:.2f})")

        return new_tasks

    # ============================================================
    # 阶段32: 低价值淘汰 — 权重<0.1自动删除
    # ============================================================

    def trim_invalid_knowledge(self, threshold: float = None) -> int:
        """
        自动淘汰低价值知识

        公理溯源：自驱公理 — 自我精简迭代，防臃肿老化

        Args:
            threshold: 淘汰阈值，默认使用 constants.KNOWLEDGE_TRIM_THRESHOLD

        Returns:
            int: 被删除的边数量
        """
        threshold = threshold or KNOWLEDGE_TRIM_THRESHOLD

        original_count = len(self._edges)
        self._edges = [e for e in self._edges if e.weight > threshold]
        removed = original_count - len(self._edges)

        if removed > 0:
            self._modified = True
            logger.info(f"知识精简: 删除 {removed} 条低价值边 (阈值:{threshold})")
            self.save()

        return removed

    # ============================================================
    # 阶段33: 可视化导出 — Mermaid/Graphviz格式
    # ============================================================

    def export_mermaid(self) -> str:
        """
        导出为Mermaid格式

        Returns:
            str: Mermaid图表代码
        """
        lines = ["graph TD"]

        # 添加节点
        for node in self._nodes.values():
            safe_name = node.name.replace(" ", "_").replace(":", "_")
            lines.append(f"    {safe_name}[{node.name}]")

        # 添加边
        for edge in self._edges:
            src = edge.source.replace(" ", "_").replace(":", "_")
            tgt = edge.target.replace(" ", "_").replace(":", "_")
            weight_label = f"|{edge.weight:.2f}|" if edge.weight < 1.0 else ""
            lines.append(f"    {src} -->{weight_label} {tgt}")

        return "\n".join(lines)

    def export_graphviz(self) -> str:
        """
        导出为Graphviz DOT格式

        Returns:
            str: DOT代码
        """
        lines = ["digraph KnowledgeGraph {"]
        lines.append("    rankdir=LR;")
        lines.append("    node [shape=box];")

        # 添加节点
        for node in self._nodes.values():
            safe_name = node.name.replace(" ", "_").replace("-", "_")
            lines.append(f'    "{safe_name}" [label="{node.name}"];')

        # 添加边
        for edge in self._edges:
            src = edge.source.replace(" ", "_").replace("-", "_")
            tgt = edge.target.replace(" ", "_").replace("-", "_")
            penwidth = max(1, int(edge.weight * 3))
            lines.append(f'    "{src}" -> "{tgt}" [label="{edge.relation}:{edge.weight:.2f}", penwidth={penwidth}];')

        lines.append("}")
        return "\n".join(lines)

    # ============================================================
    # 阶段34: 图谱健康检查 — 孤立节点检测
    # ============================================================

    def health_check(self) -> Dict:
        """
        图谱健康检查

        Returns:
            Dict: 健康检查结果
        """
        issues = []

        # 检测孤立节点（无任何边的节点）
        connected_nodes = set()
        for edge in self._edges:
            connected_nodes.add(edge.source)
            connected_nodes.add(edge.target)

        isolated = [name for name in self._nodes if name not in connected_nodes]
        if isolated:
            issues.append(f"孤立节点: {len(isolated)} 个")

        # 检测无效边（指向不存在的节点）
        invalid_edges = []
        for edge in self._edges:
            if edge.source not in self._nodes or edge.target not in self._nodes:
                invalid_edges.append(edge)

        if invalid_edges:
            issues.append(f"无效边: {len(invalid_edges)} 条")

        return {
            "is_healthy": len(issues) == 0,
            "issues": issues,
            "isolated_nodes": isolated,
            "invalid_edges_count": len(invalid_edges),
        }

    def repair(self) -> Dict:
        """
        修复图谱问题

        Returns:
            Dict: 修复结果
        """
        fixed = {"removed_invalid_edges": 0, "removed_isolated_nodes": 0}

        # 删除无效边
        original_edges = len(self._edges)
        self._edges = [e for e in self._edges
                       if e.source in self._nodes and e.target in self._nodes]
        fixed["removed_invalid_edges"] = original_edges - len(self._edges)

        if fixed["removed_invalid_edges"] > 0:
            self._modified = True

        # 删除孤立节点（可选，根据业务需求）
        # 这里保留孤立节点，因为可能是新添加的未关联知识

        if self._modified:
            self.save()

        return fixed

    # ============================================================
    # 阶段55: 知识图谱快照 — 版本化知识
    # ============================================================

    def create_snapshot(self, label: str = "") -> str:
        """
        创建知识图谱快照

        Args:
            label: 快照标签

        Returns:
            str: 快照文件路径
        """
        snapshot_dir = self.save_path.parent / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        from utils import now_iso
        timestamp = now_iso().replace(":", "-").replace(".", "-")
        snapshot_name = f"snapshot_{timestamp}_{label}.json" if label else f"snapshot_{timestamp}.json"
        snapshot_path = snapshot_dir / snapshot_name

        data = {
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "edges": [edge.to_dict() for edge in self._edges],
            "metadata": {
                "label": label,
                "saved_at": now_iso(),
                "node_count": self.node_count,
                "edge_count": self.edge_count,
            }
        }

        from utils import write_json
        write_json(snapshot_path, data)

        logger.info(f"快照创建: {snapshot_path} ({self.node_count} 节点, {self.edge_count} 边)")
        return str(snapshot_path)

    def list_snapshots(self) -> List[str]:
        """列出所有快照"""
        snapshot_dir = self.save_path.parent / "snapshots"
        if not snapshot_dir.exists():
            return []
        return sorted(str(p) for p in snapshot_dir.glob("snapshot_*.json"))

    def restore_snapshot(self, snapshot_path: str) -> bool:
        """
        从快照恢复

        Args:
            snapshot_path: 快照文件路径

        Returns:
            bool: 是否成功恢复
        """
        from utils import read_json

        # 路径遍历校验：快照必须在 save_path 的 snapshots 子目录下
        snapshot_file = Path(snapshot_path).resolve()
        snapshot_dir = self.save_path.parent / "snapshots"
        allowed_dir = snapshot_dir.resolve()

        if not str(snapshot_file).startswith(str(allowed_dir) + os.sep):
            logger.error(f"路径遍历校验失败: {snapshot_path} 不在允许的快照目录 {allowed_dir} 下")
            return False

        data = read_json(snapshot_file)
        if data is None:
            logger.error(f"快照文件无效: {snapshot_path}")
            return False

        self._nodes = {}
        for node_data in data.get("nodes", []):
            node = Node.from_dict(node_data)
            self._nodes[node.name] = node

        self._edges = []
        for edge_data in data.get("edges", []):
            edge = Edge.from_dict(edge_data)
            self._edges.append(edge)

        self._modified = True
        self.save()

        logger.info(f"快照恢复: {snapshot_path} ({self.node_count} 节点, {self.edge_count} 边)")
        return True

    # ============================================================
    # 便捷方法
    # ============================================================

    def clear(self):
        """清空图谱（谨慎使用）"""
        self._nodes.clear()
        self._edges.clear()
        self._modified = True
        logger.warning("知识图谱已清空")
        self.save()

    def __repr__(self) -> str:
        return f"KnowledgeGraph(nodes={self.node_count}, edges={self.edge_count})"
