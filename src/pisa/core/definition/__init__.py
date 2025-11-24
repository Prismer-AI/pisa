"""
PISA 定义层

职责：
1. Agent 定义数据模型
2. 定义文件解析
3. 定义验证
"""

# 导出主要组件
from .models import (
    AgentDefinition,
    AgentMetadata,
    ModelConfig,
    CapabilityReference,
    PlanningConfig,
    ContextConfig,
    ObservabilityConfig,
    RuntimeConfig,
    ValidationRule,
    # AgentLoopType 已移除 - loop type 现在是动态从 LoopRegistry 获取的字符串
)
from .parser import parse_agent_definition, AgentDefinitionParser

# 可选的导入
try:
    from .validator import validate_agent_definition
except ImportError:
    validate_agent_definition = None

try:
    from .loader import load_agent_definition
except ImportError:
    load_agent_definition = None

__all__ = [
    "AgentDefinition",
    "AgentMetadata",
    "ModelConfig",
    "CapabilityReference",
    "PlanningConfig",
    "ContextConfig",
    "ObservabilityConfig",
    "RuntimeConfig",
    "ValidationRule",
    # "AgentLoopType",  # 已移除
    "parse_agent_definition",
    "AgentDefinitionParser",
    "validate_agent_definition",
    "load_agent_definition",
]



