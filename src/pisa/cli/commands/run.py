"""
Run Command

职责：
1. 运行 Agent
2. 加载 agent.md 和 context.md
3. 启动 Agent Loop
4. 处理输入输出

使用示例：
```bash
pisa run agent.md --input "Hello"
pisa run agent.md --context context.md
pisa run agent.md --interactive
```
"""

import click
import asyncio
import json
from typing import Optional
from pathlib import Path

from pisa.cli.ui import (
    print_header,
    print_error,
    print_success,
    print_warning,
    print_info,
    print_separator,
    print_agent_execution_summary,
    print_json,
    InteractivePrompt,
    ProgressDisplay,
    display_icon,
    console
)
from pisa.cli.observability_display import display_execution_details
from pisa.startup import initialize_pisa
from pisa.core.definition import parse_agent_definition
from pisa.agents import get_registry_manager
from pisa.utils.logger import get_logger

_logger = get_logger(__name__)


@click.command(name="run", context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("agent_definition", type=click.Path(exists=True))
@click.option(
    "--context",
    "-c",
    type=click.Path(exists=True),
    help="Context definition file (context.md)"
)
@click.option(
    "--input",
    "-i",
    type=str,
    help="Input data for the agent"
)
@click.option(
    "--interactive",
    is_flag=True,
    help="Run in interactive mode"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path"
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output"
)
def run_command(
    agent_definition: str,
    context: Optional[str],
    input: Optional[str],
    interactive: bool,
    output: Optional[str],
    format: str,
    verbose: bool
) -> None:
    """
    Run an agent defined in agent.md
    
    Args:
        agent_definition: Path to agent.md
        context: Path to context.md (optional)
        input: Input data
        interactive: Interactive mode flag
        output: Output file path
        format: Output format
        verbose: Verbose mode
    """
    # 显示icon和标题
    display_icon()
    print_header("PISA Agent Runner", "Execute your AI agent")
    
    try:
        # 1. 初始化PISA系统
        print_info(f"Loading agent: {agent_definition}")
        
        with ProgressDisplay(5, "Initializing PISA system") as progress:
            # Step 1: 初始化系统
            progress.update(1, "Initializing system...")
            manager = initialize_pisa()
            
            # Step 2: 解析agent定义（用于显示信息）
            progress.update(1, "Parsing agent definition...")
            agent_def = parse_agent_definition(Path(agent_definition))
            
            # Step 3: 创建agent实例（create_agent 会重新解析）
            progress.update(1, "Creating agent instance...")
            loop = manager.create_agent(agent_definition)  # 传递路径字符串
            
            # Step 4: 准备输入
            progress.update(1, "Preparing input...")
            input_data = _prepare_input(input, interactive)
            
            # Step 5: 准备就绪
            progress.update(1, "Ready to execute")
        
        print_success(f"Agent '{agent_def.metadata.name}' loaded successfully")
        print_info(f"Loop type: {agent_def.loop_type}")
        
        if verbose:
            console.print(f"[dim]Model: {agent_def.models.default_model}[/dim]")
            console.print(f"[dim]Max iterations: {agent_def.runtime_config.max_iterations}[/dim]")
        
        print_separator()
        
        # 2. 执行agent
        if interactive:
            # 交互模式
            _run_interactive_mode(loop, agent_def)
        else:
            # 单次执行
            result = _run_single_input(loop, input_data, verbose)
            
            # 3. 输出结果
            _handle_output(result, output, format, verbose)
        
    except FileNotFoundError as e:
        print_error("File not found", str(e))
        raise click.Abort()
    except ValueError as e:
        print_error("Invalid configuration", str(e))
        raise click.Abort()
    except Exception as e:
        print_error("Execution failed", str(e))
        if verbose:
            import traceback
            traceback.print_exc()
        raise click.Abort()


def _prepare_input(input_str: Optional[str], interactive: bool) -> str:
    """
    准备输入数据
    
    Args:
        input_str: 输入字符串
        interactive: 是否交互模式
    
    Returns:
        准备好的输入数据
    """
    if input_str:
        return input_str
    
    if not interactive:
        # 非交互模式但没有提供输入，提示用户
        console.print("[yellow]No input provided. Please provide input:[/yellow]")
        return InteractivePrompt.multiline("Enter your input")
    
    return ""


def _run_single_input(loop: any, input_data: str, verbose: bool) -> dict:
    """
    单次输入运行
    
    Args:
        loop: Agent Loop 实例
        input_data: 输入数据
        verbose: 详细模式
        
    Returns:
        运行结果
    """
    print_info("Starting agent execution...")
    print_separator()
    
    # 执行agent
    try:
        result = asyncio.run(loop.run(input_data))
        
        if verbose:
            console.print()
            print_success("Execution completed")
            console.print()
        
        # 转换 LoopState 为字典格式
        if hasattr(result, 'model_dump'):
            result_dict = result.model_dump()
        elif hasattr(result, '__dict__'):
            result_dict = result.__dict__
        else:
            result_dict = {"result": str(result)}
        
        # 添加必要的字段供输出函数使用
        if 'iteration' in result_dict:
            result_dict['iterations'] = result_dict.get('iteration', 0) + 1
        
        # 判断成功状态（多种来源）
        success = False
        
        # 1. 从 metadata 获取
        if 'metadata' in result_dict and isinstance(result_dict['metadata'], dict):
            if 'success' in result_dict['metadata']:
                success = result_dict['metadata']['success']
        
        # 2. 从 observation 获取（如果有）
        if not success and 'observation' in result_dict and result_dict['observation']:
            obs = result_dict['observation']
            if isinstance(obs, dict) and obs.get('success'):
                success = True
            elif hasattr(obs, 'success') and obs.success:
                success = True
        
        # 3. 从 result 字段判断（如果有执行结果）
        if not success and 'result' in result_dict and result_dict['result']:
            res = result_dict['result']
            if isinstance(res, dict):
                if res.get('success'):
                    success = True
                # 检查嵌套的 result
                if 'result' in res and isinstance(res['result'], dict):
                    if res['result'].get('success'):
                        success = True
        
        result_dict['success'] = success
        
        return result_dict
        
    except Exception as e:
        print_error(f"Execution error: {str(e)}")
        raise


def _run_interactive_mode(loop: any, agent_def: any) -> None:
    """
    交互模式运行
    
    Args:
        loop: Agent Loop 实例
        agent_def: Agent定义
    """
    print_info("Starting interactive mode")
    console.print("[dim]Type 'exit' or 'quit' to stop, 'help' for commands[/dim]")
    print_separator()
    
    # 交互循环
    while True:
        try:
            # 获取用户输入
            console.print()
            user_input = console.input("[bold cyan]You:[/bold cyan] ")
            
            if not user_input.strip():
                continue
            
            # 处理特殊命令
            if user_input.lower() in ["exit", "quit", "q"]:
                print_info("Exiting interactive mode...")
                break
            
            if user_input.lower() == "help":
                _print_interactive_help()
                continue
            
            if user_input.lower() == "status":
                _print_agent_status(loop)
                continue
            
            if user_input.lower() == "reset":
                print_info("Resetting agent context...")
                # TODO: 实现context重置
                print_warning("Reset功能待实现")
                continue
            
            # 执行agent
            console.print()
            print_info("Processing...")
            
            try:
                result = asyncio.run(loop.run(user_input))
                
                # 显示结果
                console.print()
                console.print("[bold green]Agent:[/bold green]")
                
                if isinstance(result, dict):
                    if "result" in result:
                        console.print(result["result"])
                    else:
                        print_json(result)
                else:
                    console.print(str(result))
                
            except Exception as e:
                console.print()
                print_error(f"Execution failed: {str(e)}")
        
        except KeyboardInterrupt:
            console.print()
            print_info("Interrupted by user")
            break
        
        except EOFError:
            console.print()
            print_info("EOF received, exiting...")
            break


def _handle_output(result: dict, output_path: Optional[str], format: str, verbose: bool = False) -> None:
    """
    处理输出结果
    
    Args:
        result: 执行结果
        output_path: 输出文件路径
        format: 输出格式
        verbose: 是否显示详细信息
    """
    # 显示执行摘要
    if format == "text":
        print_agent_execution_summary(result)
        # 显示结构化的详细信息
        display_execution_details(result, verbose=verbose)
    elif format == "json":
        print_json(result)
    
    # 保存到文件
    if output_path:
        try:
            output_file = Path(output_path)
            
            if format == "json":
                with output_file.open("w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
            else:
                with output_file.open("w", encoding="utf-8") as f:
                    f.write(str(result))
            
            print_success(f"Results saved to: {output_path}")
        
        except Exception as e:
            print_error(f"Failed to save output: {str(e)}")


def _print_interactive_help() -> None:
    """打印交互模式帮助"""
    console.print()
    console.print("[bold cyan]Interactive Mode Commands:[/bold cyan]")
    console.print("  • [cyan]exit, quit, q[/cyan] - Exit interactive mode")
    console.print("  • [cyan]help[/cyan] - Show this help message")
    console.print("  • [cyan]status[/cyan] - Show agent status")
    console.print("  • [cyan]reset[/cyan] - Reset agent context")
    console.print()
    console.print("[dim]Just type your message to interact with the agent[/dim]")


def _print_agent_status(loop: any) -> None:
    """打印agent状态"""
    console.print()
    console.print("[bold cyan]Agent Status:[/bold cyan]")
    
    # 尝试获取状态信息
    try:
        if hasattr(loop, 'stats'):
            console.print(f"  • Total runs: {loop.stats.get('total_runs', 0)}")
            console.print(f"  • Successful runs: {loop.stats.get('successful_runs', 0)}")
            console.print(f"  • Failed runs: {loop.stats.get('failed_runs', 0)}")
        
        if hasattr(loop, 'context_manager'):
            console.print(f"  • Context rounds: {len(loop.context_manager.state.rounds)}")
        
        console.print(f"  • Loop type: {type(loop).__name__}")
    
    except Exception as e:
        console.print(f"  [yellow]Unable to retrieve status: {str(e)}[/yellow]")
