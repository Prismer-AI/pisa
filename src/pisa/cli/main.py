"""
PISA CLI System

整合的命令行接口，提供丰富的可观测性和交互体验
"""

import shutil
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich import box

# 导入命令
from .commands.run import run_command
from .commands.validate import validate_command
from .commands.list_capabilities import list_capabilities_command
from .commands.debug import debug_command
from .commands.init import init_command

# 导入日志系统
from pisa.utils.logger import setup_logger, get_logger


# 全局 Console 实例
console = Console()


def display_icon(console: Console) -> None:
    """显示彩色的 PISA icon"""
    icon_path = Path(__file__).parent.parent / "icon"
    if icon_path.exists():
        icon_content = icon_path.read_text(encoding="utf-8")
        # 使用 rich 的 Text 来添加颜色
        lines = icon_content.split("\n")
        for line in lines:
            if not line.strip():  # 跳过空行
                console.print()
                continue
            text = Text(line)
            
            # 找到第一个▓字符的位置，作为logo和文字的分界点
            # 如果找不到▓，则整行都是logo部分
            text_start = line.find("▓")
            if text_start == -1:
                # 整行都是logo部分
                text_start = len(line)
            
            # 为不同的字符添加不同的颜色
            # logo部分（▓之前）用青色，文字部分（▓之后）用灰色
            for i, char in enumerate(line):
                if char.isspace():
                    # 空格保持原样
                    continue
                elif i < text_start:
                    # logo部分：高亮青色（使用 bright_cyan）
                    text.stylize("bright_cyan", i, i + 1)
                else:
                    # 文字部分：灰色（使用 dim white 或 grey）
                    text.stylize("dim white", i, i + 1)
            
            console.print(text)
    else:
        console.print("[yellow]Warning: icon file not found[/yellow]")


