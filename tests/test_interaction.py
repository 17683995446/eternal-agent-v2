"""
交互增强模块测试

验证目标：
1. HTTP API路由正确
2. CLI解析正确
3. 知识浏览器工作
4. 任务追踪有效
5. 日志分析有效
6. 监控面板输出
7. 告警通知工作
8. 数据导入导出
9. 系统面板输出
"""

import pytest
import sys
import tempfile
import threading
import time
from pathlib import Path
from http.server import HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError
import json

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from knowledge_graph import KnowledgeGraph
from task_queue import TaskQueue
from interaction import (
    KnowledgeBrowser,
    TaskTracker,
    LogAnalyzer,
    MonitorPanel,
    AlertManager,
    DataImporterExporter,
    SystemPanel,
)
from api import APIHandler, APIServer
from cli import create_parser


@pytest.fixture
def sample_kg():
    """创建测试知识图谱"""
    kg = KnowledgeGraph()
    kg.add_edge("A", "B", weight=0.9, relation="因果")
    kg.add_edge("B", "C", weight=0.8, relation="因果")
    kg.add_node("isolated")
    return kg


class TestKnowledgeBrowser:
    """知识浏览器测试"""

    def test_display_node(self, sample_kg):
        """测试显示节点"""
        browser = KnowledgeBrowser(sample_kg)
        output = browser.display_node("A")

        assert "A" in output
        assert "entity" in output

    def test_display_nonexistent(self, sample_kg):
        """测试显示不存在的节点"""
        browser = KnowledgeBrowser(sample_kg)
        output = browser.display_node("NONEXISTENT")

        assert "不存在" in output

    def test_display_tree(self, sample_kg):
        """测试树形展示"""
        browser = KnowledgeBrowser(sample_kg)
        output = browser.display_tree("A")

        assert "A" in output
        assert "B" in output

    def test_search(self, sample_kg):
        """测试搜索"""
        browser = KnowledgeBrowser(sample_kg)
        results = browser.search("B")

        assert "B" in results


class TestTaskTracker:
    """任务追踪测试"""

    def test_start_and_complete(self):
        """测试追踪完整流程"""
        tracker = TaskTracker()
        tracker.start("task1")
        tracker.complete("task1", "done")

        trace = tracker.get_trace("task1")
        assert trace.state == "completed"
        assert trace.result == "done"

    def test_start_and_fail(self):
        """测试失败追踪"""
        tracker = TaskTracker()
        tracker.start("task1")
        tracker.fail("task1", "error")

        trace = tracker.get_trace("task1")
        assert trace.state == "failed"

    def test_summary(self):
        """测试摘要"""
        tracker = TaskTracker()
        tracker.start("t1")
        tracker.complete("t1")
        tracker.start("t2")
        tracker.fail("t2", "err")

        summary = tracker.summary()
        assert summary["total"] == 2
        assert summary["completed"] == 1
        assert summary["failed"] == 1

    def test_get_failed(self):
        """测试获取失败记录"""
        tracker = TaskTracker()
        tracker.start("ok_task")
        tracker.complete("ok_task")
        tracker.start("fail_task")
        tracker.fail("fail_task", "err")

        failed = tracker.get_failed()
        assert len(failed) == 1
        assert failed[0].task_name == "fail_task"


