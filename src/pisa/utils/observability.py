"""
Observability Manager

统一的可观测性管理系统，集成日志、指标、追踪、可视化。

参考:
- https://github.com/Textualize/rich
- PISA2.md 可观测性设计
"""

from typing import Any, Dict, Optional, List, Callable
from contextlib import contextmanager
import time
from datetime import datetime
from dataclasses import dataclass, field

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn
)
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.layout import Layout
from rich.text import Text
from rich import box
from rich.columns import Columns


console = Console()


@dataclass
class PhaseInfo:
    """执行阶段信息"""
    name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "running"  # running, completed, failed
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """获取持续时间（秒）"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def duration_ms(self) -> float:
        """获取持续时间（毫秒）"""
        return self.duration * 1000


class ObservabilityManager:
    """
    统一可观测性管理器
    
    功能:
    1. 实时进度追踪（多阶段）
    2. 性能指标收集
    3. 执行流程可视化
    4. 结构化日志输出
    5. 实时仪表板
    6. 数据流追踪
    
    设计目标:
    - 统一接口：所有模块使用相同的可观测性接口
    - 分层展示：支持不同级别的详细程度
    - 实时更新：Live Dashboard 实时显示状态
    - 易于集成：通过 BaseModule 自动集成
    """
    
    def __init__(
        self,
        module_name: str = "System",
        enable_live_dashboard: bool = False,
        enable_detailed_logging: bool = True
    ):
        """
        初始化可观测性管理器
        
        Args:
            module_name: 模块名称
            enable_live_dashboard: 是否启用实时仪表板
            enable_detailed_logging: 是否启用详细日志
        """
        self.module_name = module_name
        self.enable_live_dashboard = enable_live_dashboard
        self.enable_detailed_logging = enable_detailed_logging
        
        # 阶段追踪
        self.phases: List[PhaseInfo] = []
        self.current_phase: Optional[PhaseInfo] = None
        
        # 指标收集
        self.metrics: Dict[str, List[float]] = {}
        self.counters: Dict[str, int] = {}
        
        # 性能追踪
        self.traces: List[Dict[str, Any]] = []
        self._current_trace = None
        
        # 实时仪表板
        self.dashboard_live: Optional[Live] = None
        self.dashboard_stats = {
            'status': 'Initializing',
            'current_phase': None,
            'phases_completed': 0,
            'total_duration': 0.0,
            'metrics_collected': 0
        }
        
        # 启动时间
        self.start_time = time.time()
    
    # ==================== 阶段管理 ====================
    
    def start_phase(self, name: str, **metadata) -> PhaseInfo:
        """
        开始一个新阶段
        
        Args:
            name: 阶段名称
            **metadata: 阶段元数据
            
        Returns:
            PhaseInfo 对象
        """
        # 完成当前阶段
        if self.current_phase and self.current_phase.status == "running":
            self.complete_phase()
        
        # 创建新阶段
        phase = PhaseInfo(name=name, metadata=metadata)
        self.phases.append(phase)
        self.current_phase = phase
        
        # 更新仪表板
        self.dashboard_stats['current_phase'] = name
        self.dashboard_stats['status'] = f"Running: {name}"
        self._update_dashboard()
        
        if self.enable_detailed_logging:
            console.print(f"\n[bold cyan]▶ Starting Phase:[/bold cyan] {name}")
        
        return phase
    
    def complete_phase(self, success: bool = True, **metadata) -> None:
        """
        完成当前阶段
        
        Args:
            success: 是否成功
            **metadata: 额外元数据
        """
        if not self.current_phase:
            return
        
        self.current_phase.end_time = time.time()
        self.current_phase.status = "completed" if success else "failed"
        self.current_phase.metadata.update(metadata)
        
        # 更新仪表板
        self.dashboard_stats['phases_completed'] += 1
        self._update_dashboard()
        
        if self.enable_detailed_logging:
            status_icon = "✓" if success else "✗"
            status_color = "green" if success else "red"
            console.print(
                f"[{status_color}]{status_icon}[/{status_color}] "
                f"Phase completed: {self.current_phase.name} "
                f"[dim]({self.current_phase.duration:.2f}s)[/dim]"
            )
        
        self.current_phase = None
    
    def fail_phase(self, error: str, **metadata) -> None:
        """
        标记当前阶段失败
        
        Args:
            error: 错误信息
            **metadata: 额外元数据
        """
        if self.current_phase:
            self.current_phase.metadata['error'] = error
        self.complete_phase(success=False, **metadata)
    
    # ==================== 指标收集 ====================
    
    def record_metric(self, name: str, value: float) -> None:
        """
        记录指标
        
        Args:
            name: 指标名称
            value: 指标值
        """
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
        
        self.dashboard_stats['metrics_collected'] = sum(len(v) for v in self.metrics.values())
        self._update_dashboard()
    
    def increment_counter(self, name: str, amount: int = 1) -> None:
        """
        增加计数器
        
        Args:
            name: 计数器名称
            amount: 增加量
        """
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += amount
        self._update_dashboard()
    
    def get_metric_stats(self, name: str) -> Dict[str, float]:
        """获取指标统计"""
        if name not in self.metrics or not self.metrics[name]:
            return {}
        
        values = self.metrics[name]
        return {
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'count': len(values),
            'total': sum(values)
        }
    
    # ==================== 性能追踪 ====================
    
    @contextmanager
    def trace(self, name: str, **metadata):
        """
        追踪代码块性能
        
        Args:
            name: 追踪名称
            **metadata: 元数据
        """
        start_time = time.time()
        trace_data = {
            'name': name,
            'start_time': start_time,
            'metadata': metadata,
            'phase': self.current_phase.name if self.current_phase else None
        }
        
        # 支持嵌套追踪
        parent_trace = self._current_trace
        if parent_trace:
            trace_data['parent'] = parent_trace['name']
        
        self._current_trace = trace_data
        
        try:
            yield trace_data
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            trace_data['end_time'] = end_time
            trace_data['duration_ms'] = duration_ms
            
            self.traces.append(trace_data)
            self._current_trace = parent_trace
            
            # 记录为指标
            self.record_metric(f"trace.{name}.duration_ms", duration_ms)
    
    # ==================== 实时仪表板 ====================
    
    def start_dashboard(self) -> None:
        """启动实时仪表板"""
        if not self.enable_live_dashboard:
            return
        
        layout = self._create_dashboard_layout()
        self.dashboard_live = Live(layout, console=console, refresh_per_second=4)
        self.dashboard_live.start()
    
    def _create_dashboard_layout(self) -> Layout:
        """创建仪表板布局"""
        layout = Layout()
        
        # 顶部：标题
        title = Panel(
            Text(f"🔄 {self.module_name} Runtime Dashboard", style="bold cyan", justify="center"),
            box=box.DOUBLE
        )
        
        # 中间：状态表
        status_table = self._create_status_table()
        
        # 底部：阶段进度
        phase_panel = self._create_phase_panel()
        
        layout.split_column(
            Layout(title, size=3),
            Layout(status_table, size=8),
            Layout(phase_panel, size=10)
        )
        
        return layout
    
    def _create_status_table(self) -> Table:
        """创建状态表格"""
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
        
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", style="white", justify="right")
        
        table.add_row("Status", f"[yellow]{self.dashboard_stats['status']}[/yellow]")
        table.add_row("Current Phase", self.dashboard_stats['current_phase'] or "-")
        table.add_row("Phases Completed", str(self.dashboard_stats['phases_completed']))
        table.add_row("Total Duration", f"{self.dashboard_stats['total_duration']:.2f}s")
        table.add_row("Metrics Collected", str(self.dashboard_stats['metrics_collected']))
        
        # 添加计数器
        for name, value in self.counters.items():
            table.add_row(f"  {name}", str(value))
        
        return table
    
    def _create_phase_panel(self) -> Panel:
        """创建阶段面板"""
        if not self.phases:
            return Panel("No phases yet", title="Phases", box=box.ROUNDED)
        
        phase_tree = Tree("📋 Execution Phases")
        
        for phase in self.phases:
            status_icon = {
                'running': '⏳',
                'completed': '✅',
                'failed': '❌'
            }.get(phase.status, '?')
            
            branch = phase_tree.add(
                f"{status_icon} {phase.name} [dim]({phase.duration:.2f}s)[/dim]"
            )
            
            # 添加元数据
            if phase.metadata:
                for key, value in phase.metadata.items():
                    branch.add(f"[dim]{key}:[/dim] {value}")
        
        return Panel(phase_tree, title="Phases", box=box.ROUNDED)
    
    def _update_dashboard(self) -> None:
        """更新仪表板"""
        if not self.dashboard_live:
            return
        
        self.dashboard_stats['total_duration'] = time.time() - self.start_time
        layout = self._create_dashboard_layout()
        self.dashboard_live.update(layout)
    
    def stop_dashboard(self) -> None:
        """停止仪表板"""
        if self.dashboard_live:
            self.dashboard_live.stop()
            self.dashboard_live = None
    
    # ==================== 可视化输出 ====================
    
    def display_summary(self) -> None:
        """显示执行摘要"""
        console.print("\n" + "=" * 80)
        console.print(f"[bold cyan]📊 {self.module_name} Execution Summary[/bold cyan]")
        console.print("=" * 80)
        
        # 阶段摘要
        if self.phases:
            self._display_phase_summary()
        
        # 指标摘要
        if self.metrics:
            self._display_metrics_summary()
        
        # 计数器摘要
        if self.counters:
            self._display_counters_summary()
        
        # 性能追踪
        if self.traces:
            self._display_trace_summary()
        
        # 总体统计
        total_duration = time.time() - self.start_time
        console.print(f"\n[bold]Total Duration:[/bold] {total_duration:.2f}s")
        console.print("=" * 80 + "\n")
    
    def _display_phase_summary(self) -> None:
        """显示阶段摘要"""
        table = Table(
            title="[bold blue]Phases[/bold blue]",
            box=box.ROUNDED
        )
        
        table.add_column("Phase", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Duration", style="yellow", justify="right")
        
        for phase in self.phases:
            status = {
                'running': '[yellow]Running[/yellow]',
                'completed': '[green]✓[/green]',
                'failed': '[red]✗[/red]'
            }.get(phase.status, phase.status)
            
            table.add_row(
                phase.name,
                status,
                f"{phase.duration:.2f}s"
            )
        
        console.print(table)
        console.print()
    
    def _display_metrics_summary(self) -> None:
        """显示指标摘要"""
        table = Table(
            title="[bold blue]Metrics[/bold blue]",
            box=box.ROUNDED
        )
        
        table.add_column("Metric", style="cyan")
        table.add_column("Min", style="green", justify="right")
        table.add_column("Max", style="red", justify="right")
        table.add_column("Avg", style="yellow", justify="right")
        table.add_column("Count", style="dim", justify="right")
        
        for name in sorted(self.metrics.keys()):
            stats = self.get_metric_stats(name)
            if stats:
                table.add_row(
                    name,
                    f"{stats['min']:.2f}",
                    f"{stats['max']:.2f}",
                    f"{stats['avg']:.2f}",
                    str(stats['count'])
                )
        
        console.print(table)
        console.print()
    
    def _display_counters_summary(self) -> None:
        """显示计数器摘要"""
        table = Table(
            title="[bold blue]Counters[/bold blue]",
            box=box.ROUNDED
        )
        
        table.add_column("Counter", style="cyan")
        table.add_column("Value", style="yellow", justify="right")
        
        for name, value in sorted(self.counters.items()):
            table.add_row(name, str(value))
        
        console.print(table)
        console.print()
    
    def _display_trace_summary(self) -> None:
        """显示追踪摘要"""
        table = Table(
            title="[bold blue]Performance Traces[/bold blue]",
            box=box.ROUNDED
        )
        
        table.add_column("Trace", style="cyan")
        table.add_column("Duration", style="yellow", justify="right")
        table.add_column("Phase", style="dim")
        
        for trace in self.traces:
            table.add_row(
                trace['name'],
                f"{trace['duration_ms']:.2f}ms",
                trace.get('phase', '-')
            )
        
        console.print(table)
        console.print()
    
    # ==================== 上下文管理器 ====================
    
    def __enter__(self):
        """进入上下文"""
        if self.enable_live_dashboard:
            self.start_dashboard()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.dashboard_live:
            self.stop_dashboard()
        
        if exc_type is None:
            self.display_summary()
        else:
            console.print(f"\n[red]✗ Failed with error:[/red] {exc_val}\n")
            self.display_summary()
        
        return False


# ==================== 辅助类（保持向后兼容） ====================

class ProgressDisplay:
    """进度显示器（简化版）"""
    
    def __init__(self, total: Optional[int] = None, description: str = "Processing"):
        self.total = total
        self.description = description
        self.progress = None
        self.task_id = None
        self._start_time = None
    
    def start(self) -> None:
        self._start_time = time.time()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console
        )
        self.progress.start()
        self.task_id = self.progress.add_task(self.description, total=self.total)
    
    def update(self, advance: int = 1, description: Optional[str] = None) -> None:
        if self.progress and self.task_id is not None:
            if description:
                self.progress.update(self.task_id, description=description)
            self.progress.update(self.task_id, advance=advance)
    
    def complete(self, message: Optional[str] = None) -> None:
        if self.progress:
            if message and self.task_id is not None:
                self.progress.update(self.task_id, description=message)
            self.progress.stop()
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.complete()
        else:
            self.progress.stop()
        return False


class MetricsCollector:
    """指标收集器（简化版，向后兼容）"""
    
    def __init__(self, module_name: str = ""):
        self.module_name = module_name
        self.metrics: Dict[str, List[float]] = {}
        self.counters: Dict[str, int] = {}
    
    def record(self, metric_name: str, value: float) -> None:
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(value)
    
    def increment(self, counter_name: str, amount: int = 1) -> None:
        if counter_name not in self.counters:
            self.counters[counter_name] = 0
        self.counters[counter_name] += amount
    
    def get_stats(self, metric_name: str) -> Dict[str, float]:
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return {}
        
        values = self.metrics[metric_name]
        return {
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'count': len(values)
        }
    
    def get_counter(self, counter_name: str) -> int:
        return self.counters.get(counter_name, 0)
