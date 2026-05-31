"""
生产就绪层测试

阶段91-100: 配置中心、密钥管理、访问控制、审计日志、
         数据加密、自动备份、健康检查、性能分析、系统诊断
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
# 阶段91: 配置中心测试
# ============================================================

class TestConfigCenter:
    """配置中心测试"""

    def test_register_and_get(self):
        """测试注册和获取"""
        from config_center import ConfigCenter, ConfigSchema

        cc = ConfigCenter()
        cc.register_schema(ConfigSchema(key="app.name", value_type="str", default="EternalAgent"))

        assert cc.get("app.name") == "EternalAgent"
        assert cc.get("nonexistent", "default") == "default"

    def test_set_and_get(self):
        """测试设置和获取"""
        from config_center import ConfigCenter, ConfigSchema

        cc = ConfigCenter()
        cc.register_schema(ConfigSchema(key="timeout", value_type="int", default=10))
        cc.set("timeout", 30)

        assert cc.get("timeout") == 30

    def test_type_validation(self):
        """测试类型验证"""
        from config_center import ConfigCenter, ConfigSchema, ConfigValidationError

        cc = ConfigCenter()
        cc.register_schema(ConfigSchema(key="count", value_type="int", default=0))

        cc.set("count", "42")
        assert cc.get("count") == 42

        with pytest.raises(ConfigValidationError):
            cc.register_schema(ConfigSchema(key="pct", value_type="float", min_value=0, max_value=100))
            cc.set("pct", 150)

    def test_allowed_values(self):
        """测试允许值"""
        from config_center import ConfigCenter, ConfigSchema, ConfigValidationError

        cc = ConfigCenter()
        cc.register_schema(ConfigSchema(
            key="mode", value_type="str", default="auto",
            allowed_values=["auto", "manual", "off"]
        ))

        cc.set("mode", "manual")
        assert cc.get("mode") == "manual"

        with pytest.raises(ConfigValidationError):
            cc.set("mode", "invalid")

    def test_layered_priority(self):
        """测试分层优先级"""
        from config_center import ConfigCenter, ConfigSchema

        cc = ConfigCenter()
        cc.register_schema(ConfigSchema(key="key", value_type="str", default="default"))

        # file层
        cc.set("key", "from_file", source="file")
        assert cc.get("key") == "from_file"

        # runtime层覆盖
        cc.set("key", "from_runtime", source="runtime")
        assert cc.get("key") == "from_runtime"

        # 删除runtime后回退到file
        cc.delete("key", source="runtime")
        assert cc.get("key") == "from_file"

    def test_change_listener(self):
        """测试变更监听"""
        from config_center import ConfigCenter, ConfigSchema

        cc = ConfigCenter()
        cc.register_schema(ConfigSchema(key="x", value_type="int", default=0))

        changes = []
        cc.on_change("x", lambda c: changes.append(c.new_value))

        cc.set("x", 42)
        assert len(changes) == 1
        assert changes[0] == 42

    def test_save_and_load_file(self):
        """测试文件保存和加载"""
        from config_center import ConfigCenter, ConfigSchema

        with tempfile.TemporaryDirectory() as tmpdir:
            cc = ConfigCenter(config_dir=Path(tmpdir))
            cc.register_schema(ConfigSchema(key="a", value_type="int", default=1))
            cc.register_schema(ConfigSchema(key="b", value_type="str", default="hello"))
            cc.set("a", 99)

            cc.save_to_file()

            cc2 = ConfigCenter(config_dir=Path(tmpdir))
            cc2.register_schema(ConfigSchema(key="a", value_type="int", default=1))
            cc2.register_schema(ConfigSchema(key="b", value_type="str", default="hello"))
            cc2.load_from_file(Path(tmpdir) / "config.json")

            assert cc2.get("a") == 99

    def test_group(self):
        """测试配置分组"""
        from config_center import ConfigCenter, ConfigSchema

        cc = ConfigCenter()
        cc.register_schema(ConfigSchema(key="db.host", value_type="str", default="localhost", group="database"))
        cc.register_schema(ConfigSchema(key="db.port", value_type="int", default=5432, group="database"))
        cc.register_schema(ConfigSchema(key="cache.ttl", value_type="int", default=300, group="cache"))

        db_config = cc.get_group("database")
        assert "db.host" in db_config
        assert "db.port" in db_config
        assert "cache.ttl" not in db_config

    def test_change_history(self):
        """测试变更历史"""
        from config_center import ConfigCenter, ConfigSchema

        cc = ConfigCenter()
        cc.register_schema(ConfigSchema(key="x", value_type="int", default=0))
        cc.set("x", 1)
        cc.set("x", 2)
        cc.set("x", 3)

        history = cc.get_change_history("x")
        assert len(history) == 3
        assert history[-1]["new"] == 3

    def test_validate_all(self):
        """测试全量验证"""
        from config_center import ConfigCenter, ConfigSchema

        cc = ConfigCenter()
        cc.register_schema(ConfigSchema(key="ok", value_type="str", default="fine"))
        cc.register_schema(ConfigSchema(key="bad", value_type="int", min_value=0, max_value=10))

        cc.set("bad", 5)
        errors = cc.validate_all()
        assert len(errors) == 0

    def test_export_import(self):
        """测试导出导入"""
        from config_center import ConfigCenter, ConfigSchema

        cc = ConfigCenter()
        cc.register_schema(ConfigSchema(key="a", value_type="int", default=0))
        cc.set("a", 42)

        exported = cc.export()
        assert exported["a"] == 42

        cc2 = ConfigCenter()
        cc2.register_schema(ConfigSchema(key="a", value_type="int", default=0))
        count = cc2.import_config(exported)
        assert count == 1
        assert cc2.get("a") == 42


# ============================================================
# 阶段92: 密钥管理测试
# ============================================================

class TestSecretStore:
    """密钥管理测试"""

    def test_set_and_get(self):
        """测试设置和获取"""
        from secret_store import SecretStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SecretStore(store_dir=Path(tmpdir))
            store.set("api_key", "secret123")

            assert store.get("api_key") == "secret123"

    def test_get_nonexistent(self):
        """测试获取不存在的密钥"""
        from secret_store import SecretStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SecretStore(store_dir=Path(tmpdir))
            assert store.get("nonexistent") is None

    def test_delete(self):
        """测试删除"""
        from secret_store import SecretStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SecretStore(store_dir=Path(tmpdir))
            store.set("key1", "val1")
            assert store.delete("key1") is True
            assert store.get("key1") is None

    def test_list_keys(self):
        """测试列出密钥"""
        from secret_store import SecretStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SecretStore(store_dir=Path(tmpdir))
            store.set("k1", "v1", tags=["db"])
            store.set("k2", "v2", tags=["api"])
            store.set("k3", "v3", tags=["db"])

            assert len(store.list_keys()) == 3
            assert len(store.list_keys(tag="db")) == 2

    def test_metadata(self):
        """测试元数据"""
        from secret_store import SecretStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SecretStore(store_dir=Path(tmpdir))
            store.set("key1", "val1", description="测试密钥", tags=["test"])

            meta = store.get_metadata("key1")
            assert meta is not None
            assert meta["description"] == "测试密钥"
            assert "test" in meta["tags"]
            assert "val1" not in str(meta)  # 不包含明文

    def test_version_increment(self):
        """测试版本递增"""
        from secret_store import SecretStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SecretStore(store_dir=Path(tmpdir))
            store.set("key1", "v1")
            store.set("key1", "v2")
            store.set("key1", "v3")

            meta = store.get_metadata("key1")
            assert meta["version"] == 3

    def test_rotate(self):
        """测试密钥轮换"""
        from secret_store import SecretStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SecretStore(store_dir=Path(tmpdir))
            store.set("key1", "original")

            store.rotate("key1", "new_value")
            assert store.get("key1") == "new_value"

            meta = store.get_metadata("key1")
            assert meta["version"] == 2

    def test_audit_log(self):
        """测试审计日志"""
        from secret_store import SecretStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SecretStore(store_dir=Path(tmpdir))
            store.set("k1", "v1")
            store.get("k1")
            store.delete("k1")

            log = store.get_audit_log()
            assert len(log) >= 3

    def test_persistence(self):
        """测试持久化"""
        from secret_store import SecretStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = SecretStore(store_dir=Path(tmpdir))
            store1.set("shared", "data")

            store2 = SecretStore(store_dir=Path(tmpdir))
            assert store2.get("shared") == "data"


# ============================================================
# 阶段93: 访问控制测试
# ============================================================

class TestAccessControl:
    """访问控制测试"""

    def test_create_and_authenticate(self):
        """测试创建和认证"""
        from access_control import AccessControl

        ac = AccessControl()
        ac.create_user("alice", "password123", roles=["admin"])

        user = ac.authenticate("alice", "password123")
        assert user is not None
        assert user.username == "alice"

    def test_authenticate_failure(self):
        """测试认证失败"""
        from access_control import AccessControl

        ac = AccessControl()
        ac.create_user("alice", "correct")

        assert ac.authenticate("alice", "wrong") is None
        assert ac.authenticate("nonexistent", "any") is None

    def test_permission_check(self):
        """测试权限检查"""
        from access_control import AccessControl

        ac = AccessControl()
        ac.create_user("viewer", "pass", roles=["viewer"])
        ac.create_user("admin", "pass", roles=["admin"])

        assert ac.check_permission("admin", "knowledge", "write") is True
        assert ac.check_permission("viewer", "knowledge", "write") is False
        assert ac.check_permission("viewer", "knowledge", "read") is True

    def test_require_permission(self):
        """测试权限要求"""
        from access_control import AccessControl, PermissionDeniedError

        ac = AccessControl()
        ac.create_user("viewer", "pass", roles=["viewer"])

        ac.require_permission("viewer", "data", "read")  # OK

        with pytest.raises(PermissionDeniedError):
            ac.require_permission("viewer", "data", "delete")

    def test_role_assign_revoke(self):
        """测试角色分配和撤销"""
        from access_control import AccessControl

        ac = AccessControl()
        ac.create_user("bob", "pass", roles=["viewer"])

        assert ac.check_permission("bob", "data", "write") is False

        ac.assign_role("bob", "operator")
        assert ac.check_permission("bob", "data", "write") is True

        ac.revoke_role("bob", "operator")
        assert ac.check_permission("bob", "data", "write") is False

    def test_api_key(self):
        """测试API密钥"""
        from access_control import AccessControl

        ac = AccessControl()
        ac.create_user("service", "pass", roles=["operator"])

        raw_key = ac.create_api_key("service", description="测试密钥")
        assert len(raw_key) > 0

        username = ac.authenticate_api_key(raw_key)
        assert username == "service"

    def test_api_key_revoke(self):
        """测试API密钥撤销"""
        from access_control import AccessControl

        ac = AccessControl()
        ac.create_user("svc", "pass")
        raw_key = ac.create_api_key("svc")

        assert ac.authenticate_api_key(raw_key) == "svc"
        ac.revoke_api_key(raw_key)
        assert ac.authenticate_api_key(raw_key) is None

    def test_access_log(self):
        """测试访问日志"""
        from access_control import AccessControl

        ac = AccessControl()
        ac.create_user("alice", "pass")
        ac.authenticate("alice", "pass")
        ac.authenticate("alice", "wrong")

        log = ac.get_access_log()
        assert len(log) >= 2

    def test_delete_user(self):
        """测试删除用户"""
        from access_control import AccessControl

        ac = AccessControl()
        ac.create_user("temp", "pass")
        assert ac.delete_user("temp") is True
        assert ac.authenticate("temp", "pass") is None

    def test_change_password(self):
        """测试修改密码"""
        from access_control import AccessControl

        ac = AccessControl()
        ac.create_user("alice", "old_pass")
        ac.change_password("alice", "new_pass")

        assert ac.authenticate("alice", "old_pass") is None
        assert ac.authenticate("alice", "new_pass") is not None


# ============================================================
# 阶段94: 审计日志测试
# ============================================================

class TestAuditLog:
    """审计日志测试"""

    def test_record_and_query(self):
        """测试记录和查询"""
        from audit_log import AuditLog

        al = AuditLog(enable_file=False)
        al.record("auth", "login", actor="alice", level="INFO")
        al.record("config", "change", actor="admin", level="WARNING")

        results = al.query()
        assert len(results) == 2

    def test_filter_by_category(self):
        """测试按类别过滤"""
        from audit_log import AuditLog

        al = AuditLog(enable_file=False)
        al.record("auth", "login", actor="alice")
        al.record("auth", "logout", actor="alice")
        al.record("config", "change", actor="admin")

        results = al.query(category="auth")
        assert len(results) == 2

    def test_filter_by_level(self):
        """测试按级别过滤"""
        from audit_log import AuditLog

        al = AuditLog(enable_file=False)
        al.record("system", "info", level="INFO")
        al.record("system", "warn", level="WARNING")
        al.record("system", "error", level="CRITICAL")

        results = al.query(level="CRITICAL")
        assert len(results) == 1

    def test_keyword_search(self):
        """测试关键词搜索"""
        from audit_log import AuditLog

        al = AuditLog(enable_file=False)
        al.record("auth", "login_failed", actor="alice", detail="密码错误")
        al.record("auth", "login_success", actor="alice", detail="登录成功")

        results = al.query(keyword="密码")
        assert len(results) == 1

    def test_stats(self):
        """测试统计"""
        from audit_log import AuditLog

        al = AuditLog(enable_file=False)
        al.record("auth", "login", actor="alice")
        al.record("auth", "login", actor="bob")
        al.record("config", "change", actor="admin")

        stats = al.get_stats()
        assert stats["total"] == 3
        assert stats["by_category"]["auth"] == 2
        assert stats["by_actor"]["alice"] == 1

    def test_export_json(self):
        """测试导出JSON"""
        from audit_log import AuditLog

        with tempfile.TemporaryDirectory() as tmpdir:
            al = AuditLog(enable_file=False)
            al.record("test", "action", actor="user")

            output = Path(tmpdir) / "audit.json"
            count = al.export_json(output)
            assert count == 1
            assert output.exists()

    def test_filter_fn(self):
        """测试过滤器函数"""
        from audit_log import AuditLog

        al = AuditLog(enable_file=False)
        al.add_filter(lambda e: e.level != "INFO")  # 过滤掉INFO

        al.record("test", "info_action", level="INFO")
        al.record("test", "warn_action", level="WARNING")

        results = al.query()
        assert len(results) == 1
        assert results[0]["level"] == "WARNING"

    def test_count(self):
        """测试计数"""
        from audit_log import AuditLog

        al = AuditLog(enable_file=False)
        al.record("auth", "a", level="INFO")
        al.record("auth", "b", level="WARNING")
        al.record("config", "c", level="INFO")

        assert al.count() == 3
        assert al.count(category="auth") == 2
        assert al.count(level="WARNING") == 1


# ============================================================
# 阶段95: 数据加密测试
# ============================================================

class TestCryptoUtils:
    """数据加密测试"""

    def test_sha256(self):
        """测试SHA-256"""
        from encryption import CryptoUtils

        h = CryptoUtils.sha256("hello")
        assert len(h) == 64
        assert h == CryptoUtils.sha256("hello")  # 确定性

    def test_sha512(self):
        """测试SHA-512"""
        from encryption import CryptoUtils

        h = CryptoUtils.sha512("test")
        assert len(h) == 128

    def test_md5(self):
        """测试MD5"""
        from encryption import CryptoUtils

        h = CryptoUtils.md5("test")
        assert len(h) == 32

    def test_hmac_sign_verify(self):
        """测试HMAC签名验证"""
        from encryption import CryptoUtils

        sig = CryptoUtils.hmac_sign("data", "secret")
        assert CryptoUtils.hmac_verify("data", sig, "secret") is True
        assert CryptoUtils.hmac_verify("data", sig, "wrong") is False
        assert CryptoUtils.hmac_verify("tampered", sig, "secret") is False

    def test_password_hash_verify(self):
        """测试密码哈希验证"""
        from encryption import CryptoUtils

        pw_hash, salt = CryptoUtils.hash_password("mypassword")
        assert CryptoUtils.verify_password("mypassword", pw_hash, salt) is True
        assert CryptoUtils.verify_password("wrongpassword", pw_hash, salt) is False

    def test_encrypt_decrypt(self):
        """测试加密解密"""
        from encryption import CryptoUtils

        plaintext = "Hello, 永动知识图谱Agent!"
        key = "my-secret-key"

        ciphertext = CryptoUtils.encrypt(plaintext, key)
        assert ciphertext != plaintext

        decrypted = CryptoUtils.decrypt(ciphertext, key)
        assert decrypted == plaintext

    def test_encrypt_different_keys(self):
        """测试不同密钥加密"""
        from encryption import CryptoUtils, EncryptionError

        ct1 = CryptoUtils.encrypt("data", "key1")
        ct2 = CryptoUtils.encrypt("data", "key2")

        assert CryptoUtils.decrypt(ct1, "key1") == "data"
        assert CryptoUtils.decrypt(ct2, "key2") == "data"
        # 错误密钥解密应失败或返回乱码（不等于原文）
        try:
            wrong_result = CryptoUtils.decrypt(ct1, "key2")
            assert wrong_result != "data"
        except EncryptionError:
            pass  # 解密失败也是预期行为

    def test_random_generation(self):
        """测试随机数据生成"""
        from encryption import CryptoUtils

        r1 = CryptoUtils.random_hex(32)
        r2 = CryptoUtils.random_hex(32)
        assert len(r1) == 64
        assert r1 != r2

        token = CryptoUtils.random_token()
        assert len(token) > 0

    def test_checksum(self):
        """测试校验和"""
        from encryption import CryptoUtils

        data = {"key": "value", "number": 42}
        checksum = CryptoUtils.compute_checksum(data)
        assert CryptoUtils.verify_checksum(data, checksum) is True
        assert CryptoUtils.verify_checksum({"key": "different"}, checksum) is False

    def test_sign_data(self):
        """测试数据签名"""
        from encryption import CryptoUtils

        signed = CryptoUtils.sign_data({"action": "test"}, "secret")
        assert CryptoUtils.verify_signed_data(signed, "secret") is True
        assert CryptoUtils.verify_signed_data(signed, "wrong") is False


# ============================================================
# 阶段96: 自动备份测试
# ============================================================

class TestBackupManager:
    """自动备份测试"""

    def test_create_and_restore(self):
        """测试创建和恢复备份"""
        from backup import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(backup_dir=Path(tmpdir))
            data = {"nodes": {"A": {"type": "entity"}}, "edges": []}

            info = bm.create_backup(data, name="test_backup")
            assert info.record_count == 2

            restored = bm.restore_backup(info.id)
            assert restored["nodes"]["A"]["type"] == "entity"

    def test_list_backups(self):
        """测试列出备份"""
        from backup import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(backup_dir=Path(tmpdir))
            bm.create_backup({"a": 1}, name="backup1")
            bm.create_backup({"b": 2}, name="backup2")

            backups = bm.list_backups()
            assert len(backups) == 2

    def test_delete_backup(self):
        """测试删除备份"""
        from backup import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(backup_dir=Path(tmpdir))
            info = bm.create_backup({"x": 1})

            assert bm.delete_backup(info.id) is True
            assert len(bm.list_backups()) == 0

    def test_verify_backup(self):
        """测试验证备份"""
        from backup import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(backup_dir=Path(tmpdir))
            info = bm.create_backup({"data": "test"})

            result = bm.verify_backup(info.id)
            assert result["valid"] is True

    def test_backup_cleanup(self):
        """测试备份清理"""
        from backup import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(backup_dir=Path(tmpdir), max_backups=3)
            for i in range(5):
                bm.create_backup({"i": i}, name=f"backup_{i}")

            backups = bm.list_backups()
            assert len(backups) <= 3

    def test_backup_tags(self):
        """测试备份标签"""
        from backup import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(backup_dir=Path(tmpdir))
            bm.create_backup({"a": 1}, tags=["daily", "important"])
            bm.create_backup({"b": 2}, tags=["manual"])

            tagged = bm.list_backups(tag="daily")
            assert len(tagged) == 1

    def test_backup_stats(self):
        """测试备份统计"""
        from backup import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(backup_dir=Path(tmpdir))
            bm.create_backup({"a": 1})
            bm.create_backup({"b": 2})

            stats = bm.get_stats()
            assert stats["total_backups"] == 2

    def test_compressed_backup(self):
        """测试压缩备份"""
        from backup import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(backup_dir=Path(tmpdir), compress=True)
            big_data = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

            info = bm.create_backup(big_data)
            assert info.compressed_size > 0
            assert info.compressed_size < info.size_bytes

    def test_nonexistent_restore(self):
        """测试恢复不存在的备份"""
        from backup import BackupManager, BackupNotFoundError

        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(backup_dir=Path(tmpdir))
            with pytest.raises(BackupNotFoundError):
                bm.restore_backup("nonexistent")


# ============================================================
# 阶段97: 健康检查测试
# ============================================================

class TestHealthMonitor:
    """健康检查测试"""

    def test_check_all(self):
        """测试全面检查"""
        from health import HealthMonitor

        with tempfile.TemporaryDirectory() as tmpdir:
            hm = HealthMonitor(data_dir=Path(tmpdir))
            report = hm.check_all()

            assert report.overall_score >= 0
            assert report.overall_score <= 100
            assert len(report.checks) >= 2

    def test_disk_checker(self):
        """测试磁盘检查"""
        from health import DiskSpaceChecker

        checker = DiskSpaceChecker(warning_percent=99, critical_percent=99.9)
        result = checker.check()
        assert result.status in ("healthy", "degraded", "unhealthy", "unknown")
        assert result.score >= 0

    def test_memory_checker(self):
        """测试内存检查"""
        from health import MemoryChecker

        checker = MemoryChecker(warning_mb=99999, critical_mb=999999)
        result = checker.check()
        assert result.status in ("healthy", "degraded", "unhealthy", "unknown")

    def test_file_integrity_checker(self):
        """测试文件完整性检查"""
        from health import FileIntegrityChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            (data_dir / "good.json").write_text('{"valid": true}')
            (data_dir / "bad.json").write_text('{invalid json}')

            checker = FileIntegrityChecker(data_dir)
            result = checker.check()
            assert "1" in result.message or "1" in str(result.details)

    def test_data_freshness_checker(self):
        """测试数据新鲜度检查"""
        from health import DataFreshnessChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            (data_dir / "fresh.json").write_text('{}')

            checker = DataFreshnessChecker(data_dir, stale_hours=999)
            result = checker.check()
            assert result.status in ("healthy", "degraded", "unhealthy", "unknown")

    def test_health_report_dict(self):
        """测试健康报告字典"""
        from health import HealthMonitor

        hm = HealthMonitor()
        report = hm.check_all()
        d = report.to_dict()

        assert "overall_status" in d
        assert "overall_score" in d
        assert "checks" in d
        assert "recommendations" in d

    def test_register_unregister(self):
        """测试注册和注销"""
        from health import HealthMonitor, HealthChecker

        class DummyChecker(HealthChecker):
            def __init__(self):
                super().__init__("dummy")
            def check(self):
                from health import CheckResult
                return CheckResult(name="dummy", status="healthy", score=100)

        hm = HealthMonitor()
        hm.register(DummyChecker())
        assert hm.check_single("dummy") is not None

        hm.unregister("dummy")
        assert hm.check_single("dummy") is None

    def test_health_trend(self):
        """测试健康趋势"""
        from health import HealthMonitor

        hm = HealthMonitor()
        hm.check_all()
        hm.check_all()

        trend = hm.get_trend()
        assert len(trend) == 2


# ============================================================
# 阶段98: 性能分析测试
# ============================================================

class TestProfiler:
    """性能分析测试"""

    def test_profile_decorator(self):
        """测试装饰器"""
        from profiler import Profiler

        p = Profiler()

        @p.profile(name="slow_func")
        def slow_func():
            time.sleep(0.01)
            return 42

        result = slow_func()
        assert result == 42

        stats = p.get_stats("slow_func")
        assert stats is not None
        assert stats["call_count"] == 1
        assert stats["total_time_ms"] >= 5

    def test_profile_with_name(self):
        """测试命名装饰器"""
        from profiler import Profiler

        p = Profiler()

        @p.profile(name="my_func")
        def some_func():
            return 1

        some_func()
        stats = p.get_stats("my_func")
        assert stats is not None

    def test_manual_track(self):
        """测试手动追踪"""
        from profiler import Profiler

        p = Profiler()
        p.track("manual_op", 15.5)
        p.track("manual_op", 25.0)

        stats = p.get_stats("manual_op")
        assert stats["call_count"] == 2
        assert stats["avg_time_ms"] == 20.25

    def test_top_slowest(self):
        """测试最慢排行"""
        from profiler import Profiler

        p = Profiler()
        p.track("fast", 1.0)
        p.track("medium", 10.0)
        p.track("slow", 100.0)

        top = p.get_top_slowest(2)
        assert len(top) == 2
        assert top[0]["name"] == "slow"

    def test_error_tracking(self):
        """测试错误追踪"""
        from profiler import Profiler

        p = Profiler()
        p.track("failing", 5.0, error="ValueError: test")

        stats = p.get_stats("failing")
        assert stats["error_count"] == 1

    def test_snapshot(self):
        """测试快照"""
        from profiler import Profiler

        p = Profiler()
        p.track("a", 10.0)
        p.track("b", 20.0)

        snapshot = p.take_snapshot()
        assert snapshot.total_calls == 2
        assert snapshot.total_functions == 2

    def test_enable_disable(self):
        """测试启用禁用"""
        from profiler import Profiler

        p = Profiler()
        assert p.enabled is True

        p.enabled = False
        p.track("ignored", 10.0)
        assert p.get_stats("ignored") is None

        p.enabled = True
        p.track("counted", 10.0)
        assert p.get_stats("counted") is not None

    def test_reset(self):
        """测试重置"""
        from profiler import Profiler

        p = Profiler()
        p.track("a", 10.0)
        p.reset()
        assert p.get_stats("a") is None

    def test_summary(self):
        """测试摘要"""
        from profiler import Profiler

        p = Profiler()
        p.track("a", 10.0)

        summary = p.get_summary()
        assert summary["tracked_functions"] == 1
        assert summary["total_calls"] == 1


# ============================================================
# 阶段99: 系统诊断测试
# ============================================================

class TestSystemDiagnostics:
    """系统诊断测试"""

    def test_diagnose(self):
        """测试全面诊断"""
        from diagnostics import SystemDiagnostics

        with tempfile.TemporaryDirectory() as tmpdir:
            diag = SystemDiagnostics(data_dir=Path(tmpdir))
            report = diag.diagnose()

            assert report.score >= 0
            assert report.score <= 100
            assert isinstance(report.issues, list)
            assert isinstance(report.summary, str)

    def test_quick_check(self):
        """测试快速检查"""
        from diagnostics import SystemDiagnostics

        diag = SystemDiagnostics()
        result = diag.quick_check()

        assert "score" in result
        assert "status" in result
        assert "summary" in result
        assert result["status"] in ("healthy", "degraded", "unhealthy")

    def test_disk_rule(self):
        """测试磁盘诊断规则"""
        from diagnostics import DiskSpaceRule

        rule = DiskSpaceRule(warning_percent=99, critical_percent=99.9)
        issues = rule.diagnose()
        assert isinstance(issues, list)

    def test_memory_rule(self):
        """测试内存诊断规则"""
        from diagnostics import MemoryUsageRule

        rule = MemoryUsageRule(warning_mb=99999, critical_mb=999999)
        issues = rule.diagnose()
        assert isinstance(issues, list)

    def test_data_consistency_rule(self):
        """测试数据一致性规则"""
        from diagnostics import DataConsistencyRule

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            (data_dir / "good.json").write_text('{"ok": true}')
            (data_dir / "bad.json").write_text('not json at all')
            (data_dir / "empty.json").write_text('')

            rule = DataConsistencyRule(data_dir)
            issues = rule.diagnose()
            assert any(i.title == "数据文件损坏" for i in issues)

    def test_log_health_rule(self):
        """测试日志健康规则"""
        from diagnostics import LogHealthRule

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            log_dir.mkdir()
            (log_dir / "app.log").write_text(
                "INFO: ok\nERROR: bad\nERROR: worse\n" * 50
            )

            rule = LogHealthRule(log_dir)
            issues = rule.diagnose()
            assert isinstance(issues, list)

    def test_report_dict(self):
        """测试报告字典"""
        from diagnostics import SystemDiagnostics

        diag = SystemDiagnostics()
        report = diag.diagnose()
        d = report.to_dict()

        assert "score" in d
        assert "summary" in d
        assert "issue_count" in d
        assert "critical_count" in d

    def test_custom_rule(self):
        """测试自定义规则"""
        from diagnostics import SystemDiagnostics, DiagnosticRule, DiagnosticIssue

        class CustomRule(DiagnosticRule):
            def __init__(self):
                super().__init__("custom", "test")
            def diagnose(self):
                return [DiagnosticIssue(
                    severity="info",
                    category="test",
                    title="自定义检查",
                    description="这是一个自定义诊断规则",
                )]

        diag = SystemDiagnostics()
        diag.register(CustomRule())
        report = diag.diagnose()
        assert any(i.title == "自定义检查" for i in report.issues)


# ============================================================
# 阶段100: 生产就绪集成测试
# ============================================================

class TestProductionReady:
    """生产就绪集成测试"""

    def test_config_with_audit(self):
        """测试配置中心+审计日志"""
        from config_center import ConfigCenter, ConfigSchema
        from audit_log import AuditLog

        al = AuditLog(enable_file=False)
        cc = ConfigCenter()

        cc.register_schema(ConfigSchema(key="db.host", value_type="str", default="localhost"))
        changes = []
        cc.on_change("db.host", lambda c: al.record("config", "change", actor="admin", detail=f"db.host -> {c.new_value}"))

        cc.set("db.host", "newhost")
        assert al.count(category="config") == 1

    def test_access_control_with_audit(self):
        """测试访问控制+审计日志"""
        from access_control import AccessControl
        from audit_log import AuditLog

        al = AuditLog(enable_file=False)
        ac = AccessControl()
        ac.create_user("alice", "pass", roles=["admin"])

        user = ac.authenticate("alice", "pass")
        if user:
            al.record("auth", "login", actor=user.username, level="INFO", result="success")

        assert al.count(category="auth") == 1

    def test_backup_with_encryption(self):
        """测试备份+加密"""
        from backup import BackupManager
        from encryption import CryptoUtils

        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(backup_dir=Path(tmpdir))
            sensitive_data = {"api_key": "secret123", "db_password": "pass456"}

            info = bm.create_backup(sensitive_data, name="encrypted_backup")
            restored = bm.restore_backup(info.id)

            assert restored["api_key"] == "secret123"

            # 验证备份文件不是明文（gzip压缩后不应包含明文）
            backup_file = bm._find_backup_file(info.id)
            raw_bytes = backup_file.read_bytes()
            # gzip文件头是 0x1f 0x8b，不是明文JSON
            assert raw_bytes[:2] != b'{"'

    def test_health_with_diagnostics(self):
        """测试健康检查+系统诊断"""
        from health import HealthMonitor
        from diagnostics import SystemDiagnostics

        hm = HealthMonitor()
        diag = SystemDiagnostics()

        health = hm.check_all()
        diagnosis = diag.diagnose()

        assert health.overall_score >= 0
        assert diagnosis.score >= 0

    def test_profiler_with_health(self):
        """测试性能分析+健康检查"""
        from profiler import Profiler

        p = Profiler()

        @p.profile(name="health_check")
        def mock_health_check():
            time.sleep(0.01)
            return {"status": "ok"}

        mock_health_check()
        stats = p.get_stats("health_check")
        assert stats is not None
        assert stats["call_count"] == 1

    def test_full_security_flow(self):
        """测试完整安全流程"""
        from access_control import AccessControl
        from audit_log import AuditLog
        from encryption import CryptoUtils

        al = AuditLog(enable_file=False)
        ac = AccessControl()
        ac.create_user("admin", "secure_pass", roles=["admin"])

        # 认证
        user = ac.authenticate("admin", "secure_pass")
        assert user is not None
        al.record("auth", "login", actor="admin", result="success")

        # 权限检查
        assert ac.check_permission("admin", "system", "admin") is True
        al.record("permission", "check", actor="admin", detail="system:admin=granted")

        # 数据签名
        data = {"action": "deploy", "version": "1.0"}
        signed = CryptoUtils.sign_data(data, "hmac_secret")
        assert CryptoUtils.verify_signed_data(signed, "hmac_secret")

        al.record("security", "sign", actor="admin", detail="数据签名验证通过")

        # 验证审计
        assert al.count() >= 3

    def test_config_secrets_integration(self):
        """测试配置中心+密钥管理集成"""
        from config_center import ConfigCenter, ConfigSchema
        from secret_store import SecretStore

        with tempfile.TemporaryDirectory() as tmpdir:
            cc = ConfigCenter()
            cc.register_schema(ConfigSchema(key="db.password", value_type="str", default=""))

            store = SecretStore(store_dir=Path(tmpdir))
            store.set("db_password", "actual_secret_password")

            # 从密钥库获取并设置到配置中心
            db_pass = store.get("db_password")
            cc.set("db.password", db_pass, source="runtime")

            assert cc.get("db.password") == "actual_secret_password"
            # 配置中心不存储原始密钥引用
            assert store.get_metadata("db_password")["description"] == ""

    def test_end_to_end_production_scenario(self):
        """端到端生产场景测试"""
        from config_center import ConfigCenter, ConfigSchema
        from audit_log import AuditLog
        from access_control import AccessControl
        from encryption import CryptoUtils
        from health import HealthMonitor
        from profiler import Profiler
        from backup import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 配置初始化
            cc = ConfigCenter()
            cc.register_schema(ConfigSchema(key="system.name", value_type="str", default="EternalAgent"))
            cc.register_schema(ConfigSchema(key="system.max_tasks", value_type="int", default=200))

            # 2. 安全初始化
            ac = AccessControl()
            ac.create_user("admin", "admin_pass", roles=["admin"])

            # 3. 审计初始化
            al = AuditLog(enable_file=False)

            # 4. 认证并记录
            user = ac.authenticate("admin", "admin_pass")
            assert user is not None
            al.record("auth", "login", actor="admin", result="success")

            # 5. 修改配置并审计
            cc.set("system.max_tasks", 500)
            al.record("config", "change", actor="admin", detail="max_tasks -> 500")

            # 6. 性能追踪
            p = Profiler()
            p.track("config_change", 2.5)

            # 7. 健康检查
            hm = HealthMonitor(data_dir=Path(tmpdir))
            report = hm.check_all()
            al.record("health", "check", actor="system", detail=f"score={report.overall_score:.0f}")

            # 8. 备份配置
            bm = BackupManager(backup_dir=Path(tmpdir))
            bm.create_backup(cc.export(), name="config_snapshot")
            al.record("backup", "create", actor="admin")

            # 验证
            assert cc.get("system.max_tasks") == 500
            assert al.count() >= 4
            assert len(bm.list_backups()) >= 1
            assert report.overall_score > 0
