"""
Planner

任务规划器，使用 OpenAI Agent SDK 生成任务计划。

改进：
- 严格遵循 OpenAI Agent SDK
- 规划原则由上层 instruction 控制
- 输出结构化的任务树
- 支持自定义规划策略
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from pisa.config import Config
from .task_tree import TaskTree, TaskNode, TaskStatus

_logger = logging.getLogger(__name__)


class Planner:
    """
    任务规划器
    
    使用 OpenAI Agent SDK 创建 planner agent，根据目标生成任务计划。
    规划原则由 instructions 控制，不硬编码。
    """
    
    def __init__(
        self,
        instructions: Optional[str] = None,
        model: Optional[str] = None,
        max_turns: int = 2,
        **agent_kwargs
    ):
        """
        初始化规划器
        
        Args:
            instructions: 规划 agent 的指令（控制规划原则和策略）
            model: 使用的模型
            max_turns: SDK Agent 最大 turns（从定义层穿透）
            **agent_kwargs: 传递给 Agent 的额外参数
        """
        # 确保 Agent SDK 已配置
        Config.setup_agent_sdk()
        
        self.model = model or Config.agent_default_model
        self.max_turns = max_turns
        
        # 默认的规划指令（如果没有提供）
        self.instructions = instructions or self._get_default_instructions()
        
        # 额外的 agent 参数
        self.agent_kwargs = agent_kwargs
        
        _logger.info(f"Planner initialized with model: {self.model}, max_turns: {self.max_turns}")
    
    def _get_default_instructions(self) -> str:
        """获取默认的规划指令"""
        return """You are an expert task planner. Your job is to break down high-level goals into concrete, executable tasks.

**CRITICAL REQUIREMENTS**:
1. Every task MUST be assigned to an available capability from the list provided
2. The `detail_info` field must contain ACTUAL VALUES, NOT schemas or descriptions
3. Extract concrete data from the user's goal and put it in `detail_info`

**Guidelines**:
1. Analyze the goal thoroughly before planning
2. Break down complex goals into manageable sub-tasks
3. Identify dependencies between tasks
4. Create a clear execution order
5. Each task should be specific and actionable
6. Assign each task to ONE capability from the available capabilities list
7. **EXTRACT actual data from the goal and put it in `detail_info`**

**Capability Assignment Rules**:
- Every task MUST have a non-null `assigned_capability`
- The `assigned_capability` MUST be exactly one of the names from the available capabilities list
- Do NOT create fictional capability names
- Task descriptions should match what the assigned capability can do

**detail_info MUST contain ACTUAL VALUES**:
- ❌ WRONG: `{"operation": "string", "matrix_a": "array"}`  (this is a schema!)
- ✅ CORRECT: `{"operation": "multiply", "matrix_a": [[1,2],[3,4]], "matrix_b": [[5,6],[7,8]]}`
- Extract concrete values from the user's goal
- Use real data, not type descriptions
- If the user provides matrices like [[1,2],[3,4]], include them as-is in detail_info

**Output Format**:
Return a JSON object with this exact structure:
{
    "analysis": "Your analysis of the goal",
    "strategy": "Your planning strategy",
    "tasks": [
        {
            "task_id": "task_01",
            "description": "Clear description of what needs to be done",
            "detail_info": {
                "ACTUAL_PARAMETER_NAME_1": "ACTUAL_VALUE_1",
                "ACTUAL_PARAMETER_NAME_2": "ACTUAL_VALUE_2"
            },
            "dependencies": [],
            "assigned_capability": "exact_capability_name_from_list"
        }
    ],
    "execution_order": ["task_01"]
}

**Complete Example 1 - Matrix Operations**:
Goal: "计算两个矩阵的乘法：[[1,2],[3,4]] 和 [[5,6],[7,8]]"
Available Capabilities: ["matrix_operations", "compute_softmax"]

Correct Output:
{
    "analysis": "User wants to multiply two specific 2x2 matrices",
    "strategy": "Use matrix_operations capability with multiply operation",
    "tasks": [{
        "task_id": "task_01",
        "description": "Multiply the two matrices [[1,2],[3,4]] and [[5,6],[7,8]]",
        "detail_info": {
            "operation": "multiply",
            "matrix_a": [[1, 2], [3, 4]],
            "matrix_b": [[5, 6], [7, 8]]
        },
        "dependencies": [],
        "assigned_capability": "matrix_operations"
    }],
    "execution_order": ["task_01"]
}

