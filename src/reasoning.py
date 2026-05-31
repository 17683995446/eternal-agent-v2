"""
推理引擎模块 — 智能增强层

公理溯源：
- 自驱公理：系统基于知识自主推理、自主决策
- 记忆公理：推理基于结构化历史经验

设计意图：
- 零外部依赖，不引入LLM/ML框架
- 所有推理基于知识图谱的权重和关联
- 规则引擎 + 模式匹配 + 因果链 + 置信度 = 轻量推理

图难于其易，为大于其细：
- 每个推理能力独立方法
- 可单独使用，也可组合
- 推理结果可沉淀回知识图谱
"""

import re
from typing import List, Dict, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict

from knowledge_graph import KnowledgeGraph
from models import Node, Edge
from logger import get_logger

logger = get_logger("Reasoning")


# ============================================================
# 阶段61: 简单规则引擎
# ============================================================

@dataclass
class Rule:
    """
    IF-THEN 规则

    结构：
        IF condition匹配 THEN 执行action
    """
    name: str
    condition: str          # 匹配条件（正则或关键词）
    action: str            # 执行动作描述
    priority: int = 0      # 规则优先级
    enabled: bool = True    # 是否启用
    match_count: int = 0   # 匹配次数
    created_at: str = field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "condition": self.condition,
            "action": self.action,
            "priority": self.priority,
            "enabled": self.enabled,
            "match_count": self.match_count,
        }


class RuleEngine:
    """
    简单规则引擎

    公理溯源：自驱公理 — 基于规则自主产生行为

    特性：
    - IF-THEN 规则匹配（正则模式）
    - 知识图谱推理规则（函数式规则）
    - 优先级排序
    - 匹配计数
    """

    def __init__(self, kg=None):
        self._rules: List[Rule] = []
        self._kg = kg
        # 函数式推理规则: {name: callable(kg) -> List[Tuple]}
        self._inference_rules: Dict[str, Callable] = {}

    def add_rule(self, name: str, condition, action: str = "", priority: int = 0):
        """
        添加规则（双模式）

        模式1 - 正则规则: add_rule(name, condition_str, action_str, priority)
        模式2 - 推理规则: add_rule(name, callable_fn)
            callable_fn 签名: fn(kg) -> List[Tuple(target, relation, attrs)]
        """
        if callable(condition):
            # 函数式推理规则
            self._inference_rules[name] = condition
            logger.debug(f"推理规则添加: {name}")
            return None
        else:
            # 正则规则
            rule = Rule(name=name, condition=condition, action=action, priority=priority)
            self._rules.append(rule)
            self._rules.sort(key=lambda r: r.priority, reverse=True)
            logger.debug(f"规则添加: {name} (条件: {condition})")
            return rule

    def remove_rule(self, name: str) -> bool:
        """移除规则（正则规则或推理规则）"""
        for i, rule in enumerate(self._rules):
            if rule.name == name:
                self._rules.pop(i)
                return True
        if name in self._inference_rules:
            del self._inference_rules[name]
            return True
        return False

    def match(self, text: str) -> List[Rule]:
        """
        匹配文本到规则

        Args:
            text: 待匹配文本

        Returns:
            List[Rule]: 匹配的规则列表
        """
        matched = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            if re.search(rule.condition, text, re.IGNORECASE):
                rule.match_count += 1
                matched.append(rule)
        return matched

    def evaluate(self, text: str) -> List[Dict]:
        """
        评估文本，返回匹配结果

        Returns:
            List[Dict]: [{"rule": name, "action": action, "priority": int}]
        """
        matched = self.match(text)
        return [
            {"rule": r.name, "action": r.action, "priority": r.priority}
            for r in matched
        ]

    def get_rules(self) -> List[Rule]:
        """获取所有正则规则"""
        return self._rules.copy()

    def infer(self) -> List[Tuple]:
        """
        执行推理规则，返回新知识列表

        每条推理规则是一个 callable(kg) -> List[Tuple(target, relation, attrs)]
        推理结果会自动沉淀回知识图谱

        Returns:
            List[Tuple]: [(target, relation, attrs), ...]
        """
        if not self._kg:
            logger.warning("推理引擎未绑定知识图谱，无法执行推理")
            return []

        new_knowledge = []
        for name, rule_fn in self._inference_rules.items():
            try:
                results = rule_fn(self._kg)
                if results:
                    for item in results:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            target, relation = item[0], item[1]
                            attrs = item[2] if len(item) > 2 else {}
                            # 沉淀回知识图谱
                            if not self._kg.has_node(target):
                                self._kg.add_node(target, "inferred", attrs if isinstance(attrs, dict) else {})
                            new_knowledge.append(item)
                    logger.debug(f"推理规则 '{name}' 产生 {len(results)} 条新知识")
            except Exception as e:
                logger.error(f"推理规则 '{name}' 执行失败: {e}")

        return new_knowledge

    def stats(self) -> Dict:
        """规则引擎统计"""
        return {
            "total_rules": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules if r.enabled),
            "total_matches": sum(r.match_count for r in self._rules),
            "inference_rules": len(self._inference_rules),
        }


