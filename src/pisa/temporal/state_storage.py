"""
State Storage for Temporal

负责LoopState和LoopContext的序列化/反序列化，支持Temporal持久化。

特点：
1. LoopState序列化到JSON（Temporal原生支持）
2. LoopContext序列化到Markdown文件（易读、可恢复）
3. 支持断点续传
4. 支持增量保存
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime

from pisa.core.loop.state import LoopState
from pisa.core.loop.context import LoopContext
from pisa.core.context import ContextState, Message

_logger = logging.getLogger(__name__)


class StateStorage:
    """
    状态存储
    
    负责LoopState的序列化/反序列化
    """
    
    @staticmethod
    def serialize_state(state: LoopState) -> Dict[str, Any]:
        """
        序列化LoopState到字典
        
        Args:
            state: LoopState实例
            
        Returns:
            可序列化的字典
        """
        try:
            # 使用Pydantic的model_dump
            data = state.model_dump(mode='json')
            
            # 添加类型信息便于反序列化
            data['__type__'] = 'LoopState'
            data['__version__'] = '4.0'
            
            _logger.debug(f"Serialized LoopState: {len(str(data))} bytes")
            return data
            
        except Exception as e:
            _logger.error(f"Failed to serialize LoopState: {e}")
            raise
    
    @staticmethod
    def deserialize_state(data: Dict[str, Any]) -> LoopState:
        """
        反序列化字典到LoopState
        
        Args:
            data: 序列化的字典
            
        Returns:
            LoopState实例
        """
        try:
            # 验证类型
            if data.get('__type__') != 'LoopState':
                raise ValueError(f"Invalid state type: {data.get('__type__')}")
            
            # 移除元数据
            data = {k: v for k, v in data.items() if not k.startswith('__')}
            
            # 反序列化
            state = LoopState(**data)
            
            _logger.debug("Deserialized LoopState successfully")
            return state
            
        except Exception as e:
            _logger.error(f"Failed to deserialize LoopState: {e}")
            raise
    
    @staticmethod
    def save_state_to_file(state: LoopState, file_path: Path) -> None:
        """
        保存LoopState到文件
        
        Args:
            state: LoopState实例
            file_path: 保存路径
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = StateStorage.serialize_state(state)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            _logger.info(f"Saved LoopState to {file_path}")
            
        except Exception as e:
            _logger.error(f"Failed to save LoopState: {e}")
            raise
    
    @staticmethod
    def load_state_from_file(file_path: Path) -> LoopState:
        """
        从文件加载LoopState
        
        Args:
            file_path: 文件路径
            
        Returns:
            LoopState实例
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            state = StateStorage.deserialize_state(data)
            
            _logger.info(f"Loaded LoopState from {file_path}")
            return state
            
        except Exception as e:
            _logger.error(f"Failed to load LoopState: {e}")
            raise


class ContextStorage:
    """
    上下文存储
    
    负责LoopContext的序列化/反序列化到Markdown文件
    """
    
    @staticmethod
    def serialize_context(context: LoopContext) -> str:
        """
        序列化LoopContext到Markdown
        
        Args:
            context: LoopContext实例
            
        Returns:
            Markdown格式的字符串
        """
        try:
            # 获取底层的ContextState
            state = context.manager.get_state()
            
            # 构建Markdown
            lines = []
            lines.append("# Agent Context")
            lines.append("")
            lines.append(f"**Agent ID**: {state.agent_id}")
            lines.append(f"**Session ID**: {state.session_id}")
            lines.append(f"**Created**: {state.created_at}")
            lines.append(f"**Total Rounds**: {state.total_rounds}")
            lines.append(f"**Total Tokens**: {state.total_tokens}")
            lines.append("")
            
            # 所有消息
            lines.append("## Messages")
            lines.append("")
            
            for i, msg in enumerate(state.all_messages, 1):
                lines.append(f"### Message {i} - {msg.role.value}")
                lines.append("")
                lines.append(f"**Round**: {msg.round_id}")
                lines.append(f"**Timestamp**: {msg.timestamp}")
                lines.append("")
                lines.append(f"```")
                lines.append(msg.content)
                lines.append(f"```")
                lines.append("")
            
            # 压缩历史
            if state.compression_history:
                lines.append("## Compression History")
                lines.append("")
                for i, comp in enumerate(state.compression_history, 1):
                    lines.append(f"### Compression {i}")
                    lines.append(f"- Strategy: {comp.strategy}")
                    lines.append(f"- Original Tokens: {comp.original_tokens}")
                    lines.append(f"- Compressed Tokens: {comp.compressed_tokens}")
                    lines.append(f"- Ratio: {comp.compression_ratio:.2%}")
                    lines.append("")
            
            markdown = "\n".join(lines)
            
            _logger.debug(f"Serialized LoopContext: {len(markdown)} bytes")
            return markdown
            
        except Exception as e:
            _logger.error(f"Failed to serialize LoopContext: {e}")
            raise
    
    @staticmethod
    def save_context_to_file(context: LoopContext, file_path: Path) -> None:
        """
        保存LoopContext到Markdown文件
        
        Args:
            context: LoopContext实例
            file_path: 保存路径
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            markdown = ContextStorage.serialize_context(context)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            _logger.info(f"Saved LoopContext to {file_path}")
            
        except Exception as e:
            _logger.error(f"Failed to save LoopContext: {e}")
            raise
    
    @staticmethod
    def get_context_summary(context: LoopContext) -> Dict[str, Any]:
        """
        获取上下文摘要（用于Temporal事件）
        
        Args:
            context: LoopContext实例
            
        Returns:
            摘要字典
        """
        try:
            state = context.manager.get_state()
            
            return {
                "agent_id": state.agent_id,
                "session_id": state.session_id,
                "total_rounds": state.total_rounds,
                "total_messages": len(state.all_messages),
                "total_tokens": state.total_tokens,
                "active_messages": len(context.get_active_messages()),
                "compressed_count": len(state.compression_history),
            }
            
        except Exception as e:
            _logger.error(f"Failed to get context summary: {e}")
            return {}


