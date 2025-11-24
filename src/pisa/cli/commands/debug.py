"""
Debug Command

职责：
1. 启动调试模式运行 Agent
2. 显示详细的执行过程
3. 支持断点和单步执行
4. 输出调试日志

使用示例：
```bash
pisa debug agent.md --breakpoint step
pisa debug agent.md --verbose
pisa debug agent.md --step-by-step
```
"""

import click
import asyncio
import sys
from typing import Optional, List, Dict, Any
from pathlib import Path

from pisa.cli.ui import (
    print_header,
    print_error,
    print_success,
    print_warning,
    print_info,
    print_separator,
    print_panel,
    print_json,
    display_icon,
    console,
    InteractivePrompt
)
from pisa.startup import initialize_pisa
from pisa.core.definition import parse_agent_definition
from pisa.agents import get_registry_manager
from pisa.utils.logger import setup_logger, get_logger

_logger = get_logger(__name__)


@click.command(name="debug", context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("agent_definition", type=click.Path(exists=True))
@click.option(
    "--context",
    "-c",
    type=click.Path(exists=True),
    help="Context definition file"
)
@click.option(
    "--input",
    "-i",
    type=str,
    help="Input data"
)
@click.option(
    "--breakpoint",
    "-b",
    type=click.Choice(["step", "action", "error"]),
    multiple=True,
    help="Set breakpoints"
)
@click.option(
    "--step-by-step",
    "-s",
    is_flag=True,
    help="Execute step by step"
)
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="DEBUG",
    help="Log level"
)
@click.option(
    "--show-context",
    is_flag=True,
    help="Show context state at each step"
)
@click.option(
    "--show-planning",
    is_flag=True,
    help="Show planning details"
)
def debug_command(
    agent_definition: str,
    context: Optional[str],
    input: Optional[str],
    breakpoint: tuple,
    step_by_step: bool,
    log_level: str,
    show_context: bool,
    show_planning: bool
) -> None:
    """
    Debug an agent with detailed execution information
    
    Args:
        agent_definition: Path to agent.md
        context: Path to context.md
        input: Input data
        breakpoint: Breakpoint types
        step_by_step: Step-by-step mode flag
        log_level: Log level
        show_context: Show context flag
        show_planning: Show planning flag
    """
    # 设置调试日志
    setup_logger(level=log_level, enable_rich=True)
    
    # 显示icon和标题
    display_icon()
    print_header("PISA Debug Mode", "Debug your agent with detailed execution information")
    
    # 显示调试配置
    debug_config = DebugConfig(
        breakpoints=list(breakpoint),
        step_by_step=step_by_step,
        show_context=show_context,
        show_planning=show_planning,
        log_level=log_level
    )
    
    _print_debug_config(debug_config)
    print_separator()
    
    try:
        # 1. 初始化系统
        print_info("Initializing PISA system...")
        manager = initialize_pisa()
        
        # 2. 解析agent定义
        print_info(f"Loading agent: {agent_definition}")
        agent_def = parse_agent_definition(Path(agent_definition))
        
        print_success(f"Agent '{agent_def.metadata.name}' loaded")
        print_info(f"Loop type: {agent_def.loop_type.value}")
        print_separator()
        
        # 3. 创建agent实例
        print_info("Creating agent instance...")
        loop = manager.create_agent(agent_def)
        
        # 4. 准备输入
        if not input:
            console.print("[yellow]No input provided. Please enter input:[/yellow]")
            input_data = InteractivePrompt.multiline("Enter your input")
        else:
            input_data = input
        
        print_success("Ready to debug")
        print_separator()
        
        # 5. 启动调试会话
        _start_debug_session(loop, input_data, debug_config)
    
    except FileNotFoundError as e:
        print_error("File not found", str(e))
        raise click.Abort()
    except Exception as e:
        print_error("Debug session failed", str(e))
        _logger.exception("Detailed error:")
        raise click.Abort()


class DebugConfig:
    """调试配置"""
    def __init__(
        self,
        breakpoints: List[str],
        step_by_step: bool,
        show_context: bool,
        show_planning: bool,
        log_level: str
    ):
        self.breakpoints = breakpoints
        self.step_by_step = step_by_step
        self.show_context = show_context
        self.show_planning = show_planning
        self.log_level = log_level


def _print_debug_config(config: DebugConfig) -> None:
    """打印调试配置"""
    console.print()
    console.print("[bold cyan]Debug Configuration:[/bold cyan]")
    console.print(f"  • Log level: [yellow]{config.log_level}[/yellow]")
    console.print(f"  • Step-by-step: [yellow]{config.step_by_step}[/yellow]")
    console.print(f"  • Show context: [yellow]{config.show_context}[/yellow]")
    console.print(f"  • Show planning: [yellow]{config.show_planning}[/yellow]")
    
    if config.breakpoints:
        console.print(f"  • Breakpoints: [yellow]{', '.join(config.breakpoints)}[/yellow]")
    else:
        console.print(f"  • Breakpoints: [dim]None[/dim]")
    
    console.print()


