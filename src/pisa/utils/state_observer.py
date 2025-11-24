# Copyright 2025 prismer
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     https://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
State Observer Module

用于监控和记录 Agent Loop 状态变化

功能：
1. State变更追踪
2. 任务状态监控
3. 决策历史记录
4. State健康度检查

使用示例：
```python
from pisa.utils.state_observer import StateObserver

observer = StateObserver(state)

# 自动追踪
observer.snapshot("planning_start")
# ... state变化 ...
observer.snapshot("planning_end")

# 分析
print(observer.get_summary())
print(observer.get_task_stats())
```
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import defaultdict
import copy

from pisa.core.loop.state import LoopState

_logger = logging.getLogger(__name__)


class StateDiff:
    """
    State差异
    
    记录两个State快照之间的差异
    """
    
    def __init__(self, snapshot1: Dict[str, Any], snapshot2: Dict[str, Any]):
        self.snapshot1 = snapshot1
        self.snapshot2 = snapshot2
        self.changes = {}
        self.added = {}
        self.removed = {}
        
        self._calculate_diff()
    
    def _calculate_diff(self):
        """计算两个快照之间的差异"""
        # 简单实现：比较顶级字段
        keys1 = set(self.snapshot1.keys())
        keys2 = set(self.snapshot2.keys())
        
        # 新增的字段
        for key in keys2 - keys1:
            self.added[key] = self.snapshot2[key]
        
        # 删除的字段
        for key in keys1 - keys2:
            self.removed[key] = self.snapshot1[key]
        
        # 变更的字段
        for key in keys1 & keys2:
            if self.snapshot1[key] != self.snapshot2[key]:
                self.changes[key] = {
                    'from': self.snapshot1[key],
                    'to': self.snapshot2[key]
                }
    
    def has_changes(self) -> bool:
        """检查是否有变化"""
        return bool(self.changes or self.added or self.removed)
    
    def summary(self) -> str:
        """生成差异摘要"""
        parts = []
        if self.changes:
            parts.append(f"{len(self.changes)} changed")
        if self.added:
            parts.append(f"{len(self.added)} added")
        if self.removed:
            parts.append(f"{len(self.removed)} removed")
        
        return ", ".join(parts) if parts else "no changes"


class StateSnapshot:
    """
    State快照
    
    记录State在某一时刻的状态
    """
    
    def __init__(
        self,
        state: LoopState,
        label: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.label = label
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}
        
        # 创建State的深度拷贝
        try:
            self.state_data = state.model_dump() if hasattr(state, 'model_dump') else copy.deepcopy(vars(state))
        except Exception as e:
            _logger.warning(f"Failed to snapshot state: {e}")
            self.state_data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'label': self.label,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'state_data': self.state_data
        }


