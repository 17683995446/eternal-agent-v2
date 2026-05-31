"""
异常模块测试

验证目标：
1. 异常层级正确
2. 异常消息清晰
3. 原始异常可追溯
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exceptions import (
    EternalAgentError,
    SurvivalError,
    SystemOverloadError,
    SelfRepairError,
    MaxConsecutiveErrorsError,
    MemoryError,
    KnowledgeGraphError,
    NodeNotFoundError,
    EdgeNotFoundError,
    PersistenceError,
    SelfDriveError,
    TaskError,
    TaskQueueFullError,
    ConfigError,
    ConfigLoadError,
    ResourceError,
    MemoryLimitExceededError,
)


class TestExceptionHierarchy:
    """异常层级测试类"""
    
    def test_base_exception(self):
        """测试基础异常"""
        exc = EternalAgentError("test error")
        assert str(exc) == "test error"
        assert isinstance(exc, Exception)
    
    def test_survival_exceptions(self):
        """测试存续层异常"""
        exc = SurvivalError("survival error")
        assert isinstance(exc, EternalAgentError)
        
        exc2 = SystemOverloadError("overload")
        assert isinstance(exc2, SurvivalError)
        
        exc3 = SelfRepairError("repair failed")
        assert isinstance(exc3, SurvivalError)
    
    def test_memory_exceptions(self):
        """测试记忆层异常"""
        exc = MemoryError("memory error")
        assert isinstance(exc, EternalAgentError)
        
        exc2 = KnowledgeGraphError("kg error")
        assert isinstance(exc2, MemoryError)
        
        exc3 = NodeNotFoundError("node not found")
        assert isinstance(exc3, KnowledgeGraphError)
        
        exc4 = PersistenceError("persistence error")
        assert isinstance(exc4, MemoryError)
    
    def test_self_drive_exceptions(self):
        """测试自驱层异常"""
        exc = SelfDriveError("self drive error")
        assert isinstance(exc, EternalAgentError)
        
        exc2 = TaskError("task error")
        assert isinstance(exc2, SelfDriveError)
        
        exc3 = TaskQueueFullError("queue full")
        assert isinstance(exc3, SelfDriveError)
    
    def test_config_exceptions(self):
        """测试配置异常"""
        exc = ConfigError("config error")
        assert isinstance(exc, EternalAgentError)
        
        exc2 = ConfigLoadError("load error")
        assert isinstance(exc2, ConfigError)
    
    def test_resource_exceptions(self):
        """测试资源异常"""
        exc = ResourceError("resource error")
        assert isinstance(exc, EternalAgentError)
        
        exc2 = MemoryLimitExceededError("memory exceeded")
        assert isinstance(exc2, ResourceError)


class TestExceptionWithCause:
    """带原因的异常测试类"""
    
    def test_exception_with_cause(self):
        """测试异常携带原始异常"""
        original = ValueError("original error")
        exc = EternalAgentError("wrapped error", cause=original)
        
        assert exc.cause == original
        assert "original error" in str(exc)
        assert "wrapped error" in str(exc)
    
    def test_exception_without_cause(self):
        """测试异常不带原始异常"""
        exc = EternalAgentError("simple error")
        assert exc.cause is None
        assert str(exc) == "simple error"


class TestExceptionRaising:
    """异常抛出测试类"""
    
    def test_raise_and_catch(self):
        """测试抛出和捕获"""
        with pytest.raises(SystemOverloadError) as exc_info:
            raise SystemOverloadError("CPU overload")
        
        assert "CPU overload" in str(exc_info.value)
    
    def test_catch_by_base_class(self):
        """测试通过基类捕获"""
        with pytest.raises(EternalAgentError):
            raise TaskQueueFullError("queue is full")
    
    def test_catch_by_category(self):
        """测试通过类别捕获"""
        with pytest.raises(SelfDriveError):
            raise TaskError("task failed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
