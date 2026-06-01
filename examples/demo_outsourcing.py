"""
外包架构完整示例 - 演示多公司协作开发

场景：
- 公司A：开发知识图谱模块
- 公司B：开发任务队列模块  
- 公司C：开发LLM对话模块
- 集成方：通过消息总线组装

每个公司只看到：
1. 自己的契约（需要实现什么）
2. 依赖的契约（可以调用什么）
3. 消息协议（如何通信）
"""
import sys
sys.path.insert(0, '/workspace/eternal_agent/src')

from module_contract import (
    Message, MessageType, MethodContract, EventContract,
    ModuleContract, IOutsourcedModule, MessageBus, ContractValidator
)


# ============================================================
# 公司A：知识图谱模块
# ============================================================

class KnowledgeGraphModuleA(IOutsourcedModule):
    """
    公司A交付的知识图谱模块
    
    契约ID: knowledge_graph
    依赖: 无
    """
    
    def __init__(self):
        self._nodes = {}
        self._edges = []
    
    def get_contract(self) -> ModuleContract:
        return ModuleContract(
            module_id="knowledge_graph",
            module_name="知识图谱",
            version="1.0.0",
            owner="公司A",
            description="知识图谱存储与查询",
            methods=[
                MethodContract(
                    name="add_node",
                    description="添加节点",
                    input_schema={"name": "str", "type": "str"},
                    output_schema={"success": "bool"},
                    errors=["节点已存在"],
                ),
                MethodContract(
                    name="get_node",
                    description="获取节点",
                    input_schema={"name": "str"},
                    output_schema={"node": "dict or None"},
                ),
                MethodContract(
                    name="add_edge",
                    description="添加边",
                    input_schema={"source": "str", "target": "str", "relation": "str"},
                    output_schema={"success": "bool"},
                ),
                MethodContract(
                    name="query",
                    description="查询",
                    input_schema={"type": "str (optional)", "keyword": "str (optional)"},
                    output_schema={"results": "list"},
                ),
                MethodContract(
                    name="stats",
                    description="统计信息",
                    input_schema={},
                    output_schema={"node_count": "int", "edge_count": "int"},
                ),
            ],
            published_events=[
                EventContract(
                    event_name="node_added",
                    description="节点添加事件",
                    data_schema={"name": "str", "type": "str"},
                    publisher="knowledge_graph",
                ),
            ],
            dependencies=[],
        )
    
    def handle_message(self, message: Message) -> Message:
        method = message.method
        params = message.params
        
        if method == "add_node":
            name = params.get("name")
            self._nodes[name] = {"name": name, "type": params.get("type", "unknown")}
            return Message(result={"success": True})
        
        elif method == "get_node":
            name = params.get("name")
            return Message(result={"node": self._nodes.get(name)})
        
        elif method == "add_edge":
            self._edges.append({
                "source": params.get("source"),
                "target": params.get("target"),
                "relation": params.get("relation"),
            })
            return Message(result={"success": True})
        
        elif method == "query":
            node_type = params.get("type")
            results = [
                n for n in self._nodes.values()
                if not node_type or n.get("type") == node_type
            ]
            return Message(result={"results": results})
        
        elif method == "stats":
            return Message(result={
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
            })
        
        return Message(error=f"未知方法: {method}")
    
    def health_check(self) -> dict:
        return {"healthy": True, "details": {"nodes": len(self._nodes), "edges": len(self._edges)}}
    
    def shutdown(self):
        self._nodes.clear()
        self._edges.clear()


# ============================================================
# 公司B：任务队列模块
# ============================================================