**Complete Example 2 - Softmax**:
Goal: "Calculate softmax of [2.0, 1.0, 0.1]"
Available Capabilities: ["compute_softmax", "matrix_operations"]

Correct Output:
{
    "analysis": "User wants to compute softmax of a specific vector",
    "strategy": "Use compute_softmax capability with the provided data",
    "tasks": [{
        "task_id": "task_01",
        "description": "Compute softmax of the vector [2.0, 1.0, 0.1]",
        "detail_info": {
            "input_data": [2.0, 1.0, 0.1],
            "axis": -1,
            "temperature": 1.0
        },
        "dependencies": [],
        "assigned_capability": "compute_softmax"
    }],
    "execution_order": ["task_01"]
}

Remember: 
- Extract ACTUAL data from the goal
- Put REAL VALUES in detail_info
- DO NOT use type descriptions or schemas
"""
    
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
        _logger.info(f"Creating plan for goal: {goal}")
        _logger.info(f"Available capabilities: {available_capabilities}")
        
        # 准备输入
        input_text = self._build_planning_input(goal, context, available_capabilities)
        
        # 使用 OpenAI Agent SDK 创建 planner agent
        try:
            from agents import Agent, Runner
            
            # 确保 Agent SDK 已配置（双重保险）
            Config.setup_agent_sdk()
            
            # 创建 planner agent
            planner_agent = Agent(
                name="TaskPlanner",
                instructions=self.instructions,
                model=self.model,
                **self.agent_kwargs
            )
            
            # 运行 planner（使用从定义层穿透的 max_turns）
            result = await Runner.run(
                starting_agent=planner_agent,
                input=input_text,
                max_turns=self.max_turns
            )
            
            # 解析输出
            plan_output = result.final_output
            
            # 构建 TaskTree
            task_tree = self._parse_plan_output(goal, plan_output, result)
            
            _logger.info(
                f"Plan created: {len(task_tree.tasks)} tasks, "
                f"execution order: {len(task_tree.execution_order)}"
            )
            
            # ========== DEBUG: 显示创建的计划详情 ==========
            if len(task_tree.tasks) == 0:
                _logger.warning(f"⚠️ Planner created an EMPTY plan! Agent output: {plan_output[:200]}")
            else:
                _logger.info(f"✅ Plan has {len(task_tree.tasks)} tasks")
                for task_id, task in list(task_tree.tasks.items())[:3]:
                    _logger.info(f"  - {task_id}: {task.task_description[:60]}... -> {task.assigned_capability}")
            
            return task_tree
            
        except ImportError:
            _logger.error("OpenAI Agent SDK not available")
            raise RuntimeError(
                "OpenAI Agent SDK is required for planning. "
                "Please install: pip install agents-sdk"
            )
        except Exception as e:
            _logger.error(f"Failed to create plan: {e}", exc_info=True)
            raise
    
    def _build_planning_input(
        self,
        goal: str,
        context: Optional[Dict[str, Any]],
        available_capabilities: Optional[List[str]]
    ) -> str:
        """构建规划输入"""
        parts = [f"**Goal**: {goal}"]
        
        if context:
            parts.append(f"\n**Context**:\n{json.dumps(context, indent=2)}")
        
        # ========== 强调Available Capabilities（带参数信息）==========
        if available_capabilities:
            parts.append("\n" + "="*80)
            parts.append("🎯 **AVAILABLE CAPABILITIES** (You MUST choose from this exact list):")
            parts.append("="*80)
            
            # 获取capability registry来提取参数信息
            try:
                from pisa.capability.registry import get_global_registry
                registry = get_global_registry()
                
                for i, cap_name in enumerate(available_capabilities, 1):
                    cap = registry.get(cap_name)
                    if cap:
                        # 根据 capability 类型展示不同的参数信息
                        if cap.capability_type == "agent":
                            # Agent 类型：通过 handoff 调用，接受文本输入
                            parts.append(f"  {i}. '{cap_name}' (Subagent) - 通过 handoff 调用")
                            parts.append(f"      📝 输入方式: 直接提供文本描述即可，SDK 自动处理")
                            parts.append(f"      ⚠️  不要使用 detail_info，将任务描述直接写在 task_description 中")
                            if cap.description:
                                parts.append(f"      描述: {cap.description[:80]}")
                        elif hasattr(cap, 'func'):
                            # Function/MCP 类型：从签名提取参数
                            import inspect
                            sig = inspect.signature(cap.func)
                            params = []
                            for param_name, param in sig.parameters.items():
                                if param_name in ['self', 'cls', 'kwargs', 'args']:
                                    continue
                                # 获取类型注解
                                param_type = param.annotation if param.annotation != inspect.Parameter.empty else "any"
                                # 获取默认值
                                has_default = param.default != inspect.Parameter.empty
                                required = "必需" if not has_default else "可选"
                                
                                # 简化类型显示
                                if hasattr(param_type, '__name__'):
                                    type_str = param_type.__name__
                                elif isinstance(param_type, str):
                                    type_str = param_type
                                else:
                                    type_str = str(param_type).replace('typing.', '')
                                
                                params.append(f"{param_name}({required},{type_str})")
                            
                            params_str = ", ".join(params) if params else "无参数"
                            parts.append(f"  {i}. '{cap_name}' - 参数: {params_str}")
                            if cap.description:
                                parts.append(f"      描述: {cap.description[:80]}")
                        else:
                            parts.append(f"  {i}. '{cap_name}' (无详细信息)")
                    else:
                        parts.append(f"  {i}. '{cap_name}' (未注册)")
            except Exception as e:
                _logger.warning(f"Failed to get capability details: {e}")
                # Fallback: 简单列表
                for i, cap in enumerate(available_capabilities, 1):
                    parts.append(f"  {i}. '{cap}'")
            
            parts.append("="*80)
            parts.append("")
            parts.append("⚠️ **CRITICAL RULES**:")
            parts.append("1. assigned_capability MUST be exactly one of the names above (copy-paste it)")
            parts.append("2. detail_info MUST use the EXACT parameter names shown above for each capability")
            parts.append("3. detail_info MUST contain ACTUAL VALUES extracted from the goal, NOT schemas")
            parts.append("4. If the goal mentions [[1,2],[3,4]], put that exact array in detail_info")
            parts.append("5. DO NOT put type descriptions like 'string' or 'array' in detail_info")
            parts.append("6. Match parameter names EXACTLY as shown (e.g., 'text' not 'table_data')")
        else:
            parts.append("\n⚠️ WARNING: No capabilities available! Plan accordingly.")
        
        parts.append("\n📝 **Your Task**:")
        parts.append("Create a task plan that:")
        parts.append("- Uses ONLY the capabilities listed above")
        parts.append("- Uses EXACT parameter names from the capability definitions")
        parts.append("- Extracts ACTUAL data from the goal (numbers, arrays, strings)")
        parts.append("- Puts real values in detail_info, not type descriptions")
        
        return "\n".join(parts)
    
    def _parse_plan_output(
        self,
        goal: str,
        plan_output: str,
        agent_result: Any
    ) -> TaskTree:
        """
        解析 planner 输出，构建 TaskTree
        
        Args:
            goal: 原始目标
            plan_output: Planner 的输出
            agent_result: Agent 运行结果
            
        Returns:
            TaskTree 对象
        """
        # 创建任务树
        task_tree = TaskTree(root_goal=goal)
        
        # 尝试解析 JSON 输出
        try:
            # 提取 JSON（可能包含在 markdown 代码块中）
            plan_data = self._extract_json(plan_output)
            
            # 存储 agent 输出
            task_tree.planning_output = {
                "raw_output": plan_output,
                "analysis": plan_data.get("analysis"),
                "strategy": plan_data.get("strategy"),
                "agent_result": {
                    "model": getattr(agent_result, "model", None),
                    "usage": getattr(agent_result, "usage", None),
                }
            }
            
            # 创建任务节点
            tasks = plan_data.get("tasks", [])
            validation_warnings = []
            
            for task_data in tasks:
                assigned_cap = task_data.get("assigned_capability")
                task_id = task_data.get("task_id", f"task_{len(task_tree.tasks) + 1}")
                
                # ========== VALIDATION: 检查assigned_capability ==========
                if not assigned_cap or assigned_cap == "null":
                    warning_msg = f"Task {task_id} has no assigned_capability! This will fail during execution."
                    validation_warnings.append(warning_msg)
                    _logger.warning(warning_msg)
                
                task = TaskNode(
                    task_id=task_id,
                    task_description=task_data.get("description", ""),
                    task_detail_info=task_data.get("detail_info", {}),
                    dependencies=task_data.get("dependencies", []),
                    assigned_capability=assigned_cap,
                )
                task_tree.add_task(task)
            
            # 设置执行顺序
            task_tree.execution_order = plan_data.get("execution_order", [])
            
            # 如果有validation警告，记录到task_tree
            if validation_warnings:
                if not task_tree.planning_output:
                    task_tree.planning_output = {}
                task_tree.planning_output["validation_warnings"] = validation_warnings
                _logger.warning(f"Plan created with {len(validation_warnings)} validation warnings")
            
        except Exception as e:
            _logger.warning(f"Failed to parse structured output: {e}")
            # 降级：创建单个任务
            task = TaskNode(
                task_id="task_1",
                task_description=goal,
                task_detail_info={
                    "raw_plan": plan_output,
                    "parsing_error": str(e)
                }
            )
            task_tree.add_task(task)
            task_tree.execution_order = ["task_1"]
            task_tree.planning_output = {"raw_output": plan_output, "error": str(e)}
        
        return task_tree
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取 JSON（处理 markdown 代码块）
        
        Args:
            text: 包含 JSON 的文本
            
        Returns:
            解析后的 JSON 对象
        """
        # 移除 markdown 代码块标记
        text = text.strip()
        
        # 尝试找到 JSON 代码块
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        # 解析 JSON
        return json.loads(text)
    
    async def refine_plan(
        self,
        task_tree: TaskTree,
        feedback: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskTree:
        """
        根据反馈优化计划
        
        Args:
            task_tree: 当前的任务树
            feedback: 反馈信息（为什么需要优化）
            context: 额外的上下文
            
        Returns:
            优化后的任务树
        """
        _logger.info(f"Refining plan based on feedback: {feedback}")
        
        # 构建优化输入
        input_text = f"""**Original Goal**: {task_tree.root_goal}

**Current Plan**:
- Total tasks: {len(task_tree.tasks)}
- Completed: {sum(1 for t in task_tree.tasks.values() if t.status == TaskStatus.COMPLETED)}
- Failed: {sum(1 for t in task_tree.tasks.values() if t.status == TaskStatus.FAILED)}

**Feedback**: {feedback}

**Current Task Tree**:
{self._serialize_task_tree(task_tree)}

Please refine the plan based on the feedback. You can:
1. Add new tasks
2. Modify existing tasks
3. Change task dependencies
4. Adjust execution order

Maintain the same JSON output format as before.
"""
        
        try:
            from agents import Agent, Runner
            
            # 创建 planner agent（使用相同的 instructions）
            planner_agent = Agent(
                name="TaskPlanner",
                instructions=self.instructions,
                model=self.model,
                **self.agent_kwargs
            )
            
            # 运行优化（使用从定义层穿透的 max_turns）
            result = await Runner.run(
                starting_agent=planner_agent,
                input=input_text,
                max_turns=self.max_turns
            )
            
            # 解析优化后的输出
            refined_tree = self._parse_plan_output(
                task_tree.root_goal,
                result.final_output,
                result
            )
            
            # 更新版本号
            refined_tree.plan_version = task_tree.plan_version + 1
            
            # 记录重新规划历史
            refined_tree.replanning_history = task_tree.replanning_history + [
                {
                    "version": task_tree.plan_version,
                    "feedback": feedback,
                    "timestamp": datetime.now().isoformat(),
                    "original_tasks": len(task_tree.tasks),
                    "new_tasks": len(refined_tree.tasks),
                }
            ]
            
            _logger.info(f"Plan refined: version {refined_tree.plan_version}")
            
            return refined_tree
            
        except Exception as e:
            _logger.error(f"Failed to refine plan: {e}", exc_info=True)
            # 返回原计划
            return task_tree
    
    def _serialize_task_tree(self, task_tree: TaskTree) -> str:
        """序列化任务树为可读的文本"""
        lines = []
        for task_id, task in task_tree.tasks.items():
            lines.append(f"- [{task.status.value}] {task_id}: {task.task_description}")
            if task.dependencies:
                lines.append(f"  Dependencies: {', '.join(task.dependencies)}")
        return "\n".join(lines)
