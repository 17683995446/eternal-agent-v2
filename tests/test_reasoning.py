"""
推理引擎模块测试

验证目标：
1. 规则引擎匹配正确
2. 模式匹配有效
3. 因果链追踪准确
4. 假设验证框架工作
5. 置信度评估合理
6. 冲突检测有效
7. 经验泛化正确
8. 异常检测有效
9. 决策建议合理
"""

import pytest
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reasoning import (
    RuleEngine,
    PatternMatcher,
    CausalTracker,
    HypothesisEngine,
    ConfidenceEvaluator,
    ConflictDetector,
    ExperienceGeneralizer,
    AnomalyDetector,
    DecisionAdvisor,
    ReasoningEngine,
)
from knowledge_graph import KnowledgeGraph


@pytest.fixture
def sample_kg():
    """创建测试用知识图谱"""
    kg = KnowledgeGraph()
    kg.add_edge("A", "B", weight=0.9, relation="因果")
    kg.add_edge("B", "C", weight=0.8, relation="因果")
    kg.add_edge("A", "C", weight=0.3, relation="关联")
    kg.add_edge("D", "E", weight=0.95, relation="因果")
    kg.add_edge("X", "Y", weight=0.05, relation="关联")
    kg.add_node("isolated")
    return kg


class TestRuleEngine:
    """规则引擎测试"""

    def test_add_rule(self):
        """测试添加规则"""
        engine = RuleEngine()
        engine.add_rule("r1", r"error", "记录错误")
        assert len(engine.get_rules()) == 1

    def test_match_rule(self):
        """测试规则匹配"""
        engine = RuleEngine()
        engine.add_rule("r1", r"error", "记录错误")

        results = engine.match("this is an error message")
        assert len(results) == 1
        assert results[0].name == "r1"

    def test_no_match(self):
        """测试无匹配"""
        engine = RuleEngine()
        engine.add_rule("r1", r"error", "记录错误")

        results = engine.match("this is fine")
        assert len(results) == 0

    def test_priority_order(self):
        """测试优先级排序"""
        engine = RuleEngine()
        engine.add_rule("low", r"test", "低优先级", priority=1)
        engine.add_rule("high", r"test", "高优先级", priority=10)

        results = engine.evaluate("test")
        assert len(results) == 2
        assert results[0]["rule"] == "high"

    def test_match_count(self):
        """测试匹配计数"""
        engine = RuleEngine()
        engine.add_rule("r1", r"test", "动作")

        engine.match("test 1")
        engine.match("test 2")
        engine.match("no match")

        stats = engine.stats()
        assert stats["total_matches"] == 2

    def test_remove_rule(self):
        """测试移除规则"""
        engine = RuleEngine()
        engine.add_rule("r1", r"test", "动作")
        engine.remove_rule("r1")
        assert len(engine.get_rules()) == 0

    def test_disabled_rule(self):
        """测试禁用规则"""
        engine = RuleEngine()
        rule = engine.add_rule("r1", r"test", "动作")
        rule.enabled = False

        results = engine.match("test")
        assert len(results) == 0


class TestPatternMatcher:
    """模式匹配测试"""

    def test_add_and_match(self):
        """测试添加和匹配"""
        matcher = PatternMatcher()
        matcher.add_pattern("email", r"[\w.]+@[\w.]+")

        results = matcher.match("contact: user@example.com")
        assert "email" in results

    def test_no_match(self):
        """测试无匹配"""
        matcher = PatternMatcher()
        matcher.add_pattern("email", r"[\w.]+@[\w.]+")

        results = matcher.match("no email here")
        assert "email" not in results

    def test_batch_match(self):
        """测试批量匹配"""
        matcher = PatternMatcher()
        matcher.add_pattern("num", r"\d+")

        texts = ["abc", "123", "def", "456"]
        counts = matcher.match_all(texts)
        assert counts["num"] == 2


class TestCausalTracker:
    """因果链追踪测试"""

    def test_find_paths(self, sample_kg):
        """测试路径查找"""
        tracker = CausalTracker(sample_kg)
        paths = tracker.find_paths("A", "C")

        assert len(paths) >= 1
        # 至少有 A->C 直接路径
        assert any("A" in p and "C" in p for p in paths)

    def test_find_shortest_path(self, sample_kg):
        """测试最短路径"""
        tracker = CausalTracker(sample_kg)
        path = tracker.find_shortest_path("A", "C")

        assert path is not None
        assert path[0] == "A"
        assert path[-1] == "C"

    def test_no_path(self, sample_kg):
        """测试无路径"""
        tracker = CausalTracker(sample_kg)
        path = tracker.find_shortest_path("A", "D")

        assert path is None

    def test_trace_causes(self, sample_kg):
        """测试原因追踪"""
        tracker = CausalTracker(sample_kg)
        causes = tracker.trace_causes("C")

        assert "B" in causes
        assert "A" in causes

    def test_trace_effects(self, sample_kg):
        """测试影响追踪"""
        tracker = CausalTracker(sample_kg)
        effects = tracker.trace_effects("A")

        assert "B" in effects
        assert "C" in effects


