"""
Temporal Integration (v4.0)

提供Temporal工作流支持，实现Agent Loop的持久化和长时间运行。

主要组件：
1. Workflows: AgentLoopWorkflow, SimpleAgentWorkflow
2. Activities: 状态保存、Capability执行、通知等
3. StateStorage: LoopState和LoopContext的序列化
4. Client/Worker: Temporal客户端和工作器

使用示例：
```python
from pisa.temporal import (
    AgentLoopWorkflow,
    AgentWorkflowInput,
    TemporalAgentClient,
)

# 创建客户端
client = await TemporalAgentClient.create()

# 启动workflow
result = await client.start_workflow(
    workflow_id="my_task",
    task_description="Analyze this document",
    loop_type="plan_execute",
)
```
"""

from pisa.temporal.workflows import (
    AgentLoopWorkflow,
    SimpleAgentWorkflow,
    AgentWorkflowInput,
)
from pisa.temporal.activities import (
    save_state_checkpoint_activity,
    load_state_checkpoint_activity,
    list_checkpoints_activity,
    execute_capability_activity,
    notify_user_activity,
    CapabilityCallRequest,
)
from pisa.temporal.state_storage import (
    StateStorage,
    ContextStorage,
    TemporalStateManager,
)
from pisa.temporal.client import TemporalAgentClient
from pisa.temporal.worker import TemporalAgentWorker

__all__ = [
    # Workflows
    "AgentLoopWorkflow",
    "SimpleAgentWorkflow",
    "AgentWorkflowInput",
    
    # Activities
    "save_state_checkpoint_activity",
    "load_state_checkpoint_activity",
    "list_checkpoints_activity",
    "execute_capability_activity",
    "notify_user_activity",
    "CapabilityCallRequest",
    
    # Storage
    "StateStorage",
    "ContextStorage",
    "TemporalStateManager",
    
    # Client & Worker
    "TemporalAgentClient",
    "TemporalAgentWorker",
]

