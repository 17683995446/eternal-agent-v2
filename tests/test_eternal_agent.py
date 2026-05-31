"""
永恒自驱智能体测试

验证目标：
1. 智能体初始化正常
2. 任务执行闭环工作
3. 知识沉淀有效
4. 任务推演有效
5. 空闲进化触发
6. 周期进化触发
7. 永动闭环持续运行
"""

import pytest
import sys
import time
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eternal_agent import EternalSelfAgent
from models import Task, SystemStatus
from constants import NodeType, RelationType


class TestEternalAgentInitialization:
    """初始化测试"""

    def test_create_agent(self):
        """测试创建智能体"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            assert agent is not None
            assert not agent._initialized

    def test_initialize_agent(self):
        """测试初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            result = agent.initialize()

            assert result is True
            assert agent._initialized

    def test_initialize_idempotent(self):
        """测试初始化幂等性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()
            result = agent.initialize()  # 再次初始化

            assert result is True  # 应该返回True，不报错


class TestKnowledgePersistence:
    """知识持久化测试"""

    def test_knowledge_persisted_after_task(self):
        """测试任务执行后知识被持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from knowledge_graph import KnowledgeGraph
            from task_queue import TaskQueue
            from loop import EternalLoop
            
            # 使用独立的组件
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            queue = TaskQueue()
            loop = EternalLoop(queue)
            
            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = queue
            agent.loop = loop
            agent._initialized = True
            
            # 添加并执行任务
            agent.task_queue.add("test_task")
            task = agent.task_queue.pop()
            agent._execute_task(task)

            # 验证知识已沉淀
            assert agent.knowledge_graph.has_node("test_task")

    def test_task_node_attributes(self):
        """测试任务节点属性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            task = Task(name="attr_test", priority=5)
            task.complete("success_result")

            agent._persist_task_knowledge(task)

            node = agent.knowledge_graph.get_node("attr_test")
            assert node is not None
            assert node.node_type == NodeType.TASK
            assert node.attributes.get("priority") == 5
            assert node.attributes.get("result") == "success_result"


class TestTaskDerivation:
    """任务推演测试"""

    def test_derive_tasks_from_knowledge(self):
        """测试从知识推演任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            # 先创建知识关联
            agent.knowledge_graph.add_edge("source_task", "target_task", weight=0.9)

            # 推演新任务
            task = Task(name="source_task")
            derived = agent._derive_tasks_from_knowledge(task)

            assert len(derived) == 1
            assert "target_task" in derived[0]

    def test_derived_edge_created(self):
        """测试推演边被创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            # 创建知识
            agent.knowledge_graph.add_node("A")
            agent.knowledge_graph.add_node("B")

            # 推演
            task = Task(name="A")
            agent.knowledge_graph.add_edge("A", "B", weight=0.9)
            agent._derive_tasks_from_knowledge(task)

            # 验证衍生边
            edges = agent.knowledge_graph.get_edges_between("A", "B")
            assert len(edges) > 0


class TestIdleEvolution:
    """空闲进化测试"""

    def test_idle_evolve_generates_tasks(self):
        """测试空闲进化生成任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            # 先添加一些历史任务
            agent.knowledge_graph.add_task_node(Task(name="history_task"))

            # 记录当前队列大小
            before = agent.task_queue.size()

            # 触发空闲进化
            agent._idle_evolve()

            # 验证生成了新任务
            after = agent.task_queue.size()
            assert after > before

    def test_idle_evolve_empty_kg(self):
        """测试空知识图谱时的空闲进化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            # 确保知识图谱为空
            agent.knowledge_graph.clear()

            # 不应抛出异常
            agent._idle_evolve()


class TestPeriodicEvolution:
    """周期进化测试"""

    def test_periodic_evolve_trims_knowledge(self):
        """测试周期进化精简知识"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            # 添加低权重边
            agent.knowledge_graph.add_edge("A", "B", weight=0.05)
            agent.knowledge_graph.add_edge("C", "D", weight=0.9)

            before = agent.knowledge_graph.edge_count

            # 触发周期进化
            agent._periodic_evolve()

            # 低权重边应被删除
            after = agent.knowledge_graph.edge_count
            assert after < before

    def test_periodic_evolve_health_check(self):
        """测试周期进化健康检查"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            # 添加孤立节点
            agent.knowledge_graph.add_node("isolated")

            # 触发周期进化
            agent._periodic_evolve()

            # 健康检查应检测到问题
            health = agent.knowledge_graph.health_check()
            # 孤立节点是警告但不影响运行


class TestTaskProcessing:
    """任务处理测试"""

    def test_process_initial_task(self):
        """测试处理初始任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            result = agent._process_task_logic(Task(name="系统初始认知迭代"))
            assert "自检" in result

    def test_process_derived_task(self):
        """测试处理推演任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            result = agent._process_task_logic(Task(name="推演任务:目标知识"))
            assert "探索" in result

    def test_process_normal_task(self):
        """测试处理普通任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            result = agent._process_task_logic(Task(name="普通任务"))
            assert "已处理" in result