class TestHypothesisEngine:
    """假设验证测试"""

    def test_create_hypothesis(self, sample_kg):
        """测试创建假设"""
        engine = HypothesisEngine(sample_kg)
        h = engine.create_hypothesis("A导致C")

        assert h.statement == "A导致C"
        assert not h.verified

    def test_verify_hypothesis(self, sample_kg):
        """测试验证假设"""
        engine = HypothesisEngine(sample_kg)
        h = engine.create_hypothesis("A")
        engine.verify(h)

        assert h.verified
        assert h.confidence > 0
        assert h.result is not None

    def test_stats(self, sample_kg):
        """测试统计"""
        engine = HypothesisEngine(sample_kg)
        engine.create_hypothesis("h1")
        engine.create_hypothesis("h2")
        h3 = engine.create_hypothesis("h3")
        engine.verify(h3)

        stats = engine.stats()
        assert stats["total"] == 3
        assert stats["verified"] == 1
        assert stats["pending"] == 2


class TestConfidenceEvaluator:
    """置信度评估测试"""

    def test_evaluate_connected_node(self, sample_kg):
        """测试评估高连接节点"""
        evaluator = ConfidenceEvaluator(sample_kg)
        score = evaluator.evaluate_node("B")

        # B有入边和出边，应该有较高置信度
        assert score > 0

    def test_evaluate_isolated_node(self, sample_kg):
        """测试评估孤立节点"""
        evaluator = ConfidenceEvaluator(sample_kg)
        score = evaluator.evaluate_node("isolated")

        assert score == 0.0

    def test_evaluate_nonexistent(self, sample_kg):
        """测试评估不存在的节点"""
        evaluator = ConfidenceEvaluator(sample_kg)
        score = evaluator.evaluate_node("nonexistent")

        assert score == 0.0

    def test_rank_nodes(self, sample_kg):
        """测试节点排序"""
        evaluator = ConfidenceEvaluator(sample_kg)
        rankings = evaluator.rank_nodes()

        assert len(rankings) > 0
        # 应按置信度降序
        for i in range(len(rankings) - 1):
            assert rankings[i][1] >= rankings[i + 1][1]


class TestConflictDetector:
    """冲突检测测试"""

    def test_detect_isolation(self, sample_kg):
        """检测孤立节点"""
        detector = ConflictDetector(sample_kg)
        conflicts = detector.detect_isolation_conflicts()

        assert any(c["node"] == "isolated" for c in conflicts)

    def test_detect_all(self, sample_kg):
        """检测所有冲突"""
        detector = ConflictDetector(sample_kg)
        conflicts = detector.detect_all()

        assert len(conflicts) > 0


class TestExperienceGeneralizer:
    """经验泛化测试"""

    def test_extract_patterns(self, sample_kg):
        """测试提取模式"""
        gen = ExperienceGeneralizer(sample_kg)
        patterns = gen.extract_patterns(min_occurrences=1)

        assert len(patterns) > 0
        # "因果"关系出现2次
        causal = [p for p in patterns if p["pattern"] == "因果"]
        assert len(causal) == 1
        assert causal[0]["occurrences"] >= 2

    def test_generalize_task_names(self, sample_kg):
        """测试任务名泛化"""
        gen = ExperienceGeneralizer(sample_kg)
        rules = gen.generalize_task_names()

        # 没有任务节点时返回空
        assert isinstance(rules, list)


class TestAnomalyDetector:
    """异常检测测试"""

    def test_detect_weight_anomalies(self, sample_kg):
        """测试高权重异常"""
        detector = AnomalyDetector(sample_kg)
        anomalies = detector.detect_weight_anomalies(threshold=0.9)

        # D->E 权重0.95应被检测
        assert len(anomalies) >= 1
        assert any("D" in a["edge"] and "E" in a["edge"] for a in anomalies)

    def test_detect_orphan_chains(self, sample_kg):
        """测试孤立链"""
        detector = AnomalyDetector(sample_kg)
        chains = detector.detect_orphan_chains(min_length=2)

        assert isinstance(chains, list)


class TestDecisionAdvisor:
    """决策建议测试"""

    def test_suggest_next_tasks(self, sample_kg):
        """测试建议下一步"""
        advisor = DecisionAdvisor(sample_kg)
        suggestions = advisor.suggest_next_tasks("A", top_n=3)

        assert len(suggestions) > 0
        # 应包含B和C
        names = [s["task"] for s in suggestions]
        assert "B" in names or "C" in names

    def test_suggest_knowledge_gaps(self, sample_kg):
        """测试知识缺口"""
        advisor = DecisionAdvisor(sample_kg)
        gaps = advisor.suggest_knowledge_gaps()

        # 孤立节点应被建议
        assert any("isolated" in g["node"] for g in gaps)


class TestReasoningEngine:
    """统一推理引擎测试"""

    def test_analyze(self, sample_kg):
        """测试综合分析"""
        engine = ReasoningEngine(sample_kg)
        engine.rule_engine.add_rule("r1", r"A", "分析A相关")

        result = engine.analyze("A")

        assert "rules_matched" in result
        assert "patterns_matched" in result
        assert "suggestions" in result

    def test_full_health_check(self, sample_kg):
        """测试全面健康检查"""
        engine = ReasoningEngine(sample_kg)
        report = engine.full_health_check()

        assert "kg_health" in report
        assert "conflicts" in report
        assert "anomalies" in report
        assert "patterns" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
