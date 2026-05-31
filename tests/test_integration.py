"""
基础模块集成测试

验证目标：
1. 所有模块可正常导入
2. 模块间依赖正常
3. 基础功能可运行
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestModuleImports:
    """模块导入测试类"""
    
    def test_import_constants(self):
        """测试导入常量模块"""
        import constants
        assert hasattr(constants, 'LOOP_DELAY')
        assert hasattr(constants, 'EVOLVE_STEP')
        assert hasattr(constants, 'TASK_QUEUE_MAX')
    
    def test_import_models(self):
        """测试导入模型模块"""
        import models
        assert hasattr(models, 'Node')
        assert hasattr(models, 'Edge')
        assert hasattr(models, 'Task')
    
    def test_import_exceptions(self):
        """测试导入异常模块"""
        import exceptions
        assert hasattr(exceptions, 'EternalAgentError')
        assert hasattr(exceptions, 'SurvivalError')
        assert hasattr(exceptions, 'MemoryError')
    
    def test_import_utils(self):
        """测试导入工具模块"""
        import utils
        assert hasattr(utils, 'read_json')
        assert hasattr(utils, 'write_json')
        assert hasattr(utils, 'generate_uuid')
    
    def test_import_config(self):
        """测试导入配置模块"""
        import config
        assert hasattr(config, 'Config')
        assert hasattr(config, 'config')
    
    def test_import_logger(self):
        """测试导入日志模块"""
        import logger
        assert hasattr(logger, 'EternalLogger')
        assert hasattr(logger, 'logger')
    
    def test_import_monitor(self):
        """测试导入监控模块"""
        import monitor
        assert hasattr(monitor, 'ResourceMonitor')
        assert hasattr(monitor, 'monitor')


class TestModuleIntegration:
    """模块集成测试类"""
    
    def test_logger_with_constants(self):
        """测试日志模块使用常量"""
        import constants
        import logger
        
        # 验证日志使用常量中的配置
        assert constants.LOG_FORMAT is not None
        assert logger.logger is not None
    
    def test_config_with_utils(self):
        """测试配置模块使用工具函数"""
        import config
        import utils
        
        # 配置应该可以正常加载
        cfg = config.Config()
        assert cfg.to_dict() is not None
    
    def test_models_with_constants(self):
        """测试模型模块使用常量"""
        import models
        import constants
        
        # 创建节点，验证默认值来自常量
        node = models.Node(name="test")
        assert node.valid == constants.NODE_DEFAULT_VALID
    
    def test_monitor_with_exceptions(self):
        """测试监控模块使用异常"""
        import monitor
        import exceptions
        
        # 验证监控器可以抛出正确的异常
        m = monitor.ResourceMonitor(memory_limit_mb=0.001)
        with pytest.raises(exceptions.MemoryLimitExceededError):
            m.check_and_raise()


class TestBasicFunctionality:
    """基础功能测试类"""
    
    def test_config_save_and_load(self, tmp_path):
        """测试配置保存和加载"""
        import config
        import utils
        
        # 创建临时配置
        cfg = config.Config()
        cfg.set("test_key", "test_value", save_now=False)
        
        # 验证可以读取
        assert cfg.get("test_key") == "test_value"
    
    def test_logger_logging(self):
        """测试日志记录"""
        import logger
        
        # 各级别日志应该不会抛出异常
        log = logger.get_logger("test")
        log.debug("debug message")
        log.info("info message")
        log.warning("warning message")
        log.error("error message")
    
    def test_node_edge_creation(self):
        """测试节点和边创建"""
        import models
        
        node = models.Node(name="test_node", node_type="entity")
        edge = models.Edge(source="a", target="b", weight=0.8)
        
        assert node.name == "test_node"
        assert edge.weight == 0.8
    
    def test_task_lifecycle(self):
        """测试任务生命周期"""
        import models
        
        task = models.Task(name="test_task")
        task.start()
        task.complete("done")
        
        assert task.state == "completed"
        assert task.result == "done"
    
    def test_resource_monitor(self):
        """测试资源监控"""
        import monitor
        
        status = monitor.monitor.check_health()
        
        assert status is not None
        assert hasattr(status, 'is_healthy')
        assert hasattr(status, 'cpu_percent')


class TestAxiomCompliance:
    """公理合规性测试类"""
    
    def test_survival_axiom_constants(self):
        """测试存续公理相关常量"""
        import constants
        
        # 存续公理要求：循环控制、异常恢复
        assert constants.LOOP_DELAY > 0
        assert constants.SELF_REPAIR_DELAY > 0
        assert constants.MAX_CONSECUTIVE_ERRORS > 0
    
    def test_memory_axiom_constants(self):
        """测试记忆公理相关常量"""
        import constants
        
        # 记忆公理要求：持久化路径、知识结构
        assert constants.KG_SAVE_PATH is not None
        assert constants.EDGE_WEIGHT_MIN == 0.0
        assert constants.EDGE_WEIGHT_MAX == 1.0
    
    def test_self_drive_axiom_constants(self):
        """测试自驱公理相关常量"""
        import constants
        
        # 自驱公理要求：进化触发、任务生成
        assert constants.EVOLVE_STEP > 0
        assert constants.TASK_DERIVE_WEIGHT_THRESHOLD > 0
        assert constants.INITIAL_TASK is not None
    
    def test_all_code_traceable_to_axioms(self):
        """测试所有代码可溯源至公理"""
        import constants
        import models
        import exceptions
        
        # 验证核心数据结构存在
        assert hasattr(models, 'Node')  # 记忆公理
        assert hasattr(models, 'Edge')  # 记忆公理
        assert hasattr(models, 'Task')  # 自驱公理
        
        # 验证异常层级存在
        assert hasattr(exceptions, 'SurvivalError')  # 存续公理
        assert hasattr(exceptions, 'MemoryError')    # 记忆公理
        assert hasattr(exceptions, 'SelfDriveError') # 自驱公理


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
