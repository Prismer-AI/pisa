# PISA Project Structure

## 📁 Repository Layout

\`\`\`
pisa/
├── .github/                      # GitHub configuration
│   ├── ISSUE_TEMPLATE/           # Issue templates
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   ├── workflows/                # CI/CD workflows
│   │   └── ci.yml
│   └── PULL_REQUEST_TEMPLATE.md
│
├── docs/                         # Documentation
│   ├── icon.png                  # Project logo
│   ├── QUICK_START_v4.md         # Quick start guide
│   ├── IMPLEMENTATION_ROADMAP.md # Architecture overview
│   ├── capability_guide.md       # Capability development guide
│   └── api/                      # API reference
│
├── src/pisa/                     # Main source code
│   ├── capability/               # Capability system
│   │   ├── local/                # Built-in capabilities
│   │   │   ├── function/         # Function tools
│   │   │   ├── mcp/              # MCP servers
│   │   │   └── subagent/         # Subagents
│   │   └── registry.py           # Capability registration
│   │
│   ├── core/                     # Core framework
│   │   ├── loop/                 # Agent loop system
│   │   │   ├── templates/        # Loop templates
│   │   │   │   └── plan_execute.py
│   │   │   ├── modules/          # Loop modules
│   │   │   │   ├── planning.py
│   │   │   │   ├── execution.py
│   │   │   │   ├── observe.py
│   │   │   │   └── reflection.py
│   │   │   └── base.py
│   │   │
│   │   ├── planning/             # Planning system
│   │   │   ├── planner.py
│   │   │   └── task_tree.py
│   │   │
│   │   ├── context/              # Context management
│   │   │   ├── manager.py
│   │   │   └── compression.py
│   │   │
│   │   └── definition/           # Agent definition
│   │       ├── parser.py
│   │       ├── models.py
│   │       └── templates/
│   │
│   ├── cli/                      # CLI interface
│   │   ├── commands/             # CLI commands
│   │   │   ├── run.py
│   │   │   ├── validate.py
│   │   │   └── init.py
│   │   ├── ui.py                 # UI components
│   │   ├── observability_display.py
│   │   └── live_display.py
│   │
│   ├── agents/                   # Agent management
│   │   └── manager.py
│   │
│   ├── temporal/                 # Temporal integration
│   │   ├── workflows.py
│   │   └── activities.py
│   │
│   └── utils/                    # Utilities
│       ├── config.py
│       ├── logger.py
│       └── debug.py
│
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── e2e/                      # End-to-end tests
│
├── example/                      # Example projects
│   ├── PISA4/                    # Example 4
│   └── PISA5/                    # Example 5
│       ├── .prismer/
│       │   ├── agent.md
│       │   └── capability/
│       └── run_interactive.py
│
├── README.md                     # Main README
├── CONTRIBUTING.md               # Contribution guidelines
├── LICENSE.txt                   # MIT License
├── pyproject.toml                # Project configuration
├── .env.example                  # Environment template
└── .gitignore
\`\`\`

## 🗂️ Key Directories

### \`src/pisa/core/\`

Contains the core framework components:

- **loop/**: Agent loop system with templates and modules
- **planning/**: Task planning and decomposition
- **context/**: Context management and compression
- **definition/**: Agent definition parsing

### \`src/pisa/capability/\`

Capability system for tools, MCPs, and subagents:

- **local/**: Built-in capabilities
- **registry.py**: Registration and discovery

### \`src/pisa/cli/\`

Command-line interface:

- **commands/**: CLI commands (run, validate, init, etc.)
- **ui.py**: Rich-based UI components
- **observability_display.py**: Execution visualization

### \`example/\`

Example projects demonstrating PISA usage:

- Each example is a complete agent project
- Includes capability definitions and agent.md

## 📄 Key Files

### Configuration Files

- **pyproject.toml**: Python project configuration
- **.env**: Environment variables (not in repo)
- **.env.example**: Environment template

### Documentation

- **README.md**: Project overview and quick start
- **CONTRIBUTING.md**: Contribution guidelines
- **docs/**: Detailed documentation

### Templates

- **src/pisa/core/definition/templates/agent_template.md**: Agent definition template
- **.github/ISSUE_TEMPLATE/**: Issue templates
- **.github/PULL_REQUEST_TEMPLATE.md**: PR template

## 🔧 Development Files

- **tests/**: All test files
- **.github/workflows/ci.yml**: CI/CD pipeline
- **pyproject.toml**: Dependencies and build config

## 🎯 User-Facing Files

When users create an agent project:

\`\`\`
my-agent/
├── .prismer/
│   ├── agent.md              # Agent definition
│   ├── capability/           # Custom capabilities
│   │   ├── function/
│   │   ├── mcp/
│   │   └── subagent/
│   └── context.md            # Context history
├── .env                      # Local configuration
└── run.py                    # Entry point
\`\`\`

---

For more information, see:
- [Quick Start Guide](../docs/QUICK_START_v4.md)
- [Architecture Overview](../docs/IMPLEMENTATION_ROADMAP.md)
- [Contributing Guide](../CONTRIBUTING.md)
