"""
教程模块 — 文档与示例层

公理溯源：记忆公理 - 知识需要被教授和传播

设计意图：
- 提供交互式学习引导
- 分步骤教程系统
- 实践练习和测验
- 学习进度追踪

大事做于细，难事成于易：
- 每个教程专注于一个概念
- 渐进式难度递增
- 即时反馈和提示
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from pathlib import Path

from logger import get_logger
from utils import now_iso, read_json, write_json
from constants import PROJECT_ROOT, ENCODING

logger = get_logger("Tutorials")


class TutorialLevel(Enum):
    """教程难度级别"""
    BEGINNER = "beginner"      # 初级
    INTERMEDIATE = "intermediate"  # 中级
    ADVANCED = "advanced"      # 高级


class TutorialStatus(Enum):
    """教程状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    LOCKED = "locked"


@dataclass
class TutorialStep:
    """教程步骤"""
    title: str
    description: str
    code_example: Optional[str] = None
    expected_output: Optional[str] = None
    hint: Optional[str] = None
    validation: Optional[Callable[[Any], bool]] = None


@dataclass
class Tutorial:
    """教程结构"""
    id: str
    title: str
    description: str
    level: TutorialLevel
    steps: List[TutorialStep] = field(default_factory=list)
    status: TutorialStatus = TutorialStatus.NOT_STARTED
    current_step: int = 0
    completed_at: Optional[str] = None
    prerequisites: List[str] = field(default_factory=list)


@dataclass
class QuizQuestion:
    """测验题目"""
    question: str
    options: List[str]
    correct_answer: int  # 选项索引
    explanation: str


@dataclass
class TutorialProgress:
    """学习进度"""
    user_id: str
    completed_tutorials: List[str] = field(default_factory=list)
    current_tutorial: Optional[str] = None
    current_step: int = 0
    quiz_scores: Dict[str, int] = field(default_factory=dict)
    last_activity: str = field(default_factory=now_iso)


