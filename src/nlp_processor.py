"""
NLP处理器模块 — 智能增强层

公理溯源：记忆公理 - 知识需要从文本中提取和结构化

设计意图：
- 关键词提取（TF-IDF）
- 文本分词（中英文）
- 文本清洗和标准化
- 词频统计
- 零外部依赖，纯Python实现

大事做于细，难事成于易：
- 每个功能独立函数
- 支持中英文混合处理
- 可配置的停用词表
"""

import re
import math
import string
from collections import Counter
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path

from logger import get_logger
from utils import read_json, write_json, now_iso
from constants import PROJECT_ROOT, ENCODING

logger = get_logger("NLPProcessor")


# ============================================================
# 停用词表
# ============================================================

# 英文停用词
ENGLISH_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "need",
    "it", "its", "this", "that", "these", "those", "i", "you", "he",
    "she", "we", "they", "what", "which", "who", "when", "where", "why",
    "how", "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "not", "only", "same", "so", "than", "too",
    "very", "just", "also", "now", "here", "there", "then", "if", "else",
}

# 中文停用词
CHINESE_STOPWORDS = {
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都",
    "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会",
    "着", "没有", "看", "好", "自己", "这", "那", "什么", "他", "她",
    "它", "们", "这个", "那个", "这些", "那些", "可以", "没", "吗",
    "啊", "呢", "吧", "呀", "哦", "嗯", "哈", "嘿", "哎", "唉",
}


@dataclass
class Token:
    """词元"""
    text: str
    pos: str = "UNKNOWN"  # 词性
    lemma: str = ""  # 词元形式
    start: int = 0  # 起始位置
    end: int = 0  # 结束位置


@dataclass
class TextAnalysis:
    """文本分析结果"""
    original_text: str
    tokens: List[Token] = field(default_factory=list)
    keywords: List[Tuple[str, float]] = field(default_factory=list)
    word_count: int = 0
    char_count: int = 0
    language: str = "unknown"
    sentences: List[str] = field(default_factory=list)