class StateObserver:
    """
    State观察者
    
    追踪LoopState的变化和状态演进
    """
    
    def __init__(self, initial_state: Optional[LoopState] = None):
        self.snapshots: List[StateSnapshot] = []
        self.diffs: List[StateDiff] = []
        
        if initial_state:
            self.snapshot("initial", initial_state)
    
    def snapshot(self, label: str, state: Optional[LoopState] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        创建State快照
        
        Args:
            label: 快照标签
            state: 当前状态（如果为None，使用上次快照的状态）
            metadata: 元数据
        """
        if state is None and self.snapshots:
            # 如果没有提供新状态，使用上次快照的状态
            state_data = self.snapshots[-1].state_data
        elif state:
            try:
                state_data = state.model_dump() if hasattr(state, 'model_dump') else copy.deepcopy(vars(state))
            except Exception as e:
                _logger.warning(f"Failed to snapshot state: {e}")
                state_data = {}
        else:
            state_data = {}
        
        snapshot = StateSnapshot(state, label, metadata=metadata)
        self.snapshots.append(snapshot)
        
        # 计算差异
        if len(self.snapshots) >= 2:
            prev_snapshot = self.snapshots[-2]
            diff = StateDiff(prev_snapshot.state_data, snapshot.state_data)
            self.diffs.append(diff)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取观察摘要"""
        if not self.snapshots:
            return {"error": "No snapshots available"}
        
        summary = {
            "total_snapshots": len(self.snapshots),
            "total_diffs": len(self.diffs),
            "snapshots": [],
            "changes_summary": {}
        }
        
        # 快照信息
        for i, snapshot in enumerate(self.snapshots):
            summary["snapshots"].append({
                "index": i,
                "label": snapshot.label,
                "timestamp": snapshot.timestamp.isoformat(),
                "metadata": snapshot.metadata
            })
        
        # 变化汇总
        changes_summary = defaultdict(int)
        for diff in self.diffs:
            if diff.changes:
                changes_summary["changed"] += len(diff.changes)
            if diff.added:
                changes_summary["added"] += len(diff.added)
            if diff.removed:
                changes_summary["removed"] += len(diff.removed)
        
        summary["changes_summary"] = dict(changes_summary)
        
        return summary
    
    def get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        if not self.snapshots:
            return {"error": "No snapshots available"}
        
        task_stats = {
            "total_snapshots": len(self.snapshots),
            "task_states": defaultdict(int),
            "iteration_progress": [],
            "current_tasks": {}
        }
        
        for snapshot in self.snapshots:
            state_data = snapshot.state_data
            
            # 统计任务状态
            if "plan" in state_data and state_data["plan"]:
                plan = state_data["plan"]
                if "tasks" in plan:
                    for task_id, task in plan["tasks"].items():
                        if isinstance(task, dict) and "status" in task:
                            task_stats["task_states"][task["status"]] += 1
                
                # 记录当前任务
                if "current_task_id" in plan:
                    task_stats["current_tasks"][snapshot.label] = plan["current_task_id"]
            
            # 记录迭代进度
            if "iteration" in state_data:
                task_stats["iteration_progress"].append({
                    "label": snapshot.label,
                    "iteration": state_data["iteration"],
                    "timestamp": snapshot.timestamp.isoformat()
                })
        
        return dict(task_stats)
    
    def compare_snapshots(self, index1: int, index2: int) -> Optional[StateDiff]:
        """比较两个快照"""
        if index1 < 0 or index1 >= len(self.snapshots) or index2 < 0 or index2 >= len(self.snapshots):
            return None
        
        snapshot1 = self.snapshots[index1]
        snapshot2 = self.snapshots[index2]
        
        return StateDiff(snapshot1.state_data, snapshot2.state_data)
    
    def get_recent_changes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取最近的变化"""
        recent_changes = []
        
        for i, diff in enumerate(self.diffs[-limit:]):
            recent_changes.append({
                "diff_index": len(self.diffs) - limit + i,
                "snapshot_from": f"snapshot_{len(self.diffs) - limit + i}",
                "snapshot_to": f"snapshot_{len(self.diffs) - limit + i + 1}",
                "summary": diff.summary(),
                "details": {
                    "changed": list(diff.changes.keys()),
                    "added": list(diff.added.keys()),
                    "removed": list(diff.removed.keys())
                }
            })
        
        return recent_changes


# 全局观察者实例
_global_observer: Optional[StateObserver] = None


def get_global_observer() -> StateObserver:
    """获取全局State观察者"""
    global _global_observer
    if _global_observer is None:
        _global_observer = StateObserver()
    return _global_observer


def reset_global_observer():
    """重置全局观察者"""
    global _global_observer
    _global_observer = None


def track_state_changes(state: LoopState, label: str, metadata: Optional[Dict[str, Any]] = None):
    """
    追踪状态变化的辅助函数
    
    Args:
        state: 当前状态
        label: 标签
        metadata: 元数据
    """
    observer = get_global_observer()
    observer.snapshot(label, state, metadata)
