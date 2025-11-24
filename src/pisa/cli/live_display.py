"""
Live Display for Agent Execution

使用 Rich 的 Live 和 Panel 来实时展示 Agent 执行流程
参考：https://github.com/Textualize/rich
"""

from typing import Any, Dict, Optional
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.live import Live
from rich import box
import json

console = Console()


class AgentLiveDisplay:
    """Agent 执行的实时显示"""
    
    def __init__(self):
        self.live = None
        self.iteration = 0
        self.history = []
        
    def start(self):
        """开始实时显示"""
        self.live = Live(console=console, refresh_per_second=4)
        self.live.start()
    
    def stop(self):
        """停止实时显示"""
        if self.live:
            self.live.stop()
    
    def show_user_query(self, query: str):
        """显示用户查询"""
        panel = Panel(
            query,
            title="👤 User Query",
            border_style="cyan",
            box=box.ROUNDED
        )
        console.print(panel)
        console.print()
    
    def show_planning(self, iteration: int, plan: Dict[str, Any]):
        """显示规划结果"""
        # 提取任务
        tasks = plan.get('tasks', {})
        root_goal = plan.get('root_goal', 'N/A')
        
        # 创建任务表格
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Task ID", style="cyan", width=10)
        table.add_column("Capability", style="green", width=20)
        table.add_column("Description", style="white")
        
        for idx, (task_id, task) in enumerate(tasks.items(), 1):
            if isinstance(task, dict):
                capability = task.get('assigned_capability', 'N/A')
                desc = task.get('task_description', 'N/A')
            else:
                capability = getattr(task, 'assigned_capability', 'N/A')
                desc = getattr(task, 'task_description', 'N/A')
            
            if len(desc) > 50:
                desc = desc[:47] + "..."
            
            table.add_row(str(idx), task_id, capability, desc)
        
        content = Group(
            f"[bold]Goal:[/bold] {root_goal}",
            "",
            table
        )
        
        panel = Panel(
            content,
            title=f"📋 Planning (Iteration {iteration})",
            border_style="blue",
            box=box.ROUNDED
        )
        console.print(panel)
        console.print()
    
    def show_task_execution(
        self,
        iteration: int,
        task_id: str,
        capability: str,
        tool_input: Dict[str, Any],
        tool_output: Any,
        success: bool
    ):
        """显示任务执行（工具调用）"""
        # 工具输入
        input_json = json.dumps(tool_input, indent=2, ensure_ascii=False)
        input_syntax = Syntax(input_json, "json", theme="monokai", line_numbers=False)
        
        # 工具输出
        if isinstance(tool_output, dict):
            output_json = json.dumps(tool_output, indent=2, ensure_ascii=False)
        else:
            output_json = str(tool_output)
        
        # 限制长度
        if len(output_json) > 500:
            output_json = output_json[:500] + "\n... (truncated)"
        
        output_syntax = Syntax(output_json, "json", theme="monokai", line_numbers=False)
        
        # 状态图标
        status_icon = "✅" if success else "❌"
        status_color = "green" if success else "red"
        
        content = Group(
            f"[bold cyan]Task:[/bold cyan] {task_id}",
            f"[bold magenta]Capability:[/bold magenta] {capability}",
            f"[bold {status_color}]Status:[/bold {status_color}] {status_icon}",
            "",
            "[bold yellow]Input:[/bold yellow]",
            input_syntax,
            "",
            "[bold yellow]Output:[/bold yellow]",
            output_syntax
        )
        
        panel = Panel(
            content,
            title=f"🔧 Execution (Iteration {iteration})",
            border_style="green" if success else "red",
            box=box.ROUNDED
        )
        console.print(panel)
        console.print()
    
    def show_observation(
        self,
        iteration: int,
        task_id: str,
        success: bool,
        error_type: Optional[str],
        decision: str,
        reason: str
    ):
        """显示观察和决策"""
        status_icon = "✅" if success else "❌"
        status_color = "green" if success else "red"
        
        content = Group(
            f"[bold cyan]Task:[/bold cyan] {task_id}",
            f"[bold {status_color}]Execution:[/bold {status_color}] {status_icon} {'Success' if success else 'Failed'}",
            f"[bold]Error Type:[/bold] {error_type or 'None'}",
            "",
            f"[bold yellow]Decision:[/bold yellow] {decision.upper()}",
            f"[bold]Reason:[/bold] {reason}"
        )
        
        panel = Panel(
            content,
            title=f"👁️ Observation (Iteration {iteration})",
            border_style="yellow",
            box=box.ROUNDED
        )
        console.print(panel)
        console.print()
    
    def show_reflection(
        self,
        iteration: int,
        task_description: str,
        success_evaluation: bool,
        quality_score: float,
        analysis: str
    ):
        """显示反思"""
        # Handle None quality_score (when reflection parsing fails)
        if quality_score is None:
            score_color = "gray"
            score_display = "N/A"
        else:
            score_color = "green" if quality_score >= 0.8 else "yellow" if quality_score >= 0.6 else "red"
            score_display = f"{quality_score:.2f}"
        
        content = Group(
            f"[bold cyan]Task:[/bold cyan] {task_description[:80]}...",
            "",
            f"[bold]Success:[/bold] {'✅ Yes' if success_evaluation else '❌ No'}",
            f"[bold]Quality Score:[/bold] [{score_color}]{score_display}[/{score_color}]",
            "",
            f"[bold yellow]Analysis:[/bold yellow]",
            f"{analysis[:200]}..." if len(analysis) > 200 else analysis
        )
        
        panel = Panel(
            content,
            title=f"🤔 Reflection (Iteration {iteration})",
            border_style="magenta",
            box=box.ROUNDED
        )
        console.print(panel)
        console.print()
    
    def show_iteration_summary(self, iteration: int, tasks_completed: int, total_tasks: int):
        """显示迭代摘要"""
        progress = f"{tasks_completed}/{total_tasks}"
        percentage = (tasks_completed / total_tasks * 100) if total_tasks > 0 else 0
        
        console.print(f"[dim]{'─' * 80}[/dim]")
        console.print(
            f"[bold cyan]Iteration {iteration} Complete[/bold cyan] | "
            f"Progress: [green]{progress}[/green] ([yellow]{percentage:.0f}%[/yellow])"
        )
        console.print(f"[dim]{'─' * 80}[/dim]")
        console.print()


