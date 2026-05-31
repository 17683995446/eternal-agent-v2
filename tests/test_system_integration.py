"""
系统集成与演示层测试

阶段101-110: 启动入口、可视化、查询语言、基准测试、升级器、协调器
"""

import json
import os
import sys
import tempfile
import time
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ============================================================
# 阶段101: 统一启动入口测试
# ============================================================

class TestBootstrapper:
    """启动入口测试"""

    def test_boot_success(self):
        """测试成功启动"""
        from boot import Bootstrapper

        with tempfile.TemporaryDirectory() as tmpdir:
            bs = Bootstrapper(data_dir=Path(tmpdir))
            result = bs.boot()

            assert result.success is True
            assert len(result.phases) >= 5
            assert result.total_duration_ms > 0

    def test_boot_phases(self):
        """测试启动阶段"""
        from boot import Bootstrapper

        with tempfile.TemporaryDirectory() as tmpdir:
            bs = Bootstrapper(data_dir=Path(tmpdir))
            result = bs.boot()

            phase_names = [p.name for p in result.phases]
            assert "基础层初始化" in phase_names
            assert "记忆层初始化" in phase_names
            assert "自驱层初始化" in phase_names

    def test_boot_components(self):
        """测试组件初始化"""
        from boot import Bootstrapper

        with tempfile.TemporaryDirectory() as tmpdir:
            bs = Bootstrapper(data_dir=Path(tmpdir))
            bs.boot()

            assert bs.get_component("config_center") is not None
            assert bs.get_component("knowledge_graph") is not None
            assert bs.get_component("task_queue") is not None
            assert bs.get_component("agent") is not None
            assert bs.get_component("event_bus") is not None
            assert bs.get_component("profiler") is not None

    def test_boot_result_dict(self):
        """测试启动结果字典"""
        from boot import Bootstrapper

        with tempfile.TemporaryDirectory() as tmpdir:
            bs = Bootstrapper(data_dir=Path(tmpdir))
            result = bs.boot()
            d = result.to_dict()

            assert "success" in d
            assert "phases" in d
            assert "total_duration_ms" in d

    def test_shutdown(self):
        """测试优雅停机"""
        from boot import Bootstrapper

        with tempfile.TemporaryDirectory() as tmpdir:
            bs = Bootstrapper(data_dir=Path(tmpdir))
            bs.boot()
            results = bs.shutdown()

            assert "knowledge_graph" in results

    def test_get_status(self):
        """测试获取状态"""
        from boot import Bootstrapper

        with tempfile.TemporaryDirectory() as tmpdir:
            bs = Bootstrapper(data_dir=Path(tmpdir))
            bs.boot()
            status = bs.get_status()

            assert "components" in status
            assert "knowledge_graph" in status["components"]


# ============================================================
# 阶段102: 知识图谱可视化测试
# ============================================================

