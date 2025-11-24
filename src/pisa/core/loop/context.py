"""
Loop Context

Loop层的Context包装器，提供便捷的Context操作接口

职责：
1. 包装 ContextManager，提供 Loop 特定的接口
2. 管理 LLM 交互历史（Messages）
3. 提供便捷的 Context 操作方法
"""

import logging
from typing import Any, Dict, List, Optional

from pisa.core.context import ContextManager

_logger = logging.getLogger(__name__)


class LoopContext:
    """
    Loop Context 包装器
    
    包装 ContextManager，提供更高层次的 Context 操作接口
    """
    
    def __init__(
        self, 
        context_manager: Optional[ContextManager] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ):
        """
        初始化 Loop Context
        
        Args:
            context_manager: Context管理器实例，如果为None则创建新实例
            agent_id: Agent ID（用于创建新的ContextManager）
            session_id: Session ID（用于创建新的ContextManager）
            **kwargs: 其他传递给ContextManager的参数
        """
        if context_manager is not None:
            self.context_manager = context_manager
        else:
            # 创建新的ContextManager
            cm_kwargs = {}
            if agent_id is not None:
                cm_kwargs['agent_id'] = agent_id
            if session_id is not None:
                cm_kwargs['session_id'] = session_id
            cm_kwargs.update(kwargs)
            self.context_manager = ContextManager(**cm_kwargs)
        
    def add_message(self, role: str, content: str, **kwargs) -> None:
        """
        添加消息到Context
        
        Args:
            role: 消息角色（user, assistant, system）
            content: 消息内容
            **kwargs: 额外的消息字段
        """
        self.context_manager.add_message(role=role, content=content, **kwargs)
    
    def add_observation_message(self, observation: Any) -> None:
        """
        添加观察消息
        
        Args:
            observation: 观察结果
        """
        # 将观察结果转换为消息格式
        content = str(observation) if not isinstance(observation, str) else observation
        self.add_message(role="system", content=f"[OBSERVATION] {content}")
    
    def add_decision_message(self, decision: Any) -> None:
        """
        添加决策消息
        
        Args:
            decision: 决策结果
        """
        # 将决策结果转换为消息格式
        content = str(decision) if not isinstance(decision, str) else decision
        self.add_message(role="system", content=f"[DECISION] {content}")
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """
        获取所有消息
        
        Returns:
            消息列表
        """
        return self.context_manager.get_messages()
    
    def clear(self) -> None:
        """清空Context"""
        self.context_manager.clear()
    
    def get_token_count(self) -> int:
        """
        获取当前token数量
        
        Returns:
            token数量
        """
        return self.context_manager.get_token_count()
    
    def should_compress(self) -> bool:
        """
        判断是否需要压缩
        
        Returns:
            是否需要压缩
        """
        return self.context_manager.should_compress()
    
    async def compress(self) -> None:
        """
        压缩Context
        """
        await self.context_manager.compress()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        导出为字典
        
        Returns:
            Context的字典表示
        """
        return self.context_manager.to_dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoopContext":
        """
        从字典创建实例
        
        Args:
            data: Context字典数据
            
        Returns:
            LoopContext实例
        """
        context_manager = ContextManager.from_dict(data)
        return cls(context_manager=context_manager)