class TestLogAnalyzer:
    """日志分析测试"""

    def test_count_by_level(self):
        """测试按级别统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            log_path.write_text(
                "2024-01-01 00:00:00 | INFO | test\n"
                "2024-01-01 00:00:01 | ERROR | bad\n"
                "2024-01-01 00:00:02 | INFO | ok\n"
            )

            analyzer = LogAnalyzer(log_path)
            counts = analyzer.count_by_level()

            assert counts.get("INFO", 0) == 2
            assert counts.get("ERROR", 0) == 1

    def test_get_errors(self):
        """测试获取错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            log_path.write_text(
                "INFO: ok\n"
                "ERROR: bad1\n"
                "ERROR: bad2\n"
            )

            analyzer = LogAnalyzer(log_path)
            errors = analyzer.get_errors()

            assert len(errors) == 2

    def test_search(self):
        """测试搜索"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            log_path.write_text(
                "line1 keyword_here\n"
                "line2 nope\n"
                "line3 keyword_here\n"
            )

            analyzer = LogAnalyzer(log_path)
            results = analyzer.search("keyword")

            assert len(results) == 2


class TestMonitorPanel:
    """监控面板测试"""

    def test_snapshot(self):
        """测试快照"""
        panel = MonitorPanel()
        snap = panel.snapshot()

        assert "cpu_percent" in snap
        assert "memory_mb" in snap
        assert "timestamp" in snap

    def test_format_report(self):
        """测试格式化报告"""
        panel = MonitorPanel()
        report = panel.format_report()

        assert "CPU" in report
        assert "内存" in report


class TestAlertManager:
    """告警管理测试"""

    def test_send_alert(self):
        """测试发送告警"""
        manager = AlertManager()
        manager.send("warning", "测试告警")

        recent = manager.get_recent()
        assert len(recent) == 1
        assert recent[0].message == "测试告警"

    def test_handler_called(self):
        """测试处理器被调用"""
        manager = AlertManager()
        received = []

        def handler(alert):
            received.append(alert)

        manager.add_handler(handler)
        manager.send("critical", "紧急告警")

        assert len(received) == 1
        assert received[0].level == "critical"

    def test_get_by_level(self):
        """测试按级别获取"""
        manager = AlertManager()
        manager.send("info", "info1")
        manager.send("warning", "warn1")
        manager.send("info", "info2")

        info_alerts = manager.get_by_level("info")
        assert len(info_alerts) == 2


class TestDataImporterExporter:
    """数据导入导出测试"""

    def test_export_nodes_csv(self, sample_kg):
        """测试导出节点CSV"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nodes.csv"
            count = DataImporterExporter(sample_kg).export_nodes_csv(path)

            assert count > 0
            content = path.read_text()
            assert "A" in content

    def test_export_edges_csv(self, sample_kg):
        """测试导出边CSV"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "edges.csv"
            count = DataImporterExporter(sample_kg).export_edges_csv(path)

            assert count > 0

    def test_import_nodes_csv(self):
        """测试导入节点CSV"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph()
            path = Path(tmpdir) / "import.csv"
            path.write_text("name,type,valid,created_at,updated_at\nX,entity,True,2024-01-01,2024-01-01\n")

            count = DataImporterExporter(kg).import_nodes_csv(path)
            assert count == 1
            assert kg.has_node("X")

    def test_export_import_json(self, sample_kg):
        """测试JSON导出导入"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "data.json"

            # 导出
            DataImporterExporter(sample_kg).export_json(path)
            assert path.exists()

            # 导入到新图谱
            new_kg = KnowledgeGraph()
            result = DataImporterExporter(new_kg).import_json(path)

            assert result["nodes"] > 0
            assert result["edges"] > 0
            assert new_kg.has_node("A")


class TestSystemPanel:
    """系统面板测试"""

    def test_full_report(self):
        """测试完整报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            queue = TaskQueue()

            # 创建模拟agent
            from eternal_agent import EternalSelfAgent
            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = queue
            agent._initialized = True

            panel = SystemPanel(agent)
            report = panel.full_report()

            assert "系统状态" in report
            assert "知识图谱" in report
            assert "任务队列" in report
            assert "资源监控" in report


class TestCLIParser:
    """CLI解析测试"""

    def test_parse_status(self):
        """测试解析status命令"""
        parser = create_parser()
        args = parser.parse_args(["status"])
        assert args.command == "status"

    def test_parse_kg_stats(self):
        """测试解析kg stats命令"""
        parser = create_parser()
        args = parser.parse_args(["kg", "stats"])
        assert args.command == "kg"
        assert args.kg_command == "stats"

    def test_parse_task_add(self):
        """测试解析task add命令"""
        parser = create_parser()
        args = parser.parse_args(["task", "add", "my_task", "--priority", "5"])
        assert args.command == "task"
        assert args.task_command == "add"
        assert args.name == "my_task"
        assert args.priority == 5

    def test_parse_run(self):
        """测试解析run命令"""
        parser = create_parser()
        args = parser.parse_args(["run", "--port", "9090"])
        assert args.command == "run"
        assert args.port == 9090


class TestAPIRoutes:
    """HTTP API路由测试"""

    def test_api_docs(self):
        """测试API文档路由"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            queue = TaskQueue()

            from eternal_agent import EternalSelfAgent
            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = queue
            agent._initialized = True

            APIHandler.agent = agent

            server = HTTPServer(("127.0.0.1", 0), APIHandler)
            port = server.server_address[1]

            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            time.sleep(0.3)

            try:
                resp = urlopen(f"http://127.0.0.1:{port}/")
                data = json.loads(resp.read().decode())
                assert "routes" in data
            finally:
                server.shutdown()

    def test_api_health(self):
        """测试健康检查路由"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            queue = TaskQueue()

            from eternal_agent import EternalSelfAgent
            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = queue
            agent._initialized = True

            APIHandler.agent = agent

            server = HTTPServer(("127.0.0.1", 0), APIHandler)
            port = server.server_address[1]

            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            time.sleep(0.3)

            try:
                resp = urlopen(f"http://127.0.0.1:{port}/health")
                data = json.loads(resp.read().decode())
                assert "status" in data
            finally:
                server.shutdown()

    def test_api_status(self):
        """测试状态路由"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            queue = TaskQueue()

            from eternal_agent import EternalSelfAgent
            agent = EternalSelfAgent()
            agent.knowledge_graph = kg
            agent.task_queue = queue
            agent._initialized = True

            APIHandler.agent = agent

            server = HTTPServer(("127.0.0.1", 0), APIHandler)
            port = server.server_address[1]

            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            time.sleep(0.3)

            try:
                resp = urlopen(f"http://127.0.0.1:{port}/status")
                data = json.loads(resp.read().decode())
                assert "state" in data
                assert "run_counter" in data
            finally:
                server.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
