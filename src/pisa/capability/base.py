"""
Capability Base Module (Legacy Compatibility)

This module provides backward compatibility by re-exporting from the new module structure.

For new code, please import from:
- pisa.capability.models for core models
- pisa.capability.registry for registry and decorator
- pisa.capability for the public API

Legacy imports from this file are deprecated but will continue to work:
    from pisa.capability.base import Capability, capability, get_global_registry
"""

import warnings

# Re-export core models
from .models import (
    Capability,
    CapabilityType,
    BaseCapability,
    CapabilityRetriever,
    _is_agent,
    _is_mcp_server,
)

# Re-export registry and helpers
from .registry import (
    CapabilityRegistry,
    get_global_registry,
    Capabilities,
    capability,
)

# Warn about deprecated usage
warnings.warn(
    "Importing from pisa.capability.base is deprecated. "
    "Please import from pisa.capability instead:\n"
    "  from pisa.capability import Capability, capability, get_global_registry\n",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "Capability",
    "CapabilityType",
    "BaseCapability",
    "CapabilityRetriever",
    "CapabilityRegistry",
    "get_global_registry",
    "Capabilities",
    "capability",
    "_is_agent",
    "_is_mcp_server",
]
