"""
示例1: 基础知识图谱管理

本示例展示如何使用永动知识图谱Agent进行：
- 创建和管理知识图谱
- 添加节点和关系
- 查询和检索知识
- 可视化知识图谱

大事做于细，难事成于易：
- 从简单概念开始，逐步构建复杂知识网络
- 每个操作都有清晰的意图和结果验证
"""

import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from knowledge_graph import KnowledgeGraph
from visualization import KnowledgeVisualizer
from query_language import QueryEngine
from logger import get_logger

logger = get_logger("Example01")


def example_basic_operations():
    """示例：基础操作"""
    print("\n" + "="*60)
    print("示例 1.1: 基础知识图谱操作")
    print("="*60)
    
    # 创建知识图谱实例
    kg = KnowledgeGraph()
    
    # 添加节点 - 技术栈
    print("\n[1] 添加技术节点...")
    kg.add_node("Python", "language")
    kg.add_node("JavaScript", "language")
    kg.add_node("FastAPI", "framework")
    kg.add_node("React", "framework")
    kg.add_node("PostgreSQL", "database")
    kg.add_node("Redis", "database")
    print("  ✓ 添加了6个技术节点")
    
    # 添加关系
    print("\n[2] 添加关系...")
    kg.add_edge("Python", "FastAPI", "powers", 0.95)
    kg.add_edge("JavaScript", "React", "powers", 0.90)
    kg.add_edge("FastAPI", "PostgreSQL", "uses", 0.80)
    kg.add_edge("FastAPI", "Redis", "uses", 0.70)
    print("  ✓ 添加了4个关系")
    
    # 查询节点
    print("\n[3] 查询所有语言...")
    languages = kg.get_nodes_by_type("language")
    for lang in languages:
        print(f"  - {lang.name}")
    
    # 查询关系
    print("\n[4] 查询Python相关的所有关系...")
    related = kg.get_related_nodes("Python")
    for node, edges in related.items():
        for edge in edges:
            print(f"  - Python {edge.relation} {node} (权重: {edge.weight})")
    
    # 保存知识图谱
    print("\n[5] 保存知识图谱...")
    kg.save()
    print("  ✓ 知识图谱已保存")
    
    return kg


def example_query_language():
    """示例：使用查询语言"""
    print("\n" + "="*60)
    print("示例 1.2: 使用查询语言")
    print("="*60)
    
    # 加载知识图谱
    kg = KnowledgeGraph()
    engine = QueryEngine(kg)
    
    # 查询所有节点
    print("\n[1] 查询所有节点...")
    result = engine.execute("FIND nodes")
    print(f"  找到 {len(result.data)} 个节点")
    for node in result.data[:5]:  # 只显示前5个
        if isinstance(node, dict):
            print(f"  - {node.get('name', '?')} ({node.get('type', '?')})")
        else:
            print(f"  - {node.name} ({node.node_type})")
    
    # 按类型查询
    print("\n[2] 查询所有框架...")
    result = engine.execute("FIND nodes WHERE type = 'framework'")
    for node in result.data:
        if isinstance(node, dict):
            print(f"  - {node.get('name', '?')}")
        else:
            print(f"  - {node.name}")
    
    # 统计边数
    print("\n[3] 统计边数...")
    result = engine.execute("COUNT edges")
    print(f"  总边数: {result.data}")
    
    # 搜索节点
    print("\n[4] 搜索包含'Py'的节点...")
    result = engine.execute("SEARCH nodes 'Py'")
    if result.data:
        for node in result.data:
            if isinstance(node, dict):
                print(f"  - {node.get('name', '?')}")
            else:
                print(f"  - {node.name}")
    else:
        print("  未找到匹配节点")


def example_visualization():
    """示例：可视化知识图谱"""
    print("\n" + "="*60)
    print("示例 1.3: 可视化知识图谱")
    print("="*60)
    
    # 加载知识图谱
    kg = KnowledgeGraph()
    visualizer = KnowledgeVisualizer(kg)
    
    # 生成Mermaid图表
    print("\n[1] 生成Mermaid图表...")
    mermaid = visualizer.render_mermaid(direction="TB")
    print("  Mermaid 语法:")
    print("  " + "-"*50)
    for line in mermaid.split('\n')[:15]:  # 只显示前15行
        print(f"  {line}")
    print("  " + "-"*50)
    
    # 生成ASCII图表
    print("\n[2] 生成ASCII图表...")
    ascii_chart = visualizer.render_ascii()
    print(ascii_chart)
    
    # 查找路径
    print("\n[3] 查找从Python到PostgreSQL的路径...")
    paths = visualizer.find_paths("Python", "PostgreSQL", max_depth=3)
    if paths:
        for i, path in enumerate(paths[:3], 1):
            print(f"  路径 {i}: {' -> '.join(path)}")
    else:
        print("  未找到路径")


def example_advanced_operations():
    """示例：高级操作"""
    print("\n" + "="*60)
    print("示例 1.4: 高级知识图谱操作")
    print("="*60)
    
    kg = KnowledgeGraph()
    
    # 添加更多节点和关系
    print("\n[1] 扩展知识图谱...")
    kg.add_node("Machine Learning", "concept")
    kg.add_node("Deep Learning", "concept")
    kg.add_node("Neural Network", "concept")
    kg.add_node("TensorFlow", "library")
    kg.add_node("PyTorch", "library")
    
    # 添加关系
    kg.add_edge("Machine Learning", "Deep Learning", "includes", 0.90)
    kg.add_edge("Deep Learning", "Neural Network", "uses", 0.95)
    kg.add_edge("Python", "TensorFlow", "powers", 0.85)
    kg.add_edge("Python", "PyTorch", "powers", 0.85)
    kg.add_edge("TensorFlow", "Neural Network", "implements", 0.90)
    print("  ✓ 添加了ML相关概念")
    
    # 查询相关节点
    print("\n[2] 查询与Python相关的所有节点...")
    related = kg.get_related_nodes("Python")
    print(f"  找到 {len(related)} 个相关节点")
    for node_name in list(related.keys())[:5]:
        print(f"  - {node_name}")
    
    # 获取统计信息
    print("\n[3] 知识图谱统计...")
    stats = kg.stats()
    print(f"  节点总数: {stats['node_count']}")
    print(f"  边总数: {stats['edge_count']}")
    print(f"  节点类型: {list(stats['node_types'].keys())}")
    
    # 保存
    kg.save()
    print("\n  ✓ 扩展后的知识图谱已保存")


def main():
    """主函数 - 运行所有示例"""
    print("\n" + "="*60)
    print("永动知识图谱Agent - 示例1: 基础知识图谱管理")
    print("="*60)
    
    try:
        # 运行示例
        example_basic_operations()
        example_query_language()
        example_visualization()
        example_advanced_operations()
        
        print("\n" + "="*60)
        print("所有示例运行完成！")
        print("="*60)
        print("\n提示:")
        print("- 知识图谱数据保存在 data/knowledge_graph.json")
        print("- 可以使用 query_language.py 进行更多查询")
        print("- 可以使用 visualization.py 生成各种图表")
        
    except Exception as e:
        logger.error(f"示例运行失败: {e}")
        raise


if __name__ == "__main__":
    main()
