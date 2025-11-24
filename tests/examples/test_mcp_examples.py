"""
MCP Examples Tests

测试 MCP 示例代码的功能性。

Note: 这些测试需要：
1. openai-agents 已安装
2. 有效的 OpenAI API key
3. npx 可用（用于运行 npm 包）
"""

import pytest
import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

# 添加 examples 目录到 path
examples_dir = Path(__file__).parent.parent.parent / "examples" / "mcp"
sys.path.insert(0, str(examples_dir))


class TestHostedMCPExamples:
    """测试 Hosted MCP 示例"""
    
    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_basic_hosted_mcp(self):
        """测试基础 Hosted MCP 示例（需要 --run-live）"""
        pytest.skip("Requires --run-live flag and valid API key")
        from example_hosted_mcp import example_basic_hosted_mcp
        
        result = await example_basic_hosted_mcp()
        assert result is not None
        assert result.final_output is not None
    
    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_hosted_mcp_with_approval(self):
        """测试带审批的 Hosted MCP 示例（需要 --run-live）"""
        pytest.skip("Requires --run-live flag")
        from example_hosted_mcp import example_hosted_mcp_with_approval
        
        result = await example_hosted_mcp_with_approval()
        assert result is not None
    
    def test_hosted_mcp_imports(self):
        """测试示例文件可以正确导入"""
        try:
            import example_hosted_mcp
            assert hasattr(example_hosted_mcp, 'example_basic_hosted_mcp')
            assert hasattr(example_hosted_mcp, 'example_hosted_mcp_with_approval')
            assert hasattr(example_hosted_mcp, 'example_hosted_mcp_streaming')
            assert hasattr(example_hosted_mcp, 'example_hosted_mcp_connector')
        except ImportError as e:
            pytest.skip(f"Cannot import example_hosted_mcp: {e}")


class TestStdioMCPExamples:
    """测试 stdio MCP 示例"""
    
    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_filesystem_mcp(self):
        """测试 Filesystem MCP 示例（需要 --run-live）"""
        pytest.skip("Requires --run-live flag and npx")
        from example_stdio_mcp import example_filesystem_mcp
        
        result = await example_filesystem_mcp()
        assert result is not None
        assert result.final_output is not None
    
    @pytest.mark.asyncio
    async def test_calculator_mcp_server_import(self):
        """测试计算器 MCP 服务器可以导入"""
        try:
            import calculator_mcp_server
            assert hasattr(calculator_mcp_server, 'CalculatorMCPServer')
            assert hasattr(calculator_mcp_server, 'main')
        except ImportError as e:
            pytest.skip(f"Cannot import calculator_mcp_server: {e}")
    
    def test_stdio_mcp_imports(self):
        """测试 stdio 示例文件可以正确导入"""
        try:
            import example_stdio_mcp
            assert hasattr(example_stdio_mcp, 'example_filesystem_mcp')
            assert hasattr(example_stdio_mcp, 'example_custom_calculator_mcp')
            assert hasattr(example_stdio_mcp, 'example_mcp_with_tool_filter')
            assert hasattr(example_stdio_mcp, 'example_mcp_with_caching')
            assert hasattr(example_stdio_mcp, 'example_dynamic_tool_filter')
        except ImportError as e:
            pytest.skip(f"Cannot import example_stdio_mcp: {e}")


