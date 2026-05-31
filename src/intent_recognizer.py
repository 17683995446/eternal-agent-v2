"""
意图识别器模块 — 智能增强层

公理溯源：自驱公理 - 理解用户意图以更好地服务

设计意图：
- 用户意图分类
- 意图槽位提取
- 多意图识别
- 意图置信度计算
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from logger import get_logger
from nlp_processor import NLPProcessor, get_nlp_processor

logger = get_logger("IntentRecognizer")


class IntentType(Enum):
    """意图类型"""
    QUERY = "query"              # 查询
    CREATE = "create"            # 创建
    UPDATE = "update"            # 更新
    DELETE = "delete"            # 删除
    SEARCH = "search"            # 搜索
    RECOMMEND = "recommend"      # 推荐
    EXPLAIN = "explain"          # 解释
    COMPARE = "compare"          # 比较
    UNKNOWN = "unknown"          # 未知


@dataclass
class Slot:
    """槽位"""
    name: str
    value: str
    confidence: float = 1.0


@dataclass
class Intent:
    """意图"""
    intent_type: IntentType
    confidence: float
    slots: List[Slot] = field(default_factory=list)
    original_text: str = ""
    normalized_text: str = ""


class IntentRecognizer:
    """
    意图识别器
    
    基于规则的意图识别
    """
    
    def __init__(self):
        self.nlp = get_nlp_processor()
        
        # 意图模式
        self._intent_patterns = self._build_intent_patterns()
        
        # 槽位模式
        self._slot_patterns = self._build_slot_patterns()
    
    def _build_intent_patterns(self) -> Dict[IntentType, List[str]]:
        """构建意图模式"""
        return {
            IntentType.QUERY: [
                r'什么是', r'是什么', r'查询', r'查找', r'搜索',
                r'what is', r'find', r'search', r'query',
                r'多少', r'how many', r'how much',
            ],
            IntentType.CREATE: [
                r'创建', r'添加', r'新增', r'建立', r'生成',
                r'create', r'add', r'new', r'make',
            ],
            IntentType.UPDATE: [
                r'更新', r'修改', r'编辑', r'改变',
                r'update', r'modify', r'edit', r'change',
            ],
            IntentType.DELETE: [
                r'删除', r'移除', r'清除', r'去掉',
                r'delete', r'remove', r'clear',
            ],
            IntentType.SEARCH: [
                r'找', r'寻找', r'搜', r'检索',
                r'search', r'find', r'look for',
            ],
            IntentType.RECOMMEND: [
                r'推荐', r'建议', r'介绍', r'有什么好',
                r'recommend', r'suggest', r'advice',
            ],
            IntentType.EXPLAIN: [
                r'解释', r'说明', r'为什么', r'怎么',
                r'explain', r'why', r'how',
            ],
            IntentType.COMPARE: [
                r'比较', r'对比', r'区别', r'差异',
                r'compare', r'difference', r'vs',
            ],
        }
    
    def _build_slot_patterns(self) -> Dict[str, re.Pattern]:
        """构建槽位模式"""
        return {
            "entity": re.compile(r'["\']([^"\']+)["\']|「([^」]+)」'),
            "number": re.compile(r'\d+(?:\.\d+)?'),
            "date": re.compile(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?'),
            "type": re.compile(r'(节点|边|关系|属性|node|edge|relation|attribute)'),
        }
    
    def recognize(self, text: str) -> Intent:
        """
        识别意图
        
        Args:
            text: 输入文本
            
        Returns:
            意图对象
        """
        text_lower = text.lower()
        
        # 计算各意图的匹配分数
        intent_scores: Dict[IntentType, float] = {}
        
        for intent_type, patterns in self._intent_patterns.items():
            score = 0.0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 1.0
            
            if score > 0:
                intent_scores[intent_type] = score / len(patterns)
        
        # 选择最高分的意图
        if not intent_scores:
            return Intent(
                intent_type=IntentType.UNKNOWN,
                confidence=0.0,
                original_text=text
            )
        
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        
        # 提取槽位
        slots = self._extract_slots(text)
        
        # 归一化文本
        normalized = self._normalize_text(text)
        
        return Intent(
            intent_type=best_intent[0],
            confidence=min(1.0, best_intent[1] * 2),  # 放大置信度
            slots=slots,
            original_text=text,
            normalized_text=normalized
        )
    
    def _extract_slots(self, text: str) -> List[Slot]:
        """提取槽位"""
        slots = []
        
        for slot_name, pattern in self._slot_patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                # 处理元组匹配
                value = match if isinstance(match, str) else match[0] or match[1]
                if value:
                    slots.append(Slot(
                        name=slot_name,
                        value=value,
                        confidence=0.8
                    ))
        
        return slots
    
    def _normalize_text(self, text: str) -> str:
        """归一化文本"""
        # 转小写
        text = text.lower()
        
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def get_slot_value(self, intent: Intent, slot_name: str) -> Optional[str]:
        """
        获取槽位值
        
        Args:
            intent: 意图对象
            slot_name: 槽位名
            
        Returns:
            槽位值
        """
        for slot in intent.slots:
            if slot.name == slot_name:
                return slot.value
        return None
    
    def classify_intent_type(self, text: str) -> IntentType:
        """
        快速分类意图类型
        
        Args:
            text: 输入文本
            
        Returns:
            意图类型
        """
        intent = self.recognize(text)
        return intent.intent_type


def recognize_intent(text: str) -> Intent:
    """识别意图（便捷函数）"""
    recognizer = IntentRecognizer()
    return recognizer.recognize(text)
