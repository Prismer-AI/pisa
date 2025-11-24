# PISA Capability System

**Version 2.0.0**

A unified system for managing and discovering capabilities (functions, agents, and MCP servers) in the PISA framework.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Components](#core-components)
- [Capability Types](#capability-types)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [Discovery System](#discovery-system)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)
- [Examples](#examples)

---

## Overview

The PISA Capability System provides a **unified interface** for managing three types of capabilities:

1. **Function Capabilities** - Python functions that can be called as tools
2. **Agent Capabilities** - AI agents that can be handed off to (subagents)
3. **MCP Capabilities** - Model Context Protocol servers that provide tools and resources

### Key Features

- 🎯 **Unified Registration** - Single decorator for all capability types
- 🔍 **Auto-Discovery** - Automatically discover capabilities from directories
- 📦 **Type-Safe** - Full Pydantic validation and type hints
- 🔌 **Pluggable** - Easy integration with OpenAI Agent SDK
- 🏷️ **Metadata-Rich** - Comprehensive metadata for each capability
- 🔄 **Hot-Reload** - Dynamic registration and discovery

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PISA Capability System                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐ │
│  │   Function   │      │    Agent     │      │   MCP    │ │
│  │ Capabilities │      │ Capabilities │      │ Servers  │ │
│  └──────┬───────┘      └──────┬───────┘      └────┬─────┘ │
│         │                     │                    │       │
│         └─────────────────────┼────────────────────┘       │
│                               │                            │
│                    ┌──────────▼──────────┐                 │
│                    │  @capability        │                 │
│                    │  Decorator          │                 │
│                    └──────────┬──────────┘                 │
│                               │                            │
│                    ┌──────────▼──────────┐                 │
│                    │  CapabilityRegistry │                 │
│                    │  - register()       │                 │
│                    │  - get()            │                 │
│                    │  - discover()       │                 │
│                    └──────────┬──────────┘                 │
│                               │                            │
│         ┌─────────────────────┼─────────────────────┐      │
│         │                     │                     │      │
│  ┌──────▼──────┐    ┌─────────▼────────┐   ┌──────▼────┐ │
│  │ Capability  │    │   Capabilities   │   │ Discovery │ │
│  │   Model     │    │     Helper       │   │  System   │ │
│  └─────────────┘    └──────────────────┘   └───────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns** - Clear separation between models, registry, and discovery
2. **Type Safety** - Pydantic models ensure data integrity
3. **Extensibility** - Easy to add new capability types
4. **Developer Experience** - Minimal boilerplate with powerful features

---

## Core Components

### 1. Capability Model

The `Capability` class is a Pydantic model that stores metadata about a capability:

```python
class Capability(BaseModel):
    name: str                              # Unique capability name
    description: str                       # Human-readable description
    parameters: Dict[str, Any]            # JSON schema for parameters
    capability_type: CapabilityType       # "function", "agent", or "mcp"
    tags: List[str]                       # Tags for categorization
    source: str                           # "internal" or "custom"
    
    # Type-specific fields
    agent_object: Optional[Any]           # For agent capabilities
    mcp_server_object: Optional[Any]      # For MCP capabilities
    agent_config: Optional[Dict]          # Agent metadata
    mcp_config: Optional[Dict]            # MCP metadata
```

**Key Methods:**
- `get_object()` - Get the native object (function, agent, or MCP server)
- `get_for_agent()` - Get object formatted for OpenAI Agent SDK
- `from_function()` - Create from a function
- `from_agent()` - Create from an Agent
- `from_mcp()` - Create from an MCP server

### 2. CapabilityRegistry

The central registry for managing all capabilities:

```python
class CapabilityRegistry:
    def register(self, capability: Capability, func: Optional[Callable] = None)
    def get(self, name: str) -> Optional[Capability]
    def list_all(self) -> List[str]
    def search(self, query: str) -> List[Capability]
    def discover_from_module(self, module_path: str) -> List[str]
    def discover_from_directory(self, directory: Path) -> List[str]
```

**Global Registry:**
```python
from pisa.capability import get_global_registry

registry = get_global_registry()
```

### 3. @capability Decorator

The unified decorator for registering capabilities:

```python
@capability(
    capability_type: CapabilityType,      # REQUIRED: "function", "agent", or "mcp"
    name: Optional[str] = None,           # Override capability name
    description: Optional[str] = None,    # Override description
    auto_register: bool = True,           # Auto-register to global registry
    tags: List[str] = [],                 # Categorization tags
    **kwargs                              # Additional metadata
)
```

### 4. Capabilities Helper

Convenient interface for accessing capabilities:

```python
from pisa.capability import Capabilities

caps = Capabilities()

# Get any capability by name
func = caps['my_function']
agent = caps['my_agent']
mcp = caps['my_mcp_server']

# Get all of a specific type
functions = caps.get_functions()      # List[FunctionTool]
agents = caps.get_agents()            # List[Agent]
mcp_servers = caps.get_mcp_servers()  # List[MCPServer]
```

---

## Capability Types

### 1. Function Capabilities

Functions that can be called as tools by agents.

**Characteristics:**
- Synchronous or asynchronous
- Automatically wrapped with `@function_tool` decorator
- JSON schema auto-generated from type hints
- Can be regular functions or class methods

**Example:**

```python
from pisa.capability import capability
from agents import function_tool

@capability(capability_type="function", tags=["web", "crawling"])
@function_tool
async def crawl_webpage(url: str) -> str:
    """
    Crawl a webpage and return its content.
    
    Args:
        url: The URL to crawl
        
    Returns:
        The webpage content as text
    """
    # Implementation
    return "webpage content"
```

**Notes:**
- If `@function_tool` is not present, `@capability` will automatically apply it
- The decorator extracts function name, docstring, and parameter types
- Supports both sync and async functions

### 2. Agent Capabilities

AI agents that can be handed off to (subagents).

**Characteristics:**
- Instances of OpenAI Agent SDK `Agent` class
- Can be registered directly or via factory functions
- Support handoff descriptions for context switching
- Isolated execution environments

**Example (Direct Registration):**

```python
from pisa.capability import capability
from agents import Agent

@capability(capability_type="agent", name="joke_agent")
def create_joke_agent():
    return Agent(
        name="joke_agent",
        instructions="You are a comedian. Tell jokes.",
        handoff_description="Transfer to this agent for jokes and humor"
    )
```

**Example (Factory Pattern):**

```python
@capability(capability_type="agent")
def create_data_analyst():
    """Factory function that creates and returns an Agent"""
    return Agent(
        name="data_analyst",
        instructions="Analyze data and generate insights",
        tools=[analyze_data, create_chart],
        handoff_description="Analyze data and create visualizations"
    )
```

**Notes:**
- Factory functions are auto-called if they have no required parameters
- The returned Agent object is registered as a capability
- Use `handoff_description` to guide when the agent should be used

### 3. MCP Capabilities

Model Context Protocol servers that provide tools and resources.

**Characteristics:**
- Instances of `MCPServer` from OpenAI Agent SDK
- Can provide multiple tools
- Support structured content
- Can be local or remote

**Example:**

```python
from pisa.capability import capability
from agents.mcp.server import MCPServerStdio

@capability(capability_type="mcp", name="math_mcp")
def create_math_server():
    return MCPServerStdio(
        params={
            "command": "python",
            "args": ["math_server.py"]
        }
    )
```

**Notes:**
- MCP servers are registered as single capabilities
- Individual tools within the MCP are not separately registered
- The agent SDK handles routing calls to MCP tools

---

## Quick Start

### Installation

```bash
pip install pisa
```

### 1. Create a Simple Function Capability

```python
from pisa.capability import capability
from agents import function_tool

@capability(capability_type="function")
@function_tool
async def greet(name: str) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"
```

### 2. Access the Capability

```python
from pisa.capability import Capabilities

caps = Capabilities()

# Get the function
greet_func = caps['greet']

# Call it
result = await greet_func("Alice")
print(result)  # "Hello, Alice!"
```

### 3. Use in an Agent

```python
from agents import Agent
from pisa.capability import Capabilities

caps = Capabilities()

agent = Agent(
    name="assistant",
    instructions="You are a helpful assistant",
    tools=caps.get_functions()  # All function capabilities
)

result = agent.run("Greet Bob")
print(result.output)
```

---

## Usage Guide

### Creating Capabilities

#### Function Capabilities

**Basic Function:**

```python
@capability(capability_type="function", tags=["math"])
@function_tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
```

**Async Function:**

```python
@capability(capability_type="function", tags=["web"])
@function_tool
async def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text
```

**Class-Based Function:**

```python
@capability(capability_type="function")
class SearchTool:
    """Search tool with state"""
    
    def __init__(self):
        self.client = SearchClient()
    
    @function_tool
    async def run(self, query: str) -> str:
        """Search for information."""
        return await self.client.search(query)
```

#### Agent Capabilities

**Simple Agent:**

```python
@capability(capability_type="agent", name="translator")
def create_translator():
    return Agent(
        name="translator",
        instructions="You are a translator. Translate text between languages.",
        handoff_description="Use this agent to translate text"
    )
```

**Agent with Tools:**

```python
@capability(capability_type="agent")
def create_researcher():
    caps = Capabilities()
    
    return Agent(
        name="researcher",
        instructions="Research topics using web search",
        tools=[
            caps['search_web'],
            caps['crawl_webpage']
        ],
        handoff_description="Research topics using web search"
    )
```

#### MCP Capabilities

**Simple MCP Server:**

```python
@capability(capability_type="mcp", name="filesystem_mcp")
def create_filesystem_mcp():
    return MCPServerStdio(
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        }
    )
```

### Registering Capabilities

#### Auto-Registration (Recommended)

Capabilities are automatically registered when decorated:

```python
@capability(capability_type="function")  # Auto-registered
@function_tool
async def my_tool(x: int) -> int:
    return x * 2
```

#### Manual Registration

```python
from pisa.capability import get_global_registry, Capability

registry = get_global_registry()

# Register a function manually
cap = Capability.from_function(
    func=my_function,
    name="my_function",
    description="Does something useful"
)
registry.register(cap, my_function)

# Register an agent manually
agent = Agent(name="my_agent", instructions="...")
registry.register_agent(agent)

# Register an MCP server manually
mcp_server = MCPServerStdio(...)
registry.register_mcp(mcp_server)
```

### Accessing Capabilities

#### Using Capabilities Helper

```python
from pisa.capability import Capabilities

caps = Capabilities()

# By name
tool = caps['my_tool']

# With default
tool = caps.get('my_tool', default=None)

# Get all functions
functions = caps.get_functions()

# Get all agents
agents = caps.get_agents()

# Get all MCP servers
mcp_servers = caps.get_mcp_servers()

# List all names
all_names = caps.list_all()
```

#### Using Registry Directly

```python
from pisa.capability import get_global_registry

registry = get_global_registry()

# Get capability metadata
cap = registry.get('my_tool')
print(cap.name, cap.description, cap.parameters)

# Get the actual function/agent/mcp
func = cap.get_object()

# Search capabilities
results = registry.search('web')
```

---

## Discovery System

### Discover from Module

```python
from pisa.capability import get_global_registry

registry = get_global_registry()

# Discover from a Python module
discovered = registry.discover_from_module('pisa.capability.local.functions')
print(f"Discovered {len(discovered)} capabilities")
```

### Discover from Directory

```python
from pathlib import Path

# Discover all capabilities in a directory
discovered = registry.discover_from_directory(
    directory=Path("./my_capabilities"),
    pattern="*.py",
    recursive=True
)

print(f"Discovered: {discovered}")
```

### Auto-Discovery in PISA

PISA automatically discovers capabilities from:

1. **Internal Capabilities**: `src/pisa/capability/local/`
   - `functions/` - Built-in function tools
   - `subagent/` - Built-in agents
   - `mcp/` - Built-in MCP servers

2. **Custom Capabilities**: `.prismer/capability/`
   - `function/` - User-defined functions
   - `subagent/` - User-defined agents
   - `mcp/` - User-defined MCP servers

**Directory Structure:**

```
project/
├── .prismer/
│   └── capability/
│       ├── function/
│       │   └── my_tool.py
│       ├── subagent/
│       │   └── my_agent.py
│       └── mcp/
│           └── my_mcp.py
└── src/
    └── pisa/
        └── capability/
            └── local/
                ├── functions/
                ├── subagent/
                └── mcp/
```

---

## Best Practices

### 1. Use Type Hints

Always use type hints for function parameters and return types:

```python
@capability(capability_type="function")
@function_tool
async def process_data(
    input_text: str,
    max_length: int = 100
) -> Dict[str, Any]:
    """
    Process input text.
    
    Args:
        input_text: The text to process
        max_length: Maximum length of output
        
    Returns:
        Dictionary with processed results
    """
    return {"processed": input_text[:max_length]}
```

### 2. Write Clear Docstrings

Docstrings are used as capability descriptions:

```python
@capability(capability_type="function")
@function_tool
def search_papers(query: str, max_results: int = 10) -> List[Dict]:
    """
    Search for academic papers using the query.
    
    This tool searches multiple academic databases including
    arXiv, PubMed, and Google Scholar.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        List of paper metadata dictionaries
    """
    pass
```

### 3. Use Tags for Organization

Tags help organize and filter capabilities:

```python
@capability(
    capability_type="function",
    tags=["web", "crawling", "external"]
)
@function_tool
async def crawl_webpage(url: str) -> str:
    """Crawl a webpage."""
    pass
```

### 4. Follow Naming Conventions

- **Functions**: Use verb-based names (`fetch_data`, `process_text`)
- **Agents**: Use noun-based names (`translator`, `data_analyst`)
- **MCP Servers**: Use descriptive names (`filesystem_mcp`, `github_mcp`)

```python
# Good
@capability(capability_type="function", name="fetch_weather")
@capability(capability_type="agent", name="code_reviewer")
@capability(capability_type="mcp", name="database_mcp")

# Avoid
@capability(capability_type="function", name="tool1")
@capability(capability_type="agent", name="agent_helper")
```

### 5. Handle Errors Gracefully

```python
@capability(capability_type="function")
@function_tool
async def fetch_url(url: str) -> str:
    """Fetch URL content with error handling."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.text
    except httpx.TimeoutException:
        return "Error: Request timed out"
    except httpx.HTTPError as e:
        return f"Error: HTTP error {e.response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"
```

### 6. Use Factory Functions for Complex Setup

```python
@capability(capability_type="agent")
def create_research_agent():
    """Factory function for research agent with complex setup."""
    
    # Load configuration
    config = load_agent_config("research")
    
    # Initialize tools
    caps = Capabilities()
    tools = [
        caps['search_web'],
        caps['fetch_webpage'],
        caps['extract_text']
    ]
    
    # Create agent with configuration
    return Agent(
        name="researcher",
        instructions=config["instructions"],
        model=config["model"],
        tools=tools,
        handoff_description="Research topics using web search"
    )
```

### 7. Test Capabilities

```python
import pytest
from pisa.capability import get_global_registry

def test_my_capability():
    registry = get_global_registry()
    
    # Get capability
    cap = registry.get('my_tool')
    assert cap is not None
    
    # Get function
    func = cap.get_object()
    
    # Test execution
    result = func(input_data="test")
    assert result is not None
```

---

## API Reference

### Capability Model

```python
class Capability(BaseModel):
    """Capability metadata model."""
    
    name: str
    description: str
    parameters: Dict[str, Any]
    capability_type: Literal["function", "agent", "mcp"]
    tags: List[str] = []
    source: str = "custom"
    
    # Type-specific fields
    agent_object: Optional[Any] = None
    mcp_server_object: Optional[Any] = None
    agent_config: Optional[Dict] = None
    mcp_config: Optional[Dict] = None
    
    # Methods
    def get_object(self, registry=None) -> Any: ...
    def get_for_agent(self) -> Any: ...
    def to_dict(self) -> Dict: ...
    
    @classmethod
    def from_function(cls, func: Callable, ...) -> 'Capability': ...
    
    @classmethod
    def from_agent(cls, agent: Any, ...) -> 'Capability': ...
    
    @classmethod
    def from_mcp(cls, mcp_server: Any, ...) -> 'Capability': ...
```

### CapabilityRegistry

```python
class CapabilityRegistry:
    """Registry for managing capabilities."""
    
    def __init__(self, auto_register: bool = True): ...
    
    def register(self, capability: Capability, func: Optional[Callable] = None) -> None: ...
    
    def register_agent(self, agent: Any, name: Optional[str] = None, 
                      description: Optional[str] = None) -> Capability: ...
    
    def register_mcp(self, mcp_server: Any, name: Optional[str] = None,
                    description: Optional[str] = None) -> Capability: ...
    
    def get(self, name: str) -> Optional[Capability]: ...
    
    def get_function(self, name: str) -> Optional[Callable]: ...
    
    def list_all(self) -> List[str]: ...
    
    def get_all(self) -> Dict[str, Capability]: ...
    
    def search(self, query: str) -> List[Capability]: ...
    
    def clear(self) -> None: ...
    
    def discover_from_module(self, module_path: str) -> List[str]: ...
    
    def discover_from_directory(
        self,
        directory: Union[str, Path],
        pattern: str = "*.py",
        recursive: bool = True
    ) -> List[str]: ...
```

### @capability Decorator

```python
def capability(
    capability_type: Literal["function", "agent", "mcp"],
    name: Optional[str] = None,
    description: Optional[str] = None,
    registry: Optional[CapabilityRegistry] = None,
    auto_register: bool = True,
    tags: List[str] = [],
    **kwargs
) -> Callable: ...
```

**Parameters:**
- `capability_type` (required): Type of capability ("function", "agent", or "mcp")
- `name`: Override the capability name
- `description`: Override the description
- `registry`: Registry to register with (defaults to global)
- `auto_register`: Whether to auto-register (default: True)
- `tags`: List of tags for categorization
- `**kwargs`: Additional metadata

### Capabilities Helper

```python
class Capabilities:
    """Helper for accessing capabilities."""
    
    def __init__(self, registry: Optional[CapabilityRegistry] = None): ...
    
    def __getitem__(self, key: str) -> Any: ...
    
    def get(self, key: str, default: Any = None) -> Any: ...
    
    def get_capability(self, key: str) -> Optional[Capability]: ...
    
    def get_functions(self) -> List[Any]: ...
    
    def get_agents(self) -> List[Any]: ...
    
    def get_mcp_servers(self) -> List[Any]: ...
    
    def list_all(self) -> List[str]: ...
    
    def __iter__(self): ...
    
    def __len__(self) -> int: ...
```

### Global Functions

```python
def get_global_registry() -> CapabilityRegistry:
    """Get or create the global registry instance."""
    ...
```

---

## Examples

### Example 1: Simple Search Tool

```python
from pisa.capability import capability
from agents import function_tool
import httpx

@capability(
    capability_type="function",
    tags=["search", "web", "external"]
)
@function_tool
async def search_web(query: str, num_results: int = 10) -> str:
    """
    Search the web using a search API.
    
    Args:
        query: Search query string
        num_results: Number of results to return (default: 10)
        
    Returns:
        Formatted search results
    """
    # Implementation
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.search.com/search",
            params={"q": query, "n": num_results}
        )
        return response.json()
```

### Example 2: Data Analyst Agent

```python
from pisa.capability import capability, Capabilities
from agents import Agent

@capability(capability_type="agent", name="data_analyst")
def create_data_analyst():
    """
    Creates a data analyst agent that can process and visualize data.
    """
    caps = Capabilities()
    
    return Agent(
        name="data_analyst",
        instructions="""
        You are a data analyst. You can:
        1. Analyze datasets
        2. Generate statistical insights
        3. Create visualizations
        4. Identify trends and patterns
        """,
        tools=[
            caps['analyze_data'],
            caps['create_chart'],
            caps['calculate_statistics']
        ],
        handoff_description=(
            "Transfer to this agent when you need to analyze data, "
            "generate statistics, or create visualizations"
        )
    )
```

### Example 3: Filesystem MCP Server

```python
from pisa.capability import capability
from agents.mcp.server import MCPServerStdio

@capability(
    capability_type="mcp",
    name="filesystem_mcp",
    tags=["filesystem", "io"]
)
def create_filesystem_mcp():
    """
    Creates an MCP server for filesystem operations.
    
    Provides tools for reading, writing, and listing files.
    """
    return MCPServerStdio(
        params={
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                "/allowed/path"
            ]
        }
    )
```

### Example 4: Using Capabilities in an Agent

```python
from agents import Agent
from pisa.capability import Capabilities

# Initialize capabilities helper
caps = Capabilities()

# Create agent with function tools
agent = Agent(
    name="assistant",
    instructions="You are a helpful assistant with access to various tools.",
    tools=caps.get_functions(),           # All function capabilities
    handoffs=caps.get_agents(),           # All agent capabilities
    mcp_servers=caps.get_mcp_servers()    # All MCP capabilities
)

# Run agent
result = agent.run("Search for information about Python")
print(result.output)
```

### Example 5: Dynamic Capability Discovery

```python
from pathlib import Path
from pisa.capability import get_global_registry, Capabilities

# Get registry
registry = get_global_registry()

# Discover from custom directory
custom_dir = Path("./my_capabilities")
discovered = registry.discover_from_directory(custom_dir)

print(f"Discovered {len(discovered)} capabilities:")
for name in discovered:
    cap = registry.get(name)
    print(f"  - {cap.name} ({cap.capability_type}): {cap.description}")

# Use discovered capabilities
caps = Capabilities()
tool = caps['my_custom_tool']
```

---

## Migration Guide

### From v1.x to v2.0

**Key Changes:**

1. **Decorator Signature** - `capability_type` is now required:

```python
# Old (v1.x)
@capability(name="my_tool")
def my_tool(): ...

# New (v2.0)
@capability(capability_type="function", name="my_tool")
def my_tool(): ...
```

2. **Auto @function_tool** - No need to manually apply `@function_tool`:

```python
# Old (v1.x)
@function_tool
@capability(name="my_tool")
def my_tool(): ...

# New (v2.0) - @function_tool applied automatically
@capability(capability_type="function")
def my_tool(): ...

# Or explicit order
@capability(capability_type="function")
@function_tool
def my_tool(): ...
```

3. **Registry Access** - New `Capabilities` helper class:

```python
# Old (v1.x)
from pisa.capability import get_global_registry
registry = get_global_registry()
func = registry.get_function('my_tool')

# New (v2.0)
from pisa.capability import Capabilities
caps = Capabilities()
func = caps['my_tool']
```

---

## Troubleshooting

### Issue: Capability Not Found

**Problem:** `KeyError: "Capability 'my_tool' not found"`

**Solutions:**
1. Ensure the capability is decorated with `@capability`
2. Check that the module containing the capability has been imported
3. Verify `auto_register=True` (default)

```python
# Check what's registered
from pisa.capability import get_global_registry
registry = get_global_registry()
print(registry.list_all())
```

### Issue: Agent Not Appearing in Handoffs

**Problem:** Agent capability registered but not available for handoff

**Solution:** Ensure `capability_type="agent"` is specified:

```python
@capability(capability_type="agent")  # Must specify "agent"
def create_my_agent():
    return Agent(...)
```

### Issue: @function_tool Not Applied

**Problem:** Function not working as a tool

**Solution:** Either explicitly apply `@function_tool` or ensure `@capability` is used:

```python
# Option 1: Explicit @function_tool
@capability(capability_type="function")
@function_tool
async def my_tool(): ...

# Option 2: Let @capability apply it
@capability(capability_type="function")
async def my_tool(): ...
```

### Issue: MCP Server Not Registered

**Problem:** MCP server not appearing in capabilities

**Solution:** Ensure the factory function returns an MCP server instance:

```python
@capability(capability_type="mcp")
def create_mcp():
    return MCPServerStdio(...)  # Must return MCP server instance
```

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

### Adding New Capability Types

To add a new capability type:

1. Add the type to `CapabilityType` in `models.py`
2. Implement `from_<type>()` method in `Capability` class
3. Add handling in `@capability` decorator
4. Update documentation

---

## License

Copyright 2025 Prismer

Licensed under the Apache License, Version 2.0. See [LICENSE](../../LICENSE.txt) for details.

---

## Support

- **Documentation**: [PISA Documentation](../../docs/)
- **Issues**: [GitHub Issues](https://github.com/prismer/pisa/issues)
- **Discussions**: [GitHub Discussions](https://github.com/prismer/pisa/discussions)

---

**Built with ❤️ by the PISA Team**

