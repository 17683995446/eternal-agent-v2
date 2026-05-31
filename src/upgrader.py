"""
系统升级器模块

公理溯源：存续公理 - 系统可平滑升级，数据不丢失

设计意图：
- 版本管理
- 数据迁移
- 升级回滚
- 兼容性检查
- 零外部依赖
"""

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from exceptions import EternalAgentError


class UpgradeError(EternalAgentError):
    """升级异常"""
    pass


class RollbackError(UpgradeError):
    """回滚异常"""
    pass


@dataclass
class VersionInfo:
    """版本信息"""
    major: int = 1
    minor: int = 0
    patch: int = 0
    label: str = ""  # alpha, beta, rc, ""

    def __str__(self) -> str:
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.label:
            s += f"-{self.label}"
        return s

    @classmethod
    def parse(cls, version_str: str) -> 'VersionInfo':
        """解析版本字符串"""
        parts = version_str.split("-")
        nums = parts[0].split(".")
        label = parts[1] if len(parts) > 1 else ""
        return cls(
            major=int(nums[0]) if len(nums) > 0 else 0,
            minor=int(nums[1]) if len(nums) > 1 else 0,
            patch=int(nums[2]) if len(nums) > 2 else 0,
            label=label,
        )

    def __gt__(self, other: 'VersionInfo') -> bool:
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __le__(self, other: 'VersionInfo') -> bool:
        return self == other or self < other

    def __lt__(self, other: 'VersionInfo') -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __ge__(self, other: 'VersionInfo') -> bool:
        return self == other or self > other

    def __eq__(self, other: object) -> bool:
        if isinstance(other, VersionInfo):
            return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
        return False


@dataclass
class MigrationStep:
    """迁移步骤"""
    from_version: str
    to_version: str
    description: str
    migrate_fn: Optional[Callable] = None
    rollback_fn: Optional[Callable] = None


@dataclass
class UpgradeRecord:
    """升级记录"""
    from_version: str
    to_version: str
    timestamp: str
    success: bool
    detail: str = ""


