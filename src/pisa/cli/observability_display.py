"""
CLI Observability Display

统一的可观测性输出，用于 CLI 命令
整合了 Context、State、Performance 等信息的结构化显示
"""

from typing import Any, Dict, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def display_plan_summary(plan: Any) -> None:
    """
    显示任务规划摘要
    
    Args:
        plan: 任务计划（TaskTree 或 dict）
    """
    console.print()
    console.print("[bold cyan]📋 Task Plan[/bold cyan]")
    
    # 提取任务列表
    if isinstance(plan, dict):
        tasks = plan.get('tasks', {})
        root_goal = plan.get('root_goal', 'N/A')
    else:
        tasks = getattr(plan, 'tasks', {})
        root_goal = getattr(plan, 'root_goal', 'N/A')
    
    # 显示目标
    console.print(f"  [dim]Goal:[/dim] {root_goal}")
    console.print(f"  [dim]Total Tasks:[/dim] {len(tasks)}")
    console.print()
    
    # 显示任务列表
    if tasks:
        table = Table(box=box.SIMPLE)
        table.add_column("Task ID", style="cyan", width=12)
        table.add_column("Description", style="white", width=50)
        table.add_column("Capability", style="yellow", width=20)
        
        for task_id, task in tasks.items():
            if isinstance(task, dict):
                desc = task.get('task_description', 'N/A')
                cap = task.get('assigned_capability', 'N/A')
            else:
                desc = getattr(task, 'task_description', 'N/A')
                cap = getattr(task, 'assigned_capability', 'N/A')
            
            # 截断描述
            if len(desc) > 48:
                desc = desc[:45] + "..."
            
            table.add_row(task_id, desc, cap)
        
        console.print(table)
        console.print()


def display_task_execution(task_id: str, description: str, capability: str, result: Any) -> None:
    """
    显示单个任务执行详情
    
    Args:
        task_id: 任务ID
        description: 任务描述
        capability: 使用的能力
        result: 执行结果
    """
    console.print()
    console.print(f"[bold green]✓[/bold green] Task {task_id} Completed")
    console.print(f"  [dim]Description:[/dim] {description}")
    console.print(f"  [dim]Capability:[/dim] {capability}")
    
    # 提取实际结果
    if isinstance(result, dict):
        if 'result' in result and isinstance(result['result'], dict):
            actual = result['result'].get('result', result)
        else:
            actual = result.get('output', result)
    else:
        actual = result
    
    # 显示结果（简短版本）
    if isinstance(actual, (list, dict)):
        import json
        result_str = json.dumps(actual, ensure_ascii=False)
        if len(result_str) > 100:
            result_str = result_str[:100] + "..."
    else:
        result_str = str(actual)
        if len(result_str) > 100:
            result_str = result_str[:100] + "..."
    
    console.print(f"  [dim]Result:[/dim] {result_str}")
    console.print()


def display_execution_details(result: Dict[str, Any], verbose: bool = False) -> None:
    """
    显示执行详情（结构化）
    
    Args:
        result: 执行结果字典（来自 LoopState）
        verbose: 是否显示详细信息
    """
    console.print()
    console.print("=" * 80)
    console.print("[bold cyan]📊 Execution Details[/bold cyan]")
    console.print("=" * 80)
    console.print()
    
    # 1. 显示规划的任务
    if 'plan' in result and result['plan']:
        console.print()
        _show_plan_info(result['plan'])
    
    # 2. 基本信息表格
    _show_basic_info(result)
    
    # 3. 如果有 observation，显示任务执行情况
    if 'observation' in result and result['observation']:
        console.print()
        _show_observation_info(result['observation'])
    
    # 4. 如果有 result，显示执行结果
    if 'result' in result and result['result']:
        console.print()
        _show_result_info(result['result'])
    
    # 5. 如果 verbose，显示更多详情
    if verbose:
        console.print()
        _show_verbose_info(result)
    
    console.print()
    console.print("=" * 80)


