"""
Task Tree

任务树数据结构，用于表示任务的层级关系和执行依赖。

改进：
- 区分 task_description（目标描述）和 task_detail_info（任务细节）
- 结构化存储 agent 输出
- 支持任务依赖和状态管理
"""

from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"  # 等待执行
    READY = "ready"  # 就绪（依赖已满足）
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    BLOCKED = "blocked"  # 被阻塞
    CANCELLED = "cancelled"  # 已取消


class TaskNode(BaseModel):
    """
    任务节点
    
    改进：
    - task_description: 任务目标描述（简短，面向目标）
    - task_detail_info: 任务细节信息（详细，包含执行信息）
    - agent_output: 结构化存储 agent 输出
    """
    task_id: str = Field(description="任务唯一标识")
    
    # 任务信息分离
    task_description: str = Field(description="任务目标描述（What）")
    task_detail_info: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="任务细节信息（How），包括执行步骤、参数、上下文等"
    )
    
    # 任务状态
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    
    # 任务关系
    parent_id: Optional[str] = Field(default=None, description="父任务ID")
    children_ids: List[str] = Field(default_factory=list, description="子任务ID列表")
    dependencies: List[str] = Field(default_factory=list, description="依赖的任务ID列表")
    
    # 执行信息
    assigned_capability: Optional[str] = Field(default=None, description="分配的 capability 名称")
    
    # Agent 输出（结构化存储）
    agent_output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Agent 的结构化输出，包括思考过程、决策依据等"
    )
    
    # 执行结果
    result: Optional[Any] = Field(default=None, description="执行结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外的元数据")
    
    def is_ready(self, completed_tasks: set) -> bool:
        """
        判断任务是否就绪（所有依赖已完成）
        
        Args:
            completed_tasks: 已完成的任务ID集合
            
        Returns:
            是否就绪
        """
        if self.status != TaskStatus.PENDING:
            return False
        
        # 检查所有依赖是否已完成
        return all(dep_id in completed_tasks for dep_id in self.dependencies)
    
    def mark_running(self) -> None:
        """标记任务为运行中"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        self.updated_at = datetime.now()
    
    def mark_completed(self, result: Any = None, agent_output: Optional[Dict] = None) -> None:
        """
        标记任务为已完成
        
        Args:
            result: 执行结果
            agent_output: Agent 的结构化输出
        """
        self.status = TaskStatus.COMPLETED
        self.result = result
        if agent_output:
            self.agent_output = agent_output
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
    
    def mark_failed(self, error: str) -> None:
        """标记任务为失败"""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_child(self, child_id: str) -> None:
        """添加子任务"""
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)
            self.updated_at = datetime.now()
    
    def add_dependency(self, dep_id: str) -> None:
        """添加依赖"""
        if dep_id not in self.dependencies:
            self.dependencies.append(dep_id)
            self.updated_at = datetime.now()


class TaskTree(BaseModel):
    """
    任务树
    
    管理任务的层级结构和执行依赖
    """
    root_goal: str = Field(description="根目标描述")
    plan_version: int = Field(default=1, description="计划版本号")
    
    # 任务存储
    tasks: Dict[str, TaskNode] = Field(default_factory=dict, description="任务字典 {task_id: TaskNode}")
    root_task_id: Optional[str] = Field(default=None, description="根任务ID")
    
    # 执行顺序
    execution_order: List[str] = Field(default_factory=list, description="推荐的执行顺序")
    current_task_id: Optional[str] = None
    
    # 规划信息（Agent 输出）
    planning_output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="规划阶段的 Agent 结构化输出"
    )
    
    # 重新规划历史
    replanning_history: List[Dict] = Field(default_factory=list)
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def add_task(self, task: TaskNode) -> None:
        """添加任务到树中"""
        self.tasks[task.task_id] = task
        self.updated_at = datetime.now()
        
        # 如果是第一个任务，设为根任务
        if self.root_task_id is None:
            self.root_task_id = task.task_id
    
    def get_task(self, task_id: str) -> Optional[TaskNode]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_ready_tasks(self) -> List[TaskNode]:
        """
        获取所有就绪的任务（依赖已满足且状态为 PENDING）
        
        Returns:
            就绪的任务列表
        """
        completed = {
            tid for tid, task in self.tasks.items()
            if task.status == TaskStatus.COMPLETED
        }
        
        ready_tasks = []
        for task in self.tasks.values():
            if task.is_ready(completed):
                ready_tasks.append(task)
        
        return ready_tasks
    
    def mark_failed(self, task_id: str, error: str) -> None:
        """标记任务为失败"""
        if task_id in self.tasks:
            self.tasks[task_id].mark_failed(error)
            self.updated_at = datetime.now()
    
    def get_next_task(self) -> Optional[TaskNode]:
        """
        获取下一个要执行的任务
        
        Returns:
            下一个任务，如果没有则返回 None
        """
        ready_tasks = self.get_ready_tasks()
        
        if not ready_tasks:
            return None
        
        # 优先按照 execution_order
        for task_id in self.execution_order:
            task = self.get_task(task_id)
            if task and task in ready_tasks:
                return task
        
        # 如果 execution_order 中没有，返回第一个就绪任务
        return ready_tasks[0] if ready_tasks else None
    
    def get_children(self, task_id: str) -> List[TaskNode]:
        """获取任务的所有子任务"""
        task = self.get_task(task_id)
        if not task:
            return []
        
        return [
            self.tasks[child_id]
            for child_id in task.children_ids
            if child_id in self.tasks
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取任务树统计信息
        
        Returns:
            统计信息字典
        """
        status_counts = {}
        for task in self.tasks.values():
            status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1
        
        return {
            "total_tasks": len(self.tasks),
            "status_counts": status_counts,
            "root_goal": self.root_goal,
            "plan_version": self.plan_version,
            "current_task": self.current_task_id,
            "ready_tasks_count": len(self.get_ready_tasks()),
        }
    
    def is_completed(self) -> bool:
        """判断所有任务是否已完成"""
        if not self.tasks:
            return False
        
        return all(
            task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
            for task in self.tasks.values()
        )
    
    def has_failed_tasks(self) -> bool:
        """判断是否有失败的任务"""
        return any(task.status == TaskStatus.FAILED for task in self.tasks.values())
    
    def get_execution_order(self) -> List[TaskNode]:
        """
        获取任务执行顺序
        
        使用拓扑排序
        
        Returns:
            任务执行顺序
            
        TODO: 实现拓扑排序
        """
        raise NotImplementedError("待实现")
    
    def visualize(self) -> str:
        """
        可视化任务树
        
        Returns:
            任务树的文本表示
            
        TODO: 实现可视化逻辑
        """
        raise NotImplementedError("待实现")

