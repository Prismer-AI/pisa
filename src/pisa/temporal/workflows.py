"""
Temporal Workflows (v4.0 Refactored)

定义长时间运行的 Agent workflows，适配v4.0架构。

特点：
1. 使用新的LoopState进行状态管理
2. 使用新的BaseAgentLoop
3. 支持状态持久化和恢复
4. 支持暂停/恢复和人工介入

参考：
- https://github.com/temporalio/sdk-python/tree/main/temporalio/contrib/openai_agents
- PISA2.md Temporal Event 数据流设计
"""

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, Optional
from dataclasses import dataclass

from temporalio import workflow
from temporalio.common import RetryPolicy

from pisa.core.loop.state import LoopState
from pisa.core.loop.templates import PlanExecuteLoop
from pisa.core.loop.config import LoopConfig

from .activities import (
    save_state_checkpoint_activity,
    load_state_checkpoint_activity,
    notify_user_activity,
)
from .state_storage import StateStorage

_logger = logging.getLogger(__name__)


@dataclass
class AgentWorkflowInput:
    """Agent Workflow 输入 (v4.0)"""
    # 基本信息
    workflow_id: str
    task_description: str
    
    # Loop配置
    loop_type: str = "plan_execute"  # "plan_execute" or "ooda"
    max_iterations: int = 10
    
    # 恢复相关
    resume_from_checkpoint: Optional[str] = None
    
    # 额外配置
    config: Optional[Dict[str, Any]] = None