def _check_environment() -> None:
    """检查环境配置"""
    from pathlib import Path
    import os
    
    console.print()
    console.print("[bold cyan]Environment Check[/bold cyan]")
    console.print()
    
    issues = []
    warnings = []
    
    # 1. 检查 .env 文件
    env_file = Path.cwd() / ".env"
    if not env_file.exists():
        warnings.append("No .env file found in current directory")
        console.print("  [yellow]⚠[/yellow] .env file not found")
    else:
        console.print("  [green]✓[/green] .env file found")
        
        # 检查关键配置
        required_vars = [
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            warnings.append(f"Missing environment variables: {', '.join(missing_vars)}")
            console.print(f"  [yellow]⚠[/yellow] Missing variables: {', '.join(missing_vars)}")
        else:
            console.print("  [green]✓[/green] Required environment variables set")
    
    # 2. 检查 .prismer 目录
    prismer_dir = Path.cwd() / ".prismer"
    if prismer_dir.exists():
        console.print("  [green]✓[/green] .prismer directory found")
    else:
        console.print("  [dim]ℹ[/dim] .prismer directory not initialized (run 'pisa init')")
    
    # 3. 检查 Python 版本
    import sys
    python_version = sys.version_info
    if python_version.major >= 3 and python_version.minor >= 9:
        console.print(f"  [green]✓[/green] Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        issues.append(f"Python 3.9+ required, found {python_version.major}.{python_version.minor}")
        console.print(f"  [red]✗[/red] Python version too old")
    
    console.print()
    
    # 显示警告和错误
    if issues:
        console.print("[bold red]Critical Issues:[/bold red]")
        for issue in issues:
            console.print(f"  • {issue}")
        console.print()
    
    if warnings:
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for warning in warnings:
            console.print(f"  • {warning}")
        console.print()
        console.print("[dim]You can continue, but some features may not work correctly.[/dim]")
        console.print()


def display_welcome() -> None:
    """显示欢迎信息（仅面板，不包含icon）"""
    welcome_text = (
        "[bold cyan]PISA Framework[/bold cyan] - "
        "[dim]Policy-driven Intelligent System Architecture[/dim]\n\n"
        "[yellow]Version:[/yellow] 2.0.0\n"
        "[yellow]Documentation:[/yellow] https://pisa.readthedocs.io\n"
    )
    
    panel = Panel(
        welcome_text,
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(panel)
    console.print()


def init_project(console: Console) -> None:
    """初始化项目：创建 .prismer 文件夹并复制 template.md"""
    # 获取当前工作目录
    cwd = Path.cwd()
    prismer_dir = cwd / ".prismer"
    
    # 创建 .prismer 文件夹
    if not prismer_dir.exists():
        prismer_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created directory: {prismer_dir}")
    else:
        console.print(f"[yellow]Directory already exists: {prismer_dir}[/yellow]")
    
    # 复制 template.md（如果存在）
    template_path = Path(__file__).parent.parent / "agents" / "proto" / "template.md"
    target_path = prismer_dir / "template.md"
    
    if template_path.exists():
        shutil.copy2(template_path, target_path)
        console.print(f"[green]✓[/green] Copied template.md to: {target_path}")
    else:
        console.print(f"[yellow]⚠[/yellow] Template file not found: {template_path}")
        console.print(f"[dim]Continuing without template...[/dim]")
    
    # 创建示例目录结构
    examples_dir = prismer_dir / "examples"
    if not examples_dir.exists():
        examples_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created examples directory: {examples_dir}")
    
    console.print()
    console.print("[bold green]✓ Project initialized successfully![/bold green]")
    console.print()
    console.print("[dim]Next steps:[/dim]")
    console.print("  1. Create your agent definition in [cyan]agent.md[/cyan]")
    console.print("  2. Validate it with: [cyan]pisa validate agent.md[/cyan]")
    console.print("  3. Run your agent with: [cyan]pisa run agent.md[/cyan]")
    console.print()


# Note: init_project function moved to commands/init.py for better organization


@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.option('--version', '-v', is_flag=True, help='Show version')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.pass_context
def cli(ctx, version, debug):
    """
    PISA - Policy-driven Intelligent System Architecture
    
    A framework for building and orchestrating AI agents.
    """
    # 设置日志系统
    log_level = "DEBUG" if debug else "INFO"
    setup_logger(level=log_level, enable_rich=True)
    
    if version:
        console.print("[bold cyan]PISA Framework[/bold cyan] version [yellow]2.0.0[/yellow]")
        return
    
    # 如果没有子命令，显示欢迎信息
    if ctx.invoked_subcommand is None:
        # 环境检查
        _check_environment()
        
        # 显示欢迎面板（不包含icon，因为已经在上面显示了）
        welcome_text = (
            "[bold cyan]PISA Framework[/bold cyan] - "
            "[dim]Policy-driven Intelligent System Architecture[/dim]\n\n"
            "[yellow]Version:[/yellow] 2.0.0\n"
            "[yellow]Documentation:[/yellow] https://pisa.readthedocs.io\n"
        )
        
        panel = Panel(
            welcome_text,
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        console.print(panel)
        console.print()
        
        # 询问是否初始化项目
        console.print("[bold blue]Initialize PISA project?[/bold blue]")
        response = console.input("[dim](y/n):[/dim] ")
        
        if response.lower() in ['y', 'yes']:
            init_project(console)
        else:
            console.print("[yellow]Skipped initialization[/yellow]")
            console.print("[dim]Run 'pisa -h' or 'pisa --help' to see available commands[/dim]")


# 注册命令
cli.add_command(run_command, name="run")
cli.add_command(validate_command, name="validate")
cli.add_command(list_capabilities_command, name="list")
cli.add_command(debug_command, name="debug")
cli.add_command(init_command, name="init")


def main() -> None:
    """主函数"""
    # 总是先显示icon（除了子命令已经显示的情况）
    # 检查是否是help请求或者是主命令
    if len(sys.argv) == 1 or (len(sys.argv) >= 2 and sys.argv[1] in ['-h', '--help', '-v', '--version']):
        display_icon(console)
        console.print()
    
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger = get_logger()
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        console.print(f"\n[red]✗ Error:[/red] {e}")
        sys.exit(1)


def run() -> None:
    """CLI 入口点"""
    main()


if __name__ == "__main__":
    run()
