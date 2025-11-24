"""
重构后的 Agent Loop 基类

职责：
1. 集成基础设施（观测、缓存、配置）
2. 提供生命周期管理
3. 自动展示定义层信息
4. 提供通用工具方法

开发者只需要：
- 继承此类
- 实现 async run() 业务逻辑
- 实现 async step() 业务逻辑（可选）
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents import Agent, Runner

from pisa.config import Config
from pisa.capability import get_global_registry, CapabilityRegistry
from pisa.core.context import ContextManager
from pisa.utils.observability import ObservabilityManager
from pisa.core.loop.lifecycle import LifecycleManager
from pisa.core.loop import display_utils

_logger = logging.getLogger(__name__)


class IAgentLoop(ABC):
    """Agent Loop 接口"""
    
    @abstractmethod
    async def run(self, input_data: Any, **kwargs) -> Any:
        """运行 Loop"""
        pass
    
    @abstractmethod
    async def step(self, **kwargs) -> bool:
        """执行单步"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止 Loop"""
        pass


class BaseAgentLoop(IAgentLoop):
    """
    Agent Loop 基类（重构版）
    
    ✅ 自动化基础设施：
    - 观测系统自动集成
    - 定义层信息自动展示
    - 生命周期自动管理
    - Context 自动管理
    
    ✅ 开发者只需关注业务逻辑
    """
    
    def __init__(
        self,
        name: str,
        instructions: Optional[str] = None,
        model: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        context_manager: Optional[ContextManager] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        loop_definition: Optional[Any] = None,
        enable_observability: bool = True,
        enable_dashboard: bool = False,
        **kwargs
    ):
        """
        初始化 Loop
        
        Args:
            name: Agent 名称
            instructions: 指令
            model: 模型
            capabilities: Capability 名称列表
            context_manager: Context 管理器
            capability_registry: Capability 注册表
            loop_definition: Loop 定义（从 agent.md 解析）
            enable_observability: 是否启用观测
            enable_dashboard: 是否启用实时仪表板
            **kwargs: 额外参数
        """
        # 确保 Agent SDK 已配置
        Config.setup_agent_sdk()
        
        # 基本信息
        self.name = name
        self.instructions = instructions or "You are a helpful assistant."
        self.model = model or Config.agent_default_model
        self.loop_definition = loop_definition
        
        # ✅ 基础设施层：Context 管理
        self.context_manager = context_manager or ContextManager(
            agent_id=name,
            session_id=f"session_{int(datetime.now().timestamp())}"
        )
        self.context = self.context_manager  # 别名
        
        # ✅ 基础设施层：Capability 管理
        if isinstance(capabilities, CapabilityRegistry):
            self.capability_registry = capabilities
            self.capabilities = []
        else:
            self.capability_registry = capability_registry or get_global_registry()
            self.capabilities = capabilities or []
        
        # ✅ 基础设施层：观测系统（自动化）
        self.observability = None
        if enable_observability:
            self.observability = ObservabilityManager(
                module_name=f"{self.__class__.__name__}[{name}]",
                enable_live_dashboard=enable_dashboard,
                enable_detailed_logging=True
            )
        
        # ✅ 基础设施层：生命周期管理
        self.lifecycle = LifecycleManager(
            observability=self.observability,
            enable_auto_display=True
        )
        
        # 额外参数
        self.agent_kwargs = kwargs
        self.created_at = datetime.now()
        
        _logger.info(f"{self.__class__.__name__} initialized: {name}")
        
        # ✅ 自动展示定义层信息
        if loop_definition and enable_observability:
            display_utils.display_loop_definition(loop_definition)
    
    # ==================== 生命周期钩子（自动化）====================
    
    def before_run(self, input_data: Optional[Any] = None) -> None:
        """运行前钩子（自动追踪）"""
        self.lifecycle.before_run(input_data)
    
    def after_run(self, success: bool = True) -> None:
        """运行后钩子（自动完成追踪）"""
        self.lifecycle.after_run(success)
    
    def on_iteration(self) -> None:
        """迭代钩子（自动记录）"""
        self.lifecycle.on_iteration()
    
    # ==================== 通用工具方法（基础设施层）====================
    
    def display_task_tree(self, tree) -> None:
        """展示任务树（通用方法）"""
        display_utils.display_task_tree(tree)
    
    def display_context_state(self) -> None:
        """展示 Context 状态（通用方法）"""
        if self.context_manager:
            state = self.context_manager.get_state()
            display_utils.display_context_state(state)
    
    def display_summary(
        self,
        success: bool,
        task_stats: Optional[dict] = None
    ) -> None:
        """展示执行摘要（通用方法）"""
        obs_stats = None
        if self.observability:
            obs_stats = {
                'phases': len(self.observability.phases),
                'traces': len(self.observability.traces),
                'counters': dict(self.observability.counters)
            }
        
        display_utils.display_execution_summary(
            success=success,
            iterations=self.lifecycle.iteration_count,
            duration=self.lifecycle.get_duration(),
            task_stats=task_stats,
            observability_stats=obs_stats
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            **self.lifecycle.get_stats(),
            "name": self.name,
            "model": self.model,
        }
        
        if self.observability:
            stats["observability"] = {
                "phases": len(self.observability.phases),
                "metrics": len(self.observability.metrics),
                "traces": len(self.observability.traces),
                "counters": dict(self.observability.counters)
            }
        
        return stats
    
    # ==================== 抽象方法（业务逻辑层实现）====================
    
    @abstractmethod
    async def run(self, input_data: Any, **kwargs) -> Any:
        """
        运行 Loop（业务逻辑）
        
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    async def step(self, **kwargs) -> bool:
        """
        执行单步（业务逻辑）
        
        子类必须实现此方法
        """
        pass
    
    def stop(self) -> None:
        """停止 Loop"""
        self.lifecycle.is_running = False
        _logger.info(f"Loop stopped: {self.name}")



