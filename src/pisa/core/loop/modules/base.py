"""
Base Module (Refactored v4.0)

Agent Loop 模块基类，实现统一的 State → State 接口

核心设计：
1. 统一接口：__call__(state: LoopState) → LoopState
2. Context透明：模块内部可访问 self.context（LLM历史）
3. 依赖声明：STATE_REQUIRES, STATE_PRODUCES
4. 不可变：每次返回新State
"""

import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from datetime import datetime

if TYPE_CHECKING:
    from pisa.core.loop.state import LoopState
    from pisa.core.loop.context import LoopContext

from pisa.config import Config
from pisa.utils.logger import get_logger
from pisa.utils.observability import ObservabilityManager, MetricsCollector

_logger = logging.getLogger(__name__)


# ==================== 模块配置类 ====================

class ModuleConfig(BaseModel):
    """
    模块配置基类
    
    所有模块配置都应继承此类，支持从 agent.md 定义层透传配置。
    """
    # 通用配置
    model: Optional[str] = Field(default=None, description="使用的模型")
    enabled: bool = Field(default=True, description="是否启用该模块")
    
    # 可观测性配置
    enable_logging: bool = Field(default=True, description="是否启用日志")
    enable_metrics: bool = Field(default=True, description="是否启用指标收集")
    
    # 元数据
    module_name: Optional[str] = Field(default=None, description="模块名称")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
    
    class Config:
        extra = "allow"  # 允许额外字段


class ObserveModuleConfig(ModuleConfig):
    """观察模块配置"""
    # 模型配置
    observe_model: Optional[str] = Field(default=None, description="观察分析专用模型")
    decision_model: Optional[str] = Field(default=None, description="决策专用模型")
    
    # 阈值配置
    replan_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="触发重规划的健康度阈值")
    retry_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="触发重试的置信度阈值")
    failure_rate_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="失败率阈值")
    
    # 决策策略
    enable_llm_analysis: bool = Field(default=True, description="是否使用LLM进行深度分析")
    enable_pattern_matching: bool = Field(default=True, description="是否启用模式匹配")
    conservative_mode: bool = Field(default=False, description="保守模式（更倾向于重规划）")
    
    # 重试策略
    max_retries: int = Field(default=3, description="最大重试次数")
    base_retry_delay: float = Field(default=1.0, description="基础重试延迟（秒）")
    max_retry_delay: float = Field(default=60.0, description="最大重试延迟（秒）")
    exponential_backoff: bool = Field(default=True, description="是否使用指数退避")


class PlanningModuleConfig(ModuleConfig):
    """规划模块配置"""
    planning_model: Optional[str] = Field(default=None, description="规划专用模型")
    replanning_model: Optional[str] = Field(default=None, description="重规划专用模型")
    max_planning_iterations: int = Field(default=10, description="最大规划迭代次数")
    enable_replanning: bool = Field(default=True, description="是否启用重新规划")


class ExecutionModuleConfig(ModuleConfig):
    """执行模块配置"""
    execution_model: Optional[str] = Field(default=None, description="执行专用模型")
    max_retries: int = Field(default=3, description="最大重试次数")
    timeout_seconds: Optional[int] = Field(default=None, description="超时时间（秒）")
    parallel_execution: bool = Field(default=False, description="是否并行执行")


class ReflectionModuleConfig(ModuleConfig):
    """反思模块配置"""
    reflection_model: Optional[str] = Field(default=None, description="反思专用模型")
    reflection_depth: str = Field(default="standard", description="反思深度: shallow/standard/deep")
    enable_self_critique: bool = Field(default=True, description="是否启用自我批判")


class ValidationModuleConfig(ModuleConfig):
    """验证模块配置"""
    validation_model: Optional[str] = Field(default=None, description="验证专用模型")
    safety_level: str = Field(default="medium", description="安全级别: low/medium/high")
    enable_guardrails: bool = Field(default=True, description="是否启用 Guardrails")


# ==================== 模块基类 ====================