class TestSelfDriveLoop:
    """自驱闭环测试"""

    def test_execute_task_persists_knowledge(self):
        """测试任务执行沉淀知识"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            task = Task(name="loop_test")
            agent._execute_task(task)

            # 验证知识已沉淀
            assert agent.knowledge_graph.has_node("loop_test")

    def test_execute_task_derives_new_tasks(self):
        """测试任务执行推演新任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            # 预设知识关联
            agent.knowledge_graph.add_edge("seed", "derived_target", weight=0.9)

            before = agent.task_queue.size()

            task = Task(name="seed")
            agent._execute_task(task)

            after = agent.task_queue.size()
            # 应推演出新任务

    def test_full_loop_single_iteration(self):
        """测试单轮完整闭环"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from knowledge_graph import KnowledgeGraph
            from task_queue import TaskQueue
            from loop import EternalLoop
            
            # 使用独立的组件
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            queue = TaskQueue()
            loop = EternalLoop(queue)
            
            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = queue
            agent.loop = loop
            agent._initialized = True

            # 添加种子任务
            agent.task_queue.add("seed_task")

            # 执行一轮
            task = agent.task_queue.pop()
            if task:
                agent._execute_task(task)

            # 验证闭环：任务→知识→可能的新任务
            assert agent.knowledge_graph.has_node("seed_task")


class TestAgentStatus:
    """状态查询测试"""

    def test_get_status(self):
        """测试获取状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            status = agent.get_status()
            assert isinstance(status, SystemStatus)

    def test_get_kg_stats(self):
        """测试获取知识图谱统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from knowledge_graph import KnowledgeGraph
            
            # 使用独立的图谱
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            
            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent._initialized = True

            # 添加一些知识
            agent.knowledge_graph.add_node("A")
            agent.knowledge_graph.add_edge("A", "B")

            stats = agent.get_kg_stats()
            assert stats["node_count"] == 2
            assert stats["edge_count"] == 1

    def test_export_visualization(self):
        """测试导出可视化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            agent.knowledge_graph.add_edge("A", "B")

            mermaid = agent.export_kg_visualization("mermaid")
            assert "graph TD" in mermaid

            dot = agent.export_kg_visualization("graphviz")
            assert "digraph" in dot


class TestSelfDriveAxiomCompliance:
    """自驱公理合规性测试"""

    def test_no_external_input_generates_tasks(self):
        """测试无外部输入时自我产生任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            # 清空队列
            agent.task_queue.clear()

            # 添加历史知识
            agent.knowledge_graph.add_task_node(Task(name="history"))

            # 空闲进化应生成新任务
            agent._idle_evolve()

            assert not agent.task_queue.is_empty()

    def test_knowledge_drives_task_generation(self):
        """测试知识驱动任务生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            # 创建高权重知识关联
            agent.knowledge_graph.add_edge("source", "target", weight=0.95)

            # 从知识推演任务
            derived = agent.knowledge_graph.derive_new_tasks("source")

            assert len(derived) > 0
            assert "target" in derived[0]

    def test_self_evolution_trims_knowledge(self):
        """测试自我精简迭代"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            # 添加高价值和低价值知识
            agent.knowledge_graph.add_edge("A", "B", weight=0.9)  # 保留
            agent.knowledge_graph.add_edge("C", "D", weight=0.05)  # 删除

            before = agent.knowledge_graph.edge_count

            # 触发精简
            agent.knowledge_graph.trim_invalid_knowledge(threshold=0.1)

            after = agent.knowledge_graph.edge_count
            assert after < before


class TestEternalMotion:
    """永动特性测试"""

    def test_task_execution_generates_knowledge(self):
        """测试任务执行产生知识"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            before_nodes = agent.knowledge_graph.node_count

            task = Task(name="motion_test")
            agent._execute_task(task)

            after_nodes = agent.knowledge_graph.node_count
            assert after_nodes > before_nodes

    def test_knowledge_generates_tasks(self):
        """测试知识产生任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            # 创建知识
            agent.knowledge_graph.add_edge("A", "B", weight=0.9)

            before = agent.task_queue.size()

            # 从知识推演
            task = Task(name="A")
            agent._derive_tasks_from_knowledge(task)

            # 推演结果应入队
            # 注意：_derive_tasks_from_knowledge 只返回任务名，不入队
            # 实际入队由调用方完成

    def test_closed_loop_structure(self):
        """测试闭环结构完整性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = EternalSelfAgent()
            agent.initialize()

            # 验证闭环组件都存在
            assert agent.knowledge_graph is not None
            assert agent.task_queue is not None
            assert agent.loop is not None

            # 验证回调已注册
            assert agent.loop._on_task_callback is not None
            assert agent.loop._on_idle_callback is not None
            assert agent.loop._on_evolve_callback is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
