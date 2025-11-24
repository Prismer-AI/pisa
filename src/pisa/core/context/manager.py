"""
Context Manager

上下文管理器，负责管理 Agent 的运行时上下文
集成 OpenAI Agent SDK 的 RunContextWrapper
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import (
    ContextState,
    Message,
    MessageRole,
    RoundContext,
    CompressionStrategy,
)
from .compression import ContextCompressor
from .serializer import ContextSerializer

_logger = logging.getLogger(__name__)


class ContextManager:
    """
    上下文管理器
    
    职责：
    1. 管理消息历史
    2. 触发自动压缩
    3. 序列化/反序列化到 context.md
    4. 与 OpenAI Agent SDK 集成
    
    使用方式：
    ```python
    # 创建 context
    manager = ContextManager(agent_id="my_agent", session_id="sess_123")
    
    # 添加消息
    manager.add_message(MessageRole.USER, "Hello")
    manager.add_message(MessageRole.ASSISTANT, "Hi there!")
    
    # 获取给 LLM 的消息
    messages = manager.get_active_messages()
    
    # 自动压缩
    if manager.should_compress():
        await manager.compress()
    
    # 序列化
    markdown = manager.to_markdown()
    ```
    """
    
    def __init__(
        self,
        agent_id: str,
        session_id: str,
        context_state: Optional[ContextState] = None,
        compression_model: Optional[str] = None,
        **config
    ):
        """
        初始化上下文管理器
        
        Args:
            agent_id: Agent ID
            session_id: Session ID
            context_state: 已有的 context state（用于恢复）
            compression_model: 压缩使用的模型
            **config: 额外配置
        """
        if context_state:
            self.state = context_state
        else:
            self.state = ContextState(
                agent_id=agent_id,
                session_id=session_id,
                static_config=config
            )
        
        # 初始化压缩器
        self.compressor = ContextCompressor(compression_model)
        
        # 初始化序列化器
        self.serializer = ContextSerializer()
        
        _logger.info(
            f"ContextManager initialized: agent={agent_id}, session={session_id}"
        )
    
    @property
    def context(self) -> ContextState:
        """获取 context state（用于 OpenAI Agent SDK）"""
        return self.state
    
    def get_state(self) -> ContextState:
        """
        获取当前上下文状态
        
        Returns:
            ContextState对象
        """
        return self.state
    
    def add_message(
        self,
        role: MessageRole,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_call_id: Optional[str] = None,
        **metadata
    ) -> None:
        """
        添加消息到上下文
        
        Args:
            role: 消息角色
            content: 消息内容
            tool_calls: 工具调用（如果有）
            tool_call_id: 工具调用 ID（如果是工具响应）
            **metadata: 额外的元数据
        """
        self.state.add_message(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            metadata=metadata
        )
        
        _logger.debug(
            f"Added message: role={role}, content_length={len(content)}, "
            f"round={self.state.current_round}"
        )
    
    def get_active_messages(self) -> List[Dict[str, Any]]:
        """
        获取活跃的消息（用于 LLM prompt）
        
        Returns:
            OpenAI API 格式的消息列表
        """
        messages = self.state.get_active_messages()
        
        # 转换为 OpenAI API 格式
        openai_messages = []
        for msg in messages:
            message_dict = {
                "role": msg.role.value,
                "content": msg.content
            }
            
            # 添加 tool_calls 如果有
            if msg.tool_calls:
                message_dict["tool_calls"] = msg.tool_calls
            
            # 添加 tool_call_id 如果有
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id
            
            openai_messages.append(message_dict)
        
        return openai_messages
    
    def get_active_tokens(self) -> int:
        """获取活跃内容的 token 数"""
        return self.state.get_active_tokens()
    
    def should_compress(self) -> bool:
        """判断是否需要压缩"""
        return self.state.should_compress()
    
    async def compress(
        self,
        strategy: Optional[CompressionStrategy] = None
    ) -> None:
        """
        压缩上下文
        
        Args:
            strategy: 压缩策略，默认使用 state 中的配置
        """
        _logger.info(
            f"Starting compression: active_tokens={self.get_active_tokens()}, "
            f"strategy={strategy or self.state.compression_strategy}"
        )
        
        # 执行压缩
        await self.compressor.compress_context(self.state, strategy)
        
        _logger.info(
            f"Compression completed: count={self.state.compression_count}, "
            f"new_active_tokens={self.get_active_tokens()}"
        )
    
    def to_markdown(self) -> str:
        """
        序列化为 context.md
        
        Returns:
            Markdown 格式的上下文
        """
        return self.serializer.serialize(self.state)
    
    @classmethod
    def from_markdown(
        cls,
        markdown_content: str,
        compression_model: Optional[str] = None
    ) -> 'ContextManager':
        """
        从 context.md 恢复
        
        Args:
            markdown_content: Markdown 内容
            compression_model: 压缩模型
            
        Returns:
            ContextManager 实例
        """
        serializer = ContextSerializer()
        state = serializer.deserialize(markdown_content)
        
        return cls(
            agent_id=state.agent_id,
            session_id=state.session_id,
            context_state=state,
            compression_model=compression_model
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息（用于监控）
        
        Returns:
            统计信息字典
        """
        return {
            "agent_id": self.state.agent_id,
            "session_id": self.state.session_id,
            "total_rounds": len(self.state.rounds),
            "current_round": self.state.current_round,
            "total_tokens": self.state.total_tokens,
            "active_tokens": self.get_active_tokens(),
            "compression_count": self.state.compression_count,
            "last_compression_at": self.state.last_compression_at.isoformat() 
                if self.state.last_compression_at else None,
            "compression_strategy": self.state.compression_strategy.value,
            "created_at": self.state.created_at.isoformat(),
            "updated_at": self.state.updated_at.isoformat(),
        }
    
    def get_round(self, round_id: int) -> Optional[RoundContext]:
        """获取指定轮次"""
        for round_ctx in self.state.rounds:
            if round_ctx.round_id == round_id:
                return round_ctx
        return None
    
    def get_current_round(self) -> Optional[RoundContext]:
        """获取当前轮次"""
        if self.state.rounds:
            return self.state.rounds[-1]
        return None
    
    def clear_old_rounds(self, keep_recent: int = 10) -> None:
        """
        清理旧轮次（只保留最近 N 轮）
        
        Args:
            keep_recent: 保留的最近轮次数
        """
        if len(self.state.rounds) > keep_recent:
            removed_count = len(self.state.rounds) - keep_recent
            self.state.rounds = self.state.rounds[-keep_recent:]
            _logger.info(f"Cleared {removed_count} old rounds")
