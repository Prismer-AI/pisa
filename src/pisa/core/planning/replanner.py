"""
Replanner

重新规划器，当任务执行失败或遇到问题时动态调整计划。

改进：
- 严格遵循 OpenAI Agent SDK
- 基于执行反馈进行智能重规划
- 保留计划历史和版本管理
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from pisa.config import Config
from .task_tree import TaskTree, TaskNode, TaskStatus
from .planner import Planner

_logger = logging.getLogger(__name__)


class Replanner:
    """
    重新规划器
    
    当遇到以下情况时触发重新规划：
    1. 任务执行失败
    2. 发现缺少依赖
    3. 环境变化导致原计划不可行
    4. 用户反馈需要调整
    """
    
    def __init__(
        self,
        instructions: Optional[str] = None,
        model: Optional[str] = None,
        **agent_kwargs
    ):
        """
        初始化重规划器
        
        Args:
            instructions: 重规划 agent 的指令
            model: 使用的模型
            **agent_kwargs: 传递给 Agent 的额外参数
        """
        # 确保 Agent SDK 已配置
        Config.setup_agent_sdk()
        
        self.model = model or Config.agent_default_model
        
        # 重规划的默认指令
        self.instructions = instructions or self._get_default_instructions()
        
        # 额外的 agent 参数
        self.agent_kwargs = agent_kwargs
        
        # 内部使用 Planner 来生成新计划
        self.planner = Planner(
            instructions=self.instructions,
            model=self.model,
            **agent_kwargs
        )
        
        _logger.info(f"Replanner initialized with model: {self.model}")
    
    async def replan(
        self,
        original_plan: TaskTree,
        failed_tasks: List[TaskNode],
        context: Optional[Dict[str, Any]] = None
    ) -> TaskTree:
        """
        重新规划任务树
        
        Args:
            original_plan: 原始任务树
            failed_tasks: 失败的任务列表
            context: 上下文信息
        
        Returns:
            更新后的任务树
        """
        _logger.info(f"Replanning with {len(failed_tasks)} failed tasks")
        
        try:
            # 简单策略：标记失败任务，保留其他任务
            for failed_task in failed_tasks:
                if hasattr(failed_task, 'task_id'):
                    original_plan.mark_failed(failed_task.task_id, "Task failed during execution")
            
            _logger.info("Replan completed")
            return original_plan
            
        except Exception as e:
            _logger.error(f"Replan failed: {e}")
            return original_plan
    
    def _get_default_instructions(self) -> str:
        """获取默认的重规划指令"""
        return """You are an expert task replanner. Your job is to analyze failed or problematic tasks and create improved plans.

**Guidelines**:
1. Analyze WHY the original plan failed or needs adjustment
2. Learn from failures and avoid repeating mistakes
3. Consider alternative approaches and strategies
4. Preserve successful parts of the original plan when possible
5. Be realistic about constraints and limitations
6. Provide clear reasoning for changes

**Replanning Strategies**:
- **Decompose**: Break failed task into smaller sub-tasks
- **Alternative**: Use different capabilities or approaches
- **Sequential**: Change parallel tasks to sequential if dependencies were wrong
- **Skip**: Mark tasks as unnecessary if they don't serve the goal
- **Retry**: Keep the task but adjust parameters or context

**Output Format**:
Return a JSON object with:
{
    "analysis": "Why the original plan failed/needs adjustment",
    "strategy": "Your replanning strategy (decompose/alternative/sequential/skip/retry)",
    "reasoning": "Detailed reasoning for the changes",
    "tasks": [
        {
            "task_id": "unique_id",
            "description": "What needs to be done",
            "detail_info": {
                "steps": ["step 1", "step 2"],
                "changes_from_original": "What changed and why",
                "risk_mitigation": "How to avoid previous failures"
            },
            "dependencies": ["task_id_1"],
            "assigned_capability": "capability_name or null"
        }
    ],
    "execution_order": ["task_1", "task_2"]
}
"""
    
    async def replan_on_failure(
        self,
        task_tree: TaskTree,
        failed_task: TaskNode,
        error_context: Dict[str, Any]
    ) -> TaskTree:
        """
        基于失败任务重新规划
        
        Args:
            task_tree: 当前任务树
            failed_task: 失败的任务
            error_context: 错误上下文（包括错误信息、执行日志等）
            
        Returns:
            更新后的任务树
        """
        _logger.info(f"Replanning due to task failure: {failed_task.task_id}")
        
        # 构建反馈信息
        feedback = self._build_failure_feedback(failed_task, error_context)
        
        # 使用 Planner 的 refine_plan 方法
        refined_tree = await self.planner.refine_plan(
            task_tree=task_tree,
            feedback=feedback,
            context=error_context
        )
        
        return refined_tree
    
    async def replan_on_block(
        self,
        task_tree: TaskTree,
        blocked_tasks: List[TaskNode],
        reason: str
    ) -> TaskTree:
        """
        当任务被阻塞时重新规划
        
        Args:
            task_tree: 当前任务树
            blocked_tasks: 被阻塞的任务列表
            reason: 阻塞原因
            
        Returns:
            更新后的任务树
        """
        _logger.info(f"Replanning due to blocked tasks: {len(blocked_tasks)} tasks")
        
        feedback = f"""**Blocking Issue**: {reason}

