"""
异常定义模块

公理溯源：存续公理 - 局部异常永远不能击穿整体系统，需要清晰的异常层级

设计意图：
- 定义系统专用异常类型
- 支持异常分类处理
- 便于日志追踪和问题定位
"""


class EternalAgentError(Exception):
    """
    永恒智能体基础异常
    
    公理溯源：存续公理 - 所有异常的基类
    
    所有系统异常都继承此类，便于统一捕获和处理
    """
    
    def __init__(self, message: str, cause: Exception = None):
        """
        初始化异常
        
        Args:
            message: 异常消息
            cause: 原始异常（可选）
        """
        self.message = message
        self.cause = cause
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


# ============================================================
# 存续层异常
# ============================================================

class SurvivalError(EternalAgentError):
    """
    存续层异常基类
    
    公理溯源：存续公理 - 与系统存活相关的异常
    """
    pass


class SystemOverloadError(SurvivalError):
    """
    系统过载异常
    
    触发条件：CPU/内存/磁盘超过阈值
    处理策略：触发熔断保护
    """
    pass


class SelfRepairError(SurvivalError):
    """
    自愈失败异常
    
    触发条件：连续自愈尝试失败
    处理策略：记录日志，等待下次自愈
    """
    pass


class MaxConsecutiveErrorsError(SurvivalError):
    """
    最大连续错误异常
    
    触发条件：连续错误次数超过阈值
    处理策略：触发熔断保护
    """
    pass


# ============================================================
# 记忆层异常
# ============================================================

class KnowledgeMemoryError(EternalAgentError):
    """
    记忆层异常基类
    
    公理溯源：记忆公理 - 与知识图谱相关的异常
    
    注意：重命名为 KnowledgeMemoryError 以避免覆盖 Python 内置的 MemoryError
    """
    pass


class KnowledgeGraphError(KnowledgeMemoryError):
    """
    知识图谱异常
    
    触发条件：图谱操作失败
    处理策略：记录日志，尝试恢复
    """
    pass


class NodeNotFoundError(KnowledgeGraphError):
    """
    节点不存在异常
    
    触发条件：查询不存在的节点
    处理策略：返回空或创建节点
    """
    pass


class EdgeNotFoundError(KnowledgeGraphError):
    """
    边不存在异常
    
    触发条件：查询不存在的边
    处理策略：返回空或创建边
    """
    pass


class PersistenceError(KnowledgeMemoryError):
    """
    持久化异常
    
    触发条件：文件读写失败
    处理策略：记录日志，重试或使用内存数据
    """
    pass


# ============================================================
# 自驱层异常
# ============================================================

class SelfDriveError(EternalAgentError):
    """
    自驱层异常基类
    
    公理溯源：自驱公理 - 与任务执行相关的异常
    """
    pass


class TaskError(SelfDriveError):
    """
    任务异常
    
    触发条件：任务执行失败
    处理策略：标记任务失败，继续下一个任务
    """
    pass


class TaskQueueFullError(SelfDriveError):
    """
    任务队列满异常
    
    触发条件：任务队列达到上限
    处理策略：丢弃最旧任务或拒绝新任务
    """
    pass


class TaskDerivationError(SelfDriveError):
    """
    任务推演异常
    
    触发条件：从知识图谱推演任务失败
    处理策略：记录日志，跳过本次推演
    """
    pass


# ============================================================
# 配置层异常
# ============================================================

class ConfigError(EternalAgentError):
    """
    配置异常基类
    """
    pass


class ConfigLoadError(ConfigError):
    """
    配置加载异常
    
    触发条件：配置文件读取或解析失败
    处理策略：使用默认配置
    """
    pass


class ConfigValidationError(ConfigError):
    """
    配置验证异常
    
    触发条件：配置值不合法
    处理策略：使用默认值或报错
    """
    pass


# ============================================================
# 资源层异常
# ============================================================

class ResourceError(EternalAgentError):
    """
    资源异常基类
    """
    pass


class MemoryLimitExceededError(ResourceError):
    """
    内存超限异常
    
    触发条件：内存使用超过阈值
    处理策略：触发垃圾回收或熔断
    """
    pass


class DiskLimitExceededError(ResourceError):
    """
    磁盘超限异常
    
    触发条件：磁盘使用超过阈值
    处理策略：清理旧日志或知识
    """
    pass