class TestCalculatorMCPServer:
    """测试计算器 MCP 服务器"""
    
    @pytest.mark.asyncio
    async def test_calculator_server_creation(self):
        """测试服务器可以创建"""
        try:
            from calculator_mcp_server import CalculatorMCPServer
            server = CalculatorMCPServer()
            assert server is not None
            assert server.server_info["name"] == "calculator-server"
        except ImportError:
            pytest.skip("Cannot import calculator_mcp_server")
    
    @pytest.mark.asyncio
    async def test_calculator_initialize(self):
        """测试 initialize 方法"""
        try:
            from calculator_mcp_server import CalculatorMCPServer
            server = CalculatorMCPServer()
            
            result = await server.handle_initialize({})
            assert "protocolVersion" in result
            assert result["protocolVersion"] == "2024-11-05"
            assert "serverInfo" in result
            assert "capabilities" in result
        except ImportError:
            pytest.skip("Cannot import calculator_mcp_server")
    
    @pytest.mark.asyncio
    async def test_calculator_list_tools(self):
        """测试 tools/list 方法"""
        try:
            from calculator_mcp_server import CalculatorMCPServer
            server = CalculatorMCPServer()
            
            result = await server.handle_list_tools({})
            assert "tools" in result
            tools = result["tools"]
            assert len(tools) == 4
            
            tool_names = [t["name"] for t in tools]
            assert "add" in tool_names
            assert "subtract" in tool_names
            assert "multiply" in tool_names
            assert "divide" in tool_names
        except ImportError:
            pytest.skip("Cannot import calculator_mcp_server")
    
    @pytest.mark.asyncio
    async def test_calculator_add_tool(self):
        """测试 add 工具"""
        try:
            from calculator_mcp_server import CalculatorMCPServer
            server = CalculatorMCPServer()
            
            result = await server.handle_call_tool({
                "name": "add",
                "arguments": {"a": 5, "b": 3}
            })
            
            assert "content" in result
            assert len(result["content"]) > 0
            assert result["content"][0]["type"] == "text"
            assert result["content"][0]["text"] == "8"
        except ImportError:
            pytest.skip("Cannot import calculator_mcp_server")
    
    @pytest.mark.asyncio
    async def test_calculator_divide_by_zero(self):
        """测试除零错误处理"""
        try:
            from calculator_mcp_server import CalculatorMCPServer
            server = CalculatorMCPServer()
            
            result = await server.handle_call_tool({
                "name": "divide",
                "arguments": {"a": 10, "b": 0}
            })
            
            assert "content" in result
            assert "isError" in result
            assert result["isError"] is True
            assert "Division by zero" in result["content"][0]["text"]
        except ImportError:
            pytest.skip("Cannot import calculator_mcp_server")
    
    @pytest.mark.asyncio
    async def test_calculator_unknown_tool(self):
        """测试未知工具错误处理"""
        try:
            from calculator_mcp_server import CalculatorMCPServer
            server = CalculatorMCPServer()
            
            result = await server.handle_call_tool({
                "name": "unknown_tool",
                "arguments": {}
            })
            
            assert "content" in result
            assert "isError" in result
            assert result["isError"] is True
            assert "Unknown tool" in result["content"][0]["text"]
        except ImportError:
            pytest.skip("Cannot import calculator_mcp_server")
    
    @pytest.mark.asyncio
    async def test_calculator_request_routing(self):
        """测试请求路由"""
        try:
            from calculator_mcp_server import CalculatorMCPServer
            server = CalculatorMCPServer()
            
            # 测试 initialize 路由
            response = await server.handle_request({
                "method": "initialize",
                "params": {}
            })
            assert "result" in response
            assert "serverInfo" in response["result"]
            
            # 测试 tools/list 路由
            response = await server.handle_request({
                "method": "tools/list",
                "params": {}
            })
            assert "result" in response
            assert "tools" in response["result"]
            
            # 测试 tools/call 路由
            response = await server.handle_request({
                "method": "tools/call",
                "params": {"name": "add", "arguments": {"a": 1, "b": 2}}
            })
            assert "result" in response
            assert "content" in response["result"]
        except ImportError:
            pytest.skip("Cannot import calculator_mcp_server")
    
    @pytest.mark.asyncio
    async def test_calculator_unknown_method(self):
        """测试未知方法错误处理"""
        try:
            from calculator_mcp_server import CalculatorMCPServer
            server = CalculatorMCPServer()
            
            response = await server.handle_request({
                "method": "unknown_method",
                "params": {}
            })
            
            assert "error" in response
            assert response["error"]["code"] == -32601
            assert "Method not found" in response["error"]["message"]
        except ImportError:
            pytest.skip("Cannot import calculator_mcp_server")


class TestMCPIntegration:
    """集成测试"""
    
    def test_readme_exists(self):
        """测试 README 文件存在"""
        readme_path = examples_dir / "README.md"
        assert readme_path.exists(), "README.md should exist"
        
        content = readme_path.read_text()
        assert "MCP" in content
        assert "Model Context Protocol" in content
    
    def test_example_files_exist(self):
        """测试示例文件存在"""
        assert (examples_dir / "example_hosted_mcp.py").exists()
        assert (examples_dir / "example_stdio_mcp.py").exists()
        assert (examples_dir / "calculator_mcp_server.py").exists()
    
    def test_example_files_executable(self):
        """测试示例文件可执行"""
        import subprocess
        
        files = [
            "example_hosted_mcp.py",
            "example_stdio_mcp.py",
            "calculator_mcp_server.py"
        ]
        
        for filename in files:
            filepath = examples_dir / filename
            # 检查文件是否有 shebang 和 main
            content = filepath.read_text()
            assert "#!/usr/bin/env python3" in content
            assert 'if __name__ == "__main__"' in content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

