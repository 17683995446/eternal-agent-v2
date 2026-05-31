"""
智能摘要器模块 — 智能增强层

公理溯源：记忆公理 - 知识需要被浓缩和提炼

设计意图：
- 知识图谱摘要生成
- 文本摘要生成
- 关键信息提取
- 多维度摘要
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from logger import get_logger
from knowledge_graph import KnowledgeGraph
from nlp_processor import NLPProcessor, get_nlp_processor

logger = get_logger("Summarizer")


@dataclass
class Summary:
    """摘要结果"""
    text: str
    keywords: List[str]
    entities: List[str]
    stats: Dict
    format: str = "text"


class Summarizer:
    """
    智能摘要器
    
    生成知识图谱和文本摘要
    """
    
    def __init__(self, knowledge_graph: Optional[KnowledgeGraph] = None):
        self.kg = knowledge_graph
        self.nlp = get_nlp_processor()
    
    def summarize_text(self, text: str, max_length: int = 200) -> Summary:
        """
        生成文本摘要
        
        Args:
            text: 输入文本
            max_length: 最大长度
            
        Returns:
            摘要结果
        """
        # 提取关键词
        keywords_with_scores = self.nlp.extract_keywords(text, top_n=10)
        keywords = [kw for kw, _ in keywords_with_scores]
        
        # 提取实体
        entities_dict = self.nlp.extract_entities_simple(text)
        entities = []
        for entity_list in entities_dict.values():
            entities.extend(entity_list[:3])
        entities = list(set(entities))[:10]
        
        # 分句
        sentences = self.nlp.split_sentences(text)
        
        # 选择关键句（包含最多关键词的句子）
        if sentences:
            sentence_scores = []
            for sentence in sentences:
                score = sum(1 for kw in keywords if kw.lower() in sentence.lower())
                sentence_scores.append((sentence, score))
            
            # 按分数排序
            sentence_scores.sort(key=lambda x: x[1], reverse=True)
            
            # 选择句子直到达到最大长度
            summary_sentences = []
            current_length = 0
            
            for sentence, _ in sentence_scores:
                if current_length + len(sentence) <= max_length:
                    summary_sentences.append(sentence)
                    current_length += len(sentence)
            
            # 按原顺序排列
            summary_sentences = [s for s in sentences if s in summary_sentences]
            summary_text = "。".join(summary_sentences)
        else:
            summary_text = text[:max_length]
        
        # 统计
        stats = {
            "original_length": len(text),
            "summary_length": len(summary_text),
            "sentence_count": len(sentences),
            "keyword_count": len(keywords),
        }
        
        return Summary(
            text=summary_text,
            keywords=keywords,
            entities=entities,
            stats=stats
        )
    
    def summarize_knowledge_graph(self, focus_node: str = None) -> Summary:
        """
        生成知识图谱摘要
        
        Args:
            focus_node: 焦点节点（可选）
            
        Returns:
            摘要结果
        """
        if not self.kg:
            return Summary(
                text="知识图谱未初始化",
                keywords=[],
                entities=[],
                stats={}
            )
        
        # 获取统计信息
        stats = self.kg.stats()
        
        # 生成摘要文本
        lines = []
        
        # 总体概述
        lines.append(f"知识图谱包含 {stats['node_count']} 个节点和 {stats['edge_count']} 条边。")
        
        # 节点类型分布
        if stats.get('node_types'):
            type_desc = ", ".join(f"{t}: {c}个" for t, c in list(stats['node_types'].items())[:5])
            lines.append(f"节点类型分布: {type_desc}。")
        
        # 焦点节点
        if focus_node and self.kg.has_node(focus_node):
            node = self.kg.get_node(focus_node)
            related = self.kg.get_related_nodes(focus_node)
            
            lines.append(f"焦点节点 '{focus_node}' 是一个 {node.node_type} 类型节点。")
            
            if related:
                related_names = list(related.keys())[:5]
                lines.append(f"它与 {len(related)} 个节点相关，包括: {', '.join(related_names)}。")
        
        # 关键节点（连接数最多的节点）
        node_connections = []
        for node_name in self.kg._nodes:
            connections = len(self.kg.get_related_nodes(node_name))
            node_connections.append((node_name, connections))
        
        node_connections.sort(key=lambda x: x[1], reverse=True)
        
        if node_connections:
            top_nodes = [name for name, _ in node_connections[:5]]
            lines.append(f"核心节点: {', '.join(top_nodes)}。")
        
        summary_text = "\n".join(lines)
        
        # 关键词（节点名）
        keywords = [name for name, _ in node_connections[:10]]
        
        # 实体
        entities = keywords[:5]
        
        return Summary(
            text=summary_text,
            keywords=keywords,
            entities=entities,
            stats=stats
        )
    
    def summarize_node(self, node_name: str) -> Summary:
        """
        生成节点摘要
        
        Args:
            node_name: 节点名称
            
        Returns:
            摘要结果
        """
        if not self.kg or not self.kg.has_node(node_name):
            return Summary(
                text=f"节点 '{node_name}' 不存在",
                keywords=[],
                entities=[],
                stats={}
            )
        
        node = self.kg.get_node(node_name)
        related = self.kg.get_related_nodes(node_name)
        
        # 生成摘要
        lines = [f"'{node_name}' 是一个 {node.node_type} 类型的节点。"]
        
        # 属性
        if node.attributes:
            attr_items = list(node.attributes.items())[:3]
            attr_desc = ", ".join(f"{k}: {v}" for k, v in attr_items)
            lines.append(f"属性: {attr_desc}。")
        
        # 关系
        if related:
            relations = []
            for neighbor, edges in list(related.items())[:5]:
                for edge in edges:
                    relations.append(f"{edge.relation} {neighbor}")
            lines.append(f"关系: {', '.join(relations)}。")
        
        summary_text = "\n".join(lines)
        
        # 关键词
        keywords = [node_name] + list(related.keys())[:5]
        
        return Summary(
            text=summary_text,
            keywords=keywords,
            entities=keywords,
            stats={
                "node_type": node.node_type,
                "attribute_count": len(node.attributes),
                "relation_count": len(related)
            }
        )
    
    def generate_report(self, format: str = "text") -> str:
        """
        生成知识图谱报告
        
        Args:
            format: 输出格式 (text, markdown)
            
        Returns:
            报告文本
        """
        if not self.kg:
            return "知识图谱未初始化"
        
        summary = self.summarize_knowledge_graph()
        
        if format == "markdown":
            lines = [
                "# 知识图谱报告",
                "",
                "## 概述",
                "",
                summary.text,
                "",
                "## 统计信息",
                "",
            ]
            
            for key, value in summary.stats.items():
                lines.append(f"- **{key}**: {value}")
            
            lines.extend([
                "",
                "## 关键节点",
                "",
            ])
            
            for kw in summary.keywords[:10]:
                lines.append(f"- {kw}")
            
            return "\n".join(lines)
        else:
            return summary.text


def summarize(text: str, max_length: int = 200) -> Summary:
    """生成文本摘要（便捷函数）"""
    summarizer = Summarizer()
    return summarizer.summarize_text(text, max_length)


def summarize_knowledge_graph(kg: KnowledgeGraph) -> Summary:
    """生成知识图谱摘要（便捷函数）"""
    summarizer = Summarizer(kg)
    return summarizer.summarize_knowledge_graph()
