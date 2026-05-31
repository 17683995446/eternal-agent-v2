"""
文件监控模块

公理溯源：记忆公理 - 监控外部文件变化，自动将新知识纳入图谱

设计意图：
- 基于轮询的目录变化检测
- 支持文件创建/修改/删除事件
- 支持递归目录监控
- 零外部依赖（不依赖watchdog）
"""

import hashlib
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from exceptions import EternalAgentError


class FileWatcherError(EternalAgentError):
    """文件监控异常"""
    pass


@dataclass
class FileEvent:
    """
    文件变化事件

    Attributes:
        event_type: 事件类型 (created/modified/deleted)
        path: 文件路径
        timestamp: 事件时间戳
        old_hash: 旧文件哈希（仅modified）
        new_hash: 新文件哈希
    """
    event_type: str  # created, modified, deleted
    path: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    old_hash: str = ""
    new_hash: str = ""


class FileWatcher:
    """
    文件监控器

    职责：
    - 监控指定目录的文件变化
    - 通过回调通知变化事件
    - 支持启动/停止/暂停
    - 支持文件模式过滤
    """

    def __init__(
        self,
        watch_dir: Path,
        callback: Optional[Callable[[FileEvent], None]] = None,
        interval: float = 2.0,
        recursive: bool = True,
        patterns: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
    ):
        """
        Args:
            watch_dir: 监控目录
            callback: 变化回调函数
            interval: 轮询间隔（秒）
            recursive: 是否递归监控子目录
            patterns: 文件匹配模式（如 ['*.py', '*.json']）
            ignore_patterns: 忽略模式（如 ['__pycache__', '*.pyc']）
        """
        self._watch_dir = Path(watch_dir)
        self._callback = callback
        self._interval = interval
        self._recursive = recursive
        self._patterns = patterns or []
        self._ignore_patterns = ignore_patterns or ["__pycache__", ".git", "*.pyc"]

        self._file_hashes: Dict[str, str] = {}
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._event_count = 0
        self._last_scan_time: Optional[str] = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def event_count(self) -> int:
        return self._event_count

    @property
    def watched_files(self) -> int:
        return len(self._file_hashes)

    def start(self) -> None:
        """启动文件监控"""
        if self._running:
            return

        if not self._watch_dir.exists():
            self._watch_dir.mkdir(parents=True, exist_ok=True)

        # 初始扫描建立基线
        self._scan()
        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止文件监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def pause(self) -> None:
        """暂停监控"""
        self._paused = True

    def resume(self) -> None:
        """恢复监控"""
        self._paused = False

    def set_callback(self, callback: Callable[[FileEvent], None]) -> None:
        """设置变化回调"""
        self._callback = callback

    def get_snapshot(self) -> Dict[str, str]:
        """获取当前文件快照"""
        with self._lock:
            return dict(self._file_hashes)

    def force_scan(self) -> List[FileEvent]:
        """强制扫描并返回变化事件"""
        return self._scan()

    def _watch_loop(self) -> None:
        """监控循环"""
        while self._running:
            if not self._paused:
                try:
                    self._scan()
                except Exception:
                    pass
            time.sleep(self._interval)

    def _get_all_files(self) -> Any:
        """获取所有文件（辅助方法）"""
        if self._recursive:
            return self._watch_dir.rglob("*")
        return self._watch_dir.iterdir()

    def _check_file_change(self, str_path: str, file_hash: str) -> Optional[FileEvent]:
        """检查文件变化（辅助方法）"""
        with self._lock:
            if str_path not in self._file_hashes:
                return FileEvent(event_type="created", path=str_path, new_hash=file_hash)
            elif self._file_hashes[str_path] != file_hash:
                return FileEvent(
                    event_type="modified",
                    path=str_path,
                    old_hash=self._file_hashes[str_path],
                    new_hash=file_hash,
                )
        return None

    def _detect_deleted(self, current_files: Dict[str, str]) -> List[FileEvent]:
        """检测删除的文件（辅助方法）"""
        events = []
        with self._lock:
            deleted_paths = set(self._file_hashes.keys()) - set(current_files.keys())
            for str_path in deleted_paths:
                events.append(FileEvent(
                    event_type="deleted",
                    path=str_path,
                    old_hash=self._file_hashes[str_path],
                ))
        return events

    def _scan(self) -> List[FileEvent]:
        """扫描目录，检测变化"""
        events = []
        current_files: Dict[str, str] = {}

        all_files = self._get_all_files()

        for file_path in all_files:
            if not file_path.is_file():
                continue

            str_path = str(file_path)

            # 检查忽略模式
            if self._should_ignore(file_path):
                continue

            # 检查文件模式
            if self._patterns and not self._matches_patterns(file_path):
                continue

            # 计算哈希
            file_hash = self._hash_file(file_path)
            current_files[str_path] = file_hash

            # 检查变化
            event = self._check_file_change(str_path, file_hash)
            if event:
                events.append(event)

        # 检测删除的文件
        events.extend(self._detect_deleted(current_files))

        # 更新快照
        with self._lock:
            self._file_hashes = current_files

        self._event_count += len(events)
        self._last_scan_time = datetime.now().isoformat()

        # 回调通知
        if self._callback:
            for event in events:
                try:
                    self._callback(event)
                except Exception:
                    pass

        return events

    def _should_ignore(self, path: Path) -> bool:
        """检查是否应该忽略"""
        for pattern in self._ignore_patterns:
            if pattern.startswith("*"):
                if path.name.endswith(pattern[1:]):
                    return True
            elif pattern in str(path):
                return True
        return False

    def _matches_patterns(self, path: Path) -> bool:
        """检查是否匹配文件模式"""
        if not self._patterns:
            return True
        for pattern in self._patterns:
            if pattern.startswith("*"):
                if path.name.endswith(pattern[1:]):
                    return True
            elif path.name == pattern:
                return True
        return False

    @staticmethod
    def _hash_file(path: Path, block_size: int = 65536) -> str:
        """计算文件MD5哈希"""
        hasher = hashlib.md5()
        try:
            with open(path, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    hasher.update(block)
            return hasher.hexdigest()
        except (IOError, OSError):
            return ""
