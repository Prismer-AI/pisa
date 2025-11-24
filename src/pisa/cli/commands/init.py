"""
Init Command

职责：
1. 初始化PISA项目结构
2. 创建.prismer目录和子目录
3. 复制agent模板
4. 生成.gitignore

使用示例：
```bash
pisa init
pisa init --path ./my_project
```
"""

import click
import shutil
from pathlib import Path
from typing import Optional

from pisa.cli.ui import (
    print_success,
    print_error,
    print_warning,
    print_info,
    display_icon,
    console
)
from pisa.utils.logger import get_logger

_logger = get_logger(__name__)


def create_project_structure(base_path: Path) -> None:
    """
    创建完整的项目目录结构
    
    Args:
        base_path: 基础路径（.prismer目录）
    """
    # 主目录
    base_path.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]✓[/green] Created directory: [cyan]{base_path}[/cyan]")
    
    # cache/ 目录
    cache_dir = base_path / "cache"
    cache_dir.mkdir(exist_ok=True)
    (cache_dir / ".gitkeep").touch()
    console.print(f"[green]✓[/green] Created cache directory: [cyan]{cache_dir}[/cyan]")
    
    # capability/ 目录和子目录
    capability_dir = base_path / "capability"
    capability_dir.mkdir(exist_ok=True)
    
    for subdir in ["function", "subagent", "mcp"]:
        sub_path = capability_dir / subdir
        sub_path.mkdir(exist_ok=True)
        
        # 创建__init__.py
        init_file = sub_path / "__init__.py"
        init_file.write_text(f'"""\n{subdir.capitalize()} Capabilities\n"""\n')
        
        # 创建.gitkeep
        (sub_path / ".gitkeep").touch()
        
        console.print(f"[green]✓[/green] Created capability/{subdir}: [cyan]{sub_path}[/cyan]")
    
    # loop/ 目录
    loop_dir = base_path / "loop"
    loop_dir.mkdir(exist_ok=True)
    (loop_dir / "__init__.py").write_text('"""\nCustom Loop Templates\n"""\n')
    (loop_dir / ".gitkeep").touch()
    console.print(f"[green]✓[/green] Created loop directory: [cyan]{loop_dir}[/cyan]")


def copy_agent_template(base_path: Path, template_type: str = "example") -> None:
    """
    复制agent模板文件
    
    Args:
        base_path: 基础路径（.prismer目录）
        template_type: 模板类型 ("basic" 或 "example")
    """
    target_path = base_path / "agent.md"
    
    if template_type == "example":
        # 使用 pisa_example 的完整模板
        example_template_path = Path(__file__).parent.parent.parent.parent.parent / "example" / "pisa_example" / ".prismer" / "agent.md"
        
        if example_template_path.exists():
            shutil.copy2(example_template_path, target_path)
            console.print(f"[green]✓[/green] Copied example agent template to: [cyan]{target_path}[/cyan]")
            return
        else:
            console.print(f"[yellow]⚠[/yellow] Example template not found at {example_template_path}, falling back to basic template...")
            template_type = "basic"
    
    if template_type == "basic":
        # 查找基本模板文件
        template_sources = [
            # 优先使用core/definition中的模板
            Path(__file__).parent.parent.parent / "core" / "definition" / "templates" / "agent_template.md",
            # 备用：agents/proto中的模板
            Path(__file__).parent.parent.parent / "agents" / "proto" / "template.md",
        ]
        
        template_path = None
        for source in template_sources:
            if source.exists():
                template_path = source
                break
        
        if template_path and template_path.exists():
            shutil.copy2(template_path, target_path)
            console.print(f"[green]✓[/green] Copied basic agent template to: [cyan]{target_path}[/cyan]")
        else:
            # 如果模板不存在，创建一个最小的模板
            console.print(f"[yellow]⚠[/yellow] Template file not found, creating minimal template...")
            
            basic_template = """---
# Agent Definition
name: my_agent
description: My PISA Agent
version: 1.0.0
loop_type: plan_execute

model:
  default_model: gpt-4o-mini
  temperature: 0.7
  max_tokens: 4096

capabilities: []

planning:
  enabled: true
  max_iterations: 10

runtime:
  max_iterations: 10
  timeout_seconds: 300
---

# System Prompt

You are an intelligent agent designed to help users accomplish tasks.
"""
            target_path.write_text(basic_template)
            console.print(f"[green]✓[/green] Created minimal agent template: [cyan]{target_path}[/cyan]")


