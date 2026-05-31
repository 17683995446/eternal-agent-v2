"""
存续保活层集成测试

验证目标：
1. 主循环可启动、可停止
2. 心跳检测正常触发
3. 全局异常不击穿主循环
4. 自愈重启恢复正常
5. 资源熔断保护有效
6. 优雅停机安全退出
7. 运行计数器准确
8. 回调注入正确调用
"""

import pytest
import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loop import EternalLoop
from task_queue import TaskQueue
from constants import (
    LOOP_DELAY,
    SELF_REPAIR_DELAY,
    MAX_CONSECUTIVE_ERRORS,
    SystemState,
)
from models import SystemStatus


class TestEternalLoopBasic:
    """主循环基础测试"""

    def test_loop_starts_and_stops(self):
        """测试主循环启动和停止"""
        q = TaskQueue()
        loop = EternalLoop(q)

        # 在子线程中运行循环
        def run_loop():
            loop.run()

        t = threading.Thread(target=run_loop, daemon=True)
        t.start()

        # 等待循环启动
        time.sleep(0.5)

        # 验证循环在运行
        assert loop.is_alive()

        # 停止循环
        loop.stop()
        t.join(timeout=3)

        # 验证已停止
        assert not loop.is_alive()

    def test_loop_status_initial(self):
        """测试初始状态"""
        q = TaskQueue()
        loop = EternalLoop(q)

        status = loop.get_status()
        assert status.run_counter == 0
        assert status.total_tasks_completed == 0
        assert status.total_tasks_failed == 0


class TestTaskExecution:
    """任务执行测试"""

    def test_task_callback_called(self):
        """测试任务回调被调用"""
        q = TaskQueue()
        loop = EternalLoop(q)

        executed_tasks = []

        def on_task(task):
            executed_tasks.append(task.name)
            return "ok"

        loop.on_task(on_task)

        q.add("test_task_1")
        q.add("test_task_2")

        # 在子线程中运行循环
        def run_loop():
            loop.run()

        t = threading.Thread(target=run_loop, daemon=True)
        t.start()
        time.sleep(1)

        loop.stop()
        t.join(timeout=3)

        # 验证回调被调用
        assert "test_task_1" in executed_tasks
        assert "test_task_2" in executed_tasks

    def test_task_failure_counted(self):
        """测试任务失败被计数"""
        q = TaskQueue()
        loop = EternalLoop(q)

        def on_task(task):
            raise RuntimeError("模拟任务失败")

        loop.on_task(on_task)
        q.add("fail_task")

        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(1)

        loop.stop()
        t.join(timeout=3)

        assert loop.get_status().total_tasks_failed == 1


class TestSelfRepair:
    """自愈重启测试"""

    def test_self_repair_recovers(self):
        """测试自愈后系统继续运行"""
        q = TaskQueue()
        loop = EternalLoop(q)

        repair_count = 0

        def on_task(task):
            nonlocal repair_count
            if "error" in task.name:
                raise RuntimeError("模拟异常")

        loop.on_task(on_task)

        # 添加正常任务和异常任务
        q.add("error_task")
        q.add("normal_task")

        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(2)

        loop.stop()
        t.join(timeout=3)

        # 系统应该继续运行（自愈成功）
        status = loop.get_status()
        assert status.total_tasks_completed >= 1  # normal_task 应该完成

    def test_consecutive_errors_reset(self):
        """测试连续错误计数重置"""
        q = TaskQueue()
        loop = EternalLoop(q)

        call_count = 0

        def on_task(task):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RuntimeError("前两次失败")

        loop.on_task(on_task)

        for i in range(5):
            q.add(f"task_{i}")

        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(3)

        loop.stop()
        t.join(timeout=3)

        status = loop.get_status()
        # 自愈后应该重置错误计数并继续执行
        assert status.total_tasks_completed >= 2


class TestIdleMode:
    """空闲进化测试"""

    def test_idle_callback_called(self):
        """测试空闲回调被调用"""
        q = TaskQueue()
        loop = EternalLoop(q)

        idle_called = False

        def on_idle():
            nonlocal idle_called
            idle_called = True

        loop.on_idle(on_idle)

        # 不添加任务，队列始终为空
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(1)

        loop.stop()
        t.join(timeout=3)

        assert idle_called


class TestGracefulShutdown:
    """优雅停机测试"""

    def test_shutdown_callback_called(self):
        """测试停机回调被调用"""
        q = TaskQueue()
        loop = EternalLoop(q)

        shutdown_called = False

        def on_shutdown():
            nonlocal shutdown_called
            shutdown_called = True

        loop.on_shutdown(on_shutdown)

        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.5)

        loop.stop()
        t.join(timeout=3)

        assert shutdown_called

    def test_shutdown_status(self):
        """测试停机状态"""
        q = TaskQueue()
        loop = EternalLoop(q)

        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.5)

        loop.stop()
        t.join(timeout=3)

        # 停机后状态应为 SHUTTING_DOWN
        assert loop.get_status().state == SystemState.SHUTTING_DOWN


class TestRunCounter:
    """运行计数器测试"""

    def test_counter_increments(self):
        """测试计数器递增"""
        q = TaskQueue()
        loop = EternalLoop(q)

        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(1)

        loop.stop()
        t.join(timeout=3)

        # 1秒内应该有多次循环
        assert loop.get_status().run_counter > 1


class TestResourceThrottle:
    """资源熔断测试"""

    def test_resource_throttle_with_low_limit(self):
        """测试低资源阈值触发降级"""
        q = TaskQueue()
        loop = EternalLoop(q)

        # 设置极低的内存限制
        from monitor import ResourceMonitor
        loop_monitor = ResourceMonitor(memory_limit_mb=0.0001)
        # 替换全局monitor（仅测试用）
        import loop as loop_module
        original_monitor = loop_module.monitor
        loop_module.monitor = loop_monitor

        try:
            t = threading.Thread(target=loop.run, daemon=True)
            t.start()
            time.sleep(1)

            loop.stop()
            t.join(timeout=3)

            # 系统应该继续运行（降级模式，不退出）
            assert loop.get_status().run_counter > 0
        finally:
            loop_module.monitor = original_monitor


class TestCallbackChaining:
    """回调链测试"""

    def test_all_callbacks_registered(self):
        """测试所有回调可注册"""
        q = TaskQueue()
        loop = (EternalLoop(q)
                .on_task(lambda t: "done")
                .on_idle(lambda: None)
                .on_evolve(lambda: None)
                .on_shutdown(lambda: None))

        assert loop._on_task_callback is not None
        assert loop._on_idle_callback is not None
        assert loop._on_evolve_callback is not None
        assert loop._on_shutdown_callback is not None


class TestSurvivalAxiom:
    """存续公理合规性测试"""

    def test_loop_never_exits_on_exception(self):
        """测试异常不击穿主循环"""
        q = TaskQueue()
        loop = EternalLoop(q)

        def always_fail(task):
            raise RuntimeError("永远失败")

        loop.on_task(always_fail)
        q.add("task_1")
        q.add("task_2")
        q.add("task_3")

        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(2)

        # 即使所有任务都失败，循环仍在运行
        assert loop.is_alive()

        loop.stop()
        t.join(timeout=3)

        # 验证系统存活
        status = loop.get_status()
        assert status.run_counter > 0

    def test_empty_queue_never_exits(self):
        """测试空队列不退出循环"""
        q = TaskQueue()  # 空队列
        loop = EternalLoop(q)

        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(1)

        # 空队列时循环仍在运行（空闲进化模式）
        assert loop.is_alive()

        loop.stop()
        t.join(timeout=3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
