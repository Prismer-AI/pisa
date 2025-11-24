"""
Planning Module (Refactored v4.0)

任务规划模块，作为 Agent Loop 的规划组件。

核心接口：
- __call__(state) → state  # 默认规划操作（创建新计划）
- replan(state) → state    # 重新规划操作

改进：
- 整合 src/pisa/core/planning 下的 Planner, Replanner, TaskTree
- 规划原则由上层 instruction 控制
- 支持动态重新规划
- 输出结构化的任务树
- 继承 BaseModule，支持配置透传和可观测性
"""

import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from pisa.core.loop.state import LoopState
    from pisa.core.loop.context import LoopContext

from pisa.core.planning import Planner, Replanner, TaskTree, TaskNode, TaskStatus
from .base import BaseModule, PlanningModuleConfig

_logger = logging.getLogger(__name__)


class PlanningModule(BaseModule):
    """
    规划模块（重构版v4.0）
    
    职责：
    1. 根据目标生成任务计划
    2. 动态调整计划（重新规划）
    3. 管理任务树状态
    4. 提供任务执行顺序
    
    新接口：
    - __call__(state) → state  # 默认规划操作（创建新计划）
    - replan(state) → state    # 重新规划操作
    
    改进：
    - 使用 src/pisa/core/planning 下的专业模块
    - 不硬编码规划策略，由 instructions 控制
    - 严格遵循 OpenAI Agent SDK
    """
    
    # ==================== 依赖声明 ====================
    
    STATE_REQUIRES = ['input']  # 默认需要input来创建计划
    STATE_PRODUCES = ['plan', 'metadata']
    
    # ==================== 初始化 ====================
    
    def __init__(
        self,
        config: Optional[PlanningModuleConfig] = None,
        loop_context: Optional['LoopContext'] = None,
        loop_state: Optional['LoopState'] = None,
        loop: Optional[Any] = None,
        planning_instructions: Optional[str] = None,
        replanning_instructions: Optional[str] = None,
        **agent_kwargs
    ):
        """
        初始化规划模块
        
        Args:
            config: 规划模块配置
            loop_context: Loop的LLM交互上下文（共享）
            loop_state: Loop的业务状态（共享，可选）
            loop: BaseAgentLoop 引用
            planning_instructions: 规划 agent 的指令（控制规划原则）
            replanning_instructions: 重规划 agent 的指令
            **agent_kwargs: 传递给 Agent 的额外参数
        """
        # 初始化配置
        if config is None:
            config = PlanningModuleConfig()
        
        # 调用基类初始化
        super().__init__(
            config=config,
            loop_context=loop_context,
            loop_state=loop_state,
            loop=loop,
            module_type="PlanningModule",
            **agent_kwargs
        )
        
        # 解析模型配置（优先使用 planning_model）
        planning_model = config.planning_model or self.model
        replanning_model = config.replanning_model or self.model
        
        # 创建 Planner 和 Replanner
        self.planner = Planner(
            instructions=planning_instructions,
            model=planning_model,
            **agent_kwargs
        )
        
        self.replanner = Replanner(
            instructions=replanning_instructions,
            model=replanning_model,
            **agent_kwargs
        )
        
        # 当前任务树（可能为空）
        self.current_tree: Optional[TaskTree] = None
        
        self.logger.info(
            "PlanningModule initialized",
            planning_model=planning_model,
            replanning_model=replanning_model,
            has_context=self.context is not None
        )
    
    def _init_stats(self) -> Dict[str, Any]:
        """初始化统计信息"""
        return {
            "module_type": "PlanningModule",
            "plans_created": 0,
            "replans_triggered": 0,
            "total_tasks_planned": 0,
            "initialized": False,
        }
    
    # ==================== 新接口（State → State）====================
    
    async def _execute(self, state: 'LoopState') -> Dict[str, Any]:
        """
        默认的规划操作：创建新计划（State → State接口）
        
        Args:
            state: 输入State（需要input字段）
        
        Returns:
            包含plan和metadata的字典
        """
        task_description = state.input
        task_detail_info = state.metadata.get('task_detail', {})
        
        # ========== 获取available capabilities ==========
        available_capabilities = []
        
        if self.loop:
            # 从loop中获取已注册的capabilities
            cap_registry = getattr(self.loop, 'capability_registry', None)
            
            if cap_registry:
                available_capabilities = cap_registry.list_all()
                _logger.info(f"📋 Got {len(available_capabilities)} capabilities from registry")
            else:
                _logger.warning("⚠️ No capability_registry found in loop")
        else:
            _logger.warning("⚠️ No loop reference in PlanningModule")
        
        # 调用planner创建计划（传递available capabilities）
        _logger.info(f"🎯 Calling planner.create_plan with {len(available_capabilities)} capabilities")
        task_tree = await self.planner.create_plan(
            goal=task_description,
            context=task_detail_info,
            available_capabilities=available_capabilities  # ← 关键：传递可用capabilities
        )
        
        # 更新统计
        self.stats["plans_created"] = self.stats.get("plans_created", 0) + 1
        self.stats["total_tasks_planned"] = self.stats.get("total_tasks_planned", 0) + len(task_tree.tasks)
        
        # 保存当前任务树
        self.current_tree = task_tree
        
        # 更新到Context（可选）
        if self.context:
            self.context.add_message(
                role="system",
                content=f"Created plan with {len(task_tree.tasks)} tasks"
            )
        
        return {
            "plan": task_tree,
            "metadata": {
                **state.metadata,
                "planning": {
                    "total_tasks": len(task_tree.tasks),
                    "plan_created": True
                }
            }
        }
    
    async def replan(self, state: 'LoopState') -> 'LoopState':
        """
        重新规划操作（额外方法）
        
        Args:
            state: 输入State（需要plan和observation）
        
        Returns:
            包含新plan的State
        """
        if state.plan is None:
            raise ValueError("PlanningModule.replan requires state.plan")
        
        # 获取失败任务（如果有）
        failed_tasks = []
        if hasattr(state, 'result') and state.result:
            # 从result中提取失败任务
            if hasattr(state.result, 'failed_tasks'):
                failed_tasks = state.result.failed_tasks
        
        # 调用replanner（使用真实的方法签名）
        new_tree = await self.replanner.replan(
            original_plan=state.plan,
            failed_tasks=failed_tasks
        )
        
        # 更新统计
        self.stats["replans_triggered"] = self.stats.get("replans_triggered", 0) + 1
        
        # 保存当前任务树
        self.current_tree = new_tree
        
        # 获取任务数量（兼容dict和TaskTree）
        num_tasks = 0
        if isinstance(new_tree, dict):
            num_tasks = len(new_tree.get('tasks', {}))
        else:
            num_tasks = len(getattr(new_tree, 'tasks', {}))
        
        # 更新到Context（可选）
        if self.context:
            self.context.add_message(
                role="system",
                content=f"Replanned: {num_tasks} tasks"
            )
        
        return state.with_update(
            plan=new_tree,
            metadata={
                **state.metadata,
                "planning": {
                    "total_tasks": num_tasks,  # 使用前面计算好的值
                    "replanned": True
                }
            }
        )
    
    # ==================== 保留的业务逻辑 ====================
    
    async def _replan_legacy(
        self,
        task_tree: TaskTree,
        failed_tasks: List[TaskNode],
        context: Optional[Dict[str, Any]] = None
    ) -> TaskTree:
        """
        重新规划任务树
        
        Args:
            task_tree: 当前任务树
            failed_tasks: 失败的任务列表
            context: 上下文信息
        
        Returns:
            更新后的任务树
        """
        self.log_operation("replan", status="running", failed_tasks_count=len(failed_tasks))
        
        try:
            # 使用 Replanner 进行重新规划
            updated_tree = await self.replanner.replan(
                original_plan=task_tree,
                failed_tasks=failed_tasks,
                context=context or {}
            )
            
            # 更新统计
            self.stats["replans_triggered"] += 1
            
            self.log_operation(
                "replan",
                status="success",
                new_tasks_count=len(updated_tree.root.children) if updated_tree.root else 0
            )
            
            return updated_tree
            
        except Exception as e:
            self.log_operation("replan", status="error", error=str(e))
            # 如果重新规划失败，返回原任务树
            return task_tree
    
    async def create_plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        available_capabilities: Optional[List[str]] = None
    ) -> TaskTree:
        """
        根据目标创建任务计划
        
        Args:
            goal: 目标描述
            context: 上下文信息
            available_capabilities: 可用的 capabilities 列表
            
        Returns:
            TaskTree 对象
        """
        self.log_operation("create_plan", status="running", goal=goal)
        
        # 使用 Planner 创建计划
        task_tree = await self.planner.create_plan(
            goal=goal,
            context=context,
            available_capabilities=available_capabilities
        )
        
        # 更新当前任务树
        self.current_tree = task_tree
        
        # 更新统计
        self.stats["plans_created"] += 1
        self.stats["total_tasks_planned"] += len(task_tree.tasks)
        
        self.log_operation(
            "create_plan",
            status="success",
            tasks_count=len(task_tree.tasks),
            plan_version=task_tree.plan_version
        )
        
        return task_tree
    
    async def replan_on_failure(
        self,
        failed_task: TaskNode,
        error_context: Dict[str, Any]
    ) -> TaskTree:
        """
        基于失败任务重新规划
        
        Args:
            failed_task: 失败的任务
            error_context: 错误上下文
            
        Returns:
            更新后的任务树
        """
        if self.current_tree is None:
            raise ValueError("No current task tree to replan")
        
        _logger.info(f"Replanning on failure: {failed_task.task_id}")
        
        # 使用 Replanner 重新规划
        refined_tree = await self.replanner.replan_on_failure(
            task_tree=self.current_tree,
            failed_task=failed_task,
            error_context=error_context
        )
        
        # 更新当前任务树
        self.current_tree = refined_tree
        
        # 更新统计
        self.stats["replans_triggered"] += 1
        
        _logger.info(f"Plan refined to version {refined_tree.plan_version}")
        
        return refined_tree
    
    async def replan_on_block(
        self,
        blocked_tasks: List[TaskNode],
        reason: str
    ) -> TaskTree:
        """
        当任务被阻塞时重新规划
        
        Args:
            blocked_tasks: 被阻塞的任务列表
            reason: 阻塞原因
            
        Returns:
            更新后的任务树
        """
        if self.current_tree is None:
            raise ValueError("No current task tree to replan")
        
        _logger.info(f"Replanning on block: {len(blocked_tasks)} tasks")
        
        refined_tree = await self.replanner.replan_on_block(
            task_tree=self.current_tree,
            blocked_tasks=blocked_tasks,
            reason=reason
        )
        
        self.current_tree = refined_tree
        self.stats["replans_triggered"] += 1
        
        return refined_tree
    
    async def replan_on_discovery(
        self,
        discovery: str,
        affected_tasks: Optional[List[str]] = None
    ) -> TaskTree:
        """
        当发现新信息时重新规划
        
        Args:
            discovery: 新发现的信息
            affected_tasks: 受影响的任务ID列表
            
        Returns:
            更新后的任务树
        """
        if self.current_tree is None:
            raise ValueError("No current task tree to replan")
        
        _logger.info(f"Replanning on discovery: {discovery}")
        
        refined_tree = await self.replanner.replan_on_discovery(
            task_tree=self.current_tree,
            discovery=discovery,
            affected_tasks=affected_tasks
        )
        
        self.current_tree = refined_tree
        self.stats["replans_triggered"] += 1
        
        return refined_tree
    
    def get_next_task(self) -> Optional[TaskNode]:
        """
        获取下一个要执行的任务
        
        Returns:
            下一个任务，如果没有则返回 None
        """
        if self.current_tree is None:
            return None
        
        return self.current_tree.get_next_task()
    
    def mark_task_completed(
        self,
        task_id: str,
        result: Any = None,
        agent_output: Optional[Dict] = None
    ) -> None:
        """
        标记任务为已完成
        
        Args:
            task_id: 任务ID
            result: 执行结果
            agent_output: Agent 的结构化输出
        """
        if self.current_tree is None:
            raise ValueError("No current task tree")
        
        task = self.current_tree.get_task(task_id)
        if task:
            task.mark_completed(result=result, agent_output=agent_output)
            _logger.info(f"Task marked as completed: {task_id}")
        else:
            _logger.warning(f"Task not found: {task_id}")
    
    def mark_task_failed(self, task_id: str, error: str) -> None:
        """
        标记任务为失败
        
        Args:
            task_id: 任务ID
            error: 错误信息
        """
        if self.current_tree is None:
            raise ValueError("No current task tree")
        
        task = self.current_tree.get_task(task_id)
        if task:
            task.mark_failed(error=error)
            _logger.error(f"Task marked as failed: {task_id} - {error}")
        else:
            _logger.warning(f"Task not found: {task_id}")
    
    def mark_task_running(self, task_id: str) -> None:
        """
        标记任务为运行中
        
        Args:
            task_id: 任务ID
        """
        if self.current_tree is None:
            raise ValueError("No current task tree")
        
        task = self.current_tree.get_task(task_id)
        if task:
            task.mark_running()
            self.current_tree.current_task_id = task_id
            _logger.info(f"Task marked as running: {task_id}")
        else:
            _logger.warning(f"Task not found: {task_id}")
    
    def should_replan(self, failure_threshold: int = 3) -> bool:
        """
        判断是否应该触发重新规划
        
        Args:
            failure_threshold: 失败任务数量阈值
            
        Returns:
            是否应该重新规划
        """
        if self.current_tree is None:
            return False
        
        return self.replanner.should_replan(
            task_tree=self.current_tree,
            failure_threshold=failure_threshold
        )
    
    def get_tree_statistics(self) -> Dict[str, Any]:
        """
        获取任务树统计信息
        
        Returns:
            统计信息字典
        """
        if self.current_tree is None:
            return {
                "has_tree": False,
                "module_stats": self.stats
            }
        
        tree_stats = self.current_tree.get_statistics()
        
        return {
            "has_tree": True,
            "tree_stats": tree_stats,
            "module_stats": self.stats,
        }
    
    def is_plan_completed(self) -> bool:
        """判断计划是否已完成"""
        if self.current_tree is None:
            return False
        
        return self.current_tree.is_completed()
    
    def get_current_tree(self) -> Optional[TaskTree]:
        """获取当前任务树"""
        return self.current_tree
