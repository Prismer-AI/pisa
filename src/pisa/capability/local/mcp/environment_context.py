"""
Environment Context MCP

Provides system environment information including:
- Operating system details
- CPU information
- Memory usage
- Disk usage
- GPU information (if available)
- Network information
- Environment variables

This module provides functions to query the current runtime environment
that can be used by agents to adapt their behavior or provide context-aware responses.
"""

import platform
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import GPUtil
    HAS_GPUTIL = True
except ImportError:
    HAS_GPUTIL = False

from pisa.capability import capability


@capability(
    name="get_os_info",
    description="Get operating system information including OS name, version, architecture, and platform details",
    capability_type="function",
    tags=["system", "environment", "os"],
    strict_mode=False
)
async def get_os_info() -> Dict[str, Any]:
    """
    Get detailed operating system information
    
    Returns:
        Dictionary containing OS information including:
        - system: OS name (Linux, Darwin, Windows, etc.)
        - release: OS release version
        - version: Detailed version string
        - machine: Machine type (x86_64, arm64, etc.)
        - processor: Processor name
        - platform: Platform identifier
        - python_version: Python version
    """
    try:
        info = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "os": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "platform": platform.platform(),
                "architecture": platform.architecture()[0],
            },
            "python": {
                "version": platform.python_version(),
                "implementation": platform.python_implementation(),
                "compiler": platform.python_compiler(),
            },
            "node": {
                "name": platform.node(),
            }
        }
        
        return info
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve OS information"
        }


@capability(
    name="get_cpu_info",
    description="Get CPU information including core count, usage, and frequency",
    capability_type="function",
    tags=["system", "environment", "cpu"],
    strict_mode=False
)
async def get_cpu_info() -> Dict[str, Any]:
    """
    Get CPU information and current usage statistics
    
    Returns:
        Dictionary containing CPU information including:
        - physical_cores: Number of physical CPU cores
        - logical_cores: Number of logical CPU cores
        - current_freq: Current CPU frequency (if available)
        - usage_percent: Current CPU usage percentage
        - per_cpu_usage: Usage per CPU core (if available)
    """
    if not HAS_PSUTIL:
        return {
            "success": False,
            "error": "psutil not installed",
            "message": "Install psutil: pip install psutil"
        }
    
    try:
        cpu_freq = psutil.cpu_freq()
        
        info = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "usage_percent": psutil.cpu_percent(interval=1),
                "per_cpu_usage": psutil.cpu_percent(interval=1, percpu=True),
            }
        }
        
        if cpu_freq:
            info["cpu"]["frequency"] = {
                "current": cpu_freq.current,
                "min": cpu_freq.min,
                "max": cpu_freq.max,
            }
        
        # CPU times
        cpu_times = psutil.cpu_times()
        info["cpu"]["times"] = {
            "user": cpu_times.user,
            "system": cpu_times.system,
            "idle": cpu_times.idle,
        }
        
        return info
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve CPU information"
        }


@capability(
    name="get_memory_info",
    description="Get memory usage information including total, available, and used memory",
    capability_type="function",
    tags=["system", "environment", "memory"],
    strict_mode=False
)
async def get_memory_info() -> Dict[str, Any]:
    """
    Get memory usage statistics
    
    Returns:
        Dictionary containing memory information including:
        - total: Total physical memory
        - available: Available memory
        - used: Used memory
        - percent: Memory usage percentage
        - swap: Swap memory information (if available)
    """
    if not HAS_PSUTIL:
        return {
            "success": False,
            "error": "psutil not installed",
            "message": "Install psutil: pip install psutil"
        }
    
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        info = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "memory": {
                "total": mem.total,
                "available": mem.available,
                "used": mem.used,
                "free": mem.free,
                "percent": mem.percent,
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent,
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
            }
        }
        
        return info
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve memory information"
        }


