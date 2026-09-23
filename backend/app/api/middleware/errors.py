"""Centralized exception handlers protecting API clients from sensitive internal leakage."""

import time

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.schemas.common import ErrorResponseDTO
from app.application.common.errors import (
    ApplicationError,
    ServiceUnavailableError,
)
from app.domain.common.errors import (
    AeroTwinDomainError,
    EntityNotFoundError,
    InvariantViolationError,
)
from app.infrastructure.logging.logger import current_request_id, get_logger

logger = get_logger("aerotwin.api.errors")


def register_exception_handlers(app: FastAPI) -> None:
    """Register uniform exception handlers for domain, application, and unexpected errors."""

    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
        req_id = current_request_id.get()
        logger.warning(f"Entity not found: {exc.message}")
        dto = ErrorResponseDTO(
            error_code=exc.code,
            message=exc.message,
            request_id=req_id,
            timestamp=time.time(),
        )
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=dto.model_dump())

    @app.exception_handler(InvariantViolationError)
    @app.exception_handler(AeroTwinDomainError)
    async def domain_error_handler(request: Request, exc: AeroTwinDomainError) -> JSONResponse:
        req_id = current_request_id.get()
        logger.warning(f"Domain error [{exc.code}]: {exc.message}")
        dto = ErrorResponseDTO(
            error_code=exc.code,
            message=exc.message,
            request_id=req_id,
            timestamp=time.time(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=dto.model_dump()
        )

    @app.exception_handler(ServiceUnavailableError)
    async def service_unavailable_handler(
        request: Request, exc: ServiceUnavailableError
    ) -> JSONResponse:
        req_id = current_request_id.get()
        logger.error(f"Service unavailable [{exc.code}]: {exc.message}")
        dto = ErrorResponseDTO(
            error_code=exc.code,
            message=exc.message,
            request_id=req_id,
            timestamp=time.time(),
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=dto.model_dump()
        )

    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
        req_id = current_request_id.get()
        logger.warning(f"Application error [{exc.code}]: {exc.message}")
        dto = ErrorResponseDTO(
            error_code=exc.code,
            message=exc.message,
            request_id=req_id,
            timestamp=time.time(),
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=dto.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        req_id = current_request_id.get()
        logger.warning(f"Request validation failure on {request.url.path}: {exc.errors()}")
        # Sanitize error messages
        sanitized_errors = [
            {
                "loc": " -> ".join(str(loc_item) for loc_item in err.get("loc", [])),
                "msg": err.get("msg", "Invalid field"),
            }
            for err in exc.errors()
        ]
        dto = ErrorResponseDTO(
            error_code="REQUEST_VALIDATION_ERROR",
            message="Incoming request payload failed schema validation",
            request_id=req_id,
            timestamp=time.time(),
            details={"field_errors": sanitized_errors},
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=dto.model_dump()
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        req_id = current_request_id.get()
        dto = ErrorResponseDTO(
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            request_id=req_id,
            timestamp=time.time(),
        )
        return JSONResponse(status_code=exc.status_code, content=dto.model_dump())

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        req_id = current_request_id.get()
        # Log the full exception with stack trace internally for engineering diagnostics
        logger.exception(
            f"Unhandled server exception on {request.method} {request.url.path}: {exc}"
        )
        # Return safe, non-leaking generic response to client
        dto = ErrorResponseDTO(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred. Please contact ground station support with the request ID.",
            request_id=req_id,
            timestamp=time.time(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=dto.model_dump()
        )
