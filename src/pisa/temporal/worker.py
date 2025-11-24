"""
Temporal Worker

运行 Workflows 和 Activities 的 Worker。
"""

import asyncio
import logging
from typing import List, Type

from temporalio.client import Client
from temporalio.worker import Worker

from .workflows import AgentLoopWorkflow, SimpleAgentWorkflow
from .activities import (
    execute_capability_activity,
    save_context_activity,
    compress_context_activity,
    load_agent_definition_activity,
    notify_user_activity,
)

_logger = logging.getLogger(__name__)


class TemporalAgentWorker:
    """
    Temporal Agent Worker
    
    负责运行 Workflows 和 Activities。
    """
    
    def __init__(
        self,
        client: Client,
        task_queue: str = "pisa-agent-queue",
        workflows: List[Type] = None,
        activities: List = None,
        max_concurrent_activities: int = 10,
        max_concurrent_workflows: int = 10
    ):
        """
        初始化 Worker
        
        Args:
            client: Temporal Client
            task_queue: Task queue 名称
            workflows: Workflow 类列表
            activities: Activity 函数列表
            max_concurrent_activities: 最大并发 Activity 数
            max_concurrent_workflows: 最大并发 Workflow 数
        """
        self.client = client
        self.task_queue = task_queue
        
        # 默认 Workflows
        self.workflows = workflows or [
            AgentLoopWorkflow,
            SimpleAgentWorkflow
        ]
        
        # 默认 Activities
        self.activities = activities or [
            execute_capability_activity,
            save_context_activity,
            compress_context_activity,
            load_agent_definition_activity,
            notify_user_activity,
        ]
        
        self.max_concurrent_activities = max_concurrent_activities
        self.max_concurrent_workflows = max_concurrent_workflows
        
        self.worker: Optional[Worker] = None
    
    async def start(self) -> None:
        """启动 Worker"""
        _logger.info(f"Starting Temporal Worker on task queue: {self.task_queue}")
        
        self.worker = Worker(
            self.client,
            task_queue=self.task_queue,
            workflows=self.workflows,
            activities=self.activities,
            max_concurrent_activities=self.max_concurrent_activities,
            max_concurrent_workflow_tasks=self.max_concurrent_workflows
        )
        
        _logger.info(
            f"Worker registered: "
            f"{len(self.workflows)} workflows, "
            f"{len(self.activities)} activities"
        )
        
        # 运行 worker（这会阻塞）
        await self.worker.run()
    
    async def shutdown(self) -> None:
        """关闭 Worker"""
        if self.worker:
            _logger.info("Shutting down Temporal Worker")
            await self.worker.shutdown()


async def run_worker(
    target_host: str = "localhost:7233",
    namespace: str = "default",
    task_queue: str = "pisa-agent-queue"
) -> None:
    """
    运行 Worker
    
    Args:
        target_host: Temporal 服务地址
        namespace: Namespace
        task_queue: Task queue
    """
    # 连接到 Temporal
    client = await Client.connect(target_host, namespace=namespace)
    
    # 创建 Worker
    worker = TemporalAgentWorker(client, task_queue)
    
    try:
        # 启动 Worker
        await worker.start()
    except KeyboardInterrupt:
        _logger.info("Received interrupt, shutting down")
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 运行 Worker
    asyncio.run(run_worker())
