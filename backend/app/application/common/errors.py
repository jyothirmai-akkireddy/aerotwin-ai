"""Application-level exceptions representing service failures and orchestration errors."""


class ApplicationError(Exception):
    """Base exception for application service errors."""

    def __init__(self, message: str, code: str = "APPLICATION_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class ServiceUnavailableError(ApplicationError):
    """Raised when an internal or external dependency service is unavailable."""

    def __init__(self, service_name: str, details: str = ""):
        msg = f"Service '{service_name}' is currently unavailable."
        if details:
            msg += f" Details: {details}"
        super().__init__(msg, code="SERVICE_UNAVAILABLE")
        self.service_name = service_name


class ValidationFailedError(ApplicationError):
    """Raised when application-level validation fails on an incoming command or DTO."""

    def __init__(self, message: str, field_errors: dict[str, str] | None = None):
        super().__init__(message, code="VALIDATION_FAILED")
        self.field_errors = field_errors or {}


class ConfigurationError(ApplicationError):
    """Raised when application detects inconsistent or missing configuration."""

    def __init__(self, message: str):
        super().__init__(message, code="CONFIGURATION_ERROR")
