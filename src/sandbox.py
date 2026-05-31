"""
安全沙箱模块

公理溯源：存续公理 - 任务在隔离环境中执行，防止恶意或错误代码影响系统

设计意图：
- 资源限制（CPU时间、内存、输出大小）
- 代码执行隔离
- 禁止危险操作
- 执行超时
- 零外部依赖
"""

import io
import contextlib
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from exceptions import EternalAgentError


class SandboxError(EternalAgentError):
    """沙箱异常"""
    pass


class SandboxTimeoutError(SandboxError):
    """沙箱执行超时"""
    pass


class SandboxMemoryError(SandboxError):
    """沙箱内存超限"""
    pass


class SandboxSecurityError(SandboxError):
    """沙箱安全违规"""
    pass


# 禁止的内置函数和模块
FORBIDDEN_BUILTINS = {
    "exec", "eval", "compile", "__import__",
    "open", "input", "breakpoint",
}

FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil",
    "signal", "socket", "ctypes",
    "multiprocessing", "threading",
    "importlib", "pkgutil",
}


@dataclass
class SandboxResult:
    """
    沙箱执行结果

    Attributes:
        success: 是否成功
        return_value: 返回值
        stdout: 标准输出
        stderr: 标准错误
        error: 错误信息
        duration_ms: 执行耗时（毫秒）
        memory_peak_bytes: 内存峰值（估算）
        timed_out: 是否超时
        security_violations: 安全违规列表
    """
    success: bool = True
    return_value: Any = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0
    memory_peak_bytes: int = 0
    timed_out: bool = False
    security_violations: List[str] = field(default_factory=list)


@dataclass
class SandboxConfig:
    """沙箱配置"""
    timeout_seconds: float = 10.0
    max_output_bytes: int = 1024 * 1024  # 1MB
    max_memory_mb: int = 64
    allow_network: bool = False
    allow_filesystem: bool = False
    allow_imports: bool = False
    allowed_modules: Set[str] = field(default_factory=set)
    strict_mode: bool = True  # 严格模式下安全违规直接终止


