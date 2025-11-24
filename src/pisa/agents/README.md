
**项目名称：** PISA (Prismer Intelligence Server Agents) **作者：** Manus AI **日期：** 2025年11月18日 **版本：** 1.0

## 1. 概述与设计目标

PISA 框架旨在构建一个**第三代、以 Markdown 为中心、事件驱动、面向生产**的智能体服务框架。它将结合 **Temporal** 的持久化和可靠性 [1]，**OpenAI Agents SDK** 的精简 Agent Loop 抽象 [2]，以及 **Anthropic Skills** 的结构化上下文工程理念 [3]，以解决传统 Agent 框架在动态决策、上下文管理和生产部署中的核心痛点。

核心设计目标包括：

1. **Markdown 中心化定义：** 实现 Agent Loop、配置和指令的完全 Markdown 化定义，提高可读性和可维护性。

1. **生产级持久化：** 基于 Temporal 实现 Agent 状态的持久化、容错和事件驱动的执行，确保任务的可靠完成。

1. **高效上下文管理：** 引入基于 Markdown Heading 层级的细节层级（Level of Detail, LOD）上下文工程，有效对抗上下文膨胀。

1. **模块化与可扩展性：** 抽象 Agent Loop 的核心组件，实现类似 PyTorch `nn.Module` 的模块化组装，降低新 Agent 类型的创建成本。





### 1.1 整体架构图

