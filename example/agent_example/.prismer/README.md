# PISA Project

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
