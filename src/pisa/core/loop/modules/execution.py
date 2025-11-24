"""
Execution Module (Refactored v4.0)

执行模块，负责调用 Capability 并处理结果。

核心接口：
- __call__(state) → state  # 统一的State → State接口
- execute(name, args)  # 单个capability调用（保留）
- execute_batch(requests)  # 批量调用（保留）

支持 function、agent、mcp 三种类型的 capability。
继承 BaseModule，支持配置透传和可观测性。
"""

import time
import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from pisa.core.loop.state import LoopState
    from pisa.core.loop.context import LoopContext

from pisa.capability import CapabilityRegistry, Capability, get_global_registry
from .base import BaseModule, ExecutionModuleConfig

_logger = logging.getLogger(__name__)


class CapabilityCallRequest(Dict):
    """
    Capability 调用请求
    
    简化版，使用字典兼容 OpenAI tool call 格式
    """
    def __init__(
        self,
        capability_name: str,
        arguments: Dict[str, Any],
        call_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            capability_name=capability_name,
            arguments=arguments,
            call_id=call_id or f"call_{int(time.time() * 1000)}",
            **kwargs
        )


class CapabilityCallResult(Dict):
    """
    Capability 调用结果
    
    简化版，使用字典兼容 OpenAI tool result 格式
    """
    def __init__(
        self,
        call_id: str,
        capability_name: str,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        execution_time: float = 0.0,
        retries: int = 0,
        **kwargs
    ):
        super().__init__(
            call_id=call_id,
            capability_name=capability_name,
            success=success,
            result=result,
            error=error,
            execution_time=execution_time,
            retries=retries,
            **kwargs
        )


