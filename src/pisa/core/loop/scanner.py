"""
Agent Loop Scanner

职责：
1. 自动扫描指定目录下的 Loop 定义
2. 发现使用 @agent 装饰的类
3. 自动注册到 LoopRegistry
4. 支持扫描多个目录

扫描流程：
1. 遍历指定目录
2. 导入所有 Python 模块
3. 检查是否有 @agent 装饰的类
4. 自动注册到 LoopRegistry

注意：
- @agent 装饰器定义的是 Loop 模板（框架层）
- @capability(capability_type="agent") 定义的是 sub-agent（执行层）
"""

from pathlib import Path
from typing import List, Union, Optional
import importlib.util
import inspect
import logging
import sys

from .registry import get_loop_registry, LoopRegistry

_logger = logging.getLogger(__name__)


class AgentScanner:
    """
    Agent Loop 扫描器
    
    自动发现和注册使用 @agent 装饰的 Loop 类
    """
    
    def __init__(self, registry: Optional[LoopRegistry] = None):
        """
        初始化扫描器
        
        Args:
            registry: 自定义注册表（默认使用全局注册表）
        """
        self.registry = registry or get_loop_registry()
        self._scanned_modules: set = set()
        _logger.info("AgentScanner initialized")
    
    def scan_directory(
        self, 
        directory: Union[str, Path],
        pattern: str = "*.py",
        recursive: bool = True
    ) -> List[str]:
        """
        扫描目录，发现所有 @agent 装饰的 Loop 类
        
        Args:
            directory: 要扫描的目录路径
            pattern: 文件模式（默认 "*.py"）
            recursive: 是否递归扫描子目录（默认 True）
            
        Returns:
            发现的 Loop 名称列表
        """
        directory = Path(directory)
        if not directory.exists():
            _logger.warning(f"Directory does not exist: {directory}")
            return []
        
        if not directory.is_dir():
            _logger.warning(f"Path is not a directory: {directory}")
            return []
        
        discovered = []
        
        # 获取所有 Python 文件
        if recursive:
            py_files = directory.rglob(pattern)
        else:
            py_files = directory.glob(pattern)
        
        for py_file in py_files:
            if not py_file.is_file():
                continue
            
            try:
                # 构建模块名
                relative_path = py_file.relative_to(directory)
                module_name = str(relative_path.with_suffix('')).replace('/', '.').replace('\\', '.')
                
                # 加载模块
                loops = self._scan_file(py_file, module_name)
                discovered.extend(loops)
                
            except Exception as e:
                _logger.warning(f"Failed to scan {py_file}: {e}")
        
        _logger.info(f"Discovered {len(discovered)} loops in {directory}")
        return discovered
    
    def scan_module(self, module_path: str) -> List[str]:
        """
        扫描单个 Python 模块
        
        Args:
            module_path: 模块路径（如 'pisa.core.loop.templates.react'）
            
        Returns:
            发现的 Loop 名称列表
        """
        if module_path in self._scanned_modules:
            _logger.debug(f"Module already scanned: {module_path}")
            return []
        
        try:
            # 导入模块
            module = importlib.import_module(module_path)
            self._scanned_modules.add(module_path)
            
            # 扫描模块中的类
            discovered = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                # 检查是否为 Loop 类
                if self._is_loop_class(attr):
                    loop_name = getattr(attr, '__loop_name__', attr_name)
                    
                    # 检查是否已注册（@agent 装饰器会自动注册）
                    if self.registry.get(loop_name) is None:
                        # 如果未注册，手动注册
                        description = getattr(attr, '__loop_description__', None)
                        version = getattr(attr, '__loop_version__', '1.0.0')
                        metadata = getattr(attr, '__loop_metadata__', {})
                        
                        self.registry.register(
                            name=loop_name,
                            loop_class=attr,
                            description=description,
                            version=version,
                            metadata=metadata
                        )
                    
                    discovered.append(loop_name)
                    _logger.debug(f"Discovered loop '{loop_name}' from {module_path}")
            
            return discovered
            
        except Exception as e:
            _logger.error(f"Failed to scan module {module_path}: {e}")
            return []
    
    def _scan_file(self, file_path: Path, module_name: str) -> List[str]:
        """
        扫描单个 Python 文件
        
        Args:
            file_path: 文件路径
            module_name: 模块名称
            
        Returns:
            发现的 Loop 名称列表
        """
        try:
            # 动态加载模块
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                _logger.warning(f"Could not load spec for {file_path}")
                return []
            
            module = importlib.util.module_from_spec(spec)
            
            # 添加到 sys.modules 以避免重复导入
            sys.modules[module_name] = module
            
            # 执行模块
            spec.loader.exec_module(module)
            
            # 扫描模块中的类
            discovered = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                if self._is_loop_class(attr):
                    loop_name = getattr(attr, '__loop_name__', attr_name)
                    
                    # @agent 装饰器会自动注册，这里只是收集名称
                    if self.registry.get(loop_name):
                        discovered.append(loop_name)
                        _logger.debug(f"Found loop '{loop_name}' in {file_path}")
            
            return discovered
            
        except Exception as e:
            _logger.warning(f"Error scanning file {file_path}: {e}")
            return []
    
    def _is_loop_class(self, obj: any) -> bool:
        """
        检查对象是否为 @agent 装饰的 Loop 类
        
        Args:
            obj: 要检查的对象
            
        Returns:
            是否为 Loop 类
        """
        return (
            inspect.isclass(obj) and
            hasattr(obj, '__loop_name__') and
            hasattr(obj, '__loop_description__')
        )
    
    def auto_scan(
        self, 
        directories: List[Union[str, Path]],
        pattern: str = "*.py",
        recursive: bool = True
    ) -> List[str]:
        """
        自动扫描多个目录并注册所有发现的 Loop
        
        Args:
            directories: 目录列表
            pattern: 文件模式（默认 "*.py"）
            recursive: 是否递归扫描（默认 True）
            
        Returns:
            所有发现的 Loop 名称列表
        """
        all_discovered = []
        
        for directory in directories:
            _logger.info(f"Scanning directory: {directory}")
            discovered = self.scan_directory(directory, pattern, recursive)
            all_discovered.extend(discovered)
        
        _logger.info(f"Total discovered loops: {len(all_discovered)}")
        return all_discovered
    
    def scan_builtin_loops(self) -> List[str]:
        """
        扫描内置的 Loop 模板
        
        Returns:
            发现的内置 Loop 名称列表
        """
        builtin_modules = [
            'pisa.core.loop.templates.react',
            'pisa.core.loop.templates.reflex',
            'pisa.core.loop.templates.reflexion',
            'pisa.core.loop.templates.plan_execute',
        ]
        
        all_discovered = []
        for module_path in builtin_modules:
            try:
                discovered = self.scan_module(module_path)
                all_discovered.extend(discovered)
            except Exception as e:
                _logger.warning(f"Failed to scan builtin module {module_path}: {e}")
        
        return all_discovered
    
    def get_statistics(self) -> dict:
        """
        获取扫描统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'total_loops': len(self.registry.list_loops()),
            'scanned_modules': len(self._scanned_modules),
            'loops': self.registry.list_all()
        }

