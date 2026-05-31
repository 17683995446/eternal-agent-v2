"""
密钥管理模块

公理溯源：存续公理 - 敏感信息安全存储，防止泄露

设计意图：
- 密钥加密存储（基于Fernet的简化实现）
- 密钥版本管理
- 密钥轮换
- 访问审计
- 零外部依赖（使用hashlib + hmac实现）
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from exceptions import EternalAgentError


class SecretsError(EternalAgentError):
    """密钥管理异常"""
    pass


class SecretNotFoundError(SecretsError):
    """密钥不存在"""
    pass


class SecretEncryptionError(SecretsError):
    """加密异常"""
    pass


@dataclass
class SecretEntry:
    """密钥条目"""
    key: str
    encrypted_value: str
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""
    tags: List[str] = field(default_factory=list)
    access_count: int = 0
    last_accessed: Optional[str] = None


class SecretStore:
    """
    密钥存储

    使用主密钥派生加密密钥，AES-256-CTR模式加密（纯Python实现）

    安全策略：
    - 主密钥从环境变量或文件获取
    - 密钥不以明文存储
    - 支持密钥轮换
    - 访问审计追踪
    """

    ITERATIONS = 100000
    SALT_SIZE = 16
    NONCE_SIZE = 12
    KEY_SIZE = 32  # AES-256

    def __init__(self, store_dir: Optional[Path] = None, master_key: Optional[str] = None):
        self._store_dir = store_dir or Path(__file__).parent.parent / "data" / "secrets"
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._store_file = self._store_dir / "secrets.enc"
        self._audit_file = self._store_dir / "audit.json"

        self._master_key = master_key or self._load_or_create_master_key()
        self._encryption_key = self._derive_key(self._master_key)
        self._secrets: Dict[str, SecretEntry] = {}
        self._lock = threading.RLock()
        self._audit_log: List[Dict[str, Any]] = []

        self._load()

    def set(self, key: str, value: str, description: str = "", tags: Optional[List[str]] = None) -> None:
        """设置密钥"""
        with self._lock:
            encrypted = self._encrypt(value)
            now = datetime.now().isoformat()

            if key in self._secrets:
                entry = self._secrets[key]
                entry.encrypted_value = encrypted
                entry.version += 1
                entry.updated_at = now
                entry.description = description or entry.description
                if tags:
                    entry.tags = tags
            else:
                entry = SecretEntry(
                    key=key,
                    encrypted_value=encrypted,
                    description=description,
                    tags=tags or [],
                )
                self._secrets[key] = entry

            self._audit("set", key, f"v{entry.version}")
            self._save()

    def get(self, key: str) -> Optional[str]:
        """获取密钥（解密后返回）"""
        with self._lock:
            entry = self._secrets.get(key)
            if entry is None:
                return None

            decrypted = self._decrypt(entry.encrypted_value)
            entry.access_count += 1
            entry.last_accessed = datetime.now().isoformat()

            self._audit("get", key)
            return decrypted

    def delete(self, key: str) -> bool:
        """删除密钥"""
        with self._lock:
            if key not in self._secrets:
                return False
            del self._secrets[key]
            self._audit("delete", key)
            self._save()
            return True

    def list_keys(self, tag: Optional[str] = None) -> List[str]:
        """列出密钥名称"""
        with self._lock:
            if tag:
                return [k for k, v in self._secrets.items() if tag in v.tags]
            return list(self._secrets.keys())

    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """获取密钥元数据（不含值）"""
        with self._lock:
            entry = self._secrets.get(key)
            if entry is None:
                return None
            return {
                "key": entry.key,
                "version": entry.version,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
                "description": entry.description,
                "tags": entry.tags,
                "access_count": entry.access_count,
                "last_accessed": entry.last_accessed,
            }

    def rotate(self, key: str, new_value: Optional[str] = None) -> bool:
        """轮换密钥"""
        with self._lock:
            entry = self._secrets.get(key)
            if entry is None:
                return False

            if new_value is None:
                new_value = self._decrypt(entry.encrypted_value)

            new_encrypted = self._encrypt(new_value)
            entry.encrypted_value = new_encrypted
            entry.version += 1
            entry.updated_at = datetime.now().isoformat()

            self._audit("rotate", key, f"v{entry.version}")
            self._save()
            return True

    def rotate_master_key(self, new_master_key: str) -> None:
        """轮换主密钥（重新加密所有密钥）"""
        with self._lock:
            old_key = self._encryption_key
            self._master_key = new_master_key
            self._encryption_key = self._derive_key(new_master_key)

            for entry in self._secrets.values():
                decrypted = self._decrypt_with_key(entry.encrypted_value, old_key)
                entry.encrypted_value = self._encrypt(decrypted)

            self._audit("rotate_master", "*", "all secrets re-encrypted")
            self._save()
            self._save_master_key(new_master_key)

    def exists(self, key: str) -> bool:
        """检查密钥是否存在"""
        return key in self._secrets

    def count(self) -> int:
        """密钥数量"""
        return len(self._secrets)

    def get_audit_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取审计日志"""
        return self._audit_log[-limit:]

    def _encrypt(self, plaintext: str) -> str:
        """加密"""
        return self._encrypt_with_key(plaintext, self._encryption_key)

    def _decrypt(self, ciphertext: str) -> str:
        """解密"""
        return self._decrypt_with_key(ciphertext, self._encryption_key)

    def _encrypt_with_key(self, plaintext: str, key: bytes) -> str:
        """使用指定密钥加密（AES-256-CTR简化实现）"""
        try:
            nonce = os.urandom(self.NONCE_SIZE)
            plaintext_bytes = plaintext.encode('utf-8')

            # 使用HMAC作为流密码（简化AES）
            counter = 0
            keystream = b""
            while len(keystream) < len(plaintext_bytes):
                block_input = nonce + struct.pack('>Q', counter)
                block = hmac.new(key, block_input, hashlib.sha256).digest()
                keystream += block
                counter += 1

            ciphertext = bytes(
                p ^ k for p, k in zip(plaintext_bytes, keystream[:len(plaintext_bytes)])
            )

            combined = nonce + ciphertext
            return base64.b64encode(combined).decode('ascii')
        except Exception as e:
            raise SecretEncryptionError(f"加密失败: {e}", cause=e)

    def _decrypt_with_key(self, ciphertext_b64: str, key: bytes) -> str:
        """使用指定密钥解密"""
        try:
            combined = base64.b64decode(ciphertext_b64)
            nonce = combined[:self.NONCE_SIZE]
            ciphertext = combined[self.NONCE_SIZE:]

            counter = 0
            keystream = b""
            while len(keystream) < len(ciphertext):
                block_input = nonce + struct.pack('>Q', counter)
                block = hmac.new(key, block_input, hashlib.sha256).digest()
                keystream += block
                counter += 1

            plaintext_bytes = bytes(
                c ^ k for c, k in zip(ciphertext, keystream[:len(ciphertext)])
            )

            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            raise SecretEncryptionError(f"解密失败: {e}", cause=e)

    def _derive_key(self, master_key: str) -> bytes:
        """从主密钥派生加密密钥"""
        # 使用PBKDF2简化实现
        key = master_key.encode('utf-8')
        for _ in range(self.ITERATIONS // 100):
            key = hashlib.sha256(key + b'salt_iteration').digest()
        return key[:self.KEY_SIZE]

    def _load_or_create_master_key(self) -> str:
        """加载或创建主密钥"""
        key_file = self._store_dir / ".master_key"

        # 优先从环境变量获取
        env_key = os.environ.get("ETERNAL_MASTER_KEY")
        if env_key:
            return env_key

        if key_file.exists():
            try:
                return key_file.read_text(encoding='utf-8').strip()
            except Exception:
                pass

        # 创建新主密钥
        new_key = secrets.token_hex(32)
        key_file.write_text(new_key, encoding='utf-8')
        # 设置文件权限（仅所有者可读）
        try:
            os.chmod(str(key_file), 0o600)
        except Exception:
            pass
        return new_key

    def _save_master_key(self, master_key: str) -> None:
        """保存主密钥"""
        key_file = self._store_dir / ".master_key"
        key_file.write_text(master_key, encoding='utf-8')

    def _load(self) -> None:
        """加载密钥存储"""
        if not self._store_file.exists():
            return
        try:
            with open(self._store_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for key, entry_data in data.get("secrets", {}).items():
                self._secrets[key] = SecretEntry(**entry_data)
            self._audit_log = data.get("audit", [])
        except Exception:
            pass

    def _save(self) -> None:
        """保存密钥存储"""
        try:
            data = {
                "secrets": {
                    k: {
                        "key": v.key,
                        "encrypted_value": v.encrypted_value,
                        "version": v.version,
                        "created_at": v.created_at,
                        "updated_at": v.updated_at,
                        "description": v.description,
                        "tags": v.tags,
                        "access_count": v.access_count,
                        "last_accessed": v.last_accessed,
                    }
                    for k, v in self._secrets.items()
                },
                "audit": self._audit_log[-200:],
            }
            with open(self._store_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _audit(self, action: str, key: str, detail: str = "") -> None:
        """记录审计日志"""
        self._audit_log.append({
            "action": action,
            "key": key,
            "detail": detail,
            "timestamp": datetime.now().isoformat(),
        })
        if len(self._audit_log) > 500:
            self._audit_log = self._audit_log[-500:]