@capability(
    name="get_disk_info",
    description="Get disk usage information for all mounted partitions",
    capability_type="function",
    tags=["system", "environment", "disk"],
    strict_mode=False
)
async def get_disk_info(path: str = "/") -> Dict[str, Any]:
    """
    Get disk usage statistics
    
    Args:
        path: Path to check disk usage for (default: root "/")
    
    Returns:
        Dictionary containing disk information including:
        - partitions: List of all mounted partitions
        - usage: Disk usage for specified path
        - io_counters: Disk I/O statistics (if available)
    """
    if not HAS_PSUTIL:
        return {
            "success": False,
            "error": "psutil not installed",
            "message": "Install psutil: pip install psutil"
        }
    
    try:
        # Get disk usage for specified path
        usage = psutil.disk_usage(path)
        
        info = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "disk": {
                "path": path,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
            },
            "partitions": []
        }
        
        # Get all partitions
        for partition in psutil.disk_partitions():
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                info["partitions"].append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": round(partition_usage.total / (1024**3), 2),
                    "used_gb": round(partition_usage.used / (1024**3), 2),
                    "free_gb": round(partition_usage.free / (1024**3), 2),
                    "percent": partition_usage.percent,
                })
            except PermissionError:
                # Skip partitions we don't have permission to access
                continue
        
        # Get disk I/O counters
        try:
            io_counters = psutil.disk_io_counters()
            if io_counters:
                info["io"] = {
                    "read_count": io_counters.read_count,
                    "write_count": io_counters.write_count,
                    "read_bytes": io_counters.read_bytes,
                    "write_bytes": io_counters.write_bytes,
                    "read_gb": round(io_counters.read_bytes / (1024**3), 2),
                    "write_gb": round(io_counters.write_bytes / (1024**3), 2),
                }
        except Exception:
            pass
        
        return info
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve disk information"
        }


@capability(
    name="get_gpu_info",
    description="Get GPU information including model, memory usage, and temperature (if available)",
    capability_type="function",
    tags=["system", "environment", "gpu"],
    strict_mode=False
)
async def get_gpu_info() -> Dict[str, Any]:
    """
    Get GPU information and usage statistics
    
    Returns:
        Dictionary containing GPU information including:
        - gpus: List of available GPUs with details
        - count: Number of GPUs detected
    """
    if not HAS_GPUTIL:
        return {
            "success": False,
            "error": "GPUtil not installed",
            "message": "Install GPUtil: pip install gputil (only works with NVIDIA GPUs)"
        }
    
    try:
        gpus = GPUtil.getGPUs()
        
        if not gpus:
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "message": "No GPUs detected",
                "count": 0,
                "gpus": []
            }
        
        info = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "count": len(gpus),
            "gpus": []
        }
        
        for gpu in gpus:
            gpu_info = {
                "id": gpu.id,
                "name": gpu.name,
                "driver": gpu.driver,
                "memory": {
                    "total": gpu.memoryTotal,
                    "used": gpu.memoryUsed,
                    "free": gpu.memoryFree,
                    "percent": round((gpu.memoryUsed / gpu.memoryTotal) * 100, 2) if gpu.memoryTotal > 0 else 0,
                },
                "load": gpu.load * 100,  # Convert to percentage
                "temperature": gpu.temperature,
            }
            info["gpus"].append(gpu_info)
        
        return info
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve GPU information (Note: GPUtil only supports NVIDIA GPUs)"
        }


@capability(
    name="get_network_info",
    description="Get network interface information and statistics",
    capability_type="function",
    tags=["system", "environment", "network"],
    strict_mode=False
)
async def get_network_info() -> Dict[str, Any]:
    """
    Get network interface information and statistics
    
    Returns:
        Dictionary containing network information including:
        - interfaces: List of network interfaces with addresses
        - io_counters: Network I/O statistics
    """
    if not HAS_PSUTIL:
        return {
            "success": False,
            "error": "psutil not installed",
            "message": "Install psutil: pip install psutil"
        }
    
    try:
        info = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "interfaces": {},
            "io_counters": {}
        }
        
        # Get network interfaces
        if_addrs = psutil.net_if_addrs()
        for interface_name, addresses in if_addrs.items():
            info["interfaces"][interface_name] = []
            for addr in addresses:
                addr_info = {
                    "family": str(addr.family),
                    "address": addr.address,
                }
                if addr.netmask:
                    addr_info["netmask"] = addr.netmask
                if addr.broadcast:
                    addr_info["broadcast"] = addr.broadcast
                info["interfaces"][interface_name].append(addr_info)
        
        # Get network I/O counters
        net_io = psutil.net_io_counters()
        if net_io:
            info["io_counters"] = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "bytes_sent_gb": round(net_io.bytes_sent / (1024**3), 2),
                "bytes_recv_gb": round(net_io.bytes_recv / (1024**3), 2),
            }
        
        return info
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve network information"
        }


