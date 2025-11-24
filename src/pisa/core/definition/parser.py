"""
Definition Parser

解析 agent.md 文件，生成 AgentDefinition 对象。

支持的格式：
- YAML frontmatter + Markdown body
- 纯 YAML
"""

import yaml
import re
from typing import Dict, Any, Optional
from pathlib import Path

from .models import (
    AgentDefinition,
    AgentMetadata,
    # AgentLoopType,  # 已移除 - loop_type 现在是字符串
    CapabilityReference,
    ModelConfig,
    PlanningConfig,
    ValidationRule,
    ContextConfig,
    ObservabilityConfig,
    RuntimeConfig,
)


class AgentDefinitionParser:
    """
    Agent 定义解析器
    
    解析 agent.md 文件，生成 AgentDefinition 对象。
    """
    
    def __init__(self):
        pass
    
    def parse_file(self, file_path: str) -> AgentDefinition:
        """
        解析文件
        
        Args:
            file_path: agent.md 文件路径
            
        Returns:
            AgentDefinition 对象
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = path.read_text(encoding="utf-8")
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> AgentDefinition:
        """
        解析内容
        
        Args:
            content: agent.md 内容
            
        Returns:
            AgentDefinition 对象
        """
        # 检测格式
        if content.strip().startswith("---"):
            # YAML frontmatter + Markdown
            return self._parse_frontmatter_format(content)
        else:
            # 纯 YAML
            return self._parse_yaml_format(content)
    
    def _parse_frontmatter_format(self, content: str) -> AgentDefinition:
        """
        解析 frontmatter 格式
        
        格式：
        ---
        YAML 配置
        ---
        Markdown 内容
        """
        # 提取 frontmatter
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
        if not match:
            raise ValueError("Invalid frontmatter format")
        
        yaml_content = match.group(1)
        markdown_content = match.group(2).strip()
        
        # 解析 YAML
        config = yaml.safe_load(yaml_content)
        
        # 解析 Markdown sections
        sections = self._parse_markdown_sections(markdown_content)
        
        # 合并配置
        return self._build_definition(config, sections)
    
    def _parse_yaml_format(self, content: str) -> AgentDefinition:
        """解析纯 YAML 格式"""
        config = yaml.safe_load(content)
        return self._build_definition(config, {})
    
    def _parse_markdown_sections(self, markdown: str) -> Dict[str, str]:
        """
        解析 Markdown sections
        
        支持的 sections:
        - # System Prompt
        - # Planning Instructions
        - # Replanning Instructions
        - # Background Info
        - # Validation Principle
        """
        sections = {}
        
        # 分割 sections
        current_section = None
        current_content = []
        
        for line in markdown.split('\n'):
            # 检查是否是 section 标题
            if line.startswith('# '):
                # 保存上一个 section
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # 开始新 section
                current_section = line[2:].strip().lower().replace(' ', '_')
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # 保存最后一个 section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def _build_definition(
        self,
        config: Dict[str, Any],
        sections: Dict[str, str]
    ) -> AgentDefinition:
        """
        构建 AgentDefinition
        
        Args:
            config: YAML 配置
            sections: Markdown sections
            
        Returns:
            AgentDefinition 对象
        """
        # 元信息 - 优先从 metadata 字段获取，其次从顶层
        metadata_config = config.get('metadata', {})
        metadata = AgentMetadata(
            name=metadata_config.get('name', config.get('name', 'Unnamed Agent')),
            version=metadata_config.get('version', config.get('version', '1.0.0')),
            description=metadata_config.get('description', config.get('description', '')),
            author=metadata_config.get('author', config.get('author')),
            tags=metadata_config.get('tags', config.get('tags', []))
        )
        
        # Loop 类型（不再硬编码验证，由 LoopRegistry 动态验证）
        loop_type = config.get('loop_type', 'plan_execute')
        
        # 系统提示词
        system_prompt = (
            sections.get('system_prompt') or 
            config.get('system_prompt') or 
            "You are a helpful assistant."
        )
        
        # Capabilities
        capabilities = []
        for cap in config.get('capabilities', []):
            if isinstance(cap, str):
                capabilities.append(CapabilityReference(name=cap))
            elif isinstance(cap, dict):
                capabilities.append(CapabilityReference(**cap))
        
        # 模型配置
        model_cfg = config.get('model', {})
        if isinstance(model_cfg, str):
            models = ModelConfig(default_model=model_cfg)
        else:
            models = ModelConfig(**model_cfg)
        
        # 规划配置
        planning_config = None
        if 'planning' in config:
            planning_data = config['planning'].copy()
            # 添加 instructions
            if 'planning_instructions' in sections:
                planning_data['planning_instructions'] = sections['planning_instructions']
            if 'replanning_instructions' in sections:
                planning_data['replanning_instructions'] = sections['replanning_instructions']
            planning_config = PlanningConfig(**planning_data)
        
        # 验证规则
        validation_rules = []
        for rule in config.get('validation_rules', []):
            if isinstance(rule, dict):
                validation_rules.append(ValidationRule(**rule))
        
        # Context 配置
        context_cfg = config.get('context', {})
        context_config = ContextConfig(**context_cfg)
        
        # 可观测性配置
        obs_cfg = config.get('observability', {})
        observability_config = ObservabilityConfig(**obs_cfg)
        
        # 运行时配置
        runtime_cfg = config.get('runtime', {})
        runtime_config = RuntimeConfig(**runtime_cfg)
        
        # 背景信息
        background_info = sections.get('background_info') or config.get('background_info')
        
        # 额外配置
        extra_config = config.get('extra_config', {})
        
        return AgentDefinition(
            metadata=metadata,
            loop_type=loop_type,
            system_prompt=system_prompt,
            capabilities=capabilities,
            models=models,
            planning_config=planning_config,
            validation_rules=validation_rules,
            context_config=context_config,
            observability_config=observability_config,
            runtime_config=runtime_config,
            background_info=background_info,
            extra_config=extra_config
        )


# 便捷函数
def parse_agent_definition(file_path: str) -> AgentDefinition:
    """
    解析 agent.md 文件
    
    Args:
        file_path: agent.md 文件路径
        
    Returns:
        AgentDefinition 对象
    """
    parser = AgentDefinitionParser()
    return parser.parse_file(file_path)

class MarkdownParser:
    def parse(self, content: str) -> dict:
        """Convert Markdown capability definitions into structured data."""
        raise NotImplementedError("Markdown parsing is defined in v2 roadmap")
