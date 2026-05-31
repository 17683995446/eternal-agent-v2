"""
访问控制模块

公理溯源：存续公理 - 最小权限原则保护系统安全

设计意图：
- RBAC（基于角色的访问控制）
- 资源级权限
- 操作级权限
- 权限继承
- 零外部依赖
"""

import hashlib
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from exceptions import EternalAgentError


class AccessControlError(EternalAgentError):
    """访问控制异常"""
    pass


class PermissionDeniedError(AccessControlError):
    """权限拒绝"""
    pass


class AuthenticationError(AccessControlError):
    """认证失败"""
    pass


# ============================================================
# 权限定义
# ============================================================

@dataclass
class Permission:
    """权限"""
    resource: str      # 资源名称
    action: str        # 操作: read, write, delete, execute, admin
    scope: str = "*"   # 范围: * (全部), own (自己的)

    def __hash__(self) -> int:
        return hash((self.resource, self.action, self.scope))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Permission):
            return (self.resource == other.resource and
                    self.action == other.action and
                    self.scope == other.scope)
        return False

    def matches(self, resource: str, action: str, scope: str = "*") -> bool:
        """检查是否匹配请求"""
        if self.resource != "*" and self.resource != resource:
            return False
        if self.action != "*" and self.action != action:
            return False
        if self.scope != "*" and self.scope != scope:
            return False
        return True


# 预定义权限
PERM_READ = Permission(resource="*", action="read")
PERM_WRITE = Permission(resource="*", action="write")
PERM_DELETE = Permission(resource="*", action="delete")
PERM_EXECUTE = Permission(resource="*", action="execute")
PERM_ADMIN = Permission(resource="*", action="admin")


# ============================================================
# 角色
# ============================================================

@dataclass
class Role:
    """角色"""
    name: str
    description: str = ""
    permissions: Set[Permission] = field(default_factory=set)
    parent_roles: Set[str] = field(default_factory=set)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_permission(self, perm: Permission) -> None:
        self.permissions.add(perm)

    def remove_permission(self, perm: Permission) -> None:
        self.permissions.discard(perm)

    def has_permission(self, resource: str, action: str, scope: str = "*") -> bool:
        return any(p.matches(resource, action, scope) for p in self.permissions)


# 预定义角色
ROLE_ADMIN = Role(
    name="admin",
    description="管理员 - 全部权限",
    permissions={
        Permission("*", "*"),
    }
)

ROLE_OPERATOR = Role(
    name="operator",
    description="运维人员 - 读写执行权限",
    permissions={
        Permission("*", "read"),
        Permission("*", "write"),
        Permission("*", "execute"),
    }
)

ROLE_VIEWER = Role(
    name="viewer",
    description="观察者 - 只读权限",
    permissions={
        Permission("*", "read"),
    }
)


# ============================================================
# 用户
# ============================================================

@dataclass
class User:
    """用户"""
    username: str
    password_hash: str = ""
    roles: Set[str] = field(default_factory=set)
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_login: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_role(self, role_name: str) -> None:
        self.roles.add(role_name)

    def remove_role(self, role_name: str) -> None:
        self.roles.discard(role_name)

    def has_role(self, role_name: str) -> bool:
        return role_name in self.roles


@dataclass
class APIKey:
    """API密钥"""
    key_hash: str
    username: str
    description: str = ""
    permissions: Set[Permission] = field(default_factory=set)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None
    last_used: Optional[str] = None
    is_active: bool = True


# ============================================================
# 访问控制管理器
# ============================================================

