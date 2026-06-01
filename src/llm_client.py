"""
LLM客户端模块 - 硅基流动（SiliconFlow）API集成
使用OpenAI兼容格式调用

公理溯源：
- 智能公理：系统具备语言理解和生成能力
- 连接公理：通过标准API与外部LLM服务通信
"""
import json
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any, Generator
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ChatMessage:
    """对话消息"""
    role: str  # system, user, assistant
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    elapsed_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "elapsed_ms": self.elapsed_ms,
        }


class LLMClient:
    """
    硅基流动LLM客户端
    
    使用OpenAI兼容API格式
    支持多轮对话、流式输出、工具调用
    """
    
    # 硅基流动API地址
    DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
    
    # 推荐模型列表（免费/低成本）
    RECOMMENDED_MODELS = [
        "Qwen/Qwen3-8B",                    # 通义千问3 8B (推荐)
        "Qwen/Qwen2.5-7B-Instruct",         # 通义千问2.5 7B
        "THUDM/GLM-4-9B-0414",              # GLM-4 9B
        "deepseek-ai/DeepSeek-V3",          # DeepSeek V3
        "Qwen/Qwen3-14B",                   # 通义千问3 14B
    ]
    
    # 免费模型列表（向后兼容）
    FREE_MODELS = RECOMMENDED_MODELS
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "Qwen/Qwen3-8B",
        timeout: int = 60,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ):
        """
        初始化LLM客户端
        
        Args:
            api_key: 硅基流动API密钥
            base_url: API地址（默认硅基流动）
            model: 模型名称
            timeout: 请求超时时间（秒）
            max_tokens: 最大生成token数
            temperature: 生成温度（0-1）
        """
        self._api_key = api_key
        self._base_url = base_url or self.DEFAULT_BASE_URL
        self._model = model
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._temperature = temperature
        
        # 对话历史
        self._messages: List[ChatMessage] = []
        
        # 系统提示词
        self._system_prompt = "你是一个智能助手，具备知识推理和任务执行能力。"
        
        # 统计信息
        self._stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_errors": 0,
        }
    
    @property
    def model(self) -> str:
        return self._model
    
    @property
    def available_models(self) -> List[str]:
        return self.FREE_MODELS
    
    def set_model(self, model: str) -> None:
        """切换模型"""
        self._model = model
    
    def set_system_prompt(self, prompt: str) -> None:
        """设置系统提示词"""
        self._system_prompt = prompt
        # 清空历史，重新添加系统提示
        self._messages = []
    
    def clear_history(self) -> None:
        """清空对话历史"""
        self._messages = []
    
    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return [m.to_dict() for m in self._messages]
    
    def chat(
        self,
        user_input: str,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        """
        发送对话消息
        
        Args:
            user_input: 用户输入
            stream: 是否流式输出（暂不支持）
            **kwargs: 额外参数
            
        Returns:
            LLMResponse: 模型响应
        """
        import time
        start_time = time.time()
        
        # 添加用户消息
        user_msg = ChatMessage(role="user", content=user_input)
        self._messages.append(user_msg)
        
        # 构建请求
        messages = self._build_messages()
        
        try:
            response = self._call_api(messages, **kwargs)
            elapsed_ms = (time.time() - start_time) * 1000
            
            # 解析响应
            content = response["choices"][0]["message"]["content"]
            usage = response.get("usage", {})
            finish_reason = response["choices"][0].get("finish_reason", "stop")
            
            # 添加助手消息
            assistant_msg = ChatMessage(role="assistant", content=content)
            self._messages.append(assistant_msg)
            
            # 更新统计
            self._stats["total_requests"] += 1
            self._stats["total_tokens"] += usage.get("total_tokens", 0)
            
            return LLMResponse(
                content=content,
                model=self._model,
                usage=usage,
                finish_reason=finish_reason,
                elapsed_ms=elapsed_ms,
            )
            
        except Exception as e:
            self._stats["total_errors"] += 1
            # 移除失败的用户消息
            self._messages.pop()
            raise LLMError(f"LLM调用失败: {e}")
    
    def _build_messages(self) -> List[Dict[str, str]]:
        """构建API请求的消息列表"""
        messages = [{"role": "system", "content": self._system_prompt}]
        messages.extend([m.to_dict() for m in self._messages])
        return messages
    
    def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """调用硅基流动API"""
        url = f"{self._base_url}/chat/completions"
        
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "temperature": kwargs.get("temperature", self._temperature),
        }
        
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise LLMError(f"API错误 {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise LLMError(f"网络错误: {e.reason}")
    
    def stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "model": self._model,
            "message_count": len(self._messages),
        }
    
    def chat_with_context(
        self,
        user_input: str,
        context: Optional[str] = None,
    ) -> LLMResponse:
        """
        带上下文的对话
        
        Args:
            user_input: 用户输入
            context: 额外上下文信息
            
        Returns:
            LLMResponse: 模型响应
        """
        if context:
            enhanced_input = f"【上下文信息】\n{context}\n\n【用户问题】\n{user_input}"
        else:
            enhanced_input = user_input
        
        return self.chat(enhanced_input)
    
    def think(self, task: str) -> str:
        """
        思考模式 - 让模型逐步推理
        
        Args:
            task: 任务描述
            
        Returns:
            str: 推理结果
        """
        think_prompt = f"""请逐步思考以下任务，给出详细的推理过程：

{task}

请按以下格式回答：
1. 分析：理解任务的核心要求
2. 思考：列出解决思路
3. 推理：逐步推导
4. 结论：给出最终答案"""
        
        response = self.chat(think_prompt)
        return response.content
    
    def act(self, instruction: str) -> str:
        """
        行动模式 - 执行具体指令
        
        Args:
            instruction: 执行指令
            
        Returns:
            str: 执行结果
        """
        act_prompt = f"""请执行以下指令：

{instruction}

请直接给出执行结果，不需要解释过程。"""
        
        response = self.chat(act_prompt)
        return response.content


class LLMError(Exception):
    """LLM错误"""
    pass


# 全局默认客户端
_default_client: Optional[LLMClient] = None


def get_llm_client() -> Optional[LLMClient]:
    """获取默认LLM客户端"""
    return _default_client


def init_llm_client(api_key: str, **kwargs) -> LLMClient:
    """
    初始化默认LLM客户端
    
    Args:
        api_key: API密钥
        **kwargs: 其他参数
        
    Returns:
        LLMClient: 客户端实例
    """
    global _default_client
    _default_client = LLMClient(api_key=api_key, **kwargs)
    return _default_client
