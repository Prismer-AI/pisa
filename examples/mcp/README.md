# MCP (Model Context Protocol) Examples

本目录包含使用 **OpenAI Agents SDK** 集成 MCP 服务器的示例代码。

## 📚 什么是 MCP？

MCP (Model Context Protocol) 是一个开放协议，标准化了应用程序如何向 LLM 提供工具和上下文。可以把 MCP 想象成 AI 应用的 USB-C 接口。

详细文档：https://openai.github.io/openai-agents-python/mcp/

## 🎯 MCP 类型

根据 [OpenAI Agent SDK 文档](https://openai.github.io/openai-agents-python/mcp/)，支持以下 MCP 类型：

| MCP 类型 | 使用场景 | 实现类 |
|---------|---------|-------|
| **Hosted MCP** | OpenAI 托管的公开可访问的 MCP 服务器 | `HostedMCPTool` |
| **stdio MCP** | 本地子进程，通过 stdin/stdout 通信 | `MCPServerStdio` |
| **Streamable HTTP** | 本地或远程 HTTP 流式服务器 | `MCPServerStreamableHttp` |
| **HTTP with SSE** | 服务器发送事件（SSE）的 HTTP 服务器 | `MCPServerSse` |

## 📂 示例文件

### 1. Hosted MCP Tool 示例

```
example_hosted_mcp.py       # 使用 OpenAI 托管的 MCP 服务器
```

**特点**：
- 工具调用在 OpenAI 基础设施中执行
- 无需管理服务器生命周期
- 支持 approval flows
- 支持 OpenAI connectors

### 2. stdio MCP 示例

```
example_stdio_mcp.py        # 使用本地 MCP 服务器（npx）
calculator_mcp_server.py    # 自定义计算器 MCP 服务器
```

**特点**：
- 作为子进程运行
- 通过 stdin/stdout 通信
- 自动管理进程生命周期
- 适合快速原型和本地工具

### 3. HTTP MCP 示例（TODO）

```
example_http_mcp.py         # Streamable HTTP MCP 示例
example_sse_mcp.py          # SSE MCP 示例
```

## 🚀 快速开始

### 安装依赖

```bash
uv pip install openai-agents
```

### 运行 Hosted MCP 示例

```bash
cd examples/mcp
uv run python example_hosted_mcp.py
```

### 运行 stdio MCP 示例

```bash
cd examples/mcp
uv run python example_stdio_mcp.py
```

### 运行自定义计算器 MCP

```bash
cd examples/mcp
uv run python calculator_mcp_server.py
```

## 📝 代码示例

### Hosted MCP Tool

```python
from agents import Agent, HostedMCPTool, Runner
import asyncio

async def main():
    agent = Agent(
        name="Assistant",
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
    
    result = await Runner.run(agent, "Which language is this repository written in?")
    print(result.final_output)

asyncio.run(main())
```

### stdio MCP Server

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from pathlib import Path
import asyncio

async def main():
    current_dir = Path(__file__).parent
    
    # 使用 async context manager 管理服务器生命周期
    async with MCPServerStdio(
        name="Filesystem Server",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", str(current_dir)],
        },
    ) as server:
        agent = Agent(
            name="Assistant",
            instructions="Use the files to answer questions.",
            mcp_servers=[server],  # 注意：server 在 context manager 内有效
        )
        
        result = await Runner.run(agent, "List the files available.")
        print(result.final_output)

asyncio.run(main())
```

## ⚠️ 重要注意事项

### 1. Async Context Manager

**所有 MCP servers 必须在 async context manager 中使用**：

```python
async with MCPServerStdio(...) as server:
    # server 只在这个 block 内有效
    agent = Agent(mcp_servers=[server])
    result = await Runner.run(agent, "...")
# server 在这里已经关闭
```

### 2. PISA Capability 集成

**当前状态**：PISA 的 capability 系统**尚未完全支持** MCP servers，因为：

- ❌ Capability 系统直接传递 MCP server 实例
- ❌ 没有管理 async context manager 生命周期
- ❌ Loop 需要修改来支持 `async with` 语法

**未来计划**：修改 `BaseAgentLoop` 来正确管理 MCP 生命周期。

### 3. 当前推荐做法

在自定义代码中直接使用 MCP：

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async def my_custom_agent():
    async with MCPServerStdio(...) as server:
        agent = Agent(mcp_servers=[server])
        return await Runner.run(agent, "...")
```

## 🧪 测试

运行 MCP 示例测试：

```bash
uv run pytest tests/examples/test_mcp_examples.py -v
```

## 📖 更多资源

- [OpenAI MCP 文档](https://openai.github.io/openai-agents-python/mcp/)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [OpenAI Agents SDK API Reference](https://openai.github.io/openai-agents-python/ref/mcp/server/)

## 🔮 未来改进

1. ✅ 实现所有 MCP 类型的示例
2. ✅ 添加完整的单元测试
3. ⏳ 修改 PISA Loop 支持 MCP 生命周期管理
4. ⏳ 创建 MCP capability 注册机制
5. ⏳ 添加 MCP tool filtering 示例

