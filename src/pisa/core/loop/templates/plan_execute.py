"""
Plan-Execute Loop Template (v4.0 Refactored)

先规划后执行的 Loop，使用 OpenAI Agent SDK。

流程：
1. 接收用户输入
2. 使用 PlanningModule 生成任务计划
3. 使用 ExecutionModule 逐步执行计划
4. 使用 ObserveModule 监控执行状态
5. 根据监控结果决定是否重新规划
6. 使用 ReflectionModule 进行反思
7. 返回最终结果

v4.0架构特点：
- 基于新的BaseAgentLoop（自动初始化）
- State显式流动，Context隐式共享
- 模块自动初始化（planning, execution, observe, reflection）
- 简化的run方法，只包含业务编排

架构设计：
- 继承 BaseAgentLoop，获得自动初始化能力
- 使用 @agent 装饰器注册到 LoopRegistry
- 严格遵循 v4.0 的 State → State 数据流
- 集成已实现的 4 个核心模块
"""

import logging
from typing import Any

from pisa.core.loop.base import BaseAgentLoop
from pisa.core.loop.registry import agent
from pisa.core.loop.state import LoopState
from pisa.core.loop.modules import (
    PlanningModule,
    ExecutionModule,
    ReflectionModule,
    ObserveModule,
    ActionType,
)
from pisa.core.planning import TaskStatus
from pisa.cli.live_display import (
    show_user_query,
    show_planning,
    show_task_execution,
    show_observation,
    show_reflection,
    show_iteration_summary
)

_logger = logging.getLogger(__name__)


