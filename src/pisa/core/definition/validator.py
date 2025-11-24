"""
Schema Validator

职责：
1. 验证解析后的 agent.md 是否符合 schema 定义
2. 检查必填字段和字段类型
3. 验证 capability 引用是否有效
4. 验证 context 配置是否合法
5. 提供详细的验证错误信息

TODO:
- 实现 validate_agent_definition() 函数
- 实现 validate_context_definition() 函数
- 实现 validate_capability_references() 函数
- 集成 Pydantic 进行类型验证
"""

from typing import Dict, Any, List


class ValidationError(Exception):
    """验证错误异常"""
    pass


class SchemaValidator:
    """
    Schema 验证器
    
    验证 agent.md 和 context.md 的定义是否符合规范
    """
    
    def __init__(self):
        """
        初始化验证器
        
        TODO: 加载 schema 定义
        """
        pass
    
    def validate_agent_definition(self, definition: Dict[str, Any]) -> List[str]:
        """
        验证 agent 定义
        
        Args:
            definition: 解析后的 agent 定义
            
        Returns:
            验证错误列表，空列表表示验证通过
            
        TODO: 实现验证逻辑
        """
        raise NotImplementedError("待实现")
    
    def validate_context_definition(self, definition: Dict[str, Any]) -> List[str]:
        """
        验证 context 定义
        
        Args:
            definition: 解析后的 context 定义
            
        Returns:
            验证错误列表，空列表表示验证通过
            
        TODO: 实现验证逻辑
        """
        raise NotImplementedError("待实现")
    
    def validate_capability_references(self, capabilities: List[str]) -> List[str]:
        """
        验证 capability 引用是否存在
        
        Args:
            capabilities: capability 名称列表
            
        Returns:
            无效的 capability 名称列表
            
        TODO: 实现验证逻辑，需要查询 CapabilityRegistry
        """
        raise NotImplementedError("待实现")

