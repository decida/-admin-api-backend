"""
Exception classes for Admin API SDK
"""


class AdminAPIError(Exception):
    """Base exception for all Admin API errors"""

    def __init__(self, message: str, status_code: int | None = None, details: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ConnectionError(AdminAPIError):
    """Raised when connection to API fails"""
    pass


class AuthenticationError(AdminAPIError):
    """Raised when authentication fails"""
    pass


class ResourceNotFoundError(AdminAPIError):
    """Raised when requested resource is not found"""
    pass


class ValidationError(AdminAPIError):
    """Raised when request validation fails"""
    pass


class ExecutionError(AdminAPIError):
    """Raised when API resource execution fails"""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict | None = None,
        step: int | None = None,
        business_object_name: str | None = None
    ):
        super().__init__(message, status_code, details)
        self.step = step
        self.business_object_name = business_object_name
