"""
PISA Capability System

This package provides a unified system for managing capabilities (functions, agents, and MCP servers).

Core Components:
- Capability: Metadata and configuration for a capability
- CapabilityRegistry: Registry for managing capabilities
- @capability: Decorator to register capabilities
- Capabilities: Helper class for easy access to capabilities

Usage:
    # Import capability decorator and registry
    from pisa.capability import capability, get_global_registry, Capabilities
    
    # Decorate a function capability
    @capability(capability_type="function")
    async def my_tool(url: str) -> str:
        '''My tool description'''
        return "result"
    
    # Access capabilities
    caps = Capabilities()
    tool = caps['my_tool']
    
    # List all capabilities
    registry = get_global_registry()
    print(registry.list_all())
"""

# Core models
from .models import (
    Capability,
    CapabilityType,
    BaseCapability,
    CapabilityRetriever,
    _is_agent,
    _is_mcp_server,
)

# Registry and helpers
from .registry import (
    CapabilityRegistry,
    get_global_registry,
    Capabilities,
    capability,
)

# Public API
__all__ = [
    # Core models
    "Capability",
    "CapabilityType",
    "BaseCapability",
    "CapabilityRetriever",
    
    # Registry
    "CapabilityRegistry",
    "get_global_registry",
    "Capabilities",
    
    # Decorator
    "capability",
    
    # Helper functions (usually not needed directly)
    "_is_agent",
    "_is_mcp_server",
]

__version__ = "2.0.0"

