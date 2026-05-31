"""
任务队列模块测试

验证目标：
1. FIFO先进先出正常
2. 队列上限控制有效
3. 批量添加去重有效
4. 统计信息准确
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from task_queue import TaskQueue
from constants import TASK_QUEUE_MAX


class TestTaskQueueBasic:
    """队列基础操作测试"""

    def test_create_empty_queue(self):
        """测试创建空队列"""
        q = TaskQueue()
        assert q.is_empty()
        assert q.size() == 0

    def test_add_and_pop(self):
        """测试添加和弹出"""
        q = TaskQueue()
        q.add("task_1")
        q.add("task_2")

        assert q.size() == 2

        task1 = q.pop()
        assert task1.name == "task_1"

        task2 = q.pop()
        assert task2.name == "task_2"

        assert q.is_empty()

    def test_pop_empty_queue(self):
        """测试弹出空队列"""
        q = TaskQueue()
        assert q.pop() is None

    def test_get_without_remove(self):
        """测试查看队首不出队"""
        q = TaskQueue()
        q.add("task_1")

        task = q.get()
        assert task.name == "task_1"
        assert q.size() == 1  # 未出队

    def test_contains(self):
        """测试任务是否存在"""
        q = TaskQueue()
        q.add("task_1")

        assert q.contains("task_1")
        assert not q.contains("task_2")

    def test_get_all_names(self):
        """测试获取所有任务名"""
        q = TaskQueue()
        q.add("task_1")
        q.add("task_2")
        q.add("task_3")

        names = q.get_all_names()
        assert names == ["task_1", "task_2", "task_3"]

    def test_clear(self):
        """测试清空队列"""
        q = TaskQueue()
        q.add("task_1")
        q.add("task_2")

        count = q.clear()
        assert count == 2
        assert q.is_empty()

    def test_bool_and_len(self):
        """测试bool和len"""
        q = TaskQueue()
        assert not q
        assert len(q) == 0

        q.add("task_1")
        assert q
        assert len(q) == 1


class TestTaskQueueLimit:
    """队列上限控制测试"""

    def test_max_size_limit(self):
        """测试队列上限"""
        q = TaskQueue(max_size=5)

        for i in range(7):
            q.add(f"task_{i}")

        # 超出上限的任务应被丢弃
        assert q.size() == 5

    def test_discards_oldest(self):
        """测试丢弃最旧任务"""
        q = TaskQueue(max_size=3)
        q.add("task_1")
        q.add("task_2")
        q.add("task_3")
        q.add("task_4")  # 应丢弃 task_1

        names = q.get_all_names()
        assert "task_1" not in names
        assert "task_4" in names

    def test_default_max_size(self):
        """测试默认上限值"""
        q = TaskQueue()
        assert q._max_size == TASK_QUEUE_MAX

    def test_is_full(self):
        """测试队列已满判断"""
        q = TaskQueue(max_size=2)
        q.add("task_1")
        assert not q.is_full()

        q.add("task_2")
        assert q.is_full()


class TestTaskQueueBatch:
    """批量操作测试"""

    def test_batch_add(self):
        """测试批量添加"""
        q = TaskQueue()
        count = q.batch_add(["task_1", "task_2", "task_3"])
        assert count == 3
        assert q.size() == 3

    def test_batch_dedup(self):
        """测试批量添加去重"""
        q = TaskQueue()
        count = q.batch_add(["task_1", "task_1", "task_2", "task_2"])
        assert count == 2
        assert q.size() == 2

    def test_batch_no_duplicate_with_existing(self):
        """测试批量添加不与已有任务重复"""
        q = TaskQueue()
        q.add("task_1")
        count = q.batch_add(["task_1", "task_2", "task_3"])
        assert count == 2  # task_1 已存在，只添加 2 和 3


class TestTaskQueueStats:
    """统计信息测试"""

    def test_stats_structure(self):
        """测试统计信息结构"""
        q = TaskQueue(max_size=10)
        q.add("task_1")

        stats = q.stats()
        assert "size" in stats
        assert "max_size" in stats
        assert "is_empty" in stats
        assert "is_full" in stats
        assert "discarded_count" in stats

    def test_discarded_count(self):
        """测试丢弃计数"""
        q = TaskQueue(max_size=2)
        q.add("task_1")
        q.add("task_2")
        q.add("task_3")  # 丢弃 task_1
        q.add("task_4")  # 丢弃 task_2

        stats = q.stats()
        assert stats["discarded_count"] == 2

    def test_repr(self):
        """测试字符串表示"""
        q = TaskQueue(max_size=100)
        q.add("task_1")
        r = repr(q)
        assert "TaskQueue" in r
        assert "1/100" in r


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
