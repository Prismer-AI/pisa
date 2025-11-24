"""
CLI UI Components

职责：
1. 提供 Rich TUI 组件
2. 美化命令行输出
3. 提供进度条和状态显示
4. 交互式界面元素

使用 Rich 库提供：
- 表格
- 进度条
- 语法高亮
- 面板和布局
"""

import json
from typing import Any, List, Optional, Dict
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.json import JSON
from rich import box


# 全局 Console 实例
console = Console()


def display_icon() -> None:
    """显示彩色的 PISA icon"""
    from pathlib import Path
    from rich.text import Text
    
    # 获取icon文件路径
    icon_path = Path(__file__).parent.parent / "icon"
    if icon_path.exists():
        icon_content = icon_path.read_text(encoding="utf-8")
        lines = icon_content.split("\n")
        for line in lines:
            if not line.strip():
                console.print()
                continue
            text = Text(line)
            text_start = line.find("▓")
            if text_start == -1:
                text_start = len(line)
            for i, char in enumerate(line):
                if char.isspace():
                    continue
                elif i < text_start:
                    text.stylize("bright_cyan", i, i + 1)
                else:
                    text.stylize("dim white", i, i + 1)
            console.print(text)
    else:
        console.print("[yellow]Warning: icon file not found[/yellow]")
    console.print()  # 添加一个空行


def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """
    打印标题
    
    Args:
        title: 标题文本
        subtitle: 副标题
    """
    console.print()
    console.print(f"[bold cyan]{title}[/bold cyan]")
    if subtitle:
        console.print(f"[dim]{subtitle}[/dim]")
    console.print()


def print_table(
    headers: List[str],
    rows: List[List[str]],
    title: Optional[str] = None
) -> None:
    """
    打印表格
    
    Args:
        headers: 表头
        rows: 数据行
        title: 表格标题
    """
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    # 添加列
    for header in headers:
        table.add_column(header)
    
    # 添加行
    for row in rows:
        table.add_row(*row)
    
    console.print(table)


def print_panel(
    content: str,
    title: Optional[str] = None,
    border_style: str = "blue"
) -> None:
    """
    打印面板
    
    Args:
        content: 内容
        title: 标题
        border_style: 边框样式
    """
    panel = Panel(
        content,
        title=title,
        border_style=border_style,
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(panel)


def print_code(
    code: str,
    language: str = "python",
    line_numbers: bool = True
) -> None:
    """
    打印代码
    
    Args:
        code: 代码字符串
        language: 语言类型
        line_numbers: 是否显示行号
    """
    syntax = Syntax(
        code,
        language,
        theme="monokai",
        line_numbers=line_numbers,
        word_wrap=True
    )
    console.print(syntax)


def print_json(data: Any) -> None:
    """
    打印 JSON
    
    Args:
        data: 数据对象
    """
    if isinstance(data, str):
        # 如果是字符串，尝试解析为JSON
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            console.print("[yellow]Invalid JSON string[/yellow]")
            return
    
    json_obj = JSON(json.dumps(data, indent=2))
    console.print(json_obj)


def print_error(message: str, details: Optional[str] = None) -> None:
    """
    打印错误信息
    
    Args:
        message: 错误消息
        details: 详细信息
    """
    console.print(f"[bold red]✗ Error:[/bold red] {message}")
    if details:
        console.print(f"[dim]{details}[/dim]")


def print_success(message: str) -> None:
    """
    打印成功信息
    
    Args:
        message: 成功消息
    """
    console.print(f"[bold green]✓ Success:[/bold green] {message}")


def print_warning(message: str) -> None:
    """
    打印警告信息
    
    Args:
        message: 警告消息
    """
    console.print(f"[bold yellow]⚠ Warning:[/bold yellow] {message}")


def print_info(message: str) -> None:
    """
    打印信息
    
    Args:
        message: 信息消息
    """
    console.print(f"[bold blue]ℹ Info:[/bold blue] {message}")


def print_separator(char: str = "─", style: str = "dim") -> None:
    """
    打印分隔线
    
    Args:
        char: 分隔符字符
        style: 样式
    """
    width = console.width
    console.print(f"[{style}]{char * width}[/{style}]")


class ProgressDisplay:
    """
    进度显示器
    
    显示任务执行进度
    """
    
    def __init__(self, total: int, description: str = "Processing"):
        """
        初始化进度显示器
        
        Args:
            total: 总步骤数
            description: 描述文本
        """
        self.total = total
        self.description = description
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        )
        self.task_id = None
    
    def start(self) -> None:
        """开始显示进度"""
        self.progress.start()
        self.task_id = self.progress.add_task(
            self.description,
            total=self.total
        )
    
    def update(self, step: int = 1, message: Optional[str] = None) -> None:
        """
        更新进度
        
        Args:
            step: 前进步数
            message: 状态消息
        """
        if self.task_id is not None:
            self.progress.update(
                self.task_id,
                advance=step,
                description=message or self.description
            )
    
    def complete(self, message: Optional[str] = None) -> None:
        """
        完成进度
        
        Args:
            message: 完成消息
        """
        if self.task_id is not None:
            self.progress.update(
                self.task_id,
                completed=self.total,
                description=message or self.description
            )
        self.progress.stop()
    
    def __enter__(self):
        """Context manager入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager退出"""
        self.complete()


