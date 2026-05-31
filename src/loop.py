"""
存续保活层 — 主循环模块

公理溯源：存续公理 — 系统运行闭环永不终止，局部异常永远不能击穿整体系统

设计意图：
- 无限主循环（ETERNAL_LOOP），永不退出
- 全局异常捕获，任何错误不击穿系统
- 自愈重启机制，异常后自动恢复
- 心跳检测，周期性存活信号
- 资源熔断保护，超限自动降级
- 优雅停机，收到信号后安全保存状态
- 运行计数器，精确记录运行次数

大事做于细，难事成于易：
- 每个能力独立为一个方法
- 主循环只做编排，不包含业务逻辑
- 通过回调函数注入业务行为（解耦）
"""

import signal
import time
from typing import Callable, Optional

from constants import (
    LOOP_DELAY,
    SELF_REPAIR_DELAY,
    HEARTBEAT_INTERVAL,
    MAX_CONSECUTIVE_ERRORS,
    EVOLVE_STEP,
    SystemState,
)
from models import SystemStatus, Task
from task_queue import TaskQueue
from monitor import monitor
from exceptions import (
    EternalAgentError,
    MaxConsecutiveErrorsError,
    SystemOverloadError,
)
from utils import now_iso, now_timestamp, format_duration
from logger import get_logger

logger = get_logger("Loop")


