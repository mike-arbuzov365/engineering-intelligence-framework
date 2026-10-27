"""Model-free operations shared by local interfaces; no MCP dependency."""
from .instance import Instance, ServiceError

__all__ = ["Instance", "ServiceError"]
