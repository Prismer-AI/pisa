"""
Output Validator

输出验证器，验证 Agent 输出的质量和合规性。
"""

import logging
from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field

_logger = logging.getLogger(__name__)


class OutputValidationResult(BaseModel):
    """输出验证结果"""
    is_valid: bool = Field(description="是否通过验证")
    quality_score: Optional[float] = Field(default=None, description="质量评分 (0-1)")
    issues: List[str] = Field(default_factory=list, description="问题列表")
    suggestions: List[str] = Field(default_factory=list, description="改进建议")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class OutputValidator:
    """
    输出验证器
    
    验证 Agent 输出的：
    1. 格式正确性
    2. 内容完整性
    3. 质量标准
    4. 安全性
    """
    
    def __init__(self):
        """初始化输出验证器"""
        self.validators: List[callable] = []
        _logger.info("OutputValidator initialized")
    
    def add_validator(self, validator: callable) -> None:
        """
        添加自定义验证器
        
        Args:
            validator: 验证函数
        """
        self.validators.append(validator)
        _logger.debug(f"Added output validator: {validator.__name__}")
    
    def validate(
        self,
        output_data: Any,
        expected_schema: Optional[type[BaseModel]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> OutputValidationResult:
        """
        验证输出数据
        
        Args:
            output_data: 输出数据
            expected_schema: 期望的输出 schema
            context: 额外上下文
            
        Returns:
            OutputValidationResult
        """
        issues = []
        suggestions = []
        metadata = {}
        
        # 1. Schema 验证
        if expected_schema:
            try:
                from pydantic import ValidationError
                validated = expected_schema.model_validate(output_data)
                metadata["validated_output"] = validated
            except ValidationError as e:
                issues.extend([f"Schema error: {err['msg']}" for err in e.errors()])
        
        # 2. 基本验证
        basic_result = self._validate_basic(output_data)
        issues.extend(basic_result.issues)
        suggestions.extend(basic_result.suggestions)
        
        # 3. 自定义验证器
        for validator in self.validators:
            try:
                result = validator(output_data, context)
                if isinstance(result, OutputValidationResult):
                    issues.extend(result.issues)
                    suggestions.extend(result.suggestions)
                    metadata.update(result.metadata)
            except Exception as e:
                issues.append(f"Validator {validator.__name__} failed: {str(e)}")
                _logger.error(f"Output validator failed: {e}", exc_info=True)
        
        # 计算质量评分
        quality_score = self._calculate_quality_score(issues, suggestions)
        
        is_valid = len(issues) == 0
        
        return OutputValidationResult(
            is_valid=is_valid,
            quality_score=quality_score,
            issues=issues,
            suggestions=suggestions,
            metadata=metadata
        )
    
    def _validate_basic(self, output_data: Any) -> OutputValidationResult:
        """基本输出验证"""
        issues = []
        suggestions = []
        
        # 检查是否为空
        if output_data is None:
            issues.append("Output is None")
        elif isinstance(output_data, str):
            if len(output_data.strip()) == 0:
                issues.append("Output string is empty")
            elif len(output_data) < 10:
                suggestions.append("Output seems very brief, consider providing more detail")
        elif isinstance(output_data, (list, dict)) and len(output_data) == 0:
            suggestions.append("Output collection is empty")
        
        return OutputValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            suggestions=suggestions
        )
    
    def _calculate_quality_score(
        self,
        issues: List[str],
        suggestions: List[str]
    ) -> float:
        """
        计算质量评分
        
        Args:
            issues: 问题列表
            suggestions: 建议列表
            
        Returns:
            质量评分 (0-1)
        """
        if len(issues) == 0 and len(suggestions) == 0:
            return 1.0
        
        # 问题权重更高
        issue_penalty = len(issues) * 0.2
        suggestion_penalty = len(suggestions) * 0.1
        
        score = max(0.0, 1.0 - issue_penalty - suggestion_penalty)
        return score


# ==================== 预定义的验证器 ====================

def validate_no_sensitive_data(output_data: Any, context: Optional[Dict] = None) -> OutputValidationResult:
    """
    验证输出是否包含敏感数据
    
    Args:
        output_data: 输出数据
        context: 上下文
        
    Returns:
        OutputValidationResult
    """
    import re
    
    issues = []
    
    output_str = str(output_data)
    
    # 检测敏感模式
    sensitive_patterns = {
        "API key": r'[A-Za-z0-9]{32,}',
        "Password": r'password["\s:=]+[^\s"]+',
        "Token": r'token["\s:=]+[^\s"]+',
    }
    
    for pattern_name, pattern in sensitive_patterns.items():
        if re.search(pattern, output_str, re.IGNORECASE):
            issues.append(f"Potential {pattern_name} in output")
    
    return OutputValidationResult(
        is_valid=len(issues) == 0,
        issues=issues
    )


def validate_completeness(output_data: Any, context: Optional[Dict] = None) -> OutputValidationResult:
    """
    验证输出的完整性
    
    Args:
        output_data: 输出数据
        context: 上下文（可包含期望的字段）
        
    Returns:
        OutputValidationResult
    """
    issues = []
    suggestions = []
    
    if isinstance(output_data, dict):
        # 检查必需字段
        expected_fields = context.get("required_fields", []) if context else []
        
        for field in expected_fields:
            if field not in output_data:
                issues.append(f"Missing required field: {field}")
            elif output_data[field] is None:
                issues.append(f"Required field is None: {field}")
    
    return OutputValidationResult(
        is_valid=len(issues) == 0,
        issues=issues,
        suggestions=suggestions
    )

    def validate_completeness(self, output_data: Any) -> Tuple[bool, List[str]]:
        """
        验证输出完整性
        
        Args:
            output_data: 输出数据
            
        Returns:
            (是否完整, 缺失字段列表)
            
        TODO: 实现完整性检查
        """
        raise NotImplementedError("待实现")
    
    def validate_quality(self, output_data: Any) -> Tuple[bool, float]:
        """
        验证输出质量
        
        Args:
            output_data: 输出数据
            
        Returns:
            (是否达标, 质量分数 0-1)
            
        TODO: 实现质量评估逻辑
        """
        raise NotImplementedError("待实现")
    
    def post_process(self, output_data: Any) -> Any:
        """
        后处理输出
        
        格式化、清理、优化输出
        
        Args:
            output_data: 原始输出
            
        Returns:
            处理后的输出
            
        TODO: 实现后处理逻辑
        """
        raise NotImplementedError("待实现")
    
    def format_output(
        self, 
        output_data: Any, 
        target_format: str
    ) -> Any:
        """
        格式化输出
        
        Args:
            output_data: 输出数据
            target_format: 目标格式
            
        Returns:
            格式化后的输出
            
        TODO: 实现格式转换
        """
        raise NotImplementedError("待实现")

