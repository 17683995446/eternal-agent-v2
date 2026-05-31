"""
类型定义模块

公理溯源：记忆公理 - 知识图谱是唯一长期记忆载体，需要精确定义数据结构

设计意图：
- 定义节点（Node）和边（Edge）的核心数据结构
- 定义任务（Task）数据结构
- 提供数据验证和序列化能力
- 零外部依赖，仅使用Python标准库
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid

from constants import (
    NODE_DEFAULT_VALID,
    EDGE_DEFAULT_WEIGHT,
    EDGE_WEIGHT_MIN,
    EDGE_WEIGHT_MAX,
    NodeType,
    RelationType,
    TaskState,
)


@dataclass
class Node:
    """
    知识图谱节点
    
    公理溯源：记忆公理 - 节点代表一次任务、一次认知、一个实体经验
    
    属性：
        name: 节点名称（唯一标识）
        node_type: 节点类型
        created_at: 创建时间
        updated_at: 更新时间
        valid: 有效状态
        attributes: 扩展属性
    """
    name: str
    node_type: str = NodeType.ENTITY
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    valid: bool = NODE_DEFAULT_VALID
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def update_timestamp(self) -> None:
        """更新时间戳"""
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        """从字典创建节点"""
        if not isinstance(data, dict):
            raise TypeError(f"Node.from_dict 期望 dict 类型，实际得到 {type(data).__name__}")
        if 'name' not in data:
            raise ValueError("Node.from_dict 缺少必需字段 'name'")
        return cls(**data)
    
    def __hash__(self) -> int:
        """支持哈希（用于集合操作）"""
        return hash(self.name)
    
    def __eq__(self, other: object) -> bool:
        """支持相等比较"""
        if isinstance(other, Node):
            return self.name == other.name
        return False


@dataclass
class Edge:
    """
    知识图谱边
    
    公理溯源：记忆公理 - 边代表实体之间的关联逻辑，权重是智能经验积累的量化
    
    属性：
        source: 源节点名称
        target: 目标节点名称
        relation: 关系类型
        weight: 权重值（0.0-1.0）
        created_at: 创建时间
        updated_at: 更新时间
        attributes: 扩展属性
    """
    source: str
    target: str
    relation: str = RelationType.RELATED
    weight: float = EDGE_DEFAULT_WEIGHT
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后验证权重范围"""
        self.weight = max(EDGE_WEIGHT_MIN, min(EDGE_WEIGHT_MAX, self.weight))
    
    def update_weight(self, delta: float) -> None:
        """
        更新权重
        
        Args:
            delta: 权重变化量（可正可负）
        """
        self.weight = max(EDGE_WEIGHT_MIN, min(EDGE_WEIGHT_MAX, self.weight + delta))
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Edge':
        """从字典创建边"""
        if not isinstance(data, dict):
            raise TypeError(f"Edge.from_dict 期望 dict 类型，实际得到 {type(data).__name__}")
        if 'source' not in data or 'target' not in data:
            raise ValueError("Edge.from_dict 缺少必需字段 'source' 或 'target'")
        return cls(**data)
    
    def __hash__(self) -> int:
        """支持哈希"""
        return hash((self.source, self.target, self.relation))
    
    def __eq__(self, other: object) -> bool:
        """支持相等比较"""
        if isinstance(other, Edge):
            return (self.source == other.source and 
                    self.target == other.target and 
                    self.relation == other.relation)
        return False


