"""
模块注册机制 - Module Registry

功能：
- 自动发现模块
- 依赖注入
- 生命周期管理
- 边界检查

公理溯源：
- 注册公理：模块通过注册中心管理，而非直接依赖
- 注入公理：依赖通过注入获得，而非主动获取
"""
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass
import importlib
import inspect

from module_interface import (
    IModule, ModuleInfo, ModuleState, ModulePriority, 
    HealthStatus, ModuleBoundary
)


class ModuleRegistry:
    """
    模块注册中心
    
    职责：
    1. 注册模块
    2. 解析依赖
    3. 初始化顺序
    4. 依赖注入
    5. 生命周期管理
    """
    
    def __init__(self):
        self._modules: Dict[str, IModule] = {}
        self._boundaries: Dict[str, ModuleBoundary] = {}
        self._interfaces: Dict[str, Type[IModule]] = {}
        self._initialized = False
    
    # ============================================================
    # 注册
    # ============================================================
    
    def register(self, module: IModule, boundary: Optional[ModuleBoundary] = None) -> bool:
        """
        注册模块
        
        Args:
            module: 模块实例
            boundary: 模块边界定义
            
        Returns:
            bool: 是否注册成功
        """
        name = module.info.name
        
        if name in self._modules:
            return False
        
        self._modules[name] = module
        
        if boundary:
            self._boundaries[name] = boundary
        
        return True
    
    def register_interface(self, name: str, interface: Type[IModule]) -> None:
        """
        注册接口类型
        
        Args:
            name: 接口名称
            interface: 接口类
        """
        self._interfaces[name] = interface
    
    def unregister(self, name: str) -> bool:
        """注销模块"""
        if name in self._modules:
            module = self._modules[name]
            module.shutdown()
            del self._modules[name]
            if name in self._boundaries:
                del self._boundaries[name]
            return True
        return False
    
    # ============================================================
    # 获取
    # ============================================================
    
    def get(self, name: str) -> Optional[IModule]:
        """获取模块"""
        return self._modules.get(name)
    
    def get_by_interface(self, interface: Type[IModule]) -> List[IModule]:
        """按接口类型获取模块"""
        return [m for m in self._modules.values() if isinstance(m, interface)]
    
    def get_all(self) -> Dict[str, IModule]:
        """获取所有模块"""
        return dict(self._modules)
    
    # ============================================================
    # 依赖解析
    # ============================================================
    
    def resolve_dependencies(self) -> List[str]:
        """
        解析依赖，返回初始化顺序
        
        使用拓扑排序，确保依赖先于被依赖初始化
        
        Returns:
            List[str]: 模块名称列表（按初始化顺序）
        """
        # 构建依赖图
        graph: Dict[str, List[str]] = {}
        for name, module in self._modules.items():
            graph[name] = module.info.dependencies
        
        # 拓扑排序
        visited = set()
        result = []
        
        def visit(name: str, path: set):
            if name in path:
                raise ValueError(f"检测到循环依赖: {path}")
            if name in visited:
                return
            path.add(name)
            for dep in graph.get(name, []):
                if dep in graph:
                    visit(dep, path)
            path.remove(name)
            visited.add(name)
            result.append(name)
        
        # 按优先级排序后遍历
        sorted_modules = sorted(
            self._modules.items(),
            key=lambda x: x[1].info.priority.value
        )
        
        for name, _ in sorted_modules:
            visit(name, set())
        
        return result
    
    # ============================================================
    # 初始化
    # ============================================================
    
    def initialize_all(self) -> Dict[str, bool]:
        """
        初始化所有模块
        
        Returns:
            Dict[str, bool]: 模块名 -> 是否成功
        """
        if self._initialized:
            return {name: True for name in self._modules}
        
        results = {}
        order = self.resolve_dependencies()
        
        for name in order:
            module = self._modules[name]
            
            # 构建上下文（已初始化的模块）
            context = {
                n: self._modules[n] 
                for n in results if results[n]
            }
            
            try:
                success = module.initialize(context)
                results[name] = success
            except Exception as e:
                results[name] = False
        
        self._initialized = True
        return results
    
    # ============================================================
    # 健康检查
    # ============================================================
    
    def health_check_all(self) -> Dict[str, HealthStatus]:
        """检查所有模块健康状态"""
        return {
            name: module.health_check()
            for name, module in self._modules.items()
        }
    
    def get_unhealthy(self) -> List[str]:
        """获取不健康的模块"""
        return [
            name for name, status in self.health_check_all().items()
            if not status.healthy
        ]
    
    # ============================================================
    # 关闭
    # ============================================================
    
    def shutdown_all(self) -> None:
        """关闭所有模块（逆序）"""
        order = self.resolve_dependencies()
        for name in reversed(order):
            if name in self._modules:
                self._modules[name].shutdown()
        self._initialized = False
    
    # ============================================================
    # 边界检查
    # ============================================================
    
    def validate_boundaries(self) -> Dict[str, List[str]]:
        """
        验证模块边界
        
        Returns:
            Dict[str, List[str]]: 模块名 -> 违规列表
        """
        violations = {}
        
        for name, boundary in self._boundaries.items():
            issues = []
            
            # 检查依赖是否存在
            for dep in boundary.dependencies:
                if dep not in self._modules:
                    issues.append(f"依赖不存在: {dep}")
            
            # 检查能力是否实现
            module = self._modules.get(name)
            if module:
                for cap in boundary.capabilities:
                    if not hasattr(module, cap):
                        issues.append(f"能力未实现: {cap}")
            
            if issues:
                violations[name] = issues
        
        return violations
    
    # ============================================================
    # 信息
    # ============================================================
    
    def info(self) -> Dict[str, Any]:
        """获取注册中心信息"""
        return {
            "module_count": len(self._modules),
            "initialized": self._initialized,
            "modules": {
                name: module.info.to_dict()
                for name, module in self._modules.items()
            },
            "boundaries": {
                name: boundary.to_dict()
                for name, boundary in self._boundaries.items()
            },
        }
    
    def list_modules(self) -> List[Dict[str, Any]]:
        """列出所有模块信息"""
        return [
            {
                "name": name,
                "state": module.state.value,
                "priority": module.info.priority.name,
                "dependencies": module.info.dependencies,
            }
            for name, module in sorted(
                self._modules.items(),
                key=lambda x: x[1].info.priority.value
            )
        ]


# ============================================================
# 全局注册中心
# ============================================================

_registry: Optional[ModuleRegistry] = None


def get_registry() -> ModuleRegistry:
    """获取全局注册中心"""
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry


def register_module(module: IModule, boundary: Optional[ModuleBoundary] = None) -> bool:
    """注册模块到全局注册中心"""
    return get_registry().register(module, boundary)


def get_module(name: str) -> Optional[IModule]:
    """从全局注册中心获取模块"""
    return get_registry().get(name)