# ============================================================
# 阶段62: 模式匹配机制
# ============================================================

class PatternMatcher:
    """
    模式匹配器

    公理溯源：记忆公理 — 从历史经验中识别模式

    特性：
    - 关键词匹配
    - 正则匹配
    - 前缀匹配
    - 模板匹配
    """

    def __init__(self, kg=None):
        self._patterns: Dict[str, re.Pattern] = {}
        self._kg = kg

    def add_pattern(self, name: str, pattern: str) -> bool:
        """添加模式"""
        try:
            self._patterns[name] = re.compile(pattern, re.IGNORECASE)
            return True
        except re.error:
            return False

    def match(self, text: str) -> List[str]:
        """匹配文本，返回匹配的模式名列表"""
        matched = []
        for name, pattern in self._patterns.items():
            if pattern.search(text):
                matched.append(name)
        return matched

    def match_all(self, texts: List[str]) -> Dict[str, int]:
        """批量匹配，返回每个模式的匹配计数"""
        counts = defaultdict(int)
        for text in texts:
            for name in self.match(text):
                counts[name] += 1
        return dict(counts)


# ============================================================
# 阶段63: 因果链追踪
# ============================================================

class CausalTracker:
    """
    因果链追踪器

    公理溯源：记忆公理 — 追踪知识之间的因果路径

    特性：
    - BFS/DFS路径搜索
    - 最短因果链
    - 因果环检测
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    def find_paths(self, source: str, target: str, max_depth: int = 10) -> List[List[str]]:
        """
        查找从source到target的所有路径（BFS层级遍历）

        Args:
            source: 起始节点
            target: 目标节点
            max_depth: 最大搜索深度

        Returns:
            List[List[str]]: 路径列表
        """
        if not self.kg.has_node(source) or not self.kg.has_node(target):
            return []

        if source == target:
            return [[source]]

        paths = []
        # BFS层级遍历：(当前节点, 路径, 当前深度)
        queue = [(source, [source], 0)]

        while queue:
            current, path, depth = queue.pop(0)

            if depth >= max_depth:
                continue

            for edge in self.kg.get_edges_from(current):
                next_node = edge.target
                new_path = path + [next_node]

                if next_node == target:
                    paths.append(new_path)
                elif next_node not in path:  # 避免环，但不阻止不同路径访问同一节点
                    queue.append((next_node, new_path, depth + 1))

        return paths

    def find_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """查找最短路径"""
        paths = self.find_paths(source, target)
        return min(paths, key=len) if paths else None

    def trace_causes(self, node_name: str, max_depth: int = 5) -> List[str]:
        """
        追踪节点的所有原因（反向追踪，标准BFS层级遍历）

        Args:
            node_name: 节点名称
            max_depth: 最大深度

        Returns:
            List[str]: 原因节点列表
        """
        causes = []
        visited = set()
        # BFS层级遍历：(节点, 当前深度)
        queue = [(node_name, 0)]

        while queue:
            current, depth = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            if depth >= max_depth:
                continue

            for edge in self.kg.get_edges_to(current):
                if edge.source not in visited:
                    causes.append(edge.source)
                    queue.append((edge.source, depth + 1))

        return list(dict.fromkeys(causes))  # 去重保序

    def trace_effects(self, node_name: str, max_depth: int = 5) -> List[str]:
        """
        追踪节点的所有影响（正向追踪）

        Args:
            node_name: 节点名称
            max_depth: 最大深度

        Returns:
            List[str]: 影响节点列表
        """
        effects = []
        visited = set()
        queue = [node_name]

        depth = 0
        while queue and depth < max_depth:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            for edge in self.kg.get_edges_from(current):
                effects.append(edge.target)
                queue.append(edge.target)

            depth += 1

        return list(dict.fromkeys(effects))

    def detect_cycles(self) -> List[List[str]]:
        """
        检测图中的环（标准DFS三色标记法）

        Returns:
            List[List[str]]: 环列表
        """
        cycles = []
        # 三色标记: WHITE=未访问, GRAY=在当前DFS路径上, BLACK=已完成
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n.name: WHITE for n in self.kg.get_all_nodes()}
        path = []

        def dfs(node_name: str) -> None:
            color[node_name] = GRAY
            path.append(node_name)

            for edge in self.kg.get_edges_from(node_name):
                neighbor = edge.target
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    # 发现环：从path中找到环的起点
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif color[neighbor] == WHITE:
                    dfs(neighbor)

            path.pop()
            color[node_name] = BLACK

        for node_name in list(color.keys()):
            if color[node_name] == WHITE:
                dfs(node_name)

        return cycles


# ============================================================
# 阶段64: 假设验证框架
# ============================================================

@dataclass
class Hypothesis:
    """假设"""
    statement: str
    source: str = ""          # 来源节点
    confidence: float = 0.0   # 置信度
    verified: bool = False     # 是否已验证
    result: Optional[str] = None  # 验证结果
    created_at: str = field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())


class HypothesisEngine:
    """
    假设验证引擎

    公理溯源：自驱公理 — 自主探索、自主验证

    流程：创建假设 → 查找证据 → 计算置信度 → 记录结果
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
        self._hypotheses: List[Hypothesis] = []

    def create_hypothesis(self, statement: str, source: str = "") -> Hypothesis:
        """创建假设"""
        h = Hypothesis(statement=statement, source=source)
        self._hypotheses.append(h)
        logger.debug(f"假设创建: {statement}")
        return h

    def verify(self, hypothesis: Hypothesis) -> Hypothesis:
        """
        验证假设

        基于知识图谱中的证据计算置信度
        """
        evidence_count = 0
        total_weight = 0.0

        # 搜索相关节点
        for node in self.kg.get_all_nodes():
            if hypothesis.statement.lower() in node.name.lower():
                evidence_count += 1

        # 搜索相关边
        for edge in self.kg.get_all_edges():
            if (hypothesis.statement.lower() in edge.source.lower() or
                hypothesis.statement.lower() in edge.target.lower()):
                evidence_count += 1
                total_weight += edge.weight

        # 计算置信度
        if evidence_count > 0:
            hypothesis.confidence = min(1.0, (evidence_count * 0.2 + total_weight * 0.3))
        else:
            hypothesis.confidence = 0.0

        hypothesis.verified = True
        hypothesis.result = f"证据数: {evidence_count}, 置信度: {hypothesis.confidence:.2f}"

        logger.info(f"假设验证: {hypothesis.statement} → {hypothesis.result}")
        return hypothesis

    def get_verified(self) -> List[Hypothesis]:
        """获取已验证假设"""
        return [h for h in self._hypotheses if h.verified]

    def get_pending(self) -> List[Hypothesis]:
        """获取待验证假设"""
        return [h for h in self._hypotheses if not h.verified]

    def stats(self) -> Dict:
        return {
            "total": len(self._hypotheses),
            "verified": len(self.get_verified()),
            "pending": len(self.get_pending()),
            "avg_confidence": (
                sum(h.confidence for h in self.get_verified()) / len(self.get_verified())
                if self.get_verified() else 0.0
            ),
        }


