# 变更日志

本项目的所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

## [1.0.0] - 2026-05-24

### 新增

#### 基础层 (Stages 1-10)
- `constants.py` - 全局常量定义
- `logger.py` - 日志系统
- `config.py` - 配置管理
- `models.py` - 数据模型 (Node, Edge, Task)
- `utils.py` - 工具函数集
- `exceptions.py` - 异常定义
- `monitor.py` - 监控指标

#### 存续层 (Stages 11-20)
- `task_queue.py` - FIFO任务队列 (最大200任务)
- `loop.py` - 永动循环 (异常自修复)

#### 记忆层 (Stages 21-35)
- `knowledge_graph.py` - 知识图谱 (CRUD, 持久化, 任务衍生)

#### 自驱层 (Stages 36-50)
- `eternal_agent.py` - 智能体核心 (EternalSelfAgent)

#### 推理层 (Stages 61-70)
- `reasoning.py` - 推理引擎 (规则, 模式匹配, 因果追踪)

#### 交互层 (Stages 71-80)
- `api.py` - HTTP API服务
- `cli.py` - 命令行接口
- `interaction.py` - 交互协议

#### 生态层 (Stages 81-90)
- `plugin_system.py` - 插件系统
- `event_bus.py` - 事件总线
- `file_watcher.py` - 文件监控
- `scheduler.py` - 任务调度
- `http_client.py` - HTTP客户端
- `data_pipeline.py` - 数据管道
- `template_engine.py` - 模板引擎
- `persistence_v2.py` - 增量持久化
- `sandbox.py` - 沙箱执行

#### 生产层 (Stages 91-100)
- `config_center.py` - 配置中心
- `secret_store.py` - 密钥存储
- `access_control.py` - 访问控制 (RBAC)
- `audit_log.py` - 审计日志
- `encryption.py` - 加密模块
- `backup.py` - 备份管理
- `health.py` - 健康检查
- `profiler.py` - 性能分析
- `diagnostics.py` - 诊断工具

#### 集成层 (Stages 101-110)
- `boot.py` - 系统启动器
- `visualization.py` - 可视化 (Mermaid/ASCII/JSON/HTML)
- `query_language.py` - 查询语言
- `benchmark.py` - 性能基准测试
- `upgrader.py` - 版本升级
- `coordinator.py` - 分布式协调

#### 文档与示例层 (Stages 111-120)
- `doc_generator.py` - 文档生成器
- `tutorials.py` - 交互式教程
- 3个示例项目 (知识图谱/问答/自动化)

#### 智能增强层 (Stages 121-130)
- `nlp_processor.py` - NLP处理器 (分词/关键词/语言检测)
- `entity_recognizer.py` - 实体识别器
- `similarity.py` - 相似度计算器
- `adaptive_learner.py` - 自适应学习器
- `knowledge_recommender.py` - 知识推荐器
- `intent_recognizer.py` - 意图识别器
- `dialog_manager.py` - 对话管理器
- `summarizer.py` - 智能摘要器

#### 部署与运维层 (Stages 131-140)
- `Dockerfile` + `docker-compose.yml` - 容器化
- `deploy.py` - 自动化部署
- `monitoring.py` - Prometheus监控
- `alerter.py` - 告警系统

#### 项目收尾层 (Stages 141-150)
- `perf_optimizer.py` - 性能优化 (LRU缓存/对象池/批量处理)
- `code_quality.py` - 代码质量检查

### 设计原则

- **零外部依赖** - 纯Python标准库实现
- **三大公理** - 存续(Alive)、记忆(Memory)、自驱(Self-Drive)
- **分层架构** - 13个架构层级，从基础到高级
