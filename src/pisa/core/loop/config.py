"""
Loop Configuration

职责：
1. 定义LoopConfig模型（统一的Loop配置）
2. 支持模块启用/禁用
3. 支持从AgentDefinition加载配置
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from pisa.core.loop.modules.base import (
    ModuleConfig,
    PlanningModuleConfig,
    ExecutionModuleConfig,
    ReflectionModuleConfig,
    ValidationModuleConfig,
    ObserveModuleConfig,
)
from pisa.core.definition.models import AgentDefinition
from pisa.config import Config


class ContextConfig(BaseModel):
    """Context配置"""
    max_tokens: int = Field(default=100000, description="最大token数")
    compression_threshold: float = Field(default=0.8, description="压缩阈值")
    compression_strategy: str = Field(default="adaptive", description="压缩策略")
    enable_compression: bool = Field(default=True, description="是否启用压缩")


class ObservabilityConfig(BaseModel):
    """可观测性配置"""
    enabled: bool = Field(default=True, description="是否启用")
    log_level: str = Field(default="INFO", description="日志级别")
    show_context: bool = Field(default=True, description="是否显示context")
    show_state: bool = Field(default=True, description="是否显示state")


class LoopConfig(BaseModel):
    """
    Loop统一配置
    
    从definition或kwargs加载，自动构建所有模块配置
    """
    name: str = Field(description="Loop名称")
    model: str = Field(default_factory=lambda: Config.agent_default_model)
    max_iterations: int = Field(default=10, description="最大迭代次数")
    
    # Capabilities
    capabilities: List[str] = Field(default_factory=list, description="Capability 名称列表")
    
    # 子配置
    context: ContextConfig = Field(default_factory=ContextConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    
    # 模块配置
    modules: Dict[str, ModuleConfig] = Field(default_factory=dict)
    enabled_modules: Dict[str, bool] = Field(default_factory=dict)
    
    @classmethod
    def from_definition(
        cls,
        definition: AgentDefinition,
        **overrides
    ) -> "LoopConfig":
        """
        从AgentDefinition创建LoopConfig
        
        Args:
            definition: Agent定义
            **overrides: 覆盖的配置
            
        Returns:
            LoopConfig实例
        """
        # 基础配置
        default_model = definition.models.default_model or "gpt-4"
        config_dict = {
            "name": definition.metadata.name,
            "model": default_model,
            "max_iterations": definition.runtime_config.max_iterations,
            "capabilities": definition.get_capability_names(),  # 🔥 添加 capabilities
        }
        
        # Context配置
        if definition.context_config:
            config_dict["context"] = {
                "max_tokens": definition.context_config.max_tokens,
                "compression_threshold": definition.context_config.compression_threshold,
                "compression_strategy": definition.context_config.compression_strategy,
                "enable_compression": definition.context_config.compression_enabled,
            }
        
        # Observability配置
        if definition.observability_config:
            config_dict["observability"] = {
                "enabled": definition.observability_config.enable_logging,
                "log_level": definition.observability_config.log_level,
                "show_context": True,  # 默认值
                "show_state": True,    # 默认值
            }
        
        # 模块配置
        modules_dict = {}
        enabled_dict = {}
        
        # Planning配置
        if definition.planning_config:
            modules_dict["planning"] = PlanningModuleConfig(
                model=definition.models.planning_model or default_model,
                instructions=definition.planning_config.planning_instructions or "",
            )
            enabled_dict["planning"] = definition.planning_config.enabled
        
        # Execution配置（默认启用）
        modules_dict["execution"] = ExecutionModuleConfig(
            model=definition.models.execution_model or default_model,
        )
        enabled_dict["execution"] = True
        
        # Reflection配置（默认启用）
        modules_dict["reflection"] = ReflectionModuleConfig(
            model=definition.models.reflection_model or default_model,
        )
        enabled_dict["reflection"] = definition.runtime_config.enable_reflection
        
        # Observe配置（默认启用）
        modules_dict["observe"] = ObserveModuleConfig(
            model=getattr(definition.models, 'observe_model', None) or default_model,
        )
        enabled_dict["observe"] = True
        
        # Validation配置（如果有validation规则）
        if definition.validation_rules:
            modules_dict["validation"] = ValidationModuleConfig(
                model=definition.models.validation_model or default_model,
            )
            enabled_dict["validation"] = definition.runtime_config.enable_validation
        
        config_dict["modules"] = modules_dict
        config_dict["enabled_modules"] = enabled_dict
        
        # 应用覆盖
        config_dict.update(overrides)
        
        return cls(**config_dict)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "LoopConfig":
        """
        从字典创建LoopConfig
        
        Args:
            config_dict: 配置字典
            
        Returns:
            LoopConfig实例
        """
        # 设置默认值
        if "name" not in config_dict:
            config_dict["name"] = "default_loop"
        
        # 设置默认模块
        if "enabled_modules" not in config_dict:
            config_dict["enabled_modules"] = {
                "planning": True,
                "execution": True,
                "reflection": True,
                "observe": True,
            }
        
        if "modules" not in config_dict:
            default_model = config_dict.get("model", Config.agent_default_model)
            config_dict["modules"] = {
                "planning": PlanningModuleConfig(model=default_model),
                "execution": ExecutionModuleConfig(model=default_model),
                "reflection": ReflectionModuleConfig(model=default_model),
                "observe": ObserveModuleConfig(model=default_model),
            }
        
        return cls(**config_dict)
    
    def is_module_enabled(self, module_name: str) -> bool:
        """
        检查模块是否启用
        
        Args:
            module_name: 模块名称
            
        Returns:
            是否启用
        """
        return self.enabled_modules.get(module_name, False)
    
    def get_module_config(self, module_name: str) -> Optional[ModuleConfig]:
        """
        获取模块配置
        
        Args:
            module_name: 模块名称
            
        Returns:
            模块配置（如果存在）
        """
        return self.modules.get(module_name)



