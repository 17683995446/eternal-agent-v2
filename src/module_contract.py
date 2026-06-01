"""
模块外包契约规范 - Module Outsourcing Contract

核心理念：
- 每个模块 = 一个公司的交付物
- 契约 = API合同 + 数据格式 + 行为规范
- 集成 = 通过消息总线通信，零直接依赖

公理溯源：
- 契约公理：模块间只通过契约交互，不暴露实现细节
- 隔离公理：每个模块可独立开发、测试、部署
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


# ============================================================
# 第一部分：消息协议（模块间通信标准）
# ============================================================

class MessageType(Enum):
    """消息类型"""
    # 请求-响应
    REQUEST = "request"
    RESPONSE = "response"
    
    # 事件通知
    EVENT = "event"
    
    # 错误
    ERROR = "error"
    
    # 心跳
    HEARTBEAT = "heartbeat"


@dataclass
class Message:
    """
    统一消息格式 - 所有模块间通信必须使用此格式
    
    这是外包架构的核心：模块间不直接调用，而是通过消息通信
    """
    # 消息头
    msg_id: str = ""
    msg_type: MessageType = MessageType.REQUEST
    source_module: str = ""       # 发送方模块名
    target_module: str = ""       # 接收方模块名
    method: str = ""              # 调用的方法名
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 消息体
    params: Dict[str, Any] = field(default_factory=dict)   # 请求参数
    result: Any = None                                           # 响应结果
    error: Optional[str] = None                                 # 错误信息
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.value,
            "source_module": self.source_module,
            "target_module": self.target_module,
            "method": self.method,
            "timestamp": self.timestamp,
            "params": self.params,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        data["msg_type"] = MessageType(data.get("msg_type", "request"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def create_request(cls, source: str, target: str, method: str, 
                       params: Optional[Dict] = None) -> "Message":
        """创建请求消息"""
        import uuid
        return cls(
            msg_id=str(uuid.uuid4())[:8],
            msg_type=MessageType.REQUEST,
            source_module=source,
            target_module=target,
            method=method,
            params=params or {},
        )
    
    @classmethod
    def create_response(cls, request: "Message", result: Any = None, 
                         error: Optional[str] = None) -> "Message":
        """创建响应消息"""
        return cls(
            msg_id=request.msg_id,
            msg_type=MessageType.RESPONSE,
            source_module=request.target_module,
            target_module=request.source_module,
            method=request.method,
            result=result,
            error=error,
        )
    
    @classmethod
    def create_event(cls, source: str, event_name: str, 
                     data: Optional[Dict] = None) -> "Message":
        """创建事件消息"""
        import uuid
        return cls(
            msg_id=str(uuid.uuid4())[:8],
            msg_type=MessageType.EVENT,
            source_module=source,
            target_module="*",  # 广播
            method=event_name,
            params=data or {},
        )


# ============================================================
# 第二部分：模块契约（每个公司的交付合同）
# ============================================================

@dataclass
class MethodContract:
    """方法契约 - 定义一个API的输入输出规范"""
    name: str                           # 方法名
    description: str = ""                # 功能描述
    input_schema: Dict[str, Any] = field(default_factory=dict)   # 输入参数规范
    output_schema: Dict[str, Any] = field(default_factory=dict)  # 输出格式规范
    errors: List[str] = field(default_factory=list)              # 可能的错误
    timeout_ms: int = 5000               # 超时时间
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input": self.input_schema,
            "output": self.output_schema,
            "errors": self.errors,
            "timeout_ms": self.timeout_ms,
        }


@dataclass
class EventContract:
    """事件契约 - 定义模块发布/订阅的事件"""
    event_name: str
    description: str = ""
    data_schema: Dict[str, Any] = field(default_factory=dict)
    publisher: str = ""   # 发布方模块
    subscribers: List[str] = field(default_factory=list)  # 订阅方模块
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_name": self.event_name,
            "description": self.description,
            "data": self.data_schema,
            "publisher": self.publisher,
            "subscribers": self.subscribers,
        }


@dataclass
class ModuleContract:
    """
    模块契约 - 一个公司需要交付的完整合同
    
    包含：
    1. 模块信息
    2. 提供的方法（API）
    3. 发布的事件
    4. 订阅的事件
    5. 依赖的其他模块
    """
    # 模块信息
    module_id: str
    module_name: str
    version: str = "1.0.0"
    owner: str = ""  # 开发公司
    description: str = ""
    
    # 契约内容
    methods: List[MethodContract] = field(default_factory=list)
    published_events: List[EventContract] = field(default_factory=list)
    subscribed_events: List[EventContract] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "module_name": self.module_name,
            "version": self.version,
            "owner": self.owner,
            "description": self.description,
            "methods": [m.to_dict() for m in self.methods],
            "published_events": [e.to_dict() for e in self.published_events],
            "subscribed_events": [e.to_dict() for e in self.subscribed_events],
            "dependencies": self.dependencies,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================
# 第三部分：模块适配器（外包模块接入标准）
# ============================================================

class IOutsourcedModule(ABC):
    """
    外包模块接口 - 所有外包公司必须实现
    
    这是外包架构的接入标准：
    - 公司A实现此接口 → 交付 knowledge_graph.dll/.so/.py
    - 系统通过消息总线调用 → 零代码级依赖
    """
    
    @abstractmethod
    def get_contract(self) -> ModuleContract:
        """
        返回模块契约
        
        系统启动时调用，用于：
        1. 验证模块是否符合合同
        2. 注册API和事件
        3. 检查依赖是否满足
        """
        pass
    
    @abstractmethod
    def handle_message(self, message: Message) -> Message:
        """
        处理消息
        
        这是模块的唯一入口：
        - 所有调用通过消息传入
        - 所有结果通过消息返回
        - 模块内部自行实现业务逻辑
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict: {"healthy": bool, "details": {...}}
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """优雅关闭"""
        pass


