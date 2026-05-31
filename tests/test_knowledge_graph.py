"""
知识图谱模块测试

验证目标：
1. 节点CRUD正常
2. 边CRUD正常（含权重更新）
3. 持久化加载/保存有效
4. 知识推演正确
5. 低价值淘汰有效
6. 可视化导出可用
7. 健康检查准确
"""

import pytest
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from knowledge_graph import KnowledgeGraph
from models import Node, Edge, Task
from constants import NodeType, RelationType, TASK_DERIVE_WEIGHT_THRESHOLD, KNOWLEDGE_TRIM_THRESHOLD


class TestKnowledgeGraphBasic:
    """基础功能测试"""

    def test_create_empty_graph(self):
        """测试创建空图谱"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            assert kg.is_empty()
            assert kg.node_count == 0
            assert kg.edge_count == 0

    def test_graph_properties(self):
        """测试图谱属性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_node("A")
            kg.add_node("B")
            kg.add_edge("A", "B")

            assert kg.node_count == 2
            assert kg.edge_count == 1
            assert not kg.is_empty()


class TestNodeOperations:
    """节点操作测试"""

    def test_add_node(self):
        """测试添加节点"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            node = kg.add_node("test_node", node_type=NodeType.TASK)

            assert node.name == "test_node"
            assert node.node_type == NodeType.TASK
            assert kg.has_node("test_node")

    def test_add_node_idempotent(self):
        """测试添加节点幂等性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            node1 = kg.add_node("same_node")
            node2 = kg.add_node("same_node")

            assert node1 is node2
            assert kg.node_count == 1

    def test_get_node(self):
        """测试获取节点"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_node("A")

            node = kg.get_node("A")
            assert node is not None
            assert node.name == "A"

            not_found = kg.get_node("B")
            assert not_found is None

    def test_get_nodes_by_type(self):
        """测试按类型获取节点"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_node("task1", node_type=NodeType.TASK)
            kg.add_node("task2", node_type=NodeType.TASK)
            kg.add_node("entity1", node_type=NodeType.ENTITY)

            tasks = kg.get_nodes_by_type(NodeType.TASK)
            assert len(tasks) == 2

    def test_remove_node_cascade(self):
        """测试删除节点级联删除边"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("A", "B")
            kg.add_edge("B", "C")
            kg.add_edge("A", "C")

            assert kg.edge_count == 3

            kg.remove_node("B")

            assert not kg.has_node("B")
            assert kg.edge_count == 1  # 只剩 A->C


class TestEdgeOperations:
    """边操作测试"""

    def test_add_edge_auto_create_nodes(self):
        """测试添加边自动创建节点"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("X", "Y")

            assert kg.has_node("X")
            assert kg.has_node("Y")
            assert kg.edge_count == 1

    def test_add_edge_update_existing(self):
        """测试更新已有边权重"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            edge1 = kg.add_edge("A", "B", weight=0.5)
            edge2 = kg.add_edge("A", "B", weight=0.8)

            assert edge1 is edge2
            assert edge2.weight == 0.8
            assert kg.edge_count == 1

    def test_get_edges_from(self):
        """测试获取从节点出发的边"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("A", "B")
            kg.add_edge("A", "C")
            kg.add_edge("B", "C")

            edges = kg.get_edges_from("A")
            assert len(edges) == 2

    def test_get_edges_to(self):
        """测试获取指向节点的边"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("A", "C")
            kg.add_edge("B", "C")

            edges = kg.get_edges_to("C")
            assert len(edges) == 2

    def test_update_edge_weight(self):
        """测试更新边权重"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("A", "B", weight=0.5)

            kg.update_edge_weight("A", "B", 0.3)
            edge = kg.get_edges_between("A", "B")[0]
            assert edge.weight == 0.8

    def test_reinforce_and_weaken(self):
        """测试强化和弱化边"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("A", "B", weight=0.5)

            kg.reinforce_edge("A", "B", 0.1)
            edge = kg.get_edges_between("A", "B")[0]
            assert abs(edge.weight - 0.6) < 0.001

            kg.weaken_edge("A", "B", 0.2)
            assert abs(edge.weight - 0.4) < 0.001


class TestPersistence:
    """持久化测试"""

    def test_save_and_load(self):
        """测试保存和加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "kg.json"

            # 创建并保存
            kg1 = KnowledgeGraph(save_path=path)
            kg1.add_node("A")
            kg1.add_node("B")
            kg1.add_edge("A", "B", weight=0.8)
            kg1.force_save()

            # 重新加载
            kg2 = KnowledgeGraph(save_path=path)
            assert kg2.has_node("A")
            assert kg2.has_node("B")
            assert kg2.edge_count == 1

            edge = kg2.get_edges_between("A", "B")[0]
            assert edge.weight == 0.8

    def test_auto_save(self):
        """测试自动保存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "kg.json"
            kg = KnowledgeGraph(save_path=path)

            kg.add_node("auto_save_test")

            # 检查文件是否创建
            assert path.exists()


class TestTaskDerivation:
    """知识推演测试"""

    def test_derive_new_tasks(self):
        """测试推演新任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("task_A", "task_B", weight=0.9)
            kg.add_edge("task_A", "task_C", weight=0.1)  # 低于阈值0.2

            tasks = kg.derive_new_tasks("task_A")

            # 只有高权重边(0.9)会推演新任务
            assert len(tasks) == 1
            assert "task_B" in tasks[0]

    def test_derive_with_threshold(self):
        """测试自定义阈值推演"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("A", "B", weight=0.5)
            kg.add_edge("A", "C", weight=0.6)

            tasks = kg.derive_new_tasks("A", threshold=0.55)
            assert len(tasks) == 1
            assert "C" in tasks[0]

    def test_derive_from_nonexistent(self):
        """测试从不存在节点推演"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            tasks = kg.derive_new_tasks("nonexistent")
            assert tasks == []