class AccessControl:
    """
    访问控制管理器

    职责：
    - 用户管理（创建/删除/认证）
    - 角色管理（创建/分配/继承）
    - 权限检查
    - API密钥管理
    - 访问日志
    """

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._roles: Dict[str, Role] = {
            "admin": ROLE_ADMIN,
            "operator": ROLE_OPERATOR,
            "viewer": ROLE_VIEWER,
        }
        self._api_keys: Dict[str, APIKey] = {}
        self._access_log: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    @property
    def user_count(self) -> int:
        return len(self._users)

    @property
    def role_names(self) -> List[str]:
        return list(self._roles.keys())

    # ---- 用户管理 ----

    def create_user(
        self,
        username: str,
        password: str,
        roles: Optional[List[str]] = None,
    ) -> User:
        """创建用户"""
        with self._lock:
            if username in self._users:
                raise AccessControlError(f"用户 '{username}' 已存在")

            password_hash = self._hash_password(password)
            user = User(username=username, password_hash=password_hash)
            for role in (roles or ["viewer"]):
                user.add_role(role)

            self._users[username] = user
            self._log("user.create", username)
            return user

    def delete_user(self, username: str) -> bool:
        """删除用户"""
        with self._lock:
            if username not in self._users:
                return False
            del self._users[username]
            self._log("user.delete", username)
            return True

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """认证用户"""
        with self._lock:
            user = self._users.get(username)
            if user is None or not user.is_active:
                return None

            if self._verify_password(password, user.password_hash):
                user.last_login = datetime.now().isoformat()
                self._log("user.login", username, "success")
                return user

            self._log("user.login", username, "failed")
            return None

    def get_user(self, username: str) -> Optional[User]:
        """获取用户"""
        return self._users.get(username)

    def list_users(self) -> List[str]:
        """列出用户"""
        return list(self._users.keys())

    def change_password(self, username: str, new_password: str) -> bool:
        """修改密码"""
        with self._lock:
            user = self._users.get(username)
            if user is None:
                return False
            user.password_hash = self._hash_password(new_password)
            self._log("user.password_change", username)
            return True

    # ---- 角色管理 ----

    def create_role(self, role: Role) -> None:
        """创建角色"""
        with self._lock:
            self._roles[role.name] = role

    def assign_role(self, username: str, role_name: str) -> bool:
        """分配角色"""
        with self._lock:
            user = self._users.get(username)
            if user is None:
                return False
            if role_name not in self._roles:
                return False
            user.add_role(role_name)
            self._log("role.assign", f"{username}:{role_name}")
            return True

    def revoke_role(self, username: str, role_name: str) -> bool:
        """撤销角色"""
        with self._lock:
            user = self._users.get(username)
            if user is None:
                return False
            user.remove_role(role_name)
            self._log("role.revoke", f"{username}:{role_name}")
            return True

    def get_role(self, role_name: str) -> Optional[Role]:
        """获取角色"""
        return self._roles.get(role_name)

    # ---- 权限检查 ----

    def check_permission(
        self,
        username: str,
        resource: str,
        action: str,
        scope: str = "*",
    ) -> bool:
        """检查用户权限"""
        with self._lock:
            user = self._users.get(username)
            if user is None or not user.is_active:
                return False

            # 收集所有角色权限（含继承）
            all_perms = self._collect_permissions(user.roles)

            result = any(p.matches(resource, action, scope) for p in all_perms)
            self._log("permission.check", username, f"{resource}:{action}={result}")
            return result

    def require_permission(
        self,
        username: str,
        resource: str,
        action: str,
        scope: str = "*",
    ) -> None:
        """要求权限（无权限则抛异常）"""
        if not self.check_permission(username, resource, action, scope):
            raise PermissionDeniedError(
                f"用户 '{username}' 无权对 '{resource}' 执行 '{action}'"
            )

    # ---- API密钥管理 ----

    def create_api_key(
        self,
        username: str,
        description: str = "",
        permissions: Optional[Set[Permission]] = None,
    ) -> str:
        """创建API密钥（返回明文密钥，仅此一次）"""
        with self._lock:
            user = self._users.get(username)
            if user is None:
                raise AccessControlError(f"用户 '{username}' 不存在")

            raw_key = secrets.token_hex(32)
            key_hash = self._hash_password(raw_key)

            api_key = APIKey(
                key_hash=key_hash,
                username=username,
                description=description,
                permissions=permissions or set(),
            )
            self._api_keys[key_hash] = api_key
            self._log("apikey.create", username)
            return raw_key

    def authenticate_api_key(self, raw_key: str) -> Optional[str]:
        """认证API密钥，返回用户名"""
        with self._lock:
            key_hash = self._hash_password(raw_key)
            api_key = self._api_keys.get(key_hash)
            if api_key is None or not api_key.is_active:
                return None

            # 检查过期
            if api_key.expires_at:
                expires = datetime.fromisoformat(api_key.expires_at)
                if datetime.now() > expires:
                    return None

            api_key.last_used = datetime.now().isoformat()
            self._log("apikey.authenticate", api_key.username)
            return api_key.username

    def revoke_api_key(self, raw_key: str) -> bool:
        """撤销API密钥"""
        with self._lock:
            key_hash = self._hash_password(raw_key)
            if key_hash in self._api_keys:
                del self._api_keys[key_hash]
                return True
            return False

    # ---- 审计 ----

    def get_access_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取访问日志"""
        return self._access_log[-limit:]

    def _collect_permissions(self, role_names: Set[str]) -> Set[Permission]:
        """收集角色权限（含继承）"""
        perms: Set[Permission] = set()
        visited: Set[str] = set()

        def _collect(names: Set[str]):
            for name in names:
                if name in visited:
                    continue
                visited.add(name)
                role = self._roles.get(name)
                if role:
                    perms.update(role.permissions)
                    _collect(role.parent_roles)

        _collect(role_names)
        return perms

    def _log(self, action: str, subject: str, detail: str = "") -> None:
        """记录访问日志"""
        self._access_log.append({
            "action": action,
            "subject": subject,
            "detail": detail,
            "timestamp": datetime.now().isoformat(),
        })
        if len(self._access_log) > 1000:
            self._access_log = self._access_log[-1000:]

    @staticmethod
    def _hash_password(password: str) -> str:
        """密码哈希"""
        salt = "eternal_agent_salt_v1"
        return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        """验证密码"""
        return AccessControl._hash_password(password) == password_hash
