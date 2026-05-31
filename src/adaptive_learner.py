"""
自适应学习器模块 — 智能增强层

公理溯源：自驱公理 - 系统从反馈中学习和进化

设计意图：
- 从用户反馈中学习
- 调整知识权重
- 优化推荐策略
- 记录学习历史
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from logger import get_logger
from knowledge_graph import KnowledgeGraph
from utils import now_iso, read_json, write_json
from constants import PROJECT_ROOT

logger = get_logger("AdaptiveLearner")


class FeedbackType(Enum):
    """反馈类型"""
    POSITIVE = "positive"      # 正面反馈
    NEGATIVE = "negative"      # 负面反馈
    NEUTRAL = "neutral"        # 中性反馈
    CORRECTION = "correction"  # 纠正


@dataclass
class Feedback:
    """反馈"""
    id: str
    feedback_type: FeedbackType
    target: str  # 反馈目标（节点名、关系等）
    content: str  # 反馈内容
    score: float  # 分数 (-1 到 1)
    timestamp: str = field(default_factory=now_iso)
    metadata: Dict = field(default_factory=dict)


@dataclass
class LearningRecord:
    """学习记录"""
    timestamp: str
    action: str
    before: Any
    after: Any
    reason: str


class AdaptiveLearner:
    """
    自适应学习器
    
    从反馈中学习，优化知识图谱
    """
    
    def __init__(self, knowledge_graph: Optional[KnowledgeGraph] = None):
        self.kg = knowledge_graph
        self.feedbacks: List[Feedback] = []
        self.learning_records: List[LearningRecord] = []
        self.learning_rate = 0.1  # 学习率
        
        # 统计信息
        self.stats = {
            "total_feedbacks": 0,
            "positive_count": 0,
            "negative_count": 0,
            "corrections_count": 0,
        }
    
    def record_feedback(self, feedback_type: FeedbackType, target: str, 
                        content: str, score: float, metadata: Dict = None) -> Feedback:
        """
        记录反馈
        
        Args:
            feedback_type: 反馈类型
            target: 目标
            content: 内容
            score: 分数
            metadata: 元数据
            
        Returns:
            反馈对象
        """
        feedback = Feedback(
            id=f"fb_{len(self.feedbacks)}",
            feedback_type=feedback_type,
            target=target,
            content=content,
            score=max(-1.0, min(1.0, score)),  # 限制在 -1 到 1
            metadata=metadata or {}
        )
        
        self.feedbacks.append(feedback)
        
        # 更新统计
        self.stats["total_feedbacks"] += 1
        if feedback_type == FeedbackType.POSITIVE:
            self.stats["positive_count"] += 1
        elif feedback_type == FeedbackType.NEGATIVE:
            self.stats["negative_count"] += 1
        elif feedback_type == FeedbackType.CORRECTION:
            self.stats["corrections_count"] += 1
        
        logger.info(f"记录反馈: {feedback_type.value} -> {target} (分数: {score})")
        
        return feedback
    
    def learn_from_feedback(self, feedback: Feedback) -> bool:
        """
        从反馈学习
        
        Args:
            feedback: 反馈对象
            
        Returns:
            是否成功学习
        """
        if not self.kg:
            logger.warning("知识图谱未初始化，无法学习")
            return False
        
        target = feedback.target
        
        # 检查目标是否在知识图谱中
        if not self.kg.has_node(target):
            logger.warning(f"目标节点不存在: {target}")
            return False
        
        # 根据反馈类型调整
        if feedback.feedback_type == FeedbackType.POSITIVE:
            return self._apply_positive_feedback(target, feedback.score)
        elif feedback.feedback_type == FeedbackType.NEGATIVE:
            return self._apply_negative_feedback(target, feedback.score)
        elif feedback.feedback_type == FeedbackType.CORRECTION:
            return self._apply_correction(target, feedback)
        
        return True
    
    def _apply_positive_feedback(self, target: str, score: float) -> bool:
        """应用正面反馈"""
        # 增加相关边的权重
        related = self.kg.get_related_nodes(target)
        
        for neighbor, edges in related.items():
            for edge in edges:
                old_weight = edge.weight
                new_weight = min(1.0, old_weight + self.learning_rate * score)
                
                # 记录学习
                self._record_learning(
                    action="weight_increase",
                    before=old_weight,
                    after=new_weight,
                    reason=f"positive_feedback_{target}"
                )
                
                # 更新权重
                edge.weight = new_weight
        
        logger.info(f"正面反馈学习完成: {target}")
        return True
    
    def _apply_negative_feedback(self, target: str, score: float) -> bool:
        """应用负面反馈"""
        # 减少相关边的权重
        related = self.kg.get_related_nodes(target)
        
        for neighbor, edges in related.items():
            for edge in edges:
                old_weight = edge.weight
                new_weight = max(0.0, old_weight + self.learning_rate * score)  # score 是负数
                
                # 记录学习
                self._record_learning(
                    action="weight_decrease",
                    before=old_weight,
                    after=new_weight,
                    reason=f"negative_feedback_{target}"
                )
                
                # 更新权重
                edge.weight = new_weight
        
        logger.info(f"负面反馈学习完成: {target}")
        return True
    
    def _apply_correction(self, target: str, feedback: Feedback) -> bool:
        """应用纠正"""
        correction_data = feedback.metadata.get("correction", {})
        
        # 更新节点属性
        node = self.kg.get_node(target)
        if node and correction_data:
            old_attrs = dict(node.attributes)
            
            for key, value in correction_data.items():
                node.attributes[key] = value
            
            # 记录学习
            self._record_learning(
                action="attribute_correction",
                before=old_attrs,
                after=node.attributes,
                reason=f"correction_{target}"
            )
        
        logger.info(f"纠正学习完成: {target}")
        return True
    
    def _record_learning(self, action: str, before: Any, after: Any, reason: str):
        """记录学习"""
        record = LearningRecord(
            timestamp=now_iso(),
            action=action,
            before=before,
            after=after,
            reason=reason
        )
        self.learning_records.append(record)
    
    def get_feedback_summary(self) -> Dict:
        """获取反馈摘要"""
        return {
            "total": self.stats["total_feedbacks"],
            "positive": self.stats["positive_count"],
            "negative": self.stats["negative_count"],
            "corrections": self.stats["corrections_count"],
            "learning_records": len(self.learning_records),
            "satisfaction_rate": (
                self.stats["positive_count"] / self.stats["total_feedbacks"]
                if self.stats["total_feedbacks"] > 0 else 0.0
            )
        }
    
    def adjust_learning_rate(self, performance: float):
        """
        调整学习率
        
        Args:
            performance: 性能指标 (0-1)
        """
        if performance > 0.8:
            # 性能好，降低学习率
            self.learning_rate = max(0.01, self.learning_rate * 0.9)
        elif performance < 0.5:
            # 性能差，提高学习率
            self.learning_rate = min(0.3, self.learning_rate * 1.1)
        
        logger.info(f"学习率调整为: {self.learning_rate:.3f}")
    
    def save_learning_state(self, filepath: str = None):
        """保存学习状态"""
        if filepath is None:
            filepath = str(PROJECT_ROOT / "data" / "learning_state.json")
        
        state = {
            "learning_rate": self.learning_rate,
            "stats": self.stats,
            "feedbacks": [
                {
                    "id": f.id,
                    "type": f.feedback_type.value,
                    "target": f.target,
                    "content": f.content,
                    "score": f.score,
                    "timestamp": f.timestamp
                }
                for f in self.feedbacks[-100:]  # 只保存最近100条
            ],
            "learning_records": [
                {
                    "timestamp": r.timestamp,
                    "action": r.action,
                    "reason": r.reason
                }
                for r in self.learning_records[-100:]
            ]
        }
        
        write_json(filepath, state)
        logger.info(f"学习状态已保存: {filepath}")
    
    def load_learning_state(self, filepath: str = None):
        """加载学习状态"""
        if filepath is None:
            filepath = str(PROJECT_ROOT / "data" / "learning_state.json")
        
        state = read_json(filepath)
        if not state:
            return
        
        self.learning_rate = state.get("learning_rate", 0.1)
        self.stats = state.get("stats", self.stats)
        
        # 恢复反馈
        for fb_data in state.get("feedbacks", []):
            feedback = Feedback(
                id=fb_data["id"],
                feedback_type=FeedbackType(fb_data["type"]),
                target=fb_data["target"],
                content=fb_data["content"],
                score=fb_data["score"],
                timestamp=fb_data["timestamp"]
            )
            self.feedbacks.append(feedback)
        
        logger.info(f"学习状态已加载: {len(self.feedbacks)} 条反馈")


def create_feedback(feedback_type: str, target: str, content: str, 
                   score: float, metadata: Dict = None) -> Feedback:
    """创建反馈（便捷函数）"""
    fb_type = FeedbackType(feedback_type)
    learner = AdaptiveLearner()
    return learner.record_feedback(fb_type, target, content, score, metadata)
