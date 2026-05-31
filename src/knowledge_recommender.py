"""
知识推荐器模块 — 智能增强层

公理溯源：自驱公理 - 系统主动推荐相关知识

设计意图：
- 基于知识图谱的推荐
- 协同过滤推荐
- 内容相似度推荐
- 混合推荐策略
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from logger import get_logger
from knowledge_graph import KnowledgeGraph
from similarity import SimilarityCalculator

logger = get_logger("KnowledgeRecommender")


class RecommendationType(Enum):
    """推荐类型"""
    RELATED = "related"        # 相关推荐
    SIMILAR = "similar"        # 相似推荐
    TRENDING = "trending"      # 热门推荐
    PERSONALIZED = "personalized"  # 个性化推荐


@dataclass
class Recommendation:
    """推荐结果"""
    node_name: str
    score: float
    recommendation_type: RecommendationType
    reason: str
    metadata: Dict = field(default_factory=dict)


class KnowledgeRecommender:
    """
    知识推荐器
    
    基于知识图谱的智能推荐
    """
    
    def __init__(self, knowledge_graph: Optional[KnowledgeGraph] = None):
        self.kg = knowledge_graph
        self.similarity_calc = SimilarityCalculator(knowledge_graph)
        
        # 用户兴趣模型
        self.user_interests: Dict[str, float] = {}
        
        # 推荐历史
        self.recommendation_history: List[Dict] = []
    
    def recommend_related(self, node_name: str, top_k: int = 5) -> List[Recommendation]:
        """
        推荐相关节点
        
        Args:
            node_name: 目标节点
            top_k: 返回数量
            
        Returns:
            推荐列表
        """
        if not self.kg or not self.kg.has_node(node_name):
            return []
        
        recommendations = []
        
        # 获取直接相关节点
        related = self.kg.get_related_nodes(node_name)
        
        for neighbor, edges in related.items():
            # 计算推荐分数（基于边权重）
            max_weight = max(e.weight for e in edges) if edges else 0
            
            recommendations.append(Recommendation(
                node_name=neighbor,
                score=max_weight,
                recommendation_type=RecommendationType.RELATED,
                reason=f"与 {node_name} 直接关联"
            ))
        
        # 获取二级相关节点
        for neighbor in list(related.keys())[:3]:
            secondary = self.kg.get_related_nodes(neighbor)
            for sec_neighbor, sec_edges in secondary.items():
                if sec_neighbor != node_name and sec_neighbor not in related:
                    # 二级关联分数较低
                    sec_score = max(e.weight for e in sec_edges) * 0.5 if sec_edges else 0
                    
                    recommendations.append(Recommendation(
                        node_name=sec_neighbor,
                        score=sec_score,
                        recommendation_type=RecommendationType.RELATED,
                        reason=f"通过 {neighbor} 与 {node_name} 间接关联"
                    ))
        
        # 排序并返回
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:top_k]
    
    def recommend_similar(self, node_name: str, top_k: int = 5) -> List[Recommendation]:
        """
        推荐相似节点
        
        Args:
            node_name: 目标节点
            top_k: 返回数量
            
        Returns:
            推荐列表
        """
        if not self.kg:
            return []
        
        similar_nodes = self.similarity_calc.find_similar_nodes(node_name, top_k)
        
        recommendations = [
            Recommendation(
                node_name=name,
                score=score,
                recommendation_type=RecommendationType.SIMILAR,
                reason=f"与 {node_name} 相似度 {score:.2f}"
            )
            for name, score in similar_nodes
        ]
        
        return recommendations
    
    def recommend_trending(self, top_k: int = 5) -> List[Recommendation]:
        """
        推荐热门节点
        
        Args:
            top_k: 返回数量
            
        Returns:
            推荐列表
        """
        if not self.kg:
            return []
        
        # 计算节点热度（基于连接数）
        node_scores = []
        
        for node_name, node in self.kg._nodes.items():
            # 连接数
            connections = len(self.kg.get_related_nodes(node_name))
            
            # 更新时间（越新越热）
            recency_bonus = 0.1  # 简化处理
            
            score = connections + recency_bonus
            node_scores.append((node_name, score))
        
        # 排序
        node_scores.sort(key=lambda x: x[1], reverse=True)
        
        recommendations = [
            Recommendation(
                node_name=name,
                score=score,
                recommendation_type=RecommendationType.TRENDING,
                reason="热门知识"
            )
            for name, score in node_scores[:top_k]
        ]
        
        return recommendations
    
    def recommend_personalized(self, user_id: str = "default", top_k: int = 5) -> List[Recommendation]:
        """
        个性化推荐
        
        Args:
            user_id: 用户ID
            top_k: 返回数量
            
        Returns:
            推荐列表
        """
        if not self.kg:
            return []
        
        # 获取用户兴趣
        interests = self.user_interests.get(user_id, {})
        
        if not interests:
            # 新用户，返回热门推荐
            return self.recommend_trending(top_k)
        
        recommendations = []
        
        # 基于兴趣推荐
        for interest_node, interest_score in sorted(interests.items(), key=lambda x: x[1], reverse=True)[:3]:
            related = self.recommend_related(interest_node, top_k=3)
            for rec in related:
                # 调整分数
                rec.score *= interest_score
                rec.recommendation_type = RecommendationType.PERSONALIZED
                rec.reason = f"基于您对 {interest_node} 的兴趣"
                recommendations.append(rec)
        
        # 去重并排序
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec.node_name not in seen:
                seen.add(rec.node_name)
                unique_recommendations.append(rec)
        
        unique_recommendations.sort(key=lambda r: r.score, reverse=True)
        return unique_recommendations[:top_k]
    
    def update_user_interest(self, user_id: str, node_name: str, interaction_type: str = "view"):
        """
        更新用户兴趣
        
        Args:
            user_id: 用户ID
            node_name: 节点名称
            interaction_type: 交互类型 (view, like, share, etc.)
        """
        if user_id not in self.user_interests:
            self.user_interests[user_id] = {}
        
        # 根据交互类型设置权重
        weights = {
            "view": 0.1,
            "like": 0.3,
            "share": 0.5,
            "create": 0.8,
        }
        
        weight = weights.get(interaction_type, 0.1)
        
        # 更新兴趣分数
        current = self.user_interests[user_id].get(node_name, 0)
        self.user_interests[user_id][node_name] = current + weight
        
        logger.debug(f"更新用户兴趣: {user_id} -> {node_name} (+{weight})")
    
    def get_recommendations(self, context: str = "", top_k: int = 5) -> List[Recommendation]:
        """
        获取综合推荐
        
        Args:
            context: 上下文（可选节点名）
            top_k: 返回数量
            
        Returns:
            推荐列表
        """
        all_recommendations = []
        
        # 1. 相关推荐
        if context and self.kg and self.kg.has_node(context):
            all_recommendations.extend(self.recommend_related(context, top_k=3))
        
        # 2. 热门推荐
        all_recommendations.extend(self.recommend_trending(top_k=3))
        
        # 3. 个性化推荐
        all_recommendations.extend(self.recommend_personalized(top_k=3))
        
        # 去重
        seen = set()
        unique = []
        for rec in all_recommendations:
            if rec.node_name not in seen:
                seen.add(rec.node_name)
                unique.append(rec)
        
        # 排序
        unique.sort(key=lambda r: r.score, reverse=True)
        
        return unique[:top_k]


def get_recommendations(kg: KnowledgeGraph, context: str = "", top_k: int = 5) -> List[Recommendation]:
    """获取推荐（便捷函数）"""
    recommender = KnowledgeRecommender(kg)
    return recommender.get_recommendations(context, top_k)
