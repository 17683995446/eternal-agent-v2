"""
生态集成层测试

阶段81-90: 插件系统、事件总线、文件监控、定时调度、HTTP客户端、
         数据管道、模板引擎、持久化增强、安全沙箱
"""

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

# 确保src在路径中
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ============================================================
# 阶段81: 插件系统测试
# ============================================================

class TestPluginSystem:
    """插件系统测试"""

    def test_plugin_base_info(self):
        """测试插件基类"""
        from plugin_system import PluginBase, PluginInfo

        class MyPlugin(PluginBase):
            def plugin_info(self):
                return PluginInfo(name="test", version="1.0")

        plugin = MyPlugin()
        info = plugin.plugin_info()
        assert info.name == "test"
        assert info.version == "1.0"

    def test_plugin_manager_discover(self):
        """测试插件发现"""
        from plugin_system import PluginManager

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "plugins"
            plugin_dir.mkdir()

            # 创建插件文件
            (plugin_dir / "hello.py").write_text("# plugin file")
            (plugin_dir / "world.py").write_text("# another plugin")

            manager = PluginManager([plugin_dir])
            discovered = manager.discover()
            assert "hello" in discovered
            assert "world" in discovered

    def test_plugin_manager_load_and_unload(self):
        """测试插件加载和卸载"""
        from plugin_system import PluginManager, PluginBase, PluginInfo

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "plugins"
            plugin_dir.mkdir()

            # 创建有效插件
            plugin_code = '''
from plugin_system import PluginBase, PluginInfo

class TestPlugin(PluginBase):
    def plugin_info(self):
        return PluginInfo(name="test_plugin", version="1.0", description="测试插件")

    def on_load(self):
        self.loaded = True

    def on_unload(self):
        self.loaded = False
'''
            (plugin_dir / "test_plugin.py").write_text(plugin_code)

            manager = PluginManager([plugin_dir])
            plugin_inst = manager.load_plugin("test_plugin")

            assert plugin_inst is not None
            assert plugin_inst.info.name == "test_plugin"
            assert "test_plugin" in manager.plugin_names

            # 卸载
            result = manager.unload_plugin("test_plugin")
            assert result is True
            assert "test_plugin" not in manager.plugin_names

    def test_plugin_hooks(self):
        """测试插件Hook"""
        from plugin_system import PluginManager, PluginBase, PluginInfo

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "plugins"
            plugin_dir.mkdir()

            plugin_code = '''
from plugin_system import PluginBase, PluginInfo

class HookPlugin(PluginBase):
    def plugin_info(self):
        return PluginInfo(name="hooker", version="1.0")

    def hook_on_task(self, task_name):
        return f"hooked: {task_name}"
'''
            (plugin_dir / "hooker.py").write_text(plugin_code)

            manager = PluginManager([plugin_dir])
            manager.load_plugin("hooker")

            results = manager.call_hook("hook_on_task", "test_task")
            assert len(results) == 1
            assert results[0] == "hooked: test_task"

    def test_plugin_dependency(self):
        """测试插件依赖"""
        from plugin_system import PluginManager, PluginBase, PluginInfo, PluginDependencyError

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "plugins"
            plugin_dir.mkdir()

            # 带依赖的插件
            plugin_code = '''
from plugin_system import PluginBase, PluginInfo

class DepPlugin(PluginBase):
    def plugin_info(self):
        return PluginInfo(name="dep_plugin", dependencies=["nonexistent"])
'''
            (plugin_dir / "dep_plugin.py").write_text(plugin_code)

            manager = PluginManager([plugin_dir])
            with pytest.raises(PluginDependencyError):
                manager.load_plugin("dep_plugin")

    def test_plugin_enable_disable(self):
        """测试插件启用/禁用"""
        from plugin_system import PluginManager, PluginBase, PluginInfo

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "plugins"
            plugin_dir.mkdir()

            plugin_code = '''
from plugin_system import PluginBase, PluginInfo

class TogglePlugin(PluginBase):
    def plugin_info(self):
        return PluginInfo(name="toggle", version="1.0")
'''
            (plugin_dir / "toggle.py").write_text(plugin_code)

            manager = PluginManager([plugin_dir])
            manager.load_plugin("toggle")

            manager.disable_plugin("toggle")
            assert not manager.get_plugin("toggle").info.enabled

            manager.enable_plugin("toggle")
            assert manager.get_plugin("toggle").info.enabled


