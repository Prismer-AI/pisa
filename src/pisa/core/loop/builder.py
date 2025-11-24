"""
Loop Builder (Deprecated in v2.0)

职责：
1. 提供 Builder 模式构建 Loop（已废弃）
2. 保留向后兼容性

注意：
v2.0 中推荐使用 @agent_loop 装饰器和 LoopRegistry
此文件仅用于向后兼容

TODO:
- 实现基础的 Builder 接口
- 提供迁移指南
"""

from typing import Any, Dict, Optional
import warnings


class LoopBuilder:
    """
    Loop Builder（已废弃）
    
    警告：此类在 v2.0 中已废弃，请使用 @agent_loop 装饰器
    """
    
    def __init__(self):
        warnings.warn(
            "LoopBuilder is deprecated in v2.0. "
            "Please use @agent_loop decorator instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def with_context(self, context: Any) -> 'LoopBuilder':
        """
        设置上下文
        
        TODO: 实现设置逻辑
        """
        raise NotImplementedError("已废弃，请使用 @agent_loop 装饰器")
    
    def with_capabilities(self, capabilities: Dict[str, Any]) -> 'LoopBuilder':
        """
        设置 capabilities
        
        TODO: 实现设置逻辑
        """
        raise NotImplementedError("已废弃，请使用 @agent_loop 装饰器")
    
    def build(self) -> Any:
        """
        构建 Loop
        
        TODO: 实现构建逻辑
        """
        raise NotImplementedError("已废弃，请使用 @agent_loop 装饰器")

