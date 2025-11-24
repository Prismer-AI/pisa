"""
MCP (Model Context Protocol) Examples Module

This module demonstrates how to use MCP servers with PISA and OpenAI Agent SDK.

MCP Types:
- Hosted MCP: OpenAI-hosted MCP servers (uses HostedMCPTool)
- stdio MCP: Local subprocess communication via stdin/stdout
- HTTP MCP: HTTP-based MCP servers (Streamable HTTP, SSE)

Note: These are examples showing how to use MCP with OpenAI Agent SDK.
      Integration with PISA capability system requires Loop modifications
      to properly manage async context managers.

See: https://openai.github.io/openai-agents-python/mcp/
"""

__all__ = []
