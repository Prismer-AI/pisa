"""
Context Data Models

定义 Context 相关的数据模型，基于 OpenAI Agent SDK 的 Context 系统
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    """
    消息对象
    
    Compatible with OpenAI Agent SDK message format
    """
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RoundContext(BaseModel):
    """
    单轮上下文
    
    代表一次完整的用户输入-Agent响应循环
    """
    round_id: int
    messages: List[Message] = Field(default_factory=list)
    raw_content: str = ""  # Heading 3 原始内容
    compressed_content: Optional[str] = None  # Heading 2 压缩内容
    compression_ratio: Optional[float] = None
    tokens_used: int = 0
    heading_level: int = 2  # Markdown heading level (2=active, 3=archived, 4=deep)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CompressionStrategy(str, Enum):
    """压缩策略"""
    PER_ROUND = "per_round"  # 单轮压缩
    MULTI_ROUND = "multi_round"  # 多轮合并压缩
    SEMANTIC_MERGE = "semantic_merge"  # 语义合并
    ADAPTIVE = "adaptive"  # 自适应


class ContextState(BaseModel):
    """
    运行时上下文状态
    
    这是 PISA Context 的核心状态对象，可以作为 OpenAI Agent SDK 的
    RunContextWrapper 的 context 对象使用
    """
    agent_id: str
    session_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 消息历史
    messages: List[Message] = Field(default_factory=list, description="消息历史")
    
    # Heading 1: 静态配置
    static_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Heading 2+: 动态轮次上下文
    rounds: List[RoundContext] = Field(default_factory=list)
    current_round: int = 0
    
    # 全局状态
    total_tokens: int = 0
    compression_count: int = 0
    last_compression_at: Optional[datetime] = None
    
    # 压缩配置
    compression_strategy: CompressionStrategy = CompressionStrategy.PER_ROUND
    compression_trigger_tokens: int = 8000
    max_heading_depth: int = 4
    
    # ⭐ 新增：绑定的 Agent Loop 引用 (不序列化)
    owner_loop: Optional[Any] = Field(default=None, exclude=True)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        arbitrary_types_allowed = True  # 允许 owner_loop 使用任意类型
    
    def get_active_messages(self) -> List[Message]:
        """
        获取活跃的消息（用于 LLM prompt）
        
        只返回 heading_level <= 2 的消息
        """
        messages = []
        for round_ctx in self.rounds:
            if round_ctx.heading_level <= 2:
                messages.extend(round_ctx.messages)
        return messages
    
    def get_active_tokens(self) -> int:
        """计算活跃内容的 token 数"""
        return sum(
            r.tokens_used 
            for r in self.rounds 
            if r.heading_level <= 2 and not r.compressed_content
        )
    
    def should_compress(self) -> bool:
        """判断是否需要压缩"""
        return self.get_active_tokens() >= self.compression_trigger_tokens
    
    def add_message(self, role: MessageRole, content: str, **kwargs) -> None:
        """
        添加消息到当前轮次
        
        Args:
            role: 消息角色
            content: 消息内容
            **kwargs: 额外的消息属性
        """
        message = Message(
            role=role,
            content=content,
            **kwargs
        )
        
        # 如果当前没有轮次或当前轮次已完成，创建新轮次
        if not self.rounds or self._is_round_complete(self.rounds[-1]):
            self.current_round += 1
            new_round = RoundContext(
                round_id=self.current_round,
                messages=[message]
            )
            self.rounds.append(new_round)
        else:
            # 添加到当前轮次
            self.rounds[-1].messages.append(message)
        
        self.updated_at = datetime.now()
    
    def _is_round_complete(self, round_ctx: RoundContext) -> bool:
        """判断轮次是否完成（有用户输入和助手回复）"""
        if not round_ctx.messages:
            return False
        
        roles = [m.role for m in round_ctx.messages]
        return MessageRole.USER in roles and MessageRole.ASSISTANT in roles


class CompressionResult(BaseModel):
    """压缩结果"""
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    compressed_content: str
    strategy_used: CompressionStrategy
    duration_ms: float
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

