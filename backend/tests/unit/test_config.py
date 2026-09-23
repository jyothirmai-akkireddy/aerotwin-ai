"""Unit tests for configuration loading and rate-configurability."""

from app.config import AppSettings, ServerConfig, TelemetryConfig


def test_default_telemetry_rate_is_10_hz():
    """Verify default nominal telemetry rate is 10 Hz."""
    cfg = TelemetryConfig()
    assert cfg.rate_hz == 10
    assert cfg.dt_seconds == 0.1


def test_rate_configurability_override():
    """Verify that telemetry frequency can be adjusted without hardcoding."""
    cfg_50hz = TelemetryConfig(rate_hz=50)
    assert cfg_50hz.rate_hz == 50
    assert cfg_50hz.dt_seconds == 0.02

    cfg_1hz = TelemetryConfig(rate_hz=1)
    assert cfg_1hz.rate_hz == 1
    assert cfg_1hz.dt_seconds == 1.0


def test_cors_origins_list_parsing():
    """Verify that comma-delimited origins string is properly split into list."""
    server_cfg = ServerConfig(
        allowed_origins="http://localhost:3000, https://aerotwin.uav.internal "
    )
    origins = server_cfg.cors_origins
    assert len(origins) == 2
    assert "http://localhost:3000" in origins
    assert "https://aerotwin.uav.internal" in origins


def test_app_settings_composition():
    """Verify AppSettings properly composes sub-configurations."""
    app_cfg = AppSettings(
        environment="testing",
        port=9090,
        telemetry_rate_hz=25,
    )
    assert app_cfg.server.environment == "testing"
    assert app_cfg.server.port == 9090
    assert app_cfg.telemetry.rate_hz == 25
    assert app_cfg.telemetry.dt_seconds == 0.04


def test_port_resolution_when_unset(monkeypatch):
    """Verify PORT unset falls back to default port 8000."""
    monkeypatch.delenv("PORT", raising=False)
    app_cfg = AppSettings()
    assert app_cfg.port == 8000
    assert app_cfg.server.port == 8000


def test_port_resolution_when_empty_string(monkeypatch):
    """Verify empty string PORT (e.g. Vercel deployment) safely falls back to 8000."""
    monkeypatch.setenv("PORT", "")
    app_cfg = AppSettings()
    assert app_cfg.port == 8000
    assert app_cfg.server.port == 8000


def test_port_resolution_when_valid_integer_string(monkeypatch):
    """Verify integer string PORT overrides default port."""
    monkeypatch.setenv("PORT", "8001")
    app_cfg = AppSettings()
    assert app_cfg.port == 8001
    assert app_cfg.server.port == 8001

