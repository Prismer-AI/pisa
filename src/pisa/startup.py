"""
PISA 系统统一启动入口

职责：
1. 提供统一的系统初始化入口
2. 执行完整的 startup flow
3. 自动扫描和注册组件
4. 验证系统就绪状态
5. 提供启动观测输出

使用方式：
    from pisa import initialize_pisa
    
    manager = initialize_pisa()
    agent = manager.create_agent("agent.md")
    result = await agent.run("task description")
"""

import logging
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich import box

from pisa.config import Config
from pisa.agents import get_registry_manager, RegistryManager
from pisa.capability import get_global_registry
from pisa.core.loop.registry import get_loop_registry
from pisa.utils.observability import ObservabilityManager

_logger = logging.getLogger(__name__)
console = Console()


def initialize_pisa(
    capability_paths: Optional[List[Path]] = None,
    loop_paths: Optional[List[Path]] = None,
    enable_observability: bool = True,
    enable_auto_scan: bool = True,
    display_startup_info: bool = True
) -> RegistryManager:
    """
    PISA 系统统一启动入口
    
    执行完整的 Startup Flow（PISA2.md 639-671）:
    1. 启动 PISA 框架
    2. 初始化 RegistryManager
    3. 扫描和注册 Capabilities
    4. 扫描和注册 Loops
    5. 系统就绪，展示统计
    
    Args:
        capability_paths: Capability 扫描路径列表
        loop_paths: Loop 扫描路径列表
        enable_observability: 是否启用观测系统
        enable_auto_scan: 是否自动扫描（默认目录）
        display_startup_info: 是否展示启动信息
        
    Returns:
        RegistryManager 实例
        
    Example:
        >>> manager = initialize_pisa()
        >>> agent = manager.create_agent("agent.md")
        >>> await agent.run("Solve this task")
    """
    obs = None
    if enable_observability:
        obs = ObservabilityManager("PISA_Startup", enable_detailed_logging=True)
    
    if display_startup_info:
        console.print("\n")
        console.print("=" * 80, style="cyan")
        console.print(" " * 25 + "🚀 PISA Framework Startup", style="bold cyan")
        console.print("=" * 80, style="cyan")
        console.print()
    
    # ===== 步骤 1: 加载配置 =====
    if obs:
        obs.start_phase("Load Configuration")
    
    _logger.info("Loading PISA configuration...")
    Config.setup_agent_sdk()
    
    if obs:
        obs.complete_phase(success=True)
    
    if display_startup_info:
        console.print("✅ Configuration loaded", style="green")
    
    # ===== 步骤 2: 初始化 RegistryManager =====
    if obs:
        obs.start_phase("Initialize RegistryManager")
    
    _logger.info("Initializing RegistryManager...")
    manager = get_registry_manager()
    
    if obs:
        obs.complete_phase(success=True)
    
    if display_startup_info:
        console.print("✅ RegistryManager initialized", style="green")
    
    # ===== 步骤 3: 扫描 Capabilities =====
    if obs:
        obs.start_phase("Scan Capabilities")
    
    _logger.info("Scanning capabilities...")
    
    capability_registry = get_global_registry()
    
    # 1. 始终扫描 PISA 工程内部的 capabilities（如果 enable_auto_scan=True）
    if enable_auto_scan:
        internal_cap_path = Path(__file__).parent / "capability" / "local"
        if internal_cap_path.exists():
            _logger.info(f"Scanning internal capabilities: {internal_cap_path}")
            discovered = capability_registry.discover_from_directory(internal_cap_path)
            # 标记为 internal（直接修改对象，不重新注册）
            for cap_name in discovered:
                cap = capability_registry.get(cap_name)
                if cap:
                    cap.source = "internal"
            if discovered:
                _logger.info(f"Discovered {len(discovered)} internal capabilities")
                if display_startup_info:
                    console.print(f"  ✓ Loaded {len(discovered)} internal capabilities", style="dim green")
    
    # 2. 扫描用户提供的路径
    if capability_paths:
        for cap_path in capability_paths:
            cap_path = Path(cap_path)  # 确保是Path对象
            if cap_path.exists():
                _logger.info(f"Scanning user capability path: {cap_path}")
                discovered = capability_registry.discover_from_directory(cap_path)
                _logger.info(f"Discovered {len(discovered)} capabilities from {cap_path}")
    
    # 3. 扫描 .prismer/capability 目录（如果存在）
    prismer_cap_dir = Path.cwd() / ".prismer" / "capability"
    if prismer_cap_dir.exists():
        _logger.info(f"Scanning .prismer/capability directory: {prismer_cap_dir}")
        for subdir in ["function", "subagent", "mcp"]:
            subdir_path = prismer_cap_dir / subdir
            if subdir_path.exists():
                _logger.info(f"Scanning {subdir} capabilities: {subdir_path}")
                discovered = capability_registry.discover_from_directory(subdir_path)
                if discovered:
                    _logger.info(f"Discovered {len(discovered)} {subdir} capabilities from .prismer: {discovered}")
                    if display_startup_info:
                        console.print(f"  ✓ Loaded {len(discovered)} custom {subdir} capabilities", style="dim green")
    
    cap_count = len(capability_registry.list_all())
    
    if obs:
        obs.record_metric("capabilities_registered", cap_count)
        obs.complete_phase(success=True, count=cap_count)
    
    if display_startup_info:
        console.print(f"✅ Capabilities registered: {cap_count}", style="green")
    
    # ===== 步骤 4: 扫描 Loops =====
    if obs:
        obs.start_phase("Scan Agent Loops")
    
    _logger.info("Scanning agent loops...")
    
    loop_registry = get_loop_registry()
    
    # 1. 始终导入 PISA 工程内置的 loop 模板
    try:
        from pisa.core.loop.templates import plan_execute
        internal_loop_count = len(loop_registry.list_all())
        _logger.info(f"Loaded {internal_loop_count} internal loop templates")
        if display_startup_info and internal_loop_count > 0:
            console.print(f"  ✓ Loaded {internal_loop_count} internal loop templates", style="dim green")
    except ImportError as e:
        _logger.warning(f"Failed to import loop templates: {e}")
    
    # 2. 扫描用户提供的 loop 路径
    if loop_paths:
        for loop_path in loop_paths:
            loop_path = Path(loop_path)
            if loop_path.exists():
                _logger.info(f"Scanning user loop path: {loop_path}")
                discovered_loops = loop_registry.discover_from_directory(loop_path)
                if discovered_loops:
                    _logger.info(f"Discovered {len(discovered_loops)} user loops: {discovered_loops}")
                    if display_startup_info:
                        console.print(f"  ✓ Loaded {len(discovered_loops)} user loop templates", style="dim green")
    
    # 3. 扫描 .prismer/loop 目录（如果存在）
    prismer_loop_dir = Path.cwd() / ".prismer" / "loop"
    if prismer_loop_dir.exists():
        _logger.info(f"Scanning .prismer/loop directory: {prismer_loop_dir}")
        discovered_loops = loop_registry.discover_from_directory(prismer_loop_dir)
        if discovered_loops:
            _logger.info(f"Discovered {len(discovered_loops)} custom loops from .prismer: {discovered_loops}")
            if display_startup_info:
                console.print(f"  ✓ Loaded {len(discovered_loops)} custom loops", style="dim green")
    
    loop_count = len(loop_registry.list_all())
    
    if obs:
        obs.record_metric("loops_registered", loop_count)
        obs.complete_phase(success=True, count=loop_count)
    
    if display_startup_info:
        console.print(f"✅ Agent Loops registered: {loop_count}", style="green")
    
    # ===== 步骤 5: 系统就绪 =====
    if obs:
        obs.start_phase("System Ready")
        obs.complete_phase(success=True)
    
    if display_startup_info:
        console.print()
        console.print("=" * 80, style="cyan")
        console.print(" " * 30 + "✅ System Ready", style="bold green")
        console.print("=" * 80, style="cyan")
        console.print()
        
        # 展示详细统计
        _display_startup_statistics(manager)
    
    _logger.info("PISA framework initialized successfully")
    
    return manager


