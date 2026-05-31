"""
能力增强模块测试

验证目标：
1. 任务依赖图
2. 任务超时机制
3. 任务重试策略
4. 执行历史记录
5. 知识图谱快照
6. 优先级队列
7. 循环任务
8. 任务标签
"""

import pytest
import sys
import time
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models import Task, ExecutionRecord
from task_queue import TaskQueue
from knowledge_graph import KnowledgeGraph


class TestTaskDependencies:
    """任务依赖测试"""

    def test_add_dependency(self):
        """测试添加依赖"""
        task = Task(name="main_task")
        task.add_dependency("dep_1")
        task.add_dependency("dep_2")

        assert len(task.dependencies) == 2
        assert "dep_1" in task.dependencies

    def test_no_duplicate_dependency(self):
        """测试依赖去重"""
        task = Task(name="main_task")
        task.add_dependency("dep_1")
        task.add_dependency("dep_1")

        assert len(task.dependencies) == 1


class TestTaskTimeout:
    """任务超时测试"""

    def test_no_timeout_by_default(self):
        """测试默认无超时"""
        task = Task(name="task")
        assert not task.is_expired()

    def test_timeout_not_started(self):
        """测试未开始不超时"""
        task = Task(name="task", timeout=0.001)
        assert not task.is_expired()

    def test_timeout_expired(self):
        """测试超时检测"""
        task = Task(name="task", timeout=0.001)
        task.start()
        time.sleep(0.01)
        assert task.is_expired()

    def test_timeout_not_expired(self):
        """测试未超时"""
        task = Task(name="task", timeout=10.0)
        task.start()
        assert not task.is_expired()


class TestTaskRetry:
    """任务重试测试"""

    def test_can_retry(self):
        """测试可重试"""
        task = Task(name="task", max_retries=3)
        assert task.can_retry()

    def test_retry_exhausted(self):
        """测试重试耗尽"""
        task = Task(name="task", max_retries=2)
        task.record_retry()
        task.record_retry()
        assert not task.can_retry()

    def test_retry_count(self):
        """测试重试计数"""
        task = Task(name="task", max_retries=5)
        assert task.retry_count == 0
        task.record_retry()
        assert task.retry_count == 1


class TestTaskTags:
    """任务标签测试"""

    def test_add_tag(self):
        """测试添加标签"""
        task = Task(name="task")
        task.add_tag("important")
        task.add_tag("urgent")

        assert len(task.tags) == 2
        assert task.has_tag("important")

    def test_no_duplicate_tag(self):
        """测试标签去重"""
        task = Task(name="task")
        task.add_tag("tag1")
        task.add_tag("tag1")

        assert len(task.tags) == 1

    def test_has_nonexistent_tag(self):
        """测试不存在的标签"""
        task = Task(name="task")
        assert not task.has_tag("nonexistent")


class TestCyclicTask:
    """循环任务测试"""

    def test_cyclic_task_properties(self):
        """测试循环任务属性"""
        task = Task(name="heartbeat", is_cyclic=True, cyclic_interval=5.0)
        assert task.is_cyclic
        assert task.cyclic_interval == 5.0


class TestExecutionRecord:
    """执行历史记录测试"""

    def test_create_record(self):
        """测试创建记录"""
        record = ExecutionRecord(task_name="test_task")
        assert record.task_name == "test_task"

    def test_record_serialization(self):
        """测试记录序列化"""
        record = ExecutionRecord(
            task_name="test",
            state="completed",
            duration_seconds=1.5,
            result="ok"
        )
        data = record.to_dict()
        restored = ExecutionRecord.from_dict(data)

        assert restored.task_name == "test"
        assert restored.duration_seconds == 1.5


class TestPriorityQueue:
    """优先级队列测试"""

    def test_pop_highest_priority(self):
        """测试弹出最高优先级"""
        q = TaskQueue()
        q.add("low", priority=1)
        q.add("high", priority=10)
        q.add("mid", priority=5)

        task = q.pop_highest_priority()
        assert task.name == "high"

    def test_pop_by_tag(self):
        """测试按标签弹出"""
        q = TaskQueue()
        q.add("normal_task")
        # 需要直接创建带标签的任务
        tagged = Task(name="urgent_task", priority=5)
        tagged.add_tag("urgent")
        q._queue.append(tagged)

        task = q.pop_by_tag("urgent")
        assert task.name == "urgent_task"


class TestDependencyQueue:
    """依赖队列测试"""

    def test_add_with_dependencies(self):
        """测试添加带依赖的任务"""
        q = TaskQueue()
        q.add_with_dependencies("main", ["dep1", "dep2"])

        task = q.pop()
        assert task.name == "main"
        assert "dep1" in task.dependencies


class TestCyclicQueue:
    """循环任务队列测试"""

    def test_add_cyclic_task(self):
        """测试添加循环任务"""
        q = TaskQueue()
        q.add_cyclic_task("heartbeat", interval=5.0)

        task = q.pop()
        assert task.is_cyclic
        assert task.cyclic_interval == 5.0


class TestKnowledgeGraphSnapshot:
    """知识图谱快照测试"""

    def test_create_snapshot(self):
        """测试创建快照"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_node("A")
            kg.add_edge("A", "B")

            path = kg.create_snapshot("test_snapshot")
            assert Path(path).exists()

    def test_list_snapshots(self):
        """测试列出快照"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_node("A")

            kg.create_snapshot("snap1")
            kg.create_snapshot("snap2")

            snapshots = kg.list_snapshots()
            assert len(snapshots) == 2

    def test_restore_snapshot(self):
        """测试恢复快照"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_node("original")
            kg.add_edge("original", "connected")

            path = kg.create_snapshot("backup")

            # 修改图谱
            kg.add_node("new_node")
            assert kg.node_count == 3

            # 恢复快照
            kg.restore_snapshot(path)
            assert kg.node_count == 2
            assert kg.has_node("original")


class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_existing_task_creation(self):
        """测试已有Task创建方式仍然有效"""
        task = Task(name="simple_task")
        assert task.name == "simple_task"
        assert task.dependencies == []
        assert task.timeout == 0.0
        assert task.max_retries == 0
        assert task.is_cyclic == False
        assert task.tags == []

    def test_existing_queue_operations(self):
        """测试已有队列操作仍然有效"""
        q = TaskQueue()
        q.add("task1")
        q.add("task2")

        assert q.size() == 2
        task = q.pop()
        assert task.name == "task1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
