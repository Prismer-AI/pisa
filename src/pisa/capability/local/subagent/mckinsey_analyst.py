"""
McKinsey-Style Content Analysis Agent

Specialized for McKinsey-style content analysis and generation:
- Structured thinking (MECE principle)
- Pyramid principle
- Data-driven analysis
- Clear visualization recommendations
"""

from typing import Dict, Any, Optional
import json

from pisa.capability import capability
from pisa.config import Config


@capability(
    name="mckinsey_analysis",
    description="Perform McKinsey-style content analysis and generation, applying MECE principles and Pyramid principle",
    capability_type="function",
    tags=["subagent", "analysis", "mckinsey", "consulting"],
    strict_mode=False
)
async def mckinsey_analysis(
    content: str,
    analysis_type: str = "general",
    output_format: str = "structured"
) -> Dict[str, Any]:
    """
    Analyze content using McKinsey-style approach
    
    Args:
        content: Content to be analyzed
        analysis_type: Type of analysis (general, problem_solving, market_analysis, strategic)
        output_format: Output format (structured, narrative, executive_summary)
    
    Returns:
        Dictionary containing analysis results
    """
    try:
        from openai_agents import Agent, Runner
    except ImportError:
        # Fallback to development import
        try:
            from agents import Agent, Runner
        except ImportError:
            return {
                "success": False,
                "error": "OpenAI Agent SDK not installed",
                "message": "Please install openai-agents: pip install openai-agents"
            }
    
    # Ensure SDK is configured
    Config.setup_agent_sdk()
    
    # Build different system prompts based on analysis type
    analysis_prompts = {
        "general": """You are a McKinsey consultant specialized in structured analysis.

Your approach follows:
1. **MECE Principle** (Mutually Exclusive, Collectively Exhaustive)
2. **Pyramid Principle** (Answer first, then supporting arguments)
3. **Data-Driven** insights
4. **Clear recommendations**

Analyze the provided content and structure your response hierarchically.""",

        "problem_solving": """You are a McKinsey consultant specialized in problem-solving.

Apply the McKinsey Problem-Solving approach:
1. **Define the problem** clearly and specifically
2. **Disaggregate** into component parts (MECE)
3. **Prioritize** issues based on impact and feasibility
4. **Work plan** development
5. **Analysis** and hypothesis testing
6. **Synthesis** into recommendations

Structure your response using the Pyramid Principle.""",

        "market_analysis": """You are a McKinsey consultant specialized in market analysis.

Conduct a structured market analysis:
1. **Market Sizing** and segmentation
2. **Competitive Landscape** (Porter's 5 Forces if relevant)
3. **Customer Insights** and needs
4. **Trends and Drivers**
5. **Opportunities and Threats**
6. **Strategic Recommendations**

Use data-driven insights and MECE structuring.""",

        "strategic": """You are a McKinsey consultant specialized in strategy.

Provide strategic analysis:
1. **Current Situation** assessment
2. **Strategic Options** (MECE framework)
3. **Evaluation Criteria** and trade-offs
4. **Recommended Strategy**
5. **Implementation Roadmap**
6. **Key Risks and Mitigations**

Apply Pyramid Principle in structuring your response."""
    }
    
    system_prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])
    
    # Adjust instructions based on output format
    format_instructions = {
        "structured": "\n\nFormat your response as:\n- Executive Summary (3-5 bullets)\n- Key Findings (structured by theme)\n- Recommendations (prioritized)\n- Next Steps",
        "narrative": "\n\nFormat your response as a cohesive narrative with clear sections and transitions.",
        "executive_summary": "\n\nProvide only an executive summary: situation, complication, resolution, and next steps (max 200 words)."
    }
    
    system_prompt += format_instructions.get(output_format, format_instructions["structured"])
    
    # Create McKinsey Analyst Agent
    agent = Agent(
        name="McKinseyAnalyst",
        instructions=system_prompt,
        model=Config.agent_default_model
    )
    
    # Build analysis request
    user_prompt = f"""Please analyze the following content:

{content}

Analysis Type: {analysis_type}
Output Format: {output_format}

Provide your McKinsey-style analysis."""
    
    try:
        # Run analysis
        result = await Runner.run(
            starting_agent=agent,
            input=user_prompt
        )
        
        return {
            "success": True,
            "analysis_type": analysis_type,
            "output_format": output_format,
            "analysis": result.final_output,
            "metadata": {
                "model": Config.agent_default_model,
                "content_length": len(content),
                "approach": "McKinsey structured analysis"
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": "Analysis failed",
            "message": str(e),
            "analysis": None
        }


@capability(
    name="mckinsey_mece_breakdown",
    description="Break down problems or topics using MECE principle",
    capability_type="function",
    tags=["subagent", "mece", "problem-solving", "mckinsey"],
    strict_mode=False
)
async def mckinsey_mece_breakdown(
    topic: str,
    depth: int = 2,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Break down topics using MECE principle
    
    Args:
        topic: Topic or problem to break down
        depth: Depth of breakdown levels
        context: Optional contextual information
    
    Returns:
        MECE breakdown results
    """
    try:
        from openai_agents import Agent, Runner
    except ImportError:
        try:
            from agents import Agent, Runner
        except ImportError:
            return {
                "success": False,
                "error": "OpenAI Agent SDK not installed",
                "message": "Please install openai-agents: pip install openai-agents"
            }
    
    Config.setup_agent_sdk()
    
    system_prompt = """You are a McKinsey consultant expert in MECE (Mutually Exclusive, Collectively Exhaustive) structuring.

Your task is to break down topics/problems into MECE components.

Guidelines:
1. **Mutually Exclusive**: No overlap between categories
2. **Collectively Exhaustive**: Cover all possibilities
3. **Clarity**: Use clear, actionable labels
4. **Hierarchy**: Create logical levels

Output Format:
- Level 1: Main MECE categories
- Level 2: Sub-categories (if depth > 1)
- For each: Brief description and key considerations"""
    
    agent = Agent(
        name="MECEAnalyst",
        instructions=system_prompt,
        model=Config.agent_default_model
    )
    
    user_prompt = f"""Break down the following topic using MECE principle:

Topic: {topic}
Depth: {depth} levels
"""
    
    if context:
        user_prompt += f"\nContext: {context}"
    
    user_prompt += "\n\nProvide a MECE breakdown with clear categorization."
    
    try:
        result = await Runner.run(
            starting_agent=agent,
            input=user_prompt
        )
        
        return {
            "success": True,
            "topic": topic,
            "depth": depth,
            "mece_breakdown": result.final_output,
            "metadata": {
                "principle": "MECE (Mutually Exclusive, Collectively Exhaustive)",
                "model": Config.agent_default_model
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": "MECE breakdown failed",
            "message": str(e)
        }

