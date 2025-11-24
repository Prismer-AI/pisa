"""
Pydantic Schemas

职责：
1. 定义 agent.md 的 Pydantic 模型
2. 定义 context.md 的 Pydantic 模型
3. 提供类型安全的数据结构
4. 支持自动验证和序列化

TODO:
- 定义 AgentDefinition model
- 定义 ContextDefinition model
- 定义 CapabilityReference model
- 定义 LoopConfig model
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CapabilityReference(BaseModel):
    """
    Capability 引用
    
    TODO: 实现完整的 capability 引用结构
    """
    name: str = Field(..., description="Capability 名称")
    type: str = Field(..., description="Capability 类型: function/agent/mcp")
    config: Optional[Dict[str, Any]] = Field(default=None, description="配置参数")


class LoopConfig(BaseModel):
    """
    Loop 配置
    
    TODO: 实现完整的 loop 配置结构
    """
    type: str = Field(..., description="Loop 类型: reflex/react/plan_execute/reflexion")
    max_iterations: Optional[int] = Field(default=10, description="最大迭代次数")
    timeout: Optional[int] = Field(default=300, description="超时时间（秒）")


class AgentDefinition(BaseModel):
    """
    Agent 定义
    
    对应 agent.md 的完整结构
    
    TODO: 实现完整的 agent 定义结构
    """
    name: str = Field(..., description="Agent 名称")
    description: Optional[str] = Field(default=None, description="Agent 描述")
    loop_type: str = Field(..., description="Loop 类型")
    capabilities: List[CapabilityReference] = Field(default_factory=list, description="Capability 列表")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词")
    config: Optional[Dict[str, Any]] = Field(default=None, description="其他配置")


class ContextDefinition(BaseModel):
    """
    Context 定义
    
    对应 context.md 的完整结构
    
    TODO: 实现完整的 context 定义结构
    """
    max_tokens: Optional[int] = Field(default=100000, description="最大 token 数")
    compression_enabled: Optional[bool] = Field(default=True, description="是否启用压缩")
    memory_enabled: Optional[bool] = Field(default=False, description="是否启用长期记忆")
    config: Optional[Dict[str, Any]] = Field(default=None, description="其他配置")

