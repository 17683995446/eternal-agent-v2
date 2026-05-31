"""
对话管理器模块 — 智能增强层

公理溯源：自驱公理 - 支持多轮对话交互

设计意图：
- 多轮对话状态管理
- 上下文维护
- 对话历史记录
- 意图跟踪
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from logger import get_logger
from intent_recognizer import IntentRecognizer, Intent, IntentType
from knowledge_graph import KnowledgeGraph

logger = get_logger("DialogManager")


class DialogState(Enum):
    """对话状态"""
    START = "start"          # 开始
    ACTIVE = "active"        # 活跃
    WAITING = "waiting"      # 等待输入
    ENDED = "ended"          # 结束


@dataclass
class Message:
    """消息"""
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    intent: Optional[Intent] = None


@dataclass
class DialogContext:
    """对话上下文"""
    session_id: str
    state: DialogState = DialogState.START
    messages: List[Message] = field(default_factory=list)
    current_intent: Optional[Intent] = None
    slots: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


class DialogManager:
    """
    对话管理器
    
    管理多轮对话
    """
    
    def __init__(self, knowledge_graph: Optional[KnowledgeGraph] = None):
        self.kg = knowledge_graph
        self.intent_recognizer = IntentRecognizer()
        
        # 活跃会话
        self.sessions: Dict[str, DialogContext] = {}
        
        # 最大历史长度
        self.max_history = 100
    
    def start_session(self, session_id: str = None) -> DialogContext:
        """
        开始新会话
        
        Args:
            session_id: 会话ID（可选）
            
        Returns:
            对话上下文
        """
        if session_id is None:
            session_id = f"session_{len(self.sessions)}"
        
        context = DialogContext(
            session_id=session_id,
            state=DialogState.ACTIVE
        )
        
        self.sessions[session_id] = context
        logger.info(f"开始新会话: {session_id}")
        
        return context
    
    def end_session(self, session_id: str):
        """结束会话"""
        if session_id in self.sessions:
            self.sessions[session_id].state = DialogState.ENDED
            logger.info(f"结束会话: {session_id}")
    
    def process_message(self, session_id: str, user_message: str) -> Message:
        """
        处理用户消息
        
        Args:
            session_id: 会话ID
            user_message: 用户消息
            
        Returns:
            助手回复
        """
        context = self.sessions.get(session_id)
        if not context:
            context = self.start_session(session_id)
        
        # 记录用户消息
        user_msg = Message(role="user", content=user_message)
        context.messages.append(user_msg)
        
        # 识别意图
        intent = self.intent_recognizer.recognize(user_message)
        user_msg.intent = intent
        context.current_intent = intent
        
        # 更新槽位
        for slot in intent.slots:
            context.slots[slot.name] = slot.value
        
        # 生成回复
        response = self._generate_response(context, intent)
        
        # 记录助手消息
        assistant_msg = Message(role="assistant", content=response, intent=intent)
        context.messages.append(assistant_msg)
        
        # 限制历史长度
        if len(context.messages) > self.max_history:
            context.messages = context.messages[-self.max_history:]
        
        return assistant_msg
    
    def _generate_response(self, context: DialogContext, intent: Intent) -> str:
        """生成回复"""
        # 根据意图类型生成回复
        if intent.intent_type == IntentType.QUERY:
            return self._handle_query(context, intent)
        elif intent.intent_type == IntentType.CREATE:
            return self._handle_create(context, intent)
        elif intent.intent_type == IntentType.SEARCH:
            return self._handle_search(context, intent)
        elif intent.intent_type == IntentType.RECOMMEND:
            return self._handle_recommend(context, intent)
        elif intent.intent_type == IntentType.EXPLAIN:
            return self._handle_explain(context, intent)
        else:
            return self._handle_unknown(context, intent)
    
    def _handle_query(self, context: DialogContext, intent: Intent) -> str:
        """处理查询意图"""
        entity = self.intent_recognizer.get_slot_value(intent, "entity")
        
        if entity and self.kg:
            node = self.kg.get_node(entity)
            if node:
                return f"找到 '{entity}': 类型为 {node.node_type}"
            else:
                return f"未找到 '{entity}' 的相关信息"
        
        return "请问您想查询什么？"
    
    def _handle_create(self, context: DialogContext, intent: Intent) -> str:
        """处理创建意图"""
        entity = self.intent_recognizer.get_slot_value(intent, "entity")
        
        if entity:
            if self.kg:
                self.kg.add_node(entity, "entity")
                return f"已创建 '{entity}'"
            return f"准备创建 '{entity}'"
        
        return "请问您想创建什么？"
    
    def _handle_search(self, context: DialogContext, intent: Intent) -> str:
        """处理搜索意图"""
        entity = self.intent_recognizer.get_slot_value(intent, "entity")
        
        if entity:
            return f"正在搜索 '{entity}'..."
        
        return "请问您想搜索什么？"
    
    def _handle_recommend(self, context: DialogContext, intent: Intent) -> str:
        """处理推荐意图"""
        return "根据您的兴趣，我推荐以下内容..."
    
    def _handle_explain(self, context: DialogContext, intent: Intent) -> str:
        """处理解释意图"""
        entity = self.intent_recognizer.get_slot_value(intent, "entity")
        
        if entity:
            return f"关于 '{entity}' 的解释..."
        
        return "请问您想了解什么？"
    
    def _handle_unknown(self, context: DialogContext, intent: Intent) -> str:
        """处理未知意图"""
        return "抱歉，我不太理解您的意思。请换一种方式表达？"
    
    def get_context(self, session_id: str) -> Optional[DialogContext]:
        """获取对话上下文"""
        return self.sessions.get(session_id)
    
    def get_history(self, session_id: str, limit: int = 10) -> List[Message]:
        """获取对话历史"""
        context = self.sessions.get(session_id)
        if not context:
            return []
        
        return context.messages[-limit:]
    
    def clear_history(self, session_id: str):
        """清除对话历史"""
        context = self.sessions.get(session_id)
        if context:
            context.messages = []
            context.slots = {}


def create_dialog_manager(kg: Optional[KnowledgeGraph] = None) -> DialogManager:
    """创建对话管理器（便捷函数）"""
    return DialogManager(kg)
