"""
示例3: 任务自动化工作流

本示例展示如何使用永动循环和任务队列实现自动化工作流：
- 创建和管理任务队列
- 定义任务处理器
- 使用永动循环持续处理任务
- 任务优先级和重试机制

大事做于细，难事成于易：
- 从简单任务开始，逐步构建复杂工作流
- 每个任务都有明确的状态和结果
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from task_queue import TaskQueue, Task, TaskState
from loop import EternalLoop
from eternal_agent import EternalSelfAgent as EternalAgent
from knowledge_graph import KnowledgeGraph
from logger import get_logger

logger = get_logger("Example03")


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    message: str
    data: Any = None
    duration: float = 0.0


class TaskHandlers:
    """任务处理器集合"""
    
    def __init__(self):
        self.results: List[TaskResult] = []
    
    def handle_data_processing(self, task: Task) -> bool:
        """数据处理任务"""
        print(f"  [处理器] 执行数据处理: {task.name}")
        
        # 模拟数据处理
        data = task.payload.get("data", [])
        operation = task.payload.get("operation", "sum")
        
        start_time = time.time()
        
        if operation == "sum":
            result = sum(data)
            message = f"数据求和完成: {result}"
        elif operation == "average":
            result = sum(data) / len(data) if data else 0
            message = f"数据平均完成: {result:.2f}"
        elif operation == "count":
            result = len(data)
            message = f"数据计数完成: {result}"
        else:
            result = None
            message = f"未知操作: {operation}"
        
        duration = time.time() - start_time
        
        self.results.append(TaskResult(
            success=True,
            message=message,
            data=result,
            duration=duration
        ))
        
        print(f"    ✓ {message} (耗时: {duration:.3f}s)")
        return True
    
    def handle_file_operation(self, task: Task) -> bool:
        """文件操作任务"""
        print(f"  [处理器] 执行文件操作: {task.name}")
        
        operation = task.payload.get("operation", "read")
        filepath = task.payload.get("path", "")
        content = task.payload.get("content", "")
        
        start_time = time.time()
        
        try:
            if operation == "write":
                Path(filepath).write_text(content, encoding='utf-8')
                message = f"文件写入完成: {filepath}"
            elif operation == "read":
                if Path(filepath).exists():
                    data = Path(filepath).read_text(encoding='utf-8')
                    message = f"文件读取完成: {filepath} ({len(data)} 字符)"
                else:
                    message = f"文件不存在: {filepath}"
            elif operation == "delete":
                if Path(filepath).exists():
                    Path(filepath).unlink()
                    message = f"文件删除完成: {filepath}"
                else:
                    message = f"文件不存在: {filepath}"
            else:
                message = f"未知操作: {operation}"
            
            success = True
        except Exception as e:
            message = f"文件操作失败: {e}"
            success = False
        
        duration = time.time() - start_time
        
        self.results.append(TaskResult(
            success=success,
            message=message,
            duration=duration
        ))
        
        status = "✓" if success else "✗"
        print(f"    {status} {message} (耗时: {duration:.3f}s)")
        return success
    
    def handle_knowledge_update(self, task: Task) -> bool:
        """知识图谱更新任务"""
        print(f"  [处理器] 执行知识更新: {task.name}")
        
        kg = KnowledgeGraph()
        operation = task.payload.get("operation", "add_node")
        
        start_time = time.time()
        
        try:
            if operation == "add_node":
                name = task.payload.get("name", "")
                node_type = task.payload.get("type", "entity")
                kg.add_node(name, node_type)
                message = f"添加节点: {name}"
                
            elif operation == "add_edge":
                source = task.payload.get("source", "")
                target = task.payload.get("target", "")
                relation = task.payload.get("relation", "relates_to")
                weight = task.payload.get("weight", 0.5)
                kg.add_edge(source, target, relation, weight)
                message = f"添加关系: {source} -> {target}"
                
            elif operation == "query":
                query_type = task.payload.get("query_type", "nodes")
                if query_type == "nodes":
                    nodes = kg.get_all_nodes()
                    message = f"查询到 {len(nodes)} 个节点"
                else:
                    message = f"查询类型: {query_type}"
            else:
                message = f"未知操作: {operation}"
            
            kg.save()
            success = True
            
        except Exception as e:
            message = f"知识更新失败: {e}"
            success = False
        
        duration = time.time() - start_time
        
        self.results.append(TaskResult(
            success=success,
            message=message,
            duration=duration
        ))
        
        status = "✓" if success else "✗"
        print(f"    {status} {message} (耗时: {duration:.3f}s)")
        return success
    
    def handle_notification(self, task: Task) -> bool:
        """通知任务"""
        print(f"  [处理器] 发送通知: {task.name}")
        
        channel = task.payload.get("channel", "console")
        message = task.payload.get("message", "")
        
        start_time = time.time()
        
        if channel == "console":
            print(f"    [通知] {message}")
        elif channel == "log":
            logger.info(message)
        
        duration = time.time() - start_time
        
        self.results.append(TaskResult(
            success=True,
            message=f"通知已发送: {message}",
            duration=duration
        ))
        
        print(f"    ✓ 通知完成 (耗时: {duration:.3f}s)")
        return True


def example_basic_task_queue():
    """示例：基础任务队列"""
    print("\n" + "="*60)
    print("示例 3.1: 基础任务队列")
    print("="*60)
    
    # 创建任务队列
    queue = TaskQueue()
    handlers = TaskHandlers()
    
    # 注册任务处理器
    queue.register_handler("data_processing", handlers.handle_data_processing)
    queue.register_handler("file_operation", handlers.handle_file_operation)
    queue.register_handler("knowledge_update", handlers.handle_knowledge_update)
    
    # 添加任务
    print("\n[1] 添加任务到队列...")
    
    tasks = [
        Task(name="计算数据总和", task_type="data_processing", 
             payload={"data": [1, 2, 3, 4, 5], "operation": "sum"}),
        Task(name="计算数据平均", task_type="data_processing",
             payload={"data": [10, 20, 30, 40, 50], "operation": "average"}),
        Task(name="添加知识节点", task_type="knowledge_update",
             payload={"operation": "add_node", "name": "TaskAutomation", "type": "concept"}),
        Task(name="发送通知", task_type="notification",
             payload={"channel": "console", "message": "任务队列初始化完成"}),
    ]
    
    for task in tasks:
        queue.enqueue(task)
        print(f"  ✓ 添加任务: {task.name}")
    
    print(f"\n[2] 队列中有 {queue.size()} 个任务")
    
    # 处理任务
    print("\n[3] 处理任务...")
    processed = 0
    while queue.size() > 0:
        task = queue.pop()
        if task:
            handler = queue.get_handler(task.task_type)
            if handler:
                success = handler(task)
                processed += 1
            else:
                print(f"    ! 未找到处理器: {task.task_type}")
    
    print(f"\n[4] 处理完成: {processed} 个任务")
    print(f"    成功: {len([r for r in handlers.results if r.success])}")
    print(f"    失败: {len([r for r in handlers.results if not r.success])}")


def example_eternal_loop():
    """示例：永动循环"""
    print("\n" + "="*60)
    print("示例 3.2: 永动循环演示")
    print("="*60)
    
    queue = TaskQueue()
    handlers = TaskHandlers()
    
    # 注册处理器
    queue.register_handler("data_processing", handlers.handle_data_processing)
    queue.register_handler("notification", handlers.handle_notification)
    
    # 创建永动循环
    loop = EternalLoop(queue)
    
    # 添加一些任务
    print("\n[1] 添加示例任务...")
    for i in range(3):
        task = Task(
            name=f"自动任务-{i+1}",
            task_type="data_processing",
            payload={"data": list(range(i+2)), "operation": "sum"}
        )
        queue.enqueue(task)
        print(f"  ✓ 添加: {task.name}")
    
    # 设置回调
    def on_task(task: Task):
        print(f"  [回调] 开始处理: {task.name}")
    
    def on_idle():
        print("  [回调] 队列空闲，添加新任务...")
        # 添加一个新任务
        task = Task(
            name=f"动态任务-{datetime.now().strftime('%H%M%S')}",
            task_type="notification",
            payload={"channel": "console", "message": "这是动态添加的任务"}
        )
        queue.enqueue(task)
    
    # 运行循环（限制迭代次数用于演示）
    print("\n[2] 启动永动循环（演示模式，处理5个任务后停止）...")
    
    task_count = [0]
    
    def limited_task_handler(task: Task):
        task_count[0] += 1
        if task_count[0] > 5:
            loop.stop()
            return False
        
        handler = queue.get_handler(task.task_type)
        if handler:
            return handler(task)
        return False
    
    try:
        loop._on_task_callback = limited_task_handler
        loop._on_idle_callback = on_idle
        loop.run()
    except KeyboardInterrupt:
        print("\n  收到中断信号，停止循环")
    
    print(f"\n[3] 循环结束，共处理 {task_count[0]} 个任务")


def example_eternal_agent():
    """示例：完整智能体"""
    print("\n" + "="*60)
    print("示例 3.3: 完整智能体演示")
    print("="*60)
    
    # 创建智能体
    agent = EternalAgent()
    handlers = TaskHandlers()
    
    # 注册任务处理器
    agent.register_task_handler("data_processing", handlers.handle_data_processing)
    agent.register_task_handler("knowledge_update", handlers.handle_knowledge_update)
    agent.register_task_handler("notification", handlers.handle_notification)
    
    # 添加初始任务
    print("\n[1] 添加初始任务...")
    agent.submit_task(
        name="初始化知识图谱",
        task_type="knowledge_update",
        payload={"operation": "add_node", "name": "AutomationSystem", "type": "system"}
    )
    
    agent.submit_task(
        name="数据分析任务",
        task_type="data_processing",
        payload={"data": [100, 200, 300, 400, 500], "operation": "average"}
    )
    
    agent.submit_task(
        name="系统启动通知",
        task_type="notification",
        payload={"channel": "console", "message": "智能体系统已启动"}
    )
    
    print(f"  ✓ 已添加 {agent.queue.size()} 个任务")
    
    # 处理所有任务（非持续模式）
    print("\n[2] 处理任务...")
    processed = 0
    max_iterations = 10
    
    while agent.queue.size() > 0 and processed < max_iterations:
        task = agent.queue.pop()
        if task:
            handler = agent.queue.get_handler(task.task_type)
            if handler:
                success = handler(task)
                processed += 1
    
    print(f"\n[3] 处理完成: {processed} 个任务")
    
    # 显示知识图谱状态
    print("\n[4] 知识图谱状态:")
    stats = agent.knowledge_graph.stats()
    print(f"    节点数: {stats['node_count']}")
    print(f"    边数: {stats['edge_count']}")


def example_priority_and_retry():
    """示例：优先级和重试"""
    print("\n" + "="*60)
    print("示例 3.4: 任务优先级和重试")
    print("="*60)
    
    queue = TaskQueue()
    
    # 添加不同优先级的任务
    print("\n[1] 添加不同优先级的任务...")
    
    tasks = [
        Task(name="低优先级任务", task_type="test", priority=1),
        Task(name="高优先级任务", task_type="test", priority=10),
        Task(name="中优先级任务", task_type="test", priority=5),
        Task(name="紧急任务", task_type="test", priority=20),
    ]
    
    for task in tasks:
        queue.enqueue(task)
        print(f"  ✓ 添加: {task.name} (优先级: {task.priority})")
    
    # 查看队列状态
    print(f"\n[2] 队列状态:")
    print(f"    总任务数: {queue.size()}")
    
    # 处理任务（应该按优先级顺序）
    print("\n[3] 处理任务（按优先级）...")
    processed = []
    while queue.size() > 0:
        task = queue.pop()
        if task:
            processed.append(task.name)
    
    print(f"    处理顺序: {' -> '.join(processed)}")
    
    # 演示重试机制
    print("\n[4] 重试机制演示...")
    
    retry_count = [0]
    
    def flaky_handler(task: Task) -> bool:
        """有时失败的处理器"""
        retry_count[0] += 1
        if retry_count[0] < 3:
            print(f"    尝试 {retry_count[0]}: 失败，准备重试...")
            return False
        print(f"    尝试 {retry_count[0]}: 成功！")
        return True
    
    queue.register_handler("flaky", flaky_handler)
    
    task = Task(name="不稳定任务", task_type="flaky", max_retries=3)
    queue.enqueue(task)
    
    # 模拟重试
    attempts = 0
    while attempts < 5:
        task = queue.pop()
        if not task:
            break
        
        handler = queue.get_handler(task.task_type)
        success = handler(task)
        
        if success:
            break
        else:
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                queue.enqueue(task)  # 重新入队
                print(f"    任务重新入队 (重试 {task.retry_count}/{task.max_retries})")
            else:
                print(f"    任务失败: 达到最大重试次数")
                break
        
        attempts += 1


def main():
    """主函数"""
    print("\n" + "="*60)
    print("永动知识图谱Agent - 示例3: 任务自动化工作流")
    print("="*60)
    
    try:
        example_basic_task_queue()
        example_eternal_loop()
        example_eternal_agent()
        example_priority_and_retry()
        
        print("\n" + "="*60)
        print("所有示例运行完成！")
        print("="*60)
        print("\n提示:")
        print("- 任务队列支持优先级和重试机制")
        print("- 永动循环可以持续处理任务")
        print("- 可以注册自定义任务处理器")
        print("- 任务执行结果会被记录到知识图谱")
        
    except Exception as e:
        logger.error(f"示例运行失败: {e}")
        raise


if __name__ == "__main__":
    main()
