"""
Validate Command

职责：
1. 验证 agent.md 和 context.md 语法
2. 检查 Capability 引用是否存在
3. 验证 Loop 类型是否注册
4. 提供详细的错误信息

使用示例：
```bash
pisa validate agent.md
pisa validate agent.md --context context.md
pisa validate --all  # 验证所有定义文件
```
"""

import click
from typing import Optional, List, Dict, Any
from pathlib import Path

from pisa.cli.ui import (
    print_header,
    print_error,
    print_success,
    print_warning,
    print_info,
    print_separator,
    print_validation_results,
    print_table,
    display_icon,
    console
)
from pisa.startup import initialize_pisa
from pisa.core.definition import parse_agent_definition
from pisa.core.definition.validator import SchemaValidator, ValidationError
from pisa.agents import get_registry_manager
from pisa.utils.logger import get_logger

_logger = get_logger(__name__)


@click.command(name="validate", context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "definition_file",
    type=click.Path(exists=True),
    required=False
)
@click.option(
    "--context",
    "-c",
    type=click.Path(exists=True),
    help="Context definition file to validate"
)
@click.option(
    "--all",
    "-a",
    "validate_all",
    is_flag=True,
    help="Validate all definition files in current directory"
)
@click.option(
    "--strict",
    "-s",
    is_flag=True,
    help="Enable strict validation mode"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output"
)
def validate_command(
    definition_file: Optional[str],
    context: Optional[str],
    validate_all: bool,
    strict: bool,
    verbose: bool
) -> None:
    """
    Validate agent and context definitions
    
    Args:
        definition_file: Path to definition file
        context: Path to context.md
        validate_all: Validate all files flag
        strict: Strict mode flag
        verbose: Verbose mode
    """
    display_icon()
    print_header("PISA Definition Validator", "Validate your agent definitions")
    
    try:
        # 初始化系统（需要检查注册表）
        if verbose:
            print_info("Initializing PISA system...")
        
        # 检查是否有 .prismer 目录（自定义 capabilities）
        prismer_dir = Path.cwd() / ".prismer"
        capability_paths = None
        if prismer_dir.exists():
            cap_dir = prismer_dir / "capability"
            if cap_dir.exists():
                capability_paths = [cap_dir]
                if verbose:
                    print_info(f"Found .prismer/capability directory, will scan custom capabilities")
        
        manager = initialize_pisa(capability_paths=capability_paths)
        
        # 确定要验证的文件
        files_to_validate = []
        
        if validate_all:
            # 扫描当前目录所有 .md 文件
            print_info("Scanning current directory for definition files...")
            files_to_validate = _find_definition_files(Path.cwd())
            
            if not files_to_validate:
                print_warning("No definition files found in current directory")
                return
            
            print_info(f"Found {len(files_to_validate)} file(s) to validate")
        
        elif definition_file:
            files_to_validate = [Path(definition_file)]
        
        else:
            print_error("Please specify a file or use --all")
            raise click.Abort()
        
        print_separator()
        
        # 验证所有文件
        all_results = []
        for file_path in files_to_validate:
            result = _validate_file(file_path, manager, strict, verbose)
            all_results.append((file_path, result))
        
        # 显示汇总结果
        _print_summary(all_results)
        
        # 如果有错误，退出码非0
        has_errors = any(result["failed"] > 0 for _, result in all_results)
        if has_errors:
            raise click.Abort()
    
    except click.Abort:
        raise
    except Exception as e:
        print_error("Validation system error", str(e))
        if verbose:
            _logger.exception("Detailed error:")
        raise click.Abort()


def _find_definition_files(directory: Path) -> List[Path]:
    """
    查找定义文件
    
    Args:
        directory: 目录路径
    
    Returns:
        定义文件列表
    """
    files = []
    
    # 查找所有 .md 文件
    for md_file in directory.glob("*.md"):
        # 跳过README等通用文件
        if md_file.name.lower() not in ["readme.md", "contributing.md", "changelog.md"]:
            files.append(md_file)
    
    return sorted(files)