class TaskQueueModuleB(IOutsourcedModule):
    """
    公司B交付的任务队列模块
    
    契约ID: task_queue
    依赖: 无
    """
    
    def __init__(self):
        self._tasks = []
        self._task_id = 0
    
    def get_contract(self) -> ModuleContract:
        return ModuleContract(
            module_id="task_queue",
            module_name="任务队列",
            version="1.0.0",
            owner="公司B",
            description="任务调度与执行",
            methods=[
                MethodContract(
                    name="enqueue",
                    description="添加任务",
                    input_schema={"name": "str", "payload": "dict", "priority": "int"},
                    output_schema={"task_id": "int"},
                ),
                MethodContract(
                    name="dequeue",
                    description="取出任务",
                    input_schema={},
                    output_schema={"task": "dict or None"},
                ),
                MethodContract(
                    name="complete",
                    description="完成任务",
                    input_schema={"task_id": "int", "result": "any"},
                    output_schema={"success": "bool"},
                ),
                MethodContract(
                    name="stats",
                    description="统计信息",
                    input_schema={},
                    output_schema={"pending": "int", "completed": "int"},
                ),
            ],
            published_events=[
                EventContract(
                    event_name="task_completed",
                    description="任务完成事件",
                    publisher="task_queue",
                ),
            ],
            dependencies=[],
        )
    
    def handle_message(self, message: Message) -> Message:
        method = message.method
        params = message.params
        
        if method == "enqueue":
            self._task_id += 1
            task = {
                "id": self._task_id,
                "name": params.get("name"),
                "payload": params.get("payload", {}),
                "priority": params.get("priority", 0),
                "status": "pending",
            }
            self._tasks.append(task)
            return Message(result={"task_id": self._task_id})
        
        elif method == "dequeue":
            pending = [t for t in self._tasks if t["status"] == "pending"]
            if pending:
                task = pending[0]
                task["status"] = "running"
                return Message(result={"task": task})
            return Message(result={"task": None})
        
        elif method == "complete":
            task_id = params.get("task_id")
            for t in self._tasks:
                if t["id"] == task_id:
                    t["status"] = "completed"
                    t["result"] = params.get("result")
                    return Message(result={"success": True})
            return Message(error=f"任务不存在: {task_id}")
        
        elif method == "stats":
            pending = sum(1 for t in self._tasks if t["status"] == "pending")
            completed = sum(1 for t in self._tasks if t["status"] == "completed")
            return Message(result={"pending": pending, "completed": completed})
        
        return Message(error=f"未知方法: {method}")
    
    def health_check(self) -> dict:
        return {"healthy": True, "details": {"total_tasks": len(self._tasks)}}
    
    def shutdown(self):
        self._tasks.clear()


# ============================================================
# 公司C：LLM对话模块
# ============================================================

class LLMChatModuleC(IOutsourcedModule):
    """
    公司C交付的LLM对话模块
    
    契约ID: llm_chat
    依赖: 无（LLM调用由公司C内部处理）
    """
    
    def __init__(self):
        self._history = []
    
    def get_contract(self) -> ModuleContract:
        return ModuleContract(
            module_id="llm_chat",
            module_name="LLM对话",
            version="1.0.0",
            owner="公司C",
            description="大语言模型对话",
            methods=[
                MethodContract(
                    name="chat",
                    description="对话",
                    input_schema={"message": "str", "context": "str (optional)"},
                    output_schema={"reply": "str"},
                    timeout_ms=30000,
                ),
                MethodContract(
                    name="clear_history",
                    description="清空对话历史",
                    input_schema={},
                    output_schema={"success": "bool"},
                ),
            ],
            dependencies=[],
        )
    
    def handle_message(self, message: Message) -> Message:
        method = message.method
        params = message.params
        
        if method == "chat":
            user_msg = params.get("message", "")
            context = params.get("context", "")
            
            # 模拟LLM回复（实际由公司C调用真实LLM）
            self._history.append({"role": "user", "content": user_msg})
            reply = f"[LLM回复] 收到: '{user_msg[:50]}...'"
            self._history.append({"role": "assistant", "content": reply})
            
            return Message(result={"reply": reply})
        
        elif method == "clear_history":
            self._history.clear()
            return Message(result={"success": True})
        
        return Message(error=f"未知方法: {method}")
    
    def health_check(self) -> dict:
        return {"healthy": True, "details": {"history_length": len(self._history)}}
    
    def shutdown(self):
        self._history.clear()


