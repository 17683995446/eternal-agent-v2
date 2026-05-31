"""
插件系统模块

公理溯源：存续公理 - 系统可通过插件扩展能力而不修改核心代码

设计意图：
- 动态加载Python插件
- 插件生命周期管理（发现→加载→启用→禁用→卸载）
- 插件依赖解析
- 零外部依赖，仅使用importlib
"""

import importlib
import importlib.util
import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from exceptions import EternalAgentError


class PluginError(EternalAgentError):
    """插件系统异常"""
    pass


class PluginLoadError(PluginError):
    """插件加载异常"""
    pass


class PluginNotFoundError(PluginError):
    """插件未找到异常"""
    pass


class PluginDependencyError(PluginError):
    """插件依赖异常"""
    pass


@dataclass
class PluginInfo:
    """插件元信息"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class PluginInstance:
    """已加载的插件实例"""
    info: PluginInfo
    instance: Any
    module: Any
    loaded_at: str = ""
    hooks: Dict[str, Callable] = field(default_factory=dict)


class PluginBase:
    """
    插件基类

    所有插件必须继承此类并实现以下方法：
    - plugin_info() -> PluginInfo
    - on_load() -> None
    - on_unload() -> None
    """

    def plugin_info(self) -> PluginInfo:
        """返回插件元信息"""
        raise NotImplementedError("插件必须实现 plugin_info()")

    def on_load(self) -> None:
        """插件加载时调用"""
        pass

    def on_unload(self) -> None:
        """插件卸载时调用"""
        pass

    def on_enable(self) -> None:
        """插件启用时调用"""
        pass

    def on_disable(self) -> None:
        """插件禁用时调用"""
        pass


class PluginManager:
    """
    插件管理器

    职责：
    - 扫描插件目录
    - 加载/卸载插件
    - 管理插件生命周期
    - 解析插件依赖
    - 提供插件Hook注册
    """

    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        self._plugin_dirs = plugin_dirs or []
        self._plugins: Dict[str, PluginInstance] = {}
        self._hook_registry: Dict[str, List[Callable]] = {}
        self._load_order: List[str] = []

    @property
    def plugins(self) -> Dict[str, PluginInstance]:
        return dict(self._plugins)

    @property
    def plugin_names(self) -> List[str]:
        return list(self._load_order)

    def add_plugin_dir(self, path: Path) -> None:
        """添加插件搜索目录"""
        if path not in self._plugin_dirs:
            self._plugin_dirs.append(path)

    def discover(self) -> List[str]:
        """
        扫描插件目录，发现可用插件

        Returns:
            可用插件名称列表
        """
        discovered = []
        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.exists():
                continue
            for item in plugin_dir.iterdir():
                if item.is_file() and item.suffix == '.py' and item.name != '__init__.py':
                    module_name = item.stem
                    if module_name not in discovered:
                        discovered.append(module_name)
                elif item.is_dir() and (item / '__init__.py').exists():
                    if item.name not in discovered:
                        discovered.append(item.name)
        return discovered

    def load_plugin(self, name: str) -> PluginInstance:
        """
        加载指定插件

        Args:
            name: 插件名称

        Returns:
            PluginInstance

        Raises:
            PluginNotFoundError: 插件未找到
            PluginLoadError: 加载失败
            PluginDependencyError: 依赖未满足
        """
        if name in self._plugins:
            return self._plugins[name]

        module = self._find_module(name)
        if module is None:
            raise PluginNotFoundError(f"插件 '{name}' 未找到")

        # 查找插件类（继承PluginBase的类）
        plugin_class = self._find_plugin_class(module)
        if plugin_class is None:
            raise PluginLoadError(f"插件 '{name}' 中未找到 PluginBase 子类")

        # 实例化
        try:
            instance = plugin_class()
        except Exception as e:
            raise PluginLoadError(f"实例化插件 '{name}' 失败: {e}", cause=e)

        # 获取元信息
        info = instance.plugin_info()

        # 检查依赖
        for dep in info.dependencies:
            if dep not in self._plugins:
                raise PluginDependencyError(
                    f"插件 '{name}' 依赖 '{dep}'，但 '{dep}' 未加载"
                )

        # 调用 on_load
        try:
            instance.on_load()
        except Exception as e:
            raise PluginLoadError(f"插件 '{name}' on_load() 失败: {e}", cause=e)

        # 收集hooks
        hooks = self._collect_hooks(instance)

        from utils import now_iso
        plugin_inst = PluginInstance(
            info=info,
            instance=instance,
            module=module,
            loaded_at=now_iso(),
            hooks=hooks,
        )

        self._plugins[name] = plugin_inst
        self._load_order.append(name)

        # 注册hooks
        for hook_name, hook_fn in hooks.items():
            self.register_hook(hook_name, hook_fn)

        return plugin_inst

    def unload_plugin(self, name: str) -> bool:
        """
        卸载插件

        Args:
            name: 插件名称

        Returns:
            是否成功卸载
        """
        if name not in self._plugins:
            return False

        plugin_inst = self._plugins[name]

        # 先卸载依赖此插件的其他插件
        dependents = [
            n for n, p in self._plugins.items()
            if name in p.info.dependencies and n != name
        ]
        for dep_name in dependents:
            self.unload_plugin(dep_name)

        # 注销hooks
        for hook_name, hook_fn in plugin_inst.hooks.items():
            self.unregister_hook(hook_name, hook_fn)

        # 调用 on_unload
        try:
            plugin_inst.instance.on_unload()
        except Exception:
            pass  # 卸载时异常不阻断

        del self._plugins[name]
        self._load_order.remove(name)
        return True

    def enable_plugin(self, name: str) -> None:
        """启用插件"""
        if name not in self._plugins:
            raise PluginNotFoundError(f"插件 '{name}' 未加载")
        self._plugins[name].info.enabled = True
        self._plugins[name].instance.on_enable()

    def disable_plugin(self, name: str) -> None:
        """禁用插件"""
        if name not in self._plugins:
            raise PluginNotFoundError(f"插件 '{name}' 未加载")
        self._plugins[name].info.enabled = False
        self._plugins[name].instance.on_disable()

    def get_plugin(self, name: str) -> Optional[PluginInstance]:
        """获取插件实例"""
        return self._plugins.get(name)

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """注册Hook回调"""
        if hook_name not in self._hook_registry:
            self._hook_registry[hook_name] = []
        if callback not in self._hook_registry[hook_name]:
            self._hook_registry[hook_name].append(callback)

    def unregister_hook(self, hook_name: str, callback: Callable) -> None:
        """注销Hook回调"""
        if hook_name in self._hook_registry:
            self._hook_registry[hook_name] = [
                fn for fn in self._hook_registry[hook_name] if fn != callback
            ]

    def call_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> List[Any]:
        """
        调用Hook，返回所有回调的结果列表

        Args:
            hook_name: Hook名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            各回调返回值列表
        """
        results = []
        for callback in self._hook_registry.get(hook_name, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception:
                continue  # Hook异常不阻断
        return results

    def get_hooks_info(self) -> Dict[str, int]:
        """获取所有Hook信息"""
        return {name: len(cbs) for name, cbs in self._hook_registry.items()}

    def _find_module(self, name: str) -> Any:
        """查找插件模块"""
        for plugin_dir in self._plugin_dirs:
            py_file = plugin_dir / f"{name}.py"
            pkg_dir = plugin_dir / name / "__init__.py"

            if py_file.exists():
                spec = importlib.util.spec_from_file_location(name, str(py_file))
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[name] = module
                    spec.loader.exec_module(module)
                    return module

            if pkg_dir.exists():
                init_file = pkg_dir
                spec = importlib.util.spec_from_file_location(
                    f"{name}.__init__", str(init_file)
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[name] = module
                    spec.loader.exec_module(module)
                    return module

        return None

    def _find_plugin_class(self, module: Any) -> Optional[Type[PluginBase]]:
        """在模块中查找PluginBase子类"""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (inspect.isclass(attr) and
                    issubclass(attr, PluginBase) and
                    attr is not PluginBase):
                return attr
        return None

    def _collect_hooks(self, instance: Any) -> Dict[str, Callable]:
        """收集实例中以 hook_ 开头的方法"""
        hooks = {}
        for attr_name in dir(instance):
            if attr_name.startswith('hook_'):
                attr = getattr(instance, attr_name)
                if callable(attr):
                    hooks[attr_name] = attr
        return hooks

    def load_all(self) -> List[str]:
        """加载所有发现的插件"""
        discovered = self.discover()
        loaded = []
        for name in discovered:
            try:
                self.load_plugin(name)
                loaded.append(name)
            except PluginError:
                continue
        return loaded

    def unload_all(self) -> int:
        """卸载所有插件"""
        count = 0
        for name in list(self._load_order):
            if self.unload_plugin(name):
                count += 1
        return count
