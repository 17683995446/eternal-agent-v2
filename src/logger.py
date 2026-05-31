"""
日志系统模块

公理溯源：存续公理 - 系统永久在线，需要完整追踪运行状态

设计意图：
- 支持分级日志（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- 支持文件持久化，重启可追溯
- 支持控制台输出，便于实时监控
- 零外部依赖，仅使用Python标准库
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from constants import (
    LOG_PATH,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
)


class EternalLogger:
    """
    永恒智能体日志管理器
    
    公理溯源：存续公理 - 系统运行状态必须可追溯
    
    特性：
    - 单例模式，全局唯一
    - 文件 + 控制台双输出
    - 自动日志轮转
    """
    
    _instance: Optional['EternalLogger'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'EternalLogger':
        """单例模式：确保全局唯一日志管理器"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化日志系统"""
        # 避免重复初始化
        if self._initialized:
            return
        
        self._initialized = True
        self._loggers = {}
        
        # 确保日志目录存在
        log_dir = Path(LOG_PATH).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建根日志器
        self._root_logger = logging.getLogger("EternalAgent")
        self._root_logger.setLevel(getattr(logging, LOG_LEVEL))
        
        # 清除已有处理器（避免重复）
        self._root_logger.handlers.clear()
        
        # 添加文件处理器
        self._add_file_handler()
        
        # 添加控制台处理器
        self._add_console_handler()
    
    def _add_file_handler(self):
        """添加文件日志处理器"""
        file_handler = RotatingFileHandler(
            filename=LOG_PATH,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        self._root_logger.addHandler(file_handler)
    
    def _add_console_handler(self):
        """添加控制台日志处理器"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, LOG_LEVEL))
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        self._root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str = "EternalAgent") -> logging.Logger:
        """
        获取日志器
        
        Args:
            name: 日志器名称
            
        Returns:
            logging.Logger: 日志器实例
        """
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
        return self._loggers[name]
    
    def debug(self, message: str, *args, **kwargs):
        """记录DEBUG级别日志"""
        self._root_logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """记录INFO级别日志"""
        self._root_logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """记录WARNING级别日志"""
        self._root_logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """记录ERROR级别日志"""
        self._root_logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """记录CRITICAL级别日志"""
        self._root_logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """记录异常日志（包含堆栈信息）"""
        self._root_logger.exception(message, *args, **kwargs)


# 全局日志实例
# 设计意图：模块级单例，方便直接导入使用
logger = EternalLogger()


def get_logger(name: str = "EternalAgent") -> logging.Logger:
    """
    获取日志器的便捷函数
    
    Args:
        name: 日志器名称
        
    Returns:
        logging.Logger: 日志器实例
    """
    return logger.get_logger(name)
