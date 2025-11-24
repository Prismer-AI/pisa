"""
Capability Models and Core Classes

This module contains the core data models and base classes for capabilities.
All decorator and registry logic has been moved to registry.py.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union, Literal, Callable, get_type_hints
from datetime import datetime
import inspect
import logging

from pydantic import BaseModel, Field

_logger = logging.getLogger(__name__)


# Type definitions
CapabilityType = Literal["function", "agent", "mcp"]


def _is_agent(obj: Any) -> bool:
    """Check if an object is an Agent instance."""
    try:
        from agents import Agent, AgentBase
        return isinstance(obj, (Agent, AgentBase))
    except ImportError:
        # Check by class name and attributes
        return (
            hasattr(obj, 'name') and
            hasattr(obj, 'instructions') and
            hasattr(obj, 'tools')
        )


def _is_mcp_server(obj: Any) -> bool:
    """Check if an object is an MCP server instance."""
    try:
        from agents.mcp.server import MCPServer
        if isinstance(obj, MCPServer):
            return True
    except ImportError:
        pass
    
    # Check by attributes (fallback for non-standard MCP servers)
    if hasattr(obj, 'name') and hasattr(obj, 'list_tools') and hasattr(obj, 'call_tool'):
        if not _is_agent(obj):
            return True
    
    return False


class Capability(BaseModel):
    """
    Capability metadata and configuration.
    
    Represents a capability (function, agent, or MCP server) with its metadata.
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    capability_type: CapabilityType
    calling_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: str = Field(default="active")
    async_execution: bool = Field(default=True)
    max_retries: int = Field(default=3)
    tags: List[str] = Field(default_factory=list)
    """Tags for categorizing and filtering capabilities"""
    
    source: str = Field(default="custom")
    """Source of the capability: 'internal' (built-in) or 'custom' (user-defined)"""
    
    # Native object references for agent and mcp types
    agent_object: Optional[Any] = Field(default=None, exclude=True)
    """Reference to the native Agent object (for capability_type='agent')"""
    
    mcp_server_object: Optional[Any] = Field(default=None, exclude=True)
    """Reference to the native MCP server object (for capability_type='mcp')"""
    
    # Agent-specific metadata
    agent_config: Optional[Dict[str, Any]] = Field(default=None)
    """Agent configuration metadata (name, instructions, model, etc.)"""
    
    # MCP-specific metadata
    mcp_config: Optional[Dict[str, Any]] = Field(default=None)
    """MCP server configuration metadata"""
    
    def to_dict(self) -> Dict[str, Any]:
        """Dump the Capability to a dictionary."""
        data = self.model_dump(exclude={'agent_object', 'mcp_server_object'})
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Capability':
        """Load the Capability from a dictionary."""
        return cls.model_validate(data)
    
    def get_object(self, registry: Optional[Any] = None) -> Any:
        """
        Get the native object for this capability.
        
        Args:
            registry: Optional registry to use (defaults to global registry)
        
        Returns:
            - For 'function': The function object
            - For 'agent': The Agent object
            - For 'mcp': The MCP server object
        """
        if self.capability_type == "agent":
            return self.agent_object
        elif self.capability_type == "mcp":
            return self.mcp_server_object
        elif self.capability_type == "function":
            # For functions, we need to get from registry
            if registry is None:
                from .registry import get_global_registry
                registry = get_global_registry()
            func = registry.get_function(self.name)
            return func
        return None
    
    def get_for_agent(self) -> Any:
        """
        Get the object in the format needed for Agent configuration.
        
        Returns:
            - For 'function': The function (can be used directly in tools list)
            - For 'agent': The Agent object (can be used in handoffs)
            - For 'mcp': The MCP server object (can be used in mcp_servers)
        """
        return self.get_object()
    
    @classmethod
    def from_function(
        cls,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        capability_type: CapabilityType = "function",
        **kwargs
    ) -> 'Capability':
        """
        Create a Capability from a function using inspect.
        
        Args:
            func: The function to inspect
            name: Optional name override (defaults to function name)
            description: Optional description override (defaults to function docstring)
            capability_type: Type of capability (default: "function")
            **kwargs: Additional parameters to pass to Capability constructor
        
        Returns:
            Capability instance with automatically extracted information
        """
        func_name = name or func.__name__
        func_description = description or (inspect.getdoc(func) or "")
        sig = inspect.signature(func)
        
        try:
            type_hints = get_type_hints(func, include_extras=True)
        except Exception:
            type_hints = {}
        
        parameters: Dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'cls'):
                continue
            
            param_info: Dict[str, Any] = {}
            param_type = type_hints.get(param_name, Any)
            
            # Type conversion logic (simplified)
            if param_type is str or (isinstance(param_type, type) and param_type == str):
                param_info["type"] = "string"
            elif param_type is int or (isinstance(param_type, type) and param_type == int):
                param_info["type"] = "integer"
            elif param_type is float or (isinstance(param_type, type) and param_type == float):
                param_info["type"] = "number"
            elif param_type is bool or (isinstance(param_type, type) and param_type == bool):
                param_info["type"] = "boolean"
            else:
                param_info["type"] = "string"
            
            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default
            
            param_info["description"] = f"Parameter {param_name}"
            parameters["properties"][param_name] = param_info
            
            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)
        
        return cls(
            name=func_name,
            description=func_description,
            parameters=parameters,
            capability_type=capability_type,
            **kwargs
        )
    
    @classmethod
    def from_agent(
        cls,
        agent: Any,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> 'Capability':
        """Create a Capability from an Agent object."""
        agent_name = name or getattr(agent, 'name', 'unknown_agent')
        
        if description:
            agent_description = description
        else:
            agent_description = (
                getattr(agent, 'handoff_description', None) or
                getattr(agent, 'instructions', None) or
                f"Agent: {agent_name}"
            )
            if callable(agent_description):
                agent_description = f"Agent: {agent_name} (dynamic instructions)"
        
        agent_config = {
            "name": agent_name,
            "instructions": str(getattr(agent, 'instructions', '')) if not callable(getattr(agent, 'instructions', None)) else "<dynamic>",
            "model": str(getattr(agent, 'model', 'default')),
            "handoff_description": getattr(agent, 'handoff_description', None),
            "tools_count": len(getattr(agent, 'tools', [])),
            "mcp_servers_count": len(getattr(agent, 'mcp_servers', [])),
        }
        
        parameters: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input text or query for the agent"
                },
                "context": {
                    "type": "object",
                    "description": "Optional context object for the agent",
                    "required": False
                }
            },
            "required": ["input"]
        }
        
        return cls(
            name=agent_name,
            description=agent_description,
            parameters=parameters,
            capability_type="agent",
            agent_object=agent,
            agent_config=agent_config,
            **kwargs
        )
    
    @classmethod
    def from_mcp(
        cls,
        mcp_server: Any,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> 'Capability':
        """Create a Capability from an MCP server object."""
        mcp_name = name
        if not mcp_name:
            if hasattr(mcp_server, 'name'):
                if callable(mcp_server.name):
                    mcp_name = mcp_server.name()
                else:
                    mcp_name = mcp_server.name
            else:
                mcp_name = getattr(mcp_server, '__class__', type(mcp_server)).__name__
        
        if description:
            mcp_description = description
        else:
            mcp_description = f"MCP server: {mcp_name}"
            if hasattr(mcp_server, 'description'):
                mcp_description = mcp_server.description
        
        mcp_config = {
            "name": mcp_name,
            "server_type": getattr(mcp_server, '__class__', type(mcp_server)).__name__,
            "use_structured_content": getattr(mcp_server, 'use_structured_content', False),
        }
        
        parameters: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "Name of the MCP tool to call"
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments for the MCP tool",
                    "additionalProperties": True
                }
            },
            "required": ["tool_name"]
        }
        
        return cls(
            name=mcp_name,
            description=mcp_description,
            parameters=parameters,
            capability_type="mcp",
            mcp_server_object=mcp_server,
            mcp_config=mcp_config,
            **kwargs
        )


class BaseCapability(ABC):
    """
    Base class for all capability implementations.
    
    Provides structure for parameter validation and asynchronous execution.
    """

    def __init__(self, capability: Capability):
        self.capability_info = capability

    @abstractmethod
    async def run(self, **kwargs) -> str:
        """Execute the capability asynchronously."""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.capability_info.name!r}, description={self.capability_info.description!r})>"


class CapabilityRetriever(ABC):
    """
    Base class for capability retrieval strategies.
    """
    
    def __init__(self):
        super().__init__()
    
    def retrieve(self, **kwargs) -> List[BaseCapability]:
        """Retrieve capabilities based on criteria."""
        return []

