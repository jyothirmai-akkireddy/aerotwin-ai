"""Unit tests verifying error handling, status codes, and non-leakage of internal diagnostics."""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.api.middleware.errors import register_exception_handlers
from app.api.middleware.request_id import RequestIdMiddleware
from app.application.common.errors import ServiceUnavailableError
from app.domain.common.errors import EntityNotFoundError, InvariantViolationError


@pytest.fixture
def error_test_app() -> FastAPI:
    """Fixture creating a test app equipped with the error handling middleware and test routes."""
    test_app = FastAPI()
    test_app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(test_app)

    @test_app.get("/trigger-domain-error")
    def trigger_domain_error():
        raise InvariantViolationError("Physical RPM cannot exceed redline")

    @test_app.get("/trigger-not-found")
    def trigger_not_found():
        raise EntityNotFoundError("CylinderSensor", "cyl_5_temp")

    @test_app.get("/trigger-service-error")
    def trigger_service_error():
        raise ServiceUnavailableError("TelemetryIngestionService", "buffer full")

    @test_app.get("/trigger-unexpected")
    def trigger_unexpected():
        # Raise unexpected internal error with potential sensitive string
        raise ZeroDivisionError("C:/Secret/Path/divide by zero in internal algorithm")

    return test_app


def test_entity_not_found_response(error_test_app: FastAPI):
    client = TestClient(error_test_app)
    response = client.get("/trigger-not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["error_code"] == "ENTITY_NOT_FOUND"
    assert "not found" in data["message"]
    assert "x-request-id" in response.headers


def test_domain_invariant_error_response(error_test_app: FastAPI):
    client = TestClient(error_test_app)
    response = client.get("/trigger-domain-error")
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"
    assert data["error_code"] == "INVARIANT_VIOLATION"
    assert "Physical RPM" in data["message"]


def test_service_unavailable_response(error_test_app: FastAPI):
    client = TestClient(error_test_app)
    response = client.get("/trigger-service-error")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["error_code"] == "SERVICE_UNAVAILABLE"


def test_unexpected_error_masks_internal_stack_and_paths(error_test_app: FastAPI):
    """Verify that unhandled exceptions do NOT leak file paths, line numbers, or internal variables."""
    client = TestClient(error_test_app, raise_server_exceptions=False)
    response = client.get("/trigger-unexpected")
    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"
    assert data["error_code"] == "INTERNAL_SERVER_ERROR"
    # Ensure sensitive internal paths or raw Python exception message is NOT exposed to client
    assert "C:/Secret/Path" not in data["message"]
    assert "ZeroDivisionError" not in data["message"]
    assert "contact ground station support" in data["message"]
    assert "x-request-id" in response.headers
