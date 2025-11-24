"""
Unit tests for MCP生命周期管理

只测试 MCP 相关的生命周期方法，不需要完整初始化 Loop。
"""

import pytest
from unittest.mock import AsyncMock


class MockMCPServer:
    """模拟 MCP 服务器用于测试"""
    
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.started = False
        self.stopped = False
        self._enter_called = False
        self._exit_called = False
    
    async def __aenter__(self):
        """进入 context manager"""
        self._enter_called = True
        if self.should_fail:
            raise RuntimeError(f"Failed to start {self.name}")
        self.started = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出 context manager"""
        self._exit_called = True
        self.stopped = True
        return False


class MockLoop:
    """模拟的 Loop 对象，只包含 MCP 相关字段和方法"""
    
    def __init__(self):
        self.mcp_servers = []
        self._mcp_contexts = []
        self._active_mcp_servers = []
    
    async def _start_mcp_servers(self) -> None:
        """启动所有 MCP 服务器 (从 base.py 复制的逻辑)"""
        if not self.mcp_servers:
            return
        
        for mcp_server in self.mcp_servers:
            try:
                if not hasattr(mcp_server, '__aenter__'):
                    continue
                
                active_server = await mcp_server.__aenter__()
                self._mcp_contexts.append((mcp_server, None))
                self._active_mcp_servers.append(active_server)
                
            except Exception as e:
                await self._stop_mcp_servers()
                raise RuntimeError(f"Failed to start MCP server: {e}") from e
    
    async def _stop_mcp_servers(self) -> None:
        """关闭所有 MCP 服务器 (从 base.py 复制的逻辑)"""
        if not self._mcp_contexts:
            return
        
        errors = []
        for mcp_server, _ in self._mcp_contexts:
            try:
                await mcp_server.__aexit__(None, None, None)
            except Exception as e:
                server_name = getattr(mcp_server, 'name', 'unknown')
                errors.append((server_name, e))
        
        self._mcp_contexts.clear()
        self._active_mcp_servers.clear()


class TestMCPLifecycle:
    """测试 MCP 生命周期管理"""
    
    def test_initialization(self):
        """测试初始化状态"""
        loop = MockLoop()
        
        assert loop.mcp_servers == []
        assert loop._mcp_contexts == []
        assert loop._active_mcp_servers == []
    
    @pytest.mark.asyncio
    async def test_start_single_server(self):
        """测试启动单个服务器"""
        loop = MockLoop()
        server = MockMCPServer("test_server")
        loop.mcp_servers = [server]
        
        await loop._start_mcp_servers()
        
        assert server.started
        assert server._enter_called
        assert len(loop._active_mcp_servers) == 1
        assert len(loop._mcp_contexts) == 1
    
    @pytest.mark.asyncio
    async def test_start_multiple_servers(self):
        """测试启动多个服务器"""
        loop = MockLoop()
        server1 = MockMCPServer("server1")
        server2 = MockMCPServer("server2")
        server3 = MockMCPServer("server3")
        loop.mcp_servers = [server1, server2, server3]
        
        await loop._start_mcp_servers()
        
        assert all(s.started for s in [server1, server2, server3])
        assert len(loop._active_mcp_servers) == 3
        assert len(loop._mcp_contexts) == 3
    
    @pytest.mark.asyncio
    async def test_start_server_failure(self):
        """测试服务器启动失败时的清理"""
        loop = MockLoop()
        good_server = MockMCPServer("good")
        bad_server = MockMCPServer("bad", should_fail=True)
        loop.mcp_servers = [good_server, bad_server]
        
        with pytest.raises(RuntimeError, match="Failed to start"):
            await loop._start_mcp_servers()
        
        # 验证清理
        assert len(loop._active_mcp_servers) == 0
        assert len(loop._mcp_contexts) == 0
        
        # 好的服务器应该被停止
        assert good_server.stopped
    
    @pytest.mark.asyncio
    async def test_stop_servers(self):
        """测试关闭服务器"""
        loop = MockLoop()
        server1 = MockMCPServer("server1")
        server2 = MockMCPServer("server2")
        loop.mcp_servers = [server1, server2]
        
        # 先启动
        await loop._start_mcp_servers()
        assert len(loop._active_mcp_servers) == 2
        
        # 再关闭
        await loop._stop_mcp_servers()
        
        assert server1.stopped
        assert server2.stopped
        assert server1._exit_called
        assert server2._exit_called
        assert len(loop._active_mcp_servers) == 0
        assert len(loop._mcp_contexts) == 0
    
    @pytest.mark.asyncio
    async def test_stop_servers_handles_errors(self):
        """测试关闭时处理错误"""
        loop = MockLoop()
        server = MockMCPServer("server")
        loop.mcp_servers = [server]
        
        await loop._start_mcp_servers()
        
        # Mock __aexit__ 抛出异常
        async def failing_exit(*args):
            raise Exception("Exit error")
        
        server.__aexit__ = failing_exit
        
        # 应该不抛出异常，但完成清理
        await loop._stop_mcp_servers()
        
        assert len(loop._active_mcp_servers) == 0
        assert len(loop._mcp_contexts) == 0
    
    @pytest.mark.asyncio
    async def test_empty_server_list(self):
        """测试空服务器列表"""
        loop = MockLoop()
        loop.mcp_servers = []
        
        # 应该正常工作
        await loop._start_mcp_servers()
        assert len(loop._active_mcp_servers) == 0
        
        await loop._stop_mcp_servers()
        assert len(loop._active_mcp_servers) == 0
    
    @pytest.mark.asyncio
    async def test_skip_non_context_manager(self):
        """测试跳过非 context manager 对象"""
        loop = MockLoop()
        
        # 不是 context manager 的对象
        class NotAContextManager:
            def __init__(self):
                self.name = "not_cm"
        
        loop.mcp_servers = [NotAContextManager()]
        
        # 应该跳过但不报错
        await loop._start_mcp_servers()
        assert len(loop._active_mcp_servers) == 0
    
    @pytest.mark.asyncio
    async def test_mixed_servers(self):
        """测试混合的服务器（包括非 CM 对象）"""
        loop = MockLoop()
        
        good_server = MockMCPServer("good")
        
        class NotCM:
            name = "not_cm"
        
        loop.mcp_servers = [good_server, NotCM()]
        
        await loop._start_mcp_servers()
        
        # 只有好的服务器启动
        assert len(loop._active_mcp_servers) == 1
        assert good_server.started
    
    @pytest.mark.asyncio
    async def test_lifecycle_complete_cycle(self):
        """测试完整生命周期"""
        loop = MockLoop()
        server = MockMCPServer("test")
        loop.mcp_servers = [server]
        
        # 初始状态
        assert not server.started
        assert not server.stopped
        
        # 启动
        await loop._start_mcp_servers()
        assert server.started
        assert not server.stopped
        assert server._enter_called
        
        # 关闭
        await loop._stop_mcp_servers()
        assert server.started  # 仍然是 True
        assert server.stopped  # 现在是 True
        assert server._exit_called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