def _display_startup_statistics(manager: RegistryManager) -> None:
    """
    展示启动统计信息
    
    Args:
        manager: RegistryManager 实例
    """
    stats = manager.get_statistics()
    
    # Capabilities 统计
    cap_table = Table(
        title="📦 Registered Capabilities",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    cap_table.add_column("Type", style="cyan")
    cap_table.add_column("Count", style="white", justify="right")
    
    cap_table.add_row("Function", str(stats['capabilities']['by_type']['function']))
    cap_table.add_row("Agent", str(stats['capabilities']['by_type']['agent']))
    cap_table.add_row("MCP", str(stats['capabilities']['by_type']['mcp']))
    cap_table.add_row("[bold]Total[/bold]", f"[bold]{stats['capabilities']['total']}[/bold]")
    
    console.print(cap_table)
    console.print()
    
    # Loops 统计
    loop_table = Table(
        title="🔄 Registered Agent Loops",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    loop_table.add_column("Loop Type", style="magenta")
    loop_table.add_column("Description", style="white")
    
    for loop_info in stats['loops']['list']:
        loop_table.add_row(
            loop_info['name'],
            loop_info.get('description', '-')[:50]
        )
    
    console.print(loop_table)
    console.print()
    
    # ===== ✅ Phase 5: 统一的 Capabilities 表格 =====
    if stats['capabilities']['total'] > 0:
        from rich.panel import Panel
        from rich.syntax import Syntax
        import json
        
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
        
        # 获取所有 capabilities 并按 source 分组排序
        cap_names = manager.capability_registry.list_all()
        caps_data = []
        for cap_name in cap_names:
            cap = manager.capability_registry.get(cap_name)
            if cap:
                caps_data.append(cap)
        
        # 排序：internal 在前，custom 在后
        caps_data.sort(key=lambda c: (c.source != "internal", c.name))
        
        for cap in caps_data:
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
            
            # 格式化描述（限制长度）
            description = cap.description or "-"
            if len(description) > 35:
                description = description[:32] + "..."
            
            # 格式化参数（显示必需参数）
            params_info = []
            if cap.parameters and 'properties' in cap.parameters:
                required = cap.parameters.get('required', [])
                properties = cap.parameters.get('properties', {})
                
                # 显示必需参数
                for param_name in required[:2]:  # 最多显示2个
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


def validate_system_ready() -> dict:
    """
    验证系统是否就绪
    
    Returns:
        验证结果字典
        
    Example:
        >>> result = validate_system_ready()
        >>> if result['is_ready']:
        >>>     print("System ready!")
    """
    issues = []
    warnings = []
    
    # 检查配置
    try:
        Config.setup_agent_sdk()
    except Exception as e:
        issues.append(f"Configuration error: {str(e)}")
    
    # 检查 Capabilities
    cap_registry = get_global_registry()
    cap_count = len(cap_registry.list_all())
    if cap_count == 0:
        warnings.append("No capabilities registered")
    
    # 检查 Loops
    loop_registry = get_loop_registry()
    loop_count = len(loop_registry.list_all())
    if loop_count == 0:
        issues.append("No agent loops registered")
    
    is_ready = len(issues) == 0
    
    return {
        "is_ready": is_ready,
        "capabilities_count": cap_count,
        "loops_count": loop_count,
        "issues": issues,
        "warnings": warnings
    }


async def quick_start(
    agent_definition_path: str,
    task: str = "",
    capability_paths: Optional[List[str]] = None,
    loop_paths: Optional[List[str]] = None,
    return_agent: bool = False,
    **kwargs
):
    """
    快速启动：初始化系统并运行任务
    
    Args:
        agent_definition_path: agent.md 路径
        task: 任务描述（如果return_agent=True，可以为空）
        capability_paths: 自定义 capability 扫描路径（可选）
        loop_paths: 自定义 loop 扫描路径（可选）
        return_agent: 是否返回agent实例而不运行（用于交互模式）
        **kwargs: 传递给 initialize_pisa 的其他参数
        
    Returns:
        如果return_agent=True，返回agent实例
        否则返回执行结果
        
    Example:
        >>> result = quick_start("agent.md", "Analyze this data")
        >>> agent = await quick_start("agent.md", return_agent=True)
    """
    import asyncio
    
    # 初始化系统（如果还未初始化）
    # 检查是否已经初始化
    from pisa.capability import get_global_registry
    from pisa.core.loop.registry import get_loop_registry
    from pisa.agents.manager import RegistryManager
    
    registry = get_global_registry()
    loop_registry = get_loop_registry()
    
    # 如果registries为空，说明系统未初始化
    if len(registry.list_all()) == 0 and len(loop_registry.list_all()) == 0:
        manager = initialize_pisa(
            capability_paths=capability_paths,
            loop_paths=loop_paths,
            **kwargs
        )
    else:
        # 已初始化，直接使用现有的RegistryManager实例
        manager = RegistryManager.get_instance()
    
    # 创建 Agent
    agent = manager.create_agent(agent_definition_path)
    
    # 如果只是返回agent实例，不运行
    if return_agent:
        return agent
    
    # 运行任务
    if not task:
        raise ValueError("Task is required when return_agent=False")
    
    # 检测是否已经在事件循环中
    try:
        loop = asyncio.get_running_loop()
        # 已经在事件循环中，直接返回 coroutine
        return await agent.run(task)
    except RuntimeError:
        # 不在事件循环中，创建新的
        return asyncio.run(agent.run(task))

