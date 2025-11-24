"""
Definition Loader

职责：
1. 加载 agent.md 和 context.md 文件
2. 调用 parser 解析文件内容
3. 调用 validator 验证解析结果
4. 返回 Pydantic 模型实例
5. 提供友好的错误信息

TODO:
- 实现 load_agent_definition() 函数
- 实现 load_context_definition() 函数
- 集成 parser 和 validator
- 处理文件不存在等异常情况
"""

from pathlib import Path
from typing import Union

from .parser import MarkdownParser
from .validator import SchemaValidator
from .schemas import AgentDefinition, ContextDefinition


class DefinitionLoader:
    """
    定义加载器
    
    负责加载、解析和验证 agent 和 context 定义
    """
    
    def __init__(self):
        """
        初始化加载器
        
        TODO: 初始化 parser 和 validator
        """
        self.parser = MarkdownParser()
        self.validator = SchemaValidator()
    
    def load_agent_definition(self, path: Union[str, Path]) -> AgentDefinition:
        """
        加载 agent.md 定义
        
        Args:
            path: agent.md 文件路径
            
        Returns:
            AgentDefinition 实例
            
        Raises:
            FileNotFoundError: 文件不存在
            ValidationError: 验证失败
            
        TODO: 实现加载逻辑
        """
        raise NotImplementedError("待实现")
    
    def load_context_definition(self, path: Union[str, Path]) -> ContextDefinition:
        """
        加载 context.md 定义
        
        Args:
            path: context.md 文件路径
            
        Returns:
            ContextDefinition 实例
            
        Raises:
            FileNotFoundError: 文件不存在
            ValidationError: 验证失败
            
        TODO: 实现加载逻辑
        """
        raise NotImplementedError("待实现")

