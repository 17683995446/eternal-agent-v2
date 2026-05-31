"""
工具函数模块

公理溯源：记忆公理 - 提供文件操作、序列化等通用能力

设计意图：
- 文件操作封装
- 时间处理工具
- 序列化/反序列化
- 唯一ID生成
- 零外部依赖
"""

import json
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Type

logger = None  # 延迟初始化

T = TypeVar('T')


def _get_logger():
    """延迟获取logger，避免循环导入"""
    global logger
    if logger is None:
        from logger import get_logger
        logger = get_logger("Utils")
    return logger


# ============================================================
# 文件操作工具
# ============================================================

def ensure_dir(path: Path) -> Path:
    """
    确保目录存在
    
    Args:
        path: 目录路径
        
    Returns:
        Path: 目录路径
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default: Any = None, max_size: int = 0) -> Any:
    """
    读取JSON文件
    
    Args:
        path: 文件路径
        default: 默认值（文件不存在时返回）
        max_size: 文件大小限制（字节），0表示不限制
        
    Returns:
        Any: JSON数据
    """
    try:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                # 安全检查：文件大小限制
                if max_size > 0:
                    f.seek(0, 2)
                    file_size = f.tell()
                    f.seek(0)
                    if file_size > max_size:
                        _get_logger().error(f"文件过大: {path} ({file_size} bytes > {max_size} bytes)")
                        return default
                return json.load(f)
        return default
    except Exception as e:
        _get_logger().error(f"读取JSON文件失败: {path}, 错误: {e}")
        return default


def write_json(path: Path, data: Any, indent: int = 2) -> bool:
    """
    写入JSON文件
    
    Args:
        path: 文件路径
        data: 数据
        indent: 缩进空格数
        
    Returns:
        bool: 是否成功
    """
    try:
        ensure_dir(path.parent)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        _get_logger().error(f"写入JSON文件失败: {path}, 错误: {e}")
        return False


def read_text(path: Path, default: str = "") -> str:
    """
    读取文本文件
    
    Args:
        path: 文件路径
        default: 默认值
        
    Returns:
        str: 文本内容
    """
    try:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return default
    except Exception as e:
        _get_logger().error(f"读取文本文件失败: {path}, 错误: {e}")
        return default


def write_text(path: Path, content: str) -> bool:
    """
    写入文本文件
    
    Args:
        path: 文件路径
        content: 文本内容
        
    Returns:
        bool: 是否成功
    """
    try:
        ensure_dir(path.parent)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        _get_logger().error(f"写入文本文件失败: {path}, 错误: {e}")
        return False


def file_exists(path: Path) -> bool:
    """
    检查文件是否存在
    
    Args:
        path: 文件路径
        
    Returns:
        bool: 是否存在
    """
    return path.exists() and path.is_file()


def delete_file(path: Path) -> bool:
    """
    删除文件
    
    Args:
        path: 文件路径
        
    Returns:
        bool: 是否成功
    """
    try:
        if path.exists():
            path.unlink()
        return True
    except Exception as e:
        _get_logger().error(f"删除文件失败: {path}, 错误: {e}")
        return False


# ============================================================
# 时间处理工具
# ============================================================

def now_iso() -> str:
    """
    获取当前时间的ISO格式字符串
    
    Returns:
        str: ISO格式时间字符串
    """
    return datetime.now().isoformat()


def now_timestamp() -> float:
    """
    获取当前时间戳
    
    Returns:
        float: 时间戳（秒）
    """
    return time.time()


def parse_iso(iso_str: str) -> Optional[datetime]:
    """
    解析ISO格式时间字符串
    
    Args:
        iso_str: ISO格式时间字符串
        
    Returns:
        Optional[datetime]: datetime对象
    """
    try:
        return datetime.fromisoformat(iso_str)
    except Exception:
        return None


def format_duration(seconds: float) -> str:
    """
    格式化时长
    
    Args:
        seconds: 秒数
        
    Returns:
        str: 格式化后的时长字符串
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


# ============================================================
# ID生成工具
# ============================================================

def generate_uuid() -> str:
    """
    生成UUID
    
    Returns:
        str: UUID字符串
    """
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """
    生成短ID
    
    Args:
        length: ID长度
        
    Returns:
        str: 短ID
    """
    return uuid.uuid4().hex[:length]


# ============================================================
# 序列化工具
# ============================================================

def serialize(obj: Any) -> str:
    """
    序列化对象为JSON字符串
    
    Args:
        obj: 对象
        
    Returns:
        str: JSON字符串
    """
    return json.dumps(obj, ensure_ascii=False, default=str)


def deserialize(json_str: str) -> Any:
    """
    反序列化JSON字符串
    
    Args:
        json_str: JSON字符串
        
    Returns:
        Any: 对象
    """
    return json.loads(json_str)


# ============================================================
# 列表/字典工具
# ============================================================

def unique_list(items: List[Any]) -> List[Any]:
    """
    列表去重（保持顺序）
    
    Args:
        items: 列表
        
    Returns:
        List[Any]: 去重后的列表
    """
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    分块列表
    
    Args:
        items: 列表
        chunk_size: 块大小
        
    Returns:
        List[List[Any]]: 分块后的列表
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """
    深度合并字典
    
    Args:
        dict1: 字典1
        dict2: 字典2
        
    Returns:
        Dict: 合并后的字典
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ============================================================
# 验证工具
# ============================================================

def is_valid_weight(weight: float) -> bool:
    """
    验证权重值是否有效
    
    Args:
        weight: 权重值
        
    Returns:
        bool: 是否有效
    """
    return 0.0 <= weight <= 1.0


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    限制值在范围内
    
    Args:
        value: 值
        min_val: 最小值
        max_val: 最大值
        
    Returns:
        float: 限制后的值
    """
    return max(min_val, min(max_val, value))
