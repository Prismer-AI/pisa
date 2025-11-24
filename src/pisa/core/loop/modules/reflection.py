"""
Reflection Module (Refactored v4.0)

自我反思模块，分析执行结果、识别问题、提供改进建议。
继承 BaseModule，支持配置透传和可观测性。

核心接口：
- __call__(state) → state  # 默认反思操作（分析执行结果）

核心功能：
1. 结果分析：评估任务执行质量
2. 错误识别：发现执行中的问题
3. 改进建议：提供优化方案
4. 学习总结：提炼经验教训
"""

import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from pisa.core.loop.state import LoopState
    from pisa.core.loop.context import LoopContext

from pisa.config import Config
from .base import BaseModule, ReflectionModuleConfig

_logger = logging.getLogger(__name__)


class ReflectionResult(BaseModel):
    """
    反思结果
    
    结构化存储反思输出
    """
    # 执行评估
    success_evaluation: bool = Field(description="任务是否成功完成")
    quality_score: Optional[float] = Field(default=None, description="质量评分 (0-1)")
    
    # 分析
    analysis: str = Field(description="详细分析")
    strengths: List[str] = Field(default_factory=list, description="做得好的地方")
    weaknesses: List[str] = Field(default_factory=list, description="不足之处")
    
    # 问题识别
    identified_issues: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="识别的问题列表"
    )
    
    # 改进建议
    improvements: List[str] = Field(default_factory=list, description="改进建议")
    alternative_approaches: List[str] = Field(
        default_factory=list,
        description="替代方案"
    )
    
    # 学习总结
    lessons_learned: List[str] = Field(default_factory=list, description="经验教训")
    should_retry: bool = Field(default=False, description="是否建议重试")
    should_replan: bool = Field(default=False, description="是否建议重新规划")
    
    # 元数据
    reflected_at: datetime = Field(default_factory=datetime.now)
    raw_output: Optional[str] = Field(default=None, description="Agent 原始输出")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReflectionModule(BaseModule):
    """
    反思模块（重构版v4.0）
    
    使用 OpenAI Agent SDK 进行自我反思和分析。
    
    新接口：
    - __call__(state) → state  # 默认反思操作（分析执行结果）
    
    职责：
    1. 分析任务执行结果
    2. 识别问题和错误
    3. 提供改进建议
    4. 总结经验教训
    
    改进：
    - 严格遵循 OpenAI Agent SDK
    - 反思策略由 instructions 控制
    - 输出结构化的反思结果
    - 继承 BaseModule
    """
    
    # ==================== 依赖声明 ====================
    
    STATE_REQUIRES = ['task', 'result']  # 需要任务和执行结果
    STATE_PRODUCES = ['orientation', 'metadata']  # orientation = OODA的Orient阶段
    
    # ==================== 初始化 ====================
    
    def __init__(
        self,
        config: Optional[ReflectionModuleConfig] = None,
        loop_context: Optional['LoopContext'] = None,
        loop_state: Optional['LoopState'] = None,
        loop: Optional[Any] = None,
        instructions: Optional[str] = None,
        **agent_kwargs
    ):
        """
        初始化反思模块
        
        Args:
            config: 反思模块配置
            loop_context: Loop的LLM交互上下文（共享）
            loop_state: Loop的业务状态（共享，可选）
            loop: BaseAgentLoop 引用
            instructions: 反思 agent 的指令（控制反思策略）
            **agent_kwargs: 传递给 Agent 的额外参数
        """
        # 初始化配置
        if config is None:
            config = ReflectionModuleConfig()
        
        # 调用基类初始化
        super().__init__(
            config=config,
            loop_context=loop_context,
            loop_state=loop_state,
            loop=loop,
            module_type="ReflectionModule",
            **agent_kwargs
        )
        
        # 解析模型配置（优先使用 reflection_model）
        reflection_model = config.reflection_model or self.model
        
        # 默认的反思指令（如果没有提供）
        self.instructions = instructions or self._get_default_instructions()
        
        # 额外的 agent 参数
        self.agent_kwargs = agent_kwargs
        
        self.logger.info(
            "ReflectionModule initialized",
            reflection_model=reflection_model,
            has_context=self.context is not None
        )
    
    def _get_default_instructions(self) -> str:
        """获取默认的反思指令"""
        return """You are an expert analyzer and reflector. Your job is to critically analyze task execution results, identify issues, and provide actionable improvements.

**Guidelines**:
1. Be objective and constructive in your analysis
2. Focus on both what went well and what needs improvement
3. Identify root causes of problems, not just symptoms
4. Provide specific, actionable recommendations
5. Consider alternative approaches that might work better
6. Learn from both successes and failures

**Analysis Framework**:
- **Success Evaluation**: Did the task achieve its goal?
- **Quality Assessment**: How well was it done?
- **Strengths**: What worked well?
- **Weaknesses**: What could be improved?
- **Issues**: What specific problems occurred?
- **Improvements**: How can we do better next time?
- **Alternatives**: What other approaches could work?
- **Lessons**: What did we learn?

**Output Format**:
Return a JSON object:
{
    "success_evaluation": true/false,
    "quality_score": 0.0-1.0,
    "analysis": "detailed analysis",
    "strengths": ["strength 1", "strength 2"],
    "weaknesses": ["weakness 1", "weakness 2"],
    "identified_issues": [
        {
            "issue": "issue description",
            "severity": "low/medium/high",
            "root_cause": "analysis of root cause"
        }
    ],
    "improvements": ["improvement 1", "improvement 2"],
    "alternative_approaches": ["approach 1", "approach 2"],
    "lessons_learned": ["lesson 1", "lesson 2"],
    "should_retry": true/false,
    "should_replan": true/false
}
"""
    
    # ==================== 新接口（State → State）====================
    
    async def _execute(self, state: 'LoopState') -> Dict[str, Any]:
        """
        默认的反思操作：分析执行结果（State → State接口）
        
        Args:
            state: 输入State（需要task和result字段）
        
        Returns:
            包含reflection和metadata的字典
        """
        task = state.task
        result = state.result
        
        # 提取task_description
        if isinstance(task, dict):
            task_description = task.get('task_description', task.get('description', str(task)))
        else:
            task_description = getattr(task, 'task_description', getattr(task, 'description', str(task)))
        
        # 调用reflect方法进行反思
        reflection_result = await self.reflect(
            task_description=task_description,
            execution_result=result,
            context=state.metadata.get('context', {})
        )
        
        # 更新统计
        self.stats["reflections_performed"] = self.stats.get("reflections_performed", 0) + 1
        if reflection_result.identified_issues:
            self.stats["issues_identified"] = self.stats.get("issues_identified", 0) + len(reflection_result.identified_issues)
        if reflection_result.improvements:
            self.stats["improvements_suggested"] = self.stats.get("improvements_suggested", 0) + len(reflection_result.improvements)
        
        # 更新到Context（可选）
        if self.context:
            self.context.add_message(
                role="assistant",
                content=f"Reflection: {reflection_result.analysis[:200]}..."
            )
        
        return {
            "orientation": reflection_result,  # 使用orientation字段（OODA的Orient阶段）
            "metadata": {
                **state.metadata,
                "reflection": {
                    "success": reflection_result.success_evaluation,
                    "quality_score": reflection_result.quality_score,
                    "issues_count": len(reflection_result.identified_issues),
                    "should_retry": reflection_result.should_retry,
                    "should_replan": reflection_result.should_replan
                }
            }
        }
    
    # ==================== 统计 ====================
    
    def _init_stats(self) -> Dict[str, Any]:
        """初始化统计信息"""
        return {
            "module_type": "ReflectionModule",
            "reflections_performed": 0,
            "issues_identified": 0,
            "improvements_suggested": 0,
            "initialized": False,
        }
    
    async def reflect_on_success(
        self,
        task: Any,
        outcome: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ReflectionResult:
        """
        对成功执行进行反思
        
        Args:
            task: 任务信息
            outcome: 执行结果
            context: 上下文信息
        
        Returns:
            反思结果
        """
        task_description = str(task) if not isinstance(task, str) else task
        return await self.reflect(
            task_description=task_description,
            execution_result=outcome,
            context=context
        )
    
    async def reflect_on_failure(
        self,
        task: Any,
        outcome: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ReflectionResult:
        """
        对失败执行进行反思
        
        Args:
            task: 任务信息
            outcome: 执行结果
            context: 上下文信息
        
        Returns:
            反思结果
        """
        task_description = str(task) if not isinstance(task, str) else task
        return await self.reflect(
            task_description=task_description,
            execution_result=outcome,
            context=context
        )
    
    async def reflect(
        self,
        task_description: str,
        execution_result: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> ReflectionResult:
        """
        对任务执行结果进行反思
        
        Args:
            task_description: 任务描述
            execution_result: 执行结果
            context: 额外上下文（如执行日志、错误信息等）
            
        Returns:
            ReflectionResult 对象
        """
        self.log_operation("reflect", status="running", task=task_description)
        
        # 准备输入
        input_text = self._build_reflection_input(
            task_description,
            execution_result,
            context
        )
        
        try:
            from agents import Agent, Runner
            
            # 确保 Agent SDK 已配置
            Config.setup_agent_sdk()
            
            # 创建 reflection agent
            reflection_agent = Agent(
                name="Reflector",
                instructions=self.instructions,
                model=self.model,
                **self.agent_kwargs
            )
            
            # 运行反思
            result = await Runner.run(
                starting_agent=reflection_agent,
                input=input_text
            )
            
            # 解析输出
            reflection_result = self._parse_reflection_output(
                result.final_output,
                result
            )
            
            # 更新统计
            self.stats["reflections_performed"] += 1
            self.stats["issues_identified"] += len(reflection_result.identified_issues)
            self.stats["improvements_suggested"] += len(reflection_result.improvements)
            
            _logger.info(
                f"Reflection completed: "
                f"success={reflection_result.success_evaluation}, "
                f"issues={len(reflection_result.identified_issues)}, "
                f"improvements={len(reflection_result.improvements)}"
            )
            
            return reflection_result
            
        except ImportError:
            _logger.error("OpenAI Agent SDK not available")
            raise RuntimeError(
                "OpenAI Agent SDK is required for reflection. "
                "Please install: pip install agents-sdk"
            )
        except Exception as e:
            _logger.error(f"Failed to perform reflection: {e}", exc_info=True)
            # 返回降级的反思结果
            return self._create_fallback_reflection(task_description, execution_result, str(e))
    
    async def reflect_on_failure(
        self,
        task_description: str,
        error: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ReflectionResult:
        """
        对失败任务进行专门的反思
        
        Args:
            task_description: 任务描述
            error: 错误信息
            context: 额外上下文
            
        Returns:
            ReflectionResult 对象
        """
        _logger.info(f"Reflecting on failed task: {task_description}")
        
        failure_context = {
            **(context or {}),
            "execution_status": "failed",
            "error_message": error,
            "focus": "failure analysis and recovery"
        }
        
        return await self.reflect(
            task_description=task_description,
            execution_result={"status": "failed", "error": error},
            context=failure_context
        )
    
    async def reflect_on_batch(
        self,
        tasks: List[Dict[str, Any]]
    ) -> Dict[str, ReflectionResult]:
        """
        对多个任务的执行结果进行批量反思
        
        Args:
            tasks: 任务列表，每个任务包含 description, result, context
            
        Returns:
            任务ID到反思结果的映射
        """
        _logger.info(f"Performing batch reflection on {len(tasks)} tasks")
        
        reflections = {}
        for task in tasks:
            task_id = task.get("task_id", str(id(task)))
            
            try:
                reflection = await self.reflect(
                    task_description=task.get("description", "Unknown task"),
                    execution_result=task.get("result"),
                    context=task.get("context")
                )
                reflections[task_id] = reflection
            except Exception as e:
                _logger.error(f"Failed to reflect on task {task_id}: {e}")
                reflections[task_id] = self._create_fallback_reflection(
                    task.get("description", ""),
                    task.get("result"),
                    str(e)
                )
        
        return reflections
    
    def _build_reflection_input(
        self,
        task_description: str,
        execution_result: Any,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """构建反思输入"""
        import json
        
        parts = [
            f"**Task**: {task_description}",
            f"\n**Execution Result**:\n{json.dumps(execution_result, indent=2, default=str)}"
        ]
        
        if context:
            parts.append(f"\n**Context**:\n{json.dumps(context, indent=2, default=str)}")
        
        parts.append("\nPlease analyze this task execution and provide a detailed reflection.")
        
        return "\n".join(parts)
    
    def _parse_reflection_output(
        self,
        output: str,
        agent_result: Any
    ) -> ReflectionResult:
        """
        解析反思输出
        
        Args:
            output: Agent 输出
            agent_result: Agent 运行结果
            
        Returns:
            ReflectionResult 对象
        """
        import json
        
        try:
            # 提取 JSON（可能包含在 markdown 代码块中）
            reflection_data = self._extract_json(output)
            
            # 创建 ReflectionResult
            result = ReflectionResult(
                success_evaluation=reflection_data.get("success_evaluation", True),
                quality_score=reflection_data.get("quality_score"),
                analysis=reflection_data.get("analysis", ""),
                strengths=reflection_data.get("strengths", []),
                weaknesses=reflection_data.get("weaknesses", []),
                identified_issues=reflection_data.get("identified_issues", []),
                improvements=reflection_data.get("improvements", []),
                alternative_approaches=reflection_data.get("alternative_approaches", []),
                lessons_learned=reflection_data.get("lessons_learned", []),
                should_retry=reflection_data.get("should_retry", False),
                should_replan=reflection_data.get("should_replan", False),
                raw_output=output,
                metadata={
                    "model": getattr(agent_result, "model", None),
                    "usage": getattr(agent_result, "usage", None),
                }
            )
            
            return result
            
        except Exception as e:
            _logger.warning(f"Failed to parse structured output: {e}")
            # 降级：创建基本的反思结果
            return ReflectionResult(
                success_evaluation=True,
                quality_score=0.7,  # 给一个中等的默认分数
                analysis=output,
                raw_output=output,
                metadata={"parsing_error": str(e)}
            )
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """从文本中提取 JSON"""
        import json
        
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
        
        return json.loads(text)
    
    def _create_fallback_reflection(
        self,
        task_description: str,
        execution_result: Any,
        error: str
    ) -> ReflectionResult:
        """创建降级的反思结果（当 Agent 调用失败时）"""
        return ReflectionResult(
            success_evaluation=False,
            analysis=f"Reflection failed: {error}",
            identified_issues=[
                {
                    "issue": "Reflection system error",
                    "severity": "high",
                    "root_cause": error
                }
            ],
            improvements=["Fix reflection system"],
            should_retry=True,
            raw_output=f"Error: {error}",
            metadata={
                "fallback": True,
                "task_description": task_description,
                "execution_result": str(execution_result)
            }
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取反思统计信息
        
        Returns:
            统计信息字典
        """
        return {
            **self.stats,
            "model": self.model,
        }
