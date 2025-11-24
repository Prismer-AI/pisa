"""
Softmax MCP Capability

作为MCP Server提供Softmax计算功能
"""

from typing import List, Dict, Any
import numpy as np
import logging

from pisa.capability import capability

_logger = logging.getLogger(__name__)


@capability(
    name="compute_softmax",
    description="计算向量或矩阵的Softmax，支持指定axis。参数: input_data(必需,array)-输入数据, axis(可选,int,默认-1)-计算的轴, temperature(可选,float,默认1.0)-温度参数",
    capability_type="function",  # 实际是FunctionTool，用tags区分逻辑分类
    tags=["mcp", "math", "softmax", "normalization"],
    strict_mode=False
)
async def compute_softmax(
    input_data: List[float] | List[List[float]],
    axis: int = -1,
    temperature: float = 1.0
) -> Dict[str, Any]:
    """
    计算Softmax函数
    
    Softmax(x_i) = exp(x_i / T) / sum(exp(x_j / T))
    
    Args:
        input_data: 输入数据（一维或二维数组）
        axis: 计算softmax的轴（默认-1，最后一个轴）
        temperature: 温度参数，控制分布的锐度（默认1.0）
        
    Returns:
        {
            "success": bool,
            "result": List[float] or List[List[float]],
            "input_shape": List[int],
            "output_shape": List[int],
            "temperature": float,
            "sum_check": float,  # 验证和是否为1
            "message": str
        }
    """
    try:
        _logger.info(f"Computing softmax with temperature={temperature}, axis={axis}")
        
        # 转换为numpy数组
        x = np.array(input_data, dtype=np.float64)
        original_shape = x.shape
        
        # 应用温度参数
        x_scaled = x / temperature
        
        # 数值稳定的softmax计算（减去最大值避免溢出）
        x_max = np.max(x_scaled, axis=axis, keepdims=True)
        exp_x = np.exp(x_scaled - x_max)
        softmax_result = exp_x / np.sum(exp_x, axis=axis, keepdims=True)
        
        # 转换为列表
        result_list = softmax_result.tolist()
        
        # 验证：softmax的和应该为1（或接近1）
        sum_check = float(np.sum(softmax_result, axis=axis).mean())
        
        return {
            "success": True,
            "result": result_list,
            "input_shape": list(original_shape),
            "output_shape": list(softmax_result.shape),
            "temperature": temperature,
            "axis": axis,
            "sum_check": sum_check,
            "is_valid": abs(sum_check - 1.0) < 1e-6,
            "message": f"Softmax computed successfully (sum check: {sum_check:.6f})"
        }
        
    except Exception as e:
        _logger.error(f"Softmax computation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "temperature": temperature,
            "axis": axis
        }


@capability(
    name="softmax_with_attention",
    description="计算带注意力权重的Softmax，常用于Transformer。参数: query(必需,array)-查询向量, keys(必需,array)-键向量集合, scale(可选,bool,默认True)-是否按维度开方缩放",
    capability_type="function",
    tags=["mcp", "attention", "softmax", "transformer"],
    strict_mode=False
)
async def softmax_with_attention(
    query: List[float],
    keys: List[List[float]],
    scale: bool = True
) -> Dict[str, Any]:
    """
    计算注意力权重（Scaled Dot-Product Attention的softmax部分）
    
    Args:
        query: 查询向量 (d,)
        keys: 键向量集合 (n, d)
        scale: 是否按sqrt(d)缩放
        
    Returns:
        {
            "success": bool,
            "attention_weights": List[float],
            "scores": List[float],
            "scale_factor": float,
            "message": str
        }
    """
    try:
        _logger.info("Computing attention softmax")
        
        q = np.array(query, dtype=np.float64)
        k = np.array(keys, dtype=np.float64)
        
        # 计算点积得分
        scores = np.dot(k, q)  # (n,)
        
        # 可选的缩放
        scale_factor = 1.0
        if scale:
            d_k = q.shape[0]
            scale_factor = np.sqrt(d_k)
            scores = scores / scale_factor
        
        # 应用softmax
        scores_max = np.max(scores)
        exp_scores = np.exp(scores - scores_max)
        attention_weights = exp_scores / np.sum(exp_scores)
        
        return {
            "success": True,
            "attention_weights": attention_weights.tolist(),
            "raw_scores": scores.tolist(),
            "scale_factor": float(scale_factor),
            "query_dim": q.shape[0],
            "num_keys": k.shape[0],
            "message": f"Attention weights computed for {k.shape[0]} keys"
        }
        
    except Exception as e:
        _logger.error(f"Attention softmax failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }



