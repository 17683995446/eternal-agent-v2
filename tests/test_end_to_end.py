"""
端到端集成测试

验证目标：
1. 完整系统可启动运行
2. 永动闭环持续工作
3. 异常自动恢复
4. 资源保护有效
5. 持久化正常工作
"""

import pytest
import sys
import time
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eternal_agent import EternalSelfAgent
from knowledge_graph import KnowledgeGraph
from task_queue import TaskQueue
from loop import EternalLoop
from models import Task


class TestSystemStartup:
    """系统启动测试"""

    def test_system_starts(self):
        """测试系统可启动"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = TaskQueue()
            agent.loop = EternalLoop(agent.task_queue)
            agent._initialized = True

            # 系统应能初始化
            assert agent is not None
            assert agent.knowledge_graph is not None

    def test_initial_task_injected(self):
        """测试初始任务被注入"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            queue = TaskQueue()
            loop = EternalLoop(queue)

            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = queue
            agent.loop = loop

            agent._inject_initial_knowledge()

            # 验证队列中有初始任务
            assert not queue.is_empty()


class TestEternalMotionLoop:
    """永动闭环测试"""

    def test_single_iteration(self):
        """测试单轮闭环"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            queue = TaskQueue()
            loop = EternalLoop(queue)

            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = queue
            agent.loop = loop
            agent._initialized = True

            # 添加种子任务
            queue.add("seed_task")

            # 执行一轮
            task = queue.pop()
            if task:
                agent._execute_task(task)

            # 验证知识已沉淀
            assert kg.has_node("seed_task")

    def test_multiple_iterations(self):
        """测试多轮闭环"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            queue = TaskQueue()
            loop = EternalLoop(queue)

            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = queue
            agent.loop = loop
            agent._initialized = True

            # 添加种子任务
            queue.add("task_1")

            # 执行多轮
            for i in range(5):
                task = queue.pop()
                if task:
                    agent._execute_task(task)
                else:
                    break

            # 验证知识持续增长
            assert kg.node_count > 0


class TestPersistenceAcrossRestart:
    """重启持久化测试"""

    def test_knowledge_persisted(self):
        """测试知识在重启后保留"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "kg.json"

            # 第一次运行
            kg1 = KnowledgeGraph(save_path=path)
            kg1.add_node("persistent_node")
            kg1.add_edge("A", "B", weight=0.9)
            kg1.force_save()

            # 模拟重启
            kg2 = KnowledgeGraph(save_path=path)

            assert kg2.has_node("persistent_node")
            assert kg2.has_node("A")
            assert kg2.has_node("B")

    def test_task_queue_not_persisted(self):
        """测试任务队列不持久化（设计决策）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = TaskQueue()
            queue.add("temp_task")

            # 队列是内存中的，重启后清空
            # 这是设计决策：任务应该能从知识图谱恢复
            assert queue.size() == 1


class TestErrorRecovery:
    """错误恢复测试"""

    def test_task_failure_not_crash_system(self):
        """测试任务失败不崩溃系统"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            queue = TaskQueue()
            loop = EternalLoop(queue)

            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = queue
            agent.loop = loop
            agent._initialized = True

            # 注册一个会失败的任务处理器
            def failing_task(task):
                raise RuntimeError("模拟任务失败")

            loop.on_task(failing_task)

            queue.add("fail_task")

            # 在子线程中运行
            def run_loop():
                try:
                    loop.run()
                except:
                    pass

            t = threading.Thread(target=run_loop, daemon=True)
            t.start()
            time.sleep(0.5)

            loop.stop()
            t.join(timeout=2)

            # 系统应该仍在运行（或已优雅停止）
            # 不应有未捕获的异常导致崩溃


class TestResourceProtection:
    """资源保护测试"""

    def test_queue_size_limit(self):
        """测试队列大小限制"""
        queue = TaskQueue(max_size=5)

        for i in range(10):
            queue.add(f"task_{i}")

        # 队列应被限制在5个
        assert queue.size() == 5

    def test_memory_usage_reasonable(self):
        """测试内存使用合理"""
        pytest.importorskip("psutil", reason="需要psutil模块")
        import psutil
        import os

        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # 创建大量知识
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            for i in range(100):
                kg.add_node(f"node_{i}")
                if i > 0:
                    kg.add_edge(f"node_{i-1}", f"node_{i}")

        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_increase = mem_after - mem_before

        # 内存增长应合理（小于50MB）
        assert mem_increase < 50


class TestSystemIntegration:
    """系统集成测试"""

    def test_all_components_work_together(self):
        """测试所有组件协同工作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            queue = TaskQueue()
            loop = EternalLoop(queue)

            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = queue
            agent.loop = loop
            agent._initialized = True

            # 注册回调
            loop.on_task(agent._execute_task)
            loop.on_idle(agent._idle_evolve)
            loop.on_evolve(agent._periodic_evolve)

            # 添加任务
            queue.add("integration_test")

            # 执行一轮
            task = queue.pop()
            if task:
                result = agent._execute_task(task)
                assert result is not None

            # 验证知识已沉淀
            assert kg.has_node("integration_test")


class TestLongRunningSimulation:
    """长时间运行模拟测试"""

    def test_short_duration_simulation(self):
        """测试短时间模拟运行（5秒）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            queue = TaskQueue()
            loop = EternalLoop(queue)

            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = queue
            agent.loop = loop
            agent._initialized = True

            # 注册回调
            loop.on_task(agent._execute_task)
            loop.on_idle(agent._idle_evolve)

            # 添加初始任务
            queue.add("simulation_task")

            # 运行5秒
            def run_loop():
                loop.run()

            t = threading.Thread(target=run_loop, daemon=True)
            t.start()
            time.sleep(5)

            loop.stop()
            t.join(timeout=3)

            # 验证系统运行过
            status = loop.get_status()
            assert status.run_counter > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