class BaseModule(ABC):
    """
    模块基类
    
    核心设计原则：
    1. 统一接口：State → State（显式）
    2. Context透明：self.context 隐式共享（可选）
    3. 依赖声明：STATE_REQUIRES, STATE_PRODUCES
    4. 不可变：返回新State，不修改输入
    
    使用示例：
    ```python
    class MyModule(BaseModule):
        STATE_REQUIRES = ['task']
        STATE_PRODUCES = ['result']
        
        async def _execute(self, state: LoopState) -> Dict[str, Any]:
            # 从state读取
            task = state.task
            
            # 从self.context读取LLM历史（可选）
            messages = self.context.get_active_messages() if self.context else []
            
            # 业务逻辑
            result = await self._do_work(task, messages)
            
            # 返回要更新到state的字段
            return {'result': result}
    
    # 使用
    module = MyModule(config, loop_context=context)
    new_state = await module(state)  # State → State
    ```
    """
    
    # 子类必须声明State依赖
    STATE_REQUIRES: List[str] = []  # 需要从State读取的字段
    STATE_PRODUCES: List[str] = []  # 会写入State的字段
    
    def __init__(
        self,
        config: Optional[ModuleConfig] = None,
        loop_context: Optional['LoopContext'] = None,
        loop_state: Optional['LoopState'] = None,
        loop: Optional[Any] = None,  # BaseAgentLoop 引用
        module_type: str = "BaseModule",
        **kwargs
    ):
        """
        初始化模块
        
        Args:
            config: 模块配置
            loop_context: Loop的LLM交互上下文（共享，可选）
            loop_state: Loop的业务状态（共享，可选引用）
            loop: BaseAgentLoop 引用（用于访问 create_agent 等方法）
            module_type: 模块类型名称
            **kwargs: 额外参数
        """
        # 配置管理
        self.config = config or ModuleConfig()
        self.module_type = module_type
        
        # 共享的Context和State
        self.context = loop_context  # 隐式共享的LLM交互层
        self.state_ref = loop_state  # 可选的State引用（用于访问全局状态）
        self.loop = loop  # BaseAgentLoop 引用（用于 create_agent 等）
        
        # 确保 Agent SDK 已配置
        Config.setup_agent_sdk()
        
        # 模型配置
        self.model = self._resolve_model()
        
        # 可观测性
        self.logger = get_logger(enable_rich=self.config.enable_logging)
        
        # 统计信息
        self.stats = self._init_stats()
        self.created_at = datetime.now()
        
        # 生命周期状态
        self._initialized = False
        self._is_running = False
        
        self.logger.info(
            f"{module_type} initialized",
            model=self.model,
            has_context=self.context is not None,
            state_requires=self.STATE_REQUIRES,
            state_produces=self.STATE_PRODUCES
        )
    
    # ==================== 核心接口 ====================
    
    async def __call__(self, state: 'LoopState') -> 'LoopState':
        """
        统一调用接口：State → State
        
        这是模块的主要入口点，实现：
        1. 验证输入State包含所需字段
        2. 执行业务逻辑（子类实现）
        3. 返回新State（不可变）
        
        Args:
            state: 输入LoopState
        
        Returns:
            新的LoopState对象
        
        Raises:
            ValueError: 如果State缺少必需字段
        """
        # 1. 验证State包含所需字段
        self._validate_state(state)
        
        # 2. 记录操作开始
        self._is_running = True
        self.stats["operations_count"] = self.stats.get("operations_count", 0) + 1
        
        try:
            # 3. 执行业务逻辑（子类实现）
            result = await self._execute(state)
            
            # 4. 更新State（不可变）
            new_state = self._update_state(state, result)
            
            # 5. 记录成功
            self.log_operation(
                operation="execute",
                status="success",
                iteration=state.iteration
            )
            
            return new_state
            
        except Exception as e:
            # 记录错误
            self.stats["errors_count"] = self.stats.get("errors_count", 0) + 1
            self.log_operation(
                operation="execute",
                status="error",
                error=str(e),
                iteration=state.iteration
            )
            raise
        finally:
            self._is_running = False
    
    def _validate_state(self, state: 'LoopState') -> None:
        """
        验证State包含所需字段
        
        Args:
            state: 输入State
        
        Raises:
            ValueError: 如果缺少必需字段
        """
        for field in self.STATE_REQUIRES:
            if getattr(state, field, None) is None:
                raise ValueError(
                    f"{self.__class__.__name__} requires state.{field}, "
                    f"but it's None or missing"
                )
    
    @abstractmethod
    async def _execute(self, state: 'LoopState') -> Dict[str, Any]:
        """
        执行业务逻辑（子类实现）
        
        这是模块的核心逻辑，子类必须实现。
        
        可以：
        - 从 state 读取业务数据
        - 从 self.context 读取LLM历史（如果需要）
        - 调用LLM（会自动更新self.context）
        - 执行任何业务逻辑
        
        Args:
            state: 输入State
        
        Returns:
            要更新到State的字段（dict）
            例如：{"observation": Observation(...), "decision": Decision(...)}
        
        Example:
            ```python
            async def _execute(self, state):
                # 读取State
                task = state.task
                
                # 读取Context（可选）
                if self.context:
                    messages = self.context.get_active_messages()
                
                # 业务逻辑
                result = await self._do_something(task, messages)
                
                # 返回State更新
                return {"result": result}
            ```
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _execute()"
        )
    
    def _update_state(
        self,
        state: 'LoopState',
        result: Dict[str, Any]
    ) -> 'LoopState':
        """
        更新State（不可变）
        
        Args:
            state: 输入State
            result: 要更新的字段
        
        Returns:
            新的State对象
        """
        # 使用State的不可变更新
        return state.with_update(**result)
    
    # ==================== 模型解析 ====================
    
    def _resolve_model(self) -> str:
        """
        解析模型配置
        
        优先级：
        1. 模块专用模型（如 planning_model）
        2. 通用 model 配置
        3. 全局默认模型
        
        Returns:
            模型名称
        """
        # 子类可以覆盖此方法提供更具体的模型解析逻辑
        if self.config.model:
            return self.config.model
        return Config.agent_default_model
    
    # ==================== 统计信息 ====================
    
    def _init_stats(self) -> Dict[str, Any]:
        """
        初始化统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "module_type": self.module_type,
            "operations_count": 0,
            "errors_count": 0,
            "initialized": False,
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        base_stats = {
            "module_type": self.module_type,
            "model": self.model,
            "uptime_seconds": (datetime.now() - self.created_at).total_seconds(),
            "is_running": self._is_running,
        }
        
        return {**base_stats, **self.stats}
    
    def reset_statistics(self) -> None:
        """重置统计信息"""
        self.stats = self._init_stats()
        self.logger.info(f"{self.module_type} statistics reset")
    
    # ==================== 可观测性方法 ====================
    
    def log_operation(
        self,
        operation: str,
        status: str = "success",
        **kwargs
    ) -> None:
        """
        记录操作日志
        
        Args:
            operation: 操作名称
            status: 状态（success/error/running）
            **kwargs: 额外的日志字段
        """
        if not self.config.enable_logging:
            return
        
        log_data = {
            "module": self.module_type,
            "operation": operation,
            "status": status,
            **kwargs
        }
        
        if status == "error":
            self.logger.error(f"{self.module_type}.{operation} failed", **log_data)
        else:
            self.logger.info(f"{self.module_type}.{operation}", **log_data)
    
    def log_context_update(
        self,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录 context 更新
        
        Args:
            action: 更新动作
            details: 详细信息
        """
        if not self.config.enable_logging:
            return
        
        self.logger.context_update(
            action=f"[{self.module_type}] {action}",
            **(details or {})
        )
    
    def display_context_content(
        self,
        context_data: Dict[str, Any],
        title: Optional[str] = None
    ) -> None:
        """
        展示 context 内容
        
        Args:
            context_data: Context 数据
            title: 标题
        """
        if not self.config.enable_logging:
            return
        
        display_title = title or f"{self.module_type} Context"
        
        # 使用 logger 的 display_config 方法展示结构化数据
        self.logger.display_config(context_data, title=display_title)
    
    def log_metrics(
        self,
        metric_name: str,
        value: float,
        **tags
    ) -> None:
        """
        记录指标
        
        Args:
            metric_name: 指标名称
            value: 指标值
            **tags: 标签
        """
        if not self.config.enable_metrics:
            return
        
        # 记录到统计信息
        metric_key = f"metric_{metric_name}"
        if metric_key not in self.stats:
            self.stats[metric_key] = []
        
        self.stats[metric_key].append({
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "tags": tags
        })
    
    # ==================== 生命周期方法 ====================
    
    def startup(self) -> None:
        """启动模块"""
        if self._initialized:
            self.logger.warning(f"{self.module_type} already initialized")
            return
        
        self.logger.info(f"{self.module_type} starting up")
        self._initialized = True
        self.stats["initialized"] = True
    
    def shutdown(self) -> None:
        """关闭模块"""
        if not self._initialized:
            return
        
        self.logger.info(
            f"{self.module_type} shutting down",
            stats=self.get_statistics()
        )
        self._initialized = False
        self._is_running = False
    
    def __enter__(self):
        """支持上下文管理器"""
        self.startup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.shutdown()
        return False
