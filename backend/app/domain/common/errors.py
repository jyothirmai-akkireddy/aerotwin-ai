"""Domain layer core exceptions.

These exceptions represent business invariant violations and domain logic errors.
They are completely decoupled from any presentation or web framework.
"""


class AeroTwinDomainError(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class InvariantViolationError(AeroTwinDomainError):
    """Raised when an internal business invariant or physical constraint is violated."""

    def __init__(self, message: str):
        super().__init__(message, code="INVARIANT_VIOLATION")


class EntityNotFoundError(AeroTwinDomainError):
    """Raised when a requested domain entity cannot be located."""

    def __init__(self, entity_name: str, identifier: str):
        super().__init__(
            f"{entity_name} with identifier '{identifier}' was not found.", code="ENTITY_NOT_FOUND"
        )
        self.entity_name = entity_name
        self.identifier = identifier


class InvalidStateTransitionError(AeroTwinDomainError):
    """Raised when an entity attempts an illegal state transition."""

    def __init__(self, current_state: str, attempted_state: str, reason: str = ""):
        msg = f"Cannot transition from state '{current_state}' to '{attempted_state}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg, code="INVALID_STATE_TRANSITION")
        self.current_state = current_state
        self.attempted_state = attempted_state
