"""
定时调度模块

公理溯源：自驱公理 - 系统可按计划自动执行周期性任务

设计意图：
- Cron表达式解析（简化版5字段）
- 定时任务管理
- 任务执行历史
- 零外部依赖
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from exceptions import EternalAgentError


class SchedulerError(EternalAgentError):
    """调度器异常"""
    pass


class CronParseError(SchedulerError):
    """Cron表达式解析异常"""
    pass


@dataclass
class CronExpression:
    """
    简化版Cron表达式（5字段）

    格式: minute hour day_of_month month day_of_week
    支持: * (任意), 具体值, 逗号分隔, 范围(1-5), 步长(*/5)
    """
    minute: str = "*"
    hour: str = "*"
    day_of_month: str = "*"
    month: str = "*"
    day_of_week: str = "*"

    _raw: str = ""

    @classmethod
    def parse(cls, expression: str) -> 'CronExpression':
        """解析Cron表达式"""
        parts = expression.strip().split()
        if len(parts) != 5:
            raise CronParseError(
                f"Cron表达式需要5个字段，得到 {len(parts)}: '{expression}'"
            )

        cron = cls(
            minute=parts[0],
            hour=parts[1],
            day_of_month=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            _raw=expression,
        )

        # 验证各字段
        cron._validate_field(parts[0], "minute", 0, 59)
        cron._validate_field(parts[1], "hour", 0, 23)
        cron._validate_field(parts[2], "day_of_month", 1, 31)
        cron._validate_field(parts[3], "month", 1, 12)
        cron._validate_field(parts[4], "day_of_week", 0, 6)

        return cron

    def matches(self, dt: Optional[datetime] = None) -> bool:
        """检查指定时间是否匹配"""
        if dt is None:
            dt = datetime.now()

        return (
            self._field_matches(self.minute, dt.minute, 0, 59) and
            self._field_matches(self.hour, dt.hour, 0, 23) and
            self._field_matches(self.day_of_month, dt.day, 1, 31) and
            self._field_matches(self.month, dt.month, 1, 12) and
            self._field_matches(self.day_of_week, dt.weekday(), 0, 6)
        )

    def next_run(self, after: Optional[datetime] = None, max_iterations: int = 525960) -> Optional[datetime]:
        """
        计算下次运行时间（最多搜索max_iterations分钟）

        Args:
            after: 起始时间
            max_iterations: 最大搜索分钟数（默认1年）
        """
        if after is None:
            after = datetime.now()

        # 从下一分钟开始搜索
        current = after.replace(second=0, microsecond=0)

        for _ in range(max_iterations):
            current = current.replace(minute=current.minute + 1)
            # 处理分钟溢出
            if current.minute >= 60:
                current = current.replace(minute=0)
                current = current.replace(hour=current.hour + 1)
                if current.hour >= 24:
                    # 简化处理：跳到下一天
                    from datetime import timedelta
                    current = (current.replace(hour=0) + timedelta(days=1))
                    continue

            if self.matches(current):
                return current

        return None

    def describe(self) -> str:
        """生成人类可读描述"""
        descriptions = []
        if self.minute != "*":
            descriptions.append(f"第{self.minute}分钟")
        if self.hour != "*":
            descriptions.append(f"{self.hour}点")
        if self.day_of_month != "*":
            descriptions.append(f"每月{self.day_of_month}日")
        if self.month != "*":
            descriptions.append(f"{self.month}月")
        if self.day_of_week != "*":
            week_names = ["日", "一", "二", "三", "四", "五", "六"]
            if self.day_of_week == "*":
                pass
            else:
                try:
                    idx = int(self.day_of_week)
                    descriptions.append(f"周{week_names[idx]}")
                except ValueError:
                    descriptions.append(f"周{self.day_of_week}")

        if not descriptions:
            return "每分钟"
        return " ".join(descriptions)

    def _validate_step(self, part: str, name: str) -> None:
        """验证步长格式"""
        base, step = part.split("/", 1)
        if base != "*" and base != "":
            try:
                int(base)
            except ValueError:
                raise CronParseError(f"无效的 {name}: '{part}'")
        try:
            s = int(step)
            if s <= 0:
                raise CronParseError(f"{name} 步长必须 > 0: '{part}'")
        except ValueError:
            raise CronParseError(f"无效的 {name} 步长: '{part}'")

    def _validate_range(self, part: str, name: str, min_val: int, max_val: int) -> None:
        """验证范围格式"""
        start, end = part.split("-", 1)
        try:
            s, e = int(start), int(end)
            if s < min_val or e > max_val or s > e:
                raise CronParseError(f"{name} 范围无效 ({min_val}-{max_val}): '{part}'")
        except ValueError:
            raise CronParseError(f"无效的 {name} 范围: '{part}'")

    def _validate_single(self, part: str, value: str, name: str, min_val: int, max_val: int) -> None:
        """验证单个值"""
        try:
            v = int(value if "," not in value else part)
            if v < min_val or v > max_val:
                raise CronParseError(f"{name} 超出范围 ({min_val}-{max_val}): '{part}'")
        except ValueError:
            raise CronParseError(f"无效的 {name}: '{part}'")

    def _validate_field(self, value: str, name: str, min_val: int, max_val: int) -> None:
        """验证字段值"""
        if value == "*":
            return
        for part in value.split(","):
            if "/" in part:
                self._validate_step(part, name)
            elif "-" in part:
                self._validate_range(part, name, min_val, max_val)
            else:
                self._validate_single(part, value, name, min_val, max_val)

    def _field_matches(self, field_expr: str, value: int, min_val: int, max_val: int) -> bool:
        """检查字段是否匹配"""
        if field_expr == "*":
            return True

        for part in field_expr.split(","):
            if "/" in part:
                base, step_str = part.split("/", 1)
                step = int(step_str)
                if base == "*":
                    start = min_val
                else:
                    start = int(base)
                if (value - start) % step == 0 and value >= start:
                    return True
            elif "-" in part:
                start, end = part.split("-", 1)
                if int(start) <= value <= int(end):
                    return True
            else:
                if int(part) == value:
                    return True

        return False


@dataclass
class ScheduledJob:
    """调度任务"""
    name: str
    cron: CronExpression
    callback: Callable[[], Any]
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    last_error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class Scheduler:
    """
    定时调度器

    职责：
    - 管理定时任务
    - 按Cron表达式触发回调
    - 记录执行历史
    - 线程安全
    """

    def __init__(self, tick_interval: float = 30.0):
        """
        Args:
            tick_interval: 检查间隔（秒），默认30秒
        """
        self._jobs: Dict[str, ScheduledJob] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tick_interval = tick_interval
        self._stats = {
            "total_runs": 0,
            "total_errors": 0,
        }

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def job_names(self) -> List[str]:
        return list(self._jobs.keys())

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

    def add_job(
        self,
        name: str,
        cron_expression: str,
        callback: Callable[[], Any],
        enabled: bool = True,
    ) -> ScheduledJob:
        """
        添加定时任务

        Args:
            name: 任务名称
            cron_expression: Cron表达式
            callback: 回调函数
            enabled: 是否启用
        """
        cron = CronExpression.parse(cron_expression)
        job = ScheduledJob(
            name=name,
            cron=cron,
            callback=callback,
            enabled=enabled,
        )
        with self._lock:
            self._jobs[name] = job
        return job

    def remove_job(self, name: str) -> bool:
        """移除定时任务"""
        with self._lock:
            if name in self._jobs:
                del self._jobs[name]
                return True
            return False

    def enable_job(self, name: str) -> None:
        """启用任务"""
        with self._lock:
            if name in self._jobs:
                self._jobs[name].enabled = True

    def disable_job(self, name: str) -> None:
        """禁用任务"""
        with self._lock:
            if name in self._jobs:
                self._jobs[name].enabled = False

    def get_job(self, name: str) -> Optional[ScheduledJob]:
        """获取任务"""
        return self._jobs.get(name)

    def start(self) -> None:
        """启动调度器"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10.0)
            self._thread = None

    def tick(self) -> List[str]:
        """
        手动触发一次检查

        Returns:
            触发的任务名称列表
        """
        return self._check_jobs()

    def get_summary(self) -> Dict[str, Any]:
        """获取调度器摘要"""
        with self._lock:
            jobs_info = {}
            for name, job in self._jobs.items():
                jobs_info[name] = {
                    "cron": job.cron._raw,
                    "description": job.cron.describe(),
                    "enabled": job.enabled,
                    "last_run": job.last_run,
                    "next_run": job.next_run,
                    "run_count": job.run_count,
                    "last_error": job.last_error,
                }
            return {
                "running": self._running,
                "jobs": jobs_info,
                "stats": self._stats,
            }

    def _tick_loop(self) -> None:
        """调度循环"""
        while self._running:
            try:
                self._check_jobs()
            except Exception:
                pass
            time.sleep(self._tick_interval)

    def _check_jobs(self) -> List[str]:
        """检查并执行到期的任务"""
        triggered = []
        now = datetime.now()

        with self._lock:
            for name, job in self._jobs.items():
                if not job.enabled:
                    continue

                if job.cron.matches(now):
                    try:
                        job.callback()
                        job.last_run = now.isoformat()
                        job.run_count += 1
                        job.last_error = None
                        self._stats["total_runs"] += 1
                        triggered.append(name)
                    except Exception as e:
                        job.last_error = str(e)
                        self._stats["total_errors"] += 1

                # 更新下次运行时间
                next_time = job.cron.next_run(after=now)
                job.next_run = next_time.isoformat() if next_time else None

        return triggered
