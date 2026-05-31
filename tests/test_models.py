"""
类型模块测试

验证目标：
1. Node、Edge、Task数据结构正确
2. 序列化/反序列化正常
3. 权重范围限制有效
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models import Node, Edge, Task, SystemStatus
from constants import NodeType, RelationType, TaskState


class TestNode:
    """节点测试类"""
    
    def test_node_creation(self):
        """测试节点创建"""
        node = Node(name="test_node")
        assert node.name == "test_node"
        assert node.valid == True
        assert node.node_type == NodeType.ENTITY
    
    def test_node_timestamp(self):
        """测试节点时间戳"""
        node = Node(name="test_node")
        assert node.created_at is not None
        assert node.updated_at is not None
    
    def test_node_to_dict(self):
        """测试节点序列化"""
        node = Node(name="test_node", node_type=NodeType.TASK)
        data = node.to_dict()
        assert data["name"] == "test_node"
        assert data["node_type"] == NodeType.TASK
    
    def test_node_from_dict(self):
        """测试节点反序列化"""
        data = {
            "name": "test_node",
            "node_type": NodeType.CONCEPT,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "valid": True,
            "attributes": {}
        }
        node = Node.from_dict(data)
        assert node.name == "test_node"
        assert node.node_type == NodeType.CONCEPT
    
    def test_node_hash_and_equality(self):
        """测试节点哈希和相等性"""
        node1 = Node(name="test")
        node2 = Node(name="test")
        node3 = Node(name="other")
        
        assert hash(node1) == hash(node2)
        assert node1 == node2
        assert node1 != node3


class TestEdge:
    """边测试类"""
    
    def test_edge_creation(self):
        """测试边创建"""
        edge = Edge(source="node_a", target="node_b")
        assert edge.source == "node_a"
        assert edge.target == "node_b"
        assert edge.weight == 0.5  # 默认权重
    
    def test_edge_weight_clamp(self):
        """测试边权重范围限制"""
        # 权重超过上限
        edge1 = Edge(source="a", target="b", weight=1.5)
        assert edge1.weight == 1.0
        
        # 权重低于下限
        edge2 = Edge(source="a", target="b", weight=-0.5)
        assert edge2.weight == 0.0
    
    def test_edge_update_weight(self):
        """测试边权重更新"""
        edge = Edge(source="a", target="b", weight=0.5)
        edge.update_weight(0.3)
        assert edge.weight == 0.8
        
        # 测试上限
        edge.update_weight(0.5)
        assert edge.weight == 1.0
    
    def test_edge_to_dict_and_from_dict(self):
        """测试边序列化和反序列化"""
        edge = Edge(
            source="a", 
            target="b", 
            relation=RelationType.DERIVED,
            weight=0.8
        )
        data = edge.to_dict()
        restored = Edge.from_dict(data)
        
        assert restored.source == "a"
        assert restored.target == "b"
        assert restored.relation == RelationType.DERIVED
        assert restored.weight == 0.8


class TestTask:
    """任务测试类"""
    
    def test_task_creation(self):
        """测试任务创建"""
        task = Task(name="test_task")
        assert task.name == "test_task"
        assert task.state == TaskState.PENDING
        assert task.priority == 0
    
    def test_task_lifecycle(self):
        """测试任务生命周期"""
        task = Task(name="test_task")
        
        # 开始
        task.start()
        assert task.state == TaskState.RUNNING
        assert task.started_at is not None
        
        # 完成
        task.complete("success")
        assert task.state == TaskState.COMPLETED
        assert task.result == "success"
        assert task.completed_at is not None
    
    def test_task_failure(self):
        """测试任务失败"""
        task = Task(name="test_task")
        task.start()
        task.fail("error message")
        
        assert task.state == TaskState.FAILED
        assert task.error == "error message"
    
    def test_task_priority_sorting(self):
        """测试任务优先级排序"""
        task1 = Task(name="low", priority=1)
        task2 = Task(name="high", priority=10)
        task3 = Task(name="mid", priority=5)
        
        tasks = sorted([task1, task2, task3])
        assert tasks[0].name == "high"  # 最高优先级排最前


class TestSystemStatus:
    """系统状态测试类"""
    
    def test_status_creation(self):
        """测试状态创建"""
        status = SystemStatus()
        assert status.state == "initializing"
        assert status.run_counter == 0
    
    def test_status_to_dict_and_from_dict(self):
        """测试状态序列化和反序列化"""
        status = SystemStatus(
            state="running",
            run_counter=100,
            total_tasks_completed=50
        )
        data = status.to_dict()
        restored = SystemStatus.from_dict(data)
        
        assert restored.state == "running"
        assert restored.run_counter == 100
        assert restored.total_tasks_completed == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