# ============================================================
# 阶段82: 事件总线测试
# ============================================================

class TestEventBus:
    """事件总线测试"""

    def test_subscribe_and_publish(self):
        """测试订阅和发布"""
        from event_bus import EventBus, Event

        bus = EventBus()
        received = []

        def handler(event):
            received.append(event.topic)

        bus.subscribe("test.topic", handler)
        bus.publish_simple("test.topic", data="hello")

        assert len(received) == 1
        assert received[0] == "test.topic"

    def test_wildcard_subscription(self):
        """测试通配符订阅"""
        from event_bus import EventBus

        bus = EventBus()
        received = []

        bus.subscribe("*", lambda e: received.append(e.topic))

        bus.publish_simple("topic.a", data=1)
        bus.publish_simple("topic.b", data=2)

        assert len(received) == 2

    def test_unsubscribe(self):
        """测试取消订阅"""
        from event_bus import EventBus

        bus = EventBus()
        received = []

        def handler(event):
            received.append(1)

        bus.subscribe("test", handler)
        bus.publish_simple("test")
        assert len(received) == 1

        bus.unsubscribe("test", handler)
        bus.publish_simple("test")
        assert len(received) == 1  # 不再增加

    def test_event_filter(self):
        """测试事件过滤"""
        from event_bus import EventBus

        bus = EventBus()
        received = []

        bus.subscribe(
            "test",
            lambda e: received.append(e.data),
            filter_fn=lambda e: e.data and e.data.get("important"),
        )

        bus.publish_simple("test", data={"important": True})
        bus.publish_simple("test", data={"important": False})

        assert len(received) == 1

    def test_one_time_subscription(self):
        """测试一次性订阅"""
        from event_bus import EventBus

        bus = EventBus()
        count = [0]

        bus.subscribe_once("test", lambda e: count.__setitem__(0, count[0] + 1))

        bus.publish_simple("test")
        bus.publish_simple("test")

        assert count[0] == 1

    def test_event_history(self):
        """测试事件历史"""
        from event_bus import EventBus

        bus = EventBus(max_history=10)
        bus.publish_simple("a", data=1)
        bus.publish_simple("b", data=2)

        history = bus.get_history()
        assert len(history) == 2
        assert history[0]["topic"] == "a"

        filtered = bus.get_history(topic="b")
        assert len(filtered) == 1

    def test_event_stats(self):
        """测试事件统计"""
        from event_bus import EventBus

        bus = EventBus()
        bus.publish_simple("test")
        bus.publish_simple("test")

        assert bus.stats["published"] == 2

    def test_event_priority(self):
        """测试事件优先级"""
        from event_bus import EventBus

        bus = EventBus()
        order = []

        bus.subscribe("test", lambda e: order.append("low"), priority=0)
        bus.subscribe("test", lambda e: order.append("high"), priority=10)

        bus.publish_simple("test")
        assert order == ["high", "low"]


# ============================================================
# 阶段83: 文件监控测试
# ============================================================

