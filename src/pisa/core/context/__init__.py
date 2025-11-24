"""
Context Management Module

上下文管理系统，负责：
1. 管理 Agent 运行时上下文
2. 自动压缩上下文
3. 序列化/反序列化
4. 与 OpenAI Agent SDK 集成

使用方式：
```python
from pisa.core.context import ContextManager, MessageRole

# 创建 context manager
manager = ContextManager(agent_id="my_agent", session_id="sess_123")

# 添加消息
manager.add_message(MessageRole.USER, "Hello")
manager.add_message(MessageRole.ASSISTANT, "Hi!")

# 获取消息（给 LLM）
messages = manager.get_active_messages()

# 自动压缩
if manager.should_compress():
    await manager.compress()

# 序列化
markdown = manager.to_markdown()
```
"""

from .models import (
    Message,
    MessageRole,
    RoundContext,
    ContextState,
    CompressionStrategy,
    CompressionResult,
)
from .manager import ContextManager
from .compression import ContextCompressor
from .serializer import ContextSerializer

__all__ = [
    # Models
    "Message",
    "MessageRole",
    "RoundContext",
    "ContextState",
    "CompressionStrategy",
    "CompressionResult",
    
    # Manager
    "ContextManager",
    
    # Components
    "ContextCompressor",
    "ContextSerializer",
]
