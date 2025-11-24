"""
Enhanced Logger System with Rich Observability

职责：
1. 提供多层次的日志系统
2. 支持 Rich 可视化输出
3. 集成 colorlog 进行彩色日志
4. 提供结构化日志
5. 支持不同类型的日志通道

日志类型：
- [SYSTEM] 系统日志
- [CONTEXT] 上下文变化
- [PLANNING] 任务树
- [CAPABILITY] 能力调用
- [TEMPORAL] Workflow 事件
- [LOOP] Agent Loop 数据流
- [OBSERVE] 观察信息
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional, List
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text
from rich.logging import RichHandler
from rich import box
import colorlog


# 全局 Console 实例
console = Console()


class LogLevel:
    """日志级别常量"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogChannel:
    """日志通道常量"""
    SYSTEM = "SYSTEM"
    CONTEXT = "CONTEXT"
    PLANNING = "PLANNING"
    CAPABILITY = "CAPABILITY"
    TEMPORAL = "TEMPORAL"
    LOOP = "LOOP"
    OBSERVE = "OBSERVE"


class PISALogger:
    """
    PISA 增强日志系统
    
    提供多通道、可视化的日志记录
    """
    
    def __init__(
        self,
        name: str = "pisa",
        level: str = "INFO",
        log_file: Optional[Path] = None,
        enable_rich: bool = True
    ):
        """
        初始化日志系统
        
        Args:
            name: 日志器名称
            level: 日志级别
            log_file: 日志文件路径
            enable_rich: 是否启用 Rich 输出
        """
        self.name = name
        self.level = level
        self.log_file = log_file
        self.enable_rich = enable_rich
        self.console = console
        
        # 创建基础 logger
        self.logger = self._setup_system_logger()
        
        # 创建彩色 logger（用于 capability 调用）
        self.color_logger = self._setup_color_logger()
        
    def _setup_system_logger(self) -> logging.Logger:
        """设置系统日志器（使用 Rich）"""
        logger = logging.getLogger(f"{self.name}.system")
        logger.setLevel(getattr(logging, self.level))
        logger.handlers.clear()
        
        if self.enable_rich:
            # Rich handler for console
            rich_handler = RichHandler(
                console=self.console,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                show_time=True,
                show_path=True
            )
            rich_handler.setLevel(getattr(logging, self.level))
            logger.addHandler(rich_handler)
        
        # File handler
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def _setup_color_logger(self) -> logging.Logger:
        """设置彩色日志器（用于 capability 调用）"""
        logger = logging.getLogger(f"{self.name}.capability")
        logger.setLevel(getattr(logging, self.level))
        logger.handlers.clear()
        
        # Colorlog handler
        handler = colorlog.StreamHandler()
        handler.setFormatter(
            colorlog.ColoredFormatter(
                '%(log_color)s[%(levelname)s]%(reset)s %(message)s',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'bold_red',
                }
            )
        )
        logger.addHandler(handler)
        
        return logger
    
    # ==================== System Logs ====================
    
    def system(self, message: str, level: str = "INFO", **kwargs) -> None:
        """
        系统日志
        
        Args:
            message: 日志消息
            level: 日志级别
            **kwargs: 额外的上下文信息
        """
        log_method = getattr(self.logger, level.lower())
        if kwargs:
            message = f"{message} | {self._format_kwargs(kwargs)}"
        log_method(f"[SYSTEM] {message}")
    
    def debug(self, message: str, **kwargs) -> None:
        """DEBUG 级别系统日志"""
        self.system(message, "DEBUG", **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """INFO 级别系统日志"""
        self.system(message, "INFO", **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """WARNING 级别系统日志"""
        self.system(message, "WARNING", **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """ERROR 级别系统日志"""
        self.system(message, "ERROR", **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """CRITICAL 级别系统日志"""
        self.system(message, "CRITICAL", **kwargs)
    
    # ==================== Context Logs ====================
    
    def context_update(
        self,
        action: str,
        tokens_added: int = 0,
        total_tokens: int = 0,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        上下文变化日志（使用 Rich Panel）
        
        Args:
            action: 操作描述
            tokens_added: 增加的 token 数量
            total_tokens: 总 token 数量
            details: 详细信息
        """
        if not self.enable_rich:
            self.logger.info(f"[CONTEXT] {action} | Tokens: +{tokens_added} → Total: {total_tokens}")
            return
        
        # 构建内容
        content = Text()
        content.append(f"{action}\n", style="bold cyan")
        content.append(f"Tokens: ", style="dim")
        content.append(f"+{tokens_added}", style="green")
        content.append(f" → Total: ", style="dim")
        content.append(f"{total_tokens}", style="yellow")
        
        if details:
            content.append("\n\nDetails:\n", style="dim")
            for key, value in details.items():
                content.append(f"  • {key}: ", style="dim")
                content.append(f"{value}\n", style="white")
        
        panel = Panel(
            content,
            title="[bold magenta]CONTEXT UPDATE[/bold magenta]",
            border_style="magenta",
            box=box.ROUNDED
        )
        self.console.print(panel)
    
    def context_compress(
        self,
        before_tokens: int,
        after_tokens: int,
        compression_ratio: float
    ) -> None:
        """
        上下文压缩日志
        
        Args:
            before_tokens: 压缩前 token 数
            after_tokens: 压缩后 token 数
            compression_ratio: 压缩比例
        """
        if not self.enable_rich:
            self.logger.info(
                f"[CONTEXT] Compressed | {before_tokens} → {after_tokens} "
                f"({compression_ratio:.1%} reduction)"
            )
            return
        
        content = Text()
        content.append("Context Compression\n", style="bold yellow")
        content.append(f"Before: {before_tokens} tokens\n", style="dim")
        content.append(f"After: {after_tokens} tokens\n", style="green")
        content.append(f"Reduction: {compression_ratio:.1%}", style="bold green")
        
        panel = Panel(
            content,
            title="[bold yellow]⚡ COMPRESSION[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED
        )
        self.console.print(panel)
    
    # ==================== Planning Logs ====================
    
    def planning_tree(
        self,
        tasks: List[Dict[str, Any]],
        title: str = "Task Tree"
    ) -> None:
        """
        任务树日志（使用 Rich Tree）
        
        Args:
            tasks: 任务列表，每个任务包含 name, status, children
            title: 树标题
        """
        if not self.enable_rich:
            self.logger.info(f"[PLANNING] {title}")
            for task in tasks:
                self.logger.info(f"  - {task.get('name')} [{task.get('status')}]")
            return
        
        tree = Tree(f"[bold blue]{title}[/bold blue]")
        
        def add_task_to_tree(parent_node, task_data):
            """递归添加任务到树"""
            status_icon = self._get_status_icon(task_data.get('status', 'pending'))
            task_name = task_data.get('name', 'Unknown')
            
            node = parent_node.add(f"{status_icon} {task_name}")
            
            # 添加子任务
            for child in task_data.get('children', []):
                add_task_to_tree(node, child)
        
        for task in tasks:
            add_task_to_tree(tree, task)
        
        self.console.print(tree)
    
    def planning_update(self, message: str, task_count: int = 0) -> None:
        """
        规划更新日志
        
        Args:
            message: 更新消息
            task_count: 任务数量
        """
        if not self.enable_rich:
            self.logger.info(f"[PLANNING] {message}")
            return
        
        text = Text()
        text.append("📋 ", style="bold blue")
        text.append(message, style="cyan")
        if task_count > 0:
            text.append(f" ({task_count} tasks)", style="dim")
        
        self.console.print(text)
    
    # ==================== Capability Logs ====================
    
    def capability_call(
        self,
        name: str,
        args: Dict[str, Any],
        result: Optional[Any] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """
        能力调用日志（使用 colorlog）
        
        Args:
            name: 能力名称
            args: 调用参数
            result: 执行结果
            duration_ms: 执行时间（毫秒）
            success: 是否成功
            error: 错误信息
        """
        # 格式化参数
        args_str = self._format_args(args)
        
        if success:
            status_icon = "✓"
            status_text = "Success"
            level = "INFO"
        else:
            status_icon = "✗"
            status_text = f"Failed: {error}"
            level = "ERROR"
        
        duration_str = f" ({duration_ms:.0f}ms)" if duration_ms else ""
        
        message = f"[CAPABILITY] ⚙️  {name}({args_str}) → {status_icon} {status_text}{duration_str}"
        
        if self.enable_rich:
            text = Text()
            text.append("⚙️  ", style="bold cyan")
            text.append(f"{name}", style="bold yellow")
            text.append(f"({args_str})", style="dim")
            text.append(" → ", style="dim")
            
            if success:
                text.append(f"{status_icon} {status_text}", style="bold green")
            else:
                text.append(f"{status_icon} {status_text}", style="bold red")
            
            if duration_ms:
                text.append(f" ({duration_ms:.0f}ms)", style="dim cyan")
            
            self.console.print(text)
        else:
            log_method = getattr(self.color_logger, level.lower())
            log_method(message)
    
    # ==================== Loop Logs ====================
    
    def loop_start(self, loop_type: str, agent_name: str) -> None:
        """
        Loop 启动日志
        
        Args:
            loop_type: Loop 类型
            agent_name: Agent 名称
        """
        if not self.enable_rich:
            self.logger.info(f"[LOOP] Started {loop_type} loop for {agent_name}")
            return
        
        panel = Panel(
            f"[bold cyan]Loop Type:[/bold cyan] {loop_type}\n"
            f"[bold cyan]Agent:[/bold cyan] {agent_name}",
            title="[bold green]🔄 LOOP START[/bold green]",
            border_style="green",
            box=box.DOUBLE
        )
        self.console.print(panel)
    
    def loop_step(
        self,
        iteration: int,
        action: str,
        status: str = "running",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Loop 步骤日志
        
        Args:
            iteration: 迭代次数
            action: 动作描述
            status: 状态
            details: 详细信息
        """
        status_icon = {
            'running': '⟳',
            'success': '✓',
            'failed': '✗',
            'pending': '⋯'
        }.get(status, '•')
        
        if not self.enable_rich:
            self.logger.info(f"[LOOP] Step {iteration}: {action} [{status_icon}]")
            return
        
        text = Text()
        text.append(f"Step {iteration}: ", style="bold blue")
        text.append(f"{status_icon} ", style="yellow")
        text.append(action, style="white")
        
        if details:
            text.append(f" | {self._format_kwargs(details)}", style="dim")
        
        self.console.print(text)
    
    def loop_end(self, total_iterations: int, success: bool, result: Any = None) -> None:
        """
        Loop 结束日志
        
        Args:
            total_iterations: 总迭代次数
            success: 是否成功
            result: 结果
        """
        if not self.enable_rich:
            status = "Success" if success else "Failed"
            self.logger.info(f"[LOOP] Ended after {total_iterations} iterations | {status}")
            return
        
        status_color = "green" if success else "red"
        status_text = "SUCCESS" if success else "FAILED"
        
        panel = Panel(
            f"[bold cyan]Total Iterations:[/bold cyan] {total_iterations}\n"
            f"[bold cyan]Status:[/bold cyan] [bold {status_color}]{status_text}[/bold {status_color}]",
            title=f"[bold {status_color}]🏁 LOOP END[/bold {status_color}]",
            border_style=status_color,
            box=box.DOUBLE
        )
        self.console.print(panel)
    
    # ==================== Observe Logs ====================
    
    def observe(
        self,
        observation_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        观察日志
        
        Args:
            observation_type: 观察类型
            content: 观察内容
            metadata: 元数据
        """
        if not self.enable_rich:
            self.logger.info(f"[OBSERVE] {observation_type}: {content}")
            return
        
        text = Text()
        text.append("👁️  ", style="bold magenta")
        text.append(f"[{observation_type}] ", style="bold magenta")
        text.append(content, style="white")
        
        if metadata:
            text.append(f"\n  Metadata: {self._format_kwargs(metadata)}", style="dim")
        
        self.console.print(text)
    
    # ==================== Temporal Logs ====================
    
    def temporal_workflow_start(
        self,
        workflow_type: str,
        workflow_id: str,
        run_id: str
    ) -> None:
        """
        Temporal Workflow 启动日志
        
        Args:
            workflow_type: Workflow 类型
            workflow_id: Workflow ID
            run_id: Run ID
        """
        self.logger.info(
            f"[TEMPORAL] Workflow {workflow_type} started | "
            f"workflow_id={workflow_id} | run_id={run_id}"
        )
    
    def temporal_activity(
        self,
        activity_name: str,
        status: str,
        duration_ms: Optional[float] = None
    ) -> None:
        """
        Temporal Activity 日志
        
        Args:
            activity_name: Activity 名称
            status: 状态
            duration_ms: 执行时间
        """
        duration_str = f" ({duration_ms:.0f}ms)" if duration_ms else ""
        self.logger.info(f"[TEMPORAL] Activity {activity_name} | {status}{duration_str}")
    
    # ==================== Config Display ====================
    
    def display_config(self, config: Dict[str, Any], title: str = "Configuration") -> None:
        """
        显示结构化配置（使用 Rich Table）
        
        Args:
            config: 配置字典
            title: 标题
        """
        if not self.enable_rich:
            self.logger.info(f"[CONFIG] {title}")
            for key, value in config.items():
                self.logger.info(f"  {key}: {value}")
            return
        
        table = Table(title=f"[bold blue]{title}[/bold blue]", box=box.ROUNDED)
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")
        
        def add_config_rows(cfg, prefix=""):
            """递归添加配置行"""
            for key, value in cfg.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    add_config_rows(value, full_key)
                else:
                    table.add_row(full_key, str(value))
        
        add_config_rows(config)
        self.console.print(table)
    
    # ==================== Helper Methods ====================
    
    def _format_kwargs(self, kwargs: Dict[str, Any]) -> str:
        """格式化关键字参数"""
        return " | ".join(f"{k}={v}" for k, v in kwargs.items())
    
    def _format_args(self, args: Dict[str, Any]) -> str:
        """格式化函数参数"""
        if not args:
            return ""
        return ", ".join(f"{k}={self._truncate_value(v)}" for k, v in args.items())
    
    def _truncate_value(self, value: Any, max_len: int = 50) -> str:
        """截断长值"""
        str_val = str(value)
        if len(str_val) > max_len:
            return f"{str_val[:max_len]}..."
        return str_val
    
    def _get_status_icon(self, status: str) -> str:
        """获取状态图标"""
        icons = {
            'pending': '⋯',
            'in_progress': '⟳',
            'completed': '✓',
            'failed': '✗',
            'cancelled': '⊗'
        }
        return icons.get(status, '•')


# ==================== Global Logger Instance ====================

_global_logger: Optional[PISALogger] = None


def get_logger(
    name: str = "pisa",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_rich: bool = True
) -> PISALogger:
    """
    获取全局日志器实例
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径
        enable_rich: 是否启用 Rich 输出
        
    Returns:
        PISALogger 实例
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = PISALogger(name, level, log_file, enable_rich)
    return _global_logger


def setup_logger(
    name: str = "pisa",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_rich: bool = True
) -> PISALogger:
    """
    设置全局日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径
        enable_rich: 是否启用 Rich 输出
        
    Returns:
        PISALogger 实例
    """
    global _global_logger
    _global_logger = PISALogger(name, level, log_file, enable_rich)
    return _global_logger