def _start_debug_session(loop: any, input_data: str, config: DebugConfig) -> None:
    """
    启动调试会话
    
    Args:
        loop: Agent Loop 实例
        input_data: 输入数据
        config: 调试配置
    """
    print_header("Debug Session Started")
    console.print("[dim]Commands: continue (c), step (s), inspect (i), quit (q)[/dim]")
    print_separator()
    
    # 显示输入
    print_panel(
        input_data,
        title="User Input",
        border_style="cyan"
    )
    
    # 创建调试状态
    debug_state = {
        "iteration": 0,
        "paused": config.step_by_step,
        "should_break": False
    }
    
    try:
        # 如果是单步模式，先暂停
        if config.step_by_step:
            _wait_for_command(debug_state, loop, config)
        
        # 执行agent
        console.print()
        print_info("Starting execution...")
        console.print()
        
        # 注意：这里是简化版本，实际应该hook到loop的执行过程中
        result = asyncio.run(loop.run(input_data))
        
        # 显示结果
        console.print()
        print_separator("═")
        print_header("Execution Completed")
        
        if result.get("success"):
            print_success("Agent execution completed successfully")
        else:
            print_error("Agent execution failed")
            if result.get("error"):
                console.print(f"[red]Error: {result['error']}[/red]")
        
        # 显示统计
        if "statistics" in result:
            console.print()
            console.print("[bold cyan]Statistics:[/bold cyan]")
            stats = result["statistics"]
            
            if "current_plan" in stats:
                plan = stats["current_plan"]
                console.print(f"  • Total tasks: {plan.get('total_tasks', 0)}")
                console.print(f"  • Plan version: {plan.get('plan_version', 1)}")
            
            if "observability" in stats:
                obs = stats["observability"]
                console.print(f"  • Phases: {obs.get('phases', 0)}")
                console.print(f"  • Metrics: {obs.get('metrics', 0)}")
                console.print(f"  • Counters: {obs.get('counters', {})}")
        
        # 显示反思
        if result.get("reflection"):
            console.print()
            console.print("[bold cyan]Reflection:[/bold cyan]")
            print_json(result["reflection"])
    
    except KeyboardInterrupt:
        console.print()
        print_warning("Debug session interrupted by user")
    except Exception as e:
        console.print()
        print_error(f"Execution error: {str(e)}")
        _logger.exception("Detailed error:")


def _wait_for_command(debug_state: Dict, loop: any, config: DebugConfig) -> None:
    """
    等待用户命令
    
    Args:
        debug_state: 调试状态
        loop: Agent Loop实例
        config: 调试配置
    """
    while True:
        console.print()
        console.print("[bold yellow]⏸ Paused[/bold yellow]")
        
        try:
            cmd = console.input("[bold blue]debug>[/bold blue] ").strip().lower()
            
            if cmd in ["c", "continue"]:
                console.print("[green]Continuing...[/green]")
                break
            
            elif cmd in ["s", "step"]:
                console.print("[green]Stepping...[/green]")
                debug_state["should_break"] = True
                break
            
            elif cmd in ["i", "inspect"]:
                _inspect_state(loop, config)
            
            elif cmd in ["h", "help"]:
                _print_debug_help()
            
            elif cmd in ["q", "quit"]:
                console.print("[yellow]Quitting debug session...[/yellow]")
                raise KeyboardInterrupt()
            
            else:
                console.print(f"[red]Unknown command: {cmd}[/red]")
                console.print("[dim]Type 'help' for available commands[/dim]")
        
        except EOFError:
            raise KeyboardInterrupt()


def _inspect_state(loop: any, config: DebugConfig) -> None:
    """
    检查当前状态
    
    Args:
        loop: Agent Loop实例
        config: 调试配置
    """
    console.print()
    console.print("[bold cyan]Current State:[/bold cyan]")
    
    # 显示Loop状态
    console.print(f"  • Loop type: {type(loop).__name__}")
    
    if hasattr(loop, 'stats'):
        console.print(f"  • Total runs: {loop.stats.get('total_runs', 0)}")
    
    # 显示Context状态
    if config.show_context and hasattr(loop, 'context_manager'):
        console.print()
        console.print("[bold cyan]Context State:[/bold cyan]")
        
        try:
            ctx_state = loop.context_manager.get_state()
            console.print(f"  • Rounds: {len(ctx_state.rounds)}")
            console.print(f"  • Total tokens: {ctx_state.total_tokens}")
        except Exception as e:
            console.print(f"  [yellow]Unable to retrieve context: {str(e)}[/yellow]")
    
    # 显示Task Tree状态（如果有）
    if hasattr(loop, 'current_tree') and loop.current_tree:
        console.print()
        console.print("[bold cyan]Task Tree:[/bold cyan]")
        console.print(f"  • Total tasks: {len(loop.current_tree.tasks)}")
        console.print(f"  • Plan version: {loop.current_tree.plan_version}")
        
        # 显示任务状态分布
        from collections import Counter
        status_counts = Counter(task.status for task in loop.current_tree.tasks.values())
        for status, count in status_counts.items():
            console.print(f"  • {status.value}: {count}")


def _print_debug_help() -> None:
    """打印调试帮助"""
    console.print()
    console.print("[bold cyan]Debug Commands:[/bold cyan]")
    console.print("  • [cyan]continue (c)[/cyan] - Continue execution")
    console.print("  • [cyan]step (s)[/cyan] - Execute one step")
    console.print("  • [cyan]inspect (i)[/cyan] - Inspect current state")
    console.print("  • [cyan]help (h)[/cyan] - Show this help")
    console.print("  • [cyan]quit (q)[/cyan] - Quit debug session")
    console.print()


def _print_execution_state(context: any) -> None:
    """
    打印执行状态
    
    Args:
        context: 上下文管理器
    """
    console.print()
    console.print("[bold cyan]Execution State:[/bold cyan]")
    
    try:
        if hasattr(context, 'state'):
            state = context.state
            console.print(f"  • Current round: {len(state.rounds)}")
            console.print(f"  • Total tokens: {state.total_tokens}")
            console.print(f"  • Compression count: {state.compression_count}")
    except Exception as e:
        console.print(f"  [yellow]Unable to retrieve state: {str(e)}[/yellow]")

