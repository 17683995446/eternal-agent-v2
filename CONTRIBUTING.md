# 贡献指南

感谢您对永动知识图谱Agent的关注！本文档将帮助您参与项目开发。

## 开发环境

### 环境要求

- Python 3.8+
- 无需安装任何外部依赖（纯标准库实现）

### 克隆项目

```bash
git clone <repository-url>
cd eternal_agent
```

### 运行测试

```bash
cd tests
python -m pytest test_*.py -v
```

## 代码规范

### 命名规范

- **类名**: PascalCase (如 `KnowledgeGraph`)
- **函数名**: snake_case (如 `add_node`)
- **常量**: UPPER_SNAKE_CASE (如 `MAX_QUEUE_SIZE`)
- **私有方法**: _前缀 (如 `_parse_module`)

### 文档字符串

所有公共类和方法必须包含文档字符串：

```python
def add_node(self, name: str, node_type: str) -> bool:
    """
    添加节点到知识图谱
    
    Args:
        name: 节点名称
        node_type: 节点类型
        
    Returns:
        是否添加成功
    """
```

### 代码质量

运行代码质量检查：

```bash
cd src
python code_quality.py
```

## 项目结构

```
eternal_agent/
├── src/          # 源代码 (每个文件一个模块)
├── tests/        # 测试代码
├── examples/     # 示例项目
├── docs/         # 文档
└── data/         # 运行时数据
```

## 三大核心公理

所有代码必须遵循三大核心公理：

1. **存续公理 (Alive)** - 系统永不终止
2. **记忆公理 (Memory)** - 知识图谱是唯一记忆
3. **自驱公理 (Self-Drive)** - 从知识自动衍生任务

## 提交规范

### 提交信息格式

```
<type>(<scope>): <subject>

<body>
```

类型：
- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `refactor`: 重构
- `test`: 测试
- `chore`: 杂项

### 示例

```
feat(knowledge_graph): 添加节点属性搜索功能

实现了基于属性的节点搜索，支持模糊匹配。
```

## 添加新模块

1. 在 `src/` 下创建新文件
2. 添加模块文档字符串
3. 在 `tests/` 下创建对应测试
4. 运行所有测试确保通过
5. 更新 `CHANGELOG.md`

## 零外部依赖原则

本项目严格遵循零外部依赖原则。所有功能必须使用Python标准库实现。

如需添加新功能，请优先考虑标准库方案。

## 问题反馈

请通过 GitHub Issues 提交问题和建议。