# ============================================================
# 集成方：组装所有模块
# ============================================================

def demo_outsourcing():
    """演示外包架构"""
    
    print("=" * 70)
    print("🏢 模块外包架构演示")
    print("=" * 70)
    
    # 1. 创建消息总线
    bus = MessageBus()
    print("\n[1] 消息总线已创建")
    
    # 2. 各公司交付模块
    print("\n[2] 各公司交付模块:")
    
    kg = KnowledgeGraphModuleA()
    print(f"  📦 公司A → {kg.get_contract().module_name} (v{kg.get_contract().version})")
    
    tq = TaskQueueModuleB()
    print(f"  📦 公司B → {tq.get_contract().module_name} (v{tq.get_contract().version})")
    
    llm = LLMChatModuleC()
    print(f"  📦 公司C → {llm.get_contract().module_name} (v{llm.get_contract().version})")
    
    # 3. 验证契约
    print("\n[3] 契约验证:")
    validator = ContractValidator(bus)
    
    for module in [kg, tq, llm]:
        # 先注册（验证需要）
        bus.register_module(module)
        result = validator.validate(module)
        status = "✅ 通过" if result["valid"] else "❌ 失败"
        warnings = f" ({len(result['warnings'])}个警告)" if result["warnings"] else ""
        print(f"  {status} {module.get_contract().module_id}{warnings}")
    
    # 4. 模块间通信
    print("\n[4] 模块间通信演示:")
    
    # 调用公司A的知识图谱
    msg = Message.create_request("system", "knowledge_graph", "add_node", 
                                  {"name": "Python", "type": "language"})
    resp = bus.send(msg)
    print(f"  → 知识图谱.add_node('Python'): {resp.result}")
    
    msg = Message.create_request("system", "knowledge_graph", "add_node",
                                  {"name": "Java", "type": "language"})
    bus.send(msg)
    
    msg = Message.create_request("system", "knowledge_graph", "stats")
    resp = bus.send(msg)
    print(f"  → 知识图谱.stats(): {resp.result}")
    
    # 调用公司B的任务队列
    msg = Message.create_request("system", "task_queue", "enqueue",
                                  {"name": "分析报告", "priority": 1})
    resp = bus.send(msg)
    print(f"  → 任务队列.enqueue('分析报告'): {resp.result}")
    
    msg = Message.create_request("system", "task_queue", "stats")
    resp = bus.send(msg)
    print(f"  → 任务队列.stats(): {resp.result}")
    
    # 调用公司C的LLM
    msg = Message.create_request("system", "llm_chat", "chat",
                                  {"message": "你好"})
    resp = bus.send(msg)
    print(f"  → LLM.chat('你好'): {resp.result}")
    
    # 5. 健康检查
    print("\n[5] 全模块健康检查:")
    for module_id in bus.get_status()["registered_modules"]:
        msg = Message.create_request("monitor", module_id, "health_check")
        resp = bus.send(msg)
        result = resp.result if resp else {}
        if isinstance(result, dict):
            status = "✅" if result.get("healthy") else "❌"
            print(f"  {status} {module_id}: {result.get('details', {})}")
        else:
            print(f"  ❌ {module_id}: 响应异常")
    
    # 6. 输出契约文档
    print("\n[6] 契约文档（可发给各公司）:")
    for module in [kg, tq, llm]:
        contract = module.get_contract()
        print(f"\n  📄 {contract.module_name} ({contract.owner})")
        print(f"     方法: {[m.name for m in contract.methods]}")
        print(f"     事件: {[e.event_name for e in contract.published_events]}")
    
    print("\n" + "=" * 70)
    print("✅ 外包架构演示完成！")
    print("=" * 70)


if __name__ == "__main__":
    demo_outsourcing()
