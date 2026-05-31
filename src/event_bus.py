"""
事件总线模块

公理溯源：存续公理 - 系统组件间通过事件解耦通信，局部故障不传播

设计意图：
- 发布/订阅模式
- 同步和异步事件分发
- 事件过滤和优先级
- 事件历史记录
- 零外部依赖
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from exceptions import EternalAgentError


class EventError(EternalAgentError):
    """事件总线异常"""
    pass


@dataclass
class Event:
    """
    事件对象

    Attributes:
        topic: 事件主题
        data: 事件数据
        source: 事件来源
        timestamp: 事件时间戳
        id: 事件唯一ID
    """
    topic: str
    data: Any = None
    source: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    id: str = ""

    def __post_init__(self):
        if not self.id:
            from utils import generate_short_id
            self.id = generate_short_id()


@dataclass
class Subscription:
    """订阅信息"""
    callback: Callable
    priority: int = 0  # 数值越大优先级越高
    filter_fn: Optional[Callable[[Event], bool]] = None
    one_time: bool = False  # 是否只触发一次
    subscriber_name: str = ""


@dataclass
class EventRecord:
    """事件历史记录"""
    event: Event
    handled_by: List[str] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None


class EventBus:
    """
    事件总线

    职责：
    - 管理主题订阅
    - 发布事件并分发到订阅者
    - 支持通配符订阅
    - 事件历史追踪
    - 线程安全
    """

    WILDCARD = "*"

    def __init__(self, max_history: int = 1000):
        self._subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self._lock = threading.RLock()
        self._history: List[EventRecord] = []
        self._max_history = max_history
        self._stats = {
            "published": 0,
            "delivered": 0,
            "failed": 0,
        }
        self._publish_depth = 0

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

    @property
    def topics(self) -> List[str]:
        with self._lock:
            return list(self._subscriptions.keys())

    def subscribe(
        self,
        topic: str,
        callback: Callable[[Event], Any],
        priority: int = 0,
        filter_fn: Optional[Callable[[Event], bool]] = None,
        one_time: bool = False,
        subscriber_name: str = "",
    ) -> str:
        """
        订阅主题

        Args:
            topic: 主题名称（支持通配符 *）
            callback: 回调函数
            priority: 优先级（数值越大越先执行）
            filter_fn: 过滤函数，返回True才执行
            one_time: 是否只触发一次
            subscriber_name: 订阅者名称

        Returns:
            订阅ID
        """
        from utils import generate_short_id
        sub_id = generate_short_id()

        sub = Subscription(
            callback=callback,
            priority=priority,
            filter_fn=filter_fn,
            one_time=one_time,
            subscriber_name=subscriber_name or callback.__name__,
        )

        with self._lock:
            self._subscriptions[topic].append(sub)
            # 按优先级排序（高优先级在前）
            self._subscriptions[topic].sort(key=lambda s: s.priority, reverse=True)

        return sub_id

    def subscribe_once(
        self,
        topic: str,
        callback: Callable[[Event], Any],
        **kwargs: Any,
    ) -> str:
        """一次性订阅"""
        return self.subscribe(topic, callback, one_time=True, **kwargs)

    def unsubscribe(self, topic: str, callback: Callable) -> bool:
        """
        取消订阅

        Returns:
            是否成功取消
        """
        with self._lock:
            if topic not in self._subscriptions:
                return False
            original_len = len(self._subscriptions[topic])
            self._subscriptions[topic] = [
                sub for sub in self._subscriptions[topic]
                if sub.callback != callback
            ]
            return len(self._subscriptions[topic]) < original_len

    def unsubscribe_all(self, topic: Optional[str] = None) -> int:
        """
        取消订阅

        Args:
            topic: 主题名称，None表示取消所有

        Returns:
            取消的订阅数量
        """
        with self._lock:
            if topic:
                count = len(self._subscriptions.get(topic, []))
                del self._subscriptions[topic]
                return count
            else:
                total = sum(len(subs) for subs in self._subscriptions.values())
                self._subscriptions.clear()
                return total

    def publish(self, event: Event) -> List[Any]:
        """
        发布事件

        Args:
            event: 事件对象

        Returns:
            各回调返回值列表
        """
        # 递归发布防护
        self._publish_depth += 1
        if self._publish_depth > 10:
            self._publish_depth -= 1
            from logger import get_logger
            get_logger("EventBus").error(f"递归发布深度超限(>10)，拒绝发布: {event.topic}")
            return []
        try:
            results = []
            handled_by = []
            has_error = False

            with self._lock:
                self._stats["published"] += 1
                matched_subs = self._match_subscriptions(event)

                # 复制一份，避免回调中修改订阅列表
                subs_snapshot = list(matched_subs)

            for sub in subs_snapshot:
                # 过滤检查
                if sub.filter_fn and not sub.filter_fn(event):
                    continue

                try:
                    result = sub.callback(event)
                    results.append(result)
                    handled_by.append(sub.subscriber_name)
                    with self._lock:
                        self._stats["delivered"] += 1
                except Exception as e:
                    has_error = True
                    with self._lock:
                        self._stats["failed"] += 1
                    handled_by.append(f"{sub.subscriber_name}(ERROR)")

                # 一次性订阅清理
                if sub.one_time:
                    with self._lock:
                        for topic_key in list(self._subscriptions.keys()):
                            self._subscriptions[topic_key] = [
                                s for s in self._subscriptions[topic_key]
                                if not s.one_time or s.callback != sub.callback
                            ]

            # 记录历史
            record = EventRecord(
                event=event,
                handled_by=handled_by,
                success=not has_error,
            )
            self._add_history(record)

            return results
        finally:
            self._publish_depth -= 1

    def publish_simple(self, topic: str, data: Any = None, source: str = "") -> List[Any]:
        """简化的发布接口"""
        event = Event(topic=topic, data=data, source=source)
        return self.publish(event)

    def get_subscribers(self, topic: str) -> List[str]:
        """获取主题的订阅者名称列表"""
        with self._lock:
            subs = self._subscriptions.get(topic, [])
            return [s.subscriber_name for s in subs]

    def get_history(
        self,
        topic: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取事件历史

        Args:
            topic: 过滤主题
            limit: 最大返回数量

        Returns:
            事件记录字典列表
        """
        records = self._history
        if topic:
            records = [r for r in records if r.event.topic == topic]

        return [
            {
                "event_id": r.event.id,
                "topic": r.event.topic,
                "source": r.event.source,
                "timestamp": r.event.timestamp,
                "handled_by": r.handled_by,
                "success": r.success,
            }
            for r in records[-limit:]
        ]

    def clear_history(self) -> int:
        """清空事件历史"""
        count = len(self._history)
        self._history.clear()
        return count

    def _match_subscriptions(self, event: Event) -> List[Subscription]:
        """匹配事件的所有订阅"""
        matched = []
        # 精确匹配
        if event.topic in self._subscriptions:
            matched.extend(self._subscriptions[event.topic])
        # 通配符匹配
        if self.WILDCARD in self._subscriptions:
            matched.extend(self._subscriptions[self.WILDCARD])
        return matched

    def _add_history(self, record: EventRecord) -> None:
        """添加历史记录（线程安全）"""
        with self._lock:
            self._history.append(record)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]


# 全局事件总线单例
_global_bus: Optional[EventBus] = None
_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """获取全局事件总线"""
    global _global_bus
    if _global_bus is None:
        with _bus_lock:
            if _global_bus is None:
                _global_bus = EventBus()
    return _global_bus