class TestKnowledgeVisualizer:
    """可视化测试"""

    def _make_kg(self):
        """创建测试用知识图谱"""
        from knowledge_graph import KnowledgeGraph
        from constants import NodeType, RelationType

        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_node("A", node_type=NodeType.ENTITY)
            kg.add_node("B", node_type=NodeType.TASK)
            kg.add_node("C", node_type=NodeType.ENTITY)
            kg.add_edge("A", "B", relation=RelationType.RELATED, weight=0.8)
            kg.add_edge("B", "C", relation=RelationType.DERIVED, weight=0.5)
            kg.add_edge("A", "C", relation=RelationType.RELATED, weight=0.3)
            return kg

    def test_render_mermaid(self):
        """测试Mermaid渲染"""
        from visualization import KnowledgeVisualizer

        kg = self._make_kg()
        viz = KnowledgeVisualizer(kg)
        result = viz.render_mermaid()

        assert "graph LR" in result
        assert "A" in result
        assert "B" in result

    def test_render_ascii(self):
        """测试ASCII渲染"""
        from visualization import KnowledgeVisualizer

        kg = self._make_kg()
        viz = KnowledgeVisualizer(kg)
        result = viz.render_ascii()

        assert "知识图谱" in result
        assert "A" in result

    def test_render_json(self):
        """测试JSON渲染"""
        from visualization import KnowledgeVisualizer

        kg = self._make_kg()
        viz = KnowledgeVisualizer(kg)
        result = viz.render_json()

        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 3
        assert len(result["edges"]) == 3

    def test_render_stats(self):
        """测试统计渲染"""
        from visualization import KnowledgeVisualizer

        kg = self._make_kg()
        viz = KnowledgeVisualizer(kg)
        result = viz.render_stats()

        assert "节点数" in result
        assert "边数" in result

    def test_render_html(self):
        """测试HTML渲染"""
        from visualization import KnowledgeVisualizer

        kg = self._make_kg()
        viz = KnowledgeVisualizer(kg)
        result = viz.render_html()

        assert "<html" in result
        assert "知识图谱" in result

    def test_empty_graph(self):
        """测试空图谱"""
        from visualization import KnowledgeVisualizer

        viz = KnowledgeVisualizer(None)
        assert "空" in viz.render_mermaid()
        assert "空" in viz.render_ascii()

    def test_find_paths(self):
        """测试路径查找"""
        from visualization import KnowledgeVisualizer

        kg = self._make_kg()
        viz = KnowledgeVisualizer(kg)
        paths = viz.find_paths("A", "C")

        assert len(paths) >= 1
        assert paths[0][0] == "A"
        assert paths[0][-1] == "C"

    def test_subgraph(self):
        """测试子图提取"""
        from visualization import KnowledgeVisualizer

        kg = self._make_kg()
        viz = KnowledgeVisualizer(kg)
        sub = viz.extract_subgraph("A", depth=1)

        result = sub.render_json()
        assert "A" in [n["name"] for n in result["nodes"]]


# ============================================================
# 阶段103: 查询语言测试
# ============================================================

class TestQueryEngine:
    """查询语言测试"""

    def _make_kg(self):
        from knowledge_graph import KnowledgeGraph
        from constants import NodeType, RelationType

        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_node("Python", node_type=NodeType.ENTITY, attributes={"category": "language"})
            kg.add_node("Java", node_type=NodeType.ENTITY, attributes={"category": "language"})
            kg.add_node("学习Python", node_type=NodeType.TASK)
            kg.add_node("学习Java", node_type=NodeType.TASK)
            kg.add_edge("Python", "学习Python", relation=RelationType.RELATED, weight=0.9)
            kg.add_edge("Java", "学习Java", relation=RelationType.RELATED, weight=0.7)
            return kg

    def test_find_nodes(self):
        """测试FIND nodes"""
        from query_language import QueryEngine

        kg = self._make_kg()
        qe = QueryEngine(kg)
        result = qe.execute("FIND nodes")

        assert result.success is True
        assert result.result_type == "nodes"
        assert result.count == 4

    def test_find_nodes_where(self):
        """测试FIND nodes WHERE"""
        from query_language import QueryEngine

        kg = self._make_kg()
        qe = QueryEngine(kg)
        result = qe.execute('FIND nodes WHERE type=TASK')

        assert result.success is True
        assert result.count == 2

    def test_find_node(self):
        """测试FIND node"""
        from query_language import QueryEngine

        kg = self._make_kg()
        qe = QueryEngine(kg)
        result = qe.execute('FIND node "Python"')

        assert result.success is True
        assert result.count == 1
        assert result.data[0]["name"] == "Python"

    def test_find_edges(self):
        """测试FIND edges"""
        from query_language import QueryEngine

        kg = self._make_kg()
        qe = QueryEngine(kg)
        result = qe.execute("FIND edges")

        assert result.success is True
        assert result.count == 2

    def test_find_path(self):
        """测试FIND path"""
        from query_language import QueryEngine

        kg = self._make_kg()
        qe = QueryEngine(kg)
        result = qe.execute('FIND path FROM "Python" TO "学习Python"')

        assert result.success is True
        assert result.result_type == "paths"
        assert result.count >= 1

    def test_count_nodes(self):
        """测试COUNT nodes"""
        from query_language import QueryEngine

        kg = self._make_kg()
        qe = QueryEngine(kg)
        result = qe.execute("COUNT nodes")

        assert result.success is True
        assert result.data == 4

    def test_count_edges(self):
        """测试COUNT edges"""
        from query_language import QueryEngine

        kg = self._make_kg()
        qe = QueryEngine(kg)
        result = qe.execute("COUNT edges")

        assert result.success is True
        assert result.data == 2

    def test_stats(self):
        """测试STATS"""
        from query_language import QueryEngine

        kg = self._make_kg()
        qe = QueryEngine(kg)
        result = qe.execute("STATS")

        assert result.success is True
        assert result.result_type == "stats"
        assert "node_count" in result.data

    def test_search(self):
        """测试SEARCH"""
        from query_language import QueryEngine

        kg = self._make_kg()
        qe = QueryEngine(kg)
        result = qe.execute('SEARCH "Python"')

        assert result.success is True
        assert result.count >= 2  # Python节点 + 学习Python节点

    def test_empty_query(self):
        """测试空查询"""
        from query_language import QueryEngine

        qe = QueryEngine()
        result = qe.execute("")
        assert result.success is False

    def test_invalid_query(self):
        """测试无效查询"""
        from query_language import QueryEngine

        qe = QueryEngine()
        result = qe.execute("INVALID COMMAND")
        assert result.success is False