def create_pyproject(base_path: Path, project_name: str) -> None:
    """
    创建 pyproject.toml 用于管理用户自定义依赖
    
    注意：用户项目是 PISA 的"插件"，不声明对 PISA 的依赖。
    PISA 框架必须已经安装在环境中。
    
    Args:
        base_path: 基础路径（.prismer目录）
        project_name: 项目名称
    """
    pyproject_content = f"""[project]
name = "{project_name}"
version = "0.1.0"
description = "A PISA agent project"
requires-python = ">=3.11"

# ============ Custom Dependencies ============
# This project is a PISA plugin/extension.
# PISA framework must be installed separately:
#   - Development: uv pip install -e /path/to/pisa
#   - Production:  uv pip install pisa
#
# Only declare YOUR additional dependencies here:
dependencies = [
    # "pandas>=2.0.0",      # For data processing
    # "numpy>=1.24.0",       # For numerical computing
    # "requests>=2.31.0",    # For HTTP requests
    # "scikit-learn>=1.3.0", # For machine learning
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]

[project.scripts]
# Optional: Add custom CLI commands for your agent
# {project_name} = "capability.function.main:cli"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["capability*"]
"""
    
    pyproject_path = base_path / "pyproject.toml"
    pyproject_path.write_text(pyproject_content)
    console.print(f"[green]✓[/green] Created pyproject.toml: [cyan]{pyproject_path}[/cyan]")


def create_env_example(base_path: Path) -> None:
    """
    创建 .env.example 配置文件模板
    
    Args:
        base_path: 基础路径（.prismer目录）
    """
    env_content = """# ============ OpenAI Configuration (Required) ============
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_API_BASE_URL=https://api.openai.com/v1
AGENT_DEFAULT_MODEL=gpt-4o-mini
# OPENAI_API_TRACE_KEY=your-trace-key  # Optional: For tracing

# ============ Search Capabilities (Optional) ============
# Web Search (Serper API)
SERPER_API_KEY=your-serper-api-key
# SEARCH_API_KEY=your-search-api-key  # Alternative name

# Exa Search
EXASEARCH_API_KEY=your-exa-api-key
# EXA_API_KEY=your-exa-api-key  # Alternative name

# ============ Google Cloud / Gemini (Optional) ============
# For image generation
GOOGLE_PROJECT_ID=your-google-project-id
# GOOGLE_LOCATION=us-central1
# GEMINI_IMAGE_MODEL=imagen-3.0-generate-001

# ============ System Configuration (Optional) ============
PISA_DEBUG=false
# LOG_LEVEL=INFO
# ENVIRONMENT=development

# ============ Instructions ============
# 1. Copy this file to .env: cp .env.example .env
# 2. Fill in your actual API keys
# 3. Never commit .env to version control (it's in .gitignore)
# 4. Rotate API keys regularly for security
"""
    
    env_path = base_path / ".env.example"
    env_path.write_text(env_content)
    console.print(f"[green]✓[/green] Created .env.example: [cyan]{env_path}[/cyan]")


def create_gitignore(base_path: Path) -> None:
    """
    创建.gitignore文件
    
    Args:
        base_path: 基础路径（.prismer目录）
    """
    gitignore_content = """# Environment Variables
.env

# PISA Cache
cache/context.md
cache/*.json
cache/*.pkl

# Python
__pycache__/
*.py[cod]
*$py.class
*.so

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Temporary files
*.tmp
*.temp
.gitkeep
"""
    
    gitignore_path = base_path / ".gitignore"
    gitignore_path.write_text(gitignore_content)
    console.print(f"[green]✓[/green] Created .gitignore: [cyan]{gitignore_path}[/cyan]")


