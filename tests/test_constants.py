"""
常量模块测试

验证目标：
1. 所有常量可被三大公理解释
2. 常量值符合设计约束
"""

import pytest
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from constants import (
    LOOP_DELAY,
    EVOLVE_STEP,
    TASK_QUEUE_MAX,
    KG_SAVE_PATH,
    SystemState,
    TaskState,
    NodeType,
    RelationType,
)


class TestConstants:
    """常量测试类"""
    
    def test_loop_delay_positive(self):
        """测试主循环延迟为正值"""
        assert LOOP_DELAY > 0, "主循环延迟必须为正值"
        assert LOOP_DELAY < 1, "主循环延迟应小于1秒，避免CPU占用过高"
    
    def test_evolve_step_positive(self):
        """测试进化步数为正整数"""
        assert EVOLVE_STEP > 0, "进化步数必须为正整数"
        assert isinstance(EVOLVE_STEP, int), "进化步数必须为整数"
    
    def test_task_queue_max_reasonable(self):
        """测试任务队列上限合理"""
        assert TASK_QUEUE_MAX > 0, "任务队列上限必须为正值"
        assert TASK_QUEUE_MAX <= 1000, "任务队列上限不应过大"
    
    def test_kg_save_path_is_path(self):
        """测试知识图谱保存路径"""
        assert isinstance(KG_SAVE_PATH, Path), "知识图谱保存路径应为Path对象"
    
    def test_system_state_values(self):
        """测试系统状态枚举值"""
        assert hasattr(SystemState, 'INITIALIZING')
        assert hasattr(SystemState, 'RUNNING')
        assert hasattr(SystemState, 'IDLE')
        assert hasattr(SystemState, 'REPAIRING')
        assert hasattr(SystemState, 'SHUTTING_DOWN')
    
    def test_task_state_values(self):
        """测试任务状态枚举值"""
        assert hasattr(TaskState, 'PENDING')
        assert hasattr(TaskState, 'RUNNING')
        assert hasattr(TaskState, 'COMPLETED')
        assert hasattr(TaskState, 'FAILED')
    
    def test_node_type_values(self):
        """测试节点类型枚举值"""
        assert hasattr(NodeType, 'TASK')
        assert hasattr(NodeType, 'ENTITY')
        assert hasattr(NodeType, 'CONCEPT')
        assert hasattr(NodeType, 'KNOWLEDGE')
    
    def test_relation_type_values(self):
        """测试关系类型枚举值"""
        assert hasattr(RelationType, 'DERIVED')
        assert hasattr(RelationType, 'RELATED')
        assert hasattr(RelationType, 'DEPENDS_ON')
        assert hasattr(RelationType, 'EVOLVED_FROM')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
