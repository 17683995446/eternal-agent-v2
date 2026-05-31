"""
永恒自驱智能体主体 — 自驱进化层核心

公理溯源：
- 存续公理：系统运行闭环永不终止
- 记忆公理：智能 = 结构化历史经验
- 自驱公理：无外部输入时自我产生任务、自我梳理知识、自我精简迭代

设计意图：
- 整合三层架构（存续层+记忆层+自驱层）
- 实现知识驱动任务的完整永动闭环
- 提供简洁的启动接口

图难于其易，为大于其细：
- 每个能力独立方法
- 主循环只做轻量编排
- 复杂逻辑分解为可测试单元
"""

from typing import List, Optional, Dict, Any

from constants import (
    INITIAL_TASK,
    EVOLVE_STEP,
    TASK_DERIVE_WEIGHT_THRESHOLD,
    SystemState,
    NodeType,
    RelationType,
)
from models import Task, SystemStatus
from task_queue import TaskQueue
from loop import EternalLoop
from knowledge_graph import KnowledgeGraph
from logger import get_logger

logger = get_logger("EternalAgent")


class EternalSelfAgent:
    """
    永恒自驱智能体

    公理溯源：自驱公理 — 知识驱动智能体永续进化

    核心闭环：
    初始认知 → 执行任务 → 沉淀图谱 → 知识推演新任务 → 新任务再次沉淀新知
    形成无人工干预、无限循环、持续进化的软件永动体系。
    """

    def __init__(self):
        """初始化智能体"""
        # 三层架构组件
        self.knowledge_graph = KnowledgeGraph()
        self.task_queue = TaskQueue()
        self.loop = EternalLoop(self.task_queue)

        # 状态追踪
        self._initialized = False

        logger.info("永恒自驱智能体已创建")

    # ============================================================
    # 阶段36: 智能体主体类 — 初始化与启动
    # ============================================================

    def initialize(self) -> bool:
        """
        初始化系统

        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            return True

        logger.info("=" * 50)
        logger.info("初始化永恒自驱智能体...")

        # 1. 恢复历史记忆
        if not self.knowledge_graph.is_empty():
            logger.info(f"历史记忆已恢复: {self.knowledge_graph.stats()}")
        else:
            logger.info("新图谱已创建")

        # 2. 注册回调（绑定三层架构）
        self._register_callbacks()

        # 3. 阶段42: 初始认知注入
        self._inject_initial_knowledge()

        self._initialized = True
        logger.info("初始化完成")
        logger.info("=" * 50)

        return True

    def _register_callbacks(self):
        """注册主循环回调"""
        # 任务执行回调
        self.loop.on_task(self._execute_task)

        # 空闲进化回调
        self.loop.on_idle(self._idle_evolve)

        # 周期进化回调
        self.loop.on_evolve(self._periodic_evolve)

        # 停机保存回调
        self.loop.on_shutdown(self._shutdown_save)

        logger.debug("主循环回调已注册")

    def _inject_initial_knowledge(self):
        """
        阶段42: 注入初始认知任务

        公理溯源：自驱公理 — 启动自驱闭环原点
        """
        # 检查是否已有历史任务
        if self.knowledge_graph.is_empty():
            logger.info(f"注入初始认知: {INITIAL_TASK}")

            # 创建初始任务节点
            self.knowledge_graph.add_node(
                name=INITIAL_TASK,
                node_type=NodeType.TASK,
                attributes={"is_initial": True}
            )

            # 注入任务队列
            self.task_queue.add(INITIAL_TASK, priority=10)
        else:
            # 从历史记忆恢复任务
            task_nodes = self.knowledge_graph.get_nodes_by_type(NodeType.TASK)
            for node in task_nodes[:10]:  # 最多恢复10个历史任务
                self.task_queue.add(node.name, priority=5)
            logger.info(f"从历史恢复 {len(task_nodes)} 个任务")

    # ============================================================
    # 阶段37: 任务执行框架 — 标准化处理流程
    # ============================================================

    def _execute_task(self, task: Task) -> str:
        """
        执行任务

        公理溯源：
        - 存续公理：任务执行是系统驱动力
        - 记忆公理：执行结果沉淀为知识
        - 自驱公理：执行产生新任务

        处理流程：
        1. 任务开始 → 2. 业务处理 → 3. 知识沉淀 → 4. 推演新任务 → 5. 完成

        Args:
            task: 待执行任务

        Returns:
            str: 执行结果
        """
        logger.info(f"▶ 执行任务: {task.name}")

        try:
            # 阶段38: 任务→知识沉淀
            self._persist_task_knowledge(task)

            # 执行业务逻辑（简化版，后续可扩展）
            result = self._process_task_logic(task)

            # 阶段39: 知识→任务推演
            derived_tasks = self._derive_tasks_from_knowledge(task)

            # 阶段44: 任务去重（batch_add内部实现）
            if derived_tasks:
                added = self.task_queue.batch_add(derived_tasks, priority=5)
                logger.info(f"  ↳ 推演新任务: {added} 个")

            logger.info(f"✓ 任务完成: {task.name}")
            return result

        except Exception as e:
            logger.error(f"✗ 任务失败: {task.name} | {e}")
            raise

    def _process_task_logic(self, task: Task) -> str:
        """
        处理任务业务逻辑

        Args:
            task: 任务对象

        Returns:
            str: 处理结果
        """
        # 简化实现：根据任务类型执行不同逻辑
        if task.name.startswith("推演任务:"):
            # 推演任务：探索关联知识
            target = task.name.replace("推演任务:", "")
            return f"探索知识: {target}"

        elif "初始认知" in task.name:
            # 初始任务：系统自检
            return "系统自检完成"

        else:
            # 普通任务：默认处理
            return f"已处理: {task.name}"

    # ============================================================
    # 阶段38: 任务→知识沉淀
    # ============================================================

    def _persist_task_knowledge(self, task: Task):
        """
        将任务执行沉淀为知识

        公理溯源：记忆公理 — 所有行为必须落盘结构化数据
        """
        # 1. 创建任务节点
        self.knowledge_graph.add_task_node(task)

        # 2. 创建迭代边（任务→系统迭代）
        counter = self.loop.get_status().run_counter
        next_iter = f"迭代_{counter}"

        self.knowledge_graph.add_edge(
            source=task.name,
            target=next_iter,
            relation=RelationType.EVOLVED_FROM,
            weight=0.5
        )

        logger.debug(f"  ↳ 知识沉淀: {task.name} → {next_iter}")

    # ============================================================
    # 阶段39: 知识→任务推演
    # ============================================================

    def _derive_tasks_from_knowledge(self, task: Task) -> List[str]:
        """
        基于知识推演新任务

        公理溯源：自驱公理 — 知识关联自动推演新任务

        Args:
            task: 当前任务

        Returns:
            List[str]: 新任务名称列表
        """
        # 使用知识图谱推演
        derived = self.knowledge_graph.derive_new_tasks(
            task.name,
            threshold=TASK_DERIVE_WEIGHT_THRESHOLD
        )

        # 为每个推演结果创建衍生边
        for dt in derived:
            target = dt.replace("推演任务:", "")
            self.knowledge_graph.add_derived_edge(
                source_task=task.name,
                target_task=target,
                weight=0.7
            )

        return derived

    # ============================================================
    # 阶段40: 空闲自进化
    # ============================================================

    def _idle_evolve(self):
        """
        空闲进化模式

        公理溯源：自驱公理 — 无外部输入时自我梳理知识

        设计意图：
        - 队列为空时触发
        - 自动复盘历史知识
        - 生成探索性任务
        """
        logger.debug("空闲进化: 系统静默复盘")

        # 获取历史任务节点
        task_nodes = self.knowledge_graph.get_nodes_by_type(NodeType.TASK)

        if task_nodes:
            # 随机选择一个历史任务进行深度探索
            import random
            target = random.choice(task_nodes)

            # 生成探索任务
            explore_task = f"深度探索:{target.name}"
            self.task_queue.add(explore_task, priority=3)

            logger.info(f"空闲进化: 生成探索任务 '{explore_task}'")

    # ============================================================
    # 阶段41: 周期进化触发
    # ============================================================

    def _periodic_evolve(self):
        """
        周期进化触发

        公理溯源：自驱公理 — 每 EVOLVE_STEP 步自动精简知识、迭代认知
        """
        logger.info("周期进化: 知识精简与迭代")

        # 1. 淘汰低价值知识
        removed = self.knowledge_graph.trim_invalid_knowledge()
        if removed > 0:
            logger.info(f"  ↳ 精简知识: 删除 {removed} 条低价值边")

        # 2. 健康检查
        health = self.knowledge_graph.health_check()
        if not health["is_healthy"]:
            logger.warning(f"  ↳ 图谱异常: {health['issues']}")
            fixed = self.knowledge_graph.repair()
            logger.info(f"  ↳ 自动修复: {fixed}")

        # 3. 输出统计
        stats = self.knowledge_graph.stats()
        logger.info(f"  ↳ 图谱统计: {stats['node_count']} 节点, "
                   f"{stats['edge_count']} 边, "
                   f"密度 {stats['density']}")

    # ============================================================
    # 停机保存
    # ============================================================

    def _shutdown_save(self):
        """停机时保存所有状态"""
        logger.info("停机保存: 持久化知识图谱...")
        self.knowledge_graph.force_save()
        logger.info("停机保存完成")

    # ============================================================
    # 阶段43: 任务优先级 — 已在 Task 和 TaskQueue 中实现
    # ============================================================

    # Task.priority 字段 + Task.__lt__ 排序已实现优先级
    # TaskQueue 内部使用有序结构（后续可扩展为优先队列）

    # ============================================================
    # 阶段44: 任务去重 — 已在 TaskQueue.batch_add 中实现
    # ============================================================

    # batch_add 方法内部使用 unique_list 去重

    # ============================================================
    # 公共接口
    # ============================================================

    def run(self):
        """
        启动永恒主循环

        公理溯源：存续公理 — 系统运行闭环永不终止
        """
        if not self._initialized:
            self.initialize()

        logger.info("")
        logger.info("系统进入永恒主循环...")
        logger.info("(Ctrl+C 优雅停机)")
        logger.info("")

        self.loop.run()

    def stop(self):
        """停止系统"""
        logger.info("收到停止请求")
        self.loop.stop()

    def get_status(self) -> SystemStatus:
        """获取系统状态"""
        return self.loop.get_status()

    def get_kg_stats(self) -> Dict[str, Any]:
        """获取知识图谱统计"""
        return self.knowledge_graph.stats()

    def export_kg_visualization(self, format: str = "mermaid") -> str:
        """
        导出知识图谱可视化

        Args:
            format: 格式 (mermaid/graphviz)

        Returns:
            str: 可视化代码
        """
        if format == "mermaid":
            return self.knowledge_graph.export_mermaid()
        elif format == "graphviz":
            return self.knowledge_graph.export_graphviz()
        else:
            raise ValueError(f"不支持格式: {format}")

    # ============================================================
    # 扩展接口 (Phase 12 添加)
    # ============================================================

    def submit_task(self, name: str, task_type: str = "default", payload: Dict[str, Any] = None, priority: int = 5) -> str:
        """
        提交任务到队列

        Args:
            name: 任务名称
            task_type: 任务类型
            payload: 任务负载
            priority: 优先级

        Returns:
            str: 任务ID
        """
        from models import Task

        task = Task(
            name=name,
            task_type=task_type,
            payload=payload or {},
            priority=priority
        )
        self.task_queue.enqueue(task)
        logger.debug(f"提交任务: {name} (类型: {task_type})")
        return task.id

    def register_task_handler(self, task_type: str, handler):
        """
        注册任务处理器

        Args:
            task_type: 任务类型
            handler: 处理函数
        """
        self.task_queue.register_handler(task_type, handler)
        logger.debug(f"注册处理器: {task_type}")

    @property
    def queue(self):
        """获取任务队列"""
        return self.task_queue

    def start(self, on_task=None, on_idle=None, on_evolve=None, on_shutdown=None):
        """
        启动智能体（简化接口）

        Args:
            on_task: 任务处理回调（包装默认回调）
            on_idle: 空闲回调（包装默认回调）
            on_evolve: 进化回调（包装默认回调）
            on_shutdown: 停机回调（包装默认回调）
        """
        if not self._initialized:
            self.initialize()

        # 包装自定义回调，保留默认回调逻辑
        if on_task:
            default_task = self._execute_task
            def _wrapped_task(task):
                default_task(task)
                return on_task(task)
            self.loop.on_task(_wrapped_task)
        if on_idle:
            default_idle = self._idle_evolve
            def _wrapped_idle():
                default_idle()
                return on_idle()
            self.loop.on_idle(_wrapped_idle)
        if on_evolve:
            default_evolve = self._periodic_evolve
            def _wrapped_evolve():
                default_evolve()
                return on_evolve()
            self.loop.on_evolve(_wrapped_evolve)
        if on_shutdown:
            default_shutdown = self._shutdown_save
            def _wrapped_shutdown():
                default_shutdown()
                return on_shutdown()
            self.loop.on_shutdown(_wrapped_shutdown)

        logger.info("")
        logger.info("系统进入永恒主循环...")
        logger.info("(Ctrl+C 优雅停机)")
        logger.info("")

        self.loop.run()

    def __repr__(self) -> str:
        return f"EternalSelfAgent(kg={self.knowledge_graph}, queue={self.task_queue})"
