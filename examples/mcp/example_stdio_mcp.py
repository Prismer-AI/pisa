#!/usr/bin/env python3
"""
stdio MCP Server Example

演示如何使用 MCPServerStdio 来运行本地 MCP 服务器。

stdio MCP 特点：
- 作为本地子进程运行
- 通过 stdin/stdout 通信（JSON-RPC）
- SDK 自动管理进程生命周期
- 适合快速原型和本地工具集成

See: https://openai.github.io/openai-agents-python/mcp/#4-stdio-mcp-servers
"""

import asyncio
import sys
from pathlib import Path
from agents import Agent, Runner
from agents.mcp import MCPServerStdio, create_static_tool_filter


async def example_filesystem_mcp():
    """
    Filesystem MCP 示例
    
    使用 @modelcontextprotocol/server-filesystem 来访问本地文件系统。
    """
    print("=== Filesystem MCP Example ===\n")
    
    # 指定要访问的目录
    current_dir = Path(__file__).parent
    
    # 使用 async context manager 管理服务器生命周期
    async with MCPServerStdio(
        name="Filesystem Server",
        params={
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                str(current_dir)
            ],
        },
    ) as server:
        agent = Agent(
            name="File Assistant",
            instructions="Use the filesystem tools to answer questions about files.",
            mcp_servers=[server],
        )
        
        result = await Runner.run(
            agent,
            "List all Python files in the current directory"
        )
        
        print(f"Result: {result.final_output}\n")
        return result


async def example_custom_calculator_mcp():
    """
    自定义计算器 MCP 示例
    
    使用我们自己实现的计算器 MCP 服务器。
    """
    print("=== Custom Calculator MCP Example ===\n")
    
    # 计算器服务器脚本路径
    calculator_script = Path(__file__).parent / "calculator_mcp_server.py"
    
    if not calculator_script.exists():
        print(f"⚠️  Calculator server not found at: {calculator_script}")
        print("Skipping custom calculator example\n")
        return None
    
    async with MCPServerStdio(
        name="Calculator",
        params={
            "command": sys.executable,  # 使用当前 Python 解释器
            "args": [str(calculator_script)],
        },
    ) as server:
        agent = Agent(
            name="Math Assistant",
            instructions="Use the calculator tools to perform arithmetic operations.",
            mcp_servers=[server],
        )
        
        result = await Runner.run(agent, "Calculate: (15 + 27) * 3 - 10")
        print(f"Result: {result.final_output}\n")
        return result


async def example_mcp_with_tool_filter():
    """
    带工具过滤的 MCP 示例
    
    演示如何只暴露部分 MCP 工具给 agent。
    """
    print("=== MCP with Tool Filter Example ===\n")
    
    current_dir = Path(__file__).parent
    
    # 创建静态工具过滤器：只允许 read_file 和 list_directory
    tool_filter = create_static_tool_filter(
        allowed_tool_names=["read_file", "list_directory"]
    )
    
    async with MCPServerStdio(
        name="Filtered Filesystem Server",
        params={
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                str(current_dir)
            ],
        },
        tool_filter=tool_filter,  # 应用过滤器
    ) as server:
        agent = Agent(
            name="Read-Only File Assistant",
            instructions="You can only read and list files, not write or delete them.",
            mcp_servers=[server],
        )
        
        result = await Runner.run(
            agent,
            "Read the README.md file if it exists"
        )
        
        print(f"Result: {result.final_output}\n")
        return result


async def example_mcp_with_caching():
    """
    带缓存的 MCP 示例
    
    演示如何使用 tool list 缓存来提高性能。
    """
    print("=== MCP with Caching Example ===\n")
    
    current_dir = Path(__file__).parent
    
    async with MCPServerStdio(
        name="Cached Filesystem Server",
        params={
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                str(current_dir)
            ],
        },
        cache_tools_list=True,  # 启用工具列表缓存
    ) as server:
        agent = Agent(
            name="File Assistant",
            instructions="Use filesystem tools efficiently.",
            mcp_servers=[server],
        )
        
        # 第一次调用：会 list tools
        print("First run (will list tools):")
        result1 = await Runner.run(agent, "How many Python files are there?")
        print(f"Result: {result1.final_output}\n")
        
        # 第二次调用：使用缓存的 tools
        print("Second run (using cached tools):")
        result2 = await Runner.run(agent, "List all markdown files")
        print(f"Result: {result2.final_output}\n")
        
        # 可以手动清除缓存
        server.invalidate_tools_cache()
        print("Cache invalidated\n")
        
        return result1, result2


async def example_dynamic_tool_filter():
    """
    动态工具过滤示例
    
    演示如何使用自定义函数动态过滤工具。
    """
    print("=== Dynamic Tool Filter Example ===\n")
    
    from agents.mcp import ToolFilterContext
    
    async def context_aware_filter(context: ToolFilterContext, tool) -> bool:
        """
        根据上下文动态决定是否暴露工具
        
        示例规则：
        - 如果 agent 名字包含 "ReadOnly"，只允许读操作
        - 否则允许所有操作
        """
        if "ReadOnly" in context.agent.name:
            # 只允许读相关的工具
            read_tools = {"read_file", "list_directory", "get_file_info"}
            return tool.name in read_tools
        return True
    
    current_dir = Path(__file__).parent
    
    async with MCPServerStdio(
        name="Dynamic Filtered Server",
        params={
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                str(current_dir)
            ],
        },
        tool_filter=context_aware_filter,  # 使用动态过滤器
    ) as server:
        # 创建只读 agent
        readonly_agent = Agent(
            name="ReadOnly File Assistant",
            instructions="You can only read files.",
            mcp_servers=[server],
        )
        
        result = await Runner.run(
            readonly_agent,
            "List Python files and read the first one"
        )
        
        print(f"Result: {result.final_output}\n")
        return result


async def main():
    """运行所有 stdio MCP 示例"""
    print("🚀 stdio MCP Server Examples\n")
    print("These examples demonstrate using local MCP servers via stdin/stdout")
    print("See: https://openai.github.io/openai-agents-python/mcp/#4-stdio-mcp-servers\n")
    print("="*60 + "\n")
    
    try:
        # 1. Filesystem MCP
        await example_filesystem_mcp()
        
        # 2. 自定义计算器 MCP
        await example_custom_calculator_mcp()
        
        # 3. 工具过滤
        await example_mcp_with_tool_filter()
        
        # 4. 缓存
        await example_mcp_with_caching()
        
        # 5. 动态过滤
        await example_dynamic_tool_filter()
        
        print("✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