# ============================================================
# 阶段65: 置信度评估
# ============================================================

class ConfidenceEvaluator:
    """
    置信度评估器

    公理溯源：记忆公理 — 权重是智能经验积累的量化

    基于边的权重、数量、关联度计算知识可信度
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    def evaluate_node(self, node_name: str) -> float:
        """
        评估节点置信度

        因素：
        - 入边数量和权重
        - 出边数量和权重
        - 关联节点数量

        Returns:
            float: 置信度 (0.0-1.0)
        """
        if not self.kg.has_node(node_name):
            return 0.0

        incoming = self.kg.get_edges_to(node_name)
        outgoing = self.kg.get_edges_from(node_name)

        # 入边权重（被引用越多越可信）
        in_score = sum(e.weight for e in incoming) * 0.4 if incoming else 0.0

        # 出边权重（关联越多越活跃）
        out_score = sum(e.weight for e in outgoing) * 0.3 if outgoing else 0.0

        # 关联度（连接的独立节点数）
        connected = set()
        for e in incoming:
            connected.add(e.source)
        for e in outgoing:
            connected.add(e.target)
        connectivity_score = min(len(connected) * 0.1, 0.3)

        return min(1.0, in_score + out_score + connectivity_score)

    def evaluate_edge(self, source: str, target: str) -> float:
        """
        评估边置信度

        Returns:
            float: 置信度
        """
        edges = self.kg.get_edges_between(source, target)
        if not edges:
            return 0.0

        # 边的权重直接作为基础置信度
        base = edges[0].weight

        # 两端节点的置信度作为加成
        source_conf = self.evaluate_node(source)
        target_conf = self.evaluate_node(target)

        return min(1.0, base * 0.5 + (source_conf + target_conf) * 0.25)

    def rank_nodes(self) -> List[Tuple[str, float]]:
        """
        按置信度排序所有节点

        Returns:
            List[Tuple[str, float]]: [(节点名, 置信度)] 按降序
        """
        scores = []
        for node in self.kg.get_all_nodes():
            score = self.evaluate_node(node.name)
            scores.append((node.name, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


# ============================================================
# 阶段66: 知识冲突检测
# ============================================================

class ConflictDetector:
    """
    知识冲突检测器

    公理溯源：记忆公理 — 发现并处理矛盾知识
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    def detect_low_weight_conflicts(self, threshold: float = 0.3) -> List[Dict]:
        """
        检测低权重冲突（同一对节点间有低权重边）

        Returns:
            List[Dict]: 冲突列表
        """
        conflicts = []
        seen_pairs = set()

        for edge in self.kg.get_all_edges():
            pair = (edge.source, edge.target)
            reverse_pair = (edge.target, edge.source)

            if pair in seen_pairs or reverse_pair in seen_pairs:
                continue

            seen_pairs.add(pair)
            seen_pairs.add(reverse_pair)

            # 检查是否有反向边
            reverse_edges = self.kg.get_edges_between(edge.target, edge.source)
            if reverse_edges and edge.weight < threshold:
                conflicts.append({
                    "type": "low_weight_conflict",
                    "edge": f"{edge.source} -> {edge.target}",
                    "weight": edge.weight,
                    "reverse_weight": reverse_edges[0].weight,
                })

        return conflicts

    def detect_isolation_conflicts(self) -> List[Dict]:
        """检测孤立节点冲突"""
        conflicts = []
        health = self.kg.health_check()

        for node_name in health.get("isolated_nodes", []):
            conflicts.append({
                "type": "isolation",
                "node": node_name,
            })

        return conflicts

    def detect_all(self) -> List[Dict]:
        """检测所有冲突"""
        all_conflicts = []
        all_conflicts.extend(self.detect_low_weight_conflicts())
        all_conflicts.extend(self.detect_isolation_conflicts())
        return all_conflicts