class ExecutionModule(BaseModule):
    """
    执行模块（重构版v4.0）
    
    核心功能：
    - Function capabilities: 直接调用函数
    - Agent capabilities: 调用 Agent.run()
    - MCP capabilities: 调用 MCP server
    - 异步/同步执行
    - 批量并发执行
    - 错误处理和重试
    
    新接口：
    - __call__(state) → state  # 执行state.task中的capability调用
    - execute(name, args)  # 单个调用（保留）
    - execute_batch(requests)  # 批量调用（保留）
    """
    
    # ==================== 依赖声明 ====================
    
    STATE_REQUIRES = ['task']  # 需要任务信息
    STATE_PRODUCES = ['result', 'metadata']  # 产生执行结果和元数据
    
    # ==================== 初始化 ====================
    
    def __init__(
        self,
        config: Optional[ExecutionModuleConfig] = None,
        loop_context: Optional['LoopContext'] = None,
        loop_state: Optional['LoopState'] = None,
        loop: Optional[Any] = None,
        registry: Optional[CapabilityRegistry] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[float] = None,
        **kwargs
    ):
        """
        初始化执行模块
        
        Args:
            config: 执行模块配置
            loop_context: Loop的LLM交互上下文（共享）
            loop_state: Loop的业务状态（共享，可选）
            loop: BaseAgentLoop 引用
            registry: Capability 注册表（默认使用全局注册表）
            max_retries: 最大重试次数（None 则使用 config 中的值）
            timeout: 超时时间（秒，None 则使用 config 中的值）
            **kwargs: 额外参数
        """
        # 初始化配置
        if config is None:
            config = ExecutionModuleConfig()
        
        # 调用基类初始化
        super().__init__(
            config=config,
            loop_context=loop_context,
            loop_state=loop_state,
            loop=loop,
            module_type="ExecutionModule",
            **kwargs
        )
        
        self.registry = registry or get_global_registry()
        self.max_retries = max_retries or config.max_retries
        self.timeout = timeout or config.timeout_seconds or 30.0
        
        self.logger.info(
            "ExecutionModule initialized",
            max_retries=self.max_retries,
            timeout=self.timeout,
            has_context=self.context is not None
        )
        
        _logger.info(f"ExecutionModule initialized with {len(self.registry.list_all())} capabilities")
    
    def _init_stats(self) -> Dict[str, Any]:
        """初始化统计信息"""
        return {
            "module_type": "ExecutionModule",
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_retries": 0,
            "initialized": False,
        }
    
    # ==================== 新接口（State → State）====================
    
    async def _execute(self, state: 'LoopState') -> Dict[str, Any]:
        """
        执行任务中的capability调用（State → State接口）
        
        从state.task中提取capability调用信息并执行。
        
        Args:
            state: 输入State（需要task字段）
        
        Returns:
            包含result和metadata的字典
        
        Example:
            state.task应包含:
            {
                "capability_name": "search_arxiv",
                "arguments": {"query": "AI agents"}
            }
        """
        task = state.task
        
        # 提取capability调用信息
        if isinstance(task, dict):
            capability_name = task.get("capability_name") or task.get("assigned_capability")
            task_description = task.get("task_description", task.get("description", ""))
            task_detail_info = task.get("task_detail_info", {})
            call_id = task.get("call_id") or task.get("task_id")
        else:
            # 如果task是对象，尝试获取属性（支持两种字段名）
            capability_name = (
                getattr(task, "capability_name", None) or 
                getattr(task, "assigned_capability", None)
            )
            task_description = getattr(task, "task_description", getattr(task, "description", ""))
            task_detail_info = getattr(task, "task_detail_info", {})
            call_id = getattr(task, "call_id", None) or getattr(task, "task_id", None)
        
        # ========== 智能参数映射 ==========
        # 如果task有预定义的arguments，使用它
        # ⭐ 优先使用 task_detail_info 中的参数（Planner 已经生成了正确的参数）
        arguments = task.get("arguments") if isinstance(task, dict) else getattr(task, "arguments", None)
        
        if not arguments:
            # 如果 task_detail_info 本身就是完整的参数字典，直接使用它
            if task_detail_info and isinstance(task_detail_info, dict):
                # 检查 task_detail_info 是否包含实际参数（非元数据）
                has_actual_params = any(
                    key not in ['steps', 'considerations', 'estimated_complexity', 'notes']
                    for key in task_detail_info.keys()
                )
                
                if has_actual_params:
                    # Planner 已经生成了正确的参数，直接使用！
                    arguments = task_detail_info
                    _logger.info(f"Using task_detail_info as arguments: {list(arguments.keys())}")
                else:
                    # task_detail_info 只包含元数据，需要智能映射
                    arguments = self._build_arguments_from_task(
                        capability_name=capability_name,
                        task_description=task_description,
                        task_detail_info=task_detail_info
                    )
            else:
                # 没有 task_detail_info，使用智能映射
                arguments = self._build_arguments_from_task(
                    capability_name=capability_name,
                    task_description=task_description,
                    task_detail_info=task_detail_info or {}
                )
        
        if not capability_name:
            raise ValueError(
                f"ExecutionModule requires task.capability_name or task.assigned_capability, "
                f"but both are None or missing. Task: {task}"
            )
        
        # 调用现有的execute方法（传递task_description用于subagent）
        result = await self.execute(
            capability_name=capability_name,
            arguments=arguments,
            call_id=call_id,
            task_description=task_description  # ⭐ 传递任务描述给 subagent
        )
        
        # 记录到Context（可选）
        if self.context:
            self.context.add_message(
                role="system",
                content=f"Executed {capability_name}: {result.get('success')}"
            )
        
        # 返回State更新
        return {
            "result": result,
            "metadata": {
                **state.metadata,
                "last_execution": {
                    "capability": capability_name,
                    "success": result.get("success", False),
                    "execution_time": result.get("execution_time", 0.0)
                }
            }
        }
    
    # ==================== 保留的业务逻辑 ====================
    
    async def execute(
        self,
        capability_name: str,
        arguments: Dict[str, Any],
        call_id: Optional[str] = None,
        task_description: str = "",
        **kwargs
    ) -> CapabilityCallResult:
        """
        执行单个 capability 调用
        
        Args:
            capability_name: Capability 名称
            arguments: 调用参数
            call_id: 调用 ID（可选）
            **kwargs: 额外参数
            
        Returns:
            调用结果
        """
        start_time = time.time()
        call_id = call_id or f"call_{int(time.time() * 1000)}"
        
        _logger.info(f"Executing capability: {capability_name} (call_id={call_id})")
        
        # 获取 capability
        capability = self.registry.get(capability_name)
        if capability is None:
            error_msg = f"Capability '{capability_name}' not found"
            _logger.error(error_msg)
            return CapabilityCallResult(
                call_id=call_id,
                capability_name=capability_name,
                success=False,
                error=error_msg,
                execution_time=time.time() - start_time
            )
        
        # 根据类型执行
        try:
            if capability.capability_type == "function":
                result = await self._execute_function(capability, arguments, **kwargs)
            elif capability.capability_type == "agent":
                # ⭐ 对于 agent 类型（subagent），传递 task_description
                result = await self._execute_agent(capability, arguments, task_description=task_description, **kwargs)
            elif capability.capability_type == "mcp":
                result = await self._execute_mcp(capability, arguments, **kwargs)
            else:
                raise ValueError(f"Unknown capability type: {capability.capability_type}")
            
            execution_time = time.time() - start_time
            
            # 检查结果是否包含错误（OpenAI Agent SDK 不抛出异常，而是返回错误消息）
            is_error = False
            error_msg = None
            
            if isinstance(result, str):
                # 如果结果是字符串，检查是否是错误消息
                if "error occurred" in result.lower() or "invalid json input" in result.lower():
                    is_error = True
                    error_msg = result
            elif isinstance(result, dict):
                # 如果结果是字典，检查是否有 error 或 success=False 字段
                if not result.get("success", True) or result.get("error"):
                    is_error = True
                    error_msg = result.get("error", str(result))
            
            if is_error:
                _logger.error(
                    f"Capability execution failed: {capability_name} - {error_msg}"
                )
                return CapabilityCallResult(
                    call_id=call_id,
                    capability_name=capability_name,
                    success=False,
                    error=error_msg,
                    result=result,
                    execution_time=execution_time
                )
            
            _logger.info(
                f"Capability executed successfully: {capability_name} "
                f"(time={execution_time:.2f}s)"
            )
            
            return CapabilityCallResult(
                call_id=call_id,
                capability_name=capability_name,
                success=True,
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Execution failed: {str(e)}"
            _logger.error(f"{error_msg} (capability={capability_name})", exc_info=True)
            
            return CapabilityCallResult(
                call_id=call_id,
                capability_name=capability_name,
                success=False,
                error=error_msg,
                execution_time=execution_time
            )
    
    async def execute_batch(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[CapabilityCallResult]:
        """
        批量并发执行多个 capability 调用
        
        Args:
            requests: 调用请求列表，每个包含 capability_name 和 arguments
            
        Returns:
            调用结果列表
        """
        _logger.info(f"Executing batch of {len(requests)} capabilities")
        
        # 创建异步任务
        tasks = []
        for req in requests:
            if isinstance(req, dict):
                task = self.execute(
                    capability_name=req.get("capability_name", req.get("name")),
                    arguments=req.get("arguments", {}),
                    call_id=req.get("call_id")
                )
            else:
                # 如果是 CapabilityCallRequest 对象
                task = self.execute(
                    capability_name=req["capability_name"],
                    arguments=req["arguments"],
                    call_id=req.get("call_id")
                )
            tasks.append(task)
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                req = requests[i]
                call_id = req.get("call_id", f"call_{i}")
                capability_name = req.get("capability_name", req.get("name", "unknown"))
                
                processed_results.append(CapabilityCallResult(
                    call_id=call_id,
                    capability_name=capability_name,
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        success_count = sum(1 for r in processed_results if r["success"])
        _logger.info(
            f"Batch execution completed: {success_count}/{len(requests)} successful"
        )
        
        return processed_results
    
    async def _execute_function(
        self,
        capability: Capability,
        arguments: Dict[str, Any],
        **kwargs
    ) -> Any:
        """
        执行 function 类型的 capability
        
        Args:
            capability: Capability 对象
            arguments: 函数参数
            **kwargs: 额外参数
            
        Returns:
            函数执行结果
        """
        func = self.registry.get_function(capability.name)
        
        if func is None:
            raise RuntimeError(f"Function not found for capability: {capability.name}")
        
        _logger.debug(f"Calling function: {capability.name}(**{arguments})")
        
        # 检查是否是 FunctionTool 对象（来自 OpenAI Agent SDK）
        # FunctionTool 有 on_invoke_tool 方法但自身不是 callable
        is_function_tool = (
            hasattr(func, 'on_invoke_tool') and
            hasattr(func, 'name') and
            hasattr(func, 'description')
        )
        
        if is_function_tool:
            # 这是一个 FunctionTool 对象
            # on_invoke_tool 需要 (ctx: ToolContext, input: str)
            # 我们需要将参数转换为 JSON 字符串
            import json
            from agents.tool_context import ToolContext
            
            # 将参数转换为 JSON 字符串
            input_json = json.dumps(arguments)
            
            # 创建一个简单的 context（需要 tool_name, tool_call_id, tool_arguments）
            ctx = ToolContext(
                context={},
                tool_name=capability.name,
                tool_call_id=kwargs.get('call_id', 'call_0'),
                tool_arguments=input_json
            )
            
            _logger.debug(f"Calling FunctionTool with JSON: {input_json}")
            
            # 调用 on_invoke_tool
            if asyncio.iscoroutinefunction(func.on_invoke_tool):
                result = await func.on_invoke_tool(ctx, input_json)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func.on_invoke_tool(ctx, input_json))
        elif callable(func):
            # 这是一个普通函数
            if asyncio.iscoroutinefunction(func):
                # 异步函数，直接 await
                result = await func(**arguments)
            else:
                # 同步函数，在 executor 中运行
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func(**arguments))
        else:
            # 增强错误信息，帮助调试
            func_type = type(func).__name__
            func_attrs = [attr for attr in dir(func) if not attr.startswith('_')][:10]  # 只显示前10个属性
            raise RuntimeError(
                f"Function {capability.name} is neither callable nor a FunctionTool. "
                f"Type: {func_type}, Has on_invoke_tool: {hasattr(func, 'on_invoke_tool')}, "
                f"Is callable: {callable(func)}, Attributes: {func_attrs}"
            )
        
        return result
    
    async def _execute_agent(
        self,
        capability: Capability,
        arguments: Dict[str, Any],
        task_description: str = "",
        **kwargs
    ) -> Any:
        """
        执行 agent 类型的 capability（通过 handoff）
        
        对于 subagent，输入来自 task_description，而不是 detail_info。
        这符合 OpenAI Agent SDK 的 handoff 机制。
        
        Args:
            capability: Capability 对象
            arguments: Agent 参数（通常为空或包含简单输入）
            task_description: 任务描述（作为 agent 的输入）
            **kwargs: 额外参数
            
        Returns:
            Agent 执行结果
        """
        agent = capability.agent_object
        
        if agent is None:
            raise RuntimeError(f"Agent object not found for capability: {capability.name}")
        
        # ⭐ 对于 subagent，优先使用 task_description 作为输入
        # 这符合 handoff 的设计：将任务描述传递给子 agent
        if task_description:
            user_input = task_description
        else:
            # Fallback: 从 arguments 提取（兼容性）
            user_input = arguments.get("input") or arguments.get("query") or arguments.get("message") or arguments.get("text", "")
        
        _logger.info(f"Handoff to subagent '{capability.name}' with input: {user_input[:100]}...")
        
        try:
            # 使用 OpenAI Agent SDK 的 Runner
            from agents import Runner
            
            # 运行 agent
            result = await Runner.run(
                starting_agent=agent,
                input=user_input,
                **kwargs  # 可以传递 context 等
            )
            
            # 返回最终输出
            return result.final_output if hasattr(result, 'final_output') else str(result)
            
        except ImportError:
            # 如果没有 Agent SDK，尝试直接调用 run 方法
            _logger.warning("OpenAI Agent SDK not available, trying direct run() call")
            
            if hasattr(agent, 'run'):
                if asyncio.iscoroutinefunction(agent.run):
                    result = await agent.run(user_input)
                else:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, lambda: agent.run(user_input))
                return result
            else:
                raise RuntimeError(f"Agent {capability.name} has no run() method")
    
    async def _execute_mcp(
        self,
        capability: Capability,
        arguments: Dict[str, Any],
        **kwargs
    ) -> Any:
        """
        执行 mcp 类型的 capability
        
        Args:
            capability: Capability 对象
            arguments: MCP 工具参数
            **kwargs: 额外参数
            
        Returns:
            MCP 工具执行结果
        """
        mcp_server = capability.mcp_server_object
        
        if mcp_server is None:
            raise RuntimeError(f"MCP server not found for capability: {capability.name}")
        
        # MCP 的调用方式：call_tool(tool_name, arguments)
        tool_name = arguments.get("tool_name", capability.name)
        tool_args = arguments.get("arguments", arguments)
        
        _logger.debug(f"Calling MCP tool: {tool_name}(**{tool_args})")
        
        if hasattr(mcp_server, 'call_tool'):
            if asyncio.iscoroutinefunction(mcp_server.call_tool):
                result = await mcp_server.call_tool(tool_name, tool_args)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: mcp_server.call_tool(tool_name, tool_args)
                )
            return result
        else:
            raise RuntimeError(f"MCP server {capability.name} has no call_tool() method")
    
    def get_capability_schema(self, capability_name: str) -> Optional[Dict]:
        """
        获取 capability 的参数 schema
        
        Args:
            capability_name: Capability 名称
            
        Returns:
            参数 schema（JSON Schema 格式）
        """
        capability = self.registry.get(capability_name)
        if capability is None:
            return None
        
        return capability.parameters
    
    def list_available_capabilities(self) -> List[str]:
        """
        列出所有可用的 capability
        
        Returns:
            Capability 名称列表
        """
        return self.registry.list_all()
    
    def _build_arguments_from_task(
        self,
        capability_name: str,
        task_description: str,
        task_detail_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从task信息智能构造capability参数
        
        当task没有预定义的arguments时，从task_description和task_detail_info
        中提取信息来构造符合capability签名的参数。
        
        Args:
            capability_name: Capability名称
            task_description: 任务描述
            task_detail_info: 任务详细信息（来自Planner）
            
        Returns:
            构造的参数字典
        """
        # 获取capability的参数schema
        capability = self.registry.get(capability_name)
        if not capability:
            _logger.warning(f"Capability {capability_name} not found, using task_description as default")
            return {"input": task_description}
        
        # 获取参数定义
        params_schema = capability.parameters or {}
        
        # 确保params_schema是dict类型
        if not isinstance(params_schema, dict):
            _logger.warning(f"Capability {capability_name} has non-dict parameters schema: {type(params_schema)}")
            # 尝试解析为dict
            if hasattr(params_schema, '__dict__'):
                params_schema = params_schema.__dict__
            else:
                params_schema = {}
        
        arguments = {}
        
        # 常见的参数名映射策略
        # 优先检查最常见的参数名
        param_priority = [
            'requirement',  # 最高优先级
            'query',
            'input',
            'text',
            'content',
            'prompt',
            'message'
        ]
        
        # 找到第一个存在的参数名并使用
        primary_param_set = False
        for param_name in param_priority:
            if param_name in params_schema:
                arguments[param_name] = task_description
                primary_param_set = True
                break
        
        # 4. 如果有 'data' 参数且task_detail_info中有数据
        if 'data' in params_schema and task_detail_info:
            # 尝试从task_detail_info中提取数据
            if 'data' in task_detail_info:
                arguments['data'] = task_detail_info['data']
        
        # 5. 如果task_detail_info中有明确的参数映射，使用它们
        if isinstance(task_detail_info, dict) and isinstance(params_schema, dict):
            # 检查是否有直接的参数值
            for param_name in params_schema.keys():
                if param_name in task_detail_info:
                    arguments[param_name] = task_detail_info[param_name]
        
        # 6. 如果还没有设置主参数，尝试其他策略
        if not primary_param_set and not arguments:
            # 尝试使用第一个必需参数
            required_params = []
            for param_name, param_schema in params_schema.items():
                # 处理schema可能是dict或其他类型
                if isinstance(param_schema, dict):
                    if param_schema.get('required', False):
                        required_params.append(param_name)
            
            if required_params:
                # 使用第一个必需参数
                arguments[required_params[0]] = task_description
            elif params_schema:
                # 如果没有必需参数，使用第一个参数
                first_param = next(iter(params_schema.keys()))
                arguments[first_param] = task_description
            else:
                # 完全没有schema，使用通用的input字段
                arguments['input'] = task_description
        
        _logger.debug(f"Built arguments for {capability_name}: {arguments}")
        return arguments
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取执行统计信息
        
        Returns:
            统计信息字典
        """
        capabilities = self.registry.get_all()
        
        return {
            "total_capabilities": len(capabilities),
            "by_type": {
                "function": sum(1 for c in capabilities.values() if c.capability_type == "function"),
                "agent": sum(1 for c in capabilities.values() if c.capability_type == "agent"),
                "mcp": sum(1 for c in capabilities.values() if c.capability_type == "mcp"),
            },
            "capabilities": list(capabilities.keys())
        }