class EternalLoop:
    """
    永恒主循环
    
    公理溯源：存续公理 — 系统运行闭环永不终止
    
    设计原则：
    - 主循环只做编排，业务逻辑通过回调注入
    - 每个能力独立方法，职责单一
    - 全局异常捕获 + 自愈重启 = 永不终止
    """

    def __init__(self, task_queue: TaskQueue):
        """
        初始化主循环
        
        Args:
            task_queue: 任务队列（系统唯一驱动源）
        """
        self.task_queue = task_queue
        self.status = SystemStatus()
        self._alive = True          # 存续标志：永不手动置False（仅停机信号触发）
        self._last_heartbeat = 0.0  # 上次心跳时间戳
        self._last_evolve = 0       # 上次进化检查的run_counter

        # 业务回调（由上层注入，解耦存续层与业务层）
        self._on_task_callback: Optional[Callable] = None      # 任务执行回调
        self._on_idle_callback: Optional[Callable] = None      # 空闲进化回调
        self._on_evolve_callback: Optional[Callable] = None    # 周期进化回调
        self._on_shutdown_callback: Optional[Callable] = None  # 停机保存回调

        # 注册信号处理
        self._register_signals()

    # ============================================================
    # 阶段18: 优雅停机 — 信号处理
    # ============================================================

    def _register_signals(self):
        """
        注册系统信号处理
        
        公理溯源：存续公理 — 优雅停机，安全保存状态后退出
        
        设计意图：
        - SIGINT (Ctrl+C) → 优雅停机
        - SIGTERM (kill)  → 优雅停机
        """
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        logger.info("信号处理已注册 (SIGINT, SIGTERM)")

    def _signal_handler(self, signum, frame):
        """
        信号处理函数
        
        Args:
            signum: 信号编号
            frame: 当前栈帧
        """
        signal_name = signal.Signals(signum).name
        logger.warning(f"收到信号 {signal_name}，准备优雅停机...")
        self._alive = False

    # ============================================================
    # 回调注册（依赖注入）
    # ============================================================

    def on_task(self, callback: Callable):
        """注册任务执行回调"""
        self._on_task_callback = callback
        return self

    def on_idle(self, callback: Callable):
        """注册空闲进化回调"""
        self._on_idle_callback = callback
        return self

    def on_evolve(self, callback: Callable):
        """注册周期进化回调"""
        self._on_evolve_callback = callback
        return self

    def on_shutdown(self, callback: Callable):
        """注册停机保存回调"""
        self._on_shutdown_callback = callback
        return self

    # ============================================================
    # 阶段11: 主循环框架
    # ============================================================

    def run(self):
        """
        启动永恒主循环
        
        公理溯源：存续公理 — 系统运行闭环永不终止
        
        循环逻辑（极简编排）：
        1. 健康检查（心跳 + 进化触发 + 资源检查）
        2. 获取任务
        3. 有任务 → 执行；无任务 → 空闲进化
        4. 全局异常捕获 → 自愈重启
        """
        self.status.state = SystemState.RUNNING
        self.status.start_time = now_iso()
        self._last_heartbeat = now_timestamp()

        logger.info("永恒主循环启动")

        while self._alive:
            try:
                # 1. 健康检查
                self._health_check()

                # 2. 检查停机信号
                if not self._alive:
                    break

                # 3. 获取任务
                task = self.task_queue.pop_highest_priority()

                # 4. 无任务 → 空闲进化模式
                if task is None:
                    self._idle_mode()
                    continue

                # 5. 有任务 → 执行
                self._execute_task(task)

                # 6. 循环节拍控制
                time.sleep(LOOP_DELAY)

            except EternalAgentError as e:
                # 已知异常：走自愈流程
                self._self_repair(str(e))
            except Exception as e:
                # 未知异常：走自愈流程
                self._self_repair(f"未知异常: {e}")

        # 循环退出 → 优雅停机
        self._graceful_shutdown()

    # ============================================================
    # 阶段12: 心跳检测
    # ============================================================

    def _health_check(self):
        """
        健康检查
        
        公理溯源：存续公理 — 系统永久在线，需要周期性自检
        
        包含：
        - 运行计数器递增
        - 心跳信号输出
        - 周期性进化触发
        - 资源熔断检查
        """
        # 阶段19: 运行计数器
        self.status.run_counter += 1

        # 心跳检测
        now = now_timestamp()
        if now - self._last_heartbeat >= HEARTBEAT_INTERVAL:
            self._heartbeat()
            self._last_heartbeat = now

        # 周期性进化触发（每 EVOLVE_STEP 步）
        if self.status.run_counter - self._last_evolve >= EVOLVE_STEP:
            self._trigger_evolve()
            self._last_evolve = self.status.run_counter

        # 阶段15: 资源熔断保护
        self._resource_check()

    def _heartbeat(self):
        """
        心跳信号输出
        
        公理溯源：存续公理 — 周期性存活信号
        
        设计意图：每 HEARTBEAT_INTERVAL 秒输出一次系统状态
        """
        from datetime import datetime
        start_ts = datetime.fromisoformat(self.status.start_time).timestamp() if self.status.start_time else now_timestamp()
        uptime = now_timestamp() - start_ts
        self.status.last_heartbeat = now_iso()

        logger.info(
            f"心跳 | 运行次数: {self.status.run_counter} | "
            f"任务完成: {self.status.total_tasks_completed} | "
            f"任务失败: {self.status.total_tasks_failed} | "
            f"队列: {self.task_queue.size()}/{self.task_queue._max_size} | "
            f"连续错误: {self.status.consecutive_errors}"
        )

    # ============================================================
    # 阶段15: 资源熔断保护
    # ============================================================

    def _resource_check(self):
        """
        资源熔断检查
        
        公理溯源：存续公理 — 资源熔断保护，确保系统稳态运行
        
        设计意图：
        - 资源超限 → 进入空闲模式等待恢复
        - 不抛出异常，而是降级运行
        """
        if monitor.should_throttle():
            resource_status = monitor.check_health()
            logger.warning(
                f"资源超限，进入降级模式 | "
                f"CPU: {resource_status.cpu_percent:.1f}% | "
                f"内存: {resource_status.memory_mb:.1f}MB | "
                f"磁盘: {resource_status.disk_percent:.1f}%"
            )
            # 降级：延长循环节拍，减少负载
            time.sleep(LOOP_DELAY * 10)

    # ============================================================
    # 阶段13: 全局异常捕获 + 阶段14: 自愈重启
    # ============================================================

    def _self_repair(self, error_msg: str):
        """
        自愈重启
        
        公理溯源：存续公理 — 局部异常永远不能击穿整体系统
        
        设计意图：
        - 记录异常
        - 递增连续错误计数
        - 短时休眠后重置状态，继续循环
        - 连续错误过多 → 记录告警但不退出（存续公理）
        """
        self.status.state = SystemState.REPAIRING
        self.status.consecutive_errors += 1

        logger.error(
            f"自愈触发 | 连续错误: {self.status.consecutive_errors}/{MAX_CONSECUTIVE_ERRORS} | "
            f"原因: {error_msg}"
        )

        # 连续错误过多 → 告警
        if self.status.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            logger.critical(
                f"连续错误达到上限 ({MAX_CONSECUTIVE_ERRORS})，"
                f"系统将重置错误计数并继续运行（存续公理：永不退出）"
            )
            self.status.consecutive_errors = 0

        # 自愈：休眠 → 重置状态 → 继续循环
        time.sleep(SELF_REPAIR_DELAY)
        self.status.state = SystemState.RUNNING

        logger.info("自愈完成，系统恢复正常运行")

    # ============================================================
    # 任务执行（回调注入）
    # ============================================================

    def _execute_task(self, task: Task):
        """
        执行任务
        
        Args:
            task: 待执行任务
        """
        self.status.state = SystemState.RUNNING

        try:
            task.start()

            # 调用业务回调
            if self._on_task_callback:
                result = self._on_task_callback(task)
                task.complete(str(result) if result else None)
            else:
                task.complete("默认执行")

            self.status.total_tasks_completed += 1
            self.status.consecutive_errors = 0  # 成功执行，重置错误计数

            logger.debug(f"任务完成: {task.name}")

            # 阶段58: 循环任务完成后重新入队
            if task.is_cyclic and task.cyclic_interval > 0:
                new_task = Task(
                    name=task.name,
                    priority=task.priority,
                    task_type=task.task_type,
                    payload=task.payload,
                    is_cyclic=True,
                    cyclic_interval=task.cyclic_interval,
                )
                self.task_queue.enqueue(new_task)

        except Exception as e:
            task.fail(str(e))
            self.status.total_tasks_failed += 1
            logger.error(f"任务失败: {task.name} | 错误: {e}")

            # 阶段53: 重试策略
            if task.can_retry():
                task.record_retry()
                task.state = TaskState.PENDING  # 重置状态
                task.started_at = None
                task.completed_at = None
                task.error = None
                self.task_queue.add(task.name, task.priority)
                logger.info(f"任务重试: {task.name} (第{task.retry_count}次)")

            # 阶段52: 超时检测
            if task.is_expired():
                logger.warning(f"任务超时: {task.name} (超限: {task.timeout}s)")

    # ============================================================
    # 空闲进化模式
    # ============================================================

    def _idle_mode(self):
        """
        空闲进化模式
        
        公理溯源：自驱公理 — 无外部输入时，系统自我梳理知识
        
        设计意图：
        - 队列为空时触发
        - 调用空闲回调（上层实现知识复盘）
        - 短时休眠，维持循环不退出
        """
        self.status.state = SystemState.IDLE

        if self._on_idle_callback:
            try:
                self._on_idle_callback()
            except Exception as e:
                logger.warning(f"空闲进化回调异常: {e}")

        # 空闲时延长休眠，降低资源消耗
        time.sleep(LOOP_DELAY * 3)

    # ============================================================
    # 周期进化触发
    # ============================================================

    def _trigger_evolve(self):
        """
        周期进化触发
        
        公理溯源：自驱公理 — 每 EVOLVE_STEP 步自动精简知识、迭代认知
        """
        logger.info(f"周期进化触发 (第 {self.status.run_counter} 步)")

        if self._on_evolve_callback:
            try:
                self._on_evolve_callback()
            except Exception as e:
                logger.warning(f"周期进化回调异常: {e}")

    # ============================================================
    # 阶段18: 优雅停机
    # ============================================================

    def _graceful_shutdown(self):
        """
        优雅停机
        
        公理溯源：存续公理 — 即使退出也要安全保存状态
        
        设计意图：
        - 调用停机回调保存所有状态
        - 输出最终统计
        - 安全退出
        """
        self.status.state = SystemState.SHUTTING_DOWN
        logger.info("开始优雅停机...")

        # 调用停机回调（保存知识图谱等）
        if self._on_shutdown_callback:
            try:
                self._on_shutdown_callback()
            except Exception as e:
                logger.error(f"停机回调异常: {e}")

        # 最终统计
        logger.info("=" * 50)
        logger.info("系统停机统计:")
        logger.info(f"  总运行次数: {self.status.run_counter}")
        logger.info(f"  完成任务数: {self.status.total_tasks_completed}")
        logger.info(f"  失败任务数: {self.status.total_tasks_failed}")
        logger.info(f"  队列剩余任务: {self.task_queue.size()}")
        logger.info("=" * 50)
        logger.info("系统已安全停机")

    # ============================================================
    # 外部控制接口
    # ============================================================

    def stop(self):
        """外部调用停止循环"""
        logger.info("收到外部停机请求")
        self._alive = False

    def is_alive(self) -> bool:
        """系统是否存活"""
        return self._alive

    def get_status(self) -> SystemStatus:
        """获取当前系统状态"""
        return self.status
