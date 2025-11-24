"""
Temporal Activities (v4.0 Refactored)

定义可以在 Workflow 中执行的 Activities，适配v4.0架构。

Activities 是实际执行工作的单元：
- 保存/加载LoopState检查点
- 执行 Capability 调用
- 通知用户
- 数据库操作等
"""

import asyncio
import logging
from typing import Dict, Any
from dataclasses import dataclass
from pathlib import Path

from temporalio import activity

from pisa.core.loop.state import LoopState
from pisa.temporal.state_storage import (
    StateStorage,
    TemporalStateManager,
)

_logger = logging.getLogger(__name__)

# 全局状态管理器
_state_manager = None


def get_state_manager() -> TemporalStateManager:
    """获取全局状态管理器"""
    global _state_manager
    if _state_manager is None:
        _state_manager = TemporalStateManager()
    return _state_manager


# ==================== State Checkpoint Activities ====================

@activity.defn
async def save_state_checkpoint_activity(
    workflow_id: str,
    state_data: Dict[str, Any],
    checkpoint_name: str = "latest"
) -> Dict[str, str]:
    """
    保存State检查点
    
    Args:
        workflow_id: Workflow ID
        state_data: 序列化的State数据
        checkpoint_name: 检查点名称
        
    Returns:
        保存的文件路径
    """
    activity.logger.info(
        f"Saving state checkpoint: workflow={workflow_id}, checkpoint={checkpoint_name}"
    )
    
    try:
        # 反序列化State
        state = StateStorage.deserialize_state(state_data)
        
        # 获取状态管理器
        manager = get_state_manager()
        
        # 创建一个简单的context对象用于保存
        # 注意：实际应用中应该从workflow传递完整的context
        from pisa.core.loop.context import LoopContext
        context = LoopContext(
            agent_id=workflow_id,
            session_id=f"session_{workflow_id}"
        )
        
        # 保存检查点
        files = manager.save_checkpoint(
            workflow_id=workflow_id,
            state=state,
            context=context,
            checkpoint_name=checkpoint_name
        )
        
        # 发送心跳
        activity.heartbeat(f"Saved checkpoint {checkpoint_name}")
        
        activity.logger.info(f"Checkpoint saved: {checkpoint_name}")
        
        return {
            "workflow_id": workflow_id,
            "checkpoint_name": checkpoint_name,
            "state_file": str(files["state"]),
            "context_file": str(files["context"]),
            "metadata_file": str(files["metadata"]),
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to save checkpoint: {e}")
        raise


@activity.defn
async def load_state_checkpoint_activity(
    workflow_id: str,
    checkpoint_name: str = "latest"
) -> Dict[str, Any]:
    """
    加载State检查点
    
    Args:
        workflow_id: Workflow ID
        checkpoint_name: 检查点名称
        
    Returns:
        包含state和metadata的字典
    """
    activity.logger.info(
        f"Loading state checkpoint: workflow={workflow_id}, checkpoint={checkpoint_name}"
    )
    
    try:
        # 获取状态管理器
        manager = get_state_manager()
        
        # 加载检查点
        checkpoint = manager.load_checkpoint(workflow_id, checkpoint_name)
        
        # 序列化State用于传输
        state_data = StateStorage.serialize_state(checkpoint["state"])
        
        # 发送心跳
        activity.heartbeat(f"Loaded checkpoint {checkpoint_name}")
        
        activity.logger.info(f"Checkpoint loaded: {checkpoint_name}")
        
        return {
            "state": state_data,
            "metadata": checkpoint["metadata"],
            "context_file": str(checkpoint["context_file"]),
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to load checkpoint: {e}")
        raise


@activity.defn
async def list_checkpoints_activity(workflow_id: str) -> Dict[str, Any]:
    """
    列出所有检查点
    
    Args:
        workflow_id: Workflow ID
        
    Returns:
        检查点列表
    """
    activity.logger.info(f"Listing checkpoints: workflow={workflow_id}")
    
    try:
        manager = get_state_manager()
        checkpoints = manager.list_checkpoints(workflow_id)
        
        activity.logger.info(f"Found {len(checkpoints)} checkpoints")
        
        return {
            "workflow_id": workflow_id,
            "checkpoints": checkpoints,
            "count": len(checkpoints),
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to list checkpoints: {e}")
        return {
            "workflow_id": workflow_id,
            "checkpoints": [],
            "count": 0,
            "error": str(e),
        }


# ==================== Capability Execution (保留兼容性) ====================

@dataclass
class CapabilityCallRequest:
    """Capability 调用请求"""
    capability_name: str
    arguments: Dict[str, Any]
    call_id: str
    metadata: Dict[str, Any] = None


@activity.defn
async def execute_capability_activity(request: CapabilityCallRequest) -> Dict[str, Any]:
    """
    执行 Capability Activity
    
    Args:
        request: Capability 调用请求
        
    Returns:
        执行结果
    """
    activity.logger.info(
        f"Executing capability: {request.capability_name} (call_id={request.call_id})"
    )
    
    try:
        # 创建 ExecutionModule
        from pisa.core.loop.modules import ExecutionModule
        execution = ExecutionModule()
        
        # 创建一个简单的State用于执行
        state = LoopState(
            task={
                "capability": request.capability_name,
                "arguments": request.arguments,
                "call_id": request.call_id,
            }
        )
        
        # 执行 Capability
        result_state = await execution(state)
        
        activity.logger.info(
            f"Capability executed: {request.capability_name}"
        )
        
        # 发送心跳
        activity.heartbeat(f"Capability {request.capability_name} completed")
        
        return {
            "success": True,
            "result": result_state.result,
            "capability_name": request.capability_name,
            "call_id": request.call_id
        }
        
    except Exception as e:
        activity.logger.error(
            f"Capability execution failed: {request.capability_name}, error: {str(e)}"
        )
        return {
            "success": False,
            "error": str(e),
            "capability_name": request.capability_name,
            "call_id": request.call_id
        }


# ==================== Notification Activities ====================

@activity.defn
async def notify_user_activity(notification: Dict[str, Any]) -> Dict[str, Any]:
    """
    通知用户Activity
    
    Args:
        notification: 通知内容
        
    Returns:
        通知结果
    """
    activity.logger.info(f"Sending notification: {notification}")
    
    try:
        # 实际实现中应该发送邮件、Slack消息等
        # 这里只是记录日志
        activity.logger.info(
            f"Notification sent: workflow={notification.get('workflow_id')}, "
            f"status={notification.get('status')}"
        )
        
        return {
            "success": True,
            "notification_id": f"notif_{notification.get('workflow_id')}",
            "timestamp": activity.now().isoformat(),
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to send notification: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ==================== Context Activities (向后兼容) ====================

@activity.defn
async def save_context_activity(
    agent_id: str,
    session_id: str,
    context_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    保存Context Activity (向后兼容)
    
    Args:
        agent_id: Agent ID
        session_id: Session ID
        context_data: Context数据
        
    Returns:
        保存结果
    """
    activity.logger.info(f"Saving context: agent={agent_id}, session={session_id}")
    
    try:
        # 这里应该保存到数据库或文件系统
        # 为了简化，我们只记录日志
        activity.logger.info(f"Context saved: {agent_id}/{session_id}")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "session_id": session_id,
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to save context: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@activity.defn
async def compress_context_activity(
    agent_id: str,
    session_id: str,
    strategy: str = "adaptive"
) -> Dict[str, Any]:
    """
    压缩Context Activity (向后兼容)
    
    Args:
        agent_id: Agent ID
        session_id: Session ID
        strategy: 压缩策略
        
    Returns:
        压缩结果
    """
    activity.logger.info(
        f"Compressing context: agent={agent_id}, session={session_id}, strategy={strategy}"
    )
    
    try:
        # 实际实现中应该调用ContextManager的压缩方法
        activity.logger.info(f"Context compressed: {agent_id}/{session_id}")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "session_id": session_id,
            "strategy": strategy,
            "compression_ratio": 0.5,  # 示例值
        }
        
    except Exception as e:
        activity.logger.error(f"Failed to compress context: {e}")
        return {
            "success": False,
            "error": str(e),
        }
