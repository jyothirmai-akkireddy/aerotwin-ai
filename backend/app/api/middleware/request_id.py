"""Request correlation ID middleware for API tracing and telemetry debugging."""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.logging.logger import current_request_id, get_logger

logger = get_logger("aerotwin.api.access")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware attaching a unique correlation ID to every incoming request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract existing correlation ID from headers or generate new UUID4
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = current_request_id.set(request_id)

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # Attach correlation ID and execution time to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"

            # Avoid logging noisy high-frequency websocket pings or static assets
            if not request.url.path.startswith("/static"):
                logger.info(
                    f"{request.method} {request.url.path} -> {response.status_code} ({elapsed_ms:.2f}ms)"
                )
            return response
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception(
                f"Unhandled server exception on {request.method} {request.url.path}: {exc}"
            )
            from starlette.responses import JSONResponse

            from app.api.schemas.common import ErrorResponseDTO

            dto = ErrorResponseDTO(
                error_code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred. Please contact ground station support with the request ID.",
                request_id=request_id,
                timestamp=time.time(),
            )
            err_response = JSONResponse(status_code=500, content=dto.model_dump())
            err_response.headers["X-Request-ID"] = request_id
            err_response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
            return err_response
        finally:
            current_request_id.reset(token)