def _show_plan_info(plan: Any) -> None:
    """显示规划信息"""
    # 提取任务列表
    tasks = None
    if isinstance(plan, dict):
        tasks = plan.get('tasks', {})
        root_goal = plan.get('root_goal', 'N/A')
    elif hasattr(plan, 'tasks'):
        tasks = plan.tasks
        root_goal = getattr(plan, 'root_goal', 'N/A')
    else:
        return
    
    if not tasks:
        return
    
    table = Table(title="📋 Planned Tasks", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("Task ID", style="cyan", width=10)
    table.add_column("Description", style="white")
    table.add_column("Capability", style="magenta", width=20)
    table.add_column("Status", style="green", width=12)
    
    # 遍历任务
    for idx, (task_id, task) in enumerate(tasks.items(), 1):
        # 处理 task 可能是 dict 或对象
        if isinstance(task, dict):
            desc = task.get('task_description', 'N/A')
            capability = task.get('assigned_capability', 'N/A')
            status = task.get('status', 'N/A')
        else:
            desc = getattr(task, 'task_description', 'N/A')
            capability = getattr(task, 'assigned_capability', 'N/A')
            status = str(getattr(task, 'status', 'N/A'))
        
        # 截断过长的描述
        if len(desc) > 50:
            desc = desc[:50] + "..."
        
        # 状态图标
        status_str = str(status)
        if 'COMPLETED' in status_str.upper():
            status_display = "✅ Completed"
        elif 'FAILED' in status_str.upper():
            status_display = "❌ Failed"
        elif 'RUNNING' in status_str.upper():
            status_display = "⏳ Running"
        else:
            status_display = f"📌 {status}"
        
        table.add_row(
            str(idx),
            task_id,
            desc,
            capability,
            status_display
        )
    
    console.print(Panel(
        f"[bold]Goal:[/bold] {root_goal}\n[dim]Total Tasks: {len(tasks)}[/dim]",
        title="🎯 Plan Overview",
        border_style="cyan"
    ))
    console.print(table)


def _show_basic_info(result: Dict[str, Any]) -> None:
    """显示基本信息表格"""
    table = Table(title="⚡ Execution Summary", box=box.ROUNDED)
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Value", style="green")
    
    # 迭代次数
    iterations = result.get('iteration', result.get('iterations', 0))
    if isinstance(iterations, int):
        iterations += 1  # iteration 从 0 开始
    table.add_row("Iterations", str(iterations))
    
    # 成功状态
    success = result.get('success', False)
    status_icon = "✅" if success else "❌"
    table.add_row("Success", f"{status_icon} {success}")
    
    # 停止原因
    if 'metadata' in result and isinstance(result['metadata'], dict):
        exit_reason = result['metadata'].get('exit_reason', 'N/A')
        table.add_row("Exit Reason", exit_reason)
    
    # 是否有结果
    has_result = 'result' in result and result['result'] is not None
    table.add_row("Has Result", "✓" if has_result else "✗")
    
    console.print(table)


def _show_observation_info(observation: Any) -> None:
    """显示观察信息"""
    if isinstance(observation, dict):
        obs_success = observation.get('success', False)
        error_type = observation.get('error_type', 'None')
        is_recoverable = observation.get('is_recoverable', False)
    elif hasattr(observation, 'success'):
        obs_success = observation.success
        error_type = getattr(observation, 'error_type', 'None')
        is_recoverable = getattr(observation, 'is_recoverable', False)
    else:
        return
    
    table = Table(title="👁️ Task Observation", box=box.ROUNDED)
    table.add_column("Aspect", style="cyan", width=20)
    table.add_column("Status", style="yellow")
    
    table.add_row("Task Success", "✅ True" if obs_success else "❌ False")
    table.add_row("Error Type", str(error_type))
    table.add_row("Recoverable", "✓" if is_recoverable else "✗")
    
    console.print(table)


def _show_result_info(result: Any) -> None:
    """显示结果信息"""
    # 提取实际结果
    actual_result = None
    
    if isinstance(result, dict):
        # ⭐ 优先检查是否是 CapabilityCallResult 格式
        # CapabilityCallResult 有 'capability_name', 'success', 'result' 三个关键字段
        if 'capability_name' in result and 'success' in result and 'result' in result:
            # 这是一个 CapabilityCallResult，直接提取 result 字段
            actual_result = result['result']
        # 检查嵌套的 result
        elif 'result' in result and isinstance(result['result'], dict):
            inner_result = result['result']
            if 'result' in inner_result:
                actual_result = inner_result['result']
            elif 'output' in inner_result:
                actual_result = inner_result['output']
            else:
                actual_result = inner_result
        elif 'output' in result:
            actual_result = result['output']
        else:
            actual_result = result
    else:
        actual_result = result
    
    if actual_result is None:
        return
    
    # 创建结果面板
    if isinstance(actual_result, (list, dict)):
        import json
        content = json.dumps(actual_result, indent=2, ensure_ascii=False)
        # 限制显示长度
        if len(content) > 500:
            content = content[:500] + "\n... (truncated)"
    else:
        content = str(actual_result)
        if len(content) > 500:
            content = content[:500] + "... (truncated)"
    
    panel = Panel(
        content,
        title="📤 Execution Result",
        border_style="green",
        box=box.ROUNDED
    )
    console.print(panel)


def _show_verbose_info(result: Dict[str, Any]) -> None:
    """显示详细信息（verbose 模式）"""
    from datetime import datetime
    import json
    
    table = Table(title="🔍 Verbose Details", box=box.ROUNDED)
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", style="dim")
    
    # 显示所有字段（除了已经显示的）
    skip_fields = {'result', 'observation', 'metadata', 'success', 'iteration', 'iterations'}
    
    for key, value in result.items():
        if key in skip_fields:
            continue
        
        # 格式化值
        if value is None:
            str_value = "None"
        elif isinstance(value, bool):
            str_value = "True" if value else "False"
        elif isinstance(value, datetime):
            str_value = value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, (list, dict)):
            try:
                # 自定义 JSON encoder 处理 datetime
                class DateTimeEncoder(json.JSONEncoder):
                    def default(self, obj):
                        if isinstance(obj, datetime):
                            return obj.isoformat()
                        return super().default(obj)
                
                str_value = json.dumps(value, ensure_ascii=False, cls=DateTimeEncoder)
                if len(str_value) > 100:
                    str_value = str_value[:100] + "..."
            except (TypeError, ValueError):
                str_value = str(value)
                if len(str_value) > 100:
                    str_value = str_value[:100] + "..."
        else:
            str_value = str(value)
            if len(str_value) > 100:
                str_value = str_value[:100] + "..."
        
        table.add_row(key, str_value)
    
    if table.row_count > 0:
        console.print(table)


