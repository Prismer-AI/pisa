# Contributing to PISA

Thank you for your interest in contributing to PISA! We welcome contributions from the community and are excited to work with you.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

This project follows a standard Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to support@prismer.ai.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Development Setup

1. **Fork and Clone**

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/pisa.git
cd pisa

# Add upstream remote
git remote add upstream https://github.com/prismer/pisa.git
```

2. **Create a Virtual Environment**

```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Or using venv
python -m venv .venv
source .venv/bin/activate
```

3. **Install Dependencies**

```bash
# Install in development mode with dev dependencies
uv pip install -e ".[dev]"

# Or using pip
pip install -e ".[dev]"
```

4. **Set Up Pre-commit Hooks**

```bash
pre-commit install
```

5. **Verify Installation**

```bash
# Run tests
uv run pytest tests/ -v

# Check code quality
uv run ruff check src/
```

---

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

#### 🐛 Bug Reports

- Use the GitHub issue tracker
- Include a clear description, reproduction steps, and expected behavior
- Add logs, screenshots, or error messages if applicable

#### ✨ Feature Requests

- Open an issue with the "enhancement" label
- Describe the problem you're trying to solve
- Explain your proposed solution
- Consider backward compatibility

#### 📝 Documentation

- Fix typos, clarify explanations, or add examples
- Update outdated documentation
- Write tutorials or guides

#### 🔧 Code Contributions

- Bug fixes
- New features
- Performance improvements
- New capabilities or loop templates

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- Line length: 100 characters (not 79)
- Use type hints for all function signatures
- Use docstrings (Google style) for all public APIs

### Code Formatting

We use the following tools:

```bash
# Format code
uv run black src/ tests/

# Sort imports
uv run isort src/ tests/

# Lint
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `PlanningModule`, `AgentLoop`)
- **Functions/Methods**: `snake_case` (e.g., `create_agent`, `execute_task`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_MODEL`)
- **Private members**: prefix with `_` (e.g., `_internal_method`)

### Project Structure

```
src/pisa/
├── capability/         # Capability system
│   ├── local/         # Built-in capabilities
│   └── registry.py    # Capability registration
├── core/              # Core framework
│   ├── loop/          # Agent loop implementations
│   ├── planning/      # Planning system
│   ├── context/       # Context management
│   └── definition/    # Agent definition parsing
├── cli/               # CLI commands
└── utils/             # Utilities
```

---

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_planning.py -v

# Run with coverage
uv run pytest tests/ --cov=src/pisa --cov-report=html

# Run only unit tests
uv run pytest tests/unit/ -v

# Run only integration tests
uv run pytest tests/integration/ -v
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use pytest fixtures for common setup
- Aim for >80% code coverage
- Test both success and failure cases

Example test:

```python
import pytest
from pisa.core.planning import Planner

@pytest.fixture
def planner():
    return Planner(model="gpt-4o-mini")

def test_planner_creates_valid_plan(planner):
    """Test that planner creates a valid task plan."""
    goal = "Calculate 2 + 2"
    plan = await planner.create_plan(goal)
    
    assert plan is not None
    assert len(plan.tasks) > 0
    assert plan.root_goal == goal
```

---

## Documentation

### Docstring Format

We use Google-style docstrings:

```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description of the function.
    
    Longer description if needed, explaining what the function does
    and any important details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param2 is negative
        
    Example:
        >>> my_function("test", 42)
        True
    """
    pass
```

### Documentation Updates

When adding new features:

1. Update relevant markdown docs in `docs/`
2. Add docstrings to all public APIs
3. Include usage examples
4. Update the README if needed

---

## Pull Request Process

### Before Submitting

1. **Create a Branch**

```bash
git checkout -b feature/my-new-feature
# or
git checkout -b fix/bug-description
```

2. **Make Your Changes**

- Write clean, readable code
- Follow the coding standards
- Add tests for new functionality
- Update documentation

3. **Test Locally**

```bash
# Run tests
uv run pytest tests/ -v

# Check code quality
uv run ruff check src/
uv run black --check src/
uv run mypy src/
```

4. **Commit Your Changes**

```bash
# Use conventional commit messages
git commit -m "feat: add new planning strategy"
git commit -m "fix: resolve context compression bug"
git commit -m "docs: update capability guide"
```

Commit message types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

### Submitting

1. **Push to Your Fork**

```bash
git push origin feature/my-new-feature
```

2. **Create Pull Request**

- Go to the [PISA repository](https://github.com/prismer/pisa)
- Click "New Pull Request"
- Select your branch
- Fill out the PR template

### PR Template

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Updated existing tests

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

### Review Process

1. Maintainers will review your PR
2. Address any feedback or requested changes
3. Once approved, a maintainer will merge your PR

---

## Development Tips

### Debugging

```bash
# Enable debug mode
export PISA_DEBUG=true

# Run with verbose logging
pisa run .prismer/agent.md -i "test" --verbose

# Use IPython for interactive debugging
ipdb.set_trace()  # Add to your code
```

### Common Tasks

```bash
# Add a new capability
pisa init my-agent
cd my-agent/.prismer/capability/function
# Create your capability file

# Test a capability
cd example/PISA5
pisa list-capabilities
pisa run .prismer/agent.md -i "test capability"

# Create a new loop template
# Edit src/pisa/core/loop/templates/my_loop.py
# Register with @agent decorator
```

---

## Getting Help

- **Discord**: Join our [Discord server](https://discord.gg/pisa)
- **GitHub Discussions**: Ask questions in [Discussions](https://github.com/prismer/pisa/discussions)
- **Email**: Contact maintainers at dev@prismer.ai

---

## Recognition

Contributors will be:
- Listed in the README
- Credited in release notes
- Added to our [Contributors page](https://pisa.prismer.ai/contributors)

---

Thank you for contributing to PISA! 🎉