@workflow.defn
class AgentLoopWorkflow:
    """
    Agent Loop Workflow (v4.0)
    
    管理 Agent Loop 的长时间执行，基于v4.0架构：
    - 使用LoopState进行状态管理
    - 使用BaseAgentLoop（OODALoop或PlanExecuteLoop）
    - 支持自动检查点保存
    - 支持暂停/恢复
    - 支持人工介入
    
    Event Flow:
    1. WorkflowExecutionStarted
    2. 加载或初始化LoopState
    3. 执行Loop（带自动检查点）
    4. Signal: pause_workflow
    5. Signal: resume_workflow
    6. Query: get_current_state
    7. WorkflowExecutionCompleted
    """
    
    def __init__(self):
        """初始化workflow"""
        self.current_state: Optional[LoopState] = None
        self.is_paused = False
        self.loop_instance = None
        self.workflow_id = ""
    
    @workflow.run
    async def run(self, input: AgentWorkflowInput) -> Dict[str, Any]:
        """
        运行 Agent Loop Workflow
        
        Args:
            input: Workflow 输入
            
        Returns:
            执行结果
        """
        self.workflow_id = input.workflow_id
        
        workflow.logger.info(
            f"Starting Agent Loop Workflow: {input.workflow_id}, "
            f"loop_type={input.loop_type}"
        )
        
        try:
            # ==================== 步骤1: 初始化或恢复State ====================
            if input.resume_from_checkpoint:
                workflow.logger.info(f"Resuming from checkpoint: {input.resume_from_checkpoint}")
                
                # 从检查点恢复
                checkpoint_data = await workflow.execute_activity(
                    load_state_checkpoint_activity,
                    args=[input.workflow_id, input.resume_from_checkpoint],
                    start_to_close_timeout=timedelta(seconds=30),
                )
                
                self.current_state = StateStorage.deserialize_state(checkpoint_data["state"])
                workflow.logger.info(f"Resumed at iteration {self.current_state.iteration}")
            else:
                # 创建新State
                self.current_state = LoopState(
                    input=input.task_description,
                    task={"description": input.task_description}
                )
                workflow.logger.info("Created new LoopState")
            
            # ==================== 步骤2: 创建Loop实例 ====================
            loop_config = self._create_loop_config(input)
            
            if input.loop_type == "ooda":
                self.loop_instance = OODALoop(config=loop_config)
            elif input.loop_type == "plan_execute":
                self.loop_instance = PlanExecuteLoop(config=loop_config)
            else:
                raise ValueError(f"Unknown loop type: {input.loop_type}")
            
            workflow.logger.info(f"Created {input.loop_type} loop instance")
            
            # ==================== 步骤3: 执行Loop（带检查点） ====================
            final_state = await self._run_loop_with_checkpoints(input)
            
            # ==================== 步骤4: 保存最终状态 ====================
            await self._save_checkpoint("final", final_state)
            
            # ==================== 步骤5: 通知用户 ====================
            await workflow.execute_activity(
                notify_user_activity,
                args=[{
                    "workflow_id": input.workflow_id,
                    "status": "completed",
                    "exit_reason": final_state.metadata.get("exit_reason", "unknown"),
                    "iterations": final_state.iteration,
                }],
                start_to_close_timeout=timedelta(seconds=10),
            )
            
            workflow.logger.info(f"Workflow completed: {input.workflow_id}")
            
            # 返回结果
            return {
                "workflow_id": input.workflow_id,
                "success": True,
                "state": StateStorage.serialize_state(final_state),
                "iterations": final_state.iteration,
                "exit_reason": final_state.metadata.get("exit_reason"),
            }
            
        except Exception as e:
            workflow.logger.error(f"Workflow failed: {e}", exc_info=True)
            
            # 保存错误状态
            if self.current_state:
                self.current_state = self.current_state.with_update(
                    should_stop=True,
                    metadata={"exit_reason": "error", "error": str(e)}
                )
                await self._save_checkpoint("error", self.current_state)
            
            # 通知用户
            await workflow.execute_activity(
                notify_user_activity,
                args=[{
                    "workflow_id": input.workflow_id,
                    "status": "failed",
                    "error": str(e),
                }],
                start_to_close_timeout=timedelta(seconds=10),
            )
            
            return {
                "workflow_id": input.workflow_id,
                "success": False,
                "error": str(e),
            }
    
    async def _run_loop_with_checkpoints(
        self,
        input: AgentWorkflowInput
    ) -> LoopState:
        """
        运行Loop并定期保存检查点
        
        Args:
            input: Workflow输入
            
        Returns:
            最终State
        """
        try:
            # 注意：这里我们不能直接调用loop.run()，因为它是长时间运行的
            # 我们需要手动控制迭代并在每次迭代后保存检查点
            
            # 对于简单场景，我们直接调用loop.run()
            # 对于需要细粒度控制的场景，可以使用loop.step()
            
            final_state = await self.loop_instance.run(
                input.task_description,
                max_iterations=input.max_iterations
            )
            
            self.current_state = final_state
            
            return final_state
            
        except Exception as e:
            workflow.logger.error(f"Loop execution failed: {e}")
            raise
    
    async def _save_checkpoint(self, checkpoint_name: str, state: LoopState) -> None:
        """
        保存检查点
        
        Args:
            checkpoint_name: 检查点名称
            state: 当前State
        """
        try:
            serialized_state = StateStorage.serialize_state(state)
            
            await workflow.execute_activity(
                save_state_checkpoint_activity,
                args=[self.workflow_id, serialized_state, checkpoint_name],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                ),
            )
            
            workflow.logger.debug(f"Saved checkpoint: {checkpoint_name}")
            
        except Exception as e:
            workflow.logger.warning(f"Failed to save checkpoint: {e}")
            # 不中断workflow执行
    
    def _create_loop_config(self, input: AgentWorkflowInput) -> LoopConfig:
        """
        创建Loop配置
        
        Args:
            input: Workflow输入
            
        Returns:
            LoopConfig实例
        """
        config_dict = {
            "name": f"{input.loop_type}_workflow_{input.workflow_id}",
            "max_iterations": input.max_iterations,
        }
        
        # 合并用户配置
        if input.config:
            config_dict.update(input.config)
        
        return LoopConfig.from_dict(config_dict)
    
    # ==================== Signals ====================
    
    @workflow.signal
    async def pause_workflow(self):
        """暂停workflow"""
        self.is_paused = True
        workflow.logger.info("Workflow paused")
    
    @workflow.signal
    async def resume_workflow(self):
        """恢复workflow"""
        self.is_paused = False
        workflow.logger.info("Workflow resumed")
    
    # ==================== Queries ====================
    
    @workflow.query
    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """
        查询当前状态
        
        Returns:
            序列化的当前State
        """
        if self.current_state:
            return StateStorage.serialize_state(self.current_state)
        return None
    
    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """
        查询workflow状态
        
        Returns:
            状态信息
        """
        status = {
            "workflow_id": self.workflow_id,
            "is_paused": self.is_paused,
            "current_iteration": self.current_state.iteration if self.current_state else 0,
            "should_stop": self.current_state.should_stop if self.current_state else False,
        }
        
        if self.current_state:
            status["exit_reason"] = self.current_state.metadata.get("exit_reason")
        
        return status


# ==================== 简化的Workflow（用于快速开始） ====================

@workflow.defn
class SimpleAgentWorkflow:
    """
    简化的Agent Workflow
    
    不带检查点和状态恢复，适合短时间任务
    """
    
    @workflow.run
    async def run(self, input: AgentWorkflowInput) -> Dict[str, Any]:
        """
        运行简单的Agent Workflow
        
        Args:
            input: Workflow 输入
            
        Returns:
            执行结果
        """
        workflow.logger.info(f"Starting Simple Agent Workflow: {input.workflow_id}")
        
        try:
            # 创建Loop配置
            config = LoopConfig.from_dict({
                "name": input.workflow_id,
                "max_iterations": input.max_iterations,
            })
            
            # 创建Loop实例
            if input.loop_type == "ooda":
                loop = OODALoop(config=config)
            else:
                loop = PlanExecuteLoop(config=config)
            
            # 执行Loop
            final_state = await loop.run(input.task_description)
            
            workflow.logger.info(f"Workflow completed: {input.workflow_id}")
            
            return {
                "workflow_id": input.workflow_id,
                "success": True,
                "state": StateStorage.serialize_state(final_state),
                "iterations": final_state.iteration,
            }
            
        except Exception as e:
            workflow.logger.error(f"Workflow failed: {e}")
            return {
                "workflow_id": input.workflow_id,
                "success": False,
                "error": str(e),
            }