```text
┌─────────────────────────────────────────────────────────────────┐
│                         PISA Framework                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐         ┌─────────────────┐                │
│  │   agent.md      │         │   context.md    │                │
│  │ (Definition)    │────────▶│  (Runtime)      │                │
│  └─────────────────┘         └─────────────────┘                │
│          │                            │                         │
│          ▼                            ▼                         │
│  ┌──────────────────────────────────────────────────┐           │
│  │         Definition Parser & Validator            │           │
│  └──────────────────────────────────────────────────┘           │
│          │                                                      │
│          ▼                                                      │
│  ┌──────────────────────────────────────────────────┐           │
│  │            Agent Loop Engine                     │           │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │           │
│  │  │Planning  │  │Execution │  │Validation│        │           │
│  │  │  Layer   │─▶│  Layer   │─▶│  Layer   │        │           │
│  │  └──────────┘  └──────────┘  └──────────┘        │           │
│  └──────────────────────────────────────────────────┘           │
│          │                                                      │
│          ▼                                                      │
│  ┌──────────────────────────────────────────────────┐           │
│  │         Tool Execution Layer                     │           │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────┐          │           │
│  │  │Function │  │  MCP    │  │ Subagent │          │           │
│  │  │  Tools  │  │Servers  │  │ Handoff  │          │           │
│  │  └─────────┘  └─────────┘  └──────────┘          │           │
│  └──────────────────────────────────────────────────┘           │
│          │                                                      │
│          ▼                                                      │
│  ┌──────────────────────────────────────────────────┐           │
│  │      Context Management Layer                    │           │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │           │
│  │  │Raw Cache │  │Compress  │  │  Memory  │        │           │
│  │  │          │─▶│  Engine  │─▶│  Store   │        │           │
│  │  └──────────┘  └──────────┘  └──────────┘        │           │
│  └──────────────────────────────────────────────────┘           │
│          │                                                      │
│          ▼                                                      │
│  ┌──────────────────────────────────────────────────┐           │
│  │     Temporal Workflow Orchestration              │           │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │           │
│  │  │Workflow  │  │Activity  │  │  Event   │        │           │
│  │  │ Engine   │─▶│ Workers  │─▶│  Store   │        │           │
│  │  └──────────┘  └──────────┘  └──────────┘        │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 层级职责划分

#### Layer 1: Definition Layer (定义层)
- **agent.md**: Agent 元信息、工具集、规划指令、验证规则
- **context.md**: 运行时完整上下文,保持人类可读性

#### Layer 2: Parser & Loader (解析加载层)
- Markdown 解析器
- YAML Frontmatter 提取
- Schema 验证
- 定义缓存与热加载

#### Layer 3: Agent Loop Engine (核心循环引擎)
- Planning Subsystem: 任务分解与状态追踪
- Execution Subsystem: 工具调用协调
- Validation Subsystem: 输入输出验证

#### Layer 4: Tool Execution Layer (工具执行层)
- 异步并发执行
- 自我纠错机制
- 输入输出防护
- 工具注册与检索

#### Layer 5: Context Management (上下文管理层)
- LOD 上下文压缩
- Heading 层级管理
- 长期记忆存储

#### Layer 6: Persistence & Orchestration (持久化编排层)
- Temporal Workflow 定义
- 事件驱动状态机
- 分布式任务调度


















## 2. 核心概念与数据结构

PISA 框架的核心在于将 Agent 的**静态定义**与**动态上下文**分离，并以结构化的 Markdown 文件作为核心载体。

### 2.1 核心数据结构

| 数据结构 | 描述 | 存储位置 | 关键字段 |
| --- | --- | --- | --- |
| **AgentDefinition** | Agent 的静态配置和指令集。由 `agent.md` 解析而来。 | 内存/缓存 | `meta` (名称, 版本), `planning_instruction`, `tools` (Function, MCP, Subagent), `validation_rules`, `loop_type` |
| **AgentContext** | Agent 的动态运行状态和历史消息。由 `context.md` 解析和更新。 | 内存/Temporal State | `session_id`, `current_round`, `message_history` (原始/压缩), `scratchpad` (思考内容) |
| **ToolRegistry** | 注册的工具集合。用于工具的查找、加载和执行。 | 内存/服务启动时加载 | `tool_name`, `tool_function` (Python Callable), `schema` (OpenAPI/JSON Schema), `execution_mode` (Sync/Async) |
| **AgentState** | Temporal Workflow 的持久化状态。包含 AgentContext 的关键元数据。 | Temporal Server | `session_id`, `current_step`, `status` (Running, Waiting, Completed), `context_ref` (指向 `context.md` 的引用) |



### 2.2 Markdown 文件结构

#### 2.2.1 `agent.md` (Agent 定义文件)

该文件完全定义了 Agent 的行为和能力，是 PISA 框架的**静态配置中心**。

| Heading 层级 | 对应内容 | 作用 |
| --- | --- | --- |
| `# Agent Meta` | Agent 名称、版本、描述、模型配置。 | 框架加载和注册 Agent 的元信息。 |
| `# Planning Instruction` | 引导 Agent 思考和规划的系统指令。 | 核心 Prompt Engineering，指导 Agent 拆解任务。 |
| `# Tools` | 工具定义列表（Function, MCP, Subagent）。 | 定义 Agent 的能力集，包含工具名称、描述和调用规范。 |
| `# Validation Rules` | Agent 输出的校验规则和打分机制。 | 确保输出符合预期，并为自动优化提供量化指标。 |
| `# Background Info` | 长期不变的背景知识或约束条件。 | 提高 Agent 决策的准确性。 |

#### 2.2.2 `context.md` (上下文管理文件)

该文件以人类可读的方式记录了 Agent Loop 的完整历史，是 PISA 框架的**上下文中心**。它采用 LOD 结构来管理上下文的膨胀。

| Heading 层级 | 对应内容 | 作用 |
| --- | --- | --- |
| `# Session: <session_id>` | 整个会话的元信息。 | 标识会话。 |
| `## Round <N>` | 当前轮次的**压缩**消息和关键信息。 | 实际传入 LLM Context 的主要内容，保持精简。 |
| `### Round <N> Raw Content` | 当前轮次的**原始**用户输入、工具输出等。 | 保持原始信息，作为压缩的源头。 |
| `#### Round <N-M> Archive` | 经过多轮压缩后，被降级的历史原始内容。 | 长期存储，用于人类可读的完整追溯。 |