class TestKnowledgeTrimming:
    """知识淘汰测试"""

    def test_trim_low_weight_edges(self):
        """测试淘汰低权重边"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("A", "B", weight=0.9)
            kg.add_edge("A", "C", weight=0.05)
            kg.add_edge("A", "D", weight=0.08)

            removed = kg.trim_invalid_knowledge(threshold=0.1)

            assert removed == 2
            assert kg.edge_count == 1

    def test_trim_default_threshold(self):
        """测试默认阈值淘汰"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("A", "B", weight=KNOWLEDGE_TRIM_THRESHOLD + 0.01)
            kg.add_edge("A", "C", weight=KNOWLEDGE_TRIM_THRESHOLD - 0.01)

            removed = kg.trim_invalid_knowledge()
            assert removed == 1


class TestVisualization:
    """可视化导出测试"""

    def test_export_mermaid(self):
        """测试Mermaid导出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("A", "B")

            mermaid = kg.export_mermaid()
            assert "graph TD" in mermaid
            assert "A" in mermaid
            assert "B" in mermaid
            assert "-->" in mermaid

    def test_export_graphviz(self):
        """测试Graphviz导出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("A", "B", relation="测试", weight=0.8)

            dot = kg.export_graphviz()
            assert "digraph" in dot
            assert "A" in dot
            assert "B" in dot
            assert "0.80" in dot


class TestHealthCheck:
    """健康检查测试"""

    def test_health_check_healthy(self):
        """测试健康图谱"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("A", "B")

            health = kg.health_check()
            assert health["is_healthy"]
            assert len(health["issues"]) == 0

    def test_health_check_isolated(self):
        """测试孤立节点检测"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_node("isolated")
            kg.add_edge("A", "B")

            health = kg.health_check()
            assert not health["is_healthy"]
            assert len(health["isolated_nodes"]) == 1
            assert "isolated" in health["isolated_nodes"]

    def test_repair_invalid_edges(self):
        """测试修复无效边"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_node("A")
            kg.add_node("B")

            # 手动添加无效边（指向不存在的节点）
            from models import Edge
            kg._edges.append(Edge(source="A", target="nonexistent"))
            kg._modified = True

            assert kg.edge_count == 1

            fixed = kg.repair()
            assert fixed["removed_invalid_edges"] == 1
            assert kg.edge_count == 0


class TestStats:
    """统计信息测试"""

    def test_stats_structure(self):
        """测试统计信息结构"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_edge("A", "B", weight=0.8)
            kg.add_edge("B", "C", weight=0.6)

            stats = kg.stats()
            assert stats["node_count"] == 3
            assert stats["edge_count"] == 2
            assert stats["average_weight"] == 0.7
            assert "node_types" in stats
            assert "density" in stats

    def test_empty_stats(self):
        """测试空图谱统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            stats = kg.stats()
            assert stats["average_weight"] == 0.0
            assert stats["density"] == 0.0


class TestTaskNode:
    """任务节点测试"""

    def test_add_task_node(self):
        """测试从任务创建节点"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")

            task = Task(name="test_task", priority=5)
            task.complete("success")

            node = kg.add_task_node(task)

            assert node.name == "test_task"
            assert node.node_type == NodeType.TASK
            assert node.attributes.get("priority") == 5
            assert node.attributes.get("result") == "success"


class TestDerivedEdge:
    """衍生边测试"""

    def test_add_derived_edge(self):
        """测试添加衍生边"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            edge = kg.add_derived_edge("task_1", "task_2", weight=0.85)

            assert edge.source == "task_1"
            assert edge.target == "task_2"
            assert edge.relation == RelationType.DERIVED
            assert edge.weight == 0.85


class TestMemoryAxiomCompliance:
    """记忆公理合规性测试"""

    def test_all_operations_persisted(self):
        """测试所有操作都持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "kg.json"

            # 创建图谱并操作
            kg = KnowledgeGraph(save_path=path)
            kg.add_node("A")
            kg.add_edge("A", "B")

            # 重新加载验证
            kg2 = KnowledgeGraph(save_path=path)
            assert kg2.has_node("A")
            assert kg2.has_node("B")
            assert kg2.edge_count == 1

    def test_restart_not_lost(self):
        """测试重启不丢失经验"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "kg.json"

            # 第一次运行
            kg1 = KnowledgeGraph(save_path=path)
            kg1.add_node("经验节点")
            kg1.add_edge("经验节点", "关联节点", weight=0.95)

            # 模拟重启（重新加载）
            kg2 = KnowledgeGraph(save_path=path)

            assert kg2.has_node("经验节点")
            edge = kg2.get_edges_between("经验节点", "关联节点")[0]
            assert edge.weight == 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
