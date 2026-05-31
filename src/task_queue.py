"""
任务队列模块

公理溯源：
- 自驱公理：任务队列是系统唯一驱动源，所有行为由任务触发
- 资源守恒：队列上限杜绝无限膨胀

设计意图：
- 先进先出（FIFO）队列
- 固定上限，超限自动淘汰最旧任务
- 支持批量添加、去重
- 线程安全（为后续扩展预留）
- 零外部依赖
"""

from collections import deque
from typing import Any, Callable, Dict, List, Optional

from models import Task
from constants import TASK_QUEUE_MAX, TaskState
from exceptions import TaskQueueFullError
from utils import unique_list
from logger import get_logger

logger = get_logger("TaskQueue")


class TaskQueue:
    """
    任务队列
    
    公理溯源：
    - 自驱公理：系统唯一驱动源
    - 资源守恒：TASK_QUEUE_MAX 限制上限
    
    特性：
    - FIFO 先进先出
    - 超限自动丢弃最旧任务
    - 自动去重
    - 支持优先级插入
    """

    def __init__(self, max_size: int = TASK_QUEUE_MAX):
        """
        初始化任务队列
        
        Args:
            max_size: 队列最大容量
        """
        self._queue: deque = deque()
        self._max_size = max_size
        self._discarded_count = 0  # 被丢弃的任务计数
        self._handlers: Dict[str, Callable] = {}  # 任务类型处理器

    # ============================================================
    # 核心操作
    # ============================================================

    def add(self, task_name: str, priority: int = 0) -> bool:
        """
        添加任务到队列
        
        Args:
            task_name: 任务名称
            priority: 优先级（数值越大越优先，0为普通）
            
        Returns:
            bool: 是否成功入队
        """
        task = Task(name=task_name, priority=priority)

        # 队列已满时，自动丢弃最旧任务
        if len(self._queue) >= self._max_size:
            discarded = self._queue.popleft()
            self._discarded_count += 1
            logger.warning(f"队列已满({self._max_size})，丢弃最旧任务: {discarded.name}")

        self._queue.append(task)
        logger.debug(f"任务入队: {task_name} (队列大小: {len(self._queue)})")
        return True

    def batch_add(self, task_names: List[str], priority: int = 0) -> int:
        """
        批量添加任务（自动去重）
        
        Args:
            task_names: 任务名称列表
            priority: 优先级
            
        Returns:
            int: 实际入队数量
        """
        # 去重：排除已在队列中的任务
        existing = {t.name for t in self._queue}
        new_names = unique_list([n for n in task_names if n not in existing])

        count = 0
        for name in new_names:
            if self.add(name, priority):
                count += 1

        if count > 0:
            logger.debug(f"批量入队: {count} 个任务 (去重后)")
        return count

    def get(self) -> Optional[Task]:
        """
        获取队首任务（不出队）
        
        Returns:
            Optional[Task]: 队首任务，队列为空返回None
        """
        return self._queue[0] if self._queue else None

    def pop(self) -> Optional[Task]:
        """
        弹出队首任务

        Returns:
            Optional[Task]: 队首任务，队列为空返回None
        """
        if self._queue:
            task = self._queue.popleft()
            logger.debug(f"任务出队: {task.name} (剩余: {len(self._queue)})")
            return task
        return None

    def pop_highest_priority(self) -> Optional[Task]:
        """
        弹出优先级最高的任务

        阶段56: 优先级队列升级

        Returns:
            Optional[Task]: 优先级最高的任务
        """
        if not self._queue:
            return None

        # 找到优先级最高的任务
        best_idx = 0
        for i, task in enumerate(self._queue):
            if task.priority > self._queue[best_idx].priority:
                best_idx = i

        task = self._queue[best_idx]
        del self._queue[best_idx]
        logger.debug(f"优先级出队: {task.name} (优先级:{task.priority})")
        return task

    def pop_by_tag(self, tag: str) -> Optional[Task]:
        """
        弹出指定标签的任务

        阶段59: 任务标签

        Args:
            tag: 标签

        Returns:
            Optional[Task]: 匹配的任务
        """
        for i, task in enumerate(self._queue):
            if task.has_tag(tag):
                del self._queue[i]
                logger.debug(f"标签出队: {task.name} (标签:{tag})")
                return task
        return None

    def add_with_dependencies(self, task_name: str, dependencies: List[str],
                              priority: int = 0) -> bool:
        """
        添加带依赖的任务

        阶段51: 任务依赖图

        Args:
            task_name: 任务名称
            dependencies: 依赖任务列表
            priority: 优先级

        Returns:
            bool: 是否成功入队
        """
        task = Task(name=task_name, priority=priority)
        for dep in dependencies:
            task.add_dependency(dep)

        if len(self._queue) >= self._max_size:
            discarded = self._queue.popleft()
            self._discarded_count += 1

        self._queue.append(task)
        logger.debug(f"依赖任务入队: {task_name} (依赖: {dependencies})")
        return True

    def add_cyclic_task(self, task_name: str, interval: float,
                        priority: int = 0) -> bool:
        """
        添加循环任务

        阶段58: 循环任务

        Args:
            task_name: 任务名称
            interval: 循环间隔（秒）
            priority: 优先级

        Returns:
            bool: 是否成功入队
        """
        task = Task(name=task_name, priority=priority,
                    is_cyclic=True, cyclic_interval=interval)

        if len(self._queue) >= self._max_size:
            discarded = self._queue.popleft()
            self._discarded_count += 1

        self._queue.append(task)
        logger.debug(f"循环任务入队: {task_name} (间隔: {interval}s)")
        return True

    # ============================================================
    # 查询操作
    # ============================================================

    def is_empty(self) -> bool:
        """队列是否为空"""
        return len(self._queue) == 0

    def size(self) -> int:
        """当前队列大小"""
        return len(self._queue)

    def is_full(self) -> bool:
        """队列是否已满"""
        return len(self._queue) >= self._max_size

    def contains(self, task_name: str) -> bool:
        """检查任务是否在队列中"""
        return any(t.name == task_name for t in self._queue)

    def get_all_names(self) -> List[str]:
        """获取所有任务名称"""
        return [t.name for t in self._queue]

    def clear(self) -> int:
        """
        清空队列
        
        Returns:
            int: 被清空的任务数量
        """
        count = len(self._queue)
        self._queue.clear()
        logger.info(f"队列已清空，移除 {count} 个任务")
        return count

    # ============================================================
    # 统计信息
    # ============================================================

    def stats(self) -> dict:
        """
        获取队列统计信息
        
        Returns:
            dict: 统计信息
        """
        return {
            "size": len(self._queue),
            "max_size": self._max_size,
            "is_empty": self.is_empty(),
            "is_full": self.is_full(),
            "discarded_count": self._discarded_count,
        }

    def __len__(self) -> int:
        """支持 len() 操作"""
        return len(self._queue)

    def __bool__(self) -> bool:
        """支持 bool() 判断（非空为True）"""
        return len(self._queue) > 0

    def __repr__(self) -> str:
        return f"TaskQueue(size={len(self._queue)}/{self._max_size})"

    # ============================================================
    # 扩展接口
    # ============================================================

    def enqueue(self, task: Task) -> bool:
        """
        将 Task 对象直接入队

        Args:
            task: Task 对象

        Returns:
            bool: 是否成功入队
        """
        if len(self._queue) >= self._max_size:
            discarded = self._queue.popleft()
            self._discarded_count += 1
            logger.warning(f"队列已满({self._max_size})，丢弃最旧任务: {discarded.name}")

        self._queue.append(task)
        logger.debug(f"任务入队: {task.name} (队列大小: {len(self._queue)})")
        return True

    def register_handler(self, task_type: str, handler: Callable) -> None:
        """
        注册任务类型处理器

        Args:
            task_type: 任务类型
            handler: 处理函数
        """
        self._handlers[task_type] = handler
        logger.debug(f"注册任务处理器: {task_type}")

    def get_handler(self, task_type: str) -> Optional[Callable]:
        """
        获取任务类型处理器

        Args:
            task_type: 任务类型

        Returns:
            Optional[Callable]: 处理函数，未注册返回None
        """
        return self._handlers.get(task_type)