@capability(
    name="get_process_info",
    description="Get information about the current Python process",
    capability_type="function",
    tags=["system", "environment", "process"],
    strict_mode=False
)
async def get_process_info() -> Dict[str, Any]:
    """
    Get information about the current Python process
    
    Returns:
        Dictionary containing process information including:
        - pid: Process ID
        - memory: Memory usage of the process
        - cpu: CPU usage of the process
        - threads: Number of threads
        - open_files: Number of open files
    """
    if not HAS_PSUTIL:
        return {
            "success": False,
            "error": "psutil not installed",
            "message": "Install psutil: pip install psutil"
        }
    
    try:
        process = psutil.Process()
        
        info = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "process": {
                "pid": process.pid,
                "name": process.name(),
                "status": process.status(),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "num_threads": process.num_threads(),
            }
        }
        
        # Memory info
        mem_info = process.memory_info()
        info["process"]["memory"] = {
            "rss": mem_info.rss,
            "vms": mem_info.vms,
            "rss_mb": round(mem_info.rss / (1024**2), 2),
            "vms_mb": round(mem_info.vms / (1024**2), 2),
        }
        
        # Try to get open files count
        try:
            open_files = process.open_files()
            info["process"]["open_files"] = len(open_files)
        except (PermissionError, psutil.AccessDenied):
            info["process"]["open_files"] = None
        
        # Try to get connections count
        try:
            connections = process.connections()
            info["process"]["connections"] = len(connections)
        except (PermissionError, psutil.AccessDenied):
            info["process"]["connections"] = None
        
        return info
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve process information"
        }


@capability(
    name="get_env_vars",
    description="Get environment variables (filtered to avoid sensitive data by default)",
    capability_type="function",
    tags=["system", "environment", "config"],
    strict_mode=False
)
async def get_env_vars(
    include_sensitive: bool = False,
    filter_pattern: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get environment variables
    
    Args:
        include_sensitive: Include potentially sensitive variables (API keys, passwords, etc.)
        filter_pattern: Optional pattern to filter variable names (case-insensitive)
    
    Returns:
        Dictionary containing environment variables
    """
    try:
        # List of patterns that might indicate sensitive data
        sensitive_patterns = [
            'key', 'token', 'secret', 'password', 'pwd', 'pass',
            'credential', 'auth', 'api', 'private'
        ]
        
        env_vars = {}
        
        for key, value in os.environ.items():
            # Apply filter pattern if provided
            if filter_pattern and filter_pattern.lower() not in key.lower():
                continue
            
            # Check if variable might be sensitive
            is_sensitive = any(pattern in key.lower() for pattern in sensitive_patterns)
            
            if is_sensitive and not include_sensitive:
                env_vars[key] = "***REDACTED***"
            else:
                env_vars[key] = value
        
        info = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "count": len(env_vars),
            "variables": env_vars,
            "warning": "Sensitive variables are redacted. Set include_sensitive=True to view all values." if not include_sensitive else None
        }
        
        return info
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve environment variables"
        }


@capability(
    name="get_full_system_report",
    description="Get a comprehensive system report including OS, CPU, memory, disk, GPU, and network information",
    capability_type="function",
    tags=["system", "environment", "report"],
    strict_mode=False
)
async def get_full_system_report() -> Dict[str, Any]:
    """
    Get a comprehensive system report
    
    Returns:
        Dictionary containing all available system information
    """
    try:
        report = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "report": {}
        }
        
        # Gather all information
        os_info = await get_os_info()
        if os_info.get("success"):
            report["report"]["os"] = os_info
        
        cpu_info = await get_cpu_info()
        if cpu_info.get("success"):
            report["report"]["cpu"] = cpu_info
        
        memory_info = await get_memory_info()
        if memory_info.get("success"):
            report["report"]["memory"] = memory_info
        
        disk_info = await get_disk_info()
        if disk_info.get("success"):
            report["report"]["disk"] = disk_info
        
        gpu_info = await get_gpu_info()
        report["report"]["gpu"] = gpu_info  # Include even if failed
        
        network_info = await get_network_info()
        if network_info.get("success"):
            report["report"]["network"] = network_info
        
        process_info = await get_process_info()
        if process_info.get("success"):
            report["report"]["process"] = process_info
        
        # Add summary
        report["summary"] = {
            "system": os_info.get("os", {}).get("system", "Unknown"),
            "cpu_cores": cpu_info.get("cpu", {}).get("logical_cores", "Unknown"),
            "memory_gb": memory_info.get("memory", {}).get("total_gb", "Unknown"),
            "disk_gb": disk_info.get("disk", {}).get("total_gb", "Unknown"),
            "gpu_count": gpu_info.get("count", 0),
            "python_version": os_info.get("python", {}).get("version", "Unknown"),
        }
        
        return report
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to generate system report"
        }


# Module-level info
__all__ = [
    "get_os_info",
    "get_cpu_info",
    "get_memory_info",
    "get_disk_info",
    "get_gpu_info",
    "get_network_info",
    "get_process_info",
    "get_env_vars",
    "get_full_system_report",
]

