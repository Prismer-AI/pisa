"""
Temporal Client

用于启动和管理 Workflows。

参考: https://github.com/temporalio/sdk-python
"""

import uuid
from typing import Dict, Any, Optional
from datetime import timedelta

from temporalio.client import Client, WorkflowHandle
from temporalio.common import RetryPolicy

from .workflows import AgentLoopWorkflow, AgentWorkflowInput, SimpleAgentWorkflow


class TemporalAgentClient:
    """
    Temporal Agent Client
    
    提供启动和管理 Agent Workflows 的便捷接口。
    """
    
    def __init__(
        self,
        client: Client,
        task_queue: str = "pisa-agent-queue"
    ):
        """
        初始化 Client
        
        Args:
            client: Temporal Client 实例
            task_queue: Task queue 名称
        """
        self.client = client
        self.task_queue = task_queue
    
    async def start_agent(
        self,
        agent_id: str,
        session_id: str,
        user_input: str,
        agent_definition_path: Optional[str] = None,
        workflow_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> WorkflowHandle:
        """
        启动 Agent Workflow
        
        Args:
            agent_id: Agent ID
            session_id: Session ID
            user_input: 用户输入
            agent_definition_path: agent.md 文件路径
            workflow_id: 自定义 Workflow ID
            config: 额外配置
            
        Returns:
            WorkflowHandle
        """
        if workflow_id is None:
            workflow_id = f"agent-{agent_id}-{session_id}-{uuid.uuid4().hex[:8]}"
        
        input_data = AgentLoopWorkflowInput(
            agent_id=agent_id,
            session_id=session_id,
            user_input=user_input,
            agent_definition_path=agent_definition_path,
            config=config
        )
        
        handle = await self.client.start_workflow(
            AgentLoopWorkflow.run,
            input_data,
            id=workflow_id,
            task_queue=self.task_queue,
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                backoff_coefficient=2.0
            ),
            execution_timeout=timedelta(hours=24)  # 最多运行 24 小时
        )
        
        return handle
    
    async def get_workflow_handle(
        self,
        workflow_id: str
    ) -> WorkflowHandle:
        """
        获取已存在的 Workflow Handle
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            WorkflowHandle
        """
        return self.client.get_workflow_handle(workflow_id)
    
    async def send_message(
        self,
        workflow_id: str,
        message: str
    ) -> None:
        """
        向运行中的 Workflow 发送消息
        
        Args:
            workflow_id: Workflow ID
            message: 用户消息
        """
        handle = await self.get_workflow_handle(workflow_id)
        await handle.signal(AgentLoopWorkflow.handle_user_input, message)
    
    async def pause_workflow(self, workflow_id: str) -> None:
        """暂停 Workflow"""
        handle = await self.get_workflow_handle(workflow_id)
        await handle.signal(AgentLoopWorkflow.pause)
    
    async def resume_workflow(self, workflow_id: str) -> None:
        """恢复 Workflow"""
        handle = await self.get_workflow_handle(workflow_id)
        await handle.signal(AgentLoopWorkflow.resume)
    
    async def complete_workflow(
        self,
        workflow_id: str,
        result: Any = None
    ) -> None:
        """完成 Workflow"""
        handle = await self.get_workflow_handle(workflow_id)
        await handle.signal(AgentLoopWorkflow.complete, result)
    
    async def get_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        查询 Workflow 状态
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            状态信息
        """
        handle = await self.get_workflow_handle(workflow_id)
        return await handle.query(AgentLoopWorkflow.get_status)
    
    async def get_result(self, workflow_id: str) -> Any:
        """
        获取 Workflow 结果
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            结果
        """
        handle = await self.get_workflow_handle(workflow_id)
        return await handle.result()
    
    async def cancel_workflow(self, workflow_id: str) -> None:
        """
        取消 Workflow
        
        Args:
            workflow_id: Workflow ID
        """
        handle = await self.get_workflow_handle(workflow_id)
        await handle.cancel()


async def create_temporal_client(
    target_host: str = "localhost:7233",
    namespace: str = "default",
    task_queue: str = "pisa-agent-queue"
) -> TemporalAgentClient:
    """
    创建 Temporal Client
    
    Args:
        target_host: Temporal 服务地址
        namespace: Namespace
        task_queue: Task queue
        
    Returns:
        TemporalAgentClient
    """
    client = await Client.connect(
        target_host,
        namespace=namespace
    )
    
    return TemporalAgentClient(client, task_queue)
