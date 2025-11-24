# PISA MCP Integration 集成指南

## 📋 当前状态

### ✅ 已完成

1. **MCP 示例代码**（`examples/mcp/`）
   - ✅ Hosted MCP 示例（`example_hosted_mcp.py`）
   - ✅ stdio MCP 示例（`example_stdio_mcp.py`）
   - ✅ 自定义计算器 MCP 服务器（`calculator_mcp_server.py`）
   - ✅ README 文档

2. **单元测试**（`tests/examples/test_mcp_examples.py`）
   - ✅ **12个测试通过**
   - ✅ 计算器 MCP 服务器协议测试
   - ✅ 文件存在性和可执行性测试
   - ✅ 导入测试

3. **文档**
   - ✅ 详细的 README（`examples/mcp/README.md`）
   - ✅ 代码注释和 docstrings
   - ✅ 符合 [OpenAI MCP 文档](https://openai.github.io/openai-agents-python/mcp/)

### ❌ 待完成

**核心问题**：PISA 的 `capability` 系统和 MCP 的生命周期管理**不兼容**

#### 问题分析

根据 [OpenAI MCP 文档](https://openai.github.io/openai-agents-python/mcp/)，MCP服务器必须在 `async context manager` 中使用：

```python
# ✅ 正确用法
async with MCPServerStdio(...) as server:
    agent = Agent(mcp_servers=[server])
    result = await Runner.run(agent, "...")
# server 在这里自动关闭
```

但是 PISA 当前的架构：

```python
# ❌ PISA 当前实现
@capability(capability_type="mcp", name="my_mcp")
def create_mcp_server():
    return MCPServerStdio(...)  # 直接返回，没有context manager

# 在Loop中
self.mcp_servers = [...]  # 直接传递实例
agent = Agent(mcp_servers=self.mcp_servers)  # ❌ 服务器未启动！
```

**问题**：
1. ❌ MCP 服务器没有通过 `async with` 启动
2. ❌ 服务器生命周期未管理（不会自动关闭）
3. ❌ 可能导致资源泄漏（进程、连接未释放）

---

## 🔧 解决方案：修改 Loop 系统

### 方案概述

需要修改 `BaseAgentLoop` 来正确管理 MCP 服务器的生命周期。

### 实现步骤

#### 1. 修改 `BaseAgentLoop.__init__`

添加 MCP 服务器的 context 管理：

```python
class BaseAgentLoop(IAgentLoop):
    def __init__(self, definition, config, **kwargs):
        # ... 现有代码 ...
        
        self.mcp_servers = []  # MCP Server 实例列表
        self._mcp_contexts = []  # 用于存储 context manager
        self._active_mcp_servers = []  # 启动后的 server
```

#### 2. 添加 MCP 服务器启动方法

```python
async def _start_mcp_servers(self):
    """启动所有 MCP 服务器"""
    for mcp_server in self.mcp_servers:
        try:
            # 进入 context manager
            ctx = mcp_server.__aenter__()
            active_server = await ctx
            
            self._mcp_contexts.append((mcp_server, ctx))
            self._active_mcp_servers.append(active_server)
            
            _logger.debug(f"Started MCP server: {mcp_server.name}")
        except Exception as e:
            _logger.error(f"Failed to start MCP server {mcp_server.name}: {e}")
            raise
```

#### 3. 添加 MCP 服务器关闭方法

```python
async def _stop_mcp_servers(self):
    """关闭所有 MCP 服务器"""
    for mcp_server, ctx in self._mcp_contexts:
        try:
            await mcp_server.__aexit__(None, None, None)
            _logger.debug(f"Stopped MCP server: {mcp_server.name}")
        except Exception as e:
            _logger.error(f"Error stopping MCP server: {e}")
    
    self._mcp_contexts.clear()
    self._active_mcp_servers.clear()
```

#### 4. 修改 `run` 方法

```python
async def run(self, input_data: Any, **kwargs) -> LoopState:
    """运行 Agent Loop"""
    try:
        # 启动所有 MCP 服务器
        if self.mcp_servers:
            await self._start_mcp_servers()
        
        # 创建 Agent（使用启动后的服务器）
        agent = self.create_agent(
            name=self.config.name,
            instructions=self.config.instructions,
            mcp_servers=self._active_mcp_servers  # ← 使用已启动的服务器
        )
        
        # 运行 Agent
        result = await Runner.run(agent, input_data)
        
        # 更新状态
        self.state.update_from_result(result)
        
        return self.state
        
    finally:
        # 确保 MCP 服务器被关闭
        if self._mcp_contexts:
            await self._stop_mcp_servers()
```

#### 5. 修改 `create_agent` 方法

```python
def create_agent(self, name, instructions, model=None, include_tools=True, **kwargs):
    """创建 Agent（自动注入 capabilities）"""
    agent_kwargs = {}
    
    if include_tools:
        if self.tools:
            agent_kwargs['tools'] = self.tools
        
        if self.handoffs:
            agent_kwargs['handoffs'] = self.handoffs
        
        # ✅ 使用已启动的 MCP 服务器
        if self._active_mcp_servers:
            agent_kwargs['mcp_servers'] = self._active_mcp_servers
            _logger.debug(f"Injecting {len(self._active_mcp_servers)} active mcp_servers")
    
    agent_kwargs.update(kwargs)
    
    return Agent(
        name=name,
        instructions=instructions,
        model=model or self.config.model,
        **agent_kwargs
    )
```

### 修改后的文件

需要修改的文件：
- `src/pisa/core/loop/base.py` - 主要修改
- `src/pisa/core/loop/templates/plan_execute.py` - 如果有自定义 run 逻辑

### 测试计划

1. **单元测试**
   ```python
   async def test_mcp_server_lifecycle():
       """测试 MCP 服务器生命周期管理"""
       loop = BaseAgentLoop(...)
       
       # 添加 MCP 服务器
       mcp_server = MCPServerStdio(...)
       loop.mcp_servers = [mcp_server]
       
       # 运行 loop
       result = await loop.run("test input")
       
       # 验证服务器被正确启动和关闭
       assert len(loop._active_mcp_servers) == 0  # 已清理
   ```

2. **集成测试**
   ```python
   async def test_mcp_integration_with_calculator():
       """测试计算器 MCP 集成"""
       from examples.mcp.calculator_mcp_server import CalculatorMCPServer
       
       mcp_server = MCPServerStdio(
           name="calculator",
           params={"command": "python", "args": ["calculator_mcp_server.py"]}
       )
       
       loop = create_loop_with_mcp(mcp_server)
       result = await loop.run("Calculate 5 + 3")
       
       assert "8" in result.final_output
   ```

---

## 📝 使用示例

### 修改后的使用方式

```python
from pisa.core.loop import BaseAgentLoop
from agents.mcp import MCPServerStdio
from pathlib import Path

# 1. 创建 Loop
loop = BaseAgentLoop(definition=my_agent_definition)

# 2. 添加 MCP 服务器（未启动）
calculator_server = MCPServerStdio(
    name="calculator",
    params={
        "command": "python",
        "args": [str(Path("calculator_mcp_server.py"))]
    }
)

loop.mcp_servers = [calculator_server]

# 3. 运行 Loop（自动管理 MCP 生命周期）
async def main():
    result = await loop.run("Calculate: (10 + 5) * 2")
    print(result.final_output)

# MCP 服务器在 loop.run() 结束后自动关闭
```

### 与 capability 系统集成（未来）

```python
# 未来可能的 API
@capability(
    capability_type="mcp",
    name="calculator_mcp",
    description="Calculator MCP server"
)
def create_calculator_mcp():
    """返回未启动的 MCP 服务器"""
    return MCPServerStdio(
        name="calculator",
        params={"command": "python", "args": ["calculator_mcp_server.py"]}
    )

# Loop 会自动：
# 1. 从 capability 获取 MCP 服务器实例
# 2. 在 run() 时启动服务器
# 3. 在结束时关闭服务器
```

---

## ⚠️ 注意事项

### 1. MCP 服务器不是 Function

MCP 服务器不应该像 function capabilities 那样直接调用。它们是：
- 独立的进程或服务
- 需要生命周期管理
- 通过 Agent SDK 自动调用其工具

### 2. Context Manager 是必需的

**所有** MCP 服务器类型都需要 context manager：
- `MCPServerStdio` ✅
- `MCPServerStreamableHttp` ✅
- `MCPServerSse` ✅
- `HostedMCPTool` ❌ (不需要，OpenAI 管理)

### 3. 错误处理

确保即使在异常情况下也能关闭 MCP 服务器：

```python
try:
    await self._start_mcp_servers()
    # ... 运行逻辑 ...
finally:
    await self._stop_mcp_servers()  # ← 确保清理
```

---

## 🎯 下一步行动

### 立即行动

1. ✅ 阅读 OpenAI MCP 文档
2. ✅ 实现示例代码
3. ✅ 通过单元测试

### 待实现

4. ⏳ 修改 `BaseAgentLoop` 类
5. ⏳ 添加 MCP 生命周期管理测试
6. ⏳ 更新 capability resolver 支持 MCP
7. ⏳ 文档更新和示例

### 可选改进

8. ⏳ HTTP MCP 示例（Streamable HTTP, SSE）
9. ⏳ MCP tool filtering 集成
10. ⏳ MCP prompts 支持

---

## 📚 参考资源

- [OpenAI MCP 文档](https://openai.github.io/openai-agents-python/mcp/)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [OpenAI Agents SDK API](https://openai.github.io/openai-agents-python/ref/mcp/server/)
- PISA MCP 示例：`examples/mcp/`
- PISA MCP 测试：`tests/examples/test_mcp_examples.py`

---

**总结**：MCP 示例和测试已完成 ✅，现在需要修改 Loop 系统来支持 MCP 服务器的生命周期管理 ⏳

