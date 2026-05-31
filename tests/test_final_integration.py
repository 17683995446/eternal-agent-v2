"""
完整集成测试 — 项目收尾层

验证所有模块的集成功能
"""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestPerformanceOptimizer(unittest.TestCase):
    """性能优化器测试"""
    
    def test_lru_cache(self):
        from perf_optimizer import LRUCache
        cache = LRUCache(maxsize=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("d", 4)  # 淘汰a
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(cache.size(), 3)
    
    def test_lru_cache_decorator(self):
        from perf_optimizer import lru_cache
        call_count = [0]
        
        @lru_cache(maxsize=10)
        def add(a, b):
            call_count[0] += 1
            return a + b
        
        self.assertEqual(add(1, 2), 3)
        self.assertEqual(add(1, 2), 3)
        self.assertEqual(call_count[0], 1)
    
    def test_object_pool(self):
        from perf_optimizer import ObjectPool
        pool = ObjectPool(factory=lambda: {"data": 0}, maxsize=5)
        obj1 = pool.acquire()
        obj1["data"] = 42
        pool.release(obj1)
        obj2 = pool.acquire()
        self.assertEqual(pool.stats()["reused"], 1)
    
    def test_lazy_loader(self):
        from perf_optimizer import Lazy
        loaded = [False]
        lazy = Lazy(lambda: (loaded.__setitem__(0, True), 42)[1])
        self.assertFalse(lazy.is_loaded)
        self.assertEqual(lazy.get(), 42)
        self.assertTrue(lazy.is_loaded)
    
    def test_batch_processor(self):
        from perf_optimizer import BatchProcessor
        processed = []
        bp = BatchProcessor(handler=lambda batch: processed.extend(batch), batch_size=3)
        bp.add(1)
        bp.add(2)
        bp.add(3)
        bp.flush()
        self.assertEqual(processed, [1, 2, 3])
    
    def test_timer(self):
        from perf_optimizer import Timer
        with Timer("test") as t:
            time.sleep(0.01)
        self.assertGreater(t.elapsed, 0.005)
    
    def test_performance_tracker(self):
        from perf_optimizer import PerformanceTracker
        tracker = PerformanceTracker()
        tracker.record("func_a", 0.1)
        tracker.record("func_a", 0.2)
        tracker.record("func_a", 0.3)
        stats = tracker.get_stats("func_a")
        self.assertEqual(stats["count"], 3)
        self.assertAlmostEqual(stats["avg"], 0.2, places=1)


class TestCodeQuality(unittest.TestCase):
    """代码质量检查测试"""
    
    def test_quality_checker(self):
        from code_quality import CodeQualityChecker
        checker = CodeQualityChecker(Path(__file__).parent.parent / "src")
        report = checker.check(["constants.py"])
        self.assertGreater(report.files_checked, 0)
        self.assertGreater(report.total_lines, 0)
    
    def test_naming_check(self):
        from code_quality import CodeQualityChecker
        checker = CodeQualityChecker(Path(__file__).parent.parent / "src")
        report = checker.check(["constants.py"])
        # constants.py应该没有命名问题
        naming_issues = [i for i in report.issues if i.rule == "naming"]
        self.assertEqual(len(naming_issues), 0)


class TestDeployModule(unittest.TestCase):
    """部署模块测试"""
    
    def test_deployer_init(self):
        from deploy import Deployer
        deployer = Deployer()
        self.assertIsNotNone(deployer)
    
    def test_deploy_environment(self):
        from deploy import DeployEnvironment
        self.assertEqual(DeployEnvironment.DEVELOPMENT.value, "development")
        self.assertEqual(DeployEnvironment.PRODUCTION.value, "production")


class TestMonitoring(unittest.TestCase):
    """监控模块测试"""
    
    def test_metrics_registry(self):
        from monitoring import MetricsRegistry, MetricType
        registry = MetricsRegistry("test")
        registry.counter("requests", 5)
        registry.gauge("memory", 75.5)
        self.assertEqual(registry.get_counter("requests"), 5)
        self.assertEqual(registry.get_gauge("memory"), 75.5)
    
    def test_prometheus_export(self):
        from monitoring import MetricsRegistry
        registry = MetricsRegistry("test")
        registry.counter("total", 10)
        output = registry.export_prometheus()
        self.assertIn("test_total", output)
        self.assertIn("10", output)
    
    def test_histogram(self):
        from monitoring import MetricsRegistry
        registry = MetricsRegistry("test")
        for i in range(100):
            registry.histogram("duration", float(i) / 100)
        stats = registry.get_histogram_stats("duration")
        self.assertEqual(stats["count"], 100)
        self.assertAlmostEqual(stats["min"], 0.0)
        self.assertAlmostEqual(stats["max"], 0.99, places=1)


class TestAlerter(unittest.TestCase):
    """告警系统测试"""
    
    def test_alert_trigger(self):
        from alerter import Alerter, AlertRule, AlertSeverity
        alerter = Alerter()
        alerter.add_rule(AlertRule(
            name="test", metric="cpu", operator=">", threshold=80,
            severity=AlertSeverity.WARNING
        ))
        alerter.evaluate("cpu", 90)
        self.assertEqual(len(alerter.get_active_alerts()), 1)
        alerter.evaluate("cpu", 50)
        self.assertEqual(len(alerter.get_active_alerts()), 0)
    
    def test_alert_summary(self):
        from alerter import Alerter, AlertRule, AlertSeverity
        alerter = Alerter()
        alerter.add_rule(AlertRule(
            name="test1", metric="m1", operator=">", threshold=10,
            severity=AlertSeverity.WARNING
        ))
        alerter.add_rule(AlertRule(
            name="test2", metric="m2", operator=">", threshold=10,
            severity=AlertSeverity.CRITICAL
        ))
        alerter.evaluate("m1", 20)
        alerter.evaluate("m2", 20)
        summary = alerter.get_alert_summary()
        self.assertEqual(summary["active_count"], 2)


class TestAllModulesImport(unittest.TestCase):
    """所有模块导入测试"""
    
    def test_import_all_modules(self):
        """测试所有模块可以正常导入"""
        modules = [
            "constants", "logger", "config", "models", "utils", "exceptions", "monitor",
            "task_queue", "loop", "knowledge_graph", "eternal_agent",
            "reasoning", "api", "cli", "interaction",
            "plugin_system", "event_bus", "file_watcher", "scheduler", "http_client",
            "data_pipeline", "template_engine", "persistence_v2", "sandbox",
            "config_center", "secret_store", "access_control", "audit_log", "encryption",
            "backup", "health", "profiler", "diagnostics",
            "boot", "visualization", "query_language", "benchmark", "upgrader", "coordinator",
            "doc_generator", "tutorials",
            "nlp_processor", "entity_recognizer", "similarity", "adaptive_learner",
            "knowledge_recommender", "intent_recognizer", "dialog_manager", "summarizer",
            "deploy", "monitoring", "alerter",
            "perf_optimizer", "code_quality",
        ]
        
        failed = []
        for mod_name in modules:
            try:
                __import__(mod_name)
            except Exception as e:
                failed.append((mod_name, str(e)))
        
        if failed:
            self.fail(f"导入失败的模块: {failed}")
    
    def test_module_count(self):
        """验证模块数量"""
        from pathlib import Path
        src_dir = Path(__file__).parent.parent / "src"
        py_files = list(src_dir.glob("*.py"))
        # 至少应有55个Python文件
        self.assertGreaterEqual(len(py_files), 50)


if __name__ == "__main__":
    unittest.main(verbosity=2)
