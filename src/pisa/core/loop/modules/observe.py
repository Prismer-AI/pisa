"""
Observe Module - 观察与决策模块

职责：
1. Observe (观察): 收集和分析执行结果
2. Orient (理解): 根因分析和模式识别  
3. Decide (决策): 基于分析结果做出行动决策

这是实现OODA循环的核心组件。
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from agents import Agent, Runner
    from pisa.core.loop.state import LoopState
    from pisa.core.loop.context import LoopContext

from pisa.core.loop.modules.base import BaseModule, ModuleConfig, ObserveModuleConfig
from pisa.core.planning.task_tree import TaskTree, TaskNode, TaskStatus
from pisa.utils.logger import get_logger

_logger = get_logger(__name__)


# ===== Enums ===== #

class ObservationType(str, Enum):
    """观察类型"""
    TASK_EXECUTION = "task_execution"
    PLAN_PROGRESS = "plan_progress"
    CONTEXT_STATE = "context_state"
    CAPABILITY_HEALTH = "capability_health"


class FailureType(str, Enum):
    """失败类型分类"""
    TRANSIENT = "transient"                     # 暂时性失败（网络抖动、临时不可用）
    SYSTEMATIC = "systematic"                   # 系统性失败（配置错误、代码bug）
    CAPABILITY_MISSING = "capability_missing"   # 能力缺失
    DEPENDENCY_FAILED = "dependency_failed"     # 依赖任务失败
    TIMEOUT = "timeout"                         # 超时
    VALIDATION_FAILED = "validation_failed"     # 验证失败
    PARAMETER_ERROR = "parameter_error"         # 参数错误
    UNKNOWN = "unknown"                         # 未知错误


class ActionType(str, Enum):
    """决策行动类型"""
    CONTINUE = "continue"                 # 继续执行下一个任务
    RETRY = "retry"                       # 重试当前任务
    SKIP = "skip"                         # 跳过当前任务
    ADJUST_PARAMS = "adjust_params"       # 调整任务参数后重试
    REPLAN_TASK = "replan_task"          # 重新规划单个任务
    REPLAN_ALL = "replan_all"            # 重新规划整个计划
    ESCALATE = "escalate"                # 上报人工处理
    TERMINATE = "terminate"              # 终止执行


# ===== Data Models ===== #

class TaskObservation(BaseModel):
    """
    任务执行观察结果
    
    记录单个任务的执行状态、结果分析和根因判断
    """
    # 基本信息
    task_id: str = Field(description="任务ID")
    task_description: str = Field(description="任务描述")
    
    # 执行状态
    success: bool = Field(description="是否成功")
    execution_time: float = Field(default=0.0, description="执行时间（秒）")
    retry_count: int = Field(default=0, description="重试次数")
    
    # 结果分析
    result: Optional[Dict[str, Any]] = Field(default=None, description="执行结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    error_type: Optional[FailureType] = Field(default=None, description="错误类型")
    
    # 根因分析
    root_cause: Optional[str] = Field(default=None, description="根本原因")
    is_recoverable: bool = Field(default=True, description="是否可恢复")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="分析置信度")
    
    # 上下文检查
    dependencies_met: bool = Field(default=True, description="依赖是否满足")
    capability_available: bool = Field(default=True, description="能力是否可用")
    
    # 元数据
    observed_at: datetime = Field(default_factory=datetime.now, description="观察时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PlanObservation(BaseModel):
    """
    计划执行观察结果
    
    记录整体计划的进度、健康度和趋势
    """
    # 计划信息
    plan_version: int = Field(description="计划版本")
    total_tasks: int = Field(description="总任务数")
    completed_tasks: int = Field(default=0, description="已完成任务数")
    failed_tasks: int = Field(default=0, description="失败任务数")
    pending_tasks: int = Field(default=0, description="待执行任务数")
    
    # 进度分析
    progress_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="进度率")
    estimated_remaining_time: Optional[float] = Field(default=None, description="预估剩余时间")
    
    # 健康度评估
    plan_health: float = Field(default=1.0, ge=0.0, le=1.0, description="计划健康度")
    blockers: List[str] = Field(default_factory=list, description="阻塞因素")
    
    # 趋势分析
    is_making_progress: bool = Field(default=True, description="是否在推进")
    failure_trend: str = Field(default="stable", description="失败趋势: improving/stable/degrading")
    
    # 元数据
    observed_at: datetime = Field(default_factory=datetime.now, description="观察时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DecisionResult(BaseModel):
    """
    决策结果
    
    基于观察和分析做出的行动决策
    """
    # 决策核心
    action: ActionType = Field(description="决策行动")
    reason: str = Field(description="决策理由")
    confidence: float = Field(ge=0.0, le=1.0, description="决策置信度")
    
    # 行动参数
    target_task_id: Optional[str] = Field(default=None, description="目标任务ID")
    retry_delay: Optional[float] = Field(default=None, description="重试延迟（秒）")
    adjusted_params: Optional[Dict[str, Any]] = Field(default=None, description="调整后的参数")
    replan_scope: Optional[str] = Field(default=None, description="重规划范围: task/all")
    
    # 元数据
    decided_at: datetime = Field(default_factory=datetime.now, description="决策时间")
    alternative_actions: List[Dict[str, Any]] = Field(default_factory=list, description="备选行动")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ObservationContext(BaseModel):
    """
    观察上下文
    
    维护观察历史、决策历史和约束条件
    """
    # 循环状态
    current_iteration: int = Field(default=0, description="当前迭代次数")
    max_iterations: int = Field(default=10, description="最大迭代次数")
    
    # 观察历史
    task_observations: List[TaskObservation] = Field(default_factory=list, description="任务观察历史")
    plan_observations: List[PlanObservation] = Field(default_factory=list, description="计划观察历史")
    past_decisions: List[DecisionResult] = Field(default_factory=list, description="决策历史")
    
    # 约束条件
    max_retries_per_task: int = Field(default=3, description="每个任务最大重试次数")
    max_replans: int = Field(default=2, description="最大重规划次数")
    current_replan_count: int = Field(default=0, description="当前重规划次数")
    
    # 统计信息
    total_retries: int = Field(default=0, description="总重试次数")
    total_escalations: int = Field(default=0, description="总上报次数")
    
    class Config:
        arbitrary_types_allowed = True


# ===== Observe Module ===== #

class ObserveModule(BaseModule):
    """
    观察与决策模块（重构版v4.0）
    
    实现OODA循环（Observe-Orient-Decide-Act）：
    1. Observe: 观察任务执行结果和计划进度
    2. Orient: 理解失败原因和模式
    3. Decide: 基于分析做出智能决策
    4. Act: 由调用方执行决策
    
    新接口：
    - __call__(state) → state  # 默认观察操作（观察任务执行）
    - decide(state) → state    # 决策操作（基于观察做决策）
    - handle(state) → state    # 处理决策（转换为控制信号）
    
    兼容OpenAI Agent SDK：
    - 使用Agent进行LLM分析
    - 使用Runner执行agent
    - 遵循SDK的最佳实践
    """
    
    # ==================== 依赖声明 ====================
    
    STATE_REQUIRES = ['task', 'result']  # 默认观察任务执行
    STATE_PRODUCES = ['observation', 'metadata']
    
    # ==================== 初始化 ====================
    
    def __init__(
        self,
        config: Optional[ObserveModuleConfig] = None,
        loop_context: Optional['LoopContext'] = None,
        loop_state: Optional['LoopState'] = None,
        loop: Optional[Any] = None,
        **kwargs
    ):
        """
        初始化ObserveModule
        
        Args:
            config: 观察模块配置
            loop_context: Loop的LLM交互上下文（共享）
            loop_state: Loop的业务状态（共享，可选）
            loop: BaseAgentLoop 引用
            **kwargs: 额外参数
        """
        # 初始化配置
        if config is None:
            config = ObserveModuleConfig()
        
        # 调用基类初始化
        super().__init__(
            config=config,
            loop_context=loop_context,
            loop_state=loop_state,
            loop=loop,
            module_type="ObserveModule",
            **kwargs
        )
        
        # 使用observe_model或回退到默认model
        self.observe_model = config.observe_model or self.model
        
        # 初始化观察上下文
        self.observation_context = ObservationContext(
            current_iteration=0,
            max_iterations=kwargs.get('max_iterations', 10)
        )
        
        _logger.info(
            f"ObserveModule initialized | model={self.observe_model} | "
            f"llm_analysis={config.enable_llm_analysis} | "
            f"conservative={config.conservative_mode} | "
            f"has_context={self.context is not None}"
        )
    
    def _init_stats(self) -> Dict[str, Any]:
        """初始化统计信息（BaseModule抽象方法实现）"""
        return {
            "observations_count": 0,
            "decisions_count": 0,
            "retries_triggered": 0,
            "replans_triggered": 0,
            "escalations_triggered": 0,
        }
    
    # ==================== 新接口（State → State）====================
    
    async def _execute(self, state: 'LoopState') -> Dict[str, Any]:
        """
        默认的观察操作：观察任务执行结果（State → State接口）
        
        Args:
            state: 输入State（需要task和result）
        
        Returns:
            包含observation和metadata的字典
        """
        from pisa.core.planning.task_tree import TaskNode
        
        task = state.task
        result = state.result
        
        # 将task转换为TaskNode（如果需要）
        if isinstance(task, dict):
            task_node = TaskNode(
                task_id=task.get('task_id', 'unknown'),
                task_description=task.get('task_description', str(task)),
                status=task.get('status', 'completed')
            )
        else:
            task_node = task
        
        # 将result转换为执行结果字典
        if isinstance(result, dict):
            execution_result = result
        else:
            execution_result = {
                "success": getattr(result, 'success', True),
                "result": getattr(result, 'result', result),
                "execution_time": getattr(result, 'execution_time', 0.0)
            }
        
        # 调用现有的业务逻辑
        observation = await self.observe_task_execution(
            task=task_node,
            execution_result=execution_result,
            context=state.metadata
        )
        
        # 更新到Context（可选）
        if self.context:
            self.context.add_observation_message(observation)
        
        return {
            "observation": observation,
            "metadata": {
                **state.metadata,
                "last_observation": {
                    "task_id": observation.task_id,
                    "success": observation.success,
                    "observed_at": observation.observed_at.isoformat()
                }
            }
        }
    
    async def decide(self, state: 'LoopState') -> 'LoopState':
        """
        决策操作：基于观察结果做出决策（额外方法）
        
        Args:
            state: 输入State（需要observation）
        
        Returns:
            包含decision的新State
        """
        observation = state.observation
        if observation is None:
            raise ValueError("ObserveModule.decide requires state.observation")
        
        # 如果observation是字典，转换为TaskObservation对象
        # (因为LoopState.with_update使用model_dump()会将Pydantic对象序列化)
        if isinstance(observation, dict):
            observation = TaskObservation(**observation)
        
        # 获取plan observation（如果有）
        plan_observation = state.get('plan_observation')
        if isinstance(plan_observation, dict):
            plan_observation = PlanObservation(**plan_observation)
        
        # 调用现有的决策逻辑
        decision = await self.decide_next_action(
            task_observation=observation,
            plan_observation=plan_observation
        )
        
        # 更新统计
        self.stats["decisions_count"] = self.stats.get("decisions_count", 0) + 1
        
        # 更新到Context（可选）
        if self.context:
            self.context.add_decision_message(decision)
        
        return state.with_update(decision=decision)
    
    async def handle(self, state: 'LoopState') -> 'LoopState':
        """
        处理决策：将决策转换为控制信号（额外方法）
        
        Args:
            state: 输入State（需要decision）
        
        Returns:
            包含控制信号的新State
        """
        decision = state.decision
        if decision is None:
            raise ValueError("ObserveModule.handle requires state.decision")
        
        # 根据决策类型设置控制信号
        updates = {}
        
        if decision.action == ActionType.TERMINATE:
            updates['should_stop'] = True
            _logger.info("Decision: TERMINATE - stopping execution")
        
        elif decision.action == ActionType.REPLAN_ALL:
            updates['should_replan'] = True
            _logger.info("Decision: REPLAN_ALL - triggering replan")
            self.stats["replans_triggered"] = self.stats.get("replans_triggered", 0) + 1
        
        elif decision.action == ActionType.RETRY:
            updates['should_retry'] = True
            _logger.info("Decision: RETRY - retrying task")
            self.stats["retries_triggered"] = self.stats.get("retries_triggered", 0) + 1
        
        elif decision.action == ActionType.ESCALATE:
            updates['should_stop'] = True
            updates['metadata'] = {
                **state.metadata,
                'escalation': {
                    'reason': decision.reason,
                    'confidence': decision.confidence
                }
            }
            _logger.warning("Decision: ESCALATE - human intervention needed")
            self.stats["escalations_triggered"] = self.stats.get("escalations_triggered", 0) + 1
        
        elif decision.action == ActionType.CONTINUE:
            # 继续执行，不设置特殊信号
            _logger.info("Decision: CONTINUE - proceeding normally")
        
        else:
            # 其他action类型
            _logger.info(f"Decision: {decision.action} - custom handling")
        
        return state.with_update(**updates) if updates else state
    
    # ==================== 保留的业务逻辑 ====================
    # ===== Public API ===== #
    
    async def observe_task_execution(
        self,
        task: TaskNode,
        execution_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> TaskObservation:
        """
        观察单个任务的执行结果
        
        Args:
            task: 任务节点
            execution_result: 执行结果字典
            context: 额外上下文信息
        
        Returns:
            TaskObservation: 任务观察结果
        """
        self.log_operation(
            "observe_task_execution",
            status="running",
            task_id=task.task_id
        )
        
        # 1. 提取基础信息
        # 确保result是dict类型
        result_value = execution_result.get("result")
        if result_value is not None and not isinstance(result_value, dict):
            # 如果result不是dict，包装成dict
            result_value = {"value": str(result_value)}
        
        observation = TaskObservation(
            task_id=task.task_id,
            task_description=task.task_description,
            success=execution_result.get("success", False),
            execution_time=execution_result.get("execution_time", 0.0),
            retry_count=execution_result.get("retries", 0),
            result=result_value,
            error=execution_result.get("error")
        )
        
        # 2. 如果失败，进行深度分析
        if not observation.success and observation.error:
            # 2.1 分类错误类型
            observation.error_type = await self._classify_error(observation.error)
            
            # 2.2 判断可恢复性
            observation.is_recoverable = self._is_recoverable(observation.error_type)
            
            # 2.3 根因分析（使用LLM）
            if self.config.enable_llm_analysis:
                try:
                    root_cause_analysis = await self._analyze_root_cause(
                        task=task,
                        error=observation.error,
                        error_type=observation.error_type,
                        context=context
                    )
                    observation.root_cause = root_cause_analysis.get("root_cause")
                    observation.confidence = root_cause_analysis.get("confidence", 0.7)
                except Exception as e:
                    _logger.warning(f"Root cause analysis failed: {e}")
                    observation.root_cause = f"Analysis failed: {str(e)}"
                    observation.confidence = 0.3
        else:
            # 成功任务
            observation.confidence = 1.0
        
        # 3. 检查依赖和能力
        observation.dependencies_met = self._check_dependencies(task, context)
        observation.capability_available = self._check_capability(task)
        
        # 4. 记录到观察上下文
        self.observation_context.task_observations.append(observation)
        
        self.log_operation(
            "observe_task_execution",
            status="success",
            task_id=task.task_id,
            success=observation.success,
            error_type=str(observation.error_type) if observation.error_type else None,
            is_recoverable=observation.is_recoverable
        )
        
        return observation
    
    async def observe_plan_progress(
        self,
        task_tree: TaskTree,
        context: Optional[Dict[str, Any]] = None
    ) -> PlanObservation:
        """
        观察整体计划的执行进度
        
        Args:
            task_tree: 任务树
            context: 额外上下文信息
        
        Returns:
            PlanObservation: 计划观察结果
        """
        self.log_operation("observe_plan_progress", status="running")
        
        # 1. 统计任务状态
        total_tasks = len(task_tree.tasks)
        completed = sum(1 for t in task_tree.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in task_tree.tasks.values() if t.status == TaskStatus.FAILED)
        pending = sum(1 for t in task_tree.tasks.values() if t.status == TaskStatus.PENDING)
        
        observation = PlanObservation(
            plan_version=task_tree.plan_version,
            total_tasks=total_tasks,
            completed_tasks=completed,
            failed_tasks=failed,
            pending_tasks=pending,
            progress_rate=completed / max(total_tasks, 1)
        )
        
        # 2. 计算健康度
        observation.plan_health = self._calculate_plan_health(
            total_tasks,
            completed,
            failed,
            pending
        )
        
        # 3. 识别阻塞因素
        observation.blockers = self._identify_blockers(task_tree)
        
        # 4. 分析进度趋势
        observation.is_making_progress = self._check_progress_trend(
            self.observation_context.plan_observations
        )
        
        observation.failure_trend = self._analyze_failure_trend(
            self.observation_context.task_observations
        )
        
        # 5. 记录到观察上下文
        self.observation_context.plan_observations.append(observation)
        
        self.log_operation(
            "observe_plan_progress",
            status="success",
            progress=f"{observation.progress_rate:.1%}",
            health=f"{observation.plan_health:.2f}",
            trend=observation.failure_trend
        )
        
        return observation
    
    async def decide_next_action(
        self,
        task_observation: TaskObservation,
        plan_observation: PlanObservation,
        context: Optional[Dict[str, Any]] = None
    ) -> DecisionResult:
        """
        基于观察结果决定下一步行动
        
        这是核心决策逻辑！实现智能的决策矩阵。
        
        Args:
            task_observation: 任务观察结果
            plan_observation: 计划观察结果
            context: 额外上下文信息
        
        Returns:
            DecisionResult: 决策结果
        """
        self.log_operation("decide_next_action", status="running")
        
        # 执行决策矩阵
        decision = await self._evaluate_decision_matrix(
            task_observation,
            plan_observation,
            context
        )
        
        # 记录决策
        self.observation_context.past_decisions.append(decision)
        
        self.log_operation(
            "decide_next_action",
            status="success",
            action=decision.action.value,
            reason=decision.reason[:100],  # 限制长度
            confidence=f"{decision.confidence:.2f}"
        )
        
        return decision
    
    # ===== 私有方法: 错误分析 ===== #
    
    async def _classify_error(self, error_message: str) -> FailureType:
        """
        分类错误类型
        
        使用模式匹配进行快速分类
        """
        error_lower = error_message.lower()
        
        # 模式匹配规则
        if any(keyword in error_lower for keyword in ["timeout", "timed out", "time out"]):
            return FailureType.TIMEOUT
        
        elif any(keyword in error_lower for keyword in ["not found", "missing", "unavailable"]):
            return FailureType.CAPABILITY_MISSING
        
        elif any(keyword in error_lower for keyword in ["network", "connection", "unreachable"]):
            return FailureType.TRANSIENT
        
        elif any(keyword in error_lower for keyword in ["validation", "invalid", "malformed"]):
            return FailureType.VALIDATION_FAILED
        
        elif any(keyword in error_lower for keyword in ["dependency", "prerequisite"]):
            return FailureType.DEPENDENCY_FAILED
        
        elif any(keyword in error_lower for keyword in ["parameter", "argument", "input"]):
            return FailureType.PARAMETER_ERROR
        
        elif any(keyword in error_lower for keyword in ["config", "setup", "initialization"]):
            return FailureType.SYSTEMATIC
        
        else:
            return FailureType.UNKNOWN
    
    def _is_recoverable(self, error_type: FailureType) -> bool:
        """判断错误是否可恢复"""
        recoverable_types = {
            FailureType.TRANSIENT,
            FailureType.TIMEOUT,
            FailureType.PARAMETER_ERROR,
        }
        return error_type in recoverable_types
    
    async def _analyze_root_cause(
        self,
        task: TaskNode,
        error: str,
        error_type: FailureType,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        使用LLM分析根本原因
        
        兼容OpenAI Agent SDK
        """
        analysis_prompt = f"""Analyze the following task execution failure and provide root cause analysis.

Task Information:
- Description: {task.task_description}
- Task ID: {task.task_id}
- Error Type: {error_type.value}
- Error Message: {error}

Please provide:
1. Root cause (what is the fundamental reason for failure?)
2. Whether this is systematic or transient
3. Confidence level (0.0-1.0)

Respond in JSON format:
{{
    "root_cause": "brief explanation",
    "is_systematic": true/false,
    "confidence": 0.0-1.0
}}
"""
        
        try:
            # 运行时导入
            from agents import Agent, Runner
            
            # 使用OpenAI Agent SDK
            agent = Agent(
                name="RootCauseAnalyzer",
                instructions="You are an expert at analyzing task execution failures. Be concise and precise.",
                model=self.observe_model
            )
            
            runner = Runner(agent)
            result = await runner.run(analysis_prompt)
            
            # 解析结果
            # TODO: 更robust的JSON解析
            content = result if isinstance(result, str) else str(result)
            
            return {
                "root_cause": content[:200],  # 限制长度
                "confidence": 0.7  # 默认置信度
            }
            
        except Exception as e:
            _logger.error(f"Root cause analysis failed: {e}")
            return {
                "root_cause": f"Analysis error: {str(e)}",
                "confidence": 0.3
            }
    
    # ===== 私有方法: 决策矩阵 ===== #
    
    async def _evaluate_decision_matrix(
        self,
        task_obs: TaskObservation,
        plan_obs: PlanObservation,
        context: Optional[Dict[str, Any]]
    ) -> DecisionResult:
        """
        决策矩阵评估
        
        实现7条智能决策规则 + LLM兜底
        """
        
        # ===== 规则1: 任务成功 → CONTINUE =====
        if task_obs.success:
            return DecisionResult(
                action=ActionType.CONTINUE,
                reason="Task executed successfully, continue to next task",
                confidence=1.0,
                target_task_id=task_obs.task_id
            )
        
        # ===== 规则2: 暂时性失败 + 未达重试上限 → RETRY =====
        if (task_obs.error_type == FailureType.TRANSIENT or 
            task_obs.error_type == FailureType.TIMEOUT):
            
            if task_obs.retry_count < self.observation_context.max_retries_per_task:
                # 计算重试延迟（指数退避）
                if self.config.exponential_backoff:
                    retry_delay = min(
                        self.config.base_retry_delay * (2 ** task_obs.retry_count),
                        self.config.max_retry_delay
                    )
                else:
                    retry_delay = self.config.base_retry_delay
                
                return DecisionResult(
                    action=ActionType.RETRY,
                    reason=f"{task_obs.error_type.value} failure, retry {task_obs.retry_count + 1}/{self.observation_context.max_retries_per_task}",
                    confidence=0.8,
                    target_task_id=task_obs.task_id,
                    retry_delay=retry_delay
                )
        
        # ===== 规则3: 能力缺失 → REPLAN_TASK =====
        if task_obs.error_type == FailureType.CAPABILITY_MISSING:
            return DecisionResult(
                action=ActionType.REPLAN_TASK,
                reason=f"Required capability not available for task {task_obs.task_id}",
                confidence=0.9,
                target_task_id=task_obs.task_id,
                replan_scope="task"
            )
        
        # ===== 规则4: 计划健康度低 → REPLAN_ALL =====
        if plan_obs.plan_health < self.config.replan_threshold:
            if self.observation_context.current_replan_count < self.observation_context.max_replans:
                return DecisionResult(
                    action=ActionType.REPLAN_ALL,
                    reason=f"Plan health too low ({plan_obs.plan_health:.2f} < {self.config.replan_threshold}), full replan needed",
                    confidence=0.85,
                    replan_scope="all"
                )
            else:
                # 达到重规划上限，上报
                return DecisionResult(
                    action=ActionType.ESCALATE,
                    reason=f"Max replans reached ({self.observation_context.max_replans}), escalating to human",
                    confidence=0.95
                )
        
        # ===== 规则5: 失败率高 + 趋势恶化 → REPLAN_ALL =====
        failure_rate = plan_obs.failed_tasks / max(plan_obs.total_tasks, 1)
        if (failure_rate > self.config.failure_rate_threshold and
            plan_obs.failure_trend == "degrading"):
            
            if self.observation_context.current_replan_count < self.observation_context.max_replans:
                return DecisionResult(
                    action=ActionType.REPLAN_ALL,
                    reason=f"High failure rate ({failure_rate:.1%}) with degrading trend",
                    confidence=0.75,
                    replan_scope="all"
                )
        
        # ===== 规则6: 依赖失败 → SKIP =====
        if task_obs.error_type == FailureType.DEPENDENCY_FAILED:
            return DecisionResult(
                action=ActionType.SKIP,
                reason="Task dependencies not met, skipping",
                confidence=0.9,
                target_task_id=task_obs.task_id
            )
        
        # ===== 规则7: 系统性失败 → ESCALATE =====
        if task_obs.error_type == FailureType.SYSTEMATIC:
            return DecisionResult(
                action=ActionType.ESCALATE,
                reason=f"Systematic failure detected: {task_obs.root_cause or 'Unknown'}",
                confidence=0.95,
                target_task_id=task_obs.task_id
            )
        
        # ===== 规则8: 参数错误 → ADJUST_PARAMS =====
        if task_obs.error_type == FailureType.PARAMETER_ERROR:
            return DecisionResult(
                action=ActionType.ADJUST_PARAMS,
                reason="Parameter error detected, adjustment may help",
                confidence=0.6,
                target_task_id=task_obs.task_id
            )
        
        # ===== 保守模式: 更倾向于重规划 =====
        if self.config.conservative_mode:
            return DecisionResult(
                action=ActionType.REPLAN_ALL,
                reason="Conservative mode: defaulting to replan for unknown failures",
                confidence=0.5,
                replan_scope="all"
            )
        
        # ===== 默认: CONTINUE (尝试继续) =====
        return DecisionResult(
            action=ActionType.CONTINUE,
            reason="No clear recovery action, attempting to continue",
            confidence=0.3
        )
    
    # ===== 私有方法: 计划分析 ===== #
    
    def _calculate_plan_health(
        self,
        total: int,
        completed: int,
        failed: int,
        pending: int
    ) -> float:
        """
        计算计划健康度
        
        健康度公式：
        health = (completed * 1.0 + pending * 0.5 - failed * 0.5) / total
        """
        if total == 0:
            return 1.0
        
        health = (completed * 1.0 + pending * 0.5 - failed * 0.5) / total
        return max(0.0, min(1.0, health))
    
    def _identify_blockers(self, task_tree: TaskTree) -> List[str]:
        """识别阻塞因素"""
        blockers = []
        
        # 找出失败的任务
        failed_tasks = [
            t for t in task_tree.tasks.values()
            if t.status == TaskStatus.FAILED
        ]
        
        for failed_task in failed_tasks:
            # 找出依赖这个失败任务的其他任务
            dependent_count = sum(
                1 for t in task_tree.tasks.values()
                if failed_task.task_id in t.dependencies
            )
            
            if dependent_count > 0:
                blockers.append(
                    f"Task '{failed_task.task_id}' failed, blocking {dependent_count} dependent task(s)"
                )
        
        return blockers
    
    def _check_progress_trend(
        self,
        plan_observations: List[PlanObservation]
    ) -> bool:
        """检查是否在进步"""
        if len(plan_observations) < 2:
            return True
        
        recent = plan_observations[-1]
        previous = plan_observations[-2]
        
        return recent.completed_tasks > previous.completed_tasks
    
    def _analyze_failure_trend(
        self,
        task_observations: List[TaskObservation]
    ) -> str:
        """
        分析失败趋势
        
        Returns:
            "improving" | "stable" | "degrading"
        """
        if len(task_observations) < 3:
            return "stable"
        
        # 取最近5个观察
        recent_obs = task_observations[-min(5, len(task_observations)):]
        
        # 计算失败率
        failure_counts = []
        window_size = 3
        
        for i in range(len(recent_obs) - window_size + 1):
            window = recent_obs[i:i + window_size]
            failures = sum(1 for obs in window if not obs.success)
            failure_counts.append(failures)
        
        if len(failure_counts) < 2:
            return "stable"
        
        # 计算趋势（最近 vs 最早）
        recent_failures = failure_counts[-1]
        early_failures = failure_counts[0]
        
        if recent_failures < early_failures:
            return "improving"
        elif recent_failures > early_failures:
            return "degrading"
        else:
            return "stable"
    
    def _check_dependencies(
        self,
        task: TaskNode,
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """检查任务依赖是否满足"""
        # TODO: 实现完整的依赖检查逻辑
        # 需要访问TaskTree来检查依赖任务的状态
        return True
    
    def _check_capability(self, task: TaskNode) -> bool:
        """检查任务所需能力是否可用"""
        # TODO: 实现完整的能力检查逻辑
        # 需要访问CapabilityRegistry
        return True
    
    # ===== 工具方法 ===== #
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取观察统计信息"""
        return {
            "total_observations": len(self.observation_context.task_observations),
            "total_decisions": len(self.observation_context.past_decisions),
            "current_iteration": self.observation_context.current_iteration,
            "replan_count": self.observation_context.current_replan_count,
            "total_retries": self.observation_context.total_retries,
            "decision_distribution": self._get_decision_distribution()
        }
    
    def _get_decision_distribution(self) -> Dict[str, int]:
        """获取决策分布统计"""
        distribution = {}
        for decision in self.observation_context.past_decisions:
            action = decision.action.value
            distribution[action] = distribution.get(action, 0) + 1
        return distribution
    
    def reset(self):
        """重置观察上下文"""
        self.observation_context = ObservationContext(
            current_iteration=0,
            max_iterations=self.observation_context.max_iterations
        )
        _logger.info("ObservationContext reset")