# ============================================================
# 阶段106: 性能基准测试
# ============================================================

class TestBenchmark:
    """性能基准测试"""

    def test_basic_benchmark(self):
        """测试基本基准"""
        from benchmark import Benchmark

        bm = Benchmark()
        result = bm.run("test_add", lambda: 1 + 1, iterations=100)

        assert result.name == "test_add"
        assert result.iterations == 100
        assert result.avg_ms >= 0
        assert result.ops_per_sec > 0

    def test_benchmark_result_dict(self):
        """测试结果字典"""
        from benchmark import Benchmark

        bm = Benchmark()
        bm.run("test", lambda: None, iterations=10)
        results = bm.get_results()

        assert len(results) == 1
        assert results[0]["name"] == "test"

    def test_benchmark_report(self):
        """测试报告生成"""
        from benchmark import Benchmark

        bm = Benchmark()
        bm.run("fast_op", lambda: sum(range(100)), iterations=50)
        report = bm.generate_report()

        assert "性能基准测试" in report
        assert "fast_op" in report

    def test_benchmark_with_kg(self):
        """测试知识图谱基准"""
        from benchmark import Benchmark
        from knowledge_graph import KnowledgeGraph

        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(save_path=Path(tmpdir) / "kg.json")
            kg.add_node("A")
            kg.add_node("B")

            bm = Benchmark()
            results = bm.run_suite(kg)

            assert "add_node" in results
            assert "stats" in results


# ============================================================
# 阶段107: 系统升级器测试
# ============================================================