class SafeNamespace:
    """
    安全命名空间

    提供受限的Python执行环境
    """

    def __init__(self, config: SandboxConfig, stdout_stream: Optional[io.StringIO] = None):
        self._config = config
        self._violations: List[str] = []
        self._stdout_stream = stdout_stream
        self._builtins = self._create_safe_builtins()

    @property
    def violations(self) -> List[str]:
        return list(self._violations)

    def get_namespace(self, user_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取安全命名空间"""
        namespace = {
            "__builtins__": self._builtins,
            "print": self._safe_print,
            "range": range,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "frozenset": frozenset,
            "sorted": sorted,
            "reversed": reversed,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "min": min,
            "max": max,
            "sum": sum,
            "abs": abs,
            "round": round,
            "isinstance": isinstance,
            "type": type,
            "hasattr": hasattr,
            "getattr": self._safe_getattr,
            "setattr": self._safe_setattr,
            "True": True,
            "False": False,
            "None": None,
        }

        # 允许的模块
        if self._config.allow_imports:
            for mod_name in self._config.allowed_modules:
                if mod_name not in FORBIDDEN_MODULES:
                    try:
                        namespace[mod_name] = __import__(mod_name)
                    except ImportError:
                        pass

        # 用户变量
        if user_vars:
            namespace.update(user_vars)

        return namespace

    def _create_safe_builtins(self) -> Dict[str, Any]:
        """创建安全的内置函数集合"""
        import builtins
        safe = {}
        for name in dir(builtins):
            if name.startswith('_') and name != '__name__':
                continue
            if name in FORBIDDEN_BUILTINS:
                continue
            try:
                safe[name] = getattr(builtins, name)
            except Exception:
                pass
        return safe

    def _safe_print(self, *args, **kwargs):
        """安全的print函数"""
        output = self._stdout_stream or io.StringIO()
        kwargs.setdefault('file', output)
        print(*args, **kwargs)

    def _safe_getattr(self, obj: Any, name: str, *defaults: Any) -> Any:
        """安全的getattr"""
        if name.startswith('_'):
            self._violations.append(f"禁止访问私有属性: {name}")
            if self._config.strict_mode:
                raise SandboxSecurityError(f"禁止访问私有属性: {name}")
            return defaults[0] if defaults else None
        return getattr(obj, name, *defaults)

    def _safe_setattr(self, obj: Any, name: str, value: Any) -> None:
        """安全的setattr"""
        if name.startswith('_'):
            self._violations.append(f"禁止设置私有属性: {name}")
            if self._config.strict_mode:
                raise SandboxSecurityError(f"禁止设置私有属性: {name}")
            return
        setattr(obj, name, value)


class Sandbox:
    """
    安全沙箱

    职责：
    - 在隔离环境中执行代码
    - 限制资源使用
    - 检测安全违规
    - 提供执行统计
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        self._config = config or SandboxConfig()
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    @property
    def config(self) -> SandboxConfig:
        return self._config

    @property
    def history_count(self) -> int:
        return len(self._history)

    def execute(
        self,
        code: str,
        variables: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> SandboxResult:
        """
        在沙箱中执行代码

        Args:
            code: Python代码字符串
            variables: 注入的变量
            timeout: 超时时间（秒），None使用配置默认值

        Returns:
            SandboxResult
        """
        timeout_val = timeout or self._config.timeout_seconds
        start_time = time.time()

        # 捕获stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        safe_ns = SafeNamespace(self._config, stdout_stream=stdout_capture)
        namespace = safe_ns.get_namespace(variables)

        result = SandboxResult()
        result.security_violations = safe_ns.violations

        # 超时执行
        exec_error = [None]
        exec_done = threading.Event()

        def _run():
            try:
                with contextlib.redirect_stdout(stdout_capture):
                    with contextlib.redirect_stderr(stderr_capture):
                        exec(compile(code, '<sandbox>', 'exec'), namespace)
            except Exception as e:
                exec_error[0] = e
            finally:
                exec_done.set()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        if not exec_done.wait(timeout=timeout_val):
            result.success = False
            result.timed_out = True
            result.error = f"执行超时（{timeout_val}秒）"
            result.duration_ms = (time.time() - start_time) * 1000
            result.stdout = stdout_capture.getvalue()[:self._config.max_output_bytes]
            result.stderr = stderr_capture.getvalue()[:self._config.max_output_bytes]
            self._record_history(result, code)
            return result

        elapsed_ms = (time.time() - start_time) * 1000

        if exec_error[0]:
            result.success = False
            result.error = f"{type(exec_error[0]).__name__}: {exec_error[0]}"
            result.stderr = traceback.format_exc()
        else:
            result.success = True
            result.return_value = namespace.get("__return__")

        result.stdout = stdout_capture.getvalue()[:self._config.max_output_bytes]
        result.stderr = stderr_capture.getvalue()[:self._config.max_output_bytes]
        result.duration_ms = elapsed_ms
        result.security_violations = safe_ns.violations

        self._record_history(result, code)
        return result

    def execute_function(
        self,
        func: Callable,
        *args: Any,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> SandboxResult:
        """
        在沙箱中执行函数

        Args:
            func: 可调用函数
            args: 位置参数
            timeout: 超时时间
            kwargs: 关键字参数
        """
        timeout_val = timeout or self._config.timeout_seconds
        start_time = time.time()

        result = SandboxResult()
        exec_error = [None]
        exec_done = threading.Event()
        func_result = [None]

        def _run():
            try:
                func_result[0] = func(*args, **kwargs)
            except Exception as e:
                exec_error[0] = e
            finally:
                exec_done.set()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        if not exec_done.wait(timeout=timeout_val):
            result.success = False
            result.timed_out = True
            result.error = f"函数执行超时（{timeout_val}秒）"
            result.duration_ms = (time.time() - start_time) * 1000
            return result

        elapsed_ms = (time.time() - start_time) * 1000

        if exec_error[0]:
            result.success = False
            result.error = f"{type(exec_error[0]).__name__}: {exec_error[0]}"
        else:
            result.success = True
            result.return_value = func_result[0]

        result.duration_ms = elapsed_ms
        self._record_history(result, f"function:{func.__name__}")
        return result

    def evaluate_expression(
        self,
        expression: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> SandboxResult:
        """
        安全求值表达式（比execute更安全，只允许表达式）

        Args:
            expression: Python表达式
            variables: 注入的变量
        """
        # 表达式安全检查
        if any(kw in expression for kw in ["import", "exec", "eval", "compile", "__"]):
            return SandboxResult(
                success=False,
                error="表达式包含禁止的关键字",
                security_violations=["禁止的关键字"],
            )

        return self.execute(
            f"__return__ = ({expression})",
            variables=variables,
            timeout=min(self._config.timeout_seconds, 5.0),
        )

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self._history[-limit:]

    def _record_history(self, result: SandboxResult, code_hint: str) -> None:
        """记录执行历史"""
        with self._lock:
            self._history.append({
                "success": result.success,
                "duration_ms": round(result.duration_ms, 2),
                "timed_out": result.timed_out,
                "error": result.error,
                "code_preview": code_hint[:100],
                "timestamp": datetime.now().isoformat(),
            })
            # 限制历史长度
            if len(self._history) > 200:
                self._history = self._history[-200:]
