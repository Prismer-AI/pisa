"""
Loop Registry

职责：
1. 管理所有已注册的 Loop
2. 提供 @agent 装饰器（简化命名）
3. 支持 Loop 的注册、查询和实例化
4. 支持自定义 Loop 的动态加载

使用示例：
```python
from pisa.core.loop import agent, BaseAgentLoop

@agent(name="my_custom_loop")
class MyCustomLoop(BaseAgentLoop):
    async def step(self, user_input: str):
        # 自定义实现
        pass
    
    async def run(self, user_input: str, max_iterations: int = 10):
        # 自定义运行逻辑
        pass
```
"""

from typing import Dict, Type, Any, Optional, Callable, List, Union
from pathlib import Path
import functools
import logging
import importlib
import importlib.util
import os

_logger = logging.getLogger(__name__)


class LoopRegistry:
    """
    Loop 注册表
    
    单例模式，管理所有已注册的 Loop
    """
    
    _instance: Optional['LoopRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loops: Dict[str, Type] = {}
            cls._instance._metadata: Dict[str, Dict[str, Any]] = {}
            _logger.info("LoopRegistry initialized")
        return cls._instance
    
    def register(
        self, 
        name: str, 
        loop_class: Type,
        description: Optional[str] = None,
        version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        注册 Loop
        
        Args:
            name: Loop 名称
            loop_class: Loop 类
            description: Loop 描述
            version: 版本号
            metadata: 额外的元数据
        
        Raises:
            ValueError: 如果 Loop 已经注册
        """
        if name in self._loops:
            _logger.warning(f"Loop '{name}' already registered, overwriting")
        
        self._loops[name] = loop_class
        self._metadata[name] = {
            'name': name,
            'class': loop_class.__name__,
            'module': loop_class.__module__,
            'description': description,
            'version': version,
            'metadata': metadata or {}
        }
        
        _logger.info(f"Registered loop: {name} ({loop_class.__name__})")
    
    def get(self, name: str) -> Optional[Type]:
        """
        获取 Loop 类
        
        Args:
            name: Loop 名称
            
        Returns:
            Loop 类，如果不存在返回 None
        """
        return self._loops.get(name)
    
    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取 Loop 元数据
        
        Args:
            name: Loop 名称
            
        Returns:
            Loop 元数据，如果不存在返回 None
        """
        return self._metadata.get(name)
    
    def list_loops(self) -> List[str]:
        """
        列出所有已注册的 Loop
        
        Returns:
            Loop 名称列表
        """
        return list(self._loops.keys())
    
    def list_all(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有 Loop 及其元数据
        
        Returns:
            Loop 名称到元数据的映射
        """
        return self._metadata.copy()
    
    def search(self, query: str) -> List[str]:
        """
        搜索 Loop
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的 Loop 名称列表
        """
        query_lower = query.lower()
        results = []
        
        for name, meta in self._metadata.items():
            if (query_lower in name.lower() or
                (meta.get('description') and query_lower in meta['description'].lower())):
                results.append(name)
        
        return results
    
    def unregister(self, name: str) -> bool:
        """
        注销 Loop
        
        Args:
            name: Loop 名称
            
        Returns:
            是否成功注销
        """
        if name in self._loops:
            del self._loops[name]
            del self._metadata[name]
            _logger.info(f"Unregistered loop: {name}")
            return True
        return False
    
    def clear(self) -> None:
        """清空所有注册的 Loop"""
        count = len(self._loops)
        self._loops.clear()
        self._metadata.clear()
        _logger.info(f"Cleared {count} loops")
    
    def discover_from_directory(
        self,
        directory: Union[str, Path],
        pattern: str = "*.py",
        recursive: bool = True
    ) -> List[str]:
        """
        从目录中发现并注册Loop模板
        
        Args:
            directory: 要扫描的目录
            pattern: 文件匹配模式（默认: *.py）
            recursive: 是否递归扫描子目录
            
        Returns:
            发现的Loop名称列表
        """
        directory = Path(directory)
        if not directory.exists():
            _logger.warning(f"Directory does not exist: {directory}")
            return []
        
        discovered = []
        
        for file_path in directory.rglob(pattern) if recursive else directory.glob(pattern):
            if file_path.is_file() and file_path.suffix == '.py' and file_path.name != '__init__.py':
                try:
                    # 转换文件路径为模块路径
                    relative_path = file_path.relative_to(directory)
                    module_name = str(relative_path.with_suffix('')).replace(os.sep, '.')
                    
                    # 尝试作为模块导入
                    spec = importlib.util.spec_from_file_location(
                        module_name,
                        file_path
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # 发现模块中的Loop类
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            # 检查是否是类且有__agent_metadata__属性（被@agent装饰）
                            if (isinstance(attr, type) and 
                                hasattr(attr, '__agent_metadata__')):
                                metadata = attr.__agent_metadata__
                                loop_name = metadata.get('name', attr_name)
                                
                                # 注册Loop
                                self.register(
                                    name=loop_name,
                                    loop_class=attr,
                                    description=metadata.get('description'),
                                    version=metadata.get('version', '1.0.0'),
                                    metadata=metadata
                                )
                                discovered.append(loop_name)
                                _logger.info(f"Discovered loop '{loop_name}' from {file_path}")
                
                except Exception as e:
                    _logger.warning(f"Failed to process {file_path}: {e}")
        
        return discovered
    
    def create_loop(
        self, 
        name: str, 
        context_manager: Any,
        capabilities: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        创建 Loop 实例
        
        Args:
            name: Loop 名称
            context_manager: 上下文管理器
            capabilities: Capability 字典
            config: 配置
            
        Returns:
            Loop 实例
            
        Raises:
            ValueError: 如果 Loop 不存在
        """
        loop_class = self.get(name)
        if loop_class is None:
            available = ', '.join(self.list_loops())
            raise ValueError(
                f"Loop '{name}' not found. Available loops: {available}"
            )
        
        _logger.debug(f"Creating loop instance: {name}")
        return loop_class(context_manager, capabilities, config)


# 全局注册表实例
_registry: Optional[LoopRegistry] = None


def get_loop_registry() -> LoopRegistry:
    """
    获取全局 Loop 注册表
    
    Returns:
        LoopRegistry 单例实例
    """
    global _registry
    if _registry is None:
        _registry = LoopRegistry()
    return _registry


def agent(
    name: str,
    description: Optional[str] = None,
    version: str = "1.0.0",
    auto_register: bool = True,
    registry: Optional[LoopRegistry] = None,
    **metadata
) -> Callable:
    """
    Agent Loop 装饰器
    
    用于注册自定义 Loop，简化命名为 @agent
    
    Args:
        name: Loop 名称
        description: Loop 描述
        version: 版本号
        auto_register: 是否自动注册（默认 True）
        registry: 自定义注册表（默认使用全局注册表）
        **metadata: 额外的元数据
        
    Returns:
        装饰器函数
        
    使用示例：
    ```python
    from pisa.core.loop import agent
    from pisa.core.loop.base import BaseAgentLoop
    
    @agent(name="my_custom_loop", description="My special loop")
    class MyCustomLoop(BaseAgentLoop):
        async def step(self, user_input: str):
            # 自定义步骤逻辑
            return message
        
        async def run(self, user_input: str, max_iterations: int = 10):
            # 自定义运行逻辑
            return messages
    ```
    """
    def decorator(cls: Type) -> Type:
        # 验证类继承
        # Note: 这里不强制检查继承，因为用户可能使用不同的基类
        
        # 添加元数据到类
        cls.__loop_name__ = name
        cls.__loop_description__ = description
        cls.__loop_version__ = version
        cls.__loop_metadata__ = metadata
        
        # 自动注册到 Registry
        if auto_register:
            reg = registry or get_loop_registry()
            reg.register(
                name=name,
                loop_class=cls,
                description=description,
                version=version,
                metadata=metadata
            )
            _logger.debug(f"Auto-registered loop: {name}")
        
        return cls
    
    return decorator