class TestUpgrader:
    """升级器测试"""

    def test_version_parse(self):
        """测试版本解析"""
        from upgrader import VersionInfo

        v = VersionInfo.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_version_parse_with_label(self):
        """测试带标签的版本"""
        from upgrader import VersionInfo

        v = VersionInfo.parse("2.0.0-beta")
        assert v.major == 2
        assert v.label == "beta"

    def test_version_compare(self):
        """测试版本比较"""
        from upgrader import VersionInfo

        v1 = VersionInfo.parse("1.0.0")
        v2 = VersionInfo.parse("2.0.0")
        assert v2 > v1

    def test_version_str(self):
        """测试版本字符串"""
        from upgrader import VersionInfo

        v = VersionInfo(major=1, minor=2, patch=3, label="rc")
        assert "1.2.3-rc" == str(v)

    def test_current_version(self):
        """测试当前版本"""
        from upgrader import Upgrader

        with tempfile.TemporaryDirectory() as tmpdir:
            u = Upgrader(data_dir=Path(tmpdir))
            assert u.current_version.major >= 1

    def test_register_migration(self):
        """测试注册迁移"""
        from upgrader import Upgrader, MigrationStep

        with tempfile.TemporaryDirectory() as tmpdir:
            u = Upgrader(data_dir=Path(tmpdir))
            step = MigrationStep(
                from_version="1.0.0",
                to_version="2.0.0",
                description="测试迁移",
                migrate_fn=lambda: None,
            )
            u.register_migration(step)

            check = u.check_upgrade_available("2.0.0")
            assert check["available"] is True

    def test_upgrade(self):
        """测试升级"""
        from upgrader import Upgrader, MigrationStep

        with tempfile.TemporaryDirectory() as tmpdir:
            u = Upgrader(data_dir=Path(tmpdir))

            migrated = [False]
            def do_migrate():
                migrated[0] = True

            u.register_migration(MigrationStep(
                from_version="1.0.0",
                to_version="2.0.0",
                description="测试",
                migrate_fn=do_migrate,
            ))

            result = u.upgrade("2.0.0")
            assert result["success"] is True
            assert migrated[0] is True
            assert u.current_version.major == 2

    def test_upgrade_history(self):
        """测试升级历史"""
        from upgrader import Upgrader, MigrationStep

        with tempfile.TemporaryDirectory() as tmpdir:
            u = Upgrader(data_dir=Path(tmpdir))
            u.register_migration(MigrationStep(
                from_version="1.0.0", to_version="2.0.0",
                description="升级", migrate_fn=lambda: None,
            ))
            u.upgrade("2.0.0")

            history = u.history
            assert len(history) >= 1
            assert history[0]["from"] == "1.0.0"
            assert history[0]["to"] == "2.0.0"

    def test_downgrade_not_allowed(self):
        """测试不允许降级"""
        from upgrader import Upgrader

        with tempfile.TemporaryDirectory() as tmpdir:
            u = Upgrader(data_dir=Path(tmpdir))
            result = u.upgrade("0.9.0")
            assert result["success"] is False


# ============================================================
# 阶段108: 多实例协调测试
# ============================================================

class TestCoordinator:
    """多实例协调测试"""

    def test_register_and_discover(self):
        """测试注册和发现"""
        from coordinator import Coordinator

        with tempfile.TemporaryDirectory() as tmpdir:
            coord = Coordinator(coord_dir=Path(tmpdir))
            info = coord.get_cluster_info()

            assert info["instance_id"] == coord.instance_id
            assert info["active_instances"] >= 1

    def test_file_lock(self):
        """测试文件锁"""
        from coordinator import FileLock

        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            lock = FileLock(lock_path)
            assert lock.acquire(timeout=1.0) is True
            assert lock.is_locked is True

            lock.release()
            assert lock.is_locked is False

    def test_context_manager_lock(self):
        """测试上下文管理器锁"""
        from coordinator import FileLock

        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "ctx.lock"
            with FileLock(lock_path) as lock:
                assert lock.is_locked
            assert lock.is_locked is False

    def test_leader_election(self):
        """测试领导者选举"""
        from coordinator import Coordinator

        with tempfile.TemporaryDirectory() as tmpdir:
            coord = Coordinator(coord_dir=Path(tmpdir))
            leader = coord.elect_leader()

            assert leader == coord.instance_id
            assert coord.is_leader is True

    def test_heartbeat(self):
        """测试心跳"""
        from coordinator import Coordinator

        with tempfile.TemporaryDirectory() as tmpdir:
            coord = Coordinator(coord_dir=Path(tmpdir))
            coord.heartbeat()

            inst = coord.get_instance(coord.instance_id)
            assert inst is not None
            assert inst.last_heartbeat != ""

    def test_acquire_resource_lock(self):
        """测试资源锁"""
        from coordinator import Coordinator

        with tempfile.TemporaryDirectory() as tmpdir:
            coord = Coordinator(coord_dir=Path(tmpdir))
            lock = coord.acquire_lock("test_resource", timeout=1.0)

            assert lock is not None
            assert lock.is_locked is True

            lock.release()

    def test_unregister(self):
        """测试注销"""
        from coordinator import Coordinator

        with tempfile.TemporaryDirectory() as tmpdir:
            coord = Coordinator(coord_dir=Path(tmpdir))
            coord.unregister()

            info = coord.get_cluster_info()
            # 注销后自己不在活跃列表中
            assert info["active_instances"] == 0


