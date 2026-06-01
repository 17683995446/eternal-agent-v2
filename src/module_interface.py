"""
模块接口规范 - Module Interface Specification

基于SOLID原则定义模块边界：
- S (单一职责): 每个模块只做一件事
- O (开闭原则): 对扩展开放，对修改关闭
- L (里氏替换): 子类可替换父类
- I (接口隔离): 接口最小化
- D (依赖倒置): 依赖抽象而非具体

公理溯源：
- 边界公理：模块边界 = 功能边界 = 责任边界
- 契约公理：模块间通过接口通信，不直接依赖实现
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ModuleState(Enum):
    """模块状态"""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class ModulePriority(Enum):
    """模块优先级（初始化顺序）"""
    CRITICAL = 0    # 必须最先初始化（logger, exceptions）
    HIGH = 1        # 高优先级（config, constants）
    NORMAL = 2      # 正常优先级（核心业务）
    LOW = 3         # 低优先级（工具类）
    OPTIONAL = 4    # 可选模块


@dataclass
class ModuleInfo:
    """模块元信息"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    priority: ModulePriority = ModulePriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)  # 提供的接口
    state: ModuleState = ModuleState.CREATED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "priority": self.priority.name,
            "dependencies": self.dependencies,
            "provides": self.provides,
            "state": self.state.value,
        }


@dataclass
class HealthStatus:
    """健康状态"""
    healthy: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "healthy": self.healthy,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class IModule(ABC):
    """
    模块接口 - 所有模块必须实现
    
    这是模块边界的核心契约：
    - 定义了模块的生命周期
    - 定义了模块的能力边界
    - 定义了模块的健康检查
    """
    
    @property
    @abstractmethod
    def info(self) -> ModuleInfo:
        """模块信息"""
        pass
    
    @abstractmethod
    def initialize(self, context: Dict[str, Any]) -> bool:
        """
        初始化模块
        
        Args:
            context: 上下文（包含其他模块的引用）
            
        Returns:
            bool: 是否初始化成功
        """
        pass
    
    @abstractmethod
    def health_check(self) -> HealthStatus:
        """
        健康检查
        
        Returns:
            HealthStatus: 健康状态
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """关闭模块，释放资源"""
        pass


class IServiceModule(IModule):
    """
    服务模块接口 - 提供服务的模块
    
    服务模块特点：
    - 可启动/停止
    - 有运行状态
    - 可处理请求
    """
    
    @abstractmethod
    def start(self) -> bool:
        """启动服务"""
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """停止服务"""
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """是否运行中"""
        pass


class IDataModule(IModule):
    """
    数据模块接口 - 处理数据的模块
    
    数据模块特点：
    - 可读写数据
    - 有持久化能力
    - 支持查询
    """
    
    @abstractmethod
    def read(self, key: str) -> Optional[Any]:
        """读取数据"""
        pass
    
    @abstractmethod
    def write(self, key: str, value: Any) -> bool:
        """写入数据"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除数据"""
        pass
    
    @abstractmethod
    def query(self, condition: Dict[str, Any]) -> List[Any]:
        """查询数据"""
        pass


class IProcessorModule(IModule):
    """
    处理器模块接口 - 处理输入产生输出
    
    处理器特点：
    - 输入→处理→输出
    - 无状态或弱状态
    - 可组合
    """
    
    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """处理数据"""
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """验证输入"""
        pass
    
    @abstractmethod
    def validate_output(self, output_data: Any) -> bool:
        """验证输出"""
        pass


class IEventModule(IModule):
    """
    事件模块接口 - 发布/订阅事件
    
    事件模块特点：
    - 解耦模块间通信
    - 支持异步通知
    - 支持事件过滤
    """
    
    @abstractmethod
    def subscribe(self, event_type: str, handler: callable) -> str:
        """订阅事件，返回订阅ID"""
        pass
    
    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        pass
    
    @abstractmethod
    def publish(self, event_type: str, data: Any) -> int:
        """发布事件，返回处理数量"""
        pass


class ICacheModule(IModule):
    """
    缓存模块接口
    
    缓存特点：
    - 快速读写
    - 支持过期
    - 支持淘汰
    """
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        pass
    
    @abstractmethod
    def invalidate(self, key: str) -> bool:
        """使缓存失效"""
        pass
    
    @abstractmethod
    def clear(self) -> int:
        """清空缓存，返回清除数量"""
        pass


# ============================================================
# 模块边界定义
# ============================================================

@dataclass
class ModuleBoundary:
    """
    模块边界定义
    
    明确模块的：
    - 输入边界：接受什么
    - 输出边界：产生什么
    - 依赖边界：需要什么
    - 能力边界：能做什么
    """
    module_name: str
    inputs: List[str] = field(default_factory=list)      # 输入类型
    outputs: List[str] = field(default_factory=list)     # 输出类型
    dependencies: List[str] = field(default_factory=list) # 依赖模块
    capabilities: List[str] = field(default_factory=list) # 能力列表
    
    def validate(self) -> bool:
        """验证边界定义是否完整"""
        return bool(self.module_name and self.capabilities)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module_name,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "dependencies": self.dependencies,
            "capabilities": self.capabilities,
        }


# ============================================================
# 模块基类 - 提供默认实现
# ============================================================

class ModuleBase(IModule):
    """
    模块基类 - 提供默认实现
    
    继承此类可快速实现模块接口
    """
    
    def __init__(self, name: str, **kwargs):
        self._name = name
        self._state = ModuleState.CREATED
        self._info = ModuleInfo(name=name, **kwargs)
        self._context: Dict[str, Any] = {}
    
    @property
    def info(self) -> ModuleInfo:
        return self._info
    
    @property
    def state(self) -> ModuleState:
        return self._state
    
    def initialize(self, context: Dict[str, Any]) -> bool:
        """默认初始化"""
        self._context = context
        self._state = ModuleState.INITIALIZING
        try:
            # 检查依赖
            for dep in self._info.dependencies:
                if dep not in context:
                    self._state = ModuleState.ERROR
                    return False
            self._state = ModuleState.READY
            return True
        except Exception:
            self._state = ModuleState.ERROR
            return False
    
    def health_check(self) -> HealthStatus:
        """默认健康检查"""
        return HealthStatus(
            healthy=self._state in (ModuleState.READY, ModuleState.RUNNING),
            message=f"State: {self._state.value}",
        )
    
    def shutdown(self) -> None:
        """默认关闭"""
        self._state = ModuleState.SHUTDOWN
    
    def __repr__(self) -> str:
        return f"<{self._name} [{self._state.value}]>"
