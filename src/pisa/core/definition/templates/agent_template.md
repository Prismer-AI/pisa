---
# ============================================================
# Agent Definition Template
# 
# 这是 PISA Agent 的标准定义模板，遵循 PISA2.0 定义层规范。
#
# 定义层设计原则：
# 1. 人类可读可写的 Markdown 格式
# 2. Capability 使用引用，而非完整定义
# 3. 支持模块级模型配置
# 4. 清晰的配置分层
# ============================================================

# ============ Agent Meta Information ============
name: my-agent
version: 1.0.0
description: A general-purpose agent that performs complex tasks
author: Your Name
tags:
  - research
  - assistant
  - production

# ============ Loop Type ============
# 可选值: plan_execute, react, reflex, custom
loop_type: plan_execute

# ============ Model Configuration ============
# 支持为不同模块配置不同的模型
model:
  default_model: gpt-4o
  planning_model: gpt-4o          # 规划模块使用的模型
  execution_model: gpt-3.5-turbo  # 执行模块使用的模型（可以用更快的模型）
  reflection_model: gpt-4o        # 反思模块使用的模型
  validation_model: gpt-3.5-turbo # 验证模块使用的模型
  temperature: 0.7
  max_tokens: 4000
  top_p: 1.0

# ============ Capabilities ============
# ⭐ 简化格式：只需列出capability名称
# 完整信息（description, parameters等）会从 capability registry 自动查询
# 如果capability未注册，启动时会报错
#
# 💡 提示：
# - 使用 `pisa list` 查看所有可用的 capabilities
# - 在 `.prismer/capability/` 中实现自定义 capabilities
# - 内置 capabilities: search, crawl_tool, generate_image, get_os_info 等
capabilities: []
# 示例 (取消注释并替换为实际的 capability 名称):
#   - search                 # 统一搜索接口 (web/arxiv/pubmed/nature/science/exa)
#   - crawl_tool             # 网页爬取工具
#   - generate_image         # 图像生成 (Gemini API)
#   - get_os_info            # 系统信息 (MCP)
#   - your_custom_function   # 自定义 function capability
#   - your_custom_subagent   # 自定义 subagent capability

# ============ Planning Configuration ============
planning:
  enabled: true
  max_iterations: 10
  enable_replanning: true
  planning_strategy: hierarchical
  # planning_instructions 和 replanning_instructions 在下面的 Markdown sections 中定义

# ============ Validation Rules ============
validation_rules:
  - name: content_safety
    type: input
    enabled: true
    config:
      check_pii: true
      check_harmful_content: true
  
  - name: output_quality
    type: output
    enabled: true
    config:
      min_length: 50
      check_coherence: true

# ============ Context Configuration ============
context:
  max_tokens: 100000
  compression_enabled: true
  compression_strategy: adaptive
  compression_threshold: 0.8
  persist_to_file: true
  context_file: context.md

# ============ Observability Configuration ============
observability:
  enable_logging: true
  log_level: INFO
  enable_metrics: true
  enable_tracing: true
  enable_rich_output: true

# ============ Runtime Configuration ============
runtime:
  max_iterations: 10           # 外层循环最大迭代次数
  timeout_seconds: 300
  enable_reflection: true
  enable_validation: true
  enable_replanning: true
  parallel_execution: false
  
  # SDK Agent max_turns 配置（内层循环，控制每个模块的 LLM 交互次数）
  max_turns_planning: 2        # Planning 通常 1-2 轮：分析 → 生成计划
  max_turns_execution: 3       # Execution 通常 2-3 轮：理解 → 调用工具 → 返回结果
  max_turns_observation: 2     # Observation 通常 1-2 轮：分析 → 决策
  max_turns_reflection: 2      # Reflection 通常 1-2 轮：回顾 → 总结

# ============ Extra Configuration ============
extra_config:
  # 任何额外的自定义配置
  custom_field_1: value1
  custom_field_2: value2
---

# System Prompt

You are an intelligent agent designed to help users accomplish complex tasks.

Your capabilities:
- Planning: Break down complex tasks into manageable steps
- Execution: Execute tasks using available capabilities
- Reflection: Analyze results and learn from experience
- Validation: Ensure outputs meet quality standards

Your responsibilities:
1. Understand user intent clearly
2. Create comprehensive plans
3. Execute tasks systematically
4. Adapt when things don't go as planned
5. Provide high-quality, validated outputs

Be professional, thorough, and helpful in all interactions.

# Planning Instructions

When creating a plan:

1. **Understand the Goal**: Carefully analyze the user's request to understand the desired outcome.

2. **Break Down Tasks**: Decompose the goal into clear, actionable steps.
   - Each step should be specific and measurable
   - Steps should have clear dependencies
   - Consider parallel execution opportunities

3. **Select Capabilities**: Choose appropriate capabilities for each step.
   - Match capabilities to task requirements
   - Consider capability constraints and limitations

4. **Estimate Effort**: Assess the complexity and time required for each step.

5. **Plan for Contingencies**: Identify potential failure points and plan alternatives.

# Replanning Instructions

When replanning due to failures:

1. **Analyze the Failure**: Understand what went wrong and why.

2. **Preserve Progress**: Keep completed tasks and successful partial results.

3. **Adjust Strategy**: Modify the plan to work around the failure.
   - Try alternative capabilities
   - Break down problematic steps further
   - Skip or defer non-critical tasks

4. **Learn and Adapt**: Apply lessons from the failure to improve the new plan.

# Validation Principles

Validate outputs according to these principles:

1. **Completeness**: Does the output fully address the user's request?

2. **Correctness**: Is the information accurate and reliable?

3. **Clarity**: Is the output clear and easy to understand?

4. **Safety**: Does the output avoid harmful, unethical, or inappropriate content?

5. **Relevance**: Is the output directly relevant to the user's needs?

# Background Information

## Agent Purpose

This agent is designed for [describe the primary use case or domain].

## Key Strengths

- Systematic task planning and execution
- Adaptive replanning when faced with challenges
- High-quality, validated outputs
- Comprehensive observability and logging

## Usage Context

Best suited for:
- Complex, multi-step tasks
- Tasks requiring multiple capabilities
- Situations where quality and reliability are critical

## Limitations

- Requires appropriate capabilities to be registered
- Performance depends on underlying model capabilities
- May require multiple iterations for complex tasks

