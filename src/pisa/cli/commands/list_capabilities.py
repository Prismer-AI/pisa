"""
List Capabilities Command

职责：
1. 列出所有已注册的 Capability
2. 按类型过滤显示
3. 显示 Capability 详细信息
4. 支持搜索和排序

使用示例：
```bash
pisa list-capabilities
pisa list-capabilities --type function
pisa list-capabilities --search "search"
pisa list list  # 列出所有 (capabilities + loops)
```
"""

import click
import json
from typing import Optional

from pisa.cli.ui import (
    display_icon,
    print_header,
    print_table,
    print_panel,
    print_info,
    print_warning,
    console
)
from pisa.startup import initialize_pisa
from pisa.agents import get_registry_manager
from pisa.utils.logger import get_logger

_logger = get_logger(__name__)


@click.command(name="list-capabilities", context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--type",
    "-t",
    type=click.Choice(["all", "function", "agent", "mcp", "loop"]),
    default="all",
    help="Filter by type (all/function/agent/mcp/loop)"
)
@click.option(
    "--search",
    "-s",
    type=str,
    help="Search capabilities by name or description"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information"
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format"
)
def list_capabilities_command(
    type: str,
    search: Optional[str],
    verbose: bool,
    format: str
) -> None:
    """
    List all registered capabilities and loop templates
    
    Args:
        type: Type filter (all/function/agent/mcp/loop)
        search: Search query
        verbose: Verbose mode flag
        format: Output format (table/json)
    """
    display_icon()
    print_header("PISA Capabilities & Loops", "List all registered components")
    
    try:
        # 初始化系统（不显示启动信息，因为我们会自己显示）
        manager = initialize_pisa(display_startup_info=False)
        
        # 决定显示什么
        show_capabilities = type in ["all", "function", "agent", "mcp"]
        show_loops = type in ["all", "loop"]
        
        results = {
            "capabilities": [],
            "loops": []
        }
        
        # 1. 列出 Capabilities
        if show_capabilities:
            cap_type_filter = None if type == "all" else type
            capabilities = manager.list_capabilities(
                capability_type=cap_type_filter
            )
            
            # 应用搜索过滤
            if search:
                capabilities = [
                    cap for cap in capabilities
                    if search.lower() in cap.name.lower() or 
                       (cap.description and search.lower() in cap.description.lower())
                ]
            
            results["capabilities"] = [
                {
                    "name": cap.name,
                    "type": cap.capability_type,
                    "description": cap.description or "No description"
                }
                for cap in capabilities
            ]
        
        # 2. 列出 Loop Templates
        if show_loops:
            loops_dict = manager.loop_registry.list_all()
            
            # 应用搜索过滤
            if search:
                loops_dict = {
                    name: cls for name, cls in loops_dict.items()
                    if search.lower() in name.lower()
                }
            
            results["loops"] = [
                {
                    "name": loop_name,
                    "type": "loop",
                    "description": loop_cls.__doc__.split('\n')[0] if loop_cls.__doc__ else f"Agent loop template: {loop_name}"
                }
                for loop_name, loop_cls in loops_dict.items()
            ]
        
        # 3. 输出结果
        if format == "json":
            console.print_json(data=results)
        else:
            # Table 格式 - 使用改进的格式
            if results["capabilities"]:
                print_info(f"Found {len(results['capabilities'])} capabilities")
                console.print()
                
                # 使用 rich Table 创建更好的显示
                from rich.table import Table
                from rich import box
                
                cap_table = Table(
                    title="📦 Registered Capabilities",
                    box=box.ROUNDED,
                    show_header=True,
                    header_style="bold cyan"
                )
                cap_table.add_column("Name", style="cyan bold", no_wrap=True, min_width=20)
                cap_table.add_column("Source", style="magenta", no_wrap=True, min_width=12)
                cap_table.add_column("Category", style="yellow", no_wrap=False, width=15)
                cap_table.add_column("Description", style="white")
                cap_table.add_column("Parameters", style="dim", no_wrap=True, min_width=18)
                
                # 获取完整的 capability 对象以显示详细信息
                capabilities = manager.list_capabilities(
                    capability_type=cap_type_filter
                )
                
                # 应用搜索过滤
                if search:
                    capabilities = [
                        cap for cap in capabilities
                        if search.lower() in cap.name.lower() or 
                           (cap.description and search.lower() in cap.description.lower())
                    ]
                
                # 排序：internal 在前，custom 在后
                capabilities.sort(key=lambda c: (getattr(c, 'source', 'custom') != "internal", c.name))
                
                for cap in capabilities:
                    # 格式化 source
                    source = getattr(cap, 'source', 'custom')
                    if source == "internal":
                        source_display = "🏠 Built-in"
                    else:
                        source_display = "⚙️ Custom"
                    
                    # 格式化 category（使用 tags 的第一个作为主分类）
                    cap_tags = getattr(cap, 'tags', None) or []
                    if cap_tags and len(cap_tags) > 0:
                        category = cap_tags[0].title()
                        if len(cap_tags) > 1:
                            category += f" +{len(cap_tags) - 1}"
                    else:
                        category = cap.capability_type.title()
                    
                    # 格式化描述
                    description = cap.description or "-"
                    if not verbose and len(description) > 35:
                        description = description[:32] + "..."
                    
                    # 格式化参数
                    params_info = []
                    if cap.parameters and 'properties' in cap.parameters:
                        required = cap.parameters.get('required', [])
                        properties = cap.parameters.get('properties', {})
                        
                        # 显示必需参数
                        for param_name in required[:2]:
                            if param_name in properties:
                                param_type = properties[param_name].get('type', 'any')
                                params_info.append(f"{param_name}:{param_type}")
                        
                        # 如果还有更多参数
                        total_params = len(properties)
                        shown_params = len(params_info)
                        if total_params > shown_params:
                            params_info.append(f"+{total_params - shown_params} more")
                    
                    params_display = "\n".join(params_info) if params_info else "-"
                    
                    cap_table.add_row(
                        cap.name,
                        source_display,
                        category,
                        description,
                        params_display
                    )
                
                console.print(cap_table)
                console.print()
            
            if results["loops"]:
                print_info(f"Found {len(results['loops'])} loop templates")
                console.print()
                
                headers = ["Name", "Type", "Description"]
                rows = []
                for loop in results["loops"]:
                    desc = loop["description"]
                    if not verbose and len(desc) > 50:
                        desc = desc[:47] + "..."
                    rows.append([loop["name"], loop["type"], desc])
                
                print_table(headers, rows, title="🔄 Loop Templates")
                console.print()
            
            if not results["capabilities"] and not results["loops"]:
                print_warning("No capabilities or loops found")
                if search:
                    console.print(f"  Search term: [cyan]{search}[/cyan]")
        
    except Exception as e:
        _logger.error(f"Failed to list capabilities: {e}", exc_info=True)
        console.print(f"[red]✗ Error:[/red] {e}")
        raise click.Abort()


def _format_table(capabilities: list, verbose: bool) -> str:
    """
    格式化为表格
    
    Args:
        capabilities: Capability 列表
        verbose: 是否详细模式
        
    Returns:
        表格字符串
        
    TODO: 使用 rich.table 格式化
    """
    raise NotImplementedError("待实现")


def _format_json(capabilities: list) -> str:
    """
    格式化为 JSON
    
    Args:
        capabilities: Capability 列表
        
    Returns:
        JSON 字符串
        
    TODO: 实现 JSON 格式化
    """
    raise NotImplementedError("待实现")


def _format_yaml(capabilities: list) -> str:
    """
    格式化为 YAML
    
    Args:
        capabilities: Capability 列表
        
    Returns:
        YAML 字符串
        
    TODO: 实现 YAML 格式化
    """
    raise NotImplementedError("待实现")

