"""
统一的注册表管理器

职责：
1. 统一管理 CapabilityRegistry 和 LoopRegistry
2. 提供统一的注册和查询接口
3. 协调 Capability 和 Loop 的交互
4. 支持自动扫描和注册
5. 管理 Agent Definition 模板
"""

from typing import Any, Dict, List, Optional, Union, Type
from pathlib import Path
import logging

from pisa.capability import get_global_registry as get_capability_registry, Capability
from pisa.core.loop.registry import get_loop_registry, LoopRegistry
from pisa.core.definition import AgentDefinition, parse_agent_definition
from pisa.core.loop.base import IAgentLoop

_logger = logging.getLogger(__name__)


class RegistryManager:
    """
    统一的注册表管理器
    
    整合 Capability 和 Loop 的注册、查询、管理功能。
    """
    
    _instance: Optional['RegistryManager'] = None
    
    def __init__(self):
        """初始化管理器"""
        self.capability_registry = get_capability_registry()
        self.loop_registry = get_loop_registry()
        
        # 模板路径管理
        self._template_paths = {
            'agent_templates': [],
            'capability_templates': []
        }
        
        _logger.info("RegistryManager initialized")
    
    @classmethod
    def get_instance(cls) -> 'RegistryManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    # ==================== Capability 管理 ====================
    
    def list_capabilities(
        self, 
        capability_type: Optional[str] = None
    ) -> List[Capability]:
        """
        列出所有 Capability
        
        Args:
            capability_type: 过滤类型 (function/agent/mcp)
            
        Returns:
            Capability 列表
        """
        # get_all() 返回字典 {name: Capability}
        capabilities = list(self.capability_registry.get_all().values())
        
        if capability_type:
            capabilities = [
                cap for cap in capabilities 
                if cap.capability_type == capability_type
            ]
        
        return capabilities
    
    def get_capability(self, name: str) -> Optional[Capability]:
        """
        获取 Capability
        
        Args:
            name: Capability 名称
            
        Returns:
            Capability 实例或 None
        """
        return self.capability_registry.get(name)
    
    def get_capability_function(self, name: str) -> Optional[callable]:
        """
        获取 Capability 的可调用函数
        
        Args:
            name: Capability 名称
            
        Returns:
            可调用函数或 None
        """
        return self.capability_registry.get_function(name)
    
    def search_capabilities(self, query: str) -> List[Capability]:
        """
        搜索 Capability
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的 Capability 列表
        """
        return self.capability_registry.search(query)
    
    def get_capabilities_by_type(self, capability_type: str) -> List[Capability]:
        """
        按类型获取 Capability
        
        Args:
            capability_type: 类型 (function/agent/mcp)
            
        Returns:
            Capability 列表
        """
        return self.list_capabilities(capability_type=capability_type)
    
    # ==================== Loop 管理 ====================
    
    def list_loops(self) -> List[Dict[str, Any]]:
        """
        列出所有 Loop
        
        Returns:
            Loop 信息列表（字典列表）
        """
        loops = []
        # list_all() 返回 {name: class}
        for loop_name, loop_class in self.loop_registry.list_all().items():
            loop_info = {
                'name': loop_name,
                'class': loop_class.__name__ if hasattr(loop_class, '__name__') else str(loop_class),
                'description': loop_class.__doc__.split('\n')[0] if loop_class.__doc__ else ''
            }
            loops.append(loop_info)
        
        return loops
    
    def get_loop(self, name: str) -> Optional[Type[IAgentLoop]]:
        """
        获取 Loop 类
        
        Args:
            name: Loop 名称
            
        Returns:
            Loop 类或 None
        """
        return self.loop_registry.get(name)
    
    def search_loops(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索 Loop
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的 Loop 信息列表
        """
        return self.loop_registry.search(query)
    
    # ==================== Agent Definition 管理 ====================
    
    def register_agent_template_path(self, path: Union[str, Path]) -> None:
        """
        注册 Agent 模板路径
        
        Args:
            path: 模板目录或文件路径
        """
        path = Path(path)
        if path not in self._template_paths['agent_templates']:
            self._template_paths['agent_templates'].append(path)
            _logger.info(f"Registered agent template path: {path}")
    
    def register_capability_template_path(self, path: Union[str, Path]) -> None:
        """
        注册 Capability 模板路径
        
        Args:
            path: 模板目录或文件路径
        """
        path = Path(path)
        if path not in self._template_paths['capability_templates']:
            self._template_paths['capability_templates'].append(path)
            _logger.info(f"Registered capability template path: {path}")
    
    def list_agent_templates(self) -> List[Path]:
        """
        列出所有 Agent 模板
        
        Returns:
            模板文件路径列表
        """
        templates = []
        for template_path in self._template_paths['agent_templates']:
            if template_path.is_file():
                templates.append(template_path)
            elif template_path.is_dir():
                templates.extend(template_path.glob("**/*.md"))
        
        return templates
    
    def list_capability_templates(self) -> List[Path]:
        """
        列出所有 Capability 模板
        
        Returns:
            模板文件路径列表
        """
        templates = []
        for template_path in self._template_paths['capability_templates']:
            if template_path.is_file():
                templates.append(template_path)
            elif template_path.is_dir():
                templates.extend(template_path.glob("**/*.py"))
        
        return templates
    
    def load_agent_definition(
        self, 
        path: Union[str, Path]
    ) -> AgentDefinition:
        """
        加载 Agent 定义
        
        Args:
            path: agent.md 文件路径
            
        Returns:
            AgentDefinition 实例
        """
        return parse_agent_definition(path)
    
    # ==================== Agent 创建 ====================
    
    def create_agent(
        self, 
        agent_definition_path: Union[str, Path],
        auto_validate: bool = True,
        auto_initialize: bool = True,
        **kwargs
    ) -> IAgentLoop:
        """
        从定义文件创建 Agent 实例（完整流程）
        
        执行完整的 Agent 创建流程：
        1. 解析定义文件 (agent.md)
        2. 验证引用 (loop_type, capabilities)
        3. 解析能力引用 (名称 → 对象)
        4. 创建模块配置
        5. 实例化 Loop
        6. 绑定组件
        
        Args:
            agent_definition_path: agent.md 文件路径
            auto_validate: 是否自动验证引用
            auto_initialize: 是否自动初始化组件
            **kwargs: 额外的配置参数
            
        Returns:
            Agent Loop 实例
            
        Raises:
            ValueError: 引用验证失败
            FileNotFoundError: 定义文件不存在
        """
        _logger.info(f"Creating agent from: {agent_definition_path}")
        
        # ===== 步骤 1: 加载定义 =====
        agent_def = self.load_agent_definition(agent_definition_path)
        _logger.info(f"Loaded definition: {agent_def.metadata.name}")
        
        # ===== 步骤 2: 验证引用 =====
        if auto_validate:
            validation_result = self._validate_agent_definition(agent_def)
            if not validation_result['valid']:
                error_msg = "\n".join([
                    "Agent definition validation failed:",
                    *[f"  - {err}" for err in validation_result['errors']]
                ])
                _logger.error(error_msg)
                raise ValueError(error_msg)
            
            if validation_result['warnings']:
                for warning in validation_result['warnings']:
                    _logger.warning(f"Validation warning: {warning}")
        
        # ===== 步骤 3: 获取 Loop 类 =====
        loop_class = self.get_loop(agent_def.loop_type)
        if loop_class is None:
            raise ValueError(
                f"Loop type '{agent_def.loop_type}' not found. "
                f"Available: {list(self.loop_registry.list_all().keys())}"
            )
        
        # ===== 步骤 4: 直接使用 AgentDefinition (跳过 LoopDefinition 转换) =====
        # loop_definition = agent_def.to_loop_definition()  # 已废弃
        
        # ===== 步骤 5: 解析能力引用 (名称 → 对象) =====
        capability_names = agent_def.get_capability_names()
        resolved_capabilities = self._resolve_capability_references(
            capability_names
        )
        _logger.info(
            f"Resolved {len(resolved_capabilities)} capabilities"
        )
        
        # ===== 步骤 6: 创建模块配置 =====
        from pisa.core.loop.modules import (
            PlanningModuleConfig,
            ExecutionModuleConfig,
            ReflectionModuleConfig,
            ValidationModuleConfig
        )
        
        # 从 AgentDefinition 提取模块配置
        planning_config = None
        if hasattr(agent_def, 'planning_config') and agent_def.planning_config:
            planning_config = PlanningModuleConfig(
                **agent_def.planning_config.model_dump()
            )
        
        execution_config = None
        if hasattr(agent_def, 'execution_config') and agent_def.execution_config:
            execution_config = ExecutionModuleConfig(
                **agent_def.execution_config.model_dump()
            )
        
        reflection_config = None
        if hasattr(agent_def, 'reflection_config') and agent_def.reflection_config:
            reflection_config = ReflectionModuleConfig(
                **agent_def.reflection_config.model_dump()
            )
        
        validation_config = None
        if hasattr(agent_def, 'validation_config') and agent_def.validation_config:
            validation_config = ValidationModuleConfig(
                **agent_def.validation_config.model_dump()
            )
        
        # ===== 步骤 7: 实例化 Loop =====
        # BaseAgentLoop 会自己创建 LoopContext，所以不需要显式创建 ContextManager
        agent = loop_class(
            definition=agent_def,  # 传递完整的 AgentDefinition
            # 不再传递这些参数，让 BaseAgentLoop 从 definition 中提取
            # name=agent_def.metadata.name,
            # instructions=agent_def.system_prompt,
            # model=agent_def.models.default_model,
            # capabilities=resolved_capabilities,
            # capability_registry=self.capability_registry,
            **kwargs
        )
        
        _logger.info(f"✅ Agent created: {agent_def.metadata.name}")
        return agent
    
    def _validate_agent_definition(self, agent_def: AgentDefinition) -> Dict[str, Any]:
        """
        验证 Agent 定义的有效性
        
        Args:
            agent_def: AgentDefinition 实例
            
        Returns:
            验证结果字典
        """
        errors = []
        warnings = []
        
        # 1. 验证 loop_type 存在
        if not self.get_loop(agent_def.loop_type):
            available_loops = list(self.loop_registry.list_all().keys())
            errors.append(
                f"Loop type '{agent_def.loop_type}' not found. "
                f"Available: {available_loops}"
            )
        
        # 2. 验证 capabilities 存在
        for cap_ref in agent_def.capabilities:
            cap_name = cap_ref.name if hasattr(cap_ref, 'name') else str(cap_ref)
            if not self.get_capability(cap_name):
                errors.append(
                    f"Capability '{cap_name}' not found in registry"
                )
        
        # 3. 验证模型配置
        # AgentDefinition 使用 models 字段（ModelConfig 类型）
        if hasattr(agent_def, 'models'):
            if not agent_def.models or not agent_def.models.default_model:
                warnings.append("No default model specified")
        else:
            warnings.append("No model configuration found")
        
        # 4. 验证运行时配置
        if hasattr(agent_def, 'runtime_config'):
            runtime = agent_def.runtime_config
            if hasattr(runtime, 'max_iterations') and runtime.max_iterations <= 0:
                warnings.append("max_iterations should be > 0")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _resolve_capability_references(
        self, 
        capability_refs: List[Union[str, Any]]
    ) -> List[str]:
        """
        解析能力引用（保持名称列表，供 Loop 使用）
        
        Args:
            capability_refs: 能力引用列表（字符串或对象）
            
        Returns:
            能力名称列表
        """
        resolved = []
        
        for ref in capability_refs:
            # 提取名称
            if isinstance(ref, str):
                cap_name = ref
            elif hasattr(ref, 'name'):
                cap_name = ref.name
            else:
                cap_name = str(ref)
            
            # 验证存在性
            if self.get_capability(cap_name):
                resolved.append(cap_name)
            else:
                _logger.warning(f"Capability '{cap_name}' not found, skipping")
        
        return resolved
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取注册表统计信息
        
        Returns:
            统计信息字典
        """
        capabilities = self.list_capabilities()
        loops = self.list_loops()
        
        # 智能分类：根据 tags 而不是 capability_type
        # 因为所有 capabilities 在 SDK 层都是 FunctionTool，但逻辑上可以分类
        def get_logical_type(cap):
            """根据 tags 确定逻辑类型"""
            tags = getattr(cap, 'tags', [])
            if 'mcp' in tags:
                return 'mcp'
            elif 'subagent' in tags:
                return 'agent'
            else:
                return 'function'
        
        type_counts = {'function': 0, 'agent': 0, 'mcp': 0}
        for cap in capabilities:
            logical_type = get_logical_type(cap)
            type_counts[logical_type] += 1
        
        return {
            "capabilities": {
                "total": len(capabilities),
                "by_type": type_counts
            },
            "loops": {
                "total": len(loops),
                "list": loops  # 与 startup.py 保持一致
            },
            "templates": {
                "agent_paths": len(self._template_paths['agent_templates']),
                "capability_paths": len(self._template_paths['capability_templates']),
                "agent_templates": len(self.list_agent_templates()),
                "capability_templates": len(self.list_capability_templates())
            }
        }
    
    def display_statistics(self) -> None:
        """展示统计信息（使用 Rich）"""
        from rich.console import Console
        from rich.table import Table
        from rich import box
        
        console = Console()
        stats = self.get_statistics()
        
        # 创建表格
        table = Table(
            title="🗂️  PISA Registry Statistics",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Category", style="cyan", width=25)
        table.add_column("Metric", style="white", width=30)
        table.add_column("Value", style="yellow", justify="right")
        
        # Capabilities
        table.add_row(
            "Capabilities",
            "Total",
            str(stats['capabilities']['total'])
        )
        for cap_type, count in stats['capabilities']['by_type'].items():
            table.add_row(
                "",
                f"  - {cap_type}",
                str(count)
            )
        
        # Loops
        table.add_row(
            "Agent Loops",
            "Total",
            str(stats['loops']['total'])
        )
        for loop_name in stats['loops']['names']:
            table.add_row(
                "",
                f"  - {loop_name}",
                "✓"
            )
        
        # Templates
        table.add_row(
            "Templates",
            "Agent Template Paths",
            str(stats['templates']['agent_paths'])
        )
        table.add_row(
            "",
            "Agent Templates",
            str(stats['templates']['agent_templates'])
        )
        table.add_row(
            "",
            "Capability Templates",
            str(stats['templates']['capability_templates'])
        )
        
        console.print("\n")
        console.print(table)
        console.print("\n")


# ==================== 全局访问函数 ====================

_global_manager: Optional[RegistryManager] = None


def get_registry_manager() -> RegistryManager:
    """获取全局 RegistryManager 实例"""
    global _global_manager
    if _global_manager is None:
        _global_manager = RegistryManager.get_instance()
    return _global_manager


def reset_registry_manager() -> None:
    """重置全局 RegistryManager（主要用于测试）"""
    global _global_manager
    _global_manager = None