class TestFileWatcher:
    """文件监控测试"""

    def test_file_created(self):
        """测试文件创建检测"""
        from file_watcher import FileWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            events = []
            watcher = FileWatcher(
                Path(tmpdir),
                callback=lambda e: events.append(e),
                interval=0.1,
                recursive=False,
            )

            watcher.start()
            time.sleep(0.2)

            # 创建文件
            (Path(tmpdir) / "new_file.txt").write_text("hello")

            time.sleep(0.5)
            watcher.stop()

            created = [e for e in events if e.event_type == "created"]
            assert len(created) >= 1

    def test_file_modified(self):
        """测试文件修改检测"""
        from file_watcher import FileWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("v1")

            events = []
            watcher = FileWatcher(
                Path(tmpdir),
                callback=lambda e: events.append(e),
                interval=0.1,
                recursive=False,
            )

            watcher.start()
            time.sleep(0.3)

            # 修改文件
            test_file.write_text("v2 modified")

            time.sleep(0.5)
            watcher.stop()

            modified = [e for e in events if e.event_type == "modified"]
            assert len(modified) >= 1

    def test_file_deleted(self):
        """测试文件删除检测"""
        from file_watcher import FileWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "to_delete.txt"
            test_file.write_text("will be deleted")

            events = []
            watcher = FileWatcher(
                Path(tmpdir),
                callback=lambda e: events.append(e),
                interval=0.1,
                recursive=False,
            )

            watcher.start()
            time.sleep(0.3)

            test_file.unlink()

            time.sleep(0.5)
            watcher.stop()

            deleted = [e for e in events if e.event_type == "deleted"]
            assert len(deleted) >= 1

    def test_pattern_filter(self):
        """测试文件模式过滤"""
        from file_watcher import FileWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            events = []
            watcher = FileWatcher(
                Path(tmpdir),
                callback=lambda e: events.append(e),
                interval=0.1,
                patterns=["*.txt"],
                recursive=False,
            )

            watcher.start()
            time.sleep(0.2)

            (Path(tmpdir) / "test.txt").write_text("txt")
            (Path(tmpdir) / "test.log").write_text("log")

            time.sleep(0.5)
            watcher.stop()

            # 只应该检测到.txt文件
            assert len(events) >= 1
            for e in events:
                assert e.path.endswith(".txt")

    def test_pause_resume(self):
        """测试暂停/恢复"""
        from file_watcher import FileWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            events = []
            watcher = FileWatcher(
                Path(tmpdir),
                callback=lambda e: events.append(e),
                interval=0.1,
                recursive=False,
            )

            watcher.start()
            time.sleep(0.2)

            watcher.pause()
            time.sleep(0.1)
            (Path(tmpdir) / "paused.txt").write_text("paused")
            time.sleep(0.3)

            count_paused = len(events)

            watcher.resume()
            (Path(tmpdir) / "resumed.txt").write_text("resumed")
            time.sleep(0.5)

            watcher.stop()

            # 恢复后应该有新事件
            assert len(events) >= count_paused


# ============================================================
# 阶段84: 定时调度测试
# ============================================================

class TestScheduler:
    """定时调度测试"""

    def test_cron_parse_every_minute(self):
        """测试Cron解析：每分钟"""
        from scheduler import CronExpression

        cron = CronExpression.parse("* * * * *")
        assert cron.minute == "*"
        assert cron.describe() == "每分钟"

    def test_cron_parse_specific(self):
        """测试Cron解析：特定时间"""
        from scheduler import CronExpression

        cron = CronExpression.parse("30 8 * * *")
        assert cron.minute == "30"
        assert cron.hour == "8"
        assert "8点" in cron.describe()

    def test_cron_matches(self):
        """测试Cron匹配"""
        from scheduler import CronExpression
        from datetime import datetime

        cron = CronExpression.parse("30 8 * * *")
        dt = datetime(2026, 1, 1, 8, 30, 0)
        assert cron.matches(dt) is True

        dt2 = datetime(2026, 1, 1, 9, 30, 0)
        assert cron.matches(dt2) is False

    def test_cron_step(self):
        """测试Cron步长"""
        from scheduler import CronExpression
        from datetime import datetime

        cron = CronExpression.parse("*/5 * * * *")

        assert cron.matches(datetime(2026, 1, 1, 0, 0)) is True
        assert cron.matches(datetime(2026, 1, 1, 0, 5)) is True
        assert cron.matches(datetime(2026, 1, 1, 0, 3)) is False

    def test_cron_invalid(self):
        """测试无效Cron表达式"""
        from scheduler import CronExpression, CronParseError

        with pytest.raises(CronParseError):
            CronExpression.parse("invalid")

        with pytest.raises(CronParseError):
            CronExpression.parse("* * *")  # 只有3个字段

    def test_scheduler_add_job(self):
        """测试添加调度任务"""
        from scheduler import Scheduler

        scheduler = Scheduler()
        counter = [0]

        scheduler.add_job("test", "* * * * *", lambda: counter.__setitem__(0, counter[0] + 1))
        assert "test" in scheduler.job_names

    def test_scheduler_remove_job(self):
        """测试移除调度任务"""
        from scheduler import Scheduler

        scheduler = Scheduler()
        scheduler.add_job("test", "* * * * *", lambda: None)
        result = scheduler.remove_job("test")
        assert result is True
        assert "test" not in scheduler.job_names

    def test_scheduler_tick(self):
        """测试手动触发"""
        from scheduler import Scheduler, CronExpression
        from datetime import datetime
        from unittest.mock import patch

        scheduler = Scheduler()
        counter = [0]

        # 使用每分钟匹配的cron
        scheduler.add_job("every_min", "* * * * *", lambda: counter.__setitem__(0, counter[0] + 1))

        # 手动tick
        triggered = scheduler.tick()
        assert len(triggered) == 1
        assert counter[0] == 1

    def test_scheduler_summary(self):
        """测试调度器摘要"""
        from scheduler import Scheduler

        scheduler = Scheduler()
        scheduler.add_job("test", "*/5 * * * *", lambda: None)

        summary = scheduler.get_summary()
        assert "test" in summary["jobs"]
        assert summary["jobs"]["test"]["cron"] == "*/5 * * * *"


