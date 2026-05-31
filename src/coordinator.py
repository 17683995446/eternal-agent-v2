"""
多实例协调模块

公理溯源：存续公理 - 多实例可感知彼此，避免冲突

设计意图：
- 实例注册与发现
- 分布式锁（文件锁）
- 实例心跳
- 领导者选举
- 零外部依赖
"""

import fcntl
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from exceptions import EternalAgentError


class CoordinationError(EternalAgentError):
    """协调异常"""
    pass


class LockAcquisitionError(CoordinationError):
    """锁获取异常"""
    pass


@dataclass
class InstanceInfo:
    """实例信息"""
    instance_id: str
    hostname: str = ""
    pid: int = 0
    started_at: str = ""
    last_heartbeat: str = ""
    role: str = "follower"  # leader, follower
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "hostname": self.hostname,
            "pid": self.pid,
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
            "role": self.role,
            "metadata": self.metadata,
        }


class FileLock:
    """文件锁"""

    def __init__(self, lock_path: Path):
        self._lock_path = lock_path
        self._fd = None
        self._locked = False

    @property
    def is_locked(self) -> bool:
        return self._locked

    def acquire(self, timeout: float = 5.0) -> bool:
        """获取锁"""
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        start = time.time()

        while time.time() - start < timeout:
            try:
                self._fd = open(self._lock_path, 'w')
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._fd.write(f"{os.getpid()}\n{datetime.now().isoformat()}\n")
                self._fd.flush()
                self._locked = True
                return True
            except (IOError, OSError):
                if self._fd:
                    try:
                        self._fd.close()
                    except Exception:
                        pass
                    self._fd = None
                time.sleep(0.1)

        return False

    def release(self) -> None:
        """释放锁"""
        if self._fd and self._locked:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                self._fd.close()
            except Exception:
                pass
            self._locked = False
            self._fd = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()


class Coordinator:
    """
    多实例协调器

    职责：
    - 实例注册与发现
    - 分布式文件锁
    - 领导者选举
    - 心跳管理
    - 实例清理
    """

    HEARTBEAT_TIMEOUT = 30.0  # 心跳超时（秒）
    CLEANUP_INTERVAL = 60.0

    def __init__(self, coord_dir: Optional[Path] = None):
        self._coord_dir = coord_dir or Path(__file__).parent.parent / "data" / "coordination"
        self._coord_dir.mkdir(parents=True, exist_ok=True)
        self._registry_file = self._coord_dir / "instances.json"
        self._lock_dir = self._coord_dir / "locks"

        self._instance_id = self._generate_instance_id()
        self._instances: Dict[str, InstanceInfo] = {}
        self._leader_id: Optional[str] = None
        self._lock = threading.RLock()
        self._running = False

        self._register_self()

    @property
    def instance_id(self) -> str:
        return self._instance_id

    @property
    def is_leader(self) -> bool:
        return self._leader_id == self._instance_id

    @property
    def leader_id(self) -> Optional[str]:
        return self._leader_id

    @property
    def active_instances(self) -> List[InstanceInfo]:
        """获取活跃实例列表"""
        self._cleanup_stale()
        return [i for i in self._instances.values() if self._is_alive(i)]

    def acquire_lock(self, resource: str, timeout: float = 5.0) -> Optional[FileLock]:
        """
        获取分布式锁

        Args:
            resource: 资源名称
            timeout: 超时时间

        Returns:
            FileLock 或 None
        """
        lock_path = self._lock_dir / f"{resource}.lock"
        lock = FileLock(lock_path)

        if lock.acquire(timeout=timeout):
            return lock
        return None

    def try_lock(self, resource: str) -> Optional[FileLock]:
        """尝试获取锁（不等待）"""
        return self.acquire_lock(resource, timeout=0.1)

    def elect_leader(self) -> str:
        """执行领导者选举（最早注册的实例成为leader）"""
        with self._lock:
            alive = self.active_instances
            if not alive:
                self._leader_id = self._instance_id
                return self._leader_id

            # 按启动时间排序，最早的成为leader
            alive.sort(key=lambda i: i.started_at)
            self._leader_id = alive[0].instance_id

            # 更新角色
            for inst in self._instances.values():
                inst.role = "leader" if inst.instance_id == self._leader_id else "follower"

            self._save_registry()
            return self._leader_id

    def heartbeat(self) -> None:
        """发送心跳"""
        with self._lock:
            if self._instance_id in self._instances:
                self._instances[self._instance_id].last_heartbeat = datetime.now().isoformat()
                self._save_registry()

    def get_instance(self, instance_id: str) -> Optional[InstanceInfo]:
        """获取实例信息"""
        return self._instances.get(instance_id)

    def get_cluster_info(self) -> Dict[str, Any]:
        """获取集群信息"""
        alive = self.active_instances
        return {
            "instance_id": self._instance_id,
            "role": "leader" if self.is_leader else "follower",
            "leader_id": self._leader_id,
            "active_instances": len(alive),
            "total_registered": len(self._instances),
            "instances": [i.to_dict() for i in alive],
        }

    def unregister(self) -> None:
        """注销实例"""
        with self._lock:
            self._instances.pop(self._instance_id, None)
            self._save_registry()

    def _register_self(self) -> None:
        """注册自身"""
        self._load_registry()

        info = InstanceInfo(
            instance_id=self._instance_id,
            hostname=os.uname().nodename if hasattr(os, 'uname') else "localhost",
            pid=os.getpid(),
            started_at=datetime.now().isoformat(),
            last_heartbeat=datetime.now().isoformat(),
            role="follower",
        )
        self._instances[self._instance_id] = info
        self._save_registry()

    def _load_registry(self) -> None:
        """加载实例注册表"""
        if self._registry_file.exists():
            try:
                data = json.loads(self._registry_file.read_text())
                for inst_data in data.get("instances", []):
                    inst = InstanceInfo(**inst_data)
                    self._instances[inst.instance_id] = inst
            except Exception:
                pass

    def _save_registry(self) -> None:
        """保存实例注册表"""
        data = {
            "instances": [i.to_dict() for i in self._instances.values()],
            "updated_at": datetime.now().isoformat(),
        }
        self._registry_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _cleanup_stale(self) -> None:
        """清理过期实例"""
        stale = []
        for inst in self._instances.values():
            if not self._is_alive(inst) and inst.instance_id != self._instance_id:
                stale.append(inst.instance_id)

        for sid in stale:
            del self._instances[sid]

        if stale:
            self._save_registry()

    def _is_alive(self, instance: InstanceInfo) -> bool:
        """检查实例是否存活"""
        if not instance.last_heartbeat:
            return False
        try:
            last = datetime.fromisoformat(instance.last_heartbeat)
            return (datetime.now() - last).total_seconds() < self.HEARTBEAT_TIMEOUT
        except Exception:
            return False

    @staticmethod
    def _generate_instance_id() -> str:
        """生成实例ID"""
        import hashlib
        raw = f"{os.getpid()}:{time.time()}:{id(object())}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]