# 全局实例
_live_display = None


def get_live_display() -> AgentLiveDisplay:
    """获取全局 Live Display 实例"""
    global _live_display
    if _live_display is None:
        _live_display = AgentLiveDisplay()
    return _live_display


def show_user_query(query: str):
    """快捷方法：显示用户查询"""
    get_live_display().show_user_query(query)


def show_planning(iteration: int, plan: Dict[str, Any]):
    """快捷方法：显示规划"""
    get_live_display().show_planning(iteration, plan)


def show_task_execution(
    iteration: int,
    task_id: str,
    capability: str,
    tool_input: Dict[str, Any],
    tool_output: Any,
    success: bool
):
    """快捷方法：显示任务执行"""
    get_live_display().show_task_execution(
        iteration, task_id, capability, tool_input, tool_output, success
    )


def show_observation(
    iteration: int,
    task_id: str,
    success: bool,
    error_type: Optional[str],
    decision: str,
    reason: str
):
    """快捷方法：显示观察"""
    get_live_display().show_observation(
        iteration, task_id, success, error_type, decision, reason
    )


def show_reflection(
    iteration: int,
    task_description: str,
    success_evaluation: bool,
    quality_score: float,
    analysis: str
):
    """快捷方法：显示反思"""
    get_live_display().show_reflection(
        iteration, task_description, success_evaluation, quality_score, analysis
    )


def show_iteration_summary(iteration: int, tasks_completed: int, total_tasks: int):
    """快捷方法：显示迭代摘要"""
    get_live_display().show_iteration_summary(iteration, tasks_completed, total_tasks)


