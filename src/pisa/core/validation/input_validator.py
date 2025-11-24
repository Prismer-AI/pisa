"""
Input Validator

输入验证器，提供结构化的输入验证能力。
"""

import logging
from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field, ValidationError

_logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    """验证结果"""
    is_valid: bool = Field(description="是否通过验证")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class InputValidator:
    """
    输入验证器
    
    提供多层次的输入验证：
    1. 结构验证（Schema）
    2. 业务规则验证
    3. 安全验证
    """
    
    def __init__(self):
        """初始化输入验证器"""
        self.validators: List[callable] = []
        _logger.info("InputValidator initialized")
    
    def add_validator(self, validator: callable) -> None:
        """
        添加自定义验证器
        
        Args:
            validator: 验证函数，接收输入并返回 ValidationResult
        """
        self.validators.append(validator)
        _logger.debug(f"Added validator: {validator.__name__}")
    
    def validate(self, input_data: Any, schema: Optional[type[BaseModel]] = None) -> ValidationResult:
        """
        验证输入数据
        
        Args:
            input_data: 输入数据
            schema: 可选的 Pydantic schema
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        metadata = {}
        
        # 1. Schema 验证
        if schema:
            try:
                validated_data = schema.model_validate(input_data)
                metadata["validated_data"] = validated_data
            except ValidationError as e:
                errors.extend([f"Schema validation error: {err['msg']}" for err in e.errors()])
                _logger.warning(f"Schema validation failed: {e}")
        
        # 2. 基本验证
        basic_result = self._validate_basic(input_data)
        errors.extend(basic_result.errors)
        warnings.extend(basic_result.warnings)
        
        # 3. 自定义验证器
        for validator in self.validators:
            try:
                result = validator(input_data)
                if isinstance(result, ValidationResult):
                    errors.extend(result.errors)
                    warnings.extend(result.warnings)
                    metadata.update(result.metadata)
            except Exception as e:
                errors.append(f"Validator {validator.__name__} failed: {str(e)}")
                _logger.error(f"Custom validator failed: {e}", exc_info=True)
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    def _validate_basic(self, input_data: Any) -> ValidationResult:
        """
        基本验证
        
        Args:
            input_data: 输入数据
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        # 检查是否为空
        if input_data is None:
            errors.append("Input data is None")
        elif isinstance(input_data, str) and len(input_data.strip()) == 0:
            errors.append("Input string is empty")
        elif isinstance(input_data, (list, dict)) and len(input_data) == 0:
            warnings.append("Input collection is empty")
        
        # 检查字符串长度
        if isinstance(input_data, str):
            if len(input_data) > 100000:  # 100K 字符限制
                errors.append(f"Input string too long: {len(input_data)} characters")
            elif len(input_data) > 50000:
                warnings.append(f"Input string is very long: {len(input_data)} characters")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


# ==================== 预定义的验证器 ====================

def validate_no_injection(input_data: Any) -> ValidationResult:
    """
    验证是否包含注入攻击
    
    Args:
        input_data: 输入数据
        
    Returns:
        ValidationResult
    """
    errors = []
    warnings = []
    
    if isinstance(input_data, str):
        # 检测常见的注入模式
        injection_patterns = [
            "DROP TABLE",
            "DELETE FROM",
            "INSERT INTO",
            "UPDATE ",
            "EXEC(",
            "EXECUTE(",
            "<script",
            "javascript:",
            "onerror=",
            "onload=",
        ]
        
        input_upper = input_data.upper()
        for pattern in injection_patterns:
            if pattern.upper() in input_upper:
                errors.append(f"Potential injection detected: {pattern}")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_no_pii(input_data: Any) -> ValidationResult:
    """
    验证是否包含 PII（个人身份信息）
    
    Args:
        input_data: 输入数据
        
    Returns:
        ValidationResult
    """
    import re
    
    warnings = []
    
    if isinstance(input_data, str):
        # 检测常见的 PII 模式
        patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        }
        
        for pii_type, pattern in patterns.items():
            if re.search(pattern, input_data):
                warnings.append(f"Potential {pii_type} detected in input")
    
    return ValidationResult(
        is_valid=True,  # 只警告，不阻止
        errors=[],
        warnings=warnings
    )
