"""
统一启动入口模块

公理溯源：存续公理 - 系统引导编排，一键启动完整生态

设计意图：
- 统一初始化所有子系统
- 启动顺序编排
- 系统状态汇总
- 优雅启停
- 零外部依赖
"""

import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from exceptions import EternalAgentError


class BootError(EternalAgentError):
    """启动异常"""
    pass


@dataclass
class BootPhase:
    """启动阶段"""
    name: str
    status: str = "pending"  # pending, running, success, failed, skipped
    duration_ms: float = 0.0
    error: Optional[str] = None
    detail: str = ""


@dataclass
class BootResult:
    """启动结果"""
    success: bool
    phases: List[BootPhase] = field(default_factory=list)
    total_duration_ms: float = 0.0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "timestamp": self.timestamp,
            "error": self.error,
            "phases": [
                {"name": p.name, "status": p.status, "duration_ms": round(p.duration_ms, 2), "error": p.error}
                for p in self.phases
            ],
        }


class Bootstrapper:
    """
    系统引导器

    启动阶段：
    1. 基础层 — 日志、配置、常量
    2. 存续层 — 任务队列、主循环
    3. 记忆层 — 知识图谱
    4. 自驱层 — 智能体主体
    5. 生态层 — 插件、事件总线、调度器
    6. 生产层 — 配置中心、审计、健康检查
    7. 服务层 — API、CLI、仪表盘
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or Path(__file__).parent.parent / "data"
        self._phases: List[BootPhase] = []
        self._components: Dict[str, Any] = {}
        self._start_time: float = 0.0

    @property
    def components(self) -> Dict[str, Any]:
        return dict(self._components)

    def get_component(self, name: str) -> Optional[Any]:
        """获取已初始化的组件"""
        return self._components.get(name)

    def boot(self, enable_api: bool = False, enable_plugins: bool = False) -> BootResult:
        """
        执行完整启动流程

        Args:
            enable_api: 是否启动HTTP API
            enable_plugins: 是否加载插件

        Returns:
            BootResult
        """
        self._start_time = time.time()
        self._phases = []

        # 阶段1: 基础层
        self._run_phase("基础层初始化", self._init_base)

        # 阶段2: 存续层
        self._run_phase("存续层初始化", self._init_survival)

        # 阶段3: 记忆层
        self._run_phase("记忆层初始化", self._init_memory)

        # 阶段4: 自驱层
        self._run_phase("自驱层初始化", self._init_self_drive)

        # 阶段5: 生态层
        self._run_phase("生态层初始化", lambda: self._init_ecosystem(enable_plugins))

        # 阶段6: 生产层
        self._run_phase("生产层初始化", self._init_production)

        # 阶段7: 服务层
        self._run_phase("服务层初始化", lambda: self._init_services(enable_api))

        total_ms = (time.time() - self._start_time) * 1000
        success = all(p.status in ("success", "skipped") for p in self._phases)

        return BootResult(
            success=success,
            phases=self._phases,
            total_duration_ms=total_ms,
            error=None if success else "部分阶段启动失败",
        )

    def shutdown(self) -> Dict[str, Any]:
        """优雅停机"""
        results = {}

        # 停止API
        api = self._components.get("api_server")
        if api:
            try:
                api.stop()
                results["api"] = "stopped"
            except Exception:
                results["api"] = "error"

        # 停止调度器
        scheduler = self._components.get("scheduler")
        if scheduler:
            try:
                scheduler.stop()
                results["scheduler"] = "stopped"
            except Exception:
                results["scheduler"] = "error"

        # 保存知识图谱
        kg = self._components.get("knowledge_graph")
        if kg:
            try:
                kg.force_save()
                results["knowledge_graph"] = "saved"
            except Exception:
                results["knowledge_graph"] = "error"

        # 停止文件监控
        watcher = self._components.get("file_watcher")
        if watcher:
            try:
                watcher.stop()
                results["file_watcher"] = "stopped"
            except Exception:
                results["file_watcher"] = "error"

        return results

    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "components": {},
            "uptime_seconds": round((time.time() - self._start_time), 1) if self._start_time else 0,
        }

        for name, comp in self._components.items():
            if name == "knowledge_graph":
                status["components"][name] = comp.stats()
            elif name == "task_queue":
                status["components"][name] = {
                    "size": comp.size,
                    "max_size": comp._max_size,
                }
            elif name == "loop":
                try:
                    s = comp.get_status()
                    status["components"][name] = {
                        "state": s.state,
                        "run_counter": s.run_counter,
                    }
                except Exception:
                    status["components"][name] = "active"
            elif name == "event_bus":
                status["components"][name] = comp.stats
            elif name == "profiler":
                status["components"][name] = comp.get_summary()
            else:
                status["components"][name] = "loaded"

        return status

    def _run_phase(self, name: str, fn: Callable) -> None:
        """执行启动阶段"""
        phase = BootPhase(name=name, status="running")
        start = time.time()

        try:
            fn()
            phase.status = "success"
        except Exception as e:
            phase.status = "failed"
            phase.error = str(e)

        phase.duration_ms = (time.time() - start) * 1000
        self._phases.append(phase)

    def _init_base(self) -> None:
        """基础层初始化"""
        from logger import get_logger
        logger = get_logger("Boot")
        logger.info("基础层初始化...")

        from config_center import ConfigCenter, ConfigSchema
        cc = ConfigCenter(config_dir=self._data_dir / "config_center")
        cc.register_schemas([
            ConfigSchema(key="system.name", value_type="str", default="EternalAgent", group="system"),
            ConfigSchema(key="system.loop_delay", value_type="float", default=0.3, min_value=0.05, max_value=10.0, group="system"),
            ConfigSchema(key="system.max_tasks", value_type="int", default=200, min_value=10, max_value=10000, group="system"),
            ConfigSchema(key="kg.trim_threshold", value_type="float", default=0.1, group="knowledge"),
            ConfigSchema(key="kg.derive_threshold", value_type="float", default=0.2, group="knowledge"),
            ConfigSchema(key="api.enabled", value_type="bool", default=True, group="api"),
            ConfigSchema(key="api.port", value_type="int", default=8080, group="api"),
        ])
        self._components["config_center"] = cc

        from profiler import Profiler
        self._components["profiler"] = Profiler()

        logger.info("基础层初始化完成")

    def _init_survival(self) -> None:
        """存续层初始化"""
        from logger import get_logger
        get_logger("Boot").info("存续层初始化...")

        from task_queue import TaskQueue
        tq = TaskQueue()
        self._components["task_queue"] = tq

        from loop import EternalLoop
        loop = EternalLoop(tq)
        self._components["loop"] = loop

    def _init_memory(self) -> None:
        """记忆层初始化"""
        from logger import get_logger
        get_logger("Boot").info("记忆层初始化...")

        kg_path = self._data_dir / "knowledge_graph.json"
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(save_path=kg_path)
        self._components["knowledge_graph"] = kg

    def _init_self_drive(self) -> None:
        """自驱层初始化"""
        from logger import get_logger
        get_logger("Boot").info("自驱层初始化...")

        from eternal_agent import EternalSelfAgent
        agent = EternalSelfAgent()

        # 注入已初始化的组件
        agent.knowledge_graph = self._components["knowledge_graph"]
        agent.task_queue = self._components["task_queue"]
        agent.loop = self._components["loop"]

        agent.initialize()
        self._components["agent"] = agent

    def _init_ecosystem(self, enable_plugins: bool = False) -> None:
        """生态层初始化"""
        from logger import get_logger
        get_logger("Boot").info("生态层初始化...")

        from event_bus import EventBus
        bus = EventBus()
        self._components["event_bus"] = bus

        from scheduler import Scheduler
        scheduler = Scheduler(tick_interval=60.0)
        self._components["scheduler"] = scheduler

        if enable_plugins:
            from plugin_system import PluginManager
            plugin_dir = self._data_dir / "plugins"
            plugin_dir.mkdir(parents=True, exist_ok=True)
            pm = PluginManager([plugin_dir])
            pm.load_all()
            self._components["plugin_manager"] = pm

    def _init_production(self) -> None:
        """生产层初始化"""
        from logger import get_logger
        get_logger("Boot").info("生产层初始化...")

        from audit_log import AuditLog
        al = AuditLog(log_dir=self._data_dir / "audit")
        self._components["audit_log"] = al

        from health import HealthMonitor
        hm = HealthMonitor(data_dir=self._data_dir)
        self._components["health_monitor"] = hm

        from diagnostics import SystemDiagnostics
        diag = SystemDiagnostics(data_dir=self._data_dir)
        self._components["diagnostics"] = diag

    def _init_services(self, enable_api: bool = False) -> None:
        """服务层初始化"""
        from logger import get_logger
        get_logger("Boot").info("服务层初始化...")

        if enable_api:
            try:
                from api import APIServer
                agent = self._components.get("agent")
                if agent:
                    cc = self._components.get("config_center")
                    port = cc.get("api.port", 8080) if cc else 8080
                    server = APIServer(agent=agent, port=port)
                    self._components["api_server"] = server
            except Exception as e:
                from logger import get_logger
                get_logger("Boot").warning(f"API启动跳过: {e}")
