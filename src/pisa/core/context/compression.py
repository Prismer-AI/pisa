"""
Context Compression Module

使用 LLM 实现上下文压缩，支持多种压缩策略
"""

import time
import logging
from typing import List, Optional
from datetime import datetime

from pisa.config import Config
from .models import (
    RoundContext,
    ContextState,
    CompressionStrategy,
    CompressionResult,
)

_logger = logging.getLogger(__name__)


class ContextCompressor:
    """
    上下文压缩器
    
    使用 LLM 对上下文进行智能压缩，保留关键信息
    """
    
    def __init__(self, compression_model: Optional[str] = None):
        """
        初始化压缩器
        
        Args:
            compression_model: 压缩使用的模型，默认使用 config 中的配置
        """
        self.compression_model = compression_model or Config.agent_default_model
        
        # 确保 Agent SDK 已配置
        if not Config.has_agent_sdk():
            raise RuntimeError(
                "OpenAI Agent SDK not available. Please install: pip install agents-sdk"
            )
        
        # 设置 Agent SDK
        Config.setup_agent_sdk(
            disable_tracing=True,
            use_chat_completions=True
        )
        
        _logger.info(f"ContextCompressor initialized with model: {self.compression_model}")
    
    async def compress_context(
        self,
        context: ContextState,
        strategy: Optional[CompressionStrategy] = None
    ) -> ContextState:
        """
        压缩上下文
        
        Args:
            context: 要压缩的上下文
            strategy: 压缩策略，默认使用 context 中的配置
            
        Returns:
            压缩后的上下文
        """
        start_time = time.time()
        strategy = strategy or context.compression_strategy
        
        _logger.info(f"Starting compression with strategy: {strategy}")
        
        if strategy == CompressionStrategy.PER_ROUND:
            result = await self._compress_per_round(context)
        elif strategy == CompressionStrategy.MULTI_ROUND:
            result = await self._compress_multi_round(context)
        elif strategy == CompressionStrategy.SEMANTIC_MERGE:
            result = await self._compress_semantic_merge(context)
        elif strategy == CompressionStrategy.ADAPTIVE:
            result = await self._compress_adaptive(context)
        else:
            raise ValueError(f"Unknown compression strategy: {strategy}")
        
        # 更新压缩统计
        context.compression_count += 1
        context.last_compression_at = datetime.now()
        
        duration_ms = (time.time() - start_time) * 1000
        _logger.info(
            f"Compression completed: {result.original_tokens} → {result.compressed_tokens} tokens "
            f"({result.compression_ratio:.2%} ratio) in {duration_ms:.2f}ms"
        )
        
        return context
    
    async def _compress_per_round(self, context: ContextState) -> CompressionResult:
        """
        单轮压缩策略
        
        为每个未压缩的轮次生成摘要，原始内容降级到 H3
        """
        original_tokens = 0
        compressed_tokens = 0
        
        for round_ctx in context.rounds:
            # 跳过已压缩的轮次
            if round_ctx.compressed_content or round_ctx.heading_level > 2:
                continue
            
            # 计算原始 tokens
            round_tokens = self._estimate_tokens(round_ctx.raw_content)
            original_tokens += round_tokens
            
            # 生成压缩内容
            compressed = await self._compress_round_content(round_ctx)
            compressed_tokens += self._estimate_tokens(compressed)
            
            # 更新轮次
            round_ctx.compressed_content = compressed
            round_ctx.heading_level = 3  # 原始内容降级到 H3
            round_ctx.compression_ratio = compressed_tokens / round_tokens if round_tokens > 0 else 1.0
        
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        
        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            compressed_content="",  # Per-round 不生成单一内容
            strategy_used=CompressionStrategy.PER_ROUND,
            duration_ms=0  # 在外层计算
        )
    
    async def _compress_multi_round(self, context: ContextState) -> CompressionResult:
        """
        多轮合并压缩策略
        
        将多个已归档（H3）的轮次合并压缩为超压缩轮次（H2），
        原轮次降级到 H4
        """
        archived_rounds = [r for r in context.rounds if r.heading_level == 3]
        
        if len(archived_rounds) < 3:
            # 归档轮次不足，回退到 per_round
            return await self._compress_per_round(context)
        
        # 合并内容
        merged_content = "\n\n---\n\n".join(
            r.compressed_content or r.raw_content 
            for r in archived_rounds
        )
        
        original_tokens = self._estimate_tokens(merged_content)
        
        # 生成超压缩内容
        super_compressed = await self._compress_merged_content(merged_content)
        compressed_tokens = self._estimate_tokens(super_compressed)
        
        # 创建超压缩轮次
        super_round = RoundContext(
            round_id=-1,  # 特殊标记
            raw_content=merged_content,
            compressed_content=super_compressed,
            tokens_used=compressed_tokens,
            heading_level=2,
            compression_ratio=compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        )
        
        # 移除旧轮次，插入超压缩轮次
        for r in archived_rounds:
            r.heading_level = 4  # 深度归档
        
        # 在第一个归档轮次位置插入超压缩轮次
        first_archived_idx = context.rounds.index(archived_rounds[0])
        context.rounds.insert(first_archived_idx, super_round)
        
        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compressed_tokens / original_tokens if original_tokens > 0 else 1.0,
            compressed_content=super_compressed,
            strategy_used=CompressionStrategy.MULTI_ROUND,
            duration_ms=0
        )
    
    async def _compress_semantic_merge(self, context: ContextState) -> CompressionResult:
        """
        语义合并压缩策略
        
        提取关键事实和知识点，创建知识库式压缩
        """
        all_rounds_content = "\n\n---\n\n".join(
            r.compressed_content or r.raw_content 
            for r in context.rounds
        )
        
        original_tokens = self._estimate_tokens(all_rounds_content)
        
        # 提取关键事实
        key_facts = await self._extract_key_facts(all_rounds_content)
        compressed_tokens = self._estimate_tokens(key_facts)
        
        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compressed_tokens / original_tokens if original_tokens > 0 else 1.0,
            compressed_content=key_facts,
            strategy_used=CompressionStrategy.SEMANTIC_MERGE,
            duration_ms=0
        )
    
    async def _compress_adaptive(self, context: ContextState) -> CompressionResult:
        """
        自适应压缩策略
        
        根据当前状态选择最佳策略
        """
        archived_count = sum(1 for r in context.rounds if r.heading_level >= 3)
        uncompressed_count = sum(
            1 for r in context.rounds 
            if not r.compressed_content and r.heading_level == 2
        )
        
        # 决策逻辑
        if uncompressed_count >= 2:
            # 有多个未压缩轮次，使用 per_round
            return await self._compress_per_round(context)
        elif archived_count >= 3:
            # 有足够多归档轮次，使用 multi_round
            return await self._compress_multi_round(context)
        else:
            # 默认使用 per_round
            return await self._compress_per_round(context)
    
    async def _compress_round_content(self, round_ctx: RoundContext) -> str:
        """
        压缩单个轮次的内容
        
        使用 LLM 生成摘要
        """
        # 构建压缩 prompt
        prompt = self._build_compression_prompt(round_ctx.raw_content)
        
        try:
            # 使用 OpenAI Agent SDK 的 client
            client = Config.get_openai_client()
            
            response = await client.chat.completions.create(
                model=self.compression_model,
                messages=[
                    {
                        "role": "system",
                        "content": COMPRESSION_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            compressed = response.choices[0].message.content.strip()
            return compressed
            
        except Exception as e:
            _logger.error(f"Compression failed: {e}")
            # 降级：返回截断的原始内容
            return round_ctx.raw_content[:500] + "..."
    
    async def _compress_merged_content(self, merged_content: str) -> str:
        """压缩合并后的内容"""
        prompt = f"""以下是多个对话轮次的内容，请提取最重要的信息，生成一个超级简洁的摘要。

内容：
{merged_content}

要求：
- 保留所有关键决策和结果
- 去除重复信息
- 极度简洁（目标：原内容的 20-30%）
"""
        
        try:
            client = Config.get_openai_client()
            
            response = await client.chat.completions.create(
                model=self.compression_model,
                messages=[
                    {"role": "system", "content": COMPRESSION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            _logger.error(f"Multi-round compression failed: {e}")
            return merged_content[:800] + "..."
    
    async def _extract_key_facts(self, content: str) -> str:
        """提取关键事实"""
        prompt = f"""从以下对话中提取关键事实和知识点，以结构化的方式呈现。

内容：
{content}

要求：
- 提取所有重要的事实、决策、结果
- 组织成清晰的要点列表
- 保持简洁但完整
"""
        
        try:
            client = Config.get_openai_client()
            
            response = await client.chat.completions.create(
                model=self.compression_model,
                messages=[
                    {"role": "system", "content": KEY_FACTS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            _logger.error(f"Key facts extraction failed: {e}")
            return content[:1000] + "..."
    
    def _build_compression_prompt(self, content: str) -> str:
        """构建压缩 prompt"""
        return f"""请压缩以下对话内容，保留关键信息。

内容：
{content}

要求：
- 保留所有关键事实和决策
- 保留重要的工具调用和结果
- 去除冗余和重复
- 目标长度：原内容的 30-40%
"""
    
    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本的 token 数
        
        简单估算：1 token ≈ 4 字符
        """
        return len(text) // 4


# Compression System Prompts

COMPRESSION_SYSTEM_PROMPT = """You are a context compression specialist. Your job is to summarize conversation content while preserving all critical information.

Key guidelines:
- Preserve all important facts, decisions, and outcomes
- Preserve all tool calls and their results
- Remove redundant information and filler
- Use concise language
- Maintain chronological order
- Target: 30-40% of original length
"""

KEY_FACTS_SYSTEM_PROMPT = """You are a knowledge extraction specialist. Your job is to extract key facts and insights from conversations.

Key guidelines:
- Extract all important facts and decisions
- Organize information in a structured way
- Use bullet points for clarity
- Remove redundant information
- Preserve context for each fact
- Target: Clear, concise knowledge base
"""
