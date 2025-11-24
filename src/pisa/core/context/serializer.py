"""
Context Serializer

负责 ContextState 与 Markdown (context.md) 之间的序列化/反序列化
"""

import json
import logging
from typing import List, Optional
from datetime import datetime

from .models import ContextState, RoundContext, Message, MessageRole

_logger = logging.getLogger(__name__)


class ContextSerializer:
    """
    上下文序列化器
    
    将 ContextState 序列化为 context.md 格式
    """
    
    def serialize(self, state: ContextState) -> str:
        """
        序列化为 context.md
        
        格式：
        ```markdown
        ---
        agent_id: xxx
        session_id: xxx
        ...
        ---
        
        # Agent Configuration (Static)
        ...
        
        # Execution History
        
        ## Round 1
        ...
        
        ### Round 1 - Raw Archive
        ...
        ```
        """
        lines = []
        
        # YAML Frontmatter
        lines.append("---")
        lines.append(f"agent_id: {state.agent_id}")
        lines.append(f"session_id: {state.session_id}")
        lines.append(f"created_at: {state.created_at.isoformat()}")
        lines.append(f"updated_at: {state.updated_at.isoformat()}")
        lines.append(f"total_tokens: {state.total_tokens}")
        lines.append(f"compression_count: {state.compression_count}")
        if state.last_compression_at:
            lines.append(f"last_compression_at: {state.last_compression_at.isoformat()}")
        lines.append("---")
        lines.append("")
        
        # H1: Agent Configuration
        lines.append("# Agent Configuration (Static)")
        lines.append("")
        lines.append("## Metadata")
        for key, value in state.static_config.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # H1: Execution History
        lines.append("# Execution History")
        lines.append("")
        
        # Rounds
        for round_ctx in state.rounds:
            lines.extend(self._serialize_round(round_ctx))
            lines.append("")
        
        return "\n".join(lines)
    
    def _serialize_round(self, round_ctx: RoundContext) -> List[str]:
        """序列化单个轮次"""
        lines = []
        
        # Heading level
        heading = "#" * round_ctx.heading_level
        
        # Round title
        if round_ctx.compressed_content:
            title = f"{heading} Round {round_ctx.round_id} - Compressed"
        else:
            title = f"{heading} Round {round_ctx.round_id}"
        
        lines.append(title)
        lines.append("")
        
        # 如果有压缩内容，显示压缩内容
        if round_ctx.compressed_content:
            lines.append(round_ctx.compressed_content)
            lines.append("")
            lines.append(f"*Compression ratio: {round_ctx.compression_ratio:.2%}*")
            lines.append("")
            
            # 原始内容放到下一级 heading
            if round_ctx.raw_content:
                raw_heading = "#" * (round_ctx.heading_level + 1)
                lines.append(f"{raw_heading} Round {round_ctx.round_id} - Raw Archive")
                lines.append("")
                lines.append("<details>")
                lines.append(f"<summary>Original conversation ({round_ctx.tokens_used} tokens)</summary>")
                lines.append("")
                lines.append(round_ctx.raw_content)
                lines.append("")
                lines.append("</details>")
        else:
            # 显示原始消息
            for msg in round_ctx.messages:
                lines.extend(self._serialize_message(msg))
                lines.append("")
        
        return lines
    
    def _serialize_message(self, message: Message) -> List[str]:
        """序列化单条消息"""
        lines = []
        
        # 角色标题
        role_title = {
            MessageRole.USER: "**User**",
            MessageRole.ASSISTANT: "**Assistant**",
            MessageRole.SYSTEM: "**System**",
            MessageRole.TOOL: "**Tool Response**"
        }
        
        lines.append(f"{role_title.get(message.role, '**Unknown**')} ({message.timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
        lines.append("")
        
        # 内容
        lines.append(message.content)
        
        # Tool calls
        if message.tool_calls:
            lines.append("")
            lines.append("*Tool Calls:*")
            for tc in message.tool_calls:
                lines.append(f"- `{tc.get('function', {}).get('name', 'unknown')}`")
        
        return lines
    
    def deserialize(self, markdown_content: str) -> ContextState:
        """
        从 context.md 反序列化
        
        Args:
            markdown_content: Markdown 内容
            
        Returns:
            ContextState 对象
        """
        lines = markdown_content.split("\n")
        
        # 解析 frontmatter
        frontmatter = self._parse_frontmatter(lines)
        
        # 创建 ContextState
        state = ContextState(
            agent_id=frontmatter.get("agent_id", "unknown"),
            session_id=frontmatter.get("session_id", "unknown"),
            created_at=self._parse_datetime(frontmatter.get("created_at")),
            updated_at=self._parse_datetime(frontmatter.get("updated_at")),
            total_tokens=int(frontmatter.get("total_tokens", 0)),
            compression_count=int(frontmatter.get("compression_count", 0)),
            last_compression_at=self._parse_datetime(frontmatter.get("last_compression_at"))
        )
        
        # TODO: 解析 rounds（复杂，暂时跳过）
        # 实际使用时可能更多依赖 state 持久化而非完整的 markdown 解析
        
        _logger.warning("Context deserialization from markdown is partial - rounds not parsed")
        
        return state
    
    def _parse_frontmatter(self, lines: List[str]) -> dict:
        """解析 YAML frontmatter"""
        frontmatter = {}
        
        if not lines or lines[0].strip() != "---":
            return frontmatter
        
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            line = lines[i].strip()
            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip()
            i += 1
        
        return frontmatter
    
    def _parse_datetime(self, dt_str: Optional[str]) -> datetime:
        """解析 datetime 字符串"""
        if not dt_str:
            return datetime.now()
        
        try:
            return datetime.fromisoformat(dt_str)
        except (ValueError, AttributeError):
            return datetime.now()
