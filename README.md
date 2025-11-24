<div align="center">
  <img src="docs/icon.png" alt="PISA Logo" width="400"/>
  
# PISA 
  
  ### Planning, Intelligent, Self-Adaptive Agent Framework
  
  *Build production-ready AI agents with markdown-defined workflows*
  
  [![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
  [![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE.txt)
  [![OpenAI Agent SDK](https://img.shields.io/badge/OpenAI-Agent%20SDK-412991.svg)](https://openai.github.io/openai-agents-python/)
  [![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)
  
  [Quick Start](#-quick-start) •
  [Documentation](#-documentation) •
  [Examples](#-examples) •
  [Features](#-features) •
  [Contributing](#-contributing)
  
</div>

---

## 🌟 What is PISA?

**PISA** (Prismer Intelligence Server Agents) is a next-generation AI agent framework built on top of the [OpenAI Agent SDK](https://openai.github.io/openai-agents-python/). It enables developers to create sophisticated, production-ready AI agents using **markdown-based configuration** and **modular architecture**.

### Why PISA?

- 🎯 **Markdown-First**: Define agents, tools, and workflows entirely in markdown files
- 🔧 **Modular Design**: Compose agents from reusable modules (Planning, Execution, Observation, Reflection)
- 🛠️ **Rich Tooling**: Built-in support for Functions, MCP Servers, and Subagents
- 📊 **Observable**: Real-time execution tracking with beautiful CLI output powered by [Rich](https://github.com/Textualize/rich)
- 🔄 **Event-Driven**: Production-ready deployment with [Temporal](https://temporal.io/) integration
- 🎨 **Developer-Friendly**: Intuitive CLI, comprehensive logging, and extensive documentation
- **Context Enginnering**： 1st version ‘Pyramid Context Engineering’ solution 

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pisa.git
cd pisa

# Install dependencies (using uv for faster installation)
uv pip install -e .

# Or using pip
pip install -e .
```

### Configure Environment

Create a `.env` file in the project root:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# Default Model
AGENT_DEFAULT_MODEL=gpt-4o-mini

# Optional: Temporal Configuration
TEMPORAL_ADDRESS=localhost:7233
```

### Create Your First Agent

1. **Initialize a new agent project:**

```bash
pisa init my-agent
cd my-agent
```

2. **Define your agent in `.prismer/agent.md`:**

```yaml
---
name: my-first-agent
version: 1.0.0
description: A simple agent that performs calculations
loop_type: plan_execute

capabilities:
  - calculator
  - text_to_table

planning:
  max_iterations: 10
  
# ... more configuration
---

## Planning Instructions

You are a helpful mathematical assistant. Break down complex calculations into steps.

## Reflection Guidelines

After each calculation, verify the result makes sense.
```

3. **Define capabilities in `.prismer/capability/function/`:**

```python
from pisa.capability import capability
from agents.extensions.function_tool import function_tool

@capability(
    name="calculator",
    description="Perform basic mathematical operations",
    capability_type="function",
    tags=["math", "calculation"]
)
def calculator(operation: str, a: float, b: float) -> float:
    """
    Perform a mathematical operation.
    
    Args:
        operation: The operation (add, subtract, multiply, divide)
        a: First number
        b: Second number
    """
    ops = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y
    }
    return ops[operation](a, b)
```

4. **Run your agent:**

```bash
# Validate configuration
pisa validate .prismer/agent.md

# List available capabilities
pisa list-capabilities

# Run the agent
pisa run .prismer/agent.md -i "Calculate 123 * 456 and show the result"
```

---

## ✨ Features

### 🎯 Markdown-Based Agent Definition

Define your entire agent in a single markdown file:

```yaml
---
name: data-processor
loop_type: plan_execute
capabilities:
  - data_loader
  - data_cleaner
  - data_analyzer
---

## Planning Instructions
Break down data processing tasks into logical steps...

## Execution Guidelines
Ensure data quality at each step...
```

### 🔄 Multiple Loop Templates

Choose from battle-tested agent loop patterns:

- **Plan-Execute**: Plan first, then execute tasks sequentially
- **ReAct** *(coming soon)*: Reason and Act in interleaved fashion
- **Custom**: Define your own loop template

### 🛠️ Three Types of Capabilities

1. **Functions**: Simple Python functions with `@function_tool` decorator
2. **MCP Servers**: Connect to Model Context Protocol servers
3. **Subagents**: Delegate to specialized sub-agents via handoff

```python
# Function Tool
@capability(capability_type="function")
@function_tool
def my_function(param: str) -> str:
    return f"Processed: {param}"

# Subagent
@capability(capability_type="agent")
def my_subagent() -> Agent:
    return Agent(
        name="specialist",
        instructions="You are a specialist in..."
    )
```

### 📊 Beautiful CLI Output

Real-time execution visualization powered by [Rich](https://github.com/Textualize/rich):

```
╭─────────────────────────────── 👤 User Query ────────────────────────────────╮
│ Calculate the matrix multiplication of [[1,2],[3,4]] × [[5,6],[7,8]]        │
╰──────────────────────────────────────────────────────────────────────────────╯

╭───────────────────────── 📋 Planning (Iteration 0) ──────────────────────────╮
│ Goal: Matrix multiplication and analysis                                     │
│ Total Tasks: 3                                                               │
╰──────────────────────────────────────────────────────────────────────────────╯

╭───────────────────────── 🔧 Execution (Iteration 1) ─────────────────────────╮
│ Task: task_01                                                                │
│ Capability: matrix_multiply                                                  │
│ Status: ✅                                                                   │
│ Result: [[19, 22], [43, 50]]                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### 🔍 Comprehensive Observability

- **Structured Logging**: Context-aware logs with `structlog`
- **Execution Tracking**: Monitor planning, execution, observation, and reflection phases
- **Debug Mode**: Deep inspection of LLM interactions and tool calls
- **Metrics Collection**: Performance tracking for production deployments

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Quick Start Guide](docs/QUICK_START_v4.md) | Step-by-step tutorial for beginners |
| [Architecture Overview](docs/IMPLEMENTATION_ROADMAP.md) | System design and architecture |
| [Agent Definition Reference](docs/agent_template.md) | Complete agent.md specification |
| [Capability Development](docs/capability_guide.md) | How to create custom capabilities |
| [Loop Templates](docs/loop_templates.md) | Available agent loop patterns |
| [API Reference](docs/api/) | Full API documentation |

---

## 🎨 Examples

### Example 1: Math & Data Processing Agent

A sophisticated agent that performs matrix operations, calculates softmax, and generates structured tables:

```bash
cd example/PISA5
pisa run .prismer/agent.md -i "Calculate [[1,2],[3,4]] × [[5,6],[7,8]], compute softmax, and show results as a table"
```

**Capabilities Used:**
- `matrix_operations` (Function): Matrix math operations
- `compute_softmax` (MCP): Softmax calculations
- `text_to_table` (Subagent): Generate markdown tables

### Example 2: Research Assistant *(coming soon)*

```bash
cd example/research-assistant
pisa run .prismer/agent.md -i "Find recent papers on transformer architectures and summarize key findings"
```

### Example 3: Code Review Agent *(coming soon)*

```bash
cd example/code-reviewer
pisa run .prismer/agent.md --file src/my_code.py
```

---

## 🏗️ Architecture

PISA follows a clean, modular architecture:

```
┌─────────────────────────────────────────────────┐
│            Agent Definition Layer               │
│         (agent.md - Markdown Config)            │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              Loop Templates                     │
│   (Plan-Execute, ReAct, Custom Loops)           │
└─────────┬───────────────────────┬───────────────┘
          │                       │
┌─────────▼─────────┐   ┌────────▼──────────────┐
│  Core Modules     │   │  Capability System    │
│                   │   │                       │
│  - Planning       │   │  - Functions          │
│  - Execution      │   │  - MCP Servers        │
│  - Observation    │   │  - Subagents          │
│  - Reflection     │   │                       │
└─────────┬─────────┘   └────────┬──────────────┘
          │                      │
┌─────────▼──────────────────────▼───────────────┐
│          OpenAI Agent SDK Runtime              │
│   (Messages, Tools, Handoffs, Streaming)       │
└────────────────────────────────────────────────┘
```

### Key Components

- **Definition Layer**: Markdown-based configuration and instructions
- **Loop Templates**: Reusable agent behavior patterns
- **Core Modules**: Pluggable components for agent reasoning
- **Capability System**: Unified interface for tools, MCPs, and subagents
- **OpenAI Agent SDK**: Underlying LLM interaction framework

---

## 🛣️ Roadmap

### Current (v1.0 - Alpha)

- ✅ Core framework with Plan-Execute loop
- ✅ Function, MCP, and Subagent capabilities
- ✅ CLI tools and rich observability
- ✅ Markdown-based agent definition

### Coming Soon (v1.1)

- 🔲 SOTA loop templates
- 🔲 Context compression with LOD (Level of Detail)
- 🔲 Temporal workflow integration for production ready deylopment
- 🔲 Multi-agent collaboration
- 🔲 Streaming response support

### Future (v2.0)

- 🔲 Production level server capability for high I/O and concurrent
- 🔲 Agent marketplace and templates
- 🔲 Auto-optimization with feedback loops
- 🔲 Multi-modal support (images, audio, video)

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and install in development mode
git clone https://github.com/yourusername/pisa.git
cd pisa
uv pip install -e ".[dev]"

# Run tests
uv run pytest tests/ -v

# Run linter
uv run ruff check src/

# Format code
uv run black src/
```

### Areas We Need Help

- 📝 Documentation improvements
- 🐛 Bug reports and fixes
- ✨ New capability implementations
- 🎨 Loop template designs
- 🌍 Internationalization

---

## 📄 License

PISA is released under the [MIT License](LICENSE.txt).

---

## 🙏 Acknowledgments

- Built on top of [OpenAI Agent SDK](https://openai.github.io/openai-agents-python/)
- CLI powered by [Rich](https://github.com/Textualize/rich)
- Async runtime by [Temporal](https://temporal.io/)


---

## 📬 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/pisa/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/pisa/discussions)
- **Email**: support@prismer.ai
- **Twitter**: [@PrismerAI](https://twitter.com/PrismerAI)

---

<div align="center">
  
  **⭐ Star us on GitHub — it motivates us a lot!**
  
  Made with ❤️ by [Prismer AI Lab](https://prismer.ai)
  
</div>
