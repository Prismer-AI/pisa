"""
Text to Table Subagent Capability

使用OpenAI Agent SDK将文本内容转换为结构化表格
这是一个 Subagent，通过 Handoff 机制调用
"""

from typing import Dict, Any
import logging

from pisa.capability import capability
from pisa.config import Config
from agents import Agent

_logger = logging.getLogger(__name__)


def create_text_to_table_agent() -> Agent:
    """
    创建一个文本转表格的 Agent（用于 Handoff）
    
    Returns:
        Agent: 配置好的文本转表格 Agent
    """
    system_prompt = """You are a data extraction expert specialized in converting unstructured text into structured tables.

Your task is to analyze the given text and extract information into a well-formatted table.

**Guidelines**:
1. Identify key entities, attributes, and values in the text
2. Determine appropriate column headers
3. Extract or infer row data
4. Handle missing data gracefully (use "-" or "N/A")
5. Ensure consistency across rows

**Output Format**: MARKDOWN table

**Output Requirements**:
1. Return a valid markdown table
2. Include clear column headers
3. Ensure all rows have the same number of columns
4. Format numbers and text appropriately
5. Add a brief description before the table if helpful

Example Input: "Product A costs $10, weighs 2kg. Product B costs $15, weighs 3kg."

Example Output:
| Product | Price | Weight |
|---------|-------|--------|
| A       | $10   | 2kg    |
| B       | $15   | 3kg    |

Now process the user's input text and create a structured table."""

    # 确保Agent SDK已配置
    if not Config.has_agent_sdk():
        Config.setup_agent_sdk()
    
    agent = Agent(
        name="text_to_table",
        instructions=system_prompt,
        model=Config.agent_default_model or "openai/gpt-oss-120b"
    )
    
    return agent


@capability(
    name="text_to_table",
    description="使用AI将非结构化文本转换为结构化表格。通过 handoff 调用此 subagent，输入文本内容即可生成表格。",
    capability_type="agent",
    tags=["subagent", "text-processing", "table", "structured-data"],
    strict_mode=False
)
def text_to_table() -> Agent:
    """
    返回一个文本转表格的 Agent（用于 Handoff）
    
    这个 Agent 接收文本输入，将其转换为结构化的 markdown 表格。
    
    使用方式：通过 handoff 调用，Agent SDK 会自动处理输入输出。
    
    Returns:
        Agent: 配置好的文本转表格 Agent
    """
    return create_text_to_table_agent()
