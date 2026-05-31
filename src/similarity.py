"""
相似度计算器模块 — 智能增强层

公理溯源：记忆公理 - 知识关联强度需要量化计算

设计意图：
- 文本相似度计算
- 节点相似度计算
- 语义相似度（基于知识图谱）
- 多维度相似度融合
"""

import math
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from collections import Counter

from logger import get_logger
from knowledge_graph import KnowledgeGraph
from nlp_processor import NLPProcessor, get_nlp_processor

logger = get_logger("SimilarityCalculator")


@dataclass
class SimilarityResult:
    """相似度结果"""
    score: float
    method: str
    details: Dict = None


class SimilarityCalculator:
    """
    相似度计算器
    
    支持多种相似度计算方法
    """
    
    def __init__(self, knowledge_graph: Optional[KnowledgeGraph] = None):
        self.kg = knowledge_graph
        self.nlp = get_nlp_processor()
    
    def text_similarity(self, text1: str, text2: str, method: str = "cosine") -> SimilarityResult:
        """
        计算文本相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            method: 计算方法 (cosine, jaccard, edit_distance)
            
        Returns:
            相似度结果
        """
        if method == "cosine":
            return self._cosine_similarity(text1, text2)
        elif method == "jaccard":
            return self._jaccard_similarity(text1, text2)
        elif method == "edit_distance":
            return self._edit_distance_similarity(text1, text2)
        else:
            return self._cosine_similarity(text1, text2)
    
    def _cosine_similarity(self, text1: str, text2: str) -> SimilarityResult:
        """余弦相似度"""
        tokens1 = self.nlp.remove_stopwords(self.nlp.tokenize(text1))
        tokens2 = self.nlp.remove_stopwords(self.nlp.tokenize(text2))
        
        if not tokens1 or not tokens2:
            return SimilarityResult(score=0.0, method="cosine")
        
        # 词频向量
        words1 = Counter(t.text.lower() for t in tokens1)
        words2 = Counter(t.text.lower() for t in tokens2)
        
        # 所有词
        all_words = set(words1.keys()) | set(words2.keys())
        
        # 余弦相似度
        dot_product = sum(words1.get(w, 0) * words2.get(w, 0) for w in all_words)
        magnitude1 = math.sqrt(sum(v ** 2 for v in words1.values()))
        magnitude2 = math.sqrt(sum(v ** 2 for v in words2.values()))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return SimilarityResult(score=0.0, method="cosine")
        
        score = dot_product / (magnitude1 * magnitude2)
        
        return SimilarityResult(
            score=score,
            method="cosine",
            details={
                "common_words": list(set(words1.keys()) & set(words2.keys())),
                "unique_words_1": len(words1),
                "unique_words_2": len(words2)
            }
        )
    
    def _jaccard_similarity(self, text1: str, text2: str) -> SimilarityResult:
        """Jaccard相似度"""
        tokens1 = set(t.text.lower() for t in self.nlp.tokenize(text1))
        tokens2 = set(t.text.lower() for t in self.nlp.tokenize(text2))
        
        if not tokens1 or not tokens2:
            return SimilarityResult(score=0.0, method="jaccard")
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        score = len(intersection) / len(union) if union else 0.0
        
        return SimilarityResult(
            score=score,
            method="jaccard",
            details={
                "intersection": list(intersection),
                "union_size": len(union)
            }
        )
    
    def _edit_distance_similarity(self, text1: str, text2: str) -> SimilarityResult:
        """编辑距离相似度"""
        # Levenshtein距离
        m, n = len(text1), len(text2)
        
        if m == 0 or n == 0:
            return SimilarityResult(score=0.0, method="edit_distance")
        
        # DP表
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if text1[i - 1] == text2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
        
        distance = dp[m][n]
        max_len = max(m, n)
        score = 1 - (distance / max_len)
        
        return SimilarityResult(
            score=score,
            method="edit_distance",
            details={"edit_distance": distance}
        )
    
    def node_similarity(self, node1_name: str, node2_name: str) -> SimilarityResult:
        """
        计算节点相似度
        
        Args:
            node1_name: 节点1名称
            node2_name: 节点2名称
            
        Returns:
            相似度结果
        """
        if not self.kg:
            return SimilarityResult(score=0.0, method="node")
        
        node1 = self.kg.get_node(node1_name)
        node2 = self.kg.get_node(node2_name)
        
        if not node1 or not node2:
            return SimilarityResult(score=0.0, method="node")
        
        scores = []
        
        # 1. 名称相似度
        name_sim = self._cosine_similarity(node1_name, node2_name).score
        scores.append(("name", name_sim, 0.3))
        
        # 2. 类型相似度
        type_sim = 1.0 if node1.node_type == node2.node_type else 0.0
        scores.append(("type", type_sim, 0.2))
        
        # 3. 属性相似度
        attr_sim = self._attribute_similarity(node1.attributes, node2.attributes)
        scores.append(("attributes", attr_sim, 0.2))
        
        # 4. 邻居相似度
        neighbor_sim = self._neighbor_similarity(node1_name, node2_name)
        scores.append(("neighbors", neighbor_sim, 0.3))
        
        # 加权平均
        total_weight = sum(w for _, _, w in scores)
        weighted_score = sum(s * w for _, s, w in scores) / total_weight
        
        return SimilarityResult(
            score=weighted_score,
            method="node",
            details={name: score for name, score, _ in scores}
        )
    
    def _attribute_similarity(self, attrs1: Dict, attrs2: Dict) -> float:
        """属性相似度"""
        if not attrs1 and not attrs2:
            return 1.0
        if not attrs1 or not attrs2:
            return 0.0
        
        keys1 = set(attrs1.keys())
        keys2 = set(attrs2.keys())
        
        common_keys = keys1 & keys2
        if not common_keys:
            return 0.0
        
        # 比较共同属性的值
        matches = 0
        for key in common_keys:
            if attrs1[key] == attrs2[key]:
                matches += 1
        
        return matches / len(common_keys)
    
    def _neighbor_similarity(self, node1_name: str, node2_name: str) -> float:
        """邻居相似度"""
        if not self.kg:
            return 0.0
        
        neighbors1 = set(self.kg.get_related_nodes(node1_name).keys())
        neighbors2 = set(self.kg.get_related_nodes(node2_name).keys())
        
        if not neighbors1 or not neighbors2:
            return 0.0
        
        intersection = neighbors1 & neighbors2
        union = neighbors1 | neighbors2
        
        return len(intersection) / len(union) if union else 0.0
    
    def find_similar_nodes(self, node_name: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        查找相似节点
        
        Args:
            node_name: 目标节点
            top_k: 返回数量
            
        Returns:
            相似节点列表 [(节点名, 相似度), ...]
        """
        if not self.kg:
            return []
        
        similarities = []
        
        for other_name in self.kg._nodes:
            if other_name != node_name:
                sim = self.node_similarity(node_name, other_name)
                similarities.append((other_name, sim.score))
        
        # 排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def find_similar_texts(self, query: str, texts: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        """
        在文本列表中查找相似文本
        
        Args:
            query: 查询文本
            texts: 文本列表
            top_k: 返回数量
            
        Returns:
            相似文本列表 [(文本, 相似度), ...]
        """
        similarities = []
        
        for text in texts:
            sim = self.text_similarity(query, text)
            similarities.append((text, sim.score))
        
        # 排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]


def calculate_similarity(text1: str, text2: str, method: str = "cosine") -> float:
    """计算文本相似度（便捷函数）"""
    calc = SimilarityCalculator()
    result = calc.text_similarity(text1, text2, method)
    return result.score
