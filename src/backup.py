"""
自动备份模块

公理溯源：记忆公理 - 知识图谱定期备份，防止数据丢失

设计意图：
- 自动定期备份
- 备份版本管理
- 增量备份
- 备份恢复
- 备份清理策略
- 零外部依赖
"""

import gzip
import hashlib
import json
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from exceptions import EternalAgentError


class BackupError(EternalAgentError):
    """备份异常"""
    pass


class BackupNotFoundError(BackupError):
    """备份不存在"""
    pass


class BackupCorruptedError(BackupError):
    """备份损坏"""
    pass


@dataclass
class BackupInfo:
    """备份信息"""
    id: str
    name: str
    backup_type: str  # full, incremental
    created_at: str
    size_bytes: int
    compressed_size: int
    record_count: int
    checksum: str
    source_path: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.backup_type,
            "created_at": self.created_at,
            "size_bytes": self.size_bytes,
            "compressed_size": self.compressed_size,
            "record_count": self.record_count,
            "checksum": self.checksum,
            "description": self.description,
            "tags": self.tags,
        }


class BackupManager:
    """
    备份管理器

    职责：
    - 创建完整/增量备份
    - 备份恢复
    - 备份版本管理
    - 自动清理策略
    - 备份完整性验证
    """

    DEFAULT_MAX_BACKUPS = 10
    DEFAULT_COMPRESS = True

    def __init__(
        self,
        backup_dir: Optional[Path] = None,
        max_backups: int = DEFAULT_MAX_BACKUPS,
        compress: bool = DEFAULT_COMPRESS,
    ):
        self._backup_dir = backup_dir or Path(__file__).parent.parent / "data" / "backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._max_backups = max_backups
        self._compress = compress
        self._lock = threading.RLock()
        self._history: List[Dict[str, Any]] = []

    @property
    def backup_dir(self) -> Path:
        return self._backup_dir

    def create_backup(
        self,
        data: Dict[str, Any],
        name: str = "",
        description: str = "",
        tags: Optional[List[str]] = None,
        backup_type: str = "full",
    ) -> BackupInfo:
        """
        创建备份

        Args:
            data: 要备份的数据
            name: 备份名称
            description: 描述
            tags: 标签
            backup_type: 备份类型 (full/incremental)
        """
        with self._lock:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_id = hashlib.md5(
                f"{timestamp}{json.dumps(data, sort_keys=True, default=str)}".encode()
            ).hexdigest()[:12]

            if not name:
                name = f"backup_{timestamp}"

            suffix = ".json.gz" if self._compress else ".json"
            filename = f"{backup_id}_{name}{suffix}"
            filepath = self._backup_dir / filename

            # 序列化
            content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
            original_size = len(content.encode('utf-8'))
            checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()

            # 写入
            if self._compress:
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    f.write(content)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

            compressed_size = filepath.stat().st_size
            record_count = len(data) if isinstance(data, dict) else 0

            info = BackupInfo(
                id=backup_id,
                name=name,
                backup_type=backup_type,
                created_at=datetime.now().isoformat(),
                size_bytes=original_size,
                compressed_size=compressed_size,
                record_count=record_count,
                checksum=checksum,
                description=description,
                tags=tags or [],
            )

            # 保存元数据
            self._save_metadata(info)

            # 清理旧备份
            self._cleanup()

            self._history.append({
                "action": "create",
                "backup_id": backup_id,
                "timestamp": info.created_at,
            })

            return info

    def restore_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        从备份恢复

        Args:
            backup_id: 备份ID

        Returns:
            备份数据
        """
        with self._lock:
            filepath = self._find_backup_file(backup_id)
            if filepath is None:
                raise BackupNotFoundError(f"备份 '{backup_id}' 不存在")

            try:
                # 先读取原始字节计算校验和
                raw_bytes = filepath.read_bytes()
                if str(filepath).endswith('.gz'):
                    import gzip
                    raw_bytes = gzip.decompress(raw_bytes)
                computed_checksum = hashlib.sha256(raw_bytes).hexdigest()

                meta = self._load_metadata(backup_id)
                if meta and meta.get("checksum"):
                    if computed_checksum != meta["checksum"]:
                        raise BackupCorruptedError(
                            f"备份 '{backup_id}' 校验和不匹配"
                        )

                # 再解析JSON
                data = json.loads(raw_bytes.decode('utf-8'))

                self._history.append({
                    "action": "restore",
                    "backup_id": backup_id,
                    "timestamp": datetime.now().isoformat(),
                })

                return data
            except json.JSONDecodeError as e:
                raise BackupCorruptedError(f"备份 '{backup_id}' 数据损坏: {e}", cause=e)

    def list_backups(self, tag: Optional[str] = None) -> List[BackupInfo]:
        """列出所有备份"""
        metas = self._load_all_metadata()
        if tag:
            metas = [m for m in metas if tag in m.get("tags", [])]
        return [
            BackupInfo(
                id=m["id"],
                name=m["name"],
                backup_type=m.get("type", "full"),
                created_at=m["created_at"],
                size_bytes=m.get("size_bytes", 0),
                compressed_size=m.get("compressed_size", 0),
                record_count=m.get("record_count", 0),
                checksum=m.get("checksum", ""),
                description=m.get("description", ""),
                tags=m.get("tags", []),
            )
            for m in sorted(metas, key=lambda x: x["created_at"], reverse=True)
        ]

    def delete_backup(self, backup_id: str) -> bool:
        """删除备份"""
        with self._lock:
            filepath = self._find_backup_file(backup_id)
            if filepath is None:
                return False

            try:
                filepath.unlink()
                meta_path = self._backup_dir / f"{backup_id}.meta.json"
                if meta_path.exists():
                    meta_path.unlink()
                return True
            except Exception:
                return False

    def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """验证备份完整性"""
        filepath = self._find_backup_file(backup_id)
        if filepath is None:
            return {"valid": False, "error": "备份不存在"}

        if not filepath.exists():
            return {"valid": False, "error": "备份文件丢失"}

        try:
            if str(filepath).endswith('.gz'):
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    json.load(f)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    json.load(f)
            return {"valid": True, "error": None}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """获取备份统计"""
        backups = self.list_backups()
        total_size = sum(b.compressed_size for b in backups)
        return {
            "total_backups": len(backups),
            "total_size_bytes": total_size,
            "full_backups": sum(1 for b in backups if b.backup_type == "full"),
            "incremental_backups": sum(1 for b in backups if b.backup_type == "incremental"),
            "oldest": backups[-1].created_at if backups else None,
            "newest": backups[0].created_at if backups else None,
        }

    def backup_file(self, source_path: Path, name: str = "", description: str = "") -> BackupInfo:
        """备份指定文件"""
        if not source_path.exists():
            raise BackupError(f"源文件不存在: {source_path}")

        with open(source_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {"_raw_content": f.read()}

        return self.create_backup(
            data=data,
            name=name or source_path.stem,
            description=description or f"备份自 {source_path}",
            tags=["file_backup"],
        )

    def _find_backup_file(self, backup_id: str) -> Optional[Path]:
        """查找备份文件"""
        for f in self._backup_dir.iterdir():
            if f.name.startswith(backup_id) and not f.name.endswith('.meta.json') and (f.suffix == '.json' or f.name.endswith('.json.gz')):
                return f
        return None

    def _save_metadata(self, info: BackupInfo) -> None:
        """保存备份元数据"""
        meta_path = self._backup_dir / f"{info.id}.meta.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(info.to_dict(), f, ensure_ascii=False, indent=2)

    def _load_metadata(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """加载备份元数据"""
        meta_path = self._backup_dir / f"{backup_id}.meta.json"
        if not meta_path.exists():
            return None
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def _load_all_metadata(self) -> List[Dict[str, Any]]:
        """加载所有元数据"""
        metas = []
        for f in self._backup_dir.glob("*.meta.json"):
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    metas.append(json.load(fh))
            except Exception:
                pass
        return metas

    def _cleanup(self) -> None:
        """清理旧备份"""
        backups = self.list_backups()
        if len(backups) <= self._max_backups:
            return

        for old in backups[self._max_backups:]:
            try:
                self.delete_backup(old.id)
            except Exception:
                pass
