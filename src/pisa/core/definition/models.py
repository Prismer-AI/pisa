"""
Definition Models

定义层的数据模型，对应 agent.md 的结构化表示。

参考 PISA2.md 中的定义层设计。
"""

from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


# 移除硬编码的 AgentLoopType 枚举
# Loop 类型应该从 LoopRegistry 动态获取，而不是硬编码在这里
# 现在 loop_type 是一个普通的字符串，由 LoopRegistry 验证


class AgentMetadata(BaseModel):
    """Agent 元信息"""
    name: str = Field(..., description="Agent 名称")
    version: str = Field(default="1.0.0", description="版本号")
    description: Optional[str] = Field(None, description="Agent 描述")
    author: Optional[str] = Field(None, description="作者")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, description="更新时间")
    tags: List[str] = Field(default_factory=list, description="标签")


class CapabilityReference(BaseModel):
    """
    Capability 引用（已弃用，保留用于向后兼容）
    
    ⚠️ 现在推荐直接使用字符串列表：capabilities: List[str]
    完整定义会从 capability registry 自动查询。
    """
    name: str = Field(..., description="Capability 名称")
    enabled: bool = Field(default=True, description="是否启用")
    config: Dict[str, Any] = Field(default_factory=dict, description="Capability 特定配置")
    alias: Optional[str] = Field(None, description="别名")
    description: Optional[str] = Field(None, description="使用说明")


class ModelConfig(BaseModel):
    """模型配置"""
    default_model: Optional[str] = Field(None, description="默认模型")
    planning_model: Optional[str] = Field(None, description="规划模型")
    execution_model: Optional[str] = Field(None, description="执行模型")
    reflection_model: Optional[str] = Field(None, description="反思模型")
    validation_model: Optional[str] = Field(None, description="验证模型")
    observe_model: Optional[str] = Field(None, description="观察模型")
    temperature: float = Field(default=0.7, description="Temperature")
    max_tokens: Optional[int] = Field(None, description="最大 tokens")
    top_p: float = Field(default=1.0, description="Top P")


class PlanningConfig(BaseModel):
    """规划配置"""
    enabled: bool = Field(default=True, description="是否启用规划")
    max_iterations: int = Field(default=10, description="最大规划迭代")
    enable_replanning: bool = Field(default=True, description="是否启用重新规划")
    planning_instructions: Optional[str] = Field(None, description="规划指令")
    replanning_instructions: Optional[str] = Field(None, description="重规划指令")
    planning_strategy: str = Field(default="hierarchical", description="规划策略")


class ValidationRule(BaseModel):
    """验证规则"""
    name: str = Field(..., description="规则名称")
    type: str = Field(..., description="规则类型: input/output/safety")
    enabled: bool = Field(default=True, description="是否启用")
    config: Dict[str, Any] = Field(default_factory=dict, description="规则配置")
    description: Optional[str] = Field(None, description="规则描述")


class ContextConfig(BaseModel):
    """Context 配置"""
    max_tokens: int = Field(default=100000, description="最大 tokens")
    compression_enabled: bool = Field(default=True, description="是否启用压缩")
    compression_strategy: str = Field(default="adaptive", description="压缩策略")
    compression_threshold: float = Field(default=0.8, description="压缩阈值")
    persist_to_file: bool = Field(default=True, description="是否持久化到文件")
    context_file: str = Field(default="context.md", description="Context 文件名")


class ObservabilityConfig(BaseModel):
    """可观测性配置"""
    enable_logging: bool = Field(default=True, description="是否启用日志")
    log_level: str = Field(default="INFO", description="日志级别")
    enable_metrics: bool = Field(default=True, description="是否启用指标")
    enable_tracing: bool = Field(default=True, description="是否启用追踪")
    enable_rich_output: bool = Field(default=True, description="是否启用 Rich 输出")
    enable_debug: bool = Field(default=False, description="是否启用调试模式")


class RuntimeConfig(BaseModel):
    """运行时配置"""
    max_iterations: int = Field(default=10, description="最大迭代次数（外层循环）")
    timeout_seconds: Optional[int] = Field(None, description="超时时间")
    enable_reflection: bool = Field(default=True, description="是否启用反思")
    enable_validation: bool = Field(default=True, description="是否启用验证")
    enable_replanning: bool = Field(default=True, description="是否启用重新规划")
    parallel_execution: bool = Field(default=False, description="是否并行执行")
    
    # ⭐ SDK Agent 的 max_turns 配置（内层循环）
    max_turns_planning: int = Field(default=2, description="Planning Agent 最大 turns")
    max_turns_execution: int = Field(default=3, description="Execution Agent 最大 turns")
    max_turns_observation: int = Field(default=2, description="Observation Agent 最大 turns")
    max_turns_reflection: int = Field(default=2, description="Reflection Agent 最大 turns")


class AgentDefinition(BaseModel):
    """
    完整 Agent 定义 (agent.md 的结构化表示)
    
    这是定义层的核心模型，从 agent.md 解析得到。
    """
    # 元信息
    metadata: AgentMetadata
    
    # Loop 类型（字符串，由 LoopRegistry 验证）
    loop_type: str = Field(..., description="Loop 类型，必须是已注册的 loop 名称")
    
    # 系统提示词
    system_prompt: str = Field(..., description="系统提示词")
    
    # ⭐ 简化：支持字符串列表（推荐）或 CapabilityReference 列表（向后兼容）
    capabilities: Union[List[str], List[CapabilityReference]] = Field(
        default_factory=list,
        description="Capability 名称列表（推荐）或引用列表（向后兼容）"
    )
    
    # 模型配置
    models: ModelConfig = Field(default_factory=ModelConfig, description="模型配置")
    
    # 规划配置
    planning_config: Optional[PlanningConfig] = Field(None, description="规划配置")
    
    # 验证规则
    validation_rules: List[ValidationRule] = Field(
        default_factory=list,
        description="验证规则列表"
    )
    
    # Context 配置
    context_config: ContextConfig = Field(
        default_factory=ContextConfig,
        description="Context 配置"
    )
    
    # 可观测性配置
    observability_config: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig,
        description="可观测性配置"
    )
    
    # 运行时配置
    runtime_config: RuntimeConfig = Field(
        default_factory=RuntimeConfig,
        description="运行时配置"
    )
    
    # 背景信息
    background_info: Optional[str] = Field(None, description="背景信息")
    
    # 额外配置
    extra_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="额外配置"
    )
    
    class Config:
        extra = "allow"
    
    def get_capability_names(self) -> List[str]:
        """
        获取capability名称列表
        
        兼容两种格式：
        1. List[str] - 直接返回
        2. List[CapabilityReference] - 提取name字段（仅enabled=True的）
        
        Returns:
            Capability名称列表
        """
        if not self.capabilities:
            return []
        
        # 检查第一个元素的类型
        first = self.capabilities[0]
        
        if isinstance(first, str):
            # 新格式：字符串列表
            return self.capabilities
        elif isinstance(first, CapabilityReference):
            # 旧格式：CapabilityReference列表
            return [cap.name for cap in self.capabilities if cap.enabled]
        else:
            # 未知格式，尝试转换
            return [str(cap) for cap in self.capabilities]
    
    def to_loop_definition(self):
        """
        转换为 LoopDefinition (已废弃，LoopDefinition 类不存在)
        
        Returns:
            None
        """
        # TODO: LoopDefinition 类已被移除，此方法需要重新实现或删除
        import warnings
        warnings.warn(
            "to_loop_definition() is deprecated as LoopDefinition class no longer exists",
            DeprecationWarning,
            stacklevel=2
        )
        return None















