"""
Loop Templates (v4.0)

提供开箱即用的Loop模板实现。

所有模板基于v4.0架构：
- 继承新的BaseAgentLoop（自动初始化）
- State显式流动，Context隐式共享
- 模块自动初始化和配置
- 简化的run方法，只包含业务编排

可用模板：
- PlanExecuteLoop: Plan-Execute任务规划与执行循环
"""

from pisa.core.loop.templates.plan_execute import PlanExecuteLoop

__all__ = [
    "PlanExecuteLoop",
]
