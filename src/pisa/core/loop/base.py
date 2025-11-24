"""
Agent Loop Base Interface (v4.0 Refactored)

职责：
1. 定义 IAgentLoop 接口
2. 提供 BaseAgentLoop 基类
3. 自动初始化 LoopContext（LLM交互层）
4. 自动初始化 LoopState（业务逻辑层）
5. 自动初始化所有模块（传入共享对象）

v4.0架构：
- BaseAgentLoop只负责环境管理
- 子类的run()方法实现业务逻辑
- 所有模块自动初始化并共享context/state
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from pisa.core.definition.models import AgentDefinition

from pisa.config import Config
from pisa.core.loop.state import LoopState
from pisa.core.loop.context import LoopContext
from pisa.core.loop.config import LoopConfig
from pisa.utils.observability import ObservabilityManager

_logger = logging.getLogger(__name__)


class IAgentLoop(ABC):
    """
    Agent Loop 接口
    
    所有 Loop 实现必须继承此接口
    """
    
    @abstractmethod
    async def run(self, input_data: Any, **kwargs) -> LoopState:
        """
        运行 Agent Loop
        
        Args:
            input_data: 输入数据
            **kwargs: 额外参数
            
        Returns:
            输出State
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止 Loop"""
        pass


class BaseAgentLoop(IAgentLoop):
    """
    Agent Loop 基类 (v4.0)
    
    职责：
    1. 初始化 LoopContext（LLM交互层）
    2. 初始化 LoopState（业务逻辑层）
    3. 自动初始化所有模块（传入共享对象）
    4. 提供标准的run接口
    
    子类只需要实现：
    - async def run(self, input_data) -> LoopState
    """
    
    # 声明需要的模块（子类可以覆盖）
    REQUIRED_MODULES = []
    
    def __init__(
        self,
        definition: Optional["AgentDefinition"] = None,
        config: Optional[LoopConfig] = None,
        **kwargs
    ):
        """
        初始化Loop
        
        自动：
        1. 加载配置
        2. 初始化LLM交互层（LoopContext）
        3. 初始化业务逻辑层（LoopState）
        4. 初始化所有模块
        5. 初始化可观测性
        
        Args:
            definition: Agent定义（优先级高）
            config: Loop配置
            **kwargs: 额外配置覆盖
        """
        # 确保 Agent SDK 已配置
        Config.setup_agent_sdk()
        
        # 1. 加载配置
        self.config = self._load_config(definition, config, kwargs)
        
        # 2. 初始化LLM交互层（共享）
        self.context = LoopContext(
            agent_id=self.config.name,
            session_id=f"session_{int(datetime.now().timestamp())}",
            **self.config.context.model_dump()
        )
        
        # 3. 初始化业务逻辑层（共享）
        self.state = LoopState()
        
        # 4. 初始化可观测性
        self.observability = ObservabilityManager(self.config.observability.model_dump())
        
        # 4.5 解析和注册capabilities
        self.tools = []  # FunctionTool列表
        self.handoffs = []  # Agent列表
        self.mcp_servers = []  # MCP Server列表
        
        # 引用全局 capability registry（供模块使用）
        from pisa.capability.registry import get_global_registry
        self.capability_registry = get_global_registry()
        
        # Debug开关（从环境变量或配置获取）
        import os
        env_debug = os.getenv('PISA_DEBUG', '0') == '1'
        config_debug = getattr(self.config.observability, 'enable_debug', False)
        self.debug_enabled = kwargs.get('debug', False) or config_debug or env_debug
        
        if definition and definition.get_capability_names():
            self._resolve_capabilities(definition.get_capability_names())
        elif hasattr(self.config, 'capabilities') and self.config.capabilities:
            self._resolve_capabilities(self.config.capabilities)
        
        # 5. 自动初始化所有模块
        self._init_modules()
        
        # 6. 状态
        self.is_running = False
        self.iteration_count = 0
        self.created_at = datetime.now()
        
        # 7. 统计信息
        self.stats = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "total_iterations": 0,
        }
        
        _logger.info(
            f"BaseAgentLoop initialized: {self.config.name}",
            extra={
                "model": self.config.model,
                "modules": list(self.config.enabled_modules.keys())
            }
        )
    
    def _load_config(
        self,
        definition: Optional["AgentDefinition"],
        config: Optional[LoopConfig],
        overrides: Dict[str, Any]
    ) -> LoopConfig:
        """
        加载配置
        
        优先级：definition > config > overrides > 默认值
        
        Args:
            definition: Agent定义
            config: Loop配置
            overrides: 覆盖配置
            
        Returns:
            LoopConfig实例
        """
        if definition:
            # 从definition构建
            return LoopConfig.from_definition(definition, **overrides)
        elif config:
            # 使用提供的config（可能被覆盖）
            if overrides:
                # 直接在原config对象上应用覆盖，避免序列化/反序列化问题
                for key, value in overrides.items():
                    if hasattr(config, key) and key not in ['modules', 'enabled_modules']:
                        setattr(config, key, value)
            return config
        else:
            # 从overrides构建
            return LoopConfig.from_dict(overrides)
    
    def _init_modules(self):
        """
        自动初始化所有模块
        
        传入：
        - 模块配置
        - 共享的LoopContext
        - 共享的LoopState（初始状态）
        - Loop引用（self）
        """
        for name, module_class in self.REQUIRED_MODULES:
            if not self.config.is_module_enabled(name):
                _logger.debug(f"Module '{name}' is disabled, skipping initialization")
                continue
            
            module_config = self.config.get_module_config(name)
            if not module_config:
                _logger.warning(f"Module '{name}' enabled but no config found")
                continue
            
            try:
                module = module_class(
                    config=module_config,
                    loop_context=self.context,
                    loop_state=self.state,
                    loop=self  # ✅ 传递 loop 引用
                )
                setattr(self, name, module)
                _logger.debug(f"Module '{name}' initialized successfully")
            except Exception as e:
                _logger.error(f"Failed to initialize module '{name}': {e}")
                raise
    
    def _resolve_capabilities(
        self,
        capability_names: List[str]
    ) -> None:
        """
        解析capabilities并注册到Loop实例
        
        职责：
        1. 从registry查询完整信息
        2. 验证存在性
        3. 分类为functions/handoffs/mcp_servers
        4. 存储到实例变量供create_agent使用
        5. 显示配置信息
        
        Args:
            capability_names: Capability名称列表
        """
        from .capability_resolver import CapabilityResolver
        from pisa.capability.registry import get_global_registry
        
        if not capability_names:
            _logger.debug("No capabilities to resolve")
            return
        
        resolver = CapabilityResolver(get_global_registry())
        
        # 显示配置的capabilities
        try:
            resolver.display_info(capability_names)
        except Exception as e:
            _logger.warning(f"Failed to display capabilities info: {e}")
        
        # 解析为SDK格式
        try:
            resolved = resolver.resolve(capability_names, raise_on_missing=True)
            
            # 存储供create_agent使用
            self.tools = resolved["functions"]
            self.handoffs = resolved["handoffs"]
            self.mcp_servers = resolved["mcp_servers"]
            
            _logger.info(
                f"Resolved capabilities: "
                f"{len(self.tools)} functions, "
                f"{len(self.handoffs)} handoffs, "
                f"{len(self.mcp_servers)} mcp_servers"
            )
            
            # ========== DEBUG: 第一层检查 - Capability注入验证 ==========
            if self.debug_enabled:
                from pisa.utils.debug import get_debug_manager
                debug_mgr = get_debug_manager()
                debug_mgr.enabled = True
                debug_mgr.display_capabilities_injection(
                    functions=self.tools,
                    handoffs=self.handoffs,
                    mcp_servers=self.mcp_servers
                )
        except ValueError as e:
            _logger.error(f"Failed to resolve capabilities: {e}")
            raise
    
    def create_agent(
        self,
        name: str,
        instructions: str,
        model: Optional[str] = None,
        include_tools: bool = True,
        **kwargs
    ):
        """
        创建Agent（自动注入tools/handoffs/mcp_servers）
        
        这是一个便捷方法，自动传入已解析的capabilities到OpenAI Agent SDK。
        
        Args:
            name: Agent名称
            instructions: 系统指令
            model: 模型名称（默认使用loop配置的模型）
            include_tools: 是否包含tools（默认True）
            **kwargs: 其他Agent参数（会覆盖默认值）
            
        Returns:
            Agent实例（已注入tools/handoffs/mcp_servers）
            
        Example:
            ```python
            # 在Loop的run方法中
            planner = self.create_agent(
                name="TaskPlanner",
                instructions="You are a task planner...",
                model="gpt-4"  # 可选，默认使用loop的model
            )
            ```
        """
        try:
            from agents import Agent
        except ImportError:
            _logger.error("OpenAI Agent SDK not installed")
            raise ImportError(
                "OpenAI Agent SDK is required. "
                "Install with: pip install openai-agents"
            )
        
        # 准备Agent参数
        agent_kwargs = {}
        
        # 自动注入capabilities（如果include_tools=True）
        if include_tools:
            if self.tools:
                agent_kwargs['tools'] = self.tools
                _logger.debug(f"Injecting {len(self.tools)} tools into Agent")
            
            if self.handoffs:
                agent_kwargs['handoffs'] = self.handoffs
                _logger.debug(f"Injecting {len(self.handoffs)} handoffs into Agent")
            
            if self.mcp_servers:
                agent_kwargs['mcp_servers'] = self.mcp_servers
                _logger.debug(f"Injecting {len(self.mcp_servers)} mcp_servers into Agent")
        
        # 应用用户提供的kwargs（可以覆盖）
        agent_kwargs.update(kwargs)
        
        # 创建Agent
        agent = Agent(
            name=name,
            instructions=instructions,
            model=model or self.config.model,
            **agent_kwargs
        )
        
        _logger.debug(f"Created Agent: {name} with model {model or self.config.model}")
        
        # ========== DEBUG: Agent创建和SDK注入验证 ==========
        if self.debug_enabled:
            from pisa.utils.debug import get_debug_manager
            debug_mgr = get_debug_manager()
            
            # 显示Agent创建信息
            debug_mgr.display_agent_creation(
                name=name,
                model=model or self.config.model,
                instructions=instructions,
                has_tools=bool(self.tools),
                has_handoffs=bool(self.handoffs),
                has_mcp=bool(self.mcp_servers)
            )
            
            # 验证SDK注入
            debug_mgr.display_sdk_verification(
                agent_obj=agent,
                expected_tools=len(self.tools),
                expected_handoffs=len(self.handoffs),
                expected_mcp=len(self.mcp_servers)
            )
        
        return agent
    
    def before_run(self) -> None:
        """运行前钩子"""
        self.is_running = True
        self.stats["total_runs"] += 1
        _logger.debug(f"{self.config.name}: before_run()")
    
    def after_run(self, success: bool = True) -> None:
        """
        运行后钩子
        
        Args:
            success: 是否成功
        """
        self.is_running = False
        if success:
            self.stats["successful_runs"] += 1
        else:
            self.stats["failed_runs"] += 1
        _logger.debug(f"{self.config.name}: after_run(success={success})")
    
    def on_iteration(self) -> None:
        """每次迭代时调用"""
        self.iteration_count += 1
        self.stats["total_iterations"] += 1
    
    @abstractmethod
    async def run(self, input_data: Any, **kwargs) -> LoopState:
        """
        运行 Loop（子类必须实现）
        
        Args:
            input_data: 输入数据
            **kwargs: 额外参数
            
        Returns:
            最终的LoopState
        """
        pass
    
    def stop(self) -> None:
        """停止 Loop"""
        self.is_running = False
        _logger.info(f"{self.config.name}: Loop stopped")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            **self.stats,
            "name": self.config.name,
            "model": self.config.model,
            "uptime_seconds": (datetime.now() - self.created_at).total_seconds(),
            "current_iteration": self.iteration_count,
            "is_running": self.is_running,
        }

