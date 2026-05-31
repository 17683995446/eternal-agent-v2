# 永动知识图谱Agent

> 基于第一性原理 · 轻量化永动知识图谱Agent

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-passing-brightgreen.svg)]()

## 三大核心公理

1. **存续公理 (Alive)** - 系统永不终止，具备自修复能力
2. **记忆公理 (Memory)** - 知识图谱是唯一长期记忆载体
3. **自驱公理 (Self-Drive)** - 从知识自动衍生任务

## 特性

- **零外部依赖** - 纯Python标准库实现
- **永动循环** - 永不停止的任务处理引擎
- **知识图谱** - 结构化的长期记忆存储
- **推理引擎** - 从知识中推导新洞察
- **插件系统** - 可扩展的模块化架构
- **生产就绪** - 完整的监控、安全和运维功能

## 快速开始

### 安装

无需安装，直接克隆即可使用：

```bash
git clone <repository-url>
cd eternal_agent/src
```

### 基础用法

#### 1. 创建知识图谱

```python
from knowledge_graph import KnowledgeGraph

# 创建知识图谱
kg = KnowledgeGraph()

# 添加节点
kg.add_node("Python", "language")
kg.add_node("FastAPI", "framework")

# 添加关系
kg.add_edge("Python", "FastAPI", "powers", 0.95)

# 保存
kg.save()
```

#### 2. 启动永动循环

```python
from eternal_agent import EternalSelfAgent

# 创建智能体
agent = EternalSelfAgent()

# 定义任务处理器
def my_handler(task):
    print(f"处理任务: {task.name}")
    return True

# 注册处理器
agent.register_task_handler("demo", my_handler)

# 提交任务
agent.submit_task(name="示例任务", task_type="demo")

# 启动（持续运行）
agent.start()
```

#### 3. 使用查询语言

```python
from query_language import QueryEngine
from knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph()
engine = QueryEngine(kg)

# 查询节点
result = engine.execute("FIND nodes WHERE type = 'language'")
print(result.data)

# 统计
result = engine.execute("COUNT edges")
print(f"边数: {result.data}")
```

## 项目结构

```
eternal_agent/
├── src/                    # 源代码
│   ├── constants.py        # 常量定义
│   ├── logger.py           # 日志系统
│   ├── config.py           # 配置管理
│   ├── models.py           # 数据模型
│   ├── utils.py            # 工具函数
│   ├── exceptions.py       # 异常定义
│   ├── monitor.py          # 监控指标
│   ├── task_queue.py       # 任务队列
│   ├── loop.py             # 永动循环
│   ├── knowledge_graph.py  # 知识图谱
│   ├── eternal_agent.py    # 智能体核心
│   ├── reasoning.py        # 推理引擎
│   ├── api.py              # API服务
│   ├── cli.py              # 命令行接口
│   ├── plugin_system.py    # 插件系统
│   ├── event_bus.py        # 事件总线
│   ├── scheduler.py        # 任务调度
│   ├── boot.py             # 系统启动器
│   ├── visualization.py    # 可视化
│   ├── query_language.py   # 查询语言
│   ├── benchmark.py        # 性能测试
│   ├── upgrader.py         # 版本升级
│   ├── coordinator.py      # 分布式协调
│   ├── doc_generator.py    # 文档生成
│   └── tutorials.py        # 交互式教程
├── tests/                  # 测试代码
├── examples/               # 示例项目
│   ├── example_01_knowledge_base.py
│   ├── example_02_qa_system.py
│   └── example_03_task_automation.py
├── docs/                   # 文档
│   ├── API.md              # API参考文档
│   └── DEPLOY.md           # 部署文档
└── README.md               # 本文件
```

## 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                    集成层 (Integration)                      │
│     Boot │ Visualization │ Query │ Benchmark │ Upgrader      │
├─────────────────────────────────────────────────────────────┤
│                    生产层 (Production)                       │
│  Config │ Secrets │ Access │ Audit │ Encryption │ Backup     │
├─────────────────────────────────────────────────────────────┤
│                    生态层 (Ecosystem)                        │
│  Plugin │ EventBus │ Watcher │ Scheduler │ HTTP │ Pipeline  │
├─────────────────────────────────────────────────────────────┤
│                    交互层 (Interaction)                      │
│                    API │ CLI │ Protocol                      │
├─────────────────────────────────────────────────────────────┤
│                    推理层 (Reasoning)                        │
│        Rules │ Patterns │ Causal │ Similarity │ Inference   │
├─────────────────────────────────────────────────────────────┤
│                    自驱层 (Self-Drive)                       │
│                    EternalAgent (智能体核心)                  │
├─────────────────────────────────────────────────────────────┤
│                    记忆层 (Memory)                           │
│                    KnowledgeGraph (知识图谱)                  │
├─────────────────────────────────────────────────────────────┤
│                    存续层 (Survival)                         │
│                    TaskQueue │ EternalLoop                   │
├─────────────────────────────────────────────────────────────┤
│                    基础层 (Base)                             │
│  Constants │ Logger │ Config │ Models │ Utils │ Exceptions   │
└─────────────────────────────────────────────────────────────┘
```

## 示例项目

### 示例1: 基础知识图谱管理

```bash
cd examples
python example_01_knowledge_base.py
```

展示如何创建和管理知识图谱，包括添加节点、关系、查询和可视化。

### 示例2: 智能问答系统

```bash
python example_02_qa_system.py
```

展示如何构建基于知识图谱的问答系统，包括推理和模式匹配。

### 示例3: 任务自动化工作流

```bash
python example_03_task_automation.py
```

展示如何使用永动循环和任务队列实现自动化工作流。

## 交互式教程

运行交互式教程学习系统使用：

```bash
cd src
python tutorials.py
```

## 文档

- [API参考文档](docs/API.md) - 完整的API文档
- [部署文档](docs/DEPLOY.md) - 部署指南

## 运行测试

```bash
cd tests
python -m pytest test_*.py -v
```

## 核心概念

### 节点 (Node)

知识图谱中的实体，代表一个概念、任务或经验。

```python
node = Node(
    name="Python",
    node_type="language",
    attributes={"description": "一种编程语言"}
)
```

### 边 (Edge)

连接节点的关系，权重表示关联强度。

```python
edge = Edge(
    source="Python",
    target="FastAPI",
    relation="powers",
    weight=0.95
)
```

### 任务 (Task)

待处理的工作单元。

```python
task = Task(
    name="处理数据",
    task_type="data_processing",
    payload={"data": [1, 2, 3]},
    priority=5
)
```

## 配置

系统通过 `config.py` 管理配置，支持：

- 环境变量覆盖
- 配置文件加载
- 运行时动态修改

```python
from config import Config

config = Config()
config.set("log_level", "DEBUG")
```

## 监控

内置监控指标：

```python
from monitor import monitor

monitor.record("tasks_processed", 1)
print(monitor.report())
```

## 插件开发

创建自定义插件：

```python
from plugin_system import PluginBase, PluginManager

class MyPlugin(PluginBase):
    name = "my_plugin"
    version = "1.0.0"
    
    def activate(self):
        self.register_hook("agent_start", self.on_start)
    
    def on_start(self, agent):
        print(f"Agent {agent} 已启动")
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 致谢

遵循"大事做于细，难事成于易"原则，从零构建。