class Upgrader:
    """
    系统升级器

    职责：
    - 管理版本
    - 执行数据迁移
    - 支持回滚
    - 升级历史
    """

    CURRENT_VERSION = "1.0.0"

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or Path(__file__).parent.parent / "data"
        self._version_file = self._data_dir / "version.json"
        self._history_file = self._data_dir / "upgrade_history.json"
        self._backup_dir = self._data_dir / "upgrade_backups"

        self._migrations: Dict[str, MigrationStep] = {}
        self._history: List[UpgradeRecord] = []

        self._load_history()
        self._register_builtin_migrations()

    @property
    def current_version(self) -> VersionInfo:
        """获取当前版本"""
        return self._read_version()

    @property
    def history(self) -> List[Dict[str, Any]]:
        return [
            {"from": r.from_version, "to": r.to_version, "ts": r.timestamp, "success": r.success, "detail": r.detail}
            for r in self._history
        ]

    def register_migration(self, step: MigrationStep) -> None:
        """注册迁移步骤"""
        key = f"{step.from_version}->{step.to_version}"
        self._migrations[key] = step

    def check_upgrade_available(self, target_version: str) -> Dict[str, Any]:
        """检查升级是否可用"""
        current = self._read_version()
        target = VersionInfo.parse(target_version)

        if target <= current:
            return {"available": False, "reason": "目标版本不高于当前版本"}

        # 检查迁移路径
        path = self._find_migration_path(str(current), target_version)
        if not path:
            return {"available": False, "reason": "无可用迁移路径"}

        return {
            "available": True,
            "from": str(current),
            "to": target_version,
            "steps": len(path),
            "path": [f"{s.from_version} → {s.to_version}" for s in path],
        }

    def upgrade(self, target_version: str, data_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        执行升级

        Args:
            target_version: 目标版本
            data_dir: 数据目录（用于备份）
        """
        current = self._read_version()
        target = VersionInfo.parse(target_version)

        if target <= current:
            return {"success": False, "error": "目标版本不高于当前版本"}

        path = self._find_migration_path(str(current), target_version)
        if not path:
            return {"success": False, "error": "无可用迁移路径"}

        # 备份
        backup_path = None
        if data_dir:
            backup_path = self._backup_dir / f"pre_{target_version}"
            try:
                self._backup_dir.mkdir(parents=True, exist_ok=True)
                if data_dir.exists():
                    shutil.copytree(str(data_dir), str(backup_path))
            except Exception as e:
                return {"success": False, "error": f"备份失败: {e}"}

        # 执行迁移
        for step in path:
            try:
                if step.migrate_fn:
                    step.migrate_fn()
                self._record_upgrade(str(current), step.to_version, True, step.description)
            except Exception as e:
                self._record_upgrade(str(current), step.to_version, False, str(e))
                return {
                    "success": False,
                    "error": f"迁移失败: {step.from_version} → {step.to_version}: {e}",
                    "backup_path": str(backup_path) if backup_path else None,
                }

        # 更新版本号
        self._write_version(target_version)

        return {
            "success": True,
            "from": str(current),
            "to": target_version,
            "steps_completed": len(path),
            "backup_path": str(backup_path) if backup_path else None,
        }

    def _clear_data_dir(self) -> None:
        """清空数据目录（辅助方法）"""
        for item in self._data_dir.iterdir():
            if item.name not in ("upgrade_backups",):
                if item.is_dir():
                    shutil.rmtree(str(item))
                else:
                    item.unlink()

    def _restore_from_backup(self, bp: Path) -> None:
        """从备份恢复（辅助方法）"""
        for item in bp.iterdir():
            dest = self._data_dir / item.name
            if item.is_dir():
                shutil.copytree(str(item), str(dest))
            else:
                shutil.copy2(str(item), str(dest))

    def rollback(self, backup_path: Optional[str] = None) -> Dict[str, Any]:
        """回滚到上一版本"""
        if not self._history:
            return {"success": False, "error": "无升级历史"}

        last = self._history[-1]
        if not last.success:
            return {"success": False, "error": "上次升级未成功，无需回滚"}

        # 从备份恢复
        if backup_path:
            bp = Path(backup_path)
            if bp.exists():
                try:
                    self._clear_data_dir()
                    self._restore_from_backup(bp)
                except Exception as e:
                    return {"success": False, "error": f"回滚失败: {e}"}

        # 回退版本号
        self._write_version(last.from_version)
        self._record_upgrade(last.to_version, last.from_version, True, "rollback")

        return {"success": True, "from": last.to_version, "to": last.from_version}

    def _read_version(self) -> VersionInfo:
        """读取当前版本"""
        if self._version_file.exists():
            try:
                data = json.loads(self._version_file.read_text())
                return VersionInfo.parse(data.get("version", self.CURRENT_VERSION))
            except Exception:
                pass
        return VersionInfo.parse(self.CURRENT_VERSION)

    def _write_version(self, version_str: str) -> None:
        """写入版本号"""
        self._version_file.parent.mkdir(parents=True, exist_ok=True)
        self._version_file.write_text(json.dumps({
            "version": version_str,
            "updated_at": datetime.now().isoformat(),
        }, indent=2))

    def _find_migration_path(self, from_ver: str, to_ver: str) -> List[MigrationStep]:
        """查找迁移路径"""
        path = []
        current = from_ver

        while current != to_ver:
            found = False
            for key, step in self._migrations.items():
                if step.from_version == current:
                    path.append(step)
                    current = step.to_version
                    found = True
                    break
            if not found:
                return []

        return path

    def _register_builtin_migrations(self) -> None:
        """注册内置迁移"""
        pass  # 后续版本升级时添加

    def _record_upgrade(self, from_ver: str, to_ver: str, success: bool, detail: str = "") -> None:
        """记录升级"""
        record = UpgradeRecord(
            from_version=from_ver,
            to_version=to_ver,
            timestamp=datetime.now().isoformat(),
            success=success,
            detail=detail,
        )
        self._history.append(record)
        self._save_history()

    def _load_history(self) -> None:
        """加载升级历史"""
        if self._history_file.exists():
            try:
                data = json.loads(self._history_file.read_text())
                self._history = [UpgradeRecord(**r) for r in data]
            except Exception:
                pass

    def _save_history(self) -> None:
        """保存升级历史"""
        self._history_file.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {"from_version": r.from_version, "to_version": r.to_version,
             "timestamp": r.timestamp, "success": r.success, "detail": r.detail}
            for r in self._history
        ]
        self._history_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
