"""
知识图谱查询语言模块

公理溯源：记忆公理 - 提供简洁的查询接口访问知识

设计意图：
- 简化查询语法
- 支持节点查询、边查询、路径查询、统计查询
- 查询结果标准化
- 零外部依赖
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from exceptions import EternalAgentError


class QueryError(EternalAgentError):
    """查询异常"""
    pass


class QueryParseError(QueryError):
    """查询解析异常"""
    pass


@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    query: str = ""
    result_type: str = ""  # nodes, edges, paths, stats, count
    data: Any = None
    count: int = 0
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "query": self.query,
            "result_type": self.result_type,
            "count": self.count,
            "data": self.data,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
        }


class QueryEngine:
    """
    知识图谱查询引擎

    查询语法：
    - FIND nodes [WHERE type=ENTITY] [LIMIT 10]
    - FIND edges [WHERE weight>0.5]
    - FIND node "名称"
    - FIND path FROM "A" TO "B" [DEPTH 3]
    - COUNT nodes [WHERE type=TASK]
    - COUNT edges
    - STATS
    - SEARCH "关键词"
    """

    def __init__(self, knowledge_graph=None):
        self._kg = knowledge_graph

    def set_knowledge_graph(self, kg) -> None:
        """设置知识图谱"""
        self._kg = kg

    def execute(self, query: str) -> QueryResult:
        """
        执行查询

        Args:
            query: 查询字符串

        Returns:
            QueryResult
        """
        import time
        start = time.time()

        query = query.strip()
        if not query:
            return QueryResult(success=False, query=query, error="空查询")

        try:
            upper = query.upper()

            if upper.startswith("FIND"):
                result = self._execute_find(query)
            elif upper.startswith("COUNT"):
                result = self._execute_count(query)
            elif upper.startswith("STATS"):
                result = self._execute_stats()
            elif upper.startswith("SEARCH"):
                result = self._execute_search(query)
            else:
                result = QueryResult(success=False, query=query, error=f"未知查询类型: {query[:10]}")

        except Exception as e:
            result = QueryResult(success=False, query=query, error=str(e))

        result.query = query
        result.duration_ms = (time.time() - start) * 1000
        return result

    def _execute_find(self, query: str) -> QueryResult:
        """执行FIND查询"""
        if self._kg is None:
            return QueryResult(success=False, error="知识图谱未加载")

        upper = query.upper().strip()

        # FIND path FROM "A" TO "B"
        path_match = re.match(
            r'FIND\s+PATH\s+FROM\s+"([^"]+)"\s+TO\s+"([^"]+)"(?:\s+DEPTH\s+(\d+))?',
            query, re.IGNORECASE
        )
        if path_match:
            start_node = path_match.group(1)
            end_node = path_match.group(2)
            depth = int(path_match.group(3)) if path_match.group(3) else 5

            from visualization import KnowledgeVisualizer
            viz = KnowledgeVisualizer(self._kg)
            paths = viz.find_paths(start_node, end_node, depth)
            return QueryResult(
                success=True,
                result_type="paths",
                data=paths,
                count=len(paths),
            )

        # FIND node "名称"
        node_match = re.match(r'FIND\s+NODE\s+"([^"]+)"', query, re.IGNORECASE)
        if node_match:
            name = node_match.group(1)
            node = self._kg._nodes.get(name)
            if node:
                return QueryResult(
                    success=True,
                    result_type="nodes",
                    data=[{"name": node.name, "type": node.node_type, "valid": node.valid, "attributes": node.attributes}],
                    count=1,
                )
            return QueryResult(success=True, result_type="nodes", data=[], count=0)

        # FIND nodes [WHERE ...] [LIMIT n]
        if "NODES" in upper:
            where_clause = self._extract_where(query)
            limit = self._extract_limit(query, 50)

            nodes = list(self._kg._nodes.values())
            nodes = self._apply_where_nodes(nodes, where_clause)
            nodes = nodes[:limit]

            data = [
                {"name": n.name, "type": n.node_type, "valid": n.valid, "attributes": n.attributes}
                for n in nodes
            ]
            return QueryResult(success=True, result_type="nodes", data=data, count=len(data))

        # FIND edges [WHERE ...]
        if "EDGES" in upper:
            where_clause = self._extract_where(query)
            limit = self._extract_limit(query, 50)

            edges = list(self._kg._edges)
            edges = self._apply_where_edges(edges, where_clause)
            edges = edges[:limit]

            data = [
                {"source": e.source, "target": e.target, "relation": e.relation, "weight": round(e.weight, 3)}
                for e in edges
            ]
            return QueryResult(success=True, result_type="edges", data=data, count=len(data))

        # 默认：搜索所有
        return QueryResult(success=False, error="FIND语法错误，支持: FIND nodes/edges/node/path")

    def _execute_count(self, query: str) -> QueryResult:
        """执行COUNT查询"""
        if self._kg is None:
            return QueryResult(success=False, error="知识图谱未加载")

        upper = query.upper()

        if "NODES" in upper:
            where_clause = self._extract_where(query)
            nodes = list(self._kg._nodes.values())
            nodes = self._apply_where_nodes(nodes, where_clause)
            return QueryResult(success=True, result_type="count", data=len(nodes), count=len(nodes))

        elif "EDGES" in upper:
            return QueryResult(success=True, result_type="count", data=self._kg.edge_count, count=self._kg.edge_count)

        return QueryResult(success=False, error="COUNT语法错误，支持: COUNT nodes/edges")

    def _execute_stats(self) -> QueryResult:
        """执行STATS查询"""
        if self._kg is None:
            return QueryResult(success=False, error="知识图谱未加载")

        stats = self._kg.stats()

        # 额外统计
        type_counts = defaultdict(int)
        for node in self._kg._nodes.values():
            type_counts[node.node_type] += 1

        rel_counts = defaultdict(int)
        for edge in self._kg._edges:
            rel_counts[edge.relation] += 1

        stats["node_types"] = dict(type_counts)
        stats["relation_types"] = dict(rel_counts)

        return QueryResult(success=True, result_type="stats", data=stats, count=0)

    def _execute_search(self, query: str) -> QueryResult:
        """执行SEARCH查询"""
        if self._kg is None:
            return QueryResult(success=False, error="知识图谱未加载")

        match = re.match(r'SEARCH\s+"([^"]+)"', query, re.IGNORECASE)
        if not match:
            return QueryResult(success=False, error="SEARCH语法错误，用法: SEARCH \"关键词\"")

        keyword = match.group(1).lower()
        results = []

        for name, node in self._kg._nodes.items():
            if keyword in name.lower():
                results.append({"type": "node", "name": name, "node_type": node.node_type})
            else:
                for key, val in node.attributes.items():
                    if keyword in str(val).lower() or keyword in key.lower():
                        results.append({"type": "node", "name": name, "node_type": node.node_type})
                        break

        for edge in self._kg._edges:
            if keyword in edge.source.lower() or keyword in edge.target.lower() or keyword in edge.relation.lower():
                results.append({"type": "edge", "source": edge.source, "target": edge.target, "relation": edge.relation})

        return QueryResult(success=True, result_type="search", data=results, count=len(results))

    def _extract_where(self, query: str) -> List[Tuple[str, str, str]]:
        """提取WHERE子句"""
        match = re.search(r'WHERE\s+(.+?)(?:\s+LIMIT|\s*$)', query, re.IGNORECASE)
        if not match:
            return []

        conditions = []
        clause = match.group(1)
        for part in clause.split('AND'):
            part = part.strip()
            for op in [">=", "<=", "!=", "==", ">", "<", "="]:
                if op in part:
                    key, value = part.split(op, 1)
                    conditions.append((key.strip(), op, value.strip().strip('"')))
                    break
        return conditions

    def _extract_limit(self, query: str, default: int = 50) -> int:
        """提取LIMIT"""
        match = re.search(r'LIMIT\s+(\d+)', query, re.IGNORECASE)
        return int(match.group(1)) if match else default

    def _apply_where_nodes(self, nodes, conditions: List[Tuple[str, str, str]]) -> list:
        """应用WHERE条件到节点"""
        if not conditions:
            return nodes

        result = []
        for node in nodes:
            match = True
            for key, op, value in conditions:
                actual = self._get_node_field(node, key)
                if not self._compare(actual, op, value):
                    match = False
                    break
            if match:
                result.append(node)
        return result

    def _apply_where_edges(self, edges, conditions: list) -> list:
        """应用WHERE条件到边"""
        if not conditions:
            return edges

        result = []
        for edge in edges:
            match = True
            for key, op, value in conditions:
                actual = self._get_edge_field(edge, key)
                if not self._compare(actual, op, value):
                    match = False
                    break
            if match:
                result.append(edge)
        return result

    def _get_node_field(self, node, key: str):
        """获取节点字段值"""
        if key == "type" or key == "node_type":
            return node.node_type
        elif key == "name":
            return node.name
        elif key == "valid":
            return node.valid
        elif key in node.attributes:
            return node.attributes[key]
        return None

    def _get_edge_field(self, edge, key: str):
        """获取边字段值"""
        if key == "weight":
            return edge.weight
        elif key == "source":
            return edge.source
        elif key == "target":
            return edge.target
        elif key == "relation":
            return edge.relation
        return None

    def _compare(self, actual, op: str, expected: str) -> bool:
        """比较值"""
        try:
            if actual is None:
                return False
            if op in ("=", "=="):
                return str(actual).lower() == expected.lower()
            elif op == "!=":
                return str(actual).lower() != expected.lower()
            elif op == ">":
                return float(actual) > float(expected)
            elif op == "<":
                return float(actual) < float(expected)
            elif op == ">=":
                return float(actual) >= float(expected)
            elif op == "<=":
                return float(actual) <= float(expected)
        except (ValueError, TypeError):
            return False
        return False
