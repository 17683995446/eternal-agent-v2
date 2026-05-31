"""
命令行交互界面

公理溯源：存续公理 — 系统可观测、可控制

设计意图：
- 零外部依赖，仅使用 argparse
- 支持查看状态、操作知识图谱、管理任务
- 支持独立运行和交互模式
"""

import argparse
import json
import sys
from pathlib import Path

from logger import get_logger

logger = get_logger("CLI")


def create_parser():
    """创建命令行解析器"""
    parser = argparse.ArgumentParser(
        prog="eternal-agent",
        description="永恒自驱智能体系统",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # run: 启动系统
    run_parser = subparsers.add_parser("run", help="启动系统")
    run_parser.add_argument("--port", type=int, default=8080, help="HTTP API端口")
    run_parser.add_argument("--no-http", action="store_true", help="不启动HTTP API")

    # status: 查看状态
    status_parser = subparsers.add_parser("status", help="查看系统状态")
    status_parser.add_argument("--json", action="store_true", help="JSON格式输出")

    # kg: 知识图谱操作
    kg_parser = subparsers.add_parser("kg", help="知识图谱操作")
    kg_sub = kg_parser.add_subparsers(dest="kg_command")

    kg_stats = kg_sub.add_parser("stats", help="图谱统计")
    kg_nodes = kg_sub.add_parser("nodes", help="列出节点")
    kg_nodes.add_argument("--type", type=str, help="按类型过滤")
    kg_edges = kg_sub.add_parser("edges", help="列出边")
    kg_export = kg_sub.add_parser("export", help="导出可视化")
    kg_export.add_argument("--format", choices=["mermaid", "graphviz"], default="mermaid")
    kg_snapshot = kg_sub.add_parser("snapshot", help="创建快照")
    kg_snapshot.add_argument("--label", type=str, default="", help="快照标签")
    kg_health = kg_sub.add_parser("health", help="健康检查")

    # task: 任务操作
    task_parser = subparsers.add_parser("task", help="任务操作")
    task_sub = task_parser.add_subparsers(dest="task_command")

    task_add = task_sub.add_parser("add", help="添加任务")
    task_add.add_argument("name", type=str, help="任务名称")
    task_add.add_argument("--priority", type=int, default=0, help="优先级")
    task_add.add_argument("--tag", type=str, default="", help="标签")

    task_list = task_sub.add_parser("list", help="列出任务")

    # test: 运行测试
    test_parser = subparsers.add_parser("test", help="运行测试")
    test_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    return parser


def run_status(args, agent=None):
    """执行status命令"""
    if agent:
        status = agent.get_status()
        if args.json:
            print(json.dumps(status.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(f"状态: {status.state}")
            print(f"运行次数: {status.run_counter}")
            print(f"完成任务: {status.total_tasks_completed}")
            print(f"失败任务: {status.total_tasks_failed}")
            print(f"连续错误: {status.consecutive_errors}")
    else:
        print("系统未运行")


def _kg_stats(kg, args):
    """显示知识图谱统计"""
    stats = kg.stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))


def _kg_nodes(kg, args):
    """显示知识图谱节点"""
    nodes = kg.get_all_nodes()
    if args.type:
        nodes = [n for n in nodes if n.node_type == args.type]
    for node in nodes:
        print(f"  [{node.node_type}] {node.name} (valid={node.valid})")


def _kg_edges(kg, args):
    """显示知识图谱边"""
    edges = kg.get_all_edges()
    for edge in edges:
        print(f"  {edge.source} -[{edge.relation}:{edge.weight:.2f}]-> {edge.target}")


def _kg_export(kg, args):
    """导出知识图谱"""
    if args.format == "mermaid":
        print(kg.export_mermaid())
    else:
        print(kg.export_graphviz())


def _kg_snapshot(kg, args):
    """创建知识图谱快照"""
    path = kg.create_snapshot(args.label)
    print(f"快照已创建: {path}")


def _kg_health(kg, args):
    """显示知识图谱健康状态"""
    health = kg.health_check()
    print(json.dumps(health, indent=2, ensure_ascii=False))


KG_COMMANDS = {
    "stats": _kg_stats,
    "nodes": _kg_nodes,
    "edges": _kg_edges,
    "export": _kg_export,
    "snapshot": _kg_snapshot,
    "health": _kg_health,
}


def run_kg(args, agent=None):
    """执行kg命令"""
    if not agent:
        print("系统未运行")
        return

    kg = agent.knowledge_graph
    cmd = args.kg_command
    
    if cmd in KG_COMMANDS:
        KG_COMMANDS[cmd](kg, args)
    else:
        print("请指定kg子命令: stats/nodes/edges/export/snapshot/health")


def run_task(args, agent=None):
    """执行task命令"""
    if not agent:
        print("系统未运行")
        return

    if args.task_command == "add":
        agent.task_queue.add(args.name, priority=args.priority)
        print(f"任务已添加: {args.name} (优先级: {args.priority})")

    elif args.task_command == "list":
        names = agent.task_queue.get_all_names()
        stats = agent.task_queue.stats()
        print(f"队列: {stats['size']}/{stats['max_size']}")
        for name in names:
            print(f"  - {name}")

    else:
        print("请指定task子命令: add/list")


def run_tests(args):
    """执行测试"""
    import subprocess
    cmd = [sys.executable, "-m", "pytest", "tests/"]
    if args.verbose:
        cmd.append("-v")
    subprocess.run(cmd)


def main(argv=None):
    """CLI主入口"""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command == "status":
        run_status(args)
    elif args.command == "kg":
        run_kg(args)
    elif args.command == "task":
        run_task(args)
    elif args.command == "test":
        run_tests(args)
    elif args.command == "run":
        from eternal_agent import EternalSelfAgent
        agent = EternalSelfAgent()
        agent.initialize()

        if not args.no_http:
            from api import APIServer
            api = APIServer(agent, port=args.port)
            api.start()
            print(f"HTTP API: http://127.0.0.1:{args.port}")

        agent.run()
    else:
        parser.print_help()
