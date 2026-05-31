"""
示例2: 智能问答系统

本示例展示如何构建一个简单的智能问答系统：
- 基于知识图谱的问答
- 推理引擎的使用
- 模式匹配和规则应用
- 自然语言查询解析

大事做于细，难事成于易：
- 从简单的问答对开始
- 逐步添加推理能力和上下文理解
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from knowledge_graph import KnowledgeGraph
from reasoning import RuleEngine, PatternMatcher
from query_language import QueryEngine
from models import Node, Edge
from logger import get_logger

logger = get_logger("Example02")


@dataclass
class Question:
    """问题结构"""
    text: str
    question_type: str  # "what", "how", "why", "who", "where"
    subject: Optional[str] = None
    predicate: Optional[str] = None


@dataclass
class Answer:
    """答案结构"""
    text: str
    confidence: float
    sources: List[str]


class SimpleQASystem:
    """
    简单问答系统
    
    基于知识图谱和推理引擎实现基础问答能力
    """
    
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
        self.query_engine = QueryEngine(kg)
        self.rule_engine = RuleEngine(kg)
        self.pattern_matcher = PatternMatcher(kg)
        
        # 初始化知识库
        self._init_knowledge_base()
    
    def _init_knowledge_base(self):
        """初始化问答知识库"""
        # 添加常见概念
        concepts = [
            ("Python", "language", "Python是一种高级编程语言，以简洁易读著称"),
            ("JavaScript", "language", "JavaScript是Web开发的主要编程语言"),
            ("FastAPI", "framework", "FastAPI是一个现代、高性能的Python Web框架"),
            ("React", "framework", "React是Facebook开发的JavaScript UI库"),
            ("PostgreSQL", "database", "PostgreSQL是一个强大的开源关系型数据库"),
            ("Redis", "database", "Redis是一个高性能的内存键值存储"),
            ("Machine Learning", "concept", "机器学习是AI的一个分支，让计算机从数据中学习"),
            ("Deep Learning", "concept", "深度学习使用多层神经网络进行学习"),
        ]
        
        for name, node_type, description in concepts:
            self.kg.add_node(name, node_type, {"description": description})
        
        # 添加关系
        relations = [
            ("Python", "FastAPI", "powers", 0.95),
            ("JavaScript", "React", "powers", 0.90),
            ("FastAPI", "PostgreSQL", "uses", 0.80),
            ("Machine Learning", "Deep Learning", "includes", 0.90),
            ("Python", "Machine Learning", "used_for", 0.85),
        ]
        
        for source, target, relation, weight in relations:
            self.kg.add_edge(source, target, relation, weight)
        
        self.kg.save()
        logger.info("问答知识库初始化完成")
    
    def parse_question(self, question_text: str) -> Question:
        """
        解析问题
        
        Args:
            question_text: 问题文本
            
        Returns:
            解析后的问题结构
        """
        text = question_text.lower().strip()
        
        # 确定问题类型
        if text.startswith("what") or text.startswith("什么是"):
            qtype = "what"
        elif text.startswith("how") or text.startswith("如何"):
            qtype = "how"
        elif text.startswith("why") or text.startswith("为什么"):
            qtype = "why"
        elif text.startswith("who") or text.startswith("谁"):
            qtype = "who"
        elif text.startswith("where") or text.startswith("哪里"):
            qtype = "where"
        else:
            qtype = "general"
        
        # 提取主题（简单实现：查找知识图谱中存在的节点）
        subject = None
        for node in self.kg.get_all_nodes():
            node_name = node.name
            if node_name.lower() in text:
                subject = node_name
                break
        
        return Question(
            text=question_text,
            question_type=qtype,
            subject=subject
        )
    
    def answer(self, question_text: str) -> Answer:
        """
        回答问题
        
        Args:
            question_text: 问题文本
            
        Returns:
            答案结构
        """
        question = self.parse_question(question_text)
        
        if not question.subject:
            return Answer(
                text="抱歉，我无法理解这个问题。请尝试询问知识图谱中存在的概念。",
                confidence=0.0,
                sources=[]
            )
        
        # 根据问题类型选择回答策略
        if question.question_type == "what":
            return self._answer_what(question)
        elif question.question_type == "how":
            return self._answer_how(question)
        elif question.question_type == "why":
            return self._answer_why(question)
        else:
            return self._answer_general(question)
    
    def _answer_what(self, question: Question) -> Answer:
        """回答'是什么'类型的问题"""
        node = self.kg.get_node(question.subject)
        
        if not node:
            return Answer(
                text=f"抱歉，我找不到关于'{question.subject}'的信息。",
                confidence=0.0,
                sources=[]
            )
        
        # 获取描述
        description = node.attributes.get("description", "")
        
        if description:
            answer_text = f"{question.subject}是{description}"
        else:
            answer_text = f"{question.subject}是一个{node.node_type}类型的节点"
        
        # 获取相关关系
        related = self.kg.get_related_nodes(question.subject)
        if related:
            relations = []
            for target, edges in list(related.items())[:3]:
                for edge in edges:
                    relations.append(f"{edge.relation} {target}")
            if relations:
                answer_text += f"，它{'，'.join(relations)}"
        
        return Answer(
            text=answer_text,
            confidence=0.9,
            sources=[question.subject]
        )
    
    def _answer_how(self, question: Question) -> Answer:
        """回答'如何'类型的问题"""
        # 查找相关的实现方式
        related = self.kg.get_related_nodes(question.subject)
        
        if not related:
            return Answer(
                text=f"抱歉，我找不到关于如何使用'{question.subject}'的信息。",
                confidence=0.0,
                sources=[]
            )
        
        # 找出"powers"或"uses"关系
        methods = []
        for target, edges in related.items():
            for edge in edges:
                if edge.relation in ["powers", "uses", "implements"]:
                    methods.append(f"使用{target}")
        
        if methods:
            answer_text = f"{question.subject}可以通过{'，'.join(methods[:3])}来实现"
        else:
            answer_text = f"{question.subject}与{len(related)}个概念有关联"
        
        return Answer(
            text=answer_text,
            confidence=0.7,
            sources=[question.subject] + list(related.keys())[:3]
        )
    
    def _answer_why(self, question: Question) -> Answer:
        """回答'为什么'类型的问题"""
        # 查找反向关系
        node = self.kg.get_node(question.subject)
        
        if not node:
            return Answer(
                text=f"抱歉，我找不到关于'{question.subject}'的信息。",
                confidence=0.0,
                sources=[]
            )
        
        # 查找哪些节点指向它
        reasons = []
        from collections import defaultdict
        edges_by_source = defaultdict(list)
        for edge in self.kg.get_all_edges():
            edges_by_source[edge.source].append(edge)
        for source, edges in edges_by_source.items():
            for edge in edges:
                if edge.target == question.subject:
                    reasons.append(f"{source} {edge.relation}它")
        
        if reasons:
            answer_text = f"{question.subject}之所以重要，是因为{'，'.join(reasons[:3])}"
        else:
            answer_text = f"{question.subject}是知识图谱中的一个重要概念"
        
        return Answer(
            text=answer_text,
            confidence=0.6,
            sources=[question.subject]
        )
    
    def _answer_general(self, question: Question) -> Answer:
        """回答一般性问题"""
        node = self.kg.get_node(question.subject)
        
        if not node:
            return Answer(
                text=f"抱歉，我找不到关于'{question.subject}'的信息。",
                confidence=0.0,
                sources=[]
            )
        
        # 综合信息
        description = node.attributes.get("description", f"一个{node.node_type}")
        related_count = len(self.kg.get_related_nodes(question.subject))
        
        answer_text = f"{question.subject}是{description}，它与{related_count}个其他概念有关联"
        
        return Answer(
            text=answer_text,
            confidence=0.5,
            sources=[question.subject]
        )


def example_basic_qa():
    """示例：基础问答"""
    print("\n" + "="*60)
    print("示例 2.1: 基础问答")
    print("="*60)
    
    kg = KnowledgeGraph()
    qa = SimpleQASystem(kg)
    
    questions = [
        "What is Python?",
        "什么是 FastAPI?",
        "How to use Python?",
        "什么是 Machine Learning?",
        "Why is Python important?",
    ]
    
    for q in questions:
        print(f"\n问: {q}")
        answer = qa.answer(q)
        print(f"答: {answer.text}")
        print(f"   (置信度: {answer.confidence:.2f})")


def example_reasoning():
    """示例：推理能力"""
    print("\n" + "="*60)
    print("示例 2.2: 推理能力展示")
    print("="*60)
    
    kg = KnowledgeGraph()
    qa = SimpleQASystem(kg)
    
    # 添加推理规则
    print("\n[1] 添加推理规则...")
    # Python powers FastAPI, FastAPI uses PostgreSQL
    # => Python indirectly relates to PostgreSQL
    
    # 查找间接关系
    python_related = kg.get_related_nodes("Python")
    print(f"\n[2] Python直接关联 {len(python_related)} 个概念:")
    for name in python_related.keys():
        print(f"   - {name}")
    
    # 查找二级关系
    print("\n[3] Python的二级关联:")
    for direct_name in list(python_related.keys())[:2]:
        secondary = kg.get_related_nodes(direct_name)
        for sec_name in secondary.keys():
            if sec_name != "Python":
                print(f"   - Python -> {direct_name} -> {sec_name}")


def example_pattern_matching():
    """示例：模式匹配"""
    print("\n" + "="*60)
    print("示例 2.3: 模式匹配")
    print("="*60)
    
    kg = KnowledgeGraph()
    matcher = PatternMatcher(kg)
    
    # 定义模式：寻找"语言 -> 框架"的关系
    print("\n[1] 寻找'语言驱动框架'的模式...")
    
    patterns_found = []
    for edge in kg.get_all_edges():
        source_node = kg.get_node(edge.source)
        if source_node and source_node.node_type == "language":
            if edge.relation == "powers":
                target_node = kg.get_node(edge.target)
                if target_node and target_node.node_type == "framework":
                    patterns_found.append((edge.source, edge.target))
    
    if patterns_found:
        print(f"   找到 {len(patterns_found)} 个匹配:")
        for lang, framework in patterns_found:
            print(f"   - {lang} powers {framework}")
    else:
        print("   未找到匹配的模式")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("永动知识图谱Agent - 示例2: 智能问答系统")
    print("="*60)
    
    try:
        example_basic_qa()
        example_reasoning()
        example_pattern_matching()
        
        print("\n" + "="*60)
        print("所有示例运行完成！")
        print("="*60)
        print("\n提示:")
        print("- 问答系统基于知识图谱中的信息")
        print("- 可以通过添加更多节点和关系来扩展知识")
        print("- 推理引擎可以发现隐藏的关系")
        
    except Exception as e:
        logger.error(f"示例运行失败: {e}")
        raise


if __name__ == "__main__":
    main()