# ============================================================
# 阶段67: 经验泛化
# ============================================================

class ExperienceGeneralizer:
    """
    经验泛化器

    公理溯源：自驱公理 — 从具体经验提取通用规则

    从重复出现的模式中提取规则
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    def extract_patterns(self, min_occurrences: int = 2) -> List[Dict]:
        """
        提取重复模式

        查找频繁出现的边关系模式

        Returns:
            List[Dict]: 模式列表
        """
        # 统计关系类型频率
        relation_counts = defaultdict(int)
        for edge in self.kg.get_all_edges():
            key = edge.relation
            relation_counts[key] += 1

        # 提取高频模式
        patterns = []
        for relation, count in relation_counts.items():
            if count >= min_occurrences:
                patterns.append({
                    "pattern": relation,
                    "occurrences": count,
                    "type": "frequent_relation",
                })

        return sorted(patterns, key=lambda p: p["occurrences"], reverse=True)

    def generalize_task_names(self) -> List[Dict]:
        """
        从任务名中提取通用模式

        Returns:
            List[Dict]: 泛化规则列表
        """
        task_nodes = self.kg.get_nodes_by_type("task")
        if not task_nodes:
            return []

        # 提取任务名前缀
        prefix_counts = defaultdict(int)
        for node in task_nodes:
            parts = node.name.split("_")
            if len(parts) > 1:
                prefix_counts[parts[0]] += 1

        rules = []
        for prefix, count in prefix_counts.items():
            if count >= 2:
                rules.append({
                    "pattern": f"{prefix}_*",
                    "occurrences": count,
                    "type": "task_prefix",
                })

        return sorted(rules, key=lambda r: r["occurrences"], reverse=True)


# ============================================================
# 阶段68: 异常模式识别
# ============================================================

class AnomalyDetector:
    """
    异常模式识别器

    公理溯源：存续公理 — 检测偏离常态的行为
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    def detect_weight_anomalies(self, threshold: float = 0.9) -> List[Dict]:
        """
        检测异常高权重边

        Returns:
            List[Dict]: 异常列表
        """
        anomalies = []
        avg_weight = self.kg.stats()["average_weight"]

        for edge in self.kg.get_all_edges():
            if edge.weight >= threshold:
                anomalies.append({
                    "type": "high_weight",
                    "edge": f"{edge.source} -> {edge.target}",
                    "weight": edge.weight,
                    "deviation": round(edge.weight - avg_weight, 3),
                })

        return anomalies

    def detect_orphan_chains(self, min_length: int = 3) -> List[List[str]]:
        """
        检测孤立链（线性结构，无分支）

        Returns:
            List[List[str]]: 孤立链列表
        """
        # 统计每个节点的连接数
        connection_count = defaultdict(int)
        for edge in self.kg.get_all_edges():
            connection_count[edge.source] += 1
            connection_count[edge.target] += 1

        # 找出只有1-2个连接的节点
        candidates = [name for name, count in connection_count.items()
                      if count <= 2]

        # 追踪链
        chains = []
        visited = set()

        for start in candidates:
            if start in visited:
                continue

            chain = [start]
            visited.add(start)
            current = start

            while True:
                edges = self.kg.get_edges_from(current)
                if len(edges) != 1:
                    break
                next_node = edges[0].target
                if next_node in visited or connection_count.get(next_node, 0) > 2:
                    break
                chain.append(next_node)
                visited.add(next_node)
                current = next_node

            if len(chain) >= min_length:
                chains.append(chain)

        return chains


