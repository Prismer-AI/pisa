=========
Changelog
=========

All notable changes to PISA (Planning, Intelligent, Self-Adaptive Agent Framework) will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

Version 0.1.0 (2025-01-24)
==========================

Initial Alpha Release - Core Framework

Added
-----

**Core Framework**

- 🎯 Markdown-based agent definition system (``agent.md`` format)
- 🔄 Plan-Execute loop template
- 🛠️ Modular architecture with pluggable components
- 📊 Capability system supporting three types: Functions, MCP Servers, and Subagents

**Capability System**

- ``@capability`` decorator for easy capability registration
- Built-in capabilities:
  
  - ``matrix_operations`` - Matrix math operations (add, multiply, transpose, etc.)
  - ``compute_softmax`` - Softmax calculations with temperature scaling
  - ``text_to_table`` - Text to structured table conversion
  - ``unified_search`` - Web search integration (Serper, Exa)
  - ``crawl_tool`` - Web crawling with Crawl4AI
  - ``generate_image`` - Image generation with Gemini

- Capability registry with automatic discovery
- Support for local and remote capabilities

**Agent Loop System**

- Planning module with adaptive strategies
- Execution module with tool orchestration
- Observation module for state tracking
- Reflection module for self-improvement
- Validation module with guardrails
- Replanning support for dynamic adaptation

**Context Management**

- Pyramid Context Engineering for efficient context handling
- Context compression with semantic merging
- Context persistence to markdown files
- Memory management with token limits
- Context serialization and deserialization

**CLI Tools**

- ``pisa init`` - Initialize new agent projects
- ``pisa run`` - Execute agents with rich output
- ``pisa validate`` - Validate agent configurations
- ``pisa list-capabilities`` - List available capabilities
- ``pisa debug`` - Debug mode with detailed logging

**Observability**

- Rich console output with beautiful formatting
- Structured logging with ``structlog``
- Real-time execution tracking
- Debug mode for LLM interaction inspection
- Metrics collection framework

**Temporal Integration**

- Workflow definitions for agent execution
- Activity implementations for long-running tasks
- State storage and persistence
- Worker configuration for distributed execution

**Developer Experience**

- Comprehensive documentation structure
- Example agent implementations
- GitHub Actions CI/CD pipeline
- Issue and PR templates
- Contributing guidelines

**Configuration**

- Environment-based configuration with ``.env`` support
- Model configuration (temperature, max_tokens, top_p)
- Planning configuration (max_iterations, strategies)
- Validation rules
- Runtime settings (timeouts, parallel execution)

Changed
-------

- Migrated from legacy agent framework to OpenAI Agent SDK
- Updated dependency management to use ``uv`` for faster installation
- Improved error handling and user feedback

Fixed
-----

- Matrix dimension validation in matrix operations
- Context compression edge cases
- MCP server connection stability
- Agent handoff state management

Security
--------

- Added API key validation
- Implemented secure credential storage
- Added input sanitization for tool calls

Documentation
-------------

- Comprehensive README with quick start guide
- Architecture documentation
- Agent definition reference
- Capability development guide
- Contributing guidelines
- Code of Conduct
- Security policy

Known Issues
------------

- ReAct loop template not yet implemented (planned for v0.2.0)
- ReWOO loop template not yet implemented (planned for v0.2.0)
- Streaming response support incomplete
- Multi-agent collaboration features in development
- Test coverage needs improvement (~40%, target 80%)

Deprecated
----------

- Legacy loop implementation (use new modular loop system)
- Old-style capability registration (use ``@capability`` decorator)

Migration Notes
---------------

This is the first public release. No migration needed.

For detailed upgrade instructions for future versions, see the migration guide in the documentation.


Version 0.0.1 (2024-12-20)
==========================

Internal Development Release

- Initial project scaffolding with PyScaffold
- Basic project structure and dependencies
- Preliminary capability system design
- Early prototypes of planning and execution modules

---

**Note**: This project is under active development. Features and APIs may change between versions.
For the latest updates and roadmap, visit: https://github.com/prismer-ai/pisa