@dataclass
class Task:
    """
    任务数据结构
    
    公理溯源：自驱公理 - 任务是系统自我产生的工作单元
    
    属性：
        name: 任务名称
        state: 任务状态
        priority: 优先级（数值越大优先级越高）
        created_at: 创建时间
        started_at: 开始时间
        completed_at: 完成时间
        result: 执行结果
        error: 错误信息
        attributes: 扩展属性
        # 阶段51: 依赖
        dependencies: 依赖任务列表
        # 阶段52: 超时
        timeout: 超时秒数（0=不限）
        # 阶段53: 重试
        max_retries: 最大重试次数
        retry_count: 已重试次数
        # 阶段58: 循环
        is_cyclic: 是否循环任务
        cyclic_interval: 循环间隔秒数
        # 阶段59: 标签
        tags: 标签列表
    """
    name: str
    task_type: str = "default"
    payload: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: str = TaskState.PENDING
    priority: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    # 阶段51: 任务依赖
    dependencies: List[str] = field(default_factory=list)
    # 阶段52: 超时机制
    timeout: float = 0.0  # 0=不限
    # 阶段53: 重试策略
    max_retries: int = 0
    retry_count: int = 0
    # 阶段58: 循环任务
    is_cyclic: bool = False
    cyclic_interval: float = 0.0  # 秒
    # 阶段59: 标签
    tags: List[str] = field(default_factory=list)
    
    def start(self) -> None:
        """标记任务开始"""
        self.state = TaskState.RUNNING
        self.started_at = datetime.now().isoformat()
    
    def complete(self, result: Optional[str] = None) -> None:
        """标记任务完成"""
        self.state = TaskState.COMPLETED
        self.completed_at = datetime.now().isoformat()
        self.result = result
    
    def fail(self, error: str) -> None:
        """标记任务失败"""
        self.state = TaskState.FAILED
        self.completed_at = datetime.now().isoformat()
        self.error = error
    
    def add_dependency(self, task_name: str) -> None:
        """添加依赖"""
        if task_name not in self.dependencies:
            self.dependencies.append(task_name)
    
    def add_tag(self, tag: str) -> None:
        """添加标签"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def has_tag(self, tag: str) -> bool:
        """检查标签"""
        return tag in self.tags
    
    def is_expired(self) -> bool:
        """检查是否超时"""
        if self.timeout <= 0 or not self.started_at:
            return False
        started = datetime.fromisoformat(self.started_at)
        elapsed = (datetime.now() - started).total_seconds()
        return elapsed > self.timeout
    
    def can_retry(self) -> bool:
        """检查是否可重试"""
        return self.retry_count < self.max_retries
    
    def record_retry(self) -> None:
        """记录一次重试"""
        self.retry_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建任务"""
        if not isinstance(data, dict):
            raise TypeError(f"Task.from_dict 期望 dict 类型，实际得到 {type(data).__name__}")
        if 'name' not in data:
            raise ValueError("Task.from_dict 缺少必需字段 'name'")
        return cls(**data)
    
    def __lt__(self, other: object) -> bool:
        """支持优先级排序（优先级高的排前面）"""
        if not isinstance(other, Task):
            return NotImplemented
        return self.priority > other.priority
    
    def __hash__(self) -> int:
        """支持哈希"""
        return hash(self.name)
    
    def __eq__(self, other: object) -> bool:
        """支持相等比较"""
        if isinstance(other, Task):
            return self.name == other.name
        return False


@dataclass
class ExecutionRecord:
    """
    执行历史记录
    
    阶段54: 追踪每次任务执行
    """
    task_name: str
    state: str = TaskState.PENDING
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionRecord':
        return cls(**data)


@dataclass
class SystemStatus:
    """
    系统状态数据结构
    
    公理溯源：存续公理 - 系统需要持续追踪自身状态
    
    属性：
        state: 当前状态
        run_counter: 运行计数
        last_heartbeat: 最后心跳时间
        consecutive_errors: 连续错误次数
        total_tasks_completed: 总完成任务数
        total_tasks_failed: 总失败任务数
        uptime_seconds: 运行时长（秒）
    """
    state: str = "initializing"
    run_counter: int = 0
    last_heartbeat: Optional[str] = None
    consecutive_errors: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    uptime_seconds: float = 0.0
    start_time: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemStatus':
        """从字典创建状态"""
        return cls(**data)
