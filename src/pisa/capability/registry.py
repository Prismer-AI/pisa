"""
Capability Registry and Decorator

This module provides the capability registry, decorator, and helper classes
for managing capabilities (functions, agents, and MCP servers).
"""

from typing import Any, Callable, Optional, Dict, List, Union, Literal
import functools
import inspect
import asyncio
import importlib
import importlib.util
import os
import logging
from pathlib import Path
from datetime import datetime

from pydantic import BaseModel, Field

from .models import (
    Capability,
    CapabilityType,
    BaseCapability,
    CapabilityRetriever,
    _is_agent,
    _is_mcp_server,
)

_logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """
    Registry for managing and discovering capabilities.
    
    This registry automatically collects capabilities decorated with @capability
    and provides methods to discover, query, and retrieve them.
    """
    
    def __init__(self, auto_register: bool = True):
        """
        Initialize the capability registry.
        
        Args:
            auto_register: If True, capabilities decorated with @capability
                         will be automatically registered
        """
        self._capabilities: Dict[str, Capability] = {}
        self._functions: Dict[str, Callable] = {}
        self.auto_register = auto_register
        _logger.info("CapabilityRegistry initialized")
    
    def register(self, capability_obj: Capability, func: Optional[Callable] = None) -> None:
        """
        Register a capability.
        
        Args:
            capability_obj: The Capability instance to register
            func: Optional function associated with this capability
        """
        name = capability_obj.name
        if name in self._capabilities:
            # Skip if already registered (avoid duplicate warnings during discovery)
            _logger.debug(f"Capability '{name}' already registered, skipping")
            return
        
        self._capabilities[name] = capability_obj
        if func is not None:
            self._functions[name] = func
        
        _logger.debug(f"Registered capability: {name}")
    
    def register_agent(self, agent: Any, name: Optional[str] = None, description: Optional[str] = None) -> Capability:
        """
        Register an Agent object as a capability.
        
        Args:
            agent: The Agent object to register
            name: Optional name override
            description: Optional description override
        
        Returns:
            The created Capability instance
        """
        cap = Capability.from_agent(agent, name=name, description=description)
        self.register(cap, None)  # Agents don't have a simple function wrapper
        _logger.info(f"Registered agent capability: {cap.name}")
        return cap
    
    def register_mcp(self, mcp_server: Any, name: Optional[str] = None, description: Optional[str] = None) -> Capability:
        """
        Register an MCP server object as a capability.
        
        Args:
            mcp_server: The MCP server object to register
            name: Optional name override
            description: Optional description override
        
        Returns:
            The created Capability instance
        """
        cap = Capability.from_mcp(mcp_server, name=name, description=description)
        self.register(cap, None)  # MCP servers don't have a simple function wrapper
        _logger.info(f"Registered MCP capability: {cap.name}")
        return cap
    
    def get(self, name: str) -> Optional[Capability]:
        """Get a capability by name."""
        return self._capabilities.get(name)
    
    def get_function(self, name: str) -> Optional[Callable]:
        """Get the function associated with a capability."""
        return self._functions.get(name)
    
    def list_all(self) -> List[str]:
        """List all registered capability names."""
        return list(self._capabilities.keys())
    
    def get_all(self) -> Dict[str, Capability]:
        """Get all registered capabilities."""
        return self._capabilities.copy()
    
    def search(self, query: str) -> List[Capability]:
        """
        Search capabilities by name or description.
        
        Args:
            query: Search query string
        
        Returns:
            List of matching capabilities
        """
        query_lower = query.lower()
        results = []
        for cap in self._capabilities.values():
            if (query_lower in cap.name.lower() or 
                query_lower in cap.description.lower()):
                results.append(cap)
        return results
    
    def clear(self) -> None:
        """Clear all registered capabilities."""
        count = len(self._capabilities)
        self._capabilities.clear()
        self._functions.clear()
        _logger.info(f"Cleared {count} capabilities")
    
    def discover_from_module(self, module_path: str) -> List[str]:
        """
        Discover and register capabilities from a module.
        
        This will import the module and register all functions decorated
        with @capability.
        
        Args:
            module_path: Python module path (e.g., 'pisa.capability.local.functions')
        
        Returns:
            List of discovered capability names
        """
        try:
            module = importlib.import_module(module_path)
            discovered = []
            
            # Iterate through all attributes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                # Check if it's a function with a capability attribute
                if callable(attr) and hasattr(attr, 'capability'):
                    cap = attr.capability
                    self.register(cap, attr)
                    discovered.append(cap.name)
                    _logger.debug(f"Discovered capability '{cap.name}' from {module_path}")
            
            return discovered
        except Exception as e:
            _logger.error(f"Failed to discover capabilities from {module_path}: {e}")
            return []
    
    def discover_from_directory(
        self, 
        directory: Union[str, Path],
        pattern: str = "*.py",
        recursive: bool = True
    ) -> List[str]:
        """
        Discover capabilities from all Python files in a directory.
        
        Args:
            directory: Directory path to scan
            pattern: File pattern to match (default: "*.py")
            recursive: Whether to scan subdirectories recursively
        
        Returns:
            List of discovered capability names
        """
        directory = Path(directory)
        if not directory.exists():
            _logger.warning(f"Directory does not exist: {directory}")
            return []
        
        discovered = []
        
        for file_path in directory.rglob(pattern) if recursive else directory.glob(pattern):
            if file_path.is_file() and file_path.suffix == '.py':
                # Skip __init__.py files to avoid import errors and duplicate registration
                if file_path.name == '__init__.py':
                    _logger.debug(f"Skipping __init__.py: {file_path}")
                    continue
                
                try:
                    # Convert file path to module path
                    relative_path = file_path.relative_to(directory)
                    module_name = str(relative_path.with_suffix('')).replace(os.sep, '.')
                    
                    # Try to import as a module
                    spec = importlib.util.spec_from_file_location(
                        module_name, 
                        file_path
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # Discover capabilities in this module
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            # Check if it has a 'capability' attribute (FunctionTool, Agent, MCP, or decorated function)
                            if hasattr(attr, 'capability'):
                                cap = attr.capability
                                # Verify it's a Capability object
                                if isinstance(cap, Capability):
                                    self.register(cap, attr)
                                    discovered.append(cap.name)
                                    _logger.debug(f"Discovered capability '{cap.name}' from {file_path}")
                
                except Exception as e:
                    _logger.warning(f"Failed to process {file_path}: {e}")
        
        return discovered


# Global registry instance
_global_registry: Optional[CapabilityRegistry] = None


def get_global_registry() -> CapabilityRegistry:
    """
    Get or create the global capability registry.
    
    Returns:
        The global CapabilityRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = CapabilityRegistry()
    return _global_registry


class Capabilities:
    """
    Helper class to access capabilities by key and get objects directly.
    
    This provides a convenient interface to access capabilities from the registry
    and get the native objects (functions, agents, MCP servers) directly.
    
    Example:
        caps = Capabilities()
        
        # Get a function
        func = caps['fetch_webpage']
        
        # Get an agent
        agent = caps['joke_agent']
        
        # Get an MCP server
        mcp = caps['simple_mcp_server']
        
        # Get all functions for tools
        tools = caps.get_functions()
        
        # Get all agents for handoffs
        agents = caps.get_agents()
        
        # Get all MCP servers
        mcp_servers = caps.get_mcp_servers()
    """
    
    def __init__(self, registry: Optional[CapabilityRegistry] = None):
        """
        Initialize Capabilities helper.
        
        Args:
            registry: Optional registry to use (defaults to global registry)
        """
        self._registry = registry or get_global_registry()
    
    def __getitem__(self, key: str) -> Any:
        """
        Get a capability object by name.
        
        Args:
            key: Capability name
            
        Returns:
            The native object (function, agent, or MCP server)
        """
        cap = self._registry.get(key)
        if cap is None:
            raise KeyError(f"Capability '{key}' not found")
        return cap.get_object(registry=self._registry)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a capability object by name with default.
        
        Args:
            key: Capability name
            default: Default value if not found
            
        Returns:
            The native object or default
        """
        cap = self._registry.get(key)
        if cap is None:
            return default
        return cap.get_object(registry=self._registry)
    
    def get_capability(self, key: str) -> Optional[Capability]:
        """Get the Capability object by name."""
        return self._registry.get(key)
    
    def get_functions(self) -> List[Any]:
        """
        Get all function capabilities as a list of FunctionTool objects.
        
        Returns:
            List of FunctionTool objects (from @function_tool decorator) or functions
        """
        functions = []
        for name, cap in self._registry.get_all().items():
            if cap.capability_type == "function":
                func = cap.get_object(registry=self._registry)
                if func:
                    # Check if it's already a FunctionTool
                    is_function_tool = (
                        hasattr(func, 'name') and
                        hasattr(func, 'description') and
                        hasattr(func, 'params_json_schema') and
                        hasattr(func, 'on_invoke_tool')
                    )
                    if is_function_tool:
                        functions.append(func)
                    else:
                        _logger.warning(
                            f"Function capability '{name}' is not a FunctionTool. "
                            f"Make sure it's decorated with @function_tool."
                        )
        return functions
    
    def get_agents(self) -> List[Any]:
        """Get all agent capabilities as a list of Agent objects."""
        agents = []
        for name, cap in self._registry.get_all().items():
            if cap.capability_type == "agent":
                agent = cap.get_object(registry=self._registry)
                if agent:
                    agents.append(agent)
        return agents
    
    def get_mcp_servers(self) -> List[Any]:
        """Get all MCP capabilities as a list of MCP server objects."""
        servers = []
        for name, cap in self._registry.get_all().items():
            if cap.capability_type == "mcp":
                server = cap.get_object(registry=self._registry)
                if server:
                    servers.append(server)
        return servers
    
    def list_all(self) -> List[str]:
        """List all capability names."""
        return self._registry.list_all()
    
    def __iter__(self):
        """Iterate over capability names."""
        return iter(self._registry.list_all())
    
    def __len__(self) -> int:
        """Get the number of capabilities."""
        return len(self._registry.list_all())


def capability(
    capability_type: CapabilityType,
    name: Optional[str] = None,
    description: Optional[str] = None,
    registry: Optional[CapabilityRegistry] = None,
    auto_register: bool = True,
    **kwargs
) -> Union[Callable, Any]:
    """
    Decorator to automatically create and register a Capability.
    
    This decorator requires capability_type to be specified, which determines
    the processing strategy:
    
    1. For functions (capability_type="function"):
       @capability(capability_type="function")
       @function_tool
       async def my_function(url: str) -> str:
           \"\"\"Crawl a URL.\"\"\"
           return "content"
    
    2. For agents (capability_type="agent"):
       @capability(capability_type="agent")
       def create_agent():
           return Agent(name="MyAgent", instructions="...")
    
    3. For MCP servers (capability_type="mcp"):
       @capability(capability_type="mcp")
       def create_mcp():
           return MCPServerStdio(...)
    
    For functions, it automatically extracts:
    - Function name
    - Function description (from docstring)
    - Parameter types and schema
    - Return type
    
    Args:
        capability_type: Type of capability - REQUIRED ("function", "agent", or "mcp")
        name: Optional name override
        description: Optional description override
        registry: Optional registry to register with (defaults to global registry)
        auto_register: Whether to automatically register the capability (default: True)
        **kwargs: Additional parameters to pass to Capability constructor
    
    Returns:
        - For functions: Decorated function with capability attribute
        - For Agent/MCP: The same object with capability attribute attached
    
    Examples:
        # Function decorator
        @capability(capability_type="function")
        @function_tool
        async def my_function(url: str) -> str:
            \"\"\"Crawl a URL.\"\"\"
            return "content"
        
        # Agent factory function
        @capability(capability_type="agent", name="my_agent")
        def create_agent():
            return Agent(name="MyAgent", instructions="...")
        
        # MCP factory function
        @capability(capability_type="mcp", name="my_mcp")
        def create_mcp():
            return MCPServerStdio(...)
    """
    from typing import get_type_hints
    
    def decorator_or_register(obj: Any) -> Any:
        # Process based on capability_type
        if capability_type == "agent":
            # For agent type, check if it's an Agent or a factory function
            if _is_agent(obj):
                # Direct Agent object
                cap = Capability.from_agent(obj, name=name, description=description, **kwargs)
                if auto_register:
                    reg = registry or get_global_registry()
                    if reg.auto_register:
                        reg.register(cap, None)
                        _logger.debug(f"Auto-registered agent capability: {cap.name}")
                obj.capability = cap
                return obj
            elif callable(obj):
                # Factory function that returns Agent
                func = obj
                is_async = inspect.iscoroutinefunction(func)
                
                # Create wrapper
                if is_async:
                    @functools.wraps(func)
                    async def wrapper(*args, **kwargs):
                        result = await func(*args, **kwargs)
                        if _is_agent(result):
                            cap = Capability.from_agent(result, name=name, description=description, **kwargs)
                            if auto_register:
                                reg = registry or get_global_registry()
                                if reg.auto_register:
                                    reg.register(cap, None)
                            result.capability = cap
                        return result
                else:
                    @functools.wraps(func)
                    def wrapper(*args, **kwargs):
                        result = func(*args, **kwargs)
                        if _is_agent(result):
                            cap = Capability.from_agent(result, name=name, description=description, **kwargs)
                            if auto_register:
                                reg = registry or get_global_registry()
                                if reg.auto_register:
                                    reg.register(cap, None)
                            result.capability = cap
                        return result
                
                # Auto-call if no required parameters
                sig = inspect.signature(func)
                has_required = any(p.default == inspect.Parameter.empty for p in sig.parameters.values())
                if not has_required and not is_async:
                    try:
                        result = func()
                        if _is_agent(result):
                            cap = Capability.from_agent(result, name=name, description=description, **kwargs)
                            if auto_register:
                                reg = registry or get_global_registry()
                                if reg.auto_register:
                                    reg.register(cap, None)
                            result.capability = cap
                            return result
                    except Exception as e:
                        _logger.debug(f"Could not auto-call agent factory: {e}")
                
                return wrapper
            else:
                raise TypeError(f"Object {obj} is not an Agent or factory function for capability_type='agent'")
        
        elif capability_type == "mcp":
            # For mcp type, check if it's an MCP server or a factory function
            if _is_mcp_server(obj):
                # Direct MCP server object
                cap = Capability.from_mcp(obj, name=name, description=description, **kwargs)
                if auto_register:
                    reg = registry or get_global_registry()
                    if reg.auto_register:
                        reg.register(cap, None)
                        _logger.debug(f"Auto-registered MCP capability: {cap.name}")
                obj.capability = cap
                return obj
            elif callable(obj):
                # Factory function that returns MCP server
                func = obj
                is_async = inspect.iscoroutinefunction(func)
                
                # Create wrapper
                if is_async:
                    @functools.wraps(func)
                    async def wrapper(*args, **kwargs):
                        result = await func(*args, **kwargs)
                        if _is_mcp_server(result):
                            cap = Capability.from_mcp(result, name=name, description=description, **kwargs)
                            if auto_register:
                                reg = registry or get_global_registry()
                                if reg.auto_register:
                                    reg.register(cap, None)
                            result.capability = cap
                        return result
                else:
                    @functools.wraps(func)
                    def wrapper(*args, **kwargs):
                        result = func(*args, **kwargs)
                        if _is_mcp_server(result):
                            cap = Capability.from_mcp(result, name=name, description=description, **kwargs)
                            if auto_register:
                                reg = registry or get_global_registry()
                                if reg.auto_register:
                                    reg.register(cap, None)
                            result.capability = cap
                        return result
                
                # Auto-call if no required parameters
                sig = inspect.signature(func)
                has_required = any(p.default == inspect.Parameter.empty for p in sig.parameters.values())
                if not has_required and not is_async:
                    try:
                        result = func()
                        if _is_mcp_server(result):
                            cap = Capability.from_mcp(result, name=name, description=description, **kwargs)
                            if auto_register:
                                reg = registry or get_global_registry()
                                if reg.auto_register:
                                    reg.register(cap, None)
                            result.capability = cap
                            return result
                    except Exception as e:
                        _logger.debug(f"Could not auto-call MCP factory: {e}")
                
                return wrapper
            else:
                raise TypeError(f"Object {obj} is not an MCP server or factory function for capability_type='mcp'")
        
        elif capability_type == "function":
            # Check if it's already a FunctionTool object (from @function_tool decorator)
            is_function_tool = (
                hasattr(obj, 'name') and
                hasattr(obj, 'description') and
                hasattr(obj, 'params_json_schema') and
                hasattr(obj, 'on_invoke_tool')
            )
            
            if is_function_tool:
                # It's already a FunctionTool, extract information from it
                func_tool = obj
                
                # Create Capability from FunctionTool
                cap = Capability(
                    name=name or func_tool.name,
                    description=description or func_tool.description,
                    parameters=func_tool.params_json_schema,
                    capability_type="function",
                    **kwargs
                )
                
                # Attach capability to FunctionTool
                func_tool.capability = cap
                
                # Auto-register if enabled
                if auto_register:
                    reg = registry or get_global_registry()
                    if reg.auto_register:
                        reg.register(cap, func_tool)
                        _logger.debug(f"Auto-registered capability from FunctionTool: {cap.name}")
                
                return func_tool
            
            # Check if it's a class with a 'run' method
            is_class = (
                inspect.isclass(obj) and 
                obj is not type and
                not (hasattr(obj, 'name') and hasattr(obj, 'on_invoke_tool'))
            )
            
            if is_class:
                if not hasattr(obj, 'run') or not callable(getattr(obj, 'run')):
                    raise TypeError(
                        f"Class {obj.__name__} does not have a 'run' method. "
                        f"Classes decorated with @capability(capability_type='function') must have a 'run' method."
                    )
                
                # Get the run method and create wrapper
                run_method = getattr(obj, 'run')
                run_sig = inspect.signature(run_method)
                params = [p for p in run_sig.parameters.values() if p.name != 'self']
                new_sig = run_sig.replace(parameters=params)
                
                # Get type hints
                try:
                    run_type_hints = get_type_hints(run_method, include_extras=True)
                except (TypeError, NameError):
                    run_type_hints = getattr(run_method, '__annotations__', {})
                
                if 'self' in run_type_hints:
                    run_type_hints = {k: v for k, v in run_type_hints.items() if k != 'self'}
                
                # Create wrapper function
                if inspect.iscoroutinefunction(run_method):
                    async def _async_wrapper(*args, **kwargs):
                        instance = obj()
                        return await run_method(instance, *args, **kwargs)
                    class_wrapper = _async_wrapper
                else:
                    def _sync_wrapper(*args, **kwargs):
                        instance = obj()
                        return run_method(instance, *args, **kwargs)
                    class_wrapper = _sync_wrapper
                
                class_wrapper.__signature__ = new_sig
                class_wrapper.__doc__ = run_method.__doc__ or f"Run method from {obj.__name__} class"
                class_wrapper.__annotations__ = run_type_hints.copy()
                class_wrapper.__name__ = run_method.__name__ or f"{obj.__name__}_run"
                class_wrapper.__qualname__ = f"{obj.__name__}.{run_method.__name__}"
                
                func = class_wrapper
            elif not callable(obj):
                raise TypeError(
                    f"Object {obj} is not a callable function, class, or FunctionTool for capability_type='function'."
                )
            else:
                func = obj
            
            # Automatically apply @function_tool decorator
            try:
                from agents import function_tool
                
                function_tool_kwargs = {}
                for key in ['name_override', 'description_override', 'docstring_style', 
                           'use_docstring_info', 'failure_error_function', 'strict_mode', 'is_enabled']:
                    if key in kwargs:
                        function_tool_kwargs[key] = kwargs.pop(key)
                
                # Check for **kwargs parameter or complex type hints
                func_sig = inspect.signature(func)
                has_kwargs = any(
                    p.kind == inspect.Parameter.VAR_KEYWORD 
                    for p in func_sig.parameters.values()
                )
                
                # Force strict_mode=False for all capabilities to avoid schema issues
                # with Dict, List, and other complex type hints
                if 'strict_mode' not in function_tool_kwargs:
                    function_tool_kwargs['strict_mode'] = False
                
                if name and 'name_override' not in function_tool_kwargs:
                    function_tool_kwargs['name_override'] = name
                
                if description and 'description_override' not in function_tool_kwargs:
                    function_tool_kwargs['description_override'] = description
                
                if function_tool_kwargs:
                    func_tool = function_tool(**function_tool_kwargs)(func)
                else:
                    func_tool = function_tool(func)
                
                _logger.debug(f"Automatically applied @function_tool to function: {func_tool.name}")
                
            except ImportError:
                _logger.warning(
                    "agents library not available. @capability(capability_type='function') "
                    "requires @function_tool decorator. Please install 'agents' package or use @function_tool."
                )
                func_tool = None
            
            # Create Capability
            if func_tool:
                cap = Capability(
                    name=name or func_tool.name,
                    description=description or func_tool.description,
                    parameters=func_tool.params_json_schema,
                    capability_type="function",
                    **kwargs
                )
                
                func_tool.capability = cap
                
                if auto_register:
                    reg = registry or get_global_registry()
                    if reg.auto_register:
                        reg.register(cap, func_tool)
                        _logger.debug(f"Auto-registered capability from FunctionTool: {cap.name}")
                
                return func_tool
            else:
                cap = Capability.from_function(
                    func=func,
                    name=name,
                    description=description,
                    capability_type="function",
                    **kwargs
                )
                
                func.capability = cap
                
                if auto_register:
                    reg = registry or get_global_registry()
                    if reg.auto_register:
                        reg.register(cap, func)
                        _logger.debug(f"Auto-registered capability: {cap.name}")
                
                return func
        
        else:
            raise ValueError(f"Invalid capability_type: {capability_type}. Must be 'function', 'agent', or 'mcp'")
    
    return decorator_or_register