class TemporalStateManager:
    """
    Temporal状态管理器
    
    统一管理LoopState和LoopContext的持久化
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        初始化
        
        Args:
            base_path: 基础存储路径，默认为./temporal_storage
        """
        self.base_path = base_path or Path("./temporal_storage")
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        _logger.info(f"TemporalStateManager initialized: {self.base_path}")
    
    def get_workflow_path(self, workflow_id: str) -> Path:
        """
        获取workflow的存储路径
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            存储路径
        """
        return self.base_path / workflow_id
    
    def save_checkpoint(
        self,
        workflow_id: str,
        state: LoopState,
        context: LoopContext,
        checkpoint_name: str = "latest"
    ) -> Dict[str, Path]:
        """
        保存检查点
        
        Args:
            workflow_id: Workflow ID
            state: LoopState实例
            context: LoopContext实例
            checkpoint_name: 检查点名称
            
        Returns:
            保存的文件路径
        """
        try:
            workflow_path = self.get_workflow_path(workflow_id)
            workflow_path.mkdir(parents=True, exist_ok=True)
            
            # 保存State
            state_file = workflow_path / f"state_{checkpoint_name}.json"
            StateStorage.save_state_to_file(state, state_file)
            
            # 保存Context
            context_file = workflow_path / f"context_{checkpoint_name}.md"
            ContextStorage.save_context_to_file(context, context_file)
            
            # 保存元数据
            metadata_file = workflow_path / f"metadata_{checkpoint_name}.json"
            metadata = {
                "workflow_id": workflow_id,
                "checkpoint_name": checkpoint_name,
                "timestamp": datetime.now().isoformat(),
                "state_iteration": state.iteration,
                "context_summary": ContextStorage.get_context_summary(context),
            }
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            _logger.info(f"Saved checkpoint '{checkpoint_name}' for workflow {workflow_id}")
            
            return {
                "state": state_file,
                "context": context_file,
                "metadata": metadata_file,
            }
            
        except Exception as e:
            _logger.error(f"Failed to save checkpoint: {e}")
            raise
    
    def load_checkpoint(
        self,
        workflow_id: str,
        checkpoint_name: str = "latest"
    ) -> Dict[str, Any]:
        """
        加载检查点
        
        Args:
            workflow_id: Workflow ID
            checkpoint_name: 检查点名称
            
        Returns:
            包含state和metadata的字典
        """
        try:
            workflow_path = self.get_workflow_path(workflow_id)
            
            # 加载State
            state_file = workflow_path / f"state_{checkpoint_name}.json"
            state = StateStorage.load_state_from_file(state_file)
            
            # 加载元数据
            metadata_file = workflow_path / f"metadata_{checkpoint_name}.json"
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            _logger.info(f"Loaded checkpoint '{checkpoint_name}' for workflow {workflow_id}")
            
            return {
                "state": state,
                "metadata": metadata,
                "context_file": workflow_path / f"context_{checkpoint_name}.md",
            }
            
        except Exception as e:
            _logger.error(f"Failed to load checkpoint: {e}")
            raise
    
    def list_checkpoints(self, workflow_id: str) -> List[str]:
        """
        列出所有检查点
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            检查点名称列表
        """
        try:
            workflow_path = self.get_workflow_path(workflow_id)
            
            if not workflow_path.exists():
                return []
            
            # 查找所有state文件
            checkpoints = []
            for state_file in workflow_path.glob("state_*.json"):
                # 提取检查点名称
                name = state_file.stem.replace("state_", "")
                checkpoints.append(name)
            
            return sorted(checkpoints)
            
        except Exception as e:
            _logger.error(f"Failed to list checkpoints: {e}")
            return []



