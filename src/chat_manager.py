"""
对话管理模块 - 多轮对话上下文管理

公理溯源：
- 记忆公理：对话历史是短期记忆的一部分
- 连续公理：多轮对话保持上下文连贯性
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

from llm_client import LLMClient, LLMResponse, ChatMessage


@dataclass
class ConversationSession:
    """对话会话"""
    session_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    messages: List[ChatMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
        }


class ChatManager:
    """
    对话管理器
    
    功能：
    - 多会话管理
    - 上下文窗口控制
    - 对话历史持久化
    - 知识图谱联动
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        max_context_length: int = 4096,
        max_turns: int = 20,
    ):
        """
        初始化对话管理器
        
        Args:
            llm_client: LLM客户端
            max_context_length: 最大上下文长度（字符）
            max_turns: 最大对话轮数
        """
        self._llm = llm_client
        self._max_context_length = max_context_length
        self._max_turns = max_turns
        
        # 会话存储
        self._sessions: Dict[str, ConversationSession] = {}
        self._current_session_id: Optional[str] = None
        
        # 全局对话历史（无会话模式）
        self._global_history: List[ChatMessage] = []
    
    def new_session(self, session_id: Optional[str] = None) -> str:
        """
        创建新会话
        
        Args:
            session_id: 会话ID（可选，自动生成）
            
        Returns:
            str: 会话ID
        """
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self._sessions[session_id] = ConversationSession(session_id=session_id)
        self._current_session_id = session_id
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """获取会话"""
        return self._sessions.get(session_id)
    
    def switch_session(self, session_id: str) -> bool:
        """切换会话"""
        if session_id in self._sessions:
            self._current_session_id = session_id
            return True
        return False
    
    def chat(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        发送对话消息
        
        Args:
            user_input: 用户输入
            session_id: 会话ID（可选）
            **kwargs: 传递给LLM的参数
            
        Returns:
            LLMResponse: 模型响应
        """
        # 确定使用的会话
        sid = session_id or self._current_session_id
        
        if sid and sid in self._sessions:
            # 会话模式
            session = self._sessions[sid]
            
            # 添加用户消息
            user_msg = ChatMessage(role="user", content=user_input)
            session.messages.append(user_msg)
            
            # 构建上下文
            context_messages = self._build_context(session.messages)
            
            # 临时替换LLM的历史
            original_history = self._llm._messages
            self._llm._messages = context_messages[:-1]  # 不包括刚添加的用户消息
            
            try:
                response = self._llm.chat(user_input, **kwargs)
                
                # 添加助手消息到会话
                assistant_msg = ChatMessage(role="assistant", content=response.content)
                session.messages.append(assistant_msg)
                
                return response
            finally:
                # 恢复原始历史
                self._llm._messages = original_history
        else:
            # 全局模式
            return self._llm.chat(user_input, **kwargs)
    
    def _build_context(self, messages: List[ChatMessage]) -> List[ChatMessage]:
        """
        构建上下文（控制窗口大小）
        
        Args:
            messages: 原始消息列表
            
        Returns:
            List[ChatMessage]: 截断后的消息列表
        """
        # 限制轮数
        if len(messages) > self._max_turns * 2:
            messages = messages[-(self._max_turns * 2):]
        
        # 限制长度
        total_length = sum(len(m.content) for m in messages)
        if total_length > self._max_context_length:
            # 从旧到新移除，直到满足长度限制
            while messages and total_length > self._max_context_length:
                removed = messages.pop(0)
                total_length -= len(removed.content)
        
        return messages
    
    def get_history(self, session_id: Optional[str] = None) -> List[Dict[str, str]]:
        """
        获取对话历史
        
        Args:
            session_id: 会话ID（可选）
            
        Returns:
            List[Dict[str, str]]: 消息列表
        """
        sid = session_id or self._current_session_id
        
        if sid and sid in self._sessions:
            return [m.to_dict() for m in self._sessions[sid].messages]
        else:
            return [m.to_dict() for m in self._global_history]
    
    def summarize_session(self, session_id: Optional[str] = None) -> str:
        """
        总结会话内容
        
        Args:
            session_id: 会话ID
            
        Returns:
            str: 会话总结
        """
        sid = session_id or self._current_session_id
        
        if not sid or sid not in self._sessions:
            return "无会话记录"
        
        session = self._sessions[sid]
        if not session.messages:
            return "会话为空"
        
        # 构建总结提示
        history_text = "\n".join([
            f"{m.role}: {m.content}" 
            for m in session.messages
        ])
        
        summary_prompt = f"""请总结以下对话的关键内容：

{history_text}

请用简洁的语言总结：1. 讨论的主要话题 2. 得出的结论 3. 待解决的问题"""
        
        response = self._llm.chat(summary_prompt)
        return response.content
    
    def export_session(self, session_id: Optional[str] = None) -> str:
        """
        导出会话为JSON
        
        Args:
            session_id: 会话ID
            
        Returns:
            str: JSON字符串
        """
        sid = session_id or self._current_session_id
        
        if sid and sid in self._sessions:
            return json.dumps(self._sessions[sid].to_dict(), ensure_ascii=False, indent=2)
        return "{}"
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        return [
            {
                "session_id": sid,
                "created_at": s.created_at,
                "message_count": len(s.messages),
            }
            for sid, s in self._sessions.items()
        ]
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            if self._current_session_id == session_id:
                self._current_session_id = None
            return True
        return False


def create_chat_manager(api_key: str, **kwargs) -> ChatManager:
    """
    创建对话管理器的便捷函数
    
    Args:
        api_key: LLM API密钥
        **kwargs: 其他参数
        
    Returns:
        ChatManager: 对话管理器实例
    """
    llm = LLMClient(api_key=api_key)
    return ChatManager(llm, **kwargs)