@agent(
    name="plan_execute",
    description="Plan-Execute loop: plan first, then execute step by step",
    version="2.0.0"  # v4.0 refactored
)
class PlanExecuteLoop(BaseAgentLoop):
    """
    Plan-Execute Loop (v4.0)
    
    先生成完整计划，然后逐步执行。
    
    特点：
    - 自动初始化所有模块（planning, execution, observe, reflection）
    - State在循环中显式流动
    - Context在模块间隐式共享
    - 支持智能重新规划（基于ObserveModule的决策）
    - 集成反思和验证
    - 适用于复杂、多步骤的任务
    """
    
    # 声明需要的模块
    REQUIRED_MODULES = [
        ('planning', PlanningModule),
        ('execution', ExecutionModule),
        ('observe', ObserveModule),
        ('reflection', ReflectionModule),
    ]
    
    async def run(self, input_data: Any, **kwargs) -> LoopState:
        """
        执行Plan-Execute循环
        
        流程:
        1. Planning: 生成任务计划 → state.plan
        2. Execution: 执行任务 → state.result
        3. Observation: 监控执行 → state.observation
        4. Decision: 决定下一步 → state.decision
        5. Handle: 处理决策（continue/replan/terminate等）
        6. Reflection: 反思总结 → state.orientation
        
        Args:
            input_data: 输入数据（任务描述）
            **kwargs: 额外参数（如max_iterations）
            
        Returns:
            最终的LoopState
        """
        # 运行前钩子
        self.before_run()
        
        try:
            # 初始化State
            task_description = input_data if isinstance(input_data, str) else str(input_data)
            state = LoopState(
                input=task_description,
                task={"description": task_description, "type": "plan_execute_task"}
            )
            
            # 添加任务到Context
            self.context.add_message("user", f"Task: {task_description}")
            
            _logger.info(f"Plan-Execute Loop started: {task_description}")
            
            # 获取最大迭代次数
            max_iterations = kwargs.get('max_iterations', self.config.max_iterations)
            
            # ==================== 阶段1: PLANNING ====================
            _logger.info("=== Phase 1: Planning ===")
            
            # 🎨 显示用户查询
            show_user_query(state.input)
            
            state = await self.planning(state)
            
            # 🎨 显示规划结果
            if state.plan:
                plan_dict = state.plan if isinstance(state.plan, dict) else state.plan.__dict__
                show_planning(iteration=0, plan=plan_dict)
            
            if not state.plan:
                _logger.error("Planning failed: No plan generated")
                return state.with_update(
                    should_stop=True,
                    metadata={"exit_reason": "planning_failed"}
                )
            
            # 获取任务数量（兼容 dict 和 TaskTree）
            plan_tasks = state.plan.get('tasks', {}) if isinstance(state.plan, dict) else getattr(state.plan, 'tasks', {})
            _logger.info(f"Plan created: {len(plan_tasks)} tasks")
            
            # ========== DEBUG: 显示plan内容 ==========
            if self.debug_enabled:
                from pisa.utils.debug import get_debug_manager
                debug_mgr = get_debug_manager()
                debug_mgr.log(
                    "📋 Plan Details",
                    {
                        "total_tasks": len(plan_tasks),
                        "task_ids": list(plan_tasks.keys()) if plan_tasks else [],
                        "plan_type": type(state.plan).__name__
                    }
                )
                
                # 显示前3个任务的详情
                for i, (task_id, task) in enumerate(list(plan_tasks.items())[:3]):
                    task_dict = task if isinstance(task, dict) else task.__dict__
                    debug_mgr.log(
                        f"  Task {i+1}: {task_id}",
                        {
                            "description": task_dict.get('task_description', 'N/A')[:80],
                            "assigned_capability": task_dict.get('assigned_capability', 'N/A'),
                            "status": str(task_dict.get('status', 'N/A'))
                        }
                    )
            
            # ==================== 阶段2: EXECUTION LOOP ====================
            # 添加重规划计数器，避免无限重规划
            replan_count = 0
            max_replans = 3
            
            for iteration in range(max_iterations):
                self.on_iteration()
                state = state.with_update(iteration=iteration)
                
                _logger.info(f"=== Iteration {iteration + 1}/{max_iterations} ===")
                
                # ========== DEBUG: 第二层 - Context/Message观察 ==========
                if self.debug_enabled:
                    from pisa.utils.debug import get_debug_manager
                    debug_mgr = get_debug_manager()
                    
                    # 获取当前context状态
                    messages = []
                    if hasattr(self.context, 'manager') and hasattr(self.context.manager, 'get_messages'):
                        messages = [msg.model_dump() for msg in self.context.manager.get_messages()]
                    
                    debug_mgr.display_context_state(
                        iteration=iteration,
                        messages=messages,
                        token_count=self.context.get_token_count() if hasattr(self.context, 'get_token_count') else 0
                    )
                
                # 检查是否所有任务都完成
                if self._all_tasks_completed(state):
                    _logger.info("All tasks completed successfully")
                    state = state.with_update(
                        should_stop=True,
                        metadata={
                            "exit_reason": "success",
                            "iterations": iteration + 1,
                            "success": True
                        }
                    )
                    break
                
                # ---------- 2.1: Select Next Task ----------
                _logger.info("Step: Selecting next task from plan")
                next_task = self._select_next_task(state)
                
                if not next_task:
                    _logger.warning("No task available to execute")
                    break
                
                _logger.info(f"Selected task: {next_task.get('task_id') if isinstance(next_task, dict) else next_task.task_id}")
                state = state.with_update(task=next_task)
                
                # ---------- 2.2: Execute Current Task ----------
                _logger.info("Step: Executing current task")
                state = await self.execution(state)
                
                # 🎨 显示任务执行结果
                if state.result:
                    task_id = next_task.get('task_id') if isinstance(next_task, dict) else next_task.task_id
                    capability = next_task.get('assigned_capability') if isinstance(next_task, dict) else getattr(next_task, 'assigned_capability', 'N/A')
                    
                    # 提取工具输入（从 task_detail_info）
                    tool_input = next_task.get('task_detail_info', {}) if isinstance(next_task, dict) else getattr(next_task, 'task_detail_info', {})
                    
                    # 提取工具输出
                    if isinstance(state.result, dict):
                        tool_output = state.result.get('result', state.result)
                        success = state.result.get('success', False)
                    else:
                        tool_output = getattr(state.result, 'result', state.result)
                        success = getattr(state.result, 'success', False)
                    
                    show_task_execution(
                        iteration=iteration + 1,
                        task_id=task_id,
                        capability=capability,
                        tool_input=tool_input,
                        tool_output=tool_output,
                        success=success
                    )
                
                # ⭐ 更新任务状态为 COMPLETED（如果执行成功）
                if state.result and state.plan:
                    result_success = False
                    if isinstance(state.result, dict):
                        result_success = state.result.get('success', False)
                    elif hasattr(state.result, 'success'):
                        result_success = state.result.success
                    
                    if result_success:
                        # 获取当前任务 ID
                        current_task_id = next_task.get('task_id') if isinstance(next_task, dict) else next_task.task_id
                        
                        # 更新 plan 中的任务状态
                        if isinstance(state.plan, dict):
                            tasks = state.plan.get('tasks', {})
                            if current_task_id in tasks:
                                if isinstance(tasks[current_task_id], dict):
                                    tasks[current_task_id]['status'] = TaskStatus.COMPLETED
                                else:
                                    tasks[current_task_id].status = TaskStatus.COMPLETED
                                _logger.info(f"✅ Task {current_task_id} marked as COMPLETED")
                        else:
                            tasks = getattr(state.plan, 'tasks', {})
                            if current_task_id in tasks:
                                tasks[current_task_id].status = TaskStatus.COMPLETED
                                _logger.info(f"✅ Task {current_task_id} marked as COMPLETED")
                
                # ---------- 2.3: Observe Execution ----------
                _logger.info("Step: Observing execution")
                state = await self.observe(state)
                
                # 🎨 显示观察结果
                if state.observation:
                    task_id = next_task.get('task_id') if isinstance(next_task, dict) else next_task.task_id
                    
                    if isinstance(state.observation, dict):
                        obs_success = state.observation.get('success', False)
                        error_type = state.observation.get('error_type')
                    else:
                        obs_success = getattr(state.observation, 'success', False)
                        error_type = getattr(state.observation, 'error_type', None)
                    
                    # 获取决策信息
                    decision_action = "CONTINUE"
                    decision_reason = "Observation completed"
                    if state.decision:
                        if isinstance(state.decision, dict):
                            decision_action = state.decision.get('action', 'CONTINUE')
                            decision_reason = state.decision.get('reason', '')
                        else:
                            decision_action = getattr(state.decision, 'action', 'CONTINUE')
                            decision_reason = getattr(state.decision, 'reason', '')
                    
                    show_observation(
                        iteration=iteration + 1,
                        task_id=task_id,
                        success=obs_success,
                        error_type=str(error_type) if error_type else None,
                        decision=str(decision_action),
                        reason=decision_reason
                    )
                
                if not state.observation:
                    _logger.warning("No observation available")
                    continue
                
                _logger.info(f"Observation: {state.observation}")
                
                # ---------- 2.3: Decide Next Action ----------
                _logger.info("Step: Deciding next action")
                state = await self.observe.decide(state)
                
                if not state.decision:
                    _logger.warning("No decision made")
                    continue
                
                decision = state.decision
                _logger.info(f"Decision: {decision.action} - {decision.reason}")
                _logger.info(f"DEBUG: decision.action type={type(decision.action)}, value={repr(decision.action)}")
                _logger.info(f"DEBUG: ActionType.CONTINUE type={type(ActionType.CONTINUE)}, value={repr(ActionType.CONTINUE)}")
                _logger.info(f"DEBUG: comparison result={decision.action == ActionType.CONTINUE}")
                
                # ---------- 2.4: Handle Decision ----------
                _logger.info("Step: Handling decision")
                
                if decision.action == ActionType.CONTINUE:
                    # 继续执行下一个任务 - 但首先检查是否所有任务都已完成
                    all_done = self._all_tasks_completed(state)
                    _logger.info(f"Checking if all tasks completed: {all_done}")
                    
                    if all_done:
                        _logger.info("✅ All tasks completed successfully!")
                        state = state.with_update(
                            should_stop=True,
                            metadata={
                                "exit_reason": "all_tasks_completed",
                                "iterations": iteration + 1,
                                "success": True
                            }
                        )
                        break
                    _logger.info("Action: Continue to next task")
                    continue
                    
                elif decision.action == ActionType.RETRY:
                    # 重试当前任务
                    _logger.info("Action: Retrying current task")
                    # 执行模块会处理重试逻辑
                    continue
                    
                elif decision.action in [ActionType.REPLAN_TASK, ActionType.REPLAN_ALL]:
                    # 重新规划
                    replan_count += 1
                    _logger.info(f"Action: Replanning ({decision.action}) - Count: {replan_count}/{max_replans}")
                    
                    # 检查是否超过重规划次数限制
                    if replan_count > max_replans:
                        _logger.error(f"Exceeded maximum replan attempts ({max_replans})")
                        state = state.with_update(
                            should_stop=True,
                            metadata={
                                "exit_reason": "max_replans_exceeded",
                                "iterations": iteration + 1,
                                "replan_count": replan_count
                            }
                        )
                        break
                    
                    # 调用PlanningModule的replan方法
                    state = await self.planning.replan(state)
                    
                    if not state.plan:
                        _logger.error("Replanning failed")
                        state = state.with_update(
                            should_stop=True,
                            metadata={"exit_reason": "replan_failed", "iterations": iteration + 1}
                        )
                        break
                    
                    # 获取任务数量（兼容 dict 和 TaskTree）
                    plan_tasks = state.plan.get('tasks', {}) if isinstance(state.plan, dict) else getattr(state.plan, 'tasks', {})
                    _logger.info(f"Replanned: {len(plan_tasks)} tasks")
                    continue
                    
                elif decision.action == ActionType.ESCALATE:
                    # 上报问题
                    _logger.warning("Action: Escalating issue")
                    state = state.with_update(
                        should_stop=True,
                        metadata={
                            "exit_reason": "escalated",
                            "issue": decision.reason,
                            "iterations": iteration + 1
                        }
                    )
                    break
                    
                elif decision.action == ActionType.TERMINATE:
                    # 终止循环
                    _logger.info("Action: Terminating loop")
                    state = state.with_update(
                        should_stop=True,
                        metadata={
                            "exit_reason": "terminated",
                            "reason": decision.reason,
                            "iterations": iteration + 1
                        }
                    )
                    break
                
                # 🎨 显示迭代摘要
                tasks_completed = 0
                total_tasks = 0
                if state.plan:
                    plan_tasks = state.plan.get('tasks', {}) if isinstance(state.plan, dict) else getattr(state.plan, 'tasks', {})
                    total_tasks = len(plan_tasks)
                    for task in plan_tasks.values():
                        task_status = task.get('status') if isinstance(task, dict) else getattr(task, 'status', None)
                        if task_status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                            tasks_completed += 1
                
                show_iteration_summary(iteration + 1, tasks_completed, total_tasks)
                
                # 检查是否达到最大迭代次数
                if iteration + 1 >= max_iterations:
                    _logger.warning("Reached maximum iterations")
                    # 检查任务是否实际完成
                    all_done = self._all_tasks_completed(state)
                    _logger.info(f"🔍 DEBUG: all_tasks_completed = {all_done}")
                    
                    # 如果有 result 且任务完成，认为成功
                    has_result = state.result is not None
                    _logger.info(f"🔍 DEBUG: has_result = {has_result}, result = {state.result}")
                    
                    success = all_done or (has_result and state.observation and getattr(state.observation, 'success', False))
                    _logger.info(f"🔍 DEBUG: final success = {success}")
                    
                    state = state.with_update(
                        should_stop=True,
                        metadata={
                            "exit_reason": "max_iterations",
                            "iterations": iteration + 1,
                            "success": success,
                            "all_tasks_completed": all_done,
                            "has_result": has_result
                        }
                    )
                    break
            
            # ==================== 阶段3: REFLECTION ====================
            _logger.info("=== Phase 3: Reflection ===")
            state = await self.reflection(state)
            
            # 🎨 显示反思结果
            if state.orientation:
                _logger.info(f"Reflection completed: {state.orientation}")
                
                # 提取反思信息
                task_desc = "Overall execution"
                if state.task:
                    task_desc = state.task.get('task_description', 'Overall execution') if isinstance(state.task, dict) else getattr(state.task, 'task_description', 'Overall execution')
                
                if isinstance(state.orientation, dict):
                    success_eval = state.orientation.get('success_evaluation', True)
                    quality = state.orientation.get('quality_score', 0.8)
                    analysis = state.orientation.get('analysis', str(state.orientation))
                elif isinstance(state.orientation, str):
                    success_eval = True
                    quality = 0.8
                    analysis = state.orientation
                else:
                    success_eval = getattr(state.orientation, 'success_evaluation', True)
                    quality = getattr(state.orientation, 'quality_score', 0.8)
                    analysis = getattr(state.orientation, 'analysis', str(state.orientation))
                
                show_reflection(
                    iteration=state.iteration or 0,
                    task_description=task_desc,
                    success_evaluation=success_eval,
                    quality_score=quality,
                    analysis=analysis
                )
            
            # 运行后钩子
            self.after_run(success=state.should_stop)
            
            _logger.info(f"Plan-Execute Loop completed: {state.metadata.get('exit_reason', 'unknown')}")
            
            return state
            
        except Exception as e:
            _logger.error(f"Plan-Execute Loop failed: {e}", exc_info=True)
            self.after_run(success=False)
            
            # 返回失败状态
            return LoopState(
                input=input_data,
                should_stop=True,
                metadata={"exit_reason": "error", "error": str(e)}
            )
    
    def _select_next_task(self, state: LoopState):
        """
        从 plan 中选择下一个待执行的任务
        
        Args:
            state: 当前状态
            
        Returns:
            下一个任务（dict 或 TaskNode），如果没有则返回 None
        """
        if not state.plan:
            return None
        
        # 处理 plan 可能是 dict 或 TaskTree 对象的情况
        if isinstance(state.plan, dict):
            tasks = state.plan.get('tasks', {})
            execution_order = state.plan.get('execution_order', list(tasks.keys()))
        else:
            tasks = getattr(state.plan, 'tasks', {})
            execution_order = getattr(state.plan, 'execution_order', list(tasks.keys()))
        
        if not tasks:
            return None
        
        # 按照执行顺序查找第一个 PENDING 或 READY 的任务
        for task_id in execution_order:
            task = tasks.get(task_id)
            if not task:
                continue
            
            # 获取任务状态
            if isinstance(task, dict):
                task_status = task.get('status', 'pending')
            else:
                task_status = getattr(task, 'status', 'pending')
            
            # 选择第一个待执行的任务
            if task_status in [TaskStatus.PENDING, TaskStatus.READY]:
                return task
        
        # 没有找到待执行的任务
        return None
    
    def _all_tasks_completed(self, state: LoopState) -> bool:
        """
        检查是否所有任务都已完成
        
        Args:
            state: 当前状态
            
        Returns:
            是否所有任务都完成
        """
        if not state.plan:
            return False
        
        # 处理 plan 可能是 dict 或 TaskTree 对象的情况
        if isinstance(state.plan, dict):
            tasks = state.plan.get('tasks', {})
        else:
            tasks = getattr(state.plan, 'tasks', {})
        
        if not tasks:
            return False
        
        # 检查所有任务的状态
        for task in tasks.values():
            # 处理 task 可能是 dict 或 TaskNode 对象
            if isinstance(task, dict):
                task_status = task.get('status')
            else:
                task_status = getattr(task, 'status', None)
            
            if task_status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                return False
        
        return True
