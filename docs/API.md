# Eternal Agent API 文档

## 核心类

### EternalSelfAgent

永恒自驱智能体主体类，整合四层架构。

```python
from eternal_agent import EternalSelfAgent

# 创建智能体
agent = EternalSelfAgent()

# 初始化
agent.initialize()

# 启动永恒主循环（阻塞）
agent.run()

# 停止系统
agent.stop()

# 获取状态
status = agent.get_status()

# 获取知识图谱统计
stats = agent.get_kg_stats()

# 导出可视化
mermaid = agent.export_kg_visualization("mermaid")
dot = agent.export_kg_visualization("graphviz")
```

### KnowledgeGraph

知识图谱，系统唯一长期记忆载体。

```python
from knowledge_graph import KnowledgeGraph

# 创建图谱（自动加载已有数据）
kg = KnowledgeGraph()

# 或使用自定义路径
kg = KnowledgeGraph(save_path="/path/to/kg.json")

# 添加节点
node = kg.add_node("node_name", node_type="task")

# 添加边（自动创建端点节点）
edge = kg.add_edge("source", "target", relation="衍生", weight=0.8)

# 查询节点
node = kg.get_node("node_name")
exists = kg.has_node("node_name")

# 查询边
edges = kg.get_edges_from("source")
edges = kg.get_edges_to("target")

# 知识推演（基于高权重边生成新任务）
tasks = kg.derive_new_tasks("node_name", threshold=0.2)

# 知识精简（删除低权重边）
removed = kg.trim_invalid_knowledge(threshold=0.1)

# 统计
stats = kg.stats()

# 导出可视化
mermaid = kg.export_mermaid()
dot = kg.export_graphviz()

# 健康检查
health = kg.health_check()
fixed = kg.repair()
```

### TaskQueue

任务队列，系统唯一驱动源。

```python
from task_queue import TaskQueue

# 创建队列
queue = TaskQueue(max_size=200)

# 添加任务
queue.add("task_name", priority=5)

# 批量添加（自动去重）
queue.batch_add(["task1", "task2"], priority=3)

# 获取任务（不出队）
task = queue.get()

# 弹出任务
task = queue.pop()

# 查询
is_empty = queue.is_empty()
size = queue.size()
contains = queue.contains("task_name")

# 统计
stats = queue.stats()
```

### EternalLoop

永恒主循环，存续保活层核心。

```python
from loop import EternalLoop
from task_queue import TaskQueue

queue = TaskQueue()
loop = EternalLoop(queue)

# 注册回调
def handle_task(task):
    return "result"

loop.on_task(handle_task)

def idle_handler():
    pass

loop.on_idle(idle_handler)

def evolve_handler():
    pass

loop.on_evolve(evolve_handler)

def shutdown_handler():
    pass

loop.on_shutdown(shutdown_handler)

# 启动循环（阻塞，永不返回）
loop.run()

# 停止循环
loop.stop()

# 获取状态
status = loop.get_status()
```

## 数据模型

### Node

知识图谱节点。

```python
from models import Node

node = Node(
    name="node_name",
    node_type="task",  # task/entity/concept/knowledge
    attributes={"key": "value"}
)

# 序列化
data = node.to_dict()

# 反序列化
node = Node.from_dict(data)
```

### Edge

知识图谱边。

```python
from models import Edge

edge = Edge(
    source="source_node",
    target="target_node",
    relation="衍生",  # 自主衍生/关联/依赖/进化自
    weight=0.8  # 0.0-1.0
)

# 更新权重
edge.update_weight(0.1)  # 增加0.1
edge.update_weight(-0.1)  # 减少0.1

# 序列化
data = edge.to_dict()

# 反序列化
edge = Edge.from_dict(data)
```

### Task

任务。

```python
from models import Task

task = Task(
    name="task_name",
    priority=5  # 数值越大优先级越高
)

# 生命周期
task.start()
task.complete("result")
task.fail("error")

# 序列化
data = task.to_dict()

# 反序列化
task = Task.from_dict(data)
```

## 常量

```python
from constants import (
    LOOP_DELAY,              # 主循环节拍（0.3秒）
    EVOLVE_STEP,             # 进化触发步数（50步）
    TASK_QUEUE_MAX,          # 任务队列上限（200）
    KNOWLEDGE_TRIM_THRESHOLD, # 知识淘汰阈值（0.1）
    TASK_DERIVE_WEIGHT_THRESHOLD,  # 任务推演阈值（0.2）
    SystemState,             # 系统状态枚举
    TaskState,               # 任务状态枚举
    NodeType,                # 节点类型枚举
    RelationType,            # 关系类型枚举
)
```

## 异常

```python
from exceptions import (
    EternalAgentError,       # 基础异常
    SurvivalError,           # 存续层异常
    KnowledgeMemoryError,    # 记忆层异常基类（原MemoryError，已重命名避免冲突）
    KnowledgeGraphError,     # 知识图谱异常
    SelfDriveError,          # 自驱层异常
)
```