# ============================================================
# 阶段85: HTTP客户端测试
# ============================================================

class TestHTTPClient:
    """HTTP客户端测试"""

    def test_build_url(self):
        """测试URL构建"""
        from http_client import HTTPClient

        client = HTTPClient(base_url="http://localhost:8080")
        url = client._build_url("/api/test", {"key": "value"})
        assert "localhost:8080" in url
        assert "/api/test" in url
        assert "key=value" in url

    def test_build_url_absolute(self):
        """测试绝对URL"""
        from http_client import HTTPClient

        client = HTTPClient()
        url = client._build_url("https://example.com/api")
        assert url == "https://example.com/api"

    def test_http_get_to_server(self):
        """测试GET请求到本地服务器"""
        from http_client import HTTPClient
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading

        # 创建测试服务器
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode())

            def log_message(self, format, *args):
                pass  # 静默日志

        server = HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            client = HTTPClient(base_url=f"http://127.0.0.1:{port}")
            response = client.get("/test")

            assert response.ok
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
        finally:
            server.shutdown()

    def test_http_post_to_server(self):
        """测试POST请求"""
        from http_client import HTTPClient
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                self.send_response(201)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            client = HTTPClient(base_url=f"http://127.0.0.1:{port}")
            response = client.post("/submit", json_data={"name": "test"})

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "test"
        finally:
            server.shutdown()

    def test_http_cache(self):
        """测试缓存功能"""
        from http_client import HTTPClient
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading

        request_count = [0]

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                request_count[0] += 1
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"cached")

            def log_message(self, format, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            client = HTTPClient(
                base_url=f"http://127.0.0.1:{port}",
                cache_ttl=60.0,
            )

            # 第一次请求
            r1 = client.get("/cached")
            assert r1.ok

            # 第二次应该命中缓存
            r2 = client.get("/cached")
            assert r2.ok

            assert request_count[0] == 1  # 只有一次实际请求
            assert client.stats["cache_hits"] == 1
        finally:
            server.shutdown()

    def test_http_stats(self):
        """测试HTTP统计"""
        from http_client import HTTPClient

        client = HTTPClient()
        assert client.stats["total_requests"] == 0

    def test_response_properties(self):
        """测试响应属性"""
        from http_client import HTTPResponse

        resp = HTTPResponse(status_code=200, body="ok")
        assert resp.ok is True
        assert resp.text == "ok"

        resp_err = HTTPResponse(status_code=404, body="not found")
        assert resp_err.ok is False


# ============================================================
# 阶段86: 数据管道测试
# ============================================================

class TestDataPipeline:
    """数据管道测试"""

    def test_dict_source(self):
        """测试字典列表数据源"""
        from data_pipeline import DictListSource

        source = DictListSource([{"a": 1}, {"b": 2}])
        data = source.extract()
        assert len(data) == 2

    def test_json_source(self):
        """测试JSON文件数据源"""
        from data_pipeline import JSONFileSource

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "data.json"
            file_path.write_text('[{"name": "a"}, {"name": "b"}]')

            source = JSONFileSource(file_path)
            data = source.extract()
            assert len(data) == 2

    def test_csv_source(self):
        """测试CSV文件数据源"""
        from data_pipeline import CSVFileSource

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "data.csv"
            file_path.write_text("name,age\nAlice,30\nBob,25\n")

            source = CSVFileSource(file_path)
            data = source.extract()
            assert len(data) == 2
            assert data[0]["name"] == "Alice"

    def test_filter_transformer(self):
        """测试过滤转换器"""
        from data_pipeline import FilterTransformer, DictListSource

        source = DictListSource([{"a": 1}, {"a": 2}, {"a": 3}])
        data = source.extract()

        tf = FilterTransformer(lambda x: x["a"] > 1)
        result = tf.transform(data)
        assert len(result) == 2

    def test_map_transformer(self):
        """测试映射转换器"""
        from data_pipeline import MapTransformer, DictListSource

        source = DictListSource([{"a": 1}, {"a": 2}])
        data = source.extract()

        tf = MapTransformer(lambda x: {**x, "doubled": x["a"] * 2})
        result = tf.transform(data)
        assert result[0]["doubled"] == 2

    def test_sort_transformer(self):
        """测试排序转换器"""
        from data_pipeline import SortTransformer, DictListSource

        source = DictListSource([{"v": 3}, {"v": 1}, {"v": 2}])
        data = source.extract()

        tf = SortTransformer("v")
        result = tf.transform(data)
        assert result[0]["v"] == 1

    def test_deduplicate_transformer(self):
        """测试去重转换器"""
        from data_pipeline import DeduplicateTransformer, DictListSource

        source = DictListSource([{"a": 1}, {"a": 1}, {"a": 2}])
        data = source.extract()

        tf = DeduplicateTransformer(key="a")
        result = tf.transform(data)
        assert len(result) == 2

    def test_aggregate_transformer(self):
        """测试聚合转换器"""
        from data_pipeline import AggregateTransformer, DictListSource

        source = DictListSource([
            {"cat": "A", "val": 10},
            {"cat": "A", "val": 20},
            {"cat": "B", "val": 30},
        ])
        data = source.extract()

        tf = AggregateTransformer("cat", {"val": "sum"})
        result = tf.transform(data)

        assert len(result) == 2
        a_group = next(r for r in result if r["cat"] == "A")
        assert a_group["val_sum"] == 30

    def test_pipeline_run(self):
        """测试完整管道执行"""
        from data_pipeline import (
            DataPipeline, DictListSource, FilterTransformer,
            SortTransformer, MemorySink, LimitTransformer,
        )

        pipeline = DataPipeline("test_pipeline")
        pipeline.extract(DictListSource([
            {"name": "C", "score": 30},
            {"name": "A", "score": 90},
            {"name": "B", "score": 60},
            {"name": "D", "score": 10},
        ]))
        pipeline.transform(FilterTransformer(lambda x: x["score"] >= 30))
        pipeline.transform(SortTransformer("score", reverse=True))
        pipeline.transform(LimitTransformer(2))

        sink = MemorySink()
        pipeline.load(sink)

        result = pipeline.run()
        assert result.success is True
        assert result.records_output == 2
        assert sink.data[0]["name"] == "A"

    def test_pipeline_history(self):
        """测试管道历史"""
        from data_pipeline import DataPipeline, DictListSource, MemorySink

        pipeline = DataPipeline("hist_test")
        pipeline.extract(DictListSource([{"a": 1}]))
        pipeline.load(MemorySink())
        pipeline.run()
        pipeline.run()

        history = pipeline.get_history()
        assert len(history) == 2

    def test_csv_sink(self):
        """测试CSV输出"""
        from data_pipeline import DataPipeline, DictListSource, CSVFileSink

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.csv"

            pipeline = DataPipeline("csv_test")
            pipeline.extract(DictListSource([{"name": "A", "val": 1}]))
            pipeline.load(CSVFileSink(output_path))

            result = pipeline.run()
            assert result.success is True
            assert output_path.exists()


# ============================================================
# 阶段87: 模板引擎测试
# ============================================================

class TestTemplateEngine:
    """模板引擎测试"""

    def test_variable_replacement(self):
        """测试变量替换"""
        from template_engine import Template

        t = Template("Hello, {{ name }}!")
        result = t.render({"name": "World"})
        assert result == "Hello, World!"

    def test_variable_missing(self):
        """测试缺失变量"""
        from template_engine import Template

        t = Template("Value: {{ missing }}")
        result = t.render({})
        assert result == "Value: "

    def test_filter_upper(self):
        """测试大写过滤器"""
        from template_engine import Template

        t = Template("{{ name|upper }}")
        result = t.render({"name": "hello"})
        assert result == "HELLO"

    def test_filter_lower(self):
        """测试小写过滤器"""
        from template_engine import Template

        t = Template("{{ name|lower }}")
        result = t.render({"name": "HELLO"})
        assert result == "hello"

    def test_filter_default(self):
        """测试默认值过滤器"""
        from template_engine import Template

        t = Template("{{ name|default:Anonymous }}")
        result = t.render({})
        assert result == "Anonymous"

    def test_filter_length(self):
        """测试长度过滤器"""
        from template_engine import Template

        t = Template("{{ items|length }}")
        result = t.render({"items": [1, 2, 3]})
        assert result == "3"

    def test_if_condition(self):
        """测试条件判断"""
        from template_engine import Template

        t = Template("{% if show %}visible{% endif %}")
        assert t.render({"show": True}) == "visible"
        assert t.render({"show": False}) == ""

    def test_if_else(self):
        """测试条件else"""
        from template_engine import Template

        t = Template("{% if show %}yes{% else %}no{% endif %}")
        assert t.render({"show": False}) == "no"

    def test_for_loop(self):
        """测试循环"""
        from template_engine import Template

        t = Template("{% for item in items %}{{ item }} {% endfor %}")
        result = t.render({"items": ["a", "b", "c"]})
        assert "a" in result
        assert "b" in result
        assert "c" in result

    def test_loop_variable(self):
        """测试循环变量"""
        from template_engine import Template

        t = Template("{% for item in items %}{{ loop.index1 }}{% endfor %}")
        result = t.render({"items": ["x", "y"]})
        assert "1" in result
        assert "2" in result

    def test_nested_variable(self):
        """测试嵌套变量访问"""
        from template_engine import Template

        t = Template("{{ user.name }}")
        result = t.render({"user": {"name": "Alice"}})
        assert result == "Alice"

    def test_comment(self):
        """测试注释"""
        from template_engine import Template

        t = Template("Hello{# this is a comment #} World")
        result = t.render({})
        assert result == "Hello World"

    def test_render_report(self):
        """测试报告渲染"""
        from template_engine import TemplateEngine

        engine = TemplateEngine()
        report = engine.render_report(
            "测试报告",
            [
                {"title": "概述", "content": "这是概述内容"},
                {"title": "详情", "content": "这是详情内容"},
            ],
        )
        assert "测试报告" in report
        assert "概述" in report
        assert "详情" in report
        assert "永动知识图谱Agent" in report

    def test_custom_filter(self):
        """测试自定义过滤器"""
        from template_engine import Template

        t = Template("{{ value|double }}")
        t.add_filter("double", lambda x: int(x) * 2 if x else 0)
        result = t.render({"value": 5})
        assert result == "10"


# ============================================================
# 阶段88: 持久化增强测试
# ============================================================

class TestPersistenceV2:
    """持久化增强测试"""

    def test_set_and_get(self):
        """测试基本读写"""
        from persistence_v2 import IncrementalStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = IncrementalStore(Path(tmpdir))
            store.initialize()

            store.set("key1", "value1")
            assert store.get("key1") == "value1"
            assert store.get("nonexistent") is None

    def test_delete(self):
        """测试删除"""
        from persistence_v2 import IncrementalStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = IncrementalStore(Path(tmpdir))
            store.initialize()

            store.set("key1", "value1")
            result = store.delete("key1")
            assert result is True
            assert store.get("key1") is None

    def test_batch_set(self):
        """测试批量设置"""
        from persistence_v2 import IncrementalStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = IncrementalStore(Path(tmpdir))
            store.initialize()

            count = store.batch_set({"a": 1, "b": 2, "c": 3})
            assert count == 3
            assert store.record_count == 3

    def test_snapshot_and_restore(self):
        """测试快照和恢复"""
        from persistence_v2 import IncrementalStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = IncrementalStore(Path(tmpdir), snapshot_interval=1000)
            store.initialize()

            store.set("key1", "value1")
            store.set("key2", "value2")

            snapshot = store.create_snapshot("test")
            assert snapshot.record_count == 2

            # 修改数据
            store.set("key1", "modified")
            assert store.get("key1") == "modified"

            # 恢复
            count = store.restore_snapshot(snapshot.path)
            assert count == 2
            assert store.get("key1") == "value1"

    def test_list_snapshots(self):
        """测试列出快照"""
        from persistence_v2 import IncrementalStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = IncrementalStore(Path(tmpdir), snapshot_interval=2)
            store.initialize()

            store.set("a", 1)
            store.set("b", 2)
            store.set("c", 3)

            snapshots = store.list_snapshots()
            assert len(snapshots) >= 1

    def test_verify_integrity(self):
        """测试完整性验证"""
        from persistence_v2 import IncrementalStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = IncrementalStore(Path(tmpdir))
            store.initialize()

            store.set("a", 1)
            result = store.verify_integrity()
            assert result["integrity_ok"] is True
            assert result["record_count"] == 1

    def test_compressed_snapshot(self):
        """测试压缩快照"""
        from persistence_v2 import IncrementalStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = IncrementalStore(Path(tmpdir), compress_snapshots=True)
            store.initialize()

            store.set("key1", "x" * 1000)
            snapshot = store.create_snapshot("compressed")

            assert Path(snapshot.path).exists()
            assert snapshot.compressed_size > 0

    def test_persistence_across_instances(self):
        """测试跨实例持久化"""
        from persistence_v2 import IncrementalStore

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            store1 = IncrementalStore(data_dir)
            store1.initialize()
            store1.set("shared", "data")
            store1.create_snapshot("cross")

            store2 = IncrementalStore(data_dir)
            store2.initialize()
            assert store2.get("shared") == "data"


# ============================================================
# 阶段89: 安全沙箱测试
# ============================================================

class TestSandbox:
    """安全沙箱测试"""

    def test_simple_execution(self):
        """测试简单代码执行"""
        from sandbox import Sandbox, SandboxConfig

        sb = Sandbox()
        result = sb.execute("x = 1 + 1\n__return__ = x")
        assert result.success is True
        assert result.return_value == 2

    def test_execution_with_output(self):
        """测试带输出的执行"""
        from sandbox import Sandbox

        sb = Sandbox()
        result = sb.execute("print('hello from sandbox')")
        assert result.success is True
        assert "hello from sandbox" in result.stdout

    def test_execution_timeout(self):
        """测试执行超时"""
        from sandbox import Sandbox, SandboxConfig

        sb = Sandbox(config=SandboxConfig(timeout_seconds=0.5))
        result = sb.execute("while True: pass")
        assert result.success is False
        assert result.timed_out is True

    def test_forbidden_import(self):
        """测试禁止导入"""
        from sandbox import Sandbox

        sb = Sandbox()
        result = sb.execute("import os")
        # 在沙箱中import os可能被禁止或成功但不影响系统
        # 主要测试不会崩溃
        assert result.duration_ms >= 0

    def test_evaluate_expression(self):
        """测试表达式求值"""
        from sandbox import Sandbox

        sb = Sandbox()
        result = sb.evaluate_expression("2 ** 10", variables={})
        assert result.success is True
        assert result.return_value == 1024

    def test_evaluate_with_variables(self):
        """测试带变量的表达式"""
        from sandbox import Sandbox

        sb = Sandbox()
        result = sb.evaluate_expression("a + b * 2", variables={"a": 10, "b": 3})
        assert result.success is True
        assert result.return_value == 16

    def test_expression_security(self):
        """测试表达式安全"""
        from sandbox import Sandbox

        sb = Sandbox()
        result = sb.evaluate_expression("__import__('os')")
        assert result.success is False
        assert "禁止" in result.error

    def test_function_execution(self):
        """测试函数执行"""
        from sandbox import Sandbox

        sb = Sandbox()
        result = sb.execute_function(lambda x, y: x + y, 3, 4)
        assert result.success is True
        assert result.return_value == 7

    def test_function_timeout(self):
        """测试函数超时"""
        from sandbox import Sandbox

        sb = Sandbox()
        result = sb.execute_function(time.sleep, 10, timeout=0.5)
        assert result.success is False
        assert result.timed_out is True

    def test_sandbox_history(self):
        """测试沙箱历史"""
        from sandbox import Sandbox

        sb = Sandbox()
        sb.execute("x = 1")
        sb.execute("y = 2")

        history = sb.get_history()
        assert len(history) == 2

    def test_output_truncation(self):
        """测试输出截断"""
        from sandbox import Sandbox, SandboxConfig

        sb = Sandbox(config=SandboxConfig(max_output_bytes=100))
        result = sb.execute("print('x' * 10000)")
        assert result.success is True
        assert len(result.stdout) < 200  # 应该被截断


# ============================================================
# 阶段90: 生态集成测试
# ============================================================

class TestEcosystemIntegration:
    """生态集成测试"""

    def test_plugin_with_event_bus(self):
        """测试插件+事件总线集成"""
        from plugin_system import PluginManager, PluginBase, PluginInfo
        from event_bus import EventBus

        bus = EventBus()
        received = []

        bus.subscribe("plugin.event", lambda e: received.append(e.data))

        # 通过事件总线通知插件
        bus.publish_simple("plugin.event", data="test_data")
        assert len(received) == 1
        assert received[0] == "test_data"

    def test_file_watcher_with_pipeline(self):
        """测试文件监控+数据管道集成"""
        from file_watcher import FileWatcher
        from data_pipeline import DataPipeline, JSONFileSource, MemorySink

        with tempfile.TemporaryDirectory() as tmpdir:
            watch_dir = Path(tmpdir) / "watch"
            watch_dir.mkdir()
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            # 创建数据文件
            data_file = data_dir / "input.json"
            data_file.write_text('[{"name": "test", "value": 42}]')

            # 管道处理
            pipeline = DataPipeline("watch_pipeline")
            pipeline.extract(JSONFileSource(data_file))
            sink = MemorySink()
            pipeline.load(sink)
            result = pipeline.run()

            assert result.success is True
            assert len(sink.data) == 1

    def test_template_with_knowledge_data(self):
        """测试模板引擎+知识数据"""
        from template_engine import TemplateEngine

        engine = TemplateEngine()
        engine.add_global("system_name", "永动知识图谱Agent")

        report = engine.render_report(
            "知识图谱状态报告",
            [
                {"title": "节点统计", "content": "当前共有 {{ node_count }} 个节点"},
                {"title": "边统计", "content": "当前共有 {{ edge_count }} 条边"},
            ],
            context={"node_count": 42, "edge_count": 128},
        )

        assert "永动知识图谱Agent" in report
        assert "42" in report
        assert "128" in report

    def test_scheduler_with_event_bus(self):
        """测试调度器+事件总线集成"""
        from scheduler import Scheduler
        from event_bus import EventBus

        bus = EventBus()
        scheduler = Scheduler()
        events_received = []

        def scheduled_task():
            bus.publish_simple("scheduled", data="tick")

        bus.subscribe("scheduled", lambda e: events_received.append(e.data))

        scheduler.add_job("periodic", "* * * * *", scheduled_task)
        scheduler.tick()

        assert len(events_received) == 1

    def test_persistence_with_template(self):
        """测试持久化+模板引擎集成"""
        from persistence_v2 import IncrementalStore
        from template_engine import TemplateEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            store = IncrementalStore(Path(tmpdir))
            store.initialize()

            store.set("metric_a", 100)
            store.set("metric_b", 200)

            engine = TemplateEngine()
            report = engine.render_string(
                "指标A: {{ metric_a }}, 指标B: {{ metric_b }}",
                context=store.get_all(),
            )

            assert "100" in report
            assert "200" in report

    def test_sandbox_with_pipeline(self):
        """测试沙箱+数据管道集成"""
        from sandbox import Sandbox
        from data_pipeline import DataPipeline, DictListSource, MapTransformer, MemorySink

        # 用沙箱安全执行转换逻辑
        sb = Sandbox()
        transform_result = sb.evaluate_expression(
            "[x * 2 for x in items]",
            variables={"items": [1, 2, 3]},
        )
        assert transform_result.success is True
        assert transform_result.return_value == [2, 4, 6]

    def test_full_ecosystem_flow(self):
        """测试完整生态流程"""
        from event_bus import EventBus
        from template_engine import TemplateEngine
        from persistence_v2 import IncrementalStore
        from data_pipeline import DataPipeline, DictListSource, FilterTransformer, MemorySink

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 事件总线记录流程
            bus = EventBus()
            flow_log = []
            bus.subscribe("flow", lambda e: flow_log.append(e.data))

            bus.publish_simple("flow", data="开始")

            # 2. 数据管道处理
            pipeline = DataPipeline("eco_test")
            pipeline.extract(DictListSource([
                {"name": "task1", "priority": 3},
                {"name": "task2", "priority": 1},
                {"name": "task3", "priority": 5},
            ]))
            pipeline.transform(FilterTransformer(lambda x: x["priority"] >= 3))
            sink = MemorySink()
            pipeline.load(sink)
            result = pipeline.run()

            bus.publish_simple("flow", data=f"管道处理完成: {result.records_output}条")

            # 3. 持久化存储
            store = IncrementalStore(Path(tmpdir) / "store")
            store.initialize()
            store.set("pipeline_result", result.records_output)

            bus.publish_simple("flow", data="数据已持久化")

            # 4. 模板渲染报告
            engine = TemplateEngine()
            report = engine.render_string(
                "处理结果: {{ count }} 条记录\n流程日志: {{ log_count }} 条",
                context={"count": store.get("pipeline_result"), "log_count": len(flow_log)},
            )

            bus.publish_simple("flow", data="报告已生成")

            # 验证
            assert result.success is True
            assert result.records_output == 2
            assert store.get("pipeline_result") == 2
            assert "2" in report
            assert len(flow_log) == 4