# ============================================================
# 阶段69: 决策建议生成
# ============================================================

class DecisionAdvisor:
    """
    决策建议生成器

    公理溯源：自驱公理 — 基于知识推荐下一步

    基于置信度和知识关联推荐行动
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
        self.evaluator = ConfidenceEvaluator(kg)

    def suggest_next_tasks(self, current_task: str, top_n: int = 5) -> List[Dict]:
        """
        建议下一步任务

        Args:
            current_task: 当前任务
            top_n: 返回前N个建议

        Returns:
            List[Dict]: 建议列表
        """
        suggestions = []

        # 获取当前任务的高权重关联
        for edge in self.kg.get_edges_from(current_task):
            confidence = self.evaluator.evaluate_edge(
                edge.source, edge.target
            )
            suggestions.append({
                "task": edge.target,
                "relation": edge.relation,
                "weight": edge.weight,
                "confidence": round(confidence, 3),
                "reason": f"基于'{edge.relation}'关系 (权重:{edge.weight:.2f})",
            })

        # 按置信度排序
        suggestions.sort(key=lambda s: s["confidence"], reverse=True)
        return suggestions[:top_n]

    def suggest_knowledge_gaps(self) -> List[Dict]:
        """
        建议知识缺口

        找出低置信度节点，建议补充知识

        Returns:
            List[Dict]: 缺口列表
        """
        rankings = self.evaluator.rank_nodes()

        gaps = []
        for name, score in rankings:
            if score < 0.2:
                gaps.append({
                    "node": name,
                    "confidence": score,
                    "suggestion": f"节点'{name}'置信度低({score:.2f})，建议补充关联知识",
                })

        return gaps[:10]


# ============================================================
# 统一推理接口
# ============================================================

class ReasoningEngine:
    """
    统一推理引擎

    整合所有推理能力，提供统一入口
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
        self.rule_engine = RuleEngine()
        self.pattern_matcher = PatternMatcher()
        self.causal_tracker = CausalTracker(kg)
        self.hypothesis_engine = HypothesisEngine(kg)
        self.confidence_evaluator = ConfidenceEvaluator(kg)
        self.conflict_detector = ConflictDetector(kg)
        self.experience_generalizer = ExperienceGeneralizer(kg)
        self.anomaly_detector = AnomalyDetector(kg)
        self.decision_advisor = DecisionAdvisor(kg)

    def analyze(self, text: str) -> Dict:
        """
        综合分析

        Args:
            text: 分析文本

        Returns:
            Dict: 分析结果
        """
        # 规则匹配
        rule_results = self.rule_engine.evaluate(text)

        # 模式匹配
        pattern_results = self.pattern_matcher.match(text)

        # 决策建议
        suggestions = self.decision_advisor.suggest_next_tasks(text, top_n=3)

        return {
            "rules_matched": rule_results,
            "patterns_matched": pattern_results,
            "suggestions": suggestions,
        }

    def full_health_check(self) -> Dict:
        """
        全面健康检查

        Returns:
            Dict: 健康报告
        """
        return {
            "kg_health": self.kg.health_check(),
            "conflicts": self.conflict_detector.detect_all(),
            "anomalies": self.anomaly_detector.detect_weight_anomalies(),
            "patterns": self.experience_generalizer.extract_patterns(),
            "hypotheses": self.hypothesis_engine.stats(),
            "rules": self.rule_engine.stats(),
        }
