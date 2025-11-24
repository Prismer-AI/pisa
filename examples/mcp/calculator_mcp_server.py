#!/usr/bin/env python3
"""
Simple Calculator MCP Server

一个符合 MCP 协议的简单计算器服务器，通过 stdio 通信。

MCP Protocol:
- JSON-RPC 2.0 over stdin/stdout
- Methods: initialize, tools/list, tools/call
- Protocol version: 2024-11-05

See: https://modelcontextprotocol.io/
"""

import sys
import json
import asyncio
from typing import Any, Dict


class CalculatorMCPServer:
    """计算器 MCP 服务器实现"""
    
    def __init__(self):
        self.server_info = {
            "name": "calculator-server",
            "version": "1.0.0"
        }
        self.capabilities = {
            "tools": {}
        }
    
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 initialize 请求"""
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": self.server_info,
            "capabilities": self.capabilities
        }
    
    async def handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出可用工具"""
        tools = [
            {
                "name": "add",
                "description": "Add two numbers together",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["a", "b"]
                }
            },
            {
                "name": "subtract",
                "description": "Subtract second number from first",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["a", "b"]
                }
            },
            {
                "name": "multiply",
                "description": "Multiply two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["a", "b"]
                }
            },
            {
                "name": "divide",
                "description": "Divide first number by second",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "Numerator"},
                        "b": {"type": "number", "description": "Denominator"}
                    },
                    "required": ["a", "b"]
                }
            }
        ]
        return {"tools": tools}
    
    async def handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            if tool_name == "add":
                result = arguments["a"] + arguments["b"]
            elif tool_name == "subtract":
                result = arguments["a"] - arguments["b"]
            elif tool_name == "multiply":
                result = arguments["a"] * arguments["b"]
            elif tool_name == "divide":
                if arguments["b"] == 0:
                    return {
                        "content": [{"type": "text", "text": "Error: Division by zero"}],
                        "isError": True
                    }
                result = arguments["a"] / arguments["b"]
            else:
                return {
                    "content": [{"type": "text", "text": f"Error: Unknown tool '{tool_name}'"}],
                    "isError": True
                }
            
            return {
                "content": [{"type": "text", "text": str(result)}]
            }
        
        except KeyError as e:
            return {
                "content": [{"type": "text", "text": f"Error: Missing argument {e}"}],
                "isError": True
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True
            }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """路由请求到相应的处理函数"""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "initialize":
            result = await self.handle_initialize(params)
        elif method == "tools/list":
            result = await self.handle_list_tools(params)
        elif method == "tools/call":
            result = await self.handle_call_tool(params)
        else:
            return {
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
        
        return {"result": result}
    
    async def run(self):
        """主服务器循环 - 从 stdin 读取，向 stdout 写入"""
        loop = asyncio.get_event_loop()
        
        # 将 stderr 重定向到文件，避免污染 stdout
        sys.stderr = open("/tmp/calculator_mcp_server.log", "w")
        
        while True:
            try:
                # 从 stdin 读取一行
                line = await loop.run_in_executor(None, sys.stdin.readline)
                
                if not line:
                    # EOF reached
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # 解析 JSON-RPC 请求
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        }
                    }
                    print(json.dumps(response), flush=True)
                    continue
                
                # 处理请求
                response_data = await self.handle_request(request)
                
                # 构建 JSON-RPC 响应
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id")
                }
                response.update(response_data)
                
                # 写入 stdout
                print(json.dumps(response), flush=True)
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                # 错误日志到 stderr
                print(f"Server error: {e}", file=sys.stderr, flush=True)


async def main():
    """服务器入口点"""
    server = CalculatorMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())