# ============================================================
# 阶段110: 系统集成与演示集成测试
# ============================================================

class TestSystemIntegration:
    """系统集成测试"""

    def test_boot_with_visualization(self):
        """测试启动+可视化"""
        from boot import Bootstrapper
        from visualization import KnowledgeVisualizer

        with tempfile.TemporaryDirectory() as tmpdir:
            bs = Bootstrapper(data_dir=Path(tmpdir))
            bs.boot()

            kg = bs.get_component("knowledge_graph")
            viz = KnowledgeVisualizer(kg)

            mermaid = viz.render_mermaid()
            assert "graph" in mermaid

    def test_boot_with_query(self):
        """测试启动+查询"""
        from boot import Bootstrapper
        from query_language import QueryEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            bs = Bootstrapper(data_dir=Path(tmpdir))
            bs.boot()

            kg = bs.get_component("knowledge_graph")
            qe = QueryEngine(kg)

            result = qe.execute("STATS")
            assert result.success is True

    def test_boot_with_benchmark(self):
        """测试启动+基准测试"""
        from boot import Bootstrapper
        from benchmark import Benchmark

        with tempfile.TemporaryDirectory() as tmpdir:
            bs = Bootstrapper(data_dir=Path(tmpdir))
            bs.boot()

            kg = bs.get_component("knowledge_graph")
            bm = Benchmark()
            results = bm.run_suite(kg)

            assert "add_node" in results
            assert results["add_node"].ops_per_sec > 0

    def test_coordinator_with_event_bus(self):
        """测试协调器+事件总线"""
        from coordinator import Coordinator
        from event_bus import EventBus

        with tempfile.TemporaryDirectory() as tmpdir:
            coord = Coordinator(coord_dir=Path(tmpdir))
            bus = EventBus()

            events = []
            bus.subscribe("coordination", lambda e: events.append(e.data))

            bus.publish_simple("coordination", data=f"instance_{coord.instance_id}")
            assert len(events) == 1

    def test_full_lifecycle(self):
        """测试完整生命周期"""
        from boot import Bootstrapper
        from visualization import KnowledgeVisualizer
        from query_language import QueryEngine
        from benchmark import Benchmark

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 启动
            bs = Bootstrapper(data_dir=Path(tmpdir))
            boot_result = bs.boot()
            assert boot_result.success is True

            # 2. 添加知识
            kg = bs.get_component("knowledge_graph")
            kg.add_node("测试实体", node_type="entity")
            kg.add_node("测试任务", node_type="task")
            kg.add_edge("测试实体", "测试任务", relation="related", weight=0.8)

            # 3. 查询
            qe = QueryEngine(kg)
            stats = qe.execute("STATS")
            assert stats.data["node_count"] >= 2

            # 4. 可视化
            viz = KnowledgeVisualizer(kg)
            ascii_view = viz.render_ascii()
            assert "测试实体" in ascii_view

            # 5. 基准测试
            bm = Benchmark()
            bench = bm.run("add_node_bench", lambda: kg.add_node("bench"), iterations=50)
            assert bench.avg_ms >= 0

            # 6. 停机
            shutdown = bs.shutdown()
            assert "knowledge_graph" in shutdown
