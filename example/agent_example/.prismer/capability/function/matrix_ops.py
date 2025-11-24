"""
Matrix Operations Capability

提供矩阵运算功能
"""

from typing import List, Dict, Any
import numpy as np

from pisa.capability import capability


@capability(
    name="matrix_operations",
    description="执行矩阵运算，支持加法、乘法、转置等操作",
    capability_type="function",
    tags=["matrix", "math", "computation"],
    auto_register=True
)
def matrix_operations(
    operation: str,
    matrix_a: List[List[float]],
    matrix_b: List[List[float]] = None
) -> Dict[str, Any]:
    """
    执行矩阵运算
    
    Args:
        operation: 操作类型 ('add', 'multiply', 'transpose', 'inverse')
        matrix_a: 第一个矩阵
        matrix_b: 第二个矩阵（某些操作需要）
    
    Returns:
        包含运算结果的字典
    """
    try:
        # 转换为 numpy 数组
        a = np.array(matrix_a)
        
        if operation == "transpose":
            result = a.T
            return {
                "success": True,
                "operation": operation,
                "result": result.tolist(),
                "shape": result.shape
            }
        
        elif operation == "inverse":
            result = np.linalg.inv(a)
            return {
                "success": True,
                "operation": operation,
                "result": result.tolist(),
                "shape": result.shape
            }
        
        # 需要两个矩阵的操作
        if matrix_b is None:
            return {
                "success": False,
                "error": f"Operation '{operation}' requires matrix_b"
            }
        
        b = np.array(matrix_b)
        
        if operation == "add":
            result = a + b
        elif operation == "multiply":
            result = np.matmul(a, b)
        elif operation == "element_multiply":
            result = a * b
        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}. Supported: add, multiply, element_multiply, transpose, inverse"
            }
        
        return {
            "success": True,
            "operation": operation,
            "result": result.tolist(),
            "shape": result.shape
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "operation": operation
        }
