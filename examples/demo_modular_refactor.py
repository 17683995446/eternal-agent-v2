"""
模块化重构示例 - 演示如何让现有模块符合接口规范

以 knowledge_graph 为例，展示：
1. 定义模块边界
2. 实现模块接口
3. 注册到注册中心
"""
from typing import Any, Dict, List, Optional
from pathlib import Path

from module_interface import (
    IDataModule, ModuleBase, ModuleInfo, ModulePriority,
    ModuleBoundary, HealthStatus
)
from module_registry import register_module, get_registry


# ============================================================
# 第一步：定义模块边界
# ============================================================

KNOWLEDGE_GRAPH_BOUNDARY = ModuleBoundary(
    module_name="knowledge_graph",
    inputs=["node_name", "edge_definition", "query"],
    outputs=["node", "edge", "query_result"],
    dependencies=["logger", "exceptions"],
    capabilities=[
        "add_node",
        "get_node",
        "remove_node",
        "add_edge",
        "get_edges",
        "query",
        "export",
        "health_check",
    ]
)


# ============================================================
# 第二步：实现模块接口
# ============================================================

class KnowledgeGraphModule(ModuleBase, IDataModule):
    """
    知识图谱模块 - 符合 IModule + IDataModule 接口
    
    边界清晰：
    - 输入：节点名、边定义、查询条件
    - 输出：节点、边、查询结果
    - 依赖：logger, exceptions
    - 能力：增删改查、导出、健康检查
    """
    
    def __init__(self, save_path: Optional[Path] = None):
        super().__init__(
            name="knowledge_graph",
            version="2.0.0",
            description="知识图谱存储与查询",
            priority=ModulePriority.NORMAL,
            dependencies=["logger", "exceptions"],
            provides=["IDataModule", "IEventModule"],
        )
        
        self._save_path = save_path
        self._nodes: Dict[str, Any] = {}
        self._edges: List[Any] = []
    
    def initialize(self, context: Dict[str, Any]) -> bool:
        """初始化"""
        if not super().initialize(context):
            return False
        
        # 获取依赖
        self._logger = context.get("logger")
        self._exceptions = context.get("exceptions")
        
        # 加载数据
        if self._save_path and self._save_path.exists():
            try:
                import json
                with open(self._save_path, 'r') as f:
                    data = json.load(f)
                self._nodes = data.get("nodes", {})
                self._edges = data.get("edges", [])
            except Exception:
                pass
        
        return True
    
    # ============================================================
    # IDataModule 接口实现
    # ============================================================
    
    def read(self, key: str) -> Optional[Any]:
        """读取节点"""
        return self._nodes.get(key)
    
    def write(self, key: str, value: Any) -> bool:
        """写入节点"""
        self._nodes[key] = value
        return True
    
    def delete(self, key: str) -> bool:
        """删除节点"""
        if key in self._nodes:
            del self._nodes[key]
            # 级联删除相关边
            self._edges = [
                e for e in self._edges
                if e.get("source") != key and e.get("target") != key
            ]
            return True
        return False
    
    def query(self, condition: Dict[str, Any]) -> List[Any]:
        """查询节点"""
        results = []
        node_type = condition.get("type")
        name_pattern = condition.get("name_pattern")
        
        for name, node in self._nodes.items():
            if node_type and node.get("type") != node_type:
                continue
            if name_pattern and name_pattern not in name:
                continue
            results.append(node)
        
        return results
    
    # ============================================================
    # 业务方法（边界内）
    # ============================================================
    
    def add_node(self, name: str, node_type: str, **attrs) -> bool:
        """添加节点"""
        self._nodes[name] = {
            "name": name,
            "type": node_type,
            **attrs
        }
        return True
    
    def get_node(self, name: str) -> Optional[Dict[str, Any]]:
        """获取节点"""
        return self._nodes.get(name)
    
    def add_edge(self, source: str, target: str, relation: str, weight: float = 1.0) -> bool:
        """添加边"""
        if source not in self._nodes or target not in self._nodes:
            return False
        self._edges.append({
            "source": source,
            "target": target,
            "relation": relation,
            "weight": weight,
        })
        return True
    
    def get_edges(self, source: Optional[str] = None, target: Optional[str] = None) -> List[Dict]:
        """获取边"""
        edges = self._edges
        if source:
            edges = [e for e in edges if e["source"] == source]
        if target:
            edges = [e for e in edges if e["target"] == target]
        return edges
    
    def health_check(self) -> HealthStatus:
        """健康检查"""
        return HealthStatus(
            healthy=True,
            message=f"Nodes: {len(self._nodes)}, Edges: {len(self._edges)}",
            details={
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
            }
        )
    
    def stats(self) -> Dict[str, Any]:
        """统计信息"""
        return {
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "node_types": list(set(n.get("type") for n in self._nodes.values())),
        }


# ============================================================
# 第三步：注册模块
# ============================================================

def create_and_register(save_path: Optional[Path] = None) -> KnowledgeGraphModule:
    """创建并注册模块"""
    module = KnowledgeGraphModule(save_path)
    register_module(module, KNOWLEDGE_GRAPH_BOUNDARY)
    return module


# ============================================================
# 使用示例
# ============================================================

def demo():
    """演示模块化使用"""
    print("=" * 60)
    print("📦 模块化重构示例")
    print("=" * 60)
    
    # 创建模块
    kg = create_and_register()
    
    # 初始化（模拟上下文）
    context = {
        "logger": None,  # 实际使用时传入真实logger
        "exceptions": None,
    }
    kg.initialize(context)
    
    # 使用模块
    print("\n添加节点:")
    kg.add_node("Python", "language")
    kg.add_node("Java", "language")
    kg.add_node("编程", "concept")
    print(f"  Python, Java, 编程")
    
    print("\n添加边:")
    kg.add_edge("Python", "编程", "is_a")
    kg.add_edge("Java", "编程", "is_a")
    print(f"  Python -> 编程, Java -> 编程")
    
    print("\n查询:")
    results = kg.query({"type": "language"})
    print(f"  语言类型节点: {[r['name'] for r in results]}")
    
    print("\n健康检查:")
    health = kg.health_check()
    print(f"  {health.message}")
    
    print("\n模块信息:")
    print(f"  名称: {kg.info.name}")
    print(f"  版本: {kg.info.version}")
    print(f"  状态: {kg.state.value}")
    print(f"  依赖: {kg.info.dependencies}")
    
    # 查看注册中心
    print("\n注册中心:")
    registry = get_registry()
    print(f"  模块数: {len(registry.get_all())}")
    
    print("=" * 60)


if __name__ == "__main__":
    demo()
