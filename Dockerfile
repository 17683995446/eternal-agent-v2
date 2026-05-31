# 永动知识图谱Agent - Docker镜像
# 遵循"大事做于细，难事成于易"原则

# 基础镜像
FROM python:3.11-slim

# 元数据
LABEL maintainer="Eternal Agent Team"
LABEL version="1.0.0"
LABEL description="永动知识图谱Agent - 基于第一性原理的轻量化智能体"

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    LOG_LEVEL=INFO \
    DATA_DIR=/app/data

# 创建非root用户
RUN groupadd -r agent && useradd -r -g agent agent

# 创建必要目录
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R agent:agent /app

# 复制源代码
COPY src/ /app/src/
COPY examples/ /app/examples/
COPY README.md /app/

# 安装依赖（零外部依赖，仅标准库）
RUN pip install --no-cache-dir pytest

# 切换到非root用户
USER agent

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from health import HealthChecker; hc = HealthChecker(); exit(0 if hc.check()['healthy'] else 1)"

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python", "-m", "src.main"]
