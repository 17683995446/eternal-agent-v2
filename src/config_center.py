"""
配置中心模块

公理溯源：存续公理 - 系统运行时可动态调整参数，无需重启

设计意图：
- 分层配置（默认 → 全局 → 环境 → 运行时覆盖）
- 配置变更监听
- 配置验证
- 配置热更新
- 零外部依赖
"""

import copy
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from exceptions import EternalAgentError


class ConfigCenterError(EternalAgentError):
    """配置中心异常"""
    pass


class ConfigValidationError(ConfigCenterError):
    """配置验证异常"""
    pass


class ConfigNotFoundError(ConfigCenterError):
    """配置项不存在异常"""
    pass


@dataclass
class ConfigSchema:
    """配置项Schema定义"""
    key: str
    value_type: str  # str, int, float, bool, list, dict
    default: Any = None
    description: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    required: bool = False
    group: str = "default"


@dataclass
class ConfigChange:
    """配置变更记录"""
    key: str
    old_value: Any
    new_value: Any
    source: str  # default, file, runtime, environment
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ConfigCenter:
    """
    配置中心

    分层优先级（从低到高）：
    1. 默认值（Schema定义）
    2. 配置文件
    3. 环境变量
    4. 运行时设置

    职责：
    - 管理配置生命周期
    - 配置变更通知
    - 配置验证
    - 配置导出/导入
    """

    def __init__(self, config_dir: Optional[Path] = None):
        self._config_dir = config_dir or Path(__file__).parent.parent / "data" / "config_center"
        self._config_dir.mkdir(parents=True, exist_ok=True)

        self._schemas: Dict[str, ConfigSchema] = {}
        self._values: Dict[str, Any] = {}
        self._file_values: Dict[str, Any] = {}
        self._env_values: Dict[str, Any] = {}
        self._runtime_values: Dict[str, Any] = {}

        self._listeners: Dict[str, List[Callable[[ConfigChange], None]]] = {}
        self._global_listeners: List[Callable[[ConfigChange], None]] = []
        self._change_history: List[ConfigChange] = []
        self._lock = threading.RLock()

    @property
    def config_dir(self) -> Path:
        return self._config_dir

    @property
    def keys(self) -> List[str]:
        return list(self._schemas.keys())

    @property
    def groups(self) -> List[str]:
        return list(set(s.group for s in self._schemas.values()))

    def register_schema(self, schema: ConfigSchema) -> None:
        """注册配置Schema"""
        with self._lock:
            self._schemas[schema.key] = schema
            if schema.key not in self._values:
                self._values[schema.key] = copy.deepcopy(schema.default)

    def register_schemas(self, schemas: List[ConfigSchema]) -> None:
        """批量注册Schema"""
        for s in schemas:
            self.register_schema(s)

    def get_schema(self, key: str) -> Optional[ConfigSchema]:
        """获取Schema"""
        return self._schemas.get(key)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（自动按优先级合并）

        优先级：runtime > env > file > default
        """
        with self._lock:
            if key in self._runtime_values:
                return copy.deepcopy(self._runtime_values[key])
            if key in self._env_values:
                return copy.deepcopy(self._env_values[key])
            if key in self._file_values:
                return copy.deepcopy(self._file_values[key])
            if key in self._values:
                return copy.deepcopy(self._values[key])
            return default

    def set(self, key: str, value: Any, source: str = "runtime") -> bool:
        """
        设置配置值

        Args:
            key: 配置键
            value: 配置值
            source: 来源 (runtime, file, environment)
        """
        with self._lock:
            # 验证
            if key in self._schemas:
                schema = self._schemas[key]
                value = self._validate_value(schema, value)
                if value is None and schema.required:
                    raise ConfigValidationError(f"配置 '{key}' 是必填项")

            old_value = self.get(key)

            if source == "runtime":
                self._runtime_values[key] = value
            elif source == "environment":
                self._env_values[key] = value
            elif source == "file":
                self._file_values[key] = value
            else:
                self._values[key] = value

            # 记录变更
            change = ConfigChange(
                key=key,
                old_value=old_value,
                new_value=value,
                source=source,
            )
            self._change_history.append(change)

            # 通知监听器
            self._notify_listeners(key, change)

            return True

    def delete(self, key: str, source: str = "runtime") -> bool:
        """删除配置值"""
        with self._lock:
            target = {
                "runtime": self._runtime_values,
                "environment": self._env_values,
                "file": self._file_values,
            }.get(source, self._runtime_values)

            if key in target:
                old = target.pop(key)
                change = ConfigChange(key=key, old_value=old, new_value=None, source=source)
                self._change_history.append(change)
                self._notify_listeners(key, change)
                return True
            return False

    def reset(self, key: str) -> None:
        """重置配置到默认值"""
        with self._lock:
            self._runtime_values.pop(key, None)
            self._env_values.pop(key, None)
            self._file_values.pop(key, None)

    def on_change(self, key: str, callback: Callable[[ConfigChange], None]) -> None:
        """注册配置变更监听器"""
        with self._lock:
            if key not in self._listeners:
                self._listeners[key] = []
            self._listeners[key].append(callback)

    def on_any_change(self, callback: Callable[[ConfigChange], None]) -> None:
        """注册全局变更监听器"""
        self._global_listeners.append(callback)

    def load_from_file(self, file_path: Path) -> int:
        """从文件加载配置"""
        if not file_path.exists():
            return 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            count = 0
            for key, value in data.items():
                self.set(key, value, source="file")
                count += 1
            return count
        except Exception as e:
            raise ConfigCenterError(f"加载配置文件失败: {e}", cause=e)

    def save_to_file(self, file_path: Optional[Path] = None) -> None:
        """保存当前配置到文件"""
        path = file_path or self._config_dir / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            all_values = {}
            for key in self._schemas:
                all_values[key] = self.get(key)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(all_values, f, ensure_ascii=False, indent=2, default=str)

    def load_from_env(self, prefix: str = "ETERNAL_") -> int:
        """从环境变量加载配置"""
        import os
        count = 0
        for key, schema in self._schemas.items():
            env_key = f"{prefix}{key.upper()}"
            env_val = os.environ.get(env_key)
            if env_val is not None:
                typed_val = self._parse_env_value(env_val, schema.value_type)
                self.set(key, typed_val, source="environment")
                count += 1
        return count

    def get_group(self, group: str) -> Dict[str, Any]:
        """获取指定组的所有配置"""
        result = {}
        for key, schema in self._schemas.items():
            if schema.group == group:
                result[key] = self.get(key)
        return result

    def get_change_history(self, key: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取变更历史"""
        changes = self._change_history
        if key:
            changes = [c for c in changes if c.key == key]
        return [
            {"key": c.key, "old": c.old_value, "new": c.new_value, "source": c.source, "ts": c.timestamp}
            for c in changes[-limit:]
        ]

    def validate_all(self) -> List[str]:
        """验证所有配置"""
        errors = []
        for key, schema in self._schemas.items():
            value = self.get(key)
            try:
                self._validate_value(schema, value)
            except ConfigValidationError as e:
                errors.append(f"{key}: {e}")
        return errors

    def export(self) -> Dict[str, Any]:
        """导出所有配置"""
        result = {}
        for key in self._schemas:
            result[key] = self.get(key)
        return result

    def import_config(self, data: Dict[str, Any], source: str = "runtime") -> int:
        """导入配置"""
        count = 0
        for key, value in data.items():
            self.set(key, value, source=source)
            count += 1
        return count

    def _convert_type(self, value: Any, value_type: str) -> Any:
        """类型转换辅助方法"""
        if value_type == "int":
            return int(value)
        elif value_type == "float":
            return float(value)
        elif value_type == "bool":
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        elif value_type == "str":
            return str(value)
        elif value_type == "list":
            if isinstance(value, str):
                return [v.strip() for v in value.split(",")]
            return value
        elif value_type == "dict":
            if isinstance(value, str):
                import json as _json
                return _json.loads(value)
            return value
        return value

    def _validate_range(self, value: Any, min_val: Any, max_val: Any) -> None:
        """范围检查辅助方法"""
        if not isinstance(value, (int, float)):
            return
        if min_val is not None and value < min_val:
            raise ConfigValidationError(f"值 {value} 小于最小值 {min_val}")
        if max_val is not None and value > max_val:
            raise ConfigValidationError(f"值 {value} 大于最大值 {max_val}")

    def _validate_allowed(self, value: Any, allowed: List[Any]) -> None:
        """允许值检查辅助方法"""
        if allowed and value not in allowed:
            raise ConfigValidationError(f"值 {value} 不在允许列表中: {allowed}")

    def _validate_value(self, schema: ConfigSchema, value: Any) -> Any:
        """验证配置值"""
        if value is None:
            return schema.default

        # 类型转换
        try:
            value = self._convert_type(value, schema.value_type)
        except (ValueError, TypeError) as e:
            raise ConfigValidationError(f"类型转换失败: {e}")

        # 范围检查
        self._validate_range(value, schema.min_value, schema.max_value)

        # 允许值检查
        self._validate_allowed(value, schema.allowed_values)

        return value

    def _parse_env_value(self, env_val: str, value_type: str) -> Any:
        """解析环境变量值"""
        if value_type == "int":
            return int(env_val)
        elif value_type == "float":
            return float(env_val)
        elif value_type == "bool":
            return env_val.lower() in ("true", "1", "yes")
        elif value_type == "list":
            return [v.strip() for v in env_val.split(",")]
        elif value_type == "dict":
            return json.loads(env_val)
        return env_val

    def _notify_listeners(self, key: str, change: ConfigChange) -> None:
        """通知监听器"""
        for cb in self._listeners.get(key, []):
            try:
                cb(change)
            except Exception:
                pass
        for cb in self._global_listeners:
            try:
                cb(change)
            except Exception:
                pass