def display_module_execution(
    module_name: str,
    status: str,
    iteration: int,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    显示模块执行信息（用于实时输出）
    
    Args:
        module_name: 模块名称
        status: 状态（success/failed/running）
        iteration: 迭代次数
        details: 额外详情
    """
    # 状态图标
    status_icons = {
        "success": "✅",
        "failed": "❌",
        "running": "⏳"
    }
    icon = status_icons.get(status, "▶️")
    
    # 简洁的一行输出
    msg = f"{icon} [cyan]Iter {iteration}[/cyan] | [bold]{module_name}[/bold] | {status}"
    
    if details:
        # 只显示关键信息
        key_info = []
        if 'task_id' in details:
            key_info.append(f"task={details['task_id']}")
        if 'action' in details:
            key_info.append(f"action={details['action']}")
        
        if key_info:
            msg += f" | {' | '.join(key_info)}"
    
    console.print(msg)


def display_loop_summary(iterations: int, success: bool, exit_reason: str) -> None:
    """
    显示循环执行摘要
    
    Args:
        iterations: 迭代次数
        success: 是否成功
        exit_reason: 退出原因
    """
    status_color = "green" if success else "red"
    status_text = "✅ SUCCESS" if success else "❌ FAILED"
    
    console.print()
    console.print("─" * 80)
    console.print(
        f"[bold {status_color}]{status_text}[/bold {status_color}] | "
        f"Iterations: {iterations} | Exit: {exit_reason}"
    )
    console.print("─" * 80)

