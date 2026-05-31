"""
HTTP API 接口模块

公理溯源：存续公理 — 系统状态可观测、可控制

设计意图：
- 零外部依赖，仅使用 http.server
- RESTful API 查看和操作系统
- 支持查看状态、知识图谱、任务队列
- 支持添加任务、停止系统
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs

from logger import get_logger

logger = get_logger("HTTPAPI")


class APIHandler(BaseHTTPRequestHandler):
    """
    HTTP API 请求处理器

    路由：
    GET  /status       — 系统状态
    GET  /kg/stats     — 知识图谱统计
    GET  /kg/nodes     — 所有节点
    GET  /kg/edges     — 所有边
    GET  /kg/mermaid   — Mermaid可视化
    GET  /queue        — 任务队列
    GET  /health       — 健康检查
    POST /task         — 添加任务
    POST /stop         — 停止系统
    GET  /             — API文档
    """

    # 由外部注入的agent引用
    agent = None  # type: Optional[Any]

    def _send_json(self, data: Any, status: int = 200):
        """发送JSON响应"""
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> Dict:
        """读取请求体"""
        length = int(self.headers.get('Content-Length', 0))
        if length > 0:
            body = self.rfile.read(length)
            return json.loads(body.decode('utf-8'))
        return {}

    def do_GET(self):
        """处理GET请求"""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == '/' or path == '/api':
                self._handle_docs()
            elif path == '/status':
                self._handle_status()
            elif path == '/kg/stats':
                self._handle_kg_stats()
            elif path == '/kg/nodes':
                self._handle_kg_nodes()
            elif path == '/kg/edges':
                self._handle_kg_edges()
            elif path == '/kg/mermaid':
                self._handle_kg_mermaid()
            elif path == '/queue':
                self._handle_queue()
            elif path == '/health':
                self._handle_health()
            else:
                self._send_json({"error": "未找到路由"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        """处理POST请求"""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == '/task':
                self._handle_add_task()
            elif path == '/stop':
                self._handle_stop()
            else:
                self._send_json({"error": "未找到路由"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    # ============================================================
    # GET 处理器
    # ============================================================

    def _handle_docs(self):
        """API文档"""
        docs = {
            "name": "Eternal Agent HTTP API",
            "version": "1.0",
            "routes": {
                "GET /": "API文档",
                "GET /status": "系统状态",
                "GET /kg/stats": "知识图谱统计",
                "GET /kg/nodes": "所有节点",
                "GET /kg/edges": "所有边",
                "GET /kg/mermaid": "Mermaid可视化",
                "GET /queue": "任务队列",
                "GET /health": "健康检查",
                "POST /task": "添加任务 (body: {name, priority})",
                "POST /stop": "停止系统",
            }
        }
        self._send_json(docs)

    def _handle_status(self):
        """系统状态"""
        if not self.agent:
            self._send_json({"error": "agent未注入"}, 503)
            return

        status = self.agent.get_status()
        self._send_json(status.to_dict())

    def _handle_kg_stats(self):
        """知识图谱统计"""
        if not self.agent:
            self._send_json({"error": "agent未注入"}, 503)
            return

        stats = self.agent.get_kg_stats()
        self._send_json(stats)

    def _handle_kg_nodes(self):
        """所有节点"""
        if not self.agent:
            self._send_json({"error": "agent未注入"}, 503)
            return

        nodes = [n.to_dict() for n in self.agent.knowledge_graph.get_all_nodes()]
        self._send_json({"nodes": nodes, "count": len(nodes)})

    def _handle_kg_edges(self):
        """所有边"""
        if not self.agent:
            self._send_json({"error": "agent未注入"}, 503)
            return

        edges = [e.to_dict() for e in self.agent.knowledge_graph.get_all_edges()]
        self._send_json({"edges": edges, "count": len(edges)})

    def _handle_kg_mermaid(self):
        """Mermaid可视化"""
        if not self.agent:
            self._send_json({"error": "agent未注入"}, 503)
            return

        mermaid = self.agent.knowledge_graph.export_mermaid()
        self._send_json({"mermaid": mermaid})

    def _handle_queue(self):
        """任务队列"""
        if not self.agent:
            self._send_json({"error": "agent未注入"}, 503)
            return

        stats = self.agent.task_queue.stats()
        names = self.agent.task_queue.get_all_names()
        self._send_json({"stats": stats, "tasks": names})

    def _handle_health(self):
        """健康检查"""
        from monitor import monitor
        status = monitor.check_health()
        self._send_json({
            "status": "healthy" if status.is_healthy else "unhealthy",
            "cpu": status.cpu_percent,
            "memory_mb": status.memory_mb,
            "disk_percent": status.disk_percent,
            "warnings": status.warnings,
        })

    # ============================================================
    # POST 处理器
    # ============================================================

    def _handle_add_task(self):
        """添加任务"""
        if not self.agent:
            self._send_json({"error": "agent未注入"}, 503)
            return

        body = self._read_body()
        name = body.get("name", "")
        priority = body.get("priority", 0)

        if not name:
            self._send_json({"error": "缺少name参数"}, 400)
            return

        self.agent.task_queue.add(name, priority=priority)
        self._send_json({"success": True, "task": name, "priority": priority})

    def _handle_stop(self):
        """停止系统"""
        if not self.agent:
            self._send_json({"error": "agent未注入"}, 503)
            return

        self.agent.stop()
        self._send_json({"success": True, "message": "系统正在停止"})

    def log_message(self, format, *args):
        """自定义日志"""
        logger.debug(f"HTTP: {args[0][:-1] if args else ''}")


class APIServer:
    """
    HTTP API 服务器

    用法：
        server = APIServer(agent, port=8080)
        server.start()  # 非阻塞
        server.stop()
    """

    def __init__(self, agent, port: int = 8080, host: str = "127.0.0.1"):
        self.agent = agent
        self.port = port
        self.host = host
        self._server: Optional[HTTPServer] = None

        # 注入agent引用
        APIHandler.agent = agent

    def start(self):
        """启动服务器（非阻塞）"""
        import threading

        def _run():
            self._server = HTTPServer((self.host, self.port), APIHandler)
            logger.info(f"HTTP API 启动: http://{self.host}:{self.port}")
            self._server.serve_forever()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def stop(self):
        """停止服务器"""
        if self._server:
            self._server.shutdown()
            logger.info("HTTP API 已停止")
