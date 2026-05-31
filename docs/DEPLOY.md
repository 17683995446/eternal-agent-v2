# Eternal Agent 部署文档

## 系统要求

- Python 3.8+
- 内存：最低 128MB，推荐 512MB
- 磁盘：最低 100MB 可用空间
- 操作系统：Linux/macOS/Windows

## 安装

### 1. 克隆仓库

```bash
git clone <repository-url>
cd eternal_agent
```

### 2. 安装依赖

```bash
# 无外部依赖，仅需Python标准库
# 可选安装psutil用于资源监控
pip install psutil
```

### 3. 目录结构

```
eternal_agent/
├── src/           # 源代码
├── tests/         # 测试
├── docs/          # 文档
├── data/          # 数据存储（自动创建）
│   ├── knowledge_graph.json  # 知识图谱
│   ├── config.json           # 配置
│   └── logs/                 # 日志
└── README.md
```

## 启动

### 开发模式

```bash
cd eternal_agent
python src/main.py
```

### 后台运行（Linux）

```bash
nohup python src/main.py > output.log 2>&1 &
echo $! > eternal_agent.pid
```

### 使用 systemd（Linux）

创建 `/etc/systemd/system/eternal-agent.service`：

```ini
[Unit]
Description=Eternal Self-Driving Agent
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/eternal_agent
ExecStart=/usr/bin/python3 src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用并启动：

```bash
sudo systemctl enable eternal-agent
sudo systemctl start eternal-agent
sudo systemctl status eternal-agent
```

## 配置

配置文件位于 `data/config.json`，首次运行自动创建。

```json
{
  "loop_delay": 0.3,
  "evolve_step": 50,
  "task_queue_max": 200,
  "log_level": "INFO"
}
```

## 监控

### 查看日志

```bash
# 实时查看
tail -f data/logs/eternal_agent.log

# 查看最近100行
tail -n 100 data/logs/eternal_agent.log
```

### 查看知识图谱

```bash
# 查看图谱文件
cat data/knowledge_graph.json | python -m json.tool
```

### 导出可视化

```python
from eternal_agent import EternalSelfAgent

agent = EternalSelfAgent()
agent.initialize()

# 导出Mermaid格式
print(agent.export_kg_visualization("mermaid"))

# 导出Graphviz格式
print(agent.export_kg_visualization("graphviz"))
```

## 停止

### 优雅停机

```bash
# 前台运行：Ctrl+C

# 后台运行：发送SIGTERM
kill -TERM $(cat eternal_agent.pid)
```

### systemd 停止

```bash
sudo systemctl stop eternal-agent
```

## 备份

### 备份知识图谱

```bash
cp data/knowledge_graph.json backup/kg_$(date +%Y%m%d).json
```

### 自动备份脚本

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/path/to/backups"
mkdir -p $BACKUP_DIR

cp data/knowledge_graph.json $BACKUP_DIR/kg_$(date +%Y%m%d_%H%M%S).json

# 保留最近30个备份
ls -t $BACKUP_DIR/kg_*.json | tail -n +31 | xargs rm -f
```

## 故障排查

### 系统不启动

1. 检查Python版本：`python --version`（需3.8+）
2. 检查日志：`cat data/logs/eternal_agent.log`
3. 检查磁盘空间：`df -h`

### 知识图谱损坏

```python
from knowledge_graph import KnowledgeGraph

# 尝试修复
kg = KnowledgeGraph()
health = kg.health_check()
print(health)

fixed = kg.repair()
print(fixed)
```

### 重置系统

```bash
# 停止系统
# 删除数据目录
rm -rf data/
# 重新启动
python src/main.py
```

## 性能调优

### 降低CPU占用

编辑 `data/config.json`：

```json
{
  "loop_delay": 1.0  # 增加循环节拍
}
```

### 减少磁盘写入

编辑 `src/constants.py`：

```python
# 增加日志文件大小限制
LOG_MAX_BYTES = 50 * 1024 * 1024  # 50MB
```

## 安全

### 文件权限

```bash
# 限制数据目录权限
chmod 700 data/
chmod 600 data/knowledge_graph.json
chmod 600 data/config.json
```

### 日志清理

```bash
# 清理旧日志
find data/logs/ -name "*.log" -mtime +30 -delete
```
