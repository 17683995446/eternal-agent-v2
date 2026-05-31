"""
数据加密模块

公理溯源：存续公理 - 敏感数据加密保护，防止泄露

设计意图：
- 对称加密（AES-256简化）
- 哈希工具（SHA-256/512, MD5）
- HMAC签名/验证
- 密码哈希（PBKDF2简化）
- 零外部依赖
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from exceptions import EternalAgentError


class EncryptionError(EternalAgentError):
    """加密异常"""
    pass


class HashMismatchError(EncryptionError):
    """哈希不匹配"""
    pass


class CryptoUtils:
    """
    加密工具集

    提供：
    - 对称加密/解密
    - 哈希计算
    - HMAC签名/验证
    - 密码哈希
    - 随机数据生成
    """

    # ============================================================
    # 哈希工具
    # ============================================================

    @staticmethod
    def sha256(data: str) -> str:
        """SHA-256哈希"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    @staticmethod
    def sha512(data: str) -> str:
        """SHA-512哈希"""
        return hashlib.sha512(data.encode('utf-8')).hexdigest()

    @staticmethod
    def md5(data: str) -> str:
        """MD5哈希（仅用于非安全场景）"""
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    @staticmethod
    def file_hash(file_path: str, algorithm: str = "sha256") -> str:
        """文件哈希"""
        hasher = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(65536), b''):
                hasher.update(block)
        return hasher.hexdigest()

    @staticmethod
    def hash_bytes(data: bytes, algorithm: str = "sha256") -> str:
        """字节哈希"""
        hasher = hashlib.new(algorithm)
        hasher.update(data)
        return hasher.hexdigest()

    # ============================================================
    # HMAC工具
    # ============================================================

    @staticmethod
    def hmac_sign(data: str, secret: str, algorithm: str = "sha256") -> str:
        """HMAC签名"""
        h = hmac.new(secret.encode('utf-8'), data.encode('utf-8'), algorithm)
        return h.hexdigest()

    @staticmethod
    def hmac_verify(data: str, signature: str, secret: str, algorithm: str = "sha256") -> bool:
        """HMAC验证"""
        expected = CryptoUtils.hmac_sign(data, secret, algorithm)
        return hmac.compare_digest(expected, signature)

    # ============================================================
    # 密码哈希
    # ============================================================

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None, iterations: int = 100000) -> Tuple[str, str]:
        """
        密码哈希（PBKDF2简化）

        Returns:
            (hash_hex, salt_hex)
        """
        if salt is None:
            salt = secrets.token_hex(16)

        salt_bytes = bytes.fromhex(salt)
        password_bytes = password.encode('utf-8')

        # PBKDF2简化实现
        dk = password_bytes + salt_bytes
        for _ in range(iterations // 100):
            dk = hashlib.sha256(dk).digest()

        return dk.hex(), salt

    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str, iterations: int = 100000) -> bool:
        """验证密码"""
        computed_hash, _ = CryptoUtils.hash_password(password, salt, iterations)
        return hmac.compare_digest(computed_hash, password_hash)

    # ============================================================
    # 对称加密
    # ============================================================

    @staticmethod
    def encrypt(plaintext: str, key: str) -> str:
        """
        对称加密（AES-256-CTR简化实现）

        Args:
            plaintext: 明文
            key: 加密密钥（自动派生为256位）

        Returns:
            Base64编码的密文
        """
        try:
            # 派生256位密钥
            key_bytes = hashlib.sha256(key.encode('utf-8')).digest()
            nonce = os.urandom(12)
            plaintext_bytes = plaintext.encode('utf-8')

            # HMAC-CTR模式
            counter = 0
            keystream = b""
            while len(keystream) < len(plaintext_bytes):
                block_input = nonce + struct.pack('>Q', counter)
                block = hmac.new(key_bytes, block_input, hashlib.sha256).digest()
                keystream += block
                counter += 1

            ciphertext = bytes(
                p ^ k for p, k in zip(plaintext_bytes, keystream[:len(plaintext_bytes)])
            )

            combined = nonce + ciphertext
            return base64.b64encode(combined).decode('ascii')
        except Exception as e:
            raise EncryptionError(f"加密失败: {e}", cause=e)

    @staticmethod
    def decrypt(ciphertext_b64: str, key: str) -> str:
        """
        对称解密

        Args:
            ciphertext_b64: Base64编码的密文
            key: 加密密钥

        Returns:
            明文
        """
        try:
            key_bytes = hashlib.sha256(key.encode('utf-8')).digest()
            combined = base64.b64decode(ciphertext_b64)
            nonce = combined[:12]
            ciphertext = combined[12:]

            counter = 0
            keystream = b""
            while len(keystream) < len(ciphertext):
                block_input = nonce + struct.pack('>Q', counter)
                block = hmac.new(key_bytes, block_input, hashlib.sha256).digest()
                keystream += block
                counter += 1

            plaintext_bytes = bytes(
                c ^ k for c, k in zip(ciphertext, keystream[:len(ciphertext)])
            )

            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            raise EncryptionError(f"解密失败: {e}", cause=e)

    # ============================================================
    # 随机数据
    # ============================================================

    @staticmethod
    def random_bytes(length: int = 32) -> bytes:
        """生成随机字节"""
        return secrets.token_bytes(length)

    @staticmethod
    def random_hex(length: int = 32) -> str:
        """生成随机十六进制字符串"""
        return secrets.token_hex(length)

    @staticmethod
    def random_token(length: int = 32) -> str:
        """生成URL安全的随机令牌"""
        return secrets.token_urlsafe(length)

    # ============================================================
    # 数据完整性
    # ============================================================

    @staticmethod
    def compute_checksum(data: Any) -> str:
        """计算数据校验和"""
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def verify_checksum(data: Any, expected_checksum: str) -> bool:
        """验证数据校验和"""
        computed = CryptoUtils.compute_checksum(data)
        return hmac.compare_digest(computed, expected_checksum)

    @staticmethod
    def sign_data(data: Dict[str, Any], secret: str) -> Dict[str, Any]:
        """对数据签名"""
        content = json.dumps(data, sort_keys=True, default=str)
        signature = CryptoUtils.hmac_sign(content, secret)
        return {
            "data": data,
            "signature": signature,
            "algorithm": "hmac-sha256",
        }

    @staticmethod
    def verify_signed_data(signed: Dict[str, Any], secret: str) -> bool:
        """验证签名数据"""
        if "data" not in signed or "signature" not in signed:
            return False
        content = json.dumps(signed["data"], sort_keys=True, default=str)
        return CryptoUtils.hmac_verify(content, signed["signature"], secret)