class TutorialManager:
    """
    教程管理器
    
    管理所有教程的加载、执行和进度追踪
    """
    
    def __init__(self, progress_file: Optional[Path] = None):
        self.tutorials: Dict[str, Tutorial] = {}
        self.progress: Dict[str, TutorialProgress] = {}
        self.progress_file = progress_file or (PROJECT_ROOT / "data" / "tutorial_progress.json")
        self._load_progress()
        self._init_tutorials()
    
    def _init_tutorials(self):
        """初始化内置教程"""
        # 教程1: 基础知识图谱
        self._create_knowledge_graph_tutorial()
        
        # 教程2: 任务队列
        self._create_task_queue_tutorial()
        
        # 教程3: 永动循环
        self._create_eternal_loop_tutorial()
        
        # 教程4: 推理引擎
        self._create_reasoning_tutorial()
    
    def _create_knowledge_graph_tutorial(self):
        """创建知识图谱教程"""
        steps = [
            TutorialStep(
                title="创建知识图谱",
                description="首先，我们需要创建一个知识图谱实例。知识图谱是系统的核心记忆载体。",
                code_example="""
from knowledge_graph import KnowledgeGraph

# 创建知识图谱实例
kg = KnowledgeGraph()
print("知识图谱创建成功！")
""",
                expected_output="知识图谱创建成功！",
                hint="使用 KnowledgeGraph() 构造函数创建实例"
            ),
            TutorialStep(
                title="添加节点",
                description="节点代表知识图谱中的实体。让我们添加一些技术相关的节点。",
                code_example="""
# 添加节点
kg.add_node("Python", "language")
kg.add_node("FastAPI", "framework")
print("已添加 2 个节点")
""",
                expected_output="已添加 2 个节点",
                hint="使用 add_node(name, type) 方法添加节点"
            ),
            TutorialStep(
                title="添加关系",
                description="关系连接不同的节点，表示它们之间的关联。",
                code_example="""
# 添加关系
kg.add_edge("Python", "FastAPI", "powers", 0.95)
print("已添加关系: Python powers FastAPI")
""",
                expected_output="已添加关系: Python powers FastAPI",
                hint="使用 add_edge(source, target, relation, weight) 方法"
            ),
            TutorialStep(
                title="查询知识",
                description="现在让我们查询知识图谱中的信息。",
                code_example="""
# 查询节点
nodes = kg.find_nodes(node_type="language")
print(f"找到 {len(nodes)} 个语言节点")
for node in nodes:
    print(f"  - {node.name}")
""",
                expected_output="找到 1 个语言节点\n  - Python",
                hint="使用 find_nodes() 方法查询节点"
            ),
            TutorialStep(
                title="保存知识",
                description="最后，保存知识图谱到文件，确保数据不会丢失。",
                code_example="""
# 保存知识图谱
kg.save()
print("知识图谱已保存！")
""",
                expected_output="知识图谱已保存！",
                hint="使用 save() 方法保存知识图谱"
            )
        ]
        
        tutorial = Tutorial(
            id="knowledge_graph_basics",
            title="知识图谱基础",
            description="学习如何创建和管理知识图谱，包括添加节点、关系和查询知识。",
            level=TutorialLevel.BEGINNER,
            steps=steps
        )
        
        self.tutorials[tutorial.id] = tutorial
    
    def _create_task_queue_tutorial(self):
        """创建任务队列教程"""
        steps = [
            TutorialStep(
                title="创建任务队列",
                description="任务队列是系统的存续层核心，用于管理待处理的任务。",
                code_example="""
from task_queue import TaskQueue, Task

# 创建任务队列
queue = TaskQueue()
print("任务队列创建成功！")
""",
                expected_output="任务队列创建成功！",
                hint="使用 TaskQueue() 构造函数"
            ),
            TutorialStep(
                title="添加任务",
                description="向队列中添加任务，每个任务都有名称、类型和负载。",
                code_example="""
# 创建任务
task = Task(
    name="示例任务",
    task_type="demo",
    payload={"message": "Hello"}
)

# 添加到队列
queue.enqueue(task)
print(f"队列中有 {queue.size()} 个任务")
""",
                expected_output="队列中有 1 个任务",
                hint="使用 Task 类创建任务，enqueue() 方法添加"
            ),
            TutorialStep(
                title="注册处理器",
                description="为任务类型注册处理器函数。",
                code_example="""
# 定义处理器
def my_handler(task):
    print(f"处理任务: {task.name}")
    print(f"负载: {task.payload}")
    return True

# 注册处理器
queue.register_handler("demo", my_handler)
print("处理器注册成功！")
""",
                expected_output="处理器注册成功！",
                hint="使用 register_handler(task_type, handler) 方法"
            ),
            TutorialStep(
                title="处理任务",
                description="从队列中取出任务并处理。",
                code_example="""
# 取出任务
task = queue.dequeue()
if task:
    # 获取处理器
    handler = queue.get_handler(task.task_type)
    if handler:
        success = handler(task)
        print(f"任务处理{'成功' if success else '失败'}")
""",
                expected_output="处理任务: 示例任务\n负载: {'message': 'Hello'}\n任务处理成功",
                hint="使用 dequeue() 取出任务，get_handler() 获取处理器"
            )
        ]
        
        tutorial = Tutorial(
            id="task_queue_basics",
            title="任务队列基础",
            description="学习如何使用任务队列管理任务，包括添加、处理和状态管理。",
            level=TutorialLevel.BEGINNER,
            steps=steps,
            prerequisites=["knowledge_graph_basics"]
        )
        
        self.tutorials[tutorial.id] = tutorial
    
    def _create_eternal_loop_tutorial(self):
        """创建永动循环教程"""
        steps = [
            TutorialStep(
                title="创建永动循环",
                description="永动循环是系统的核心，确保任务持续被处理。",
                code_example="""
from loop import EternalLoop
from task_queue import TaskQueue

# 创建队列和循环
queue = TaskQueue()
loop = EternalLoop(queue)
print("永动循环创建成功！")
""",
                expected_output="永动循环创建成功！",
                hint="使用 EternalLoop(queue) 构造函数"
            ),
            TutorialStep(
                title="设置回调",
                description="设置各种回调函数来处理不同的事件。",
                code_example="""
# 定义回调
def on_task(task):
    print(f"开始处理: {task.name}")

def on_idle():
    print("队列空闲，等待新任务...")

print("回调函数已定义")
""",
                expected_output="回调函数已定义",
                hint="定义回调函数并在运行循环时传入"
            ),
            TutorialStep(
                title="运行循环",
                description="启动永动循环。注意：实际运行时会持续执行。",
                code_example="""
# 添加示例任务
task = Task(name="循环任务", task_type="demo")
queue.enqueue(task)

print("准备启动循环...")
print("提示：实际使用时调用 loop.run(on_task=on_task, on_idle=on_idle)")
""",
                expected_output="准备启动循环...\n提示：实际使用时调用 loop.run(on_task=on_task, on_idle=on_idle)",
                hint="使用 run() 方法启动循环，可以设置各种回调"
            )
        ]
        
        tutorial = Tutorial(
            id="eternal_loop_basics",
            title="永动循环基础",
            description="学习如何使用永动循环持续处理任务。",
            level=TutorialLevel.INTERMEDIATE,
            steps=steps,
            prerequisites=["task_queue_basics"]
        )
        
        self.tutorials[tutorial.id] = tutorial
    
    def _create_reasoning_tutorial(self):
        """创建推理引擎教程"""
        steps = [
            TutorialStep(
                title="创建推理引擎",
                description="推理引擎可以从现有知识中推导出新知识。",
                code_example="""
from reasoning import RuleEngine
from knowledge_graph import KnowledgeGraph

# 创建知识图谱和推理引擎
kg = KnowledgeGraph()
engine = RuleEngine(kg)
print("推理引擎创建成功！")
""",
                expected_output="推理引擎创建成功！",
                hint="使用 RuleEngine(kg) 构造函数"
            ),
            TutorialStep(
                title="添加规则",
                description="定义推理规则，当条件满足时触发结论。",
                code_example="""
# 添加规则
def if_python_then_fastapi(kg):
    # 如果知道Python，推荐FastAPI
    if kg.has_node("Python") and not kg.has_node("FastAPI"):
        return [("FastAPI", "framework", {"note": "推荐学习"})]
    return []

engine.add_rule("recommend_fastapi", if_python_then_fastapi)
print("规则添加成功！")
""",
                expected_output="规则添加成功！",
                hint="使用 add_rule(name, rule_fn) 方法添加规则"
            ),
            TutorialStep(
                title="执行推理",
                description="运行推理引擎，应用所有规则。",
                code_example="""
# 先添加Python节点
kg.add_node("Python", "language")

# 执行推理
new_knowledge = engine.infer()
print(f"推理完成，发现 {len(new_knowledge)} 条新知识")
for node in new_knowledge:
    print(f"  - 推荐: {node[0]}")
""",
                expected_output="推理完成，发现 1 条新知识\n  - 推荐: FastAPI",
                hint="使用 infer() 方法执行推理"
            )
        ]
        
        tutorial = Tutorial(
            id="reasoning_basics",
            title="推理引擎基础",
            description="学习如何使用推理引擎从现有知识中推导新知识。",
            level=TutorialLevel.ADVANCED,
            steps=steps,
            prerequisites=["knowledge_graph_basics"]
        )
        
        self.tutorials[tutorial.id] = tutorial
    
    def list_tutorials(self, level: Optional[TutorialLevel] = None) -> List[Tutorial]:
        """
        列出所有教程
        
        Args:
            level: 按难度级别过滤
            
        Returns:
            教程列表
        """
        tutorials = list(self.tutorials.values())
        if level:
            tutorials = [t for t in tutorials if t.level == level]
        return sorted(tutorials, key=lambda t: (t.level.value, t.id))
    
    def get_tutorial(self, tutorial_id: str) -> Optional[Tutorial]:
        """获取指定教程"""
        return self.tutorials.get(tutorial_id)
    
    def start_tutorial(self, tutorial_id: str, user_id: str = "default") -> Optional[TutorialStep]:
        """
        开始教程
        
        Args:
            tutorial_id: 教程ID
            user_id: 用户ID
            
        Returns:
            第一个步骤
        """
        tutorial = self.tutorials.get(tutorial_id)
        if not tutorial:
            logger.error(f"教程不存在: {tutorial_id}")
            return None
        
        # 检查前置条件
        for prereq in tutorial.prerequisites:
            if prereq not in self.progress.get(user_id, TutorialProgress(user_id=user_id)).completed_tutorials:
                logger.warning(f"前置教程未完成: {prereq}")
                return None
        
        # 更新状态
        tutorial.status = TutorialStatus.IN_PROGRESS
        tutorial.current_step = 0
        
        # 更新进度
        if user_id not in self.progress:
            self.progress[user_id] = TutorialProgress(user_id=user_id)
        self.progress[user_id].current_tutorial = tutorial_id
        self.progress[user_id].current_step = 0
        self._save_progress()
        
        return tutorial.steps[0] if tutorial.steps else None
    
    def next_step(self, tutorial_id: str, user_id: str = "default") -> Optional[TutorialStep]:
        """
        进入下一步
        
        Args:
            tutorial_id: 教程ID
            user_id: 用户ID
            
        Returns:
            下一步，如果完成则返回None
        """
        tutorial = self.tutorials.get(tutorial_id)
        if not tutorial:
            return None
        
        tutorial.current_step += 1
        
        # 更新进度
        if user_id in self.progress:
            self.progress[user_id].current_step = tutorial.current_step
            self._save_progress()
        
        if tutorial.current_step >= len(tutorial.steps):
            # 教程完成
            tutorial.status = TutorialStatus.COMPLETED
            tutorial.completed_at = now_iso()
            if user_id in self.progress:
                if tutorial_id not in self.progress[user_id].completed_tutorials:
                    self.progress[user_id].completed_tutorials.append(tutorial_id)
                self.progress[user_id].current_tutorial = None
                self._save_progress()
            return None
        
        return tutorial.steps[tutorial.current_step]
    
    def get_current_step(self, tutorial_id: str) -> Optional[TutorialStep]:
        """获取当前步骤"""
        tutorial = self.tutorials.get(tutorial_id)
        if not tutorial or tutorial.current_step >= len(tutorial.steps):
            return None
        return tutorial.steps[tutorial.current_step]
    
    def get_progress(self, user_id: str = "default") -> TutorialProgress:
        """获取用户进度"""
        return self.progress.get(user_id, TutorialProgress(user_id=user_id))
    
    def _load_progress(self):
        """加载进度"""
        if self.progress_file.exists():
            try:
                data = read_json(self.progress_file)
                for user_id, progress_data in data.items():
                    self.progress[user_id] = TutorialProgress(
                        user_id=user_id,
                        completed_tutorials=progress_data.get("completed_tutorials", []),
                        current_tutorial=progress_data.get("current_tutorial"),
                        current_step=progress_data.get("current_step", 0),
                        quiz_scores=progress_data.get("quiz_scores", {}),
                        last_activity=progress_data.get("last_activity", now_iso())
                    )
                logger.info(f"已加载 {len(self.progress)} 个用户的进度")
            except Exception as e:
                logger.warning(f"加载进度失败: {e}")
    
    def _save_progress(self):
        """保存进度"""
        try:
            data = {}
            for user_id, progress in self.progress.items():
                data[user_id] = {
                    "completed_tutorials": progress.completed_tutorials,
                    "current_tutorial": progress.current_tutorial,
                    "current_step": progress.current_step,
                    "quiz_scores": progress.quiz_scores,
                    "last_activity": now_iso()
                }
            write_json(self.progress_file, data)
        except Exception as e:
            logger.warning(f"保存进度失败: {e}")