class ModuleAdapter:
    """
    模块适配器 - 将外包模块接入消息总线
    
    作用：
    1. 接收消息 → 路由到正确的方法
    2. 调用方法 → 包装为消息返回
    3. 隔离实现 → 系统不直接调用模块代码
    """
    
    def __init__(self, module: IOutsourcedModule):
        self._module = module
        self._contract = module.get_contract()
        self._method_map: Dict[str, MethodContract] = {}
        
        # 构建方法映射
        for method in self._contract.methods:
            self._method_map[method.name] = method
    
    def handle_message(self, message: Message) -> Message:
        """处理消息"""
        if message.msg_type == MessageType.HEARTBEAT:
            health = self._module.health_check()
            return Message.create_response(message, result=health)
        
        if message.msg_type == MessageType.REQUEST:
            return self._handle_request(message)
        
        return Message.create_response(message, error="不支持的消息类型")
    
    def _handle_request(self, message: Message) -> Message:
        """处理请求"""
        method_name = message.method
        
        if method_name not in self._method_map:
            return Message.create_response(
                message, 
                error=f"方法不存在: {method_name}"
            )
        
        try:
            result = self._module.handle_message(message)
            return Message.create_response(message, result=result)
        except Exception as e:
            return Message.create_response(
                message, 
                error=f"执行失败: {str(e)}"
            )
    
    @property
    def contract(self) -> ModuleContract:
        return self._contract


# ============================================================
# 第四部分：消息总线（模块间通信基础设施）
# ============================================================

class MessageBus:
    """
    消息总线 - 模块间通信的唯一通道
    
    职责：
    1. 路由消息到目标模块
    2. 广播事件到订阅者
    3. 超时管理
    4. 错误处理
    """
    
    def __init__(self):
        self._adapters: Dict[str, ModuleAdapter] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._message_log: List[Dict] = []
    
    def register_module(self, module: IOutsourcedModule) -> bool:
        """注册外包模块"""
        contract = module.get_contract()
        adapter = ModuleAdapter(module)
        self._adapters[contract.module_id] = adapter
        return True
    
    def send(self, message: Message, timeout_ms: int = 5000) -> Optional[Message]:
        """
        发送消息（同步）
        
        Args:
            message: 消息
            timeout_ms: 超时
            
        Returns:
            Message: 响应消息
        """
        target = message.target_module
        
        if target not in self._adapters:
            return Message.create_response(
                message, 
                error=f"模块不存在: {target}"
            )
        
        adapter = self._adapters[target]
        response = adapter.handle_message(message)
        
        self._log_message(message)
        self._log_message(response)
        
        return response
    
    def publish(self, event: Message) -> int:
        """
        发布事件（广播）
        
        Returns:
            int: 处理数量
        """
        count = 0
        event_name = event.method
        
        for module_id, adapter in self._adapters.items():
            if module_id != event.source_module:
                try:
                    adapter.handle_message(event)
                    count += 1
                except Exception:
                    pass
        
        self._log_message(event)
        return count
    
    def _log_message(self, message: Message) -> None:
        """记录消息日志"""
        self._message_log.append(message.to_dict())
        if len(self._message_log) > 1000:
            self._message_log = self._message_log[-500:]
    
    def get_status(self) -> Dict[str, Any]:
        """获取总线状态"""
        return {
            "registered_modules": list(self._adapters.keys()),
            "message_count": len(self._message_log),
        }


# ============================================================
# 第五部分：契约验证器
# ============================================================

class ContractValidator:
    """
    契约验证器 - 验证模块是否符合合同
    
    在模块接入时自动检查：
    1. 方法是否完整实现
    2. 事件是否符合格式
    3. 依赖是否满足
    """
    
    def __init__(self, bus: MessageBus):
        self._bus = bus
    
    def validate(self, module: IOutsourcedModule) -> Dict[str, Any]:
        """
        验证模块契约
        
        Returns:
            Dict: {"valid": bool, "errors": [...], "warnings": [...]}
        """
        contract = module.get_contract()
        errors = []
        warnings = []
        
        # 检查方法
        for method in contract.methods:
            test_msg = Message.create_request(
                source="validator",
                target=contract.module_id,
                method=method.name,
                params=self._generate_test_params(method.input_schema)
            )
            
            try:
                response = module.handle_message(test_msg)
                if response.error:
                    errors.append(f"方法 {method.name} 返回错误: {response.error}")
            except Exception as e:
                errors.append(f"方法 {method.name} 异常: {str(e)}")
        
        # 检查依赖
        for dep in contract.dependencies:
            if dep not in self._bus._adapters:
                warnings.append(f"依赖模块未注册: {dep}")
        
        # 检查健康
        try:
            health = module.health_check()
            if not health.get("healthy", False):
                errors.append(f"健康检查失败: {health}")
        except Exception as e:
            errors.append(f"健康检查异常: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "module": contract.module_id,
            "errors": errors,
            "warnings": warnings,
        }
    
    def _generate_test_params(self, schema: Dict) -> Dict:
        """根据schema生成测试参数"""
        if not schema:
            return {}
        return {"_test": True}