**Blocked Tasks**:
{chr(10).join(f'- {task.task_id}: {task.task_description}' for task in blocked_tasks)}

The execution is blocked. Please adjust the plan to:
1. Resolve dependencies issues
2. Find alternative approaches
3. Or mark tasks as skippable if they're not critical
"""
        
        refined_tree = await self.planner.refine_plan(
            task_tree=task_tree,
            feedback=feedback,
            context={"blocked_tasks": [t.task_id for t in blocked_tasks], "reason": reason}
        )
        
        return refined_tree
    
    async def replan_on_discovery(
        self,
        task_tree: TaskTree,
        discovery: str,
        affected_tasks: Optional[List[str]] = None
    ) -> TaskTree:
        """
        当发现新信息导致需要调整计划时重新规划
        
        Args:
            task_tree: 当前任务树
            discovery: 新发现的信息
            affected_tasks: 受影响的任务ID列表
            
        Returns:
            更新后的任务树
        """
        _logger.info(f"Replanning due to new discovery: {discovery}")
        
        feedback = f"""**New Discovery**: {discovery}

This new information may affect the current plan.
"""
        
        if affected_tasks:
            feedback += f"\n**Potentially Affected Tasks**: {', '.join(affected_tasks)}"
        
        feedback += "\n\nPlease adjust the plan to incorporate this new information."
        
        refined_tree = await self.planner.refine_plan(
            task_tree=task_tree,
            feedback=feedback,
            context={"discovery": discovery, "affected_tasks": affected_tasks or []}
        )
        
        return refined_tree
    
    def _build_failure_feedback(
        self,
        failed_task: TaskNode,
        error_context: Dict[str, Any]
    ) -> str:
        """构建失败任务的反馈信息"""
        feedback_parts = [
            f"**Failed Task**: {failed_task.task_id}",
            f"**Description**: {failed_task.task_description}",
            f"**Error**: {failed_task.error or 'Unknown error'}",
        ]
        
        if failed_task.task_detail_info:
            feedback_parts.append(
                f"**Task Details**: {failed_task.task_detail_info}"
            )
        
        if error_context:
            feedback_parts.append(
                f"**Error Context**: {error_context}"
            )
        
        feedback_parts.append("""
Please analyze this failure and create an improved plan. Consider:
1. Why did this task fail?
2. Should we try a different approach?
3. Should we break it down into smaller tasks?
4. Are there missing dependencies?
5. Should we skip this task if it's not critical?
""")
        
        return "\n\n".join(feedback_parts)
    
    def should_replan(
        self,
        task_tree: TaskTree,
        failure_threshold: int = 3
    ) -> bool:
        """
        判断是否应该触发重新规划
        
        Args:            task_tree: 当前任务树
            failure_threshold: 失败任务数量阈值
            
        Returns:            是否应该重新规划
        """
        # 统计失败任务
        failed_count = sum(
            1 for task in task_tree.tasks.values()
            if task.status == TaskStatus.FAILED
        )
        
        # 检查是否有被阻塞的任务
        blocked_count = sum(
            1 for task in task_tree.tasks.values()
            if task.status == TaskStatus.BLOCKED
        )
        
        # 检查是否有就绪任务
        ready_tasks = task_tree.get_ready_tasks()
        
        # 触发重新规划的条件
        should_replan = (
            failed_count >= failure_threshold  # 失败任务过多
            or (blocked_count > 0 and len(ready_tasks) == 0)  # 有阻塞且无就绪任务
            or (not task_tree.is_completed() and len(ready_tasks) == 0 and failed_count > 0)  # 卡住了
        )
        
        if should_replan:
            _logger.warning(
                f"Replanning triggered: {failed_count} failed, "
                f"{blocked_count} blocked, {len(ready_tasks)} ready"
            )
        
        return should_replan