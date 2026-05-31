"""
永恒自驱智能体系统 - 主入口

公理溯源：
- 存续公理：系统启动后永不终止
- 记忆公理：启动时加载历史记忆
- 自驱公理：注入初始认知任务，启动自驱闭环

设计意图：
- 提供系统唯一启动入口
- 整合四层架构
- 展示永动闭环
"""

import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from eternal_agent import EternalSelfAgent
from logger import get_logger

logger = get_logger("Main")


def main():
    """
    主入口函数

    公理溯源：
    - 存续公理：启动后进入主循环，永不退出
    - 记忆公理：加载历史知识图谱
    - 自驱公理：注入初始任务，启动自驱闭环
    """
    logger.info("=" * 60)
    logger.info("  永恒自驱智能体系统")
    logger.info("  基于第一性原理 · 轻量化永动知识图谱Agent")
    logger.info("=" * 60)
    logger.info("")
    logger.info("  三大核心公理：")
    logger.info("  1. 存续公理：系统运行闭环永不终止")
    logger.info("  2. 记忆公理：智能 = 结构化历史经验")
    logger.info("  3. 自驱公理：无外部输入时自我产生任务")
    logger.info("")
    logger.info("=" * 60)

    try:
        # 创建并启动智能体
        agent = EternalSelfAgent()
        agent.initialize()

        # 阶段完成提示
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ 第一阶段（基础架构搭建）完成")
        logger.info("✓ 第二阶段（存续保活层）完成")
        logger.info("✓ 第三阶段（知识记忆层）完成")
        logger.info("✓ 第四阶段（自驱进化层）完成")
        logger.info("")
        logger.info("永动闭环已启动：")
        logger.info("  任务执行 → 知识沉淀 → 任务推演 → 新任务执行")
        logger.info("")
        logger.info("下一阶段: 系统集成验证（阶段46-50）")
        logger.info("=" * 60)
        logger.info("")
        logger.info("系统进入永恒主循环...")
        logger.info("(Ctrl+C 优雅停机)")
        logger.info("")

        # 启动永恒主循环（阻塞，永不返回）
        agent.run()

        return 0

    except Exception as e:
        logger.exception(f"系统启动失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
