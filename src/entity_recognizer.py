"""
实体识别器模块 — 智能增强层

公理溯源：记忆公理 - 从文本中识别实体并结构化存储

设计意图：
- 命名实体识别（NER）
- 实体类型分类
- 实体链接到知识图谱
- 零外部依赖，基于规则实现
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from logger import get_logger
from knowledge_graph import KnowledgeGraph
from nlp_processor import NLPProcessor, get_nlp_processor

logger = get_logger("EntityRecognizer")


class EntityType(Enum):
    """实体类型"""
    PERSON = "person"           # 人物
    ORGANIZATION = "organization"  # 组织
    LOCATION = "location"       # 地点
    DATE = "date"              # 日期
    TIME = "time"              # 时间
    MONEY = "money"            # 金额
    PERCENT = "percent"        # 百分比
    PRODUCT = "product"        # 产品
    TECHNOLOGY = "technology"  # 技术
    CONCEPT = "concept"        # 概念
    UNKNOWN = "unknown"        # 未知


@dataclass
class Entity:
    """实体"""
    text: str
    entity_type: EntityType
    start: int
    end: int
    confidence: float = 1.0
    normalized: str = ""  # 标准化形式
    metadata: Dict = field(default_factory=dict)


class EntityRecognizer:
    """
    实体识别器
    
    基于规则的命名实体识别
    """
    
    def __init__(self, knowledge_graph: Optional[KnowledgeGraph] = None):
        self.kg = knowledge_graph
        self.nlp = get_nlp_processor()
        
        # 实体模式
        self._patterns = self._build_patterns()
        
        # 已知实体词典
        self._entity_dict: Dict[str, EntityType] = {}
        
        # 从知识图谱加载已知实体
        if self.kg:
            self._load_entities_from_kg()
    
    def _build_patterns(self) -> Dict[EntityType, List[re.Pattern]]:
        """构建实体识别模式"""
        patterns = {
            # 日期模式
            EntityType.DATE: [
                re.compile(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?'),
                re.compile(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}'),
                re.compile(r'\d{4}年\d{1,2}月\d{1,2}日'),
            ],
            # 时间模式
            EntityType.TIME: [
                re.compile(r'\d{1,2}:\d{2}(:\d{2})?'),
                re.compile(r'\d{1,2}[点时]\d{1,2}分?'),
            ],
            # 金额模式
            EntityType.MONEY: [
                re.compile(r'[¥$€£]\s*\d+(?:\.\d{2})?'),
                re.compile(r'\d+(?:\.\d{2})?\s*[元美欧英]元?'),
                re.compile(r'\d+(?:\.\d{2})?\s*(?:万|亿|million|billion)'),
            ],
            # 百分比模式
            EntityType.PERCENT: [
                re.compile(r'\d+(?:\.\d+)?\s*[%％]'),
            ],
            # 邮箱
            EntityType.PERSON: [
                re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            ],
            # URL
            EntityType.TECHNOLOGY: [
                re.compile(r'https?://[^\s]+'),
                re.compile(r'github\.com/[^\s]+'),
            ],
        }
        return patterns
    
    def _load_entities_from_kg(self):
        """从知识图谱加载已知实体"""
        if not self.kg:
            return
        
        for node_name, node in self.kg._nodes.items():
            node_type = node.node_type.lower()
            
            # 映射节点类型到实体类型
            type_mapping = {
                "entity": EntityType.CONCEPT,
                "concept": EntityType.CONCEPT,
                "technology": EntityType.TECHNOLOGY,
                "product": EntityType.PRODUCT,
                "person": EntityType.PERSON,
                "organization": EntityType.ORGANIZATION,
                "location": EntityType.LOCATION,
            }
            
            entity_type = type_mapping.get(node_type, EntityType.UNKNOWN)
            self._entity_dict[node_name.lower()] = entity_type
    
    def add_known_entity(self, name: str, entity_type: EntityType):
        """添加已知实体"""
        self._entity_dict[name.lower()] = entity_type

    def _recognize_by_patterns(self, text: str) -> List[Entity]:
        """基于模式识别（辅助方法）"""
        entities = []
        for entity_type, patterns in self._patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    entities.append(Entity(
                        text=match.group(),
                        entity_type=entity_type,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.9
                    ))
        return entities

    def _recognize_by_dict(self, text: str) -> List[Entity]:
        """基于词典识别（辅助方法）"""
        entities = []
        text_lower = text.lower()
        for entity_name, entity_type in self._entity_dict.items():
            start = 0
            while True:
                pos = text_lower.find(entity_name, start)
                if pos == -1:
                    break
                end = pos + len(entity_name)
                entities.append(Entity(
                    text=text[pos:end],
                    entity_type=entity_type,
                    start=pos,
                    end=end,
                    confidence=0.8
                ))
                start = end
        return entities

    def _recognize_proper_nouns(self, text: str) -> List[Entity]:
        """识别专有名词（辅助方法）"""
        entities = []
        tokens = self.nlp.tokenize(text)
        for token in tokens:
            if token.pos == "ENGLISH" and len(token.text) > 1:
                if token.text[0].isupper():
                    if token.text.lower() not in self._entity_dict:
                        entities.append(Entity(
                            text=token.text,
                            entity_type=EntityType.UNKNOWN,
                            start=token.start,
                            end=token.end,
                            confidence=0.6
                        ))
        return entities

    def recognize(self, text: str) -> List[Entity]:
        """
        识别文本中的实体
        
        Args:
            text: 输入文本
            
        Returns:
            实体列表
        """
        entities = []
        
        # 1. 基于模式识别
        entities.extend(self._recognize_by_patterns(text))
        
        # 2. 基于词典识别
        entities.extend(self._recognize_by_dict(text))
        
        # 3. 识别专有名词
        entities.extend(self._recognize_proper_nouns(text))
        
        # 去重和排序
        entities = self._deduplicate_entities(entities)
        entities.sort(key=lambda e: e.start)
        
        return entities
    
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """去重实体"""
        seen = set()
        unique = []
        
        for entity in entities:
            key = (entity.start, entity.end)
            if key not in seen:
                seen.add(key)
                unique.append(entity)
        
        return unique
    
    def classify_entity(self, text: str) -> EntityType:
        """
        分类实体类型
        
        Args:
            text: 实体文本
            
        Returns:
            实体类型
        """
        # 检查词典
        if text.lower() in self._entity_dict:
            return self._entity_dict[text.lower()]
        
        # 检查模式
        for entity_type, patterns in self._patterns.items():
            for pattern in patterns:
                if pattern.match(text):
                    return entity_type
        
        return EntityType.UNKNOWN
    
    def link_to_knowledge_graph(self, entity: Entity) -> Optional[str]:
        """
        将实体链接到知识图谱
        
        Args:
            entity: 实体
            
        Returns:
            知识图谱节点名称
        """
        if not self.kg:
            return None
        
        # 查找匹配节点
        node = self.kg.get_node(entity.text)
        if node:
            return entity.text
        
        # 模糊匹配
        for node_name in self.kg._nodes:
            if entity.text.lower() in node_name.lower():
                return node_name
        
        return None
    
    def extract_and_store(self, text: str) -> List[Entity]:
        """
        提取实体并存储到知识图谱
        
        Args:
            text: 输入文本
            
        Returns:
            实体列表
        """
        entities = self.recognize(text)
        
        if self.kg:
            for entity in entities:
                # 创建节点
                node_type = entity.entity_type.value
                self.kg.add_node(
                    entity.text,
                    node_type,
                    {
                        "confidence": entity.confidence,
                        "normalized": entity.normalized,
                        "source_text": text[:100]
                    }
                )
        
        return entities


def recognize_entities(text: str, kg: Optional[KnowledgeGraph] = None) -> List[Entity]:
    """识别实体（便捷函数）"""
    recognizer = EntityRecognizer(kg)
    return recognizer.recognize(text)
