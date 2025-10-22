"""
Admin API Backend SDK
Python client for easy integration with Admin API Backend resources.
"""

from .client import AdminAPIClient
from .exceptions import (
    AdminAPIError,
    ConnectionError,
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
    ExecutionError,
)
from .models import (
    APIResource,
    ExecutionResult,
    ChainExecutionResult,
)

__version__ = "1.0.0"
__all__ = [
    "AdminAPIClient",
    "AdminAPIError",
    "ConnectionError",
    "AuthenticationError",
    "ResourceNotFoundError",
    "ValidationError",
    "ExecutionError",
    "APIResource",
    "ExecutionResult",
    "ChainExecutionResult",
]
