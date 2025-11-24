"""
Loop State

Agent Loop 的业务执行状态

特点：
- 纯 Pydantic（可序列化到 Temporal）
- 结构化数据（不是 Messages）
- 不可变更新（每次返回新State）
- 不包含：Agent实例、函数、模块

与 ContextState 的区别：
- LoopState: 业务状态（任务、决策、结果）
- ContextState: LLM历史（Messages、Tool calls）
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List
from datetime import datetime
import json


class LoopState(BaseModel):
    """
    Agent Loop 的业务执行状态
    
    这是业务逻辑层的核心状态对象，维护：
    - 任务和规划信息
    - 观察和决策结果
    - 执行结果和控制信号
    
    设计原则：
    1. 纯 Pydantic 模型（可序列化）
    2. 不可变（每次更新返回新State）
    3. 类型安全（所有字段有明确类型）
    4. Temporal 兼容（可序列化为 JSON）
    
    使用示例：
    ```python
    # 创建初始State
    state = LoopState(input="分析这个文件", task=Task(...))
    
    # 不可变更新
    state = state.with_update(observation=Observation(...))
    state = state.with_update(decision=Decision(...))
    
    # 控制信号
    state = state.with_update(should_stop=True)
    
    # 序列化
    data = state.to_dict()
    state2 = LoopState.from_dict(data)
    ```
    """
    
    # ==================== 核心业务数据 ====================
    
    input: Any = Field(
        default=None,
        description="原始输入数据"
    )
    
    task: Optional[Any] = Field(
        default=None,
        description="当前执行的任务"
    )
    
    plan: Optional[Any] = Field(
        default=None,
        description="规划结果（如TaskTree）"
    )
    
    observation: Optional[Any] = Field(
        default=None,
        description="观察结果（结构化）"
    )
    
    orientation: Optional[Any] = Field(
        default=None,
        description="定位分析结果（OODA循环）"
    )
    
    decision: Optional[Any] = Field(
        default=None,
        description="决策结果"
    )
    
    result: Optional[Any] = Field(
        default=None,
        description="执行结果"
    )
    
    multimodal_data: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="多模态数据存储（图像、音频、视频等非文本数据）"
    )
    
    # ==================== 控制信号 ====================
    
    iteration: int = Field(
        default=0,
        description="当前迭代次数"
    )
    
    should_stop: bool = Field(
        default=False,
        description="是否应该停止循环"
    )
    
    should_replan: bool = Field(
        default=False,
        description="是否应该重新规划"
    )
    
    should_retry: bool = Field(
        default=False,
        description="是否应该重试"
    )
    
    retry_count: int = Field(
        default=0,
        description="重试次数"
    )
    
    # ==================== 元数据 ====================
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="State创建时间"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="额外的元数据"
    )
    
    # ==================== 历史记录 ====================
    
    history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="State变化历史"
    )
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    # ==================== 不可变更新 ====================
    
    def with_update(self, **kwargs) -> 'LoopState':
        """
        不可变更新：返回新State
        
        类似PyTorch的tensor操作，每次返回新对象
        
        Args:
            **kwargs: 要更新的字段
        
        Returns:
            新的LoopState对象
        
        Example:
            ```python
            state = LoopState(input="test")
            new_state = state.with_update(iteration=1, task=Task(...))
            # state 不变，new_state 是新对象
            ```
        """
        # 获取当前所有数据
        data = self.model_dump()
        
        # 更新指定字段
        data.update(kwargs)
        
        # 自动记录历史（除非显式传入history）
        if 'history' not in kwargs and kwargs:
            # 记录本次更新
            history_entry = {
                'iteration': self.iteration,
                'timestamp': datetime.now().isoformat(),
                'updates': {k: str(v)[:100] for k, v in kwargs.items()}  # 截断长字符串
            }
            data['history'] = self.history + [history_entry]
        
        # 更新timestamp
        if 'timestamp' not in kwargs:
            data['timestamp'] = datetime.now()
        
        # 返回新State
        return LoopState(**data)
    
    # ==================== 便捷方法 ====================
    
    def get(self, key: str, default=None):
        """
        便捷访问字段
        
        Args:
            key: 字段名
            default: 默认值
        
        Returns:
            字段值或默认值
        """
        return getattr(self, key, default)
    
    def set(self, **kwargs) -> 'LoopState':
        """
        便捷设置（返回新State）
        
        Args:
            **kwargs: 要设置的字段
        
        Returns:
            新的LoopState对象
        """
        return self.with_update(**kwargs)
    
    def increment_iteration(self) -> 'LoopState':
        """
        增加迭代次数
        
        Returns:
            新的LoopState对象
        """
        return self.with_update(iteration=self.iteration + 1)
    
    def increment_retry(self) -> 'LoopState':
        """
        增加重试次数
        
        Returns:
            新的LoopState对象
        """
        return self.with_update(
            retry_count=self.retry_count + 1,
            should_retry=False  # 重置重试信号
        )
    
    def reset_control_signals(self) -> 'LoopState':
        """
        重置所有控制信号
        
        Returns:
            新的LoopState对象
        """
        return self.with_update(
            should_stop=False,
            should_replan=False,
            should_retry=False
        )
    
    # ==================== 序列化 ====================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（Temporal序列化）
        
        Returns:
            字典表示
        """
        return self.model_dump()
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """
        转换为JSON字符串
        
        Args:
            indent: 缩进（None表示紧凑格式）
        
        Returns:
            JSON字符串
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoopState':
        """
        从字典恢复（Temporal反序列化）
        
        Args:
            data: 字典数据
        
        Returns:
            LoopState对象
        """
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'LoopState':
        """
        从JSON字符串恢复
        
        Args:
            json_str: JSON字符串
        
        Returns:
            LoopState对象
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    # ==================== 状态检查 ====================
    
    def is_complete(self) -> bool:
        """
        检查是否完成
        
        Returns:
            True如果应该停止或有结果
        """
        return self.should_stop or self.result is not None
    
    def needs_action(self) -> bool:
        """
        检查是否需要采取行动
        
        Returns:
            True如果有控制信号
        """
        return self.should_replan or self.should_retry
    
    # ==================== 多模态数据操作 ====================
    
    def add_multimodal_data(
        self,
        data_type: str,
        data: str,
        mime_type: str = None,
        metadata: Dict[str, Any] = None
    ) -> 'LoopState':
        """
        添加多模态数据
        
        Args:
            data_type: 数据类型 (image, audio, video, etc.)
            data: Base64编码的数据
            mime_type: MIME类型 (e.g., "image/png", "audio/mp3")
            metadata: 额外的元数据
        
        Returns:
            新的LoopState对象
        
        Example:
            ```python
            state = state.add_multimodal_data(
                data_type="image",
                data="iVBORw0KGgoAAAANS...",
                mime_type="image/png",
                metadata={"prompt": "A sunset", "size": "2K"}
            )
            ```
        """
        new_multimodal_data = self.multimodal_data.copy()
        
        if data_type not in new_multimodal_data:
            new_multimodal_data[data_type] = []
        
        entry = {
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        if mime_type:
            entry["mime_type"] = mime_type
        
        if metadata:
            entry["metadata"] = metadata
        
        new_multimodal_data[data_type].append(entry)
        
        return self.with_update(multimodal_data=new_multimodal_data)
    
    def get_multimodal_data(
        self,
        data_type: str,
        index: int = -1
    ) -> Optional[Dict[str, Any]]:
        """
        获取多模态数据
        
        Args:
            data_type: 数据类型 (image, audio, video, etc.)
            index: 数据索引（默认-1获取最新的）
        
        Returns:
            数据项或None
        
        Example:
            ```python
            image = state.get_multimodal_data("image", index=-1)
            if image:
                print(f"MIME: {image['mime_type']}")
                print(f"Data length: {len(image['data'])}")
            ```
        """
        if data_type not in self.multimodal_data:
            return None
        
        data_list = self.multimodal_data[data_type]
        if not data_list:
            return None
        
        try:
            return data_list[index]
        except IndexError:
            return None
    
    def list_multimodal_types(self) -> List[str]:
        """
        列出所有多模态数据类型
        
        Returns:
            数据类型列表
        """
        return list(self.multimodal_data.keys())
    
    def count_multimodal_data(self, data_type: str = None) -> int:
        """
        统计多模态数据数量
        
        Args:
            data_type: 数据类型（None表示统计全部）
        
        Returns:
            数据项数量
        """
        if data_type is None:
            return sum(len(items) for items in self.multimodal_data.values())
        
        return len(self.multimodal_data.get(data_type, []))
    
    def has_error(self) -> bool:
        """
        检查是否有错误
        
        Returns:
            True如果结果表示错误
        """
        if self.result is None:
            return False
        
        # 检查result是否有error或success字段
        if isinstance(self.result, dict):
            return not self.result.get('success', True)
        
        # 检查result对象是否有success属性
        if hasattr(self.result, 'success'):
            return not self.result.success
        
        return False
    
    # ==================== 调试 ====================
    
    def summary(self) -> Dict[str, Any]:
        """
        获取State摘要（用于调试和日志）
        
        Returns:
            摘要信息
        """
        return {
            'iteration': self.iteration,
            'has_task': self.task is not None,
            'has_plan': self.plan is not None,
            'has_observation': self.observation is not None,
            'has_decision': self.decision is not None,
            'has_result': self.result is not None,
            'should_stop': self.should_stop,
            'should_replan': self.should_replan,
            'should_retry': self.should_retry,
            'retry_count': self.retry_count,
            'timestamp': self.timestamp.isoformat(),
            'history_length': len(self.history),
            'multimodal_types': self.list_multimodal_types(),
            'multimodal_count': self.count_multimodal_data()
        }
    
    def __repr__(self) -> str:
        """字符串表示（调试用）"""
        return f"LoopState(iteration={self.iteration}, complete={self.is_complete()})"
    
    def __str__(self) -> str:
        """用户友好的字符串表示"""
        summary = self.summary()
        return (
            f"LoopState(iter={summary['iteration']}, "
            f"task={summary['has_task']}, "
            f"result={summary['has_result']}, "
            f"stop={summary['should_stop']})"
        )