class NLPProcessor:
    """
    NLP处理器
    
    核心能力：
    - 文本分词（中英文）
    - 关键词提取（TF-IDF）
    - 文本清洗
    - 词频统计
    """
    
    def __init__(self, custom_stopwords: Optional[Set[str]] = None):
        self.stopwords = ENGLISH_STOPWORDS | CHINESE_STOPWORDS
        if custom_stopwords:
            self.stopwords |= custom_stopwords
        
        # 文档频率（用于TF-IDF）
        self.document_frequency: Dict[str, int] = {}
        self.total_documents = 0
        
        # 词元模式
        self._chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        self._english_pattern = re.compile(r'[a-zA-Z]+')
        self._number_pattern = re.compile(r'\d+')
    
    def detect_language(self, text: str) -> str:
        """
        检测文本语言
        
        Args:
            text: 输入文本
            
        Returns:
            语言标识 ('zh', 'en', 'mixed', 'unknown')
        """
        chinese_chars = len(self._chinese_pattern.findall(text))
        english_chars = len(self._english_pattern.findall(text))
        total = chinese_chars + english_chars
        
        if total == 0:
            return "unknown"
        
        chinese_ratio = chinese_chars / total
        english_ratio = english_chars / total
        
        if chinese_ratio > 0.7:
            return "zh"
        elif english_ratio > 0.7:
            return "en"
        elif chinese_ratio > 0.1 and english_ratio > 0.1:
            return "mixed"
        elif chinese_ratio > english_ratio:
            return "zh"
        else:
            return "en"
    
    def clean_text(self, text: str) -> str:
        """
        清洗文本
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除特殊字符（保留中英文、数字、基本标点）
        text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:\'"()（）。，！？；：""''、]', ' ', text)
        
        # 合并多个空格
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _tokenize_chinese(self, text: str, start: int, end: int, tokens: List[Token]) -> None:
        """处理中文分词（辅助方法）"""
        chinese_text = text[start:end]
        if len(chinese_text) >= 2:
            for k in range(0, len(chinese_text) - 1, 2):
                word = chinese_text[k:k+2]
                tokens.append(Token(text=word, pos="CHINESE", start=start + k, end=start + k + 2))
            if len(chinese_text) % 2 == 1:
                last_char = chinese_text[-1]
                tokens.append(Token(text=last_char, pos="CHINESE", start=start + len(chinese_text) - 1, end=start + len(chinese_text)))
        else:
            tokens.append(Token(text=chinese_text, pos="CHINESE", start=start, end=end))

    def _tokenize_english(self, text: str, start: int, end: int, tokens: List[Token]) -> None:
        """处理英文分词（辅助方法）"""
        word = text[start:end].lower()
        tokens.append(Token(text=word, pos="ENGLISH", start=start, end=end))

    def _tokenize_number(self, text: str, start: int, end: int, tokens: List[Token]) -> None:
        """处理数字分词（辅助方法）"""
        tokens.append(Token(text=text[start:end], pos="NUMBER", start=start, end=end))

    def tokenize(self, text: str) -> List[Token]:
        """
        分词
        
        Args:
            text: 输入文本
            
        Returns:
            词元列表
        """
        tokens = []
        text = self.clean_text(text)
        
        i = 0
        while i < len(text):
            char = text[i]
            
            # 中文字符
            if self._chinese_pattern.match(char):
                j = i + 1
                while j < len(text) and self._chinese_pattern.match(text[j]):
                    j += 1
                self._tokenize_chinese(text, i, j, tokens)
                i = j
            
            # 英文单词
            elif self._english_pattern.match(char):
                j = i
                while j < len(text) and self._english_pattern.match(text[j]):
                    j += 1
                self._tokenize_english(text, i, j, tokens)
                i = j
            
            # 数字
            elif self._number_pattern.match(char):
                j = i
                while j < len(text) and (self._number_pattern.match(text[j]) or text[j] == '.'):
                    j += 1
                self._tokenize_number(text, i, j, tokens)
                i = j
            
            else:
                i += 1
        
        return tokens
    
    def remove_stopwords(self, tokens: List[Token]) -> List[Token]:
        """
        移除停用词
        
        Args:
            tokens: 词元列表
            
        Returns:
            过滤后的词元列表
        """
        return [t for t in tokens if t.text.lower() not in self.stopwords]
    
    def get_word_frequency(self, tokens: List[Token]) -> Dict[str, int]:
        """
        计算词频
        
        Args:
            tokens: 词元列表
            
        Returns:
            词频字典
        """
        words = [t.text.lower() for t in tokens]
        return dict(Counter(words))
    
    def compute_tf(self, tokens: List[Token]) -> Dict[str, float]:
        """
        计算TF（词频）
        
        Args:
            tokens: 词元列表
            
        Returns:
            TF字典
        """
        word_count = len(tokens)
        if word_count == 0:
            return {}
        
        freq = self.get_word_frequency(tokens)
        return {word: count / word_count for word, count in freq.items()}
    
    def compute_idf(self, word: str) -> float:
        """
        计算IDF（逆文档频率）
        
        Args:
            word: 词
            
        Returns:
            IDF值
        """
        df = self.document_frequency.get(word.lower(), 0)
        if df == 0:
            return 0.0
        
        return math.log((self.total_documents + 1) / (df + 1)) + 1
    
    def compute_tfidf(self, tokens: List[Token]) -> Dict[str, float]:
        """
        计算TF-IDF
        
        Args:
            tokens: 词元列表
            
        Returns:
            TF-IDF字典
        """
        tf = self.compute_tf(tokens)
        tfidf = {}
        
        for word, tf_value in tf.items():
            idf = self.compute_idf(word)
            tfidf[word] = tf_value * idf
        
        return tfidf
    
    def update_document_frequency(self, tokens: List[Token]):
        """
        更新文档频率
        
        Args:
            tokens: 文档的词元列表
        """
        unique_words = set(t.text.lower() for t in tokens)
        
        for word in unique_words:
            self.document_frequency[word] = self.document_frequency.get(word, 0) + 1
        
        self.total_documents += 1
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        提取关键词
        
        Args:
            text: 输入文本
            top_n: 返回前N个关键词
            
        Returns:
            关键词列表 [(词, 分数), ...]
        """
        # 分词
        tokens = self.tokenize(text)
        
        # 移除停用词
        tokens = self.remove_stopwords(tokens)
        
        if not tokens:
            return []
        
        # 计算TF-IDF
        tfidf = self.compute_tfidf(tokens)
        
        # 如果没有文档频率，使用TF
        if not tfidf or all(v == 0 for v in tfidf.values()):
            tf = self.compute_tf(tokens)
            tfidf = tf
        
        # 排序
        sorted_keywords = sorted(tfidf.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_keywords[:top_n]
    
    def split_sentences(self, text: str) -> List[str]:
        """
        分句
        
        Args:
            text: 输入文本
            
        Returns:
            句子列表
        """
        # 中英文句号、问号、感叹号
        pattern = r'[。！？.!?]+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def analyze(self, text: str) -> TextAnalysis:
        """
        完整文本分析
        
        Args:
            text: 输入文本
            
        Returns:
            分析结果
        """
        # 清洗
        cleaned = self.clean_text(text)
        
        # 检测语言
        language = self.detect_language(text)
        
        # 分词
        tokens = self.tokenize(cleaned)
        
        # 提取关键词
        keywords = self.extract_keywords(cleaned)
        
        # 分句
        sentences = self.split_sentences(text)
        
        return TextAnalysis(
            original_text=text,
            tokens=tokens,
            keywords=keywords,
            word_count=len(tokens),
            char_count=len(cleaned),
            language=language,
            sentences=sentences
        )
    
    def extract_entities_simple(self, text: str) -> Dict[str, List[str]]:
        """
        简单实体提取（基于规则）
        
        Args:
            text: 输入文本
            
        Returns:
            实体字典 {类型: [实体列表]}
        """
        entities = {
            "numbers": [],
            "english_words": [],
            "chinese_words": [],
            "emails": [],
            "urls": [],
            "dates": [],
        }
        
        # 数字
        numbers = self._number_pattern.findall(text)
        entities["numbers"] = list(set(numbers))
        
        # 英文单词（大写开头的可能是专有名词）
        english_words = self._english_pattern.findall(text)
        proper_nouns = [w for w in english_words if w[0].isupper() and len(w) > 1]
        entities["english_words"] = list(set(proper_nouns))
        
        # 中文词
        tokens = self.tokenize(text)
        chinese_words = [t.text for t in tokens if t.pos == "CHINESE" and len(t.text) > 1]
        entities["chinese_words"] = list(set(chinese_words))
        
        # 邮箱
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        entities["emails"] = re.findall(email_pattern, text)
        
        # URL
        url_pattern = r'https?://[^\s]+'
        entities["urls"] = re.findall(url_pattern, text)
        
        # 日期（简单模式）
        date_patterns = [
            r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?',  # 2024-01-15 或 2024年1月15日
            r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',  # 01-15-2024
        ]
        for pattern in date_patterns:
            entities["dates"].extend(re.findall(pattern, text))
        
        return entities
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        计算文本相似度（基于词频）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度 (0-1)
        """
        tokens1 = self.remove_stopwords(self.tokenize(text1))
        tokens2 = self.remove_stopwords(self.tokenize(text2))
        
        if not tokens1 or not tokens2:
            return 0.0
        
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
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def summarize_keywords(self, text: str, max_keywords: int = 5) -> str:
        """
        基于关键词生成摘要
        
        Args:
            text: 输入文本
            max_keywords: 最大关键词数
            
        Returns:
            关键词摘要
        """
        keywords = self.extract_keywords(text, top_n=max_keywords)
        if not keywords:
            return ""
        
        keyword_str = ", ".join(kw for kw, _ in keywords)
        return f"关键词: {keyword_str}"


# 全局处理器实例
_default_processor: Optional[NLPProcessor] = None


def get_nlp_processor() -> NLPProcessor:
    """获取NLP处理器实例"""
    global _default_processor
    
    if _default_processor is None:
        _default_processor = NLPProcessor()
    
    return _default_processor


# 便捷函数
def tokenize(text: str) -> List[str]:
    """分词（便捷函数）"""
    processor = get_nlp_processor()
    tokens = processor.tokenize(text)
    return [t.text for t in tokens]


def extract_keywords(text: str, top_n: int = 10) -> List[Tuple[str, float]]:
    """提取关键词（便捷函数）"""
    processor = get_nlp_processor()
    return processor.extract_keywords(text, top_n)


def text_similarity(text1: str, text2: str) -> float:
    """文本相似度（便捷函数）"""
    processor = get_nlp_processor()
    return processor.similarity(text1, text2)


if __name__ == "__main__":
    # 测试
    processor = NLPProcessor()
    
    # 测试中文
    text_zh = "永动知识图谱Agent是一个基于第一性原理设计的智能系统，具有存续、记忆、自驱三大核心能力。"
    print("中文测试:")
    print(f"  语言检测: {processor.detect_language(text_zh)}")
    print(f"  分词: {[t.text for t in processor.tokenize(text_zh)][:10]}")
    print(f"  关键词: {processor.extract_keywords(text_zh, 5)}")
    
    # 测试英文
    text_en = "The Eternal Knowledge Graph Agent is an intelligent system based on first principles."
    print("\n英文测试:")
    print(f"  语言检测: {processor.detect_language(text_en)}")
    print(f"  分词: {[t.text for t in processor.tokenize(text_en)][:10]}")
    print(f"  关键词: {processor.extract_keywords(text_en, 5)}")
    
    # 测试相似度
    print(f"\n相似度: {processor.similarity(text_zh, text_en):.3f}")
