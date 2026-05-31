"""
配置管理模块

公理溯源：记忆公理 - 配置作为系统认知的一部分，需要持久化存储

设计意图：
- 支持JSON格式配置文件
- 支持默认配置
- 支持配置热更新
- 零外部依赖
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from constants import CONFIG_PATH
from logger import get_logger

logger = get_logger("Config")


class Config:
    """
    配置管理器
    
    公理溯源：记忆公理 - 配置是系统的结构化认知
    
    特性：
    - 单例模式
    - 自动加载/保存
    - 默认配置兜底
    """
    
    _instance: Optional['Config'] = None
    _initialized: bool = False
    
    # 默认配置
    DEFAULT_CONFIG: Dict[str, Any] = {
        # 存续配置
        "loop_delay": 0.3,
        "self_repair_delay": 1.0,
        "heartbeat_interval": 60,
        "max_consecutive_errors": 10,
        
        # 记忆配置
        "kg_save_path": "data/knowledge_graph.json",
        
        # 自驱配置
        "evolve_step": 50,
        "task_derive_weight_threshold": 0.2,
        "knowledge_trim_threshold": 0.1,
        "initial_task": "系统初始认知迭代",
        
        # 资源配置
        "task_queue_max": 200,
        "memory_limit_mb": 512,
        "cpu_limit_percent": 80,
        "disk_limit_percent": 90,
        
        # 日志配置
        "log_level": "INFO",
    }
    
    def __new__(cls) -> 'Config':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        if self._initialized:
            return
        
        self._initialized = True
        self._config: Dict[str, Any] = {}
        self._config_path = Path(CONFIG_PATH)
        
        # 加载配置
        self.load()
    
    def load(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        # 尝试从文件加载
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                logger.info(f"配置加载成功: {self._config_path}")
            except Exception as e:
                logger.warning(f"配置加载失败，使用默认配置: {e}")
                self._config = self.DEFAULT_CONFIG.copy()
                self.save()
        else:
            # 文件不存在，使用默认配置并保存
            logger.info("配置文件不存在，创建默认配置")
            self._config = self.DEFAULT_CONFIG.copy()
            self.save()
        
        return self._config
    
    def save(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            bool: 保存是否成功
        """
        try:
            # 确保目录存在
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"配置保存成功: {self._config_path}")
            return True
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any, save_now: bool = True) -> None:
        """
        设置配置项
        
        Args:
            key: 配置键名
            value: 配置值
            save_now: 是否立即保存
        """
        self._config[key] = value
        logger.debug(f"配置更新: {key} = {value}")
        
        if save_now:
            self.save()
    
    def update(self, config_dict: Dict[str, Any], save_now: bool = True) -> None:
        """
        批量更新配置
        
        Args:
            config_dict: 配置字典
            save_now: 是否立即保存
        """
        self._config.update(config_dict)
        logger.debug(f"批量更新配置: {list(config_dict.keys())}")
        
        if save_now:
            self.save()
    
    def reset(self) -> None:
        """重置为默认配置"""
        self._config = self.DEFAULT_CONFIG.copy()
        self.save()
        logger.info("配置已重置为默认值")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        导出配置为字典
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return self._config.copy()
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self._config[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """支持字典式设置"""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """支持 in 操作符"""
        return key in self._config


# 全局配置实例
config = Config()
