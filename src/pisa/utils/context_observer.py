"""
Context Observer

追踪和可视化LoopContext的变化，监控LLM交互历史。

功能：
1. Message统计（数量、类型、token数）
2. Context压缩监控
3. Tool调用追踪
4. Context健康度检查

使用示例：
```python
from pisa.utils.context_observer import ContextObserver

observer = ContextObserver(context)

# 自动追踪
observer.snapshot("planning_start")
# ... context变化 ...
observer.snapshot("planning_end")

# 分析
print(observer.get_summary())
print(observer.get_message_stats())
```
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import defaultdict
import json

from pisa.core.loop.context import LoopContext

_logger = logging.getLogger(__name__)


class ContextSnapshot:
    """
    Context快照
    
    记录Context在某一时刻的状态
    """
    
    def __init__(
        self,
        context: LoopContext,
        label: str,
        timestamp: Optional[datetime] = None
    ):
        """
        初始化快照
        
        Args:
            context: LoopContext实例
            label: 快照标签
            timestamp: 时间戳
        """
        self.label = label
        self.timestamp = timestamp or datetime.now()
        
        # 提取统计信息
        self.message_count = len(context.get_active_messages())
        self.round_count = len(context.manager.state.rounds)
        self.compression_count = context.manager.compression_count
        
        # 分析消息类型
        self.message_stats = self._compute_message_stats(context)
    
    def _compute_message_stats(self, context: LoopContext) -> Dict[str, Any]:
        """
        计算消息统计
        
        Args:
            context: LoopContext实例
            
        Returns:
            统计字典
        """
        messages = context.get_active_messages()
        
        stats = {
            "total": len(messages),
            "by_role": defaultdict(int),
            "tool_calls": 0,
            "tool_results": 0,
        }
        
        for msg in messages:
            role = msg.get("role", "unknown")
            stats["by_role"][role] += 1
            
            # 统计tool相关消息
            if "tool_calls" in msg:
                stats["tool_calls"] += len(msg.get("tool_calls", []))
            
            if role == "tool":
                stats["tool_results"] += 1
        
        stats["by_role"] = dict(stats["by_role"])
        
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "label": self.label,
            "timestamp": self.timestamp.isoformat(),
            "message_count": self.message_count,
            "round_count": self.round_count,
            "compression_count": self.compression_count,
            "message_stats": self.message_stats,
        }


class ContextDiff:
    """
    Context差异
    
    对比两个ContextSnapshot的变化
    """
    
    def __init__(self, snapshot_from: ContextSnapshot, snapshot_to: ContextSnapshot):
        """
        初始化差异
        
        Args:
            snapshot_from: 起始快照
            snapshot_to: 结束快照
        """
        self.snapshot_from = snapshot_from
        self.snapshot_to = snapshot_to
        
        # 计算差异
        self.message_delta = snapshot_to.message_count - snapshot_from.message_count
        self.round_delta = snapshot_to.round_count - snapshot_from.round_count
        self.compression_delta = snapshot_to.compression_count - snapshot_from.compression_count
        
        # 时间差
        self.time_delta = (snapshot_to.timestamp - snapshot_from.timestamp).total_seconds()
    
    def has_changes(self) -> bool:
        """是否有变化"""
        return (
            self.message_delta != 0
            or self.round_delta != 0
            or self.compression_delta != 0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "from": self.snapshot_from.label,
            "to": self.snapshot_to.label,
            "time_delta_seconds": self.time_delta,
            "changes": {
                "messages": {
                    "from": self.snapshot_from.message_count,
                    "to": self.snapshot_to.message_count,
                    "delta": self.message_delta,
                },
                "rounds": {
                    "from": self.snapshot_from.round_count,
                    "to": self.snapshot_to.round_count,
                    "delta": self.round_delta,
                },
                "compressions": {
                    "from": self.snapshot_from.compression_count,
                    "to": self.snapshot_to.compression_count,
                    "delta": self.compression_delta,
                },
            },
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        if not self.has_changes():
            return f"No changes ({self.snapshot_from.label} → {self.snapshot_to.label})"
        
        changes = []
        if self.message_delta != 0:
            changes.append(f"messages: {self.message_delta:+d}")
        if self.round_delta != 0:
            changes.append(f"rounds: {self.round_delta:+d}")
        if self.compression_delta != 0:
            changes.append(f"compressions: {self.compression_delta:+d}")
        
        return f"{self.snapshot_from.label} → {self.snapshot_to.label}: {', '.join(changes)}"


class ContextObserver:
    """
    Context观察器
    
    监控LoopContext的变化和健康状态
    """
    
    def __init__(
        self,
        context: LoopContext,
        max_snapshots: int = 50
    ):
        """
        初始化
        
        Args:
            context: 要监控的LoopContext
            max_snapshots: 最大快照数
        """
        self.context = context
        self.max_snapshots = max_snapshots
        
        # 快照历史: {label: snapshot}
        self.snapshots: Dict[str, ContextSnapshot] = {}
        
        # 快照序列
        self.snapshot_sequence: List[str] = []
        
        # 统计信息
        self.stats = defaultdict(int)
        
        _logger.debug(f"ContextObserver initialized: max_snapshots={max_snapshots}")
    
    def snapshot(self, label: str) -> ContextSnapshot:
        """
        创建Context快照
        
        Args:
            label: 快照标签
            
        Returns:
            ContextSnapshot实例
        """
        snapshot = ContextSnapshot(self.context, label)
        
        # 记录快照
        self.snapshots[label] = snapshot
        self.snapshot_sequence.append(label)
        
        # 限制快照数量
        if len(self.snapshot_sequence) > self.max_snapshots:
            oldest_label = self.snapshot_sequence.pop(0)
            if oldest_label in self.snapshots:
                del self.snapshots[oldest_label]
        
        # 更新统计
        self.stats["total_snapshots"] += 1
        
        _logger.debug(
            f"Snapshot created: {label} "
            f"(messages={snapshot.message_count}, rounds={snapshot.round_count})"
        )
        
        return snapshot
    
    def get_snapshot(self, label: str) -> Optional[ContextSnapshot]:
        """
        获取快照
        
        Args:
            label: 快照标签
            
        Returns:
            ContextSnapshot实例或None
        """
        return self.snapshots.get(label)
    
    def get_diff(self, label_from: str, label_to: str) -> Optional[ContextDiff]:
        """
        获取两个快照之间的差异
        
        Args:
            label_from: 起始标签
            label_to: 结束标签
            
        Returns:
            ContextDiff实例或None
        """
        snapshot_from = self.get_snapshot(label_from)
        snapshot_to = self.get_snapshot(label_to)
        
        if snapshot_from is None or snapshot_to is None:
            _logger.warning(
                f"Cannot compute diff: missing snapshot ({label_from} or {label_to})"
            )
            return None
        
        return ContextDiff(snapshot_from, snapshot_to)
    
    def get_message_stats(self) -> Dict[str, Any]:
        """
        获取当前消息统计
        
        Returns:
            统计字典
        """
        messages = self.context.get_active_messages()
        
        stats = {
            "total_messages": len(messages),
            "by_role": defaultdict(int),
            "tool_calls": 0,
            "tool_results": 0,
        }
        
        for msg in messages:
            role = msg.get("role", "unknown")
            stats["by_role"][role] += 1
            
            if "tool_calls" in msg:
                stats["tool_calls"] += len(msg.get("tool_calls", []))
            
            if role == "tool":
                stats["tool_results"] += 1
        
        stats["by_role"] = dict(stats["by_role"])
        
        return stats
    
    def get_health_check(self) -> Dict[str, Any]:
        """
        执行Context健康检查
        
        Returns:
            健康状态字典
        """
        message_count = len(self.context.get_active_messages())
        round_count = len(self.context.manager.state.rounds)
        compression_count = self.context.manager.compression_count
        
        # 健康指标
        health = {
            "status": "healthy",
            "warnings": [],
            "metrics": {
                "message_count": message_count,
                "round_count": round_count,
                "compression_count": compression_count,
                "avg_messages_per_round": (
                    message_count / round_count if round_count > 0 else 0
                ),
            },
        }
        
        # 检查消息数是否过多（建议<100）
        if message_count > 100:
            health["warnings"].append(
                f"Message count is high ({message_count}). Consider compression."
            )
            health["status"] = "warning"
        
        # 检查压缩频率
        if round_count > 5 and compression_count == 0:
            health["warnings"].append(
                f"No compression after {round_count} rounds. Consider enabling compression."
            )
            health["status"] = "warning"
        
        return health
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取完整摘要
        
        Returns:
            摘要字典
        """
        summary = {
            "observer_stats": dict(self.stats),
            "current_context": {
                "message_count": len(self.context.get_active_messages()),
                "round_count": len(self.context.manager.state.rounds),
                "compression_count": self.context.manager.compression_count,
            },
            "message_stats": self.get_message_stats(),
            "health_check": self.get_health_check(),
            "snapshot_count": len(self.snapshots),
        }
        
        # 计算相邻快照的变化
        if len(self.snapshot_sequence) > 1:
            changes = []
            for i in range(len(self.snapshot_sequence) - 1):
                label_from = self.snapshot_sequence[i]
                label_to = self.snapshot_sequence[i + 1]
                
                diff = self.get_diff(label_from, label_to)
                if diff and diff.has_changes():
                    changes.append(diff.to_dict())
            
            summary["snapshot_changes"] = changes
        
        return summary
    
    def clear(self) -> None:
        """清空历史"""
        self.snapshots.clear()
        self.snapshot_sequence.clear()
        self.stats.clear()
        _logger.debug("ContextObserver cleared")
    
    def export_to_json(self, file_path: str) -> None:
        """
        导出到JSON文件
        
        Args:
            file_path: 文件路径
        """
        try:
            summary = self.get_summary()
            
            # 添加快照详情
            snapshots_detail = []
            for label in self.snapshot_sequence:
                if label in self.snapshots:
                    snapshots_detail.append(self.snapshots[label].to_dict())
            
            data = {
                "observer_type": "ContextObserver",
                "exported_at": datetime.now().isoformat(),
                "summary": summary,
                "snapshots": snapshots_detail,
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            _logger.info(f"Exported context history to {file_path}")
            
        except Exception as e:
            _logger.error(f"Failed to export history: {e}")
            raise

