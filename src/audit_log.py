"""
审计日志模块

公理溯源：存续公理 - 全操作可追溯，满足安全合规要求

设计意图：
- 结构化审计日志
- 日志分级（INFO/WARNING/CRITICAL）
- 日志搜索与过滤
- 日志导出
- 日志轮转
- 零外部依赖
"""

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from exceptions import EternalAgentError


class AuditError(EternalAgentError):
    """审计异常"""
    pass


@dataclass
class AuditEntry:
    """审计日志条目"""
    timestamp: str
    level: str          # INFO, WARNING, CRITICAL
    category: str       # auth, config, knowledge, task, system, api
    action: str         # 具体操作
    actor: str          # 操作者
    resource: str = ""  # 操作资源
    detail: str = ""    # 详细信息
    result: str = ""    # success/failure
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            from utils import generate_short_id
            self.id = generate_short_id()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "level": self.level,
            "category": self.category,
            "action": self.action,
            "actor": self.actor,
            "resource": self.resource,
            "detail": self.detail,
            "result": self.result,
            "metadata": self.metadata,
        }


class AuditLog:
    """
    审计日志

    职责：
    - 记录所有关键操作
    - 支持多后端（内存、文件）
    - 日志搜索与过滤
    - 日志统计
    - 日志轮转
    """

    MAX_MEMORY_ENTRIES = 10000
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_BACKUP_FILES = 5

    def __init__(self, log_dir: Optional[Path] = None, enable_file: bool = True):
        self._log_dir = log_dir or Path(__file__).parent.parent / "data" / "audit"
        self._enable_file = enable_file
        self._entries: List[AuditEntry] = []
        self._lock = threading.RLock()
        self._stats = {
            "total": 0,
            "by_level": {},
            "by_category": {},
            "by_actor": {},
        }
        self._filters: List[Callable[[AuditEntry], bool]] = []

        if self._enable_file:
            self._log_dir.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        category: str,
        action: str,
        actor: str = "system",
        level: str = "INFO",
        resource: str = "",
        detail: str = "",
        result: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """记录审计日志"""
        # 检查过滤器
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            level=level.upper(),
            category=category,
            action=action,
            actor=actor,
            resource=resource,
            detail=detail,
            result=result,
            metadata=metadata or {},
        )

        if self._filters:
            if not all(f(entry) for f in self._filters):
                return entry

        with self._lock:
            self._entries.append(entry)
            self._stats["total"] += 1
            self._stats["by_level"][level.upper()] = self._stats["by_level"].get(level.upper(), 0) + 1
            self._stats["by_category"][category] = self._stats["by_category"].get(category, 0) + 1
            self._stats["by_actor"][actor] = self._stats["by_actor"].get(actor, 0) + 1

            # 内存限制
            if len(self._entries) > self.MAX_MEMORY_ENTRIES:
                self._entries = self._entries[-self.MAX_MEMORY_ENTRIES:]

            # 文件写入
            if self._enable_file:
                self._write_to_file(entry)

        return entry

    def _apply_filters(
        self,
        entries: List[AuditEntry],
        category: Optional[str] = None,
        level: Optional[str] = None,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None,
        keyword: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[AuditEntry]:
        """应用过滤条件（辅助方法）"""
        filtered = entries
        
        # 按条件依次过滤
        if category:
            filtered = [e for e in filtered if e.category == category]
        if level:
            filtered = [e for e in filtered if e.level == level.upper()]
        if actor:
            filtered = [e for e in filtered if e.actor == actor]
        if action:
            filtered = [e for e in filtered if action in e.action]
        if result:
            filtered = [e for e in filtered if e.result == result]
        if keyword:
            kw = keyword.lower()
            def match_keyword(e):
                detail_str = str(e.detail) if not isinstance(e.detail, str) else e.detail
                return (kw in detail_str.lower() or
                        kw in e.action.lower() or
                        kw in e.resource.lower())
            filtered = [e for e in filtered if match_keyword(e)]
        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]
        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]
        
        return filtered

    def query(
        self,
        category: Optional[str] = None,
        level: Optional[str] = None,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None,
        keyword: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """查询审计日志"""
        with self._lock:
            filtered = self._apply_filters(
                self._entries, category, level, actor, 
                action, result, keyword, start_time, end_time
            )
            return [e.to_dict() for e in filtered[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        """获取审计统计"""
        with self._lock:
            return {
                "total": self._stats["total"],
                "by_level": dict(self._stats["by_level"]),
                "by_category": dict(self._stats["by_category"]),
                "by_actor": dict(self._stats["by_actor"]),
                "memory_entries": len(self._entries),
            }

    def add_filter(self, filter_fn: Callable[[AuditEntry], bool]) -> None:
        """添加日志过滤器"""
        self._filters.append(filter_fn)

    def clear_filters(self) -> None:
        """清空过滤器"""
        self._filters.clear()

    def export_json(self, file_path: Path, limit: int = 1000) -> int:
        """导出为JSON"""
        with self._lock:
            entries = [e.to_dict() for e in self._entries[-limit:]]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2, default=str)
        return len(entries)

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近日志"""
        with self._lock:
            return [e.to_dict() for e in self._entries[-limit:]]

    def count(self, category: Optional[str] = None, level: Optional[str] = None) -> int:
        """计数"""
        with self._lock:
            entries = self._entries
            if category:
                entries = [e for e in entries if e.category == category]
            if level:
                entries = [e for e in entries if e.level == level.upper()]
            return len(entries)

    def _write_to_file(self, entry: AuditEntry) -> None:
        """写入文件"""
        try:
            log_file = self._log_dir / "audit.log"
            line = json.dumps(entry.to_dict(), ensure_ascii=False, default=str) + "\n"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(line)

            # 轮转检查
            if log_file.exists() and log_file.stat().st_size > self.MAX_FILE_SIZE:
                self._rotate_log(log_file)
        except Exception:
            pass

    def _rotate_log(self, log_file: Path) -> None:
        """日志轮转"""
        try:
            for i in range(self.MAX_BACKUP_FILES - 1, 0, -1):
                old = log_file.with_suffix(f".log.{i}")
                new = log_file.with_suffix(f".log.{i + 1}")
                if old.exists():
                    if new.exists():
                        new.unlink()
                    old.rename(new)
            log_file.rename(log_file.with_suffix(".log.1"))
        except Exception:
            pass
