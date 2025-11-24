"""
Loop 展示工具

提供通用的展示方法，供所有 Agent Loop 使用。

职责：
1. 定义层信息展示
2. 任务树可视化
3. Context 状态展示
4. 执行摘要展示
"""

from typing import Any, Optional
from rich.console import Console
from rich.table import Table
from rich.tree import Tree as RichTree
from rich.panel import Panel
from rich import box

from pisa.core.planning import TaskTree, TaskStatus
from pisa.core.context.models import ContextState
from pisa.utils import context_display


console = Console()


def display_loop_definition(loop_definition: Any) -> None:
    """
    展示 Loop 定义信息
    
    Args:
        loop_definition: LoopDefinition 对象
    """
    if not loop_definition:
        return
    
    table = Table(
        title=f"🎯 Agent Loop Definition: {loop_definition.name}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("配置项", style="cyan", width=25)
    table.add_column("值", style="white")
    
    # 基本信息
    table.add_row("Loop Type", loop_definition.loop_type)
    table.add_row("Version", loop_definition.version)
    table.add_row("Description", loop_definition.description or "-")
    
    # 模型配置
    if loop_definition.model:
        table.add_row("Default Model", loop_definition.model)
    if hasattr(loop_definition, 'planning_model') and loop_definition.planning_model:
        table.add_row("Planning Model", loop_definition.planning_model)
    if hasattr(loop_definition, 'execution_model') and loop_definition.execution_model:
        table.add_row("Execution Model", loop_definition.execution_model)
    if hasattr(loop_definition, 'reflection_model') and loop_definition.reflection_model:
        table.add_row("Reflection Model", loop_definition.reflection_model)
    
    # 能力列表
    if loop_definition.capabilities:
        caps_str = ", ".join(loop_definition.capabilities[:5])
        if len(loop_definition.capabilities) > 5:
            caps_str += f", ... (+{len(loop_definition.capabilities) - 5} more)"
        table.add_row("Capabilities", caps_str)
    
    # 运行时配置
    if hasattr(loop_definition, 'max_iterations'):
        table.add_row("Max Iterations", str(loop_definition.max_iterations))
    if hasattr(loop_definition, 'enable_replanning'):
        table.add_row("Enable Replanning", "✓" if loop_definition.enable_replanning else "✗")
    if hasattr(loop_definition, 'enable_reflection'):
        table.add_row("Enable Reflection", "✓" if loop_definition.enable_reflection else "✗")
    if hasattr(loop_definition, 'enable_validation'):
        table.add_row("Enable Validation", "✓" if loop_definition.enable_validation else "✗")
    
    console.print("\n")
    console.print(table)
    console.print("\n")


def display_task_tree(tree: TaskTree) -> None:
    """
    展示任务树
    
    Args:
        tree: TaskTree 对象
    """
    rich_tree = RichTree(
        f"📋 Task Plan (v{tree.plan_version})",
        guide_style="dim"
    )
    
    # 按照执行顺序展示任务
    for i, task in enumerate(tree.tasks.values(), 1):
        status_icon = {
            TaskStatus.PENDING: "⏸️",
            TaskStatus.RUNNING: "▶️",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.BLOCKED: "🚫"
        }.get(task.status, "❓")
        
        task_branch = rich_tree.add(
            f"{status_icon} [{i}] {task.task_description}"
        )
        
        # 添加任务详情
        if task.task_detail_info:
            detail = task.task_detail_info[:100]
            if len(task.task_detail_info) > 100:
                detail += "..."
            task_branch.add(f"[dim]Details: {detail}[/dim]")
        
        if task.metadata.get("capability"):
            task_branch.add(
                f"[cyan]Capability:[/cyan] {task.metadata['capability']}"
            )
        
        if task.dependencies:
            deps_str = ", ".join(task.dependencies[:3])
            if len(task.dependencies) > 3:
                deps_str += f", ... (+{len(task.dependencies) - 3} more)"
            task_branch.add(f"[yellow]Dependencies:[/yellow] {deps_str}")
    
    console.print("\n")
    console.print(Panel(rich_tree, title="📊 Execution Plan", box=box.ROUNDED))
    console.print("\n")


def display_context_state(context_state: ContextState) -> None:
    """
    展示 Context 状态
    
    Args:
        context_state: ContextState 对象
    """
    table = Table(
        title="📝 Context State",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")
    
    table.add_row("Current Round", str(context_state.current_round))
    table.add_row("Total Messages", str(len(context_state.messages)))
    table.add_row("Total Tokens", f"{context_state.total_tokens:,}")
    table.add_row("Compressions", str(context_state.compression_count))
    
    console.print("\n")
    console.print(table)
    
    # 展示最近的消息
    if context_state.messages:
        recent_messages = context_state.messages[-3:]
        # 使用 context_display 模块的函数
        if hasattr(context_display, 'display_messages'):
            context_display.display_messages(
                [msg.model_dump() for msg in recent_messages],
                title="Recent Messages (Last 3)",
                max_content_length=150
            )
    console.print("\n")


def display_execution_summary(
    success: bool,
    iterations: int,
    duration: float,
    task_stats: Optional[dict] = None,
    observability_stats: Optional[dict] = None
) -> None:
    """
    展示执行摘要
    
    Args:
        success: 是否成功
        iterations: 迭代次数
        duration: 执行时长（秒）
        task_stats: 任务统计信息
        observability_stats: 观测统计信息
    """
    status_icon = "✅" if success else "❌"
    status_text = "[green]SUCCESS[/green]" if success else "[red]FAILED[/red]"
    
    console.print("\n" + "=" * 80)
    console.print(f"{status_icon} Execution Summary - {status_text}")
    console.print("=" * 80)
    
    # 基本信息
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Total Iterations", str(iterations))
    table.add_row("Duration", f"{duration:.2f}s")
    
    # 任务统计
    if task_stats:
        table.add_row("Tasks Planned", str(task_stats.get('total_tasks', 0)))
        table.add_row("Tasks Completed", str(task_stats.get('completed', 0)))
        table.add_row("Tasks Failed", str(task_stats.get('failed', 0)))
    
    # 观测统计
    if observability_stats:
        table.add_row("Phases Tracked", str(observability_stats.get('phases', 0)))
        table.add_row("Traces Recorded", str(observability_stats.get('traces', 0)))
    
    console.print(table)
    console.print("=" * 80 + "\n")



