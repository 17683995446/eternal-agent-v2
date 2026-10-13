#!/usr/bin/env python3
"""
智能对话演示 - Eternal Agent + 硅基流动LLM

演示功能：
1. 自然语言对话
2. 多轮上下文
3. 思考模式（逐步推理）
4. 与知识图谱联动
"""
import sys
sys.path.insert(0, '/workspace/eternal_agent/src')

from llm_client import LLMClient, init_llm_client
from chat_manager import ChatManager
from knowledge_graph import KnowledgeGraph

# API密钥
API_KEY = "REDACTED_API_KEY"

def demo_basic_chat():
    """演示1: 基础对话"""
    print("\n" + "=" * 60)
    print("演示1: 基础对话")
    print("=" * 60)
    
    client = LLMClient(api_key=API_KEY)
    
    # 单轮对话
    print("\n用户: 你好，请介绍一下自己")
    response = client.chat("你好，请介绍一下自己")
    print(f"助手: {response.content}")
    print(f"[耗时: {response.elapsed_ms:.0f}ms]")
    
    # 多轮对话
    print("\n用户: 你能做什么？")
    response = client.chat("你能做什么？")
    print(f"助手: {response.content[:200]}...")
    
    print("\n用户: 给我一个简单的Python示例")
    response = client.chat("给我一个简单的Python示例")
    print(f"助手: {response.content[:300]}...")


def demo_session_chat():
    """演示2: 多会话管理"""
    print("\n" + "=" * 60)
    print("演示2: 多会话管理")
    print("=" * 60)
    
    llm = LLMClient(api_key=API_KEY)
    manager = ChatManager(llm)
    
    # 创建会话1
    session1 = manager.new_session("tech_chat")
    print(f"\n创建会话: {session1}")
    
    print("\n用户: Python中list和tuple有什么区别？")
    response = manager.chat("Python中list和tuple有什么区别？")
    print(f"助手: {response.content[:200]}...")
    
    print("\n用户: 那dict呢？")
    response = manager.chat("那dict呢？")
    print(f"助手: {response.content[:200]}...")
    
    # 创建会话2
    session2 = manager.new_session("casual_chat")
    print(f"\n创建新会话: {session2}")
    
    print("\n用户: 今天天气怎么样？")
    response = manager.chat("今天天气怎么样？")
    print(f"助手: {response.content[:150]}...")
    
    # 列出所有会话
    print("\n所有会话:")
    for s in manager.list_sessions():
        print(f"  - {s['session_id']}: {s['message_count']}条消息")


def demo_think_mode():
    """演示3: 思考模式"""
    print("\n" + "=" * 60)
    print("演示3: 思考模式（逐步推理）")
    print("=" * 60)
    
    client = LLMClient(api_key=API_KEY)
    
    task = "如果一个房间里有100个人，每人平均认识50个人，那么这个房间里至少有多少对人互相认识？"
    
    print(f"\n问题: {task}")
    print("\n思考中...")
    
    result = client.think(task)
    print(f"\n推理过程:\n{result}")


def demo_kg_integration():
    """演示4: 知识图谱联动"""
    print("\n" + "=" * 60)
    print("演示4: 知识图谱 + LLM联动")
    print("=" * 60)
    
    # 初始化知识图谱
    kg = KnowledgeGraph()
    kg.add_node("Python", "语言")
    kg.add_node("Java", "语言")
    kg.add_node("JavaScript", "语言")
    kg.add_edge("Python", "Java", "竞争对手")
    kg.add_edge("Python", "JavaScript", "竞争对手")
    
    # 初始化LLM
    client = LLMClient(api_key=API_KEY)
    
    # 从知识图谱获取上下文
    context = f"知识库中的信息:\n"
    for node in kg.get_all_nodes():
        context += f"- {node.name} (类型: {node.node_type})\n"
    
    print(f"\n{context}")
    
    # 结合上下文提问
    question = "根据知识库，有哪些编程语言？它们之间有什么关系？"
    print(f"用户: {question}")
    
    response = client.chat_with_context(question, context)
    print(f"助手: {response.content}")


def demo_interactive():
    """演示5: 交互式对话"""
    print("\n" + "=" * 60)
    print("演示5: 交互式对话 (输入 'quit' 退出)")
    print("=" * 60)
    
    client = LLMClient(api_key=API_KEY)
    client.set_system_prompt("你是Eternal Agent的智能助手，具备知识推理和任务执行能力。回答要简洁专业。")
    
    print("\n开始对话 (输入问题后按回车):")
    
    while True:
        try:
            user_input = input("\n用户: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ('quit', 'exit', 'q'):
                print("再见！")
                break
            
            response = client.chat(user_input)
            print(f"助手: {response.content}")
            
        except KeyboardInterrupt:
            print("\n再见！")
            break


def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     Eternal Agent + 硅基流动LLM 智能对话演示            ║
║     模型: Qwen3-8B (通义千问3)                           ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # 运行演示
    demo_basic_chat()
    demo_session_chat()
    # demo_think_mode()  # 跳过，耗时较长
    demo_kg_integration()
    
    print("\n" + "=" * 60)
    print("所有演示完成！")
    print("=" * 60)
    
    # 显示统计
    client = LLMClient(api_key=API_KEY)
    print(f"\nLLM统计: {client.stats()}")


if __name__ == "__main__":
    main()