class InteractivePrompt:
    """
    交互式提示
    
    提供交互式输入界面
    """
    
    @staticmethod
    def ask(
        question: str,
        default: Optional[str] = None,
        choices: Optional[List[str]] = None
    ) -> str:
        """
        询问用户输入
        
        Args:
            question: 问题文本
            default: 默认值
            choices: 选项列表
            
        Returns:
            用户输入
        """
        if choices:
            # 显示选项
            console.print(f"[bold blue]{question}[/bold blue]")
            for i, choice in enumerate(choices, 1):
                console.print(f"  {i}. {choice}")
            
            # 获取用户选择
            while True:
                try:
                    response = Prompt.ask(
                        "Enter choice number",
                        default=str(default) if default else None
                    )
                    idx = int(response) - 1
                    if 0 <= idx < len(choices):
                        return choices[idx]
                    else:
                        console.print("[red]Invalid choice, please try again[/red]")
                except ValueError:
                    console.print("[red]Please enter a valid number[/red]")
        else:
            return Prompt.ask(question, default=default)
    
    @staticmethod
    def confirm(question: str, default: bool = False) -> bool:
        """
        确认提示
        
        Args:
            question: 问题文本
            default: 默认值
            
        Returns:
            用户确认结果
        """
        return Confirm.ask(question, default=default)
    
    @staticmethod
    def multiline(prompt: str = "Enter text (Ctrl+D to finish)") -> str:
        """
        多行输入
        
        Args:
            prompt: 提示文本
            
        Returns:
            用户输入的多行文本
        """
        console.print(f"[bold blue]{prompt}[/bold blue]")
        lines = []
        try:
            while True:
                line = console.input("[dim]> [/dim]")
                lines.append(line)
        except EOFError:
            pass
        return "\n".join(lines)


def print_validation_results(results: Dict[str, Any]) -> None:
    """
    打印验证结果
    
    Args:
        results: 验证结果字典
            {
                "passed": int,
                "failed": int,
                "warnings": int,
                "errors": List[str],
                "warnings_list": List[str]
            }
    """
    console.print()
    print_header("Validation Results")
    
    # 统计信息
    passed = results.get("passed", 0)
    failed = results.get("failed", 0)
    warnings = results.get("warnings", 0)
    
    # 显示统计
    console.print(f"[green]✓ {passed} checks passed[/green]")
    if failed > 0:
        console.print(f"[red]✗ {failed} errors found[/red]")
    if warnings > 0:
        console.print(f"[yellow]⚠ {warnings} warnings[/yellow]")
    
    console.print()
    
    # 显示错误详情
    if results.get("errors"):
        console.print("[bold red]Errors:[/bold red]")
        for error in results["errors"]:
            console.print(f"  • {error}")
        console.print()
    
    # 显示警告详情
    if results.get("warnings_list"):
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for warning in results["warnings_list"]:
            console.print(f"  • {warning}")
        console.print()
    
    # 最终判断
    if failed > 0:
        print_error("Validation failed. Please fix the errors above.")
    elif warnings > 0:
        print_warning("Validation passed with warnings.")
    else:
        print_success("All validations passed!")


def print_agent_execution_summary(result: Dict[str, Any]) -> None:
    """
    打印Agent执行摘要
    
    Args:
        result: 执行结果字典
    """
    console.print()
    print_separator("═")
    print_header("Agent Execution Summary")
    
    # 基本信息
    success = result.get("success", False)
    iterations = result.get("iterations", 0)
    
    if success:
        console.print(f"[bold green]Status:[/bold green] Completed Successfully ✓")
    else:
        console.print(f"[bold red]Status:[/bold red] Failed ✗")
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
    
    console.print(f"[bold cyan]Iterations:[/bold cyan] {iterations}")
    
    # 统计信息
    if "statistics" in result:
        stats = result["statistics"]
        console.print()
        console.print("[bold cyan]Statistics:[/bold cyan]")
        
        if "current_plan" in stats:
            plan = stats["current_plan"]
            console.print(f"  • Total tasks: {plan.get('total_tasks', 0)}")
            console.print(f"  • Plan version: {plan.get('plan_version', 1)}")
        
        if "observability" in stats:
            obs = stats["observability"]
            console.print(f"  • Phases tracked: {obs.get('phases', 0)}")
            console.print(f"  • Metrics collected: {obs.get('metrics', 0)}")
    
    # 反思结果
    if result.get("reflection"):
        console.print()
        console.print("[bold cyan]Reflection:[/bold cyan]")
        reflection = result["reflection"]
        if isinstance(reflection, dict):
            if "insights" in reflection:
                for insight in reflection["insights"][:3]:  # 显示前3条
                    console.print(f"  • {insight}")
        else:
            console.print(f"  {str(reflection)[:200]}...")
    
    print_separator("═")
    console.print()
