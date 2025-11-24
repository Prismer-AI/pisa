#!/usr/bin/env python3
"""
Hosted MCP Tool Example

演示如何使用 HostedMCPTool 来访问 OpenAI 托管的 MCP 服务器。

Hosted MCP 特点：
- 工具调用在 OpenAI 基础设施中执行
- 无需管理服务器生命周期
- 支持公开可访问的 MCP 服务器
- 支持 approval flows
- 支持 OpenAI connectors

See: https://openai.github.io/openai-agents-python/mcp/#1-hosted-mcp-server-tools
"""

import asyncio
import os
from agents import Agent, HostedMCPTool, Runner


async def example_basic_hosted_mcp():
    """
    基础 Hosted MCP 示例
    
    使用 gitmcp.io 的公开 MCP 服务器来查询 GitHub 仓库信息。
    """
    print("=== Basic Hosted MCP Example ===\n")
    
    agent = Agent(
        name="GitHub Assistant",
        tools=[
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "gitmcp",
                    "server_url": "https://gitmcp.io/openai/codex",
                    "require_approval": "never",
                }
            )
        ],
    )
    
    result = await Runner.run(
        agent,
        "Which language is the main language used in this repository?"
    )
    
    print(f"Result: {result.final_output}\n")
    return result


async def example_hosted_mcp_with_approval():
    """
    带审批流程的 Hosted MCP 示例
    
    演示如何在执行工具前要求审批。
    """
    print("=== Hosted MCP with Approval Example ===\n")
    
    from agents import MCPToolApprovalFunctionResult, MCPToolApprovalRequest
    
    # 定义安全的工具列表
    SAFE_TOOLS = {"read_project_metadata", "list_files"}
    
    def approve_tool(request: MCPToolApprovalRequest) -> MCPToolApprovalFunctionResult:
        """审批回调函数"""
        tool_name = request.data.name
        print(f"Approval requested for tool: {tool_name}")
        
        if tool_name in SAFE_TOOLS:
            print(f"✅ Approved: {tool_name}")
            return {"approve": True}
        else:
            print(f"❌ Denied: {tool_name}")
            return {
                "approve": False,
                "reason": f"Tool '{tool_name}' requires manual review"
            }
    
    agent = Agent(
        name="Secure GitHub Assistant",
        tools=[
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "gitmcp",
                    "server_url": "https://gitmcp.io/openai/codex",
                    "require_approval": "always",  # 总是需要审批
                },
                on_approval_request=approve_tool,
            )
        ],
    )
    
    result = await Runner.run(agent, "List the files in this repository")
    print(f"Result: {result.final_output}\n")
    return result


async def example_hosted_mcp_streaming():
    """
    流式 Hosted MCP 示例
    
    演示如何流式接收 MCP 工具的输出。
    """
    print("=== Hosted MCP Streaming Example ===\n")
    
    agent = Agent(
        name="GitHub Assistant",
        tools=[
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "gitmcp",
                    "server_url": "https://gitmcp.io/openai/codex",
                    "require_approval": "never",
                }
            )
        ],
    )
    
    print("Streaming results:\n")
    result = Runner.run_streamed(
        agent,
        "Summarize the top 3 programming languages used in this repository"
    )
    
    async for event in result.stream_events():
        if event.type == "run_item_stream_event":
            print(f"Stream event: {event.item}")
    
    print(f"\nFinal output: {result.final_output}\n")
    return result


async def example_hosted_mcp_connector():
    """
    Connector-backed Hosted MCP 示例
    
    演示如何使用 OpenAI Connectors（如 Google Calendar）。
    
    Note: 需要有效的 connector authorization token
    """
    print("=== Hosted MCP Connector Example ===\n")
    
    # 检查是否有 connector authorization
    auth_token = os.environ.get("GOOGLE_CALENDAR_AUTHORIZATION")
    
    if not auth_token:
        print("⚠️  GOOGLE_CALENDAR_AUTHORIZATION not set, skipping connector example")
        print("To use connectors, set up OAuth and get an authorization token\n")
        return None
    
    agent = Agent(
        name="Calendar Assistant",
        tools=[
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "google_calendar",
                    "connector_id": "connector_googlecalendar",
                    "authorization": auth_token,
                    "require_approval": "never",
                }
            )
        ],
    )
    
    result = await Runner.run(agent, "What events do I have today?")
    print(f"Result: {result.final_output}\n")
    return result


async def main():
    """运行所有 Hosted MCP 示例"""
    print("🚀 Hosted MCP Tool Examples\n")
    print("These examples demonstrate using OpenAI-hosted MCP servers")
    print("See: https://openai.github.io/openai-agents-python/mcp/#1-hosted-mcp-server-tools\n")
    print("="*60 + "\n")
    
    try:
        # 1. 基础示例
        await example_basic_hosted_mcp()
        
        # 2. 带审批的示例
        await example_hosted_mcp_with_approval()
        
        # 3. 流式示例
        await example_hosted_mcp_streaming()
        
        # 4. Connector 示例（可选）
        await example_hosted_mcp_connector()
        
        print("✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