def create_readme(base_path: Path) -> None:
    """
    创建README.md
    
    Args:
        base_path: 基础路径（.prismer目录）
    """
    readme_content = """# PISA Project

This is a PISA agent project initialized with `pisa init`.

## Prerequisites

**PISA Framework Required**: This project is a PISA plugin/extension and requires the PISA framework to be installed.

### Install PISA Framework

**Option 1: Development Environment** (if working on PISA itself)
```bash
cd /path/to/pisa
uv pip install -e .
```

**Option 2: Production Environment** (using released version)
```bash
uv pip install pisa
```

## Directory Structure

```
.prismer/
├── agent.md            # Agent definition
├── pyproject.toml      # Custom dependencies
├── .env.example        # Configuration template (copy to .env)
├── .gitignore          # Git ignore rules
├── README.md           # Project documentation
├── cache/              # Cache directory for context and intermediate data
├── capability/         # Custom capabilities
│   ├── function/       # Function-type capabilities
│   ├── subagent/       # Subagent-type capabilities
│   └── mcp/            # MCP-type capabilities
└── loop/               # Custom loop templates
```

## Getting Started

1. **Configure Environment**: Set up your API keys and configuration:
   ```bash
   cd .prismer
   cp .env.example .env
   # Edit .env and fill in your API keys
   ```

2. **Install Dependencies**: If your capabilities need additional packages:
   ```bash
   # Edit pyproject.toml to add your dependencies
   uv pip install -e .
   ```

3. **Edit Agent Definition**: Modify `agent.md` to configure your agent

4. **Implement Capabilities**: Add your capabilities in `capability/` directories

5. **Validate**: Run `pisa validate agent.md` to check configuration

6. **Run**: Execute `pisa run agent.md` to start your agent

## Capability Development

### Function Capability

Create a Python file in `capability/function/`:

```python
from pisa.capability import capability, CapabilityType

@capability(
    name="my_function",
    description="My function capability",
    capability_type=CapabilityType.FUNCTION
)
async def my_function(param: str) -> dict:
    return {"result": param}
```

### Subagent Capability

Create a Python file in `capability/subagent/`:

```python
from pisa.capability import capability, CapabilityType
from pisa.config import Config
from agents import Agent, Runner

@capability(
    name="my_subagent",
    description="My subagent capability",
    capability_type=CapabilityType.AGENT
)
async def my_subagent(task: str) -> dict:
    agent = Config.create_agent(
        name="subagent",
        instructions="...",
        model="openai/gpt-oss-120b"
    )
    runner = Runner(agent=agent)
    result = await runner.run(messages=[{"role": "user", "content": task}])
    return {"result": result.content}
```

## Documentation

- [Developer Guide](https://github.com/your-org/pisa/docs/DEVELOPER_GUIDE.md)
- [API Reference](https://github.com/your-org/pisa/docs/API_REFERENCE.md)
"""
    
    readme_path = base_path / "README.md"
    readme_path.write_text(readme_content)
    console.print(f"[green]✓[/green] Created README.md: [cyan]{readme_path}[/cyan]")


