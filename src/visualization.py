"""
知识图谱可视化模块

公理溯源：记忆公理 - 将结构化知识转化为人类可理解的图形

设计意图：
- 多格式输出（Mermaid、ASCII、JSON、HTML）
- 子图提取
- 路径高亮
- 统计图表
- 零外部依赖
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from exceptions import EternalAgentError


class VisualizationError(EternalAgentError):
    """可视化异常"""
    pass


class KnowledgeVisualizer:
    """
    知识图谱可视化器

    支持格式：
    - mermaid: Mermaid流程图语法
    - ascii: ASCII字符图
    - json: 结构化JSON
    - html: 内嵌HTML页面
    - stats: 统计摘要
    """

    def __init__(self, knowledge_graph=None):
        self._kg = knowledge_graph

    def set_knowledge_graph(self, kg) -> None:
        """设置知识图谱"""
        self._kg = kg

    def render_mermaid(
        self,
        direction: str = "LR",
        highlight_nodes: Optional[List[str]] = None,
        max_nodes: int = 100,
    ) -> str:
        """渲染Mermaid图"""
        if self._kg is None:
            return "graph LR\n    empty[空图谱]"

        nodes = {}
        edges = []

        # 收集节点
        for name, node in self._kg._nodes.items():
            if len(nodes) >= max_nodes:
                break
            label = self._escape_mermaid(name)
            node_style = ""
            if highlight_nodes and name in highlight_nodes:
                node_style = " ::::highlight"
            nodes[name] = f"    {self._mermaid_id(name)}[{label}]{node_style}"

        # 收集边
        for edge in self._kg._edges:
            if edge.source in nodes and edge.target in nodes:
                style = ""
                if edge.weight >= 0.7:
                    style = " ::::strong"
                elif edge.weight < 0.3:
                    style = " ::::weak"
                edges.append(
                    f"    {self._mermaid_id(edge.source)} -->|{edge.relation} {edge.weight:.1f}| "
                    f"{self._mermaid_id(edge.target)}{style}"
                )

        lines = [f"graph {direction}"]
        lines.extend(nodes.values())
        lines.append("")
        lines.append("    classDef highlight fill:#ff9,stroke:#333,stroke-width:2px")
        lines.append("    classDef strong stroke:#333,stroke-width:3px")
        lines.append("    classDef weak stroke:#ccc,stroke-dasharray: 5 5")
        lines.extend(edges)

        return "\n".join(lines)

    def render_ascii(self, max_nodes: int = 30, max_edges: int = 50) -> str:
        """渲染ASCII图"""
        if self._kg is None or self._kg.is_empty():
            return "  (空图谱)"

        lines = []
        lines.append("╔══════════════════════════════════════╗")
        lines.append("║      知识图谱 ASCII 视图            ║")
        lines.append("╠══════════════════════════════════════╣")

        # 节点列表
        node_count = 0
        for name, node in self._kg._nodes.items():
            if node_count >= max_nodes:
                lines.append(f"  ... 还有 {self._kg.node_count - max_nodes} 个节点")
                break
            marker = "●" if node.valid else "○"
            type_tag = node.node_type[:3]
            lines.append(f"  {marker} [{type_tag}] {name}")
            node_count += 1

        lines.append("╠══════════════════════════════════════╣")

        # 边列表
        edge_count = 0
        for edge in self._kg._edges:
            if edge_count >= max_edges:
                lines.append(f"  ... 还有 {self._kg.edge_count - max_edges} 条边")
                break
            if not edge.source or not edge.target:
                continue
            weight_bar = "█" * int(edge.weight * 5) + "░" * (5 - int(edge.weight * 5))
            lines.append(f"  {edge.source[:15]:15s} ─{weight_bar}→ {edge.target[:15]:15s} [{edge.relation}]")
            edge_count += 1

        lines.append("╚══════════════════════════════════════╝")
        return "\n".join(lines)

    def render_json(self) -> Dict[str, Any]:
        """渲染为结构化JSON"""
        if self._kg is None:
            return {"nodes": [], "edges": [], "stats": {}}

        return {
            "nodes": [
                {
                    "name": n.name,
                    "type": n.node_type,
                    "valid": n.valid,
                    "attributes": n.attributes,
                }
                for n in self._kg._nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                    "weight": round(e.weight, 3),
                }
                for e in self._kg._edges
            ],
            "stats": self._kg.stats(),
        }

    def render_stats(self) -> str:
        """渲染统计摘要"""
        if self._kg is None:
            return "图谱未加载"

        stats = self._kg.stats()
        lines = [
            "┌─ 知识图谱统计 ─────────────────┐",
            f"│ 节点数: {stats['node_count']:<22}│",
            f"│ 边数:   {stats['edge_count']:<22}│",
            f"│ 密度:   {stats['density']:<22.4f}│",
            "├─ 节点类型分布 ─────────────────┤",
        ]

        type_counts = defaultdict(int)
        for node in self._kg._nodes.values():
            type_counts[node.node_type] += 1

        for ntype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 20)
            lines.append(f"│ {ntype:<8} {bar:<14} {count:<5}│")

        lines.append("├─ 边关系分布 ───────────────────┤")

        rel_counts = defaultdict(int)
        for edge in self._kg._edges:
            rel_counts[edge.relation] += 1

        for rel, count in sorted(rel_counts.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 20)
            lines.append(f"│ {rel:<10} {bar:<12} {count:<5}│")

        lines.append("└────────────────────────────────┘")
        return "\n".join(lines)

    def render_html(self, title: str = "知识图谱") -> str:
        """渲染为HTML页面"""
        if self._kg is None:
            return "<html><body><h1>图谱未加载</h1></body></html>"

        mermaid_code = self.render_mermaid()
        stats = self.render_stats()

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: 'Noto Sans SC', sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #333; border-bottom: 2px solid #4a90d9; padding-bottom: 10px; }}
        .panel {{ background: white; border-radius: 8px; padding: 20px; margin: 15px 0;
                  box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        .stats {{ white-space: pre; font-family: monospace; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="panel">
            <h2>图谱可视化 (Mermaid)</h2>
            <pre class="mermaid">{mermaid_code}</pre>
        </div>
        <div class="panel">
            <h2>统计信息</h2>
            <pre class="stats">{stats}</pre>
        </div>
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true }});
    </script>
</body>
</html>"""

    def extract_subgraph(self, center_node: str, depth: int = 1) -> 'KnowledgeVisualizer':
        """提取子图"""
        if self._kg is None:
            return KnowledgeVisualizer()

        visited_nodes = set()
        visited_edges = []

        def _bfs(node_name: str, current_depth: int):
            if current_depth > depth or node_name in visited_nodes:
                return
            visited_nodes.add(node_name)
            for edge in self._kg._edges:
                if edge.source == node_name and edge.target not in visited_nodes:
                    visited_edges.append(edge)
                    _bfs(edge.target, current_depth + 1)
                elif edge.target == node_name and edge.source not in visited_nodes:
                    visited_edges.append(edge)
                    _bfs(edge.source, current_depth + 1)

        _bfs(center_node, 0)

        # 创建子图可视化
        sub = KnowledgeVisualizer()
        sub._kg = type('SubKG', (), {
            '_nodes': {n: self._kg._nodes[n] for n in visited_nodes if n in self._kg._nodes},
            '_edges': visited_edges,
            'is_empty': lambda: len(visited_nodes) == 0,
            'node_count': len(visited_nodes),
            'edge_count': len(visited_edges),
            'stats': lambda _self=None: {"node_count": len(visited_nodes), "edge_count": len(visited_edges), "density": 0},
        })()
        return sub

    def find_paths(self, start: str, end: str, max_depth: int = 5) -> List[List[str]]:
        """查找两节点间的路径（BFS）"""
        if self._kg is None:
            return []

        # 构建邻接表
        adj = defaultdict(list)
        for edge in self._kg._edges:
            adj[edge.source].append(edge.target)
            adj[edge.target].append(edge.source)

        paths = []
        queue = [[start]]
        while queue and len(paths) < 10:
            path = queue.pop(0)
            if len(path) > max_depth + 1:
                continue
            current = path[-1]
            if current == end:
                paths.append(path)
                continue
            for neighbor in adj[current]:
                if neighbor not in path:
                    queue.append(path + [neighbor])

        return paths

    def _escape_mermaid(self, text: str) -> str:
        """转义Mermaid特殊字符"""
        if text is None:
            return ""
        return text.replace('"', "'").replace("[", "(").replace("]", ")")

    def _mermaid_id(self, name: str) -> str:
        """生成Mermaid节点ID"""
        import re
        if name is None:
            return "unknown"
        safe = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '_', str(name))
        return safe[:30]
