"""
PISA Core Loop System

提供 Agent Loop 的基础设施和模板。

新架构（重构版）：
- display_utils: 通用展示方法
- lifecycle: 生命周期管理
- base_refactored: 增强的基类（自动化基础设施）
- templates/: Loop 模板（纯业务逻辑）

旧架构（兼容）：
- base: 原始基类
- templates/plan_execute: 原始模板

使用方式：
    # 推荐：使用重构版
    from pisa.core.loop.base_refactored import BaseAgentLoop
    from pisa.core.loop.templates.plan_execute_refactored import PlanExecuteLoop
    
    # 或通过 RegistryManager 创建
    from pisa.agents import get_registry_manager
    manager = get_registry_manager()
    agent = manager.create_agent("agent.md")
"""

# 重构版（推荐）- 暂时禁用，因为依赖的模块未实现
# from .base_refactored import BaseAgentLoop as BaseAgentLoopRefactored, IAgentLoop
# from .lifecycle import LifecycleManager
# from .display_utils import (
#     display_loop_definition,
#     display_task_tree,
#     display_context_state,
#     display_execution_summary
# )

# 旧版（兼容）
from .base import BaseAgentLoop, IAgentLoop

# Registry
from .registry import (
    LoopRegistry,
    get_loop_registry,
    agent,
)

# Capability Resolver
from .capability_resolver import CapabilityResolver

# Public API
__all__ = [
    # 接口
    "IAgentLoop",
    
    # 基类
    "BaseAgentLoop",
    
    # Registry
    "LoopRegistry",
    "get_loop_registry",
    "agent",
    
    # Capability Resolver
    "CapabilityResolver",
]

