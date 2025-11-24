"""
Capability Resolver

职责：
1. 从capability名称列表查询完整信息
2. 验证capability是否存在
3. 转换为OpenAI Agent SDK所需的格式（functions/handoffs/mcp_servers）
4. 显示capabilities信息表格

使用示例：
```python
from pisa.capability.registry import get_global_registry
from pisa.core.loop.capability_resolver import CapabilityResolver

resolver = CapabilityResolver(get_global_registry())

# 解析capabilities
result = resolver.resolve(["tool1", "tool2", "agent1"])
# result = {
#     "functions": [FunctionTool1, FunctionTool2],
#     "handoffs": [Agent1],
#     "mcp_servers": []
# }

# 显示信息
resolver.display_info(["tool1", "tool2", "agent1"])
```
"""

import logging
from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.console import Console
from rich import box

_logger = logging.getLogger(__name__)


class CapabilityResolver:
    """
    Capability解析器
    
    将capability名称列表转换为OpenAI Agent SDK所需的格式：
    - functions: List[FunctionTool] - 函数工具
    - handoffs: List[Agent] - 子Agent
    - mcp_servers: List[MCPServer] - MCP服务器
    """
    
    def __init__(self, registry: "CapabilityRegistry"):
        """
        初始化Resolver
        
        Args:
            registry: CapabilityRegistry实例
        """
        self.registry = registry
        self._console = Console()
    
    def resolve(
        self,
        capability_names: List[str],
        raise_on_missing: bool = True
    ) -> Dict[str, List[Any]]:
        """
        解析capability列表
        
        将字符串名称列表转换为OpenAI Agent SDK所需的对象列表。
        
        Args:
            capability_names: Capability名称列表
            raise_on_missing: 是否在capability不存在时抛出异常
            
        Returns:
            包含三个列表的字典：
            {
                "functions": [FunctionTool, ...],  # function类型
                "handoffs": [Agent, ...],          # agent类型
                "mcp_servers": [MCPServer, ...]    # mcp类型
            }
            
        Raises:
            ValueError: 如果有capability不存在且raise_on_missing=True
        """
        functions = []
        handoffs = []
        mcp_servers = []
        missing = []
        
        _logger.info(f"Resolving {len(capability_names)} capabilities...")
        
        for name in capability_names:
            # 从registry查询
            cap = self.registry.get(name)
            
            if not cap:
                missing.append(name)
                _logger.warning(f"Capability not found: {name}")
                continue
            
            # 获取实际对象
            try:
                obj = cap.get_object(registry=self.registry)
                
                # 根据类型分类
                if cap.capability_type == "function":
                    functions.append(obj)
                    _logger.debug(f"Resolved function: {name} -> {type(obj).__name__}")
                elif cap.capability_type == "agent":
                    handoffs.append(obj)
                    _logger.debug(f"Resolved agent: {name} -> {type(obj).__name__}")
                elif cap.capability_type == "mcp":
                    mcp_servers.append(obj)
                    _logger.debug(f"Resolved mcp: {name} -> {type(obj).__name__}")
                else:
                    _logger.warning(f"Unknown capability type: {cap.capability_type} for {name}")
            
            except Exception as e:
                _logger.error(f"Failed to get object for capability {name}: {e}")
                missing.append(name)
        
        # 检查缺失的capabilities
        if missing and raise_on_missing:
            available = self.registry.list_all()
            raise ValueError(
                f"Capabilities not found in registry: {missing}\n"
                f"Available capabilities: {available}\n"
                f"Hint: Make sure all capabilities are registered before initializing the loop."
            )
        
        _logger.info(
            f"Resolved: {len(functions)} functions, "
            f"{len(handoffs)} handoffs, "
            f"{len(mcp_servers)} mcp_servers"
        )
        
        return {
            "functions": functions,
            "handoffs": handoffs,
            "mcp_servers": mcp_servers
        }
    
    def display_info(
        self,
        capability_names: List[str],
        title: str = "📦 Configured Capabilities"
    ) -> None:
        """
        显示capabilities信息表格
        
        用于启动时展示已配置的capabilities，帮助开发者了解可用工具。
        
        Args:
            capability_names: Capability名称列表
            title: 表格标题
        """
        table = Table(
            title=title,
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Description", style="white")
        table.add_column("Status", style="green", justify="center")
        
        for name in capability_names:
            cap = self.registry.get(name)
            
            if cap:
                # 成功找到
                desc = cap.description[:60] + "..." if len(cap.description) > 60 else cap.description
                
                # 从 tags 推断逻辑类型
                logical_type = "FUNCTION"
                if cap.tags:
                    if "mcp" in cap.tags:
                        logical_type = "MCP"
                    elif "agent" in cap.tags or "subagent" in cap.tags:
                        logical_type = "AGENT"
                
                table.add_row(
                    cap.name,
                    logical_type,
                    desc,
                    "✓"
                )
            else:
                # 未找到
                table.add_row(
                    name,
                    "???",
                    "[red]Not found in registry[/red]",
                    "✗"
                )
        
        self._console.print()
        self._console.print(table)
        self._console.print()
    
    def display_detailed_info(
        self,
        capability_names: List[str]
    ) -> None:
        """
        显示详细的capabilities信息
        
        包括参数、配置等详细信息。
        
        Args:
            capability_names: Capability名称列表
        """
        from rich.panel import Panel
        from rich.syntax import Syntax
        import json
        
        for name in capability_names:
            cap = self.registry.get(name)
            
            if not cap:
                self._console.print(f"[red]Capability not found: {name}[/red]")
                continue
            
            # 构建详细信息
            info_lines = [
                f"[bold cyan]{cap.name}[/bold cyan]",
                f"Type: [magenta]{cap.capability_type}[/magenta]",
                f"Description: {cap.description}",
                ""
            ]
            
            # 添加参数信息
            if cap.parameters:
                info_lines.append("[bold]Parameters:[/bold]")
                try:
                    params_json = json.dumps(cap.parameters, indent=2)
                    syntax = Syntax(params_json, "json", theme="monokai")
                    self._console.print(Panel(
                        "\n".join(info_lines),
                        title=f"📦 {cap.name}",
                        border_style="cyan"
                    ))
                    self._console.print(syntax)
                except Exception as e:
                    info_lines.append(str(cap.parameters))
                    self._console.print(Panel(
                        "\n".join(info_lines),
                        title=f"📦 {cap.name}",
                        border_style="cyan"
                    ))
            else:
                self._console.print(Panel(
                    "\n".join(info_lines),
                    title=f"📦 {cap.name}",
                    border_style="cyan"
                ))
            
            self._console.print()
    
    def validate(
        self,
        capability_names: List[str]
    ) -> Dict[str, Any]:
        """
        验证capabilities是否可用
        
        Args:
            capability_names: Capability名称列表
            
        Returns:
            验证结果字典：
            {
                "valid": bool,
                "found": List[str],
                "missing": List[str],
                "errors": Dict[str, str]
            }
        """
        found = []
        missing = []
        errors = {}
        
        for name in capability_names:
            cap = self.registry.get(name)
            
            if not cap:
                missing.append(name)
                continue
            
            # 尝试获取对象
            try:
                obj = cap.get_object(registry=self.registry)
                if obj is None:
                    errors[name] = "get_object() returned None"
                else:
                    found.append(name)
            except Exception as e:
                errors[name] = str(e)
        
        return {
            "valid": len(missing) == 0 and len(errors) == 0,
            "found": found,
            "missing": missing,
            "errors": errors
        }