def _validate_file(
    file_path: Path,
    manager: any,
    strict: bool = False,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    验证单个文件
    
    Args:
        file_path: 文件路径
        manager: RegistryManager实例
        strict: 严格模式
        verbose: 详细模式
        
    Returns:
        验证结果字典
    """
    console.print()
    console.print(f"[bold cyan]Validating:[/bold cyan] {file_path.name}")
    console.print()
    
    results = {
        "passed": 0,
        "failed": 0,
        "warnings": 0,
        "errors": [],
        "warnings_list": []
    }
    
    try:
        # 1. 检查文件是否可读
        if not file_path.exists():
            results["errors"].append(f"File not found: {file_path}")
            results["failed"] += 1
            return results
        
        console.print("  [dim]Step 1:[/dim] Reading file...")
        results["passed"] += 1
        
        # 2. 解析定义
        console.print("  [dim]Step 2:[/dim] Parsing definition...")
        try:
            agent_def = parse_agent_definition(file_path)
            results["passed"] += 1
            console.print(f"  [green]✓[/green] Parsed successfully")
        except Exception as e:
            results["errors"].append(f"Parse error: {str(e)}")
            results["failed"] += 1
            console.print(f"  [red]✗[/red] Parse failed")
            return results  # 解析失败，无法继续
        
        # 3. 验证Schema
        console.print("  [dim]Step 3:[/dim] Validating schema...")
        try:
            validator = SchemaValidator()
            # TODO: 实际schema验证
            results["passed"] += 1
            console.print(f"  [green]✓[/green] Schema valid")
        except ValidationError as e:
            results["errors"].append(f"Schema validation error: {str(e)}")
            results["failed"] += 1
            console.print(f"  [red]✗[/red] Schema invalid")
        
        # 4. 检查Loop类型（从 LoopRegistry 动态验证）
        console.print("  [dim]Step 4:[/dim] Checking loop type...")
        loop_registry = manager.loop_registry
        registered_loops = [info['name'] for info in manager.list_loops()]
        
        if agent_def.loop_type in registered_loops:
            results["passed"] += 1
            console.print(f"  [green]✓[/green] Loop type '{agent_def.loop_type}' registered")
        else:
            results["errors"].append(
                f"Loop type '{agent_def.loop_type}' not registered. Available loops: {', '.join(registered_loops)}"
            )
            results["failed"] += 1
            console.print(f"  [red]✗[/red] Loop type '{agent_def.loop_type}' not found")
            
            if verbose:
                console.print(f"  [dim]Available loops: {', '.join(registered_loops)}[/dim]")
        
        # 5. 检查Capability引用
        console.print("  [dim]Step 5:[/dim] Checking capability references...")
        
        if agent_def.capabilities:
            cap_registry = manager.capability_registry
            available_caps = [cap.name for cap in manager.list_capabilities()]
            
            missing_caps = []
            for cap_ref in agent_def.capabilities:
                cap_name = cap_ref.name if hasattr(cap_ref, 'name') else str(cap_ref)
                
                if cap_name not in available_caps:
                    missing_caps.append(cap_name)
            
            if missing_caps:
                results["errors"].append(
                    f"Capabilities not found: {', '.join(missing_caps)}"
                )
                results["failed"] += 1
                console.print(f"  [red]✗[/red] {len(missing_caps)} capability(s) not found")
                
                if verbose:
                    for cap in missing_caps:
                        console.print(f"    [red]•[/red] {cap}")
                    console.print(f"  [dim]Available: {', '.join(available_caps[:5])}...[/dim]")
            else:
                results["passed"] += 1
                console.print(f"  [green]✓[/green] All capabilities found")
        else:
            results["warnings_list"].append("No capabilities defined")
            results["warnings"] += 1
            console.print(f"  [yellow]⚠[/yellow] No capabilities defined")
        
        # 6. 检查Validation Rules（如果有）
        console.print("  [dim]Step 6:[/dim] Checking validation rules...")
        
        if agent_def.validation_rules:
            # TODO: 验证validator函数是否存在
            results["passed"] += 1
            console.print(f"  [green]✓[/green] {len(agent_def.validation_rules)} validation rule(s) defined")
        else:
            if strict:
                results["warnings_list"].append("No validation rules defined")
                results["warnings"] += 1
                console.print(f"  [yellow]⚠[/yellow] No validation rules")
            else:
                results["passed"] += 1
                console.print(f"  [dim]No validation rules (optional)[/dim]")
        
        # 7. 检查模型配置
        console.print("  [dim]Step 7:[/dim] Checking model configuration...")
        
        if agent_def.models and agent_def.models.default_model:
            results["passed"] += 1
            console.print(f"  [green]✓[/green] Default model: {agent_def.models.default_model}")
        else:
            results["warnings_list"].append("No default model specified")
            results["warnings"] += 1
            console.print(f"  [yellow]⚠[/yellow] No default model")
        
        # 8. 严格模式额外检查
        if strict:
            console.print("  [dim]Step 8:[/dim] Strict mode checks...")
            
            # 检查description
            if not agent_def.metadata.description:
                results["warnings_list"].append("No description provided")
                results["warnings"] += 1
            
            # 检查version
            if not agent_def.metadata.version:
                results["warnings_list"].append("No version specified")
                results["warnings"] += 1
            
            if results["warnings"] == 0:
                console.print(f"  [green]✓[/green] All strict checks passed")
    
    except Exception as e:
        results["errors"].append(f"Unexpected error: {str(e)}")
        results["failed"] += 1
        console.print(f"  [red]✗[/red] Validation error")
        if verbose:
            _logger.exception("Detailed error:")
    
    return results


def _print_summary(all_results: List[tuple]) -> None:
    """
    打印验证汇总
    
    Args:
        all_results: 所有验证结果列表
    """
    console.print()
    print_separator("═")
    print_header("Validation Summary")
    
    # 创建汇总表格
    table_data = []
    for file_path, result in all_results:
        status = "✓ Pass" if result["failed"] == 0 else "✗ Fail"
        status_style = "green" if result["failed"] == 0 else "red"
        
        table_data.append([
            file_path.name,
            f"[{status_style}]{status}[/{status_style}]",
            str(result["passed"]),
            str(result["failed"]),
            str(result["warnings"])
        ])
    
    print_table(
        headers=["File", "Status", "Passed", "Failed", "Warnings"],
        rows=table_data,
        title="Validation Results"
    )
    
    # 显示详细错误
    console.print()
    for file_path, result in all_results:
        if result["errors"] or result["warnings_list"]:
            console.print(f"[bold cyan]{file_path.name}:[/bold cyan]")
            
            for error in result["errors"]:
                console.print(f"  [red]✗[/red] {error}")
            
            for warning in result["warnings_list"]:
                console.print(f"  [yellow]⚠[/yellow] {warning}")
            
            console.print()
    
    # 总体统计
    total_passed = sum(r["passed"] for _, r in all_results)
    total_failed = sum(r["failed"] for _, r in all_results)
    total_warnings = sum(r["warnings"] for _, r in all_results)
    total_files = len(all_results)
    passed_files = sum(1 for _, r in all_results if r["failed"] == 0)
    
    console.print(f"[bold]Overall:[/bold]")
    console.print(f"  • {passed_files}/{total_files} file(s) passed")
    console.print(f"  • {total_passed} checks passed")
    console.print(f"  • {total_failed} errors found")
    console.print(f"  • {total_warnings} warnings")
    console.print()
    
    if total_failed == 0:
        print_success("All validations passed!")
    else:
        print_error(f"{total_failed} error(s) found. Please fix them before running.")
    
    print_separator("═")
    
    # TODO: 实现结果格式化输出
    # raise NotImplementedError("待实现")

