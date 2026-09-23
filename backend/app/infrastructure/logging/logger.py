"""Structured logging foundation supporting correlation IDs and safe telemetry logging."""

import contextvars
import logging
import sys

# Context variable tracking correlation request IDs across asynchronous tasks
current_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_request_id", default=None
)


class CorrelationIdFormatter(logging.Formatter):
    """Log formatter injecting current request correlation ID into log records."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = current_request_id.get()
        record.request_id = f"[{req_id}] " if req_id else ""
        return super().format(record)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure root logger with correlation ID formatting and clean console output."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers if setup is called multiple times
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = CorrelationIdFormatter(
            fmt="%(asctime)s [%(levelname)s] %(request_id)s%(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger instance."""
    return logging.getLogger(name)