@click.command(name="init", context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "project_name",
    type=str,
    required=False,
    default=None,
)
@click.option(
    "--path",
    "-p",
    type=click.Path(),
    default=None,
    help="Project path (default: current directory or project_name if provided)"
)
@click.option(
    "--name",
    "-n",
    type=str,
    default=None,
    help="Override project name (default: directory name or project_name argument)"
)
@click.option(
    "--template",
    "-t",
    type=click.Choice(["basic", "example"], case_sensitive=False),
    default="example",
    help="Agent template to use (basic: minimal template, example: full example from pisa_example)"
)
def init_command(project_name: Optional[str], path: Optional[str], name: Optional[str], template: str) -> None:
    """
    Initialize a new PISA project
    
    Usage:
        pisa init                    # Create .prismer in current directory
        pisa init my_agent           # Create my_agent/.prismer directory
        pisa init --path /some/path  # Create .prismer at specified path
    
    Creates the .prismer directory structure with:
    - agent.md template
    - pyproject.toml for custom dependencies
    - .env.example for configuration
    - cache/ directory
    - capability/ directories (function, subagent, mcp)
    - loop/ directory for custom loops
    - .gitignore and README.md
    """
    display_icon()
    console.print()
    console.print("[bold blue]Initializing PISA project...[/bold blue]")
    console.print()
    
    try:
        # 确定项目路径
        if path:
            # 如果指定了 --path，使用指定路径
            project_path = Path(path).resolve()
        elif project_name:
            # 如果提供了 project_name 参数，在当前目录下创建该文件夹
            project_path = Path.cwd() / project_name
            project_path.mkdir(parents=True, exist_ok=True)
        else:
            # 都没有，在当前目录创建
            project_path = Path.cwd()
        
        # 确定项目名称
        if name is None:
            # 优先使用 project_name 参数，否则使用目录名
            name = project_name if project_name else project_path.name
        
        console.print(f"[dim]Project path:[/dim] [cyan]{project_path}[/cyan]")
        console.print(f"[dim]Project name:[/dim] [cyan]{name}[/cyan]")
        console.print()
        
        # 创建.prismer目录
        prismer_dir = project_path / ".prismer"
        
        if prismer_dir.exists():
            console.print(f"[yellow]⚠ Directory already exists: {prismer_dir}[/yellow]")
            if not click.confirm("Do you want to continue and overwrite?", default=False):
                console.print("[yellow]Initialization cancelled[/yellow]")
                return
            console.print()
        
        # 创建项目结构
        create_project_structure(prismer_dir)
        console.print()
        
        # 复制模板
        copy_agent_template(prismer_dir, template)
        console.print()
        
        # 创建 pyproject.toml
        create_pyproject(prismer_dir, name)
        console.print()
        
        # 创建 .env.example
        create_env_example(prismer_dir)
        console.print()
        
        # 创建.gitignore
        create_gitignore(prismer_dir)
        console.print()
        
        # 创建README
        create_readme(prismer_dir)
        console.print()
        
        # 成功消息
        console.print("[bold green]✓ Project initialized successfully![/bold green]")
        console.print()
        console.print("[dim]Next steps:[/dim]")
        if project_name:
            console.print(f"  1. Navigate to project: [cyan]cd {project_name}[/cyan]")
            console.print(f"  2. Configure environment: [cyan]cd .prismer && cp .env.example .env && vim .env[/cyan]")
            console.print(f"  3. Install dependencies: [cyan]uv pip install -e .prismer[/cyan]")
            console.print(f"  4. Validate configuration: [cyan]pisa validate .prismer/agent.md[/cyan]")
            console.print(f"  5. Run your agent: [cyan]pisa run .prismer/agent.md[/cyan]")
        else:
            console.print("  1. Configure environment: [cyan]cd .prismer && cp .env.example .env && vim .env[/cyan]")
            console.print("  2. Install dependencies: [cyan]uv pip install -e .prismer[/cyan]")
            console.print("  3. Validate configuration: [cyan]pisa validate .prismer/agent.md[/cyan]")
            console.print("  4. Run your agent: [cyan]pisa run .prismer/agent.md[/cyan]")
        console.print()
        
        _logger.info(f"PISA project initialized at {prismer_dir}")
        
    except Exception as e:
        console.print()
        print_error(f"Failed to initialize project: {e}")
        _logger.error(f"Initialization failed: {e}", exc_info=True)
        raise click.Abort()