class InteractiveTutorial:
    """
    交互式教程
    
    提供命令行交互式教程体验
    """
    
    def __init__(self):
        self.manager = TutorialManager()
    
    def run(self):
        """运行交互式教程"""
        print("\n" + "="*60)
        print("永动知识图谱Agent - 交互式教程")
        print("="*60)
        
        while True:
            print("\n主菜单:")
            print("1. 浏览教程")
            print("2. 查看进度")
            print("3. 退出")
            
            choice = input("\n请选择 (1-3): ").strip()
            
            if choice == "1":
                self._browse_tutorials()
            elif choice == "2":
                self._show_progress()
            elif choice == "3":
                print("\n感谢使用，再见！")
                break
            else:
                print("无效选择，请重试")
    
    def _browse_tutorials(self):
        """浏览教程"""
        tutorials = self.manager.list_tutorials()
        
        print("\n" + "-"*60)
        print("可用教程:")
        print("-"*60)
        
        for i, tutorial in enumerate(tutorials, 1):
            status = "✓" if tutorial.status == TutorialStatus.COMPLETED else " "
            level_icon = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}
            icon = level_icon.get(tutorial.level.value, "⚪")
            print(f"{i}. [{status}] {icon} {tutorial.title} ({tutorial.level.value})")
            print(f"   {tutorial.description[:50]}...")
        
        print("\n0. 返回主菜单")
        
        try:
            choice = int(input("\n请选择教程编号: ").strip())
            if choice == 0:
                return
            if 1 <= choice <= len(tutorials):
                self._run_tutorial(tutorials[choice - 1])
            else:
                print("无效选择")
        except ValueError:
            print("请输入数字")
    
    def _run_tutorial(self, tutorial: Tutorial):
        """运行指定教程"""
        print(f"\n{'='*60}")
        print(f"教程: {tutorial.title}")
        print(f"{'='*60}")
        print(f"{tutorial.description}\n")
        
        # 开始教程
        step = self.manager.start_tutorial(tutorial.id)
        
        while step:
            print(f"\n{'-'*60}")
            print(f"步骤 {tutorial.current_step + 1}/{len(tutorial.steps)}: {step.title}")
            print(f"{'-'*60}")
            print(step.description)
            
            if step.code_example:
                print("\n代码示例:")
                print("```python")
                print(step.code_example.strip())
                print("```")
            
            print("\n选项:")
            print("1. 下一步")
            print("2. 查看提示")
            print("3. 退出教程")
            
            choice = input("\n请选择 (1-3): ").strip()
            
            if choice == "1":
                step = self.manager.next_step(tutorial.id)
                if step is None:
                    print(f"\n🎉 恭喜！你已完成教程: {tutorial.title}")
                    input("\n按回车键继续...")
            elif choice == "2":
                if step.hint:
                    print(f"\n提示: {step.hint}")
                else:
                    print("\n暂无提示")
                input("\n按回车键继续...")
            elif choice == "3":
                print("\n已退出教程")
                break
            else:
                print("无效选择")
    
    def _show_progress(self):
        """显示学习进度"""
        progress = self.manager.get_progress()
        
        print("\n" + "-"*60)
        print("学习进度")
        print("-"*60)
        print(f"已完成教程: {len(progress.completed_tutorials)}")
        
        if progress.completed_tutorials:
            print("\n已完成:")
            for tid in progress.completed_tutorials:
                tutorial = self.manager.get_tutorial(tid)
                if tutorial:
                    print(f"  ✓ {tutorial.title}")
        
        if progress.current_tutorial:
            tutorial = self.manager.get_tutorial(progress.current_tutorial)
            if tutorial:
                print(f"\n进行中: {tutorial.title}")
                print(f"  步骤: {progress.current_step + 1}/{len(tutorial.steps)}")
        
        input("\n按回车键继续...")


def run_tutorial():
    """运行教程（入口函数）"""
    tutorial = InteractiveTutorial()
    tutorial.run()


if __name__ == "__main__":
    run_tutorial()
