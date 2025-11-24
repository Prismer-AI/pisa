"""
Validation Module

验证模块，整合 src/pisa/core/validation 下的各个验证组件。
继承 BaseModule，支持配置透传和可观测性。

职责：
1. 协调 Input Guardrails 和 Input Validator
2. 协调 Output Guardrails 和 Output Validator
3. 提供统一的验证接口
4. 管理验证统计信息
"""

import logging
from typing import Any, Optional, Dict, List, Tuple

from pisa.core.validation import (
    InputGuardrail,
    OutputGuardrail,
    GuardrailResult,
    InputValidator,
    ValidationResult,
    OutputValidator,
    OutputValidationResult,
)
from .base import BaseModule, ValidationModuleConfig

_logger = logging.getLogger(__name__)


class ValidationModule(BaseModule):
    """
    验证模块
    
    整合多层次的验证能力：
    1. Input Guardrails: LLM 基础的输入验证
    2. Input Validator: 结构化的输入验证
    3. Output Guardrails: LLM 基础的输出验证
    4. Output Validator: 结构化的输出验证
    """
    
    def __init__(self, config: Optional[ValidationModuleConfig] = None):
        """
        初始化验证模块
        
        Args:
            config: 验证模块配置
        """
        # 初始化配置
        if config is None:
            config = ValidationModuleConfig()
        
        # 调用基类初始化
        super().__init__(config=config, module_type="ValidationModule")
        
        # 验证组件
        self.input_guardrails: List[InputGuardrail] = []
        self.output_guardrails: List[OutputGuardrail] = []
        self.input_validator = InputValidator()
        self.output_validator = OutputValidator()
        
        self.logger.info("ValidationModule initialized with config")
    
    def _init_stats(self) -> Dict[str, Any]:
        """初始化统计信息"""
        return {
            "module_type": "ValidationModule",
            "input_validations": 0,
            "input_failures": 0,
            "output_validations": 0,
            "output_failures": 0,
            "guardrails_triggered": 0,
            "initialized": False,
        }
    
    def add_input_guardrail(self, guardrail: InputGuardrail) -> None:
        """
        添加 Input Guardrail
        
        Args:
            guardrail: InputGuardrail 实例
        """
        self.input_guardrails.append(guardrail)
        self.logger.info(f"Added input guardrail: {guardrail.name}")
    
    def add_output_guardrail(self, guardrail: OutputGuardrail) -> None:
        """
        添加 Output Guardrail
        
        Args:
            guardrail: OutputGuardrail 实例
        """
        self.output_guardrails.append(guardrail)
        _logger.info(f"Added output guardrail: {guardrail.name}")
    
    async def validate_input(
        self,
        input_data: Any,
        schema: Optional[type] = None,
        context: Optional[Dict[str, Any]] = None,
        run_guardrails: bool = True
    ) -> Dict[str, Any]:
        """
        验证输入
        
        Args:
            input_data: 输入数据
            schema: 可选的 schema 验证
            context: 额外的上下文
            run_guardrails: 是否运行 guardrails
            
        Returns:
            验证结果字典
        """
        self.stats["input_validations"] += 1
        
        # 1. 结构化验证
        validation_result = self.input_validator.validate(input_data, schema)
        
        # 2. Guardrails 验证（异步）
        guardrail_results = []
        if run_guardrails and self.input_guardrails:
            input_text = str(input_data)
            for guardrail in self.input_guardrails:
                try:
                    result = await guardrail.validate(input_text, context)
                    guardrail_results.append({
                        "guardrail": guardrail.name,
                        "result": result
                    })
                    
                    if result.tripwire_triggered:
                        self.stats["guardrails_triggered"] += 1
                        _logger.warning(
                            f"Input guardrail '{guardrail.name}' triggered: "
                            f"{result.reasoning}"
                        )
                except Exception as e:
                    _logger.error(
                        f"Input guardrail '{guardrail.name}' failed: {e}",
                        exc_info=True
                    )
                    guardrail_results.append({
                        "guardrail": guardrail.name,
                        "error": str(e)
                    })
        
        # 综合结果
        is_valid = validation_result.is_valid and not any(
            gr.get("result") and gr["result"].tripwire_triggered
            for gr in guardrail_results
        )
        
        if not is_valid:
            self.stats["input_failures"] += 1
        
        return {
            "is_valid": is_valid,
            "validation": validation_result.model_dump(),
            "guardrails": guardrail_results,
            "stats": {
                "total_errors": len(validation_result.errors),
                "total_warnings": len(validation_result.warnings),
                "guardrails_triggered": sum(
                    1 for gr in guardrail_results
                    if gr.get("result") and gr["result"].tripwire_triggered
                )
            }
        }
    
    async def validate_output(
        self,
        output_data: Any,
        schema: Optional[type] = None,
        context: Optional[Dict[str, Any]] = None,
        run_guardrails: bool = True
    ) -> Dict[str, Any]:
        """
        验证输出
        
        Args:
            output_data: 输出数据
            schema: 可选的 schema 验证
            context: 额外的上下文
            run_guardrails: 是否运行 guardrails
            
        Returns:
            验证结果字典
        """
        self.stats["output_validations"] += 1
        
        # 1. 结构化验证
        validation_result = self.output_validator.validate(output_data, schema, context)
        
        # 2. Guardrails 验证（异步）
        guardrail_results = []
        if run_guardrails and self.output_guardrails:
            for guardrail in self.output_guardrails:
                try:
                    result = await guardrail.validate(output_data, context)
                    guardrail_results.append({
                        "guardrail": guardrail.name,
                        "result": result
                    })
                    
                    if result.tripwire_triggered:
                        self.stats["guardrails_triggered"] += 1
                        _logger.warning(
                            f"Output guardrail '{guardrail.name}' triggered: "
                            f"{result.reasoning}"
                        )
                except Exception as e:
                    _logger.error(
                        f"Output guardrail '{guardrail.name}' failed: {e}",
                        exc_info=True
                    )
                    guardrail_results.append({
                        "guardrail": guardrail.name,
                        "error": str(e)
                    })
        
        # 综合结果
        is_valid = validation_result.is_valid and not any(
            gr.get("result") and gr["result"].tripwire_triggered
            for gr in guardrail_results
        )
        
        if not is_valid:
            self.stats["output_failures"] += 1
        
        return {
            "is_valid": is_valid,
            "quality_score": validation_result.quality_score,
            "validation": validation_result.model_dump(),
            "guardrails": guardrail_results,
            "stats": {
                "total_issues": len(validation_result.issues),
                "total_suggestions": len(validation_result.suggestions),
                "guardrails_triggered": sum(
                    1 for gr in guardrail_results
                    if gr.get("result") and gr["result"].tripwire_triggered
                )
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取验证统计信息
        
        Returns:
            统计信息字典
        """
        return {
            **self.stats,
            "input_guardrails_count": len(self.input_guardrails),
            "output_guardrails_count": len(self.output_guardrails),
            "input_success_rate": (
                (self.stats["input_validations"] - self.stats["input_failures"]) 
                / max(self.stats["input_validations"], 1)
            ),
            "output_success_rate": (
                (self.stats["output_validations"] - self.stats["output_failures"])
                / max(self.stats["output_validations"], 1)
            ),
        }

    def validate_safety(
        self, 
        action: Dict[str, Any],
        context: Any
    ) -> Tuple[bool, str]:
        """
        验证安全性
        
        Args:
            action: 要执行的动作
            context: 上下文
            
        Returns:
            (是否安全, 验证信息)
            
        TODO: 实现安全性验证逻辑
        """
        raise NotImplementedError("待实现")
    
    def validate_compliance(
        self, 
        action: Dict[str, Any],
        rules: list
    ) -> Tuple[bool, str]:
        """
        验证合规性
        
        Args:
            action: 要执行的动作
            rules: 规则列表
            
        Returns:
            (是否合规, 验证信息)
            
        TODO: 实现合规性验证逻辑
        """
        raise NotImplementedError("待实现")

