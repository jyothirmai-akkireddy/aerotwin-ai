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


def test_local_default_storage_root_resolves_to_data(monkeypatch):
    """Verify local/default environment still resolves runtime storage root to data/."""
    from pathlib import Path

    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    monkeypatch.delenv("LAMBDA_TASK_ROOT", raising=False)
    monkeypatch.delenv("AEROTWIN_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("STORAGE_ROOT", raising=False)

    app_cfg = AppSettings(environment="development")
    assert app_cfg.storage.base_dir == "data"
    assert app_cfg.storage.sqlite_db_path == "data/aerotwin.db"
    assert app_cfg.storage.parquet_data_dir == "data/telemetry_parquet"
    assert app_cfg.storage.missions_dir == Path("data/missions")
    assert app_cfg.storage.sqlite_dir == Path("data/sqlite")


def test_serverless_vercel_environment_resolves_to_tmp(monkeypatch):
    """Verify Vercel/serverless environment resolves runtime writable storage root to /tmp/aerotwin."""
    from pathlib import Path

    monkeypatch.setenv("VERCEL", "1")
    app_cfg = AppSettings()
    assert app_cfg.storage.base_dir == "/tmp/aerotwin"
    assert app_cfg.storage.sqlite_db_path == "/tmp/aerotwin/aerotwin.db"
    assert app_cfg.storage.parquet_data_dir == "/tmp/aerotwin/telemetry_parquet"
    assert app_cfg.storage.missions_dir == Path("/tmp/aerotwin/missions")
    assert app_cfg.storage.sqlite_dir == Path("/tmp/aerotwin/sqlite")


def test_production_environment_resolves_to_tmp(monkeypatch):
    """Verify production environment resolves runtime writable storage root to /tmp/aerotwin."""
    monkeypatch.delenv("VERCEL", raising=False)
    app_cfg = AppSettings(environment="production")
    assert app_cfg.storage.base_dir == "/tmp/aerotwin"
    assert app_cfg.storage.sqlite_db_path == "/tmp/aerotwin/aerotwin.db"
    assert app_cfg.storage.parquet_data_dir == "/tmp/aerotwin/telemetry_parquet"


def test_mission_service_initialization_in_serverless(monkeypatch):
    """Verify MissionService initializes without attempting to mkdir under package data directory."""
    from pathlib import Path
    from app.application.services.mission_service import MissionService
    from app.config import settings

    prev_base = settings.storage.base_dir
    prev_parquet = settings.storage.parquet_data_dir
    settings.storage.base_dir = "/tmp/aerotwin"
    settings.storage.parquet_data_dir = "/tmp/aerotwin/telemetry_parquet"

    try:
        service = MissionService()
        assert service.storage_dir == Path("/tmp/aerotwin/missions")
        missions = service.list_predefined_missions()
        assert len(missions) > 0
    finally:
        settings.storage.base_dir = prev_base
        settings.storage.parquet_data_dir = prev_parquet


def test_replay_service_initialization_in_serverless(monkeypatch):
    """Verify ReplayService initializes without attempting to mkdir under package data directory."""
    from pathlib import Path
    from app.application.services.replay_service import ReplayService
    from app.config import settings

    prev_base = settings.storage.base_dir
    prev_parquet = settings.storage.parquet_data_dir
    settings.storage.base_dir = "/tmp/aerotwin"
    settings.storage.parquet_data_dir = "/tmp/aerotwin/telemetry_parquet"

    try:
        service = ReplayService()
        for d in service.search_dirs:
            assert str(d).startswith(str(Path("/tmp/aerotwin")))
        datasets = service.list_available_datasets()
        assert isinstance(datasets, list)
    finally:
        settings.storage.base_dir = prev_base
        settings.storage.parquet_data_dir = prev_parquet


def test_static_model_and_config_paths_remain_unchanged():
    """Verify bundled static model and asset paths are NOT moved to /tmp and stay in package paths."""
    from app.config import settings

    assert settings.diagnostics.anomaly_detector_path == "models/anomaly_detector.joblib"
    assert settings.diagnostics.fault_classifier_path == "models/fault_classifier.joblib"
    assert not settings.diagnostics.anomaly_detector_path.startswith("/tmp")
    assert not settings.diagnostics.fault_classifier_path.startswith("/tmp")


def test_existing_local_behavior_remains_unchanged(monkeypatch):
    """Verify existing local behavior remains unchanged for MissionService and ReplayService."""
    from pathlib import Path
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    from app.application.services.mission_service import MissionService
    from app.application.services.replay_service import ReplayService
    from app.config import settings

    prev_base = settings.storage.base_dir
    prev_parquet = settings.storage.parquet_data_dir
    settings.storage.base_dir = "data"
    settings.storage.parquet_data_dir = "data/telemetry_parquet"

    try:
        m_service = MissionService()
        assert m_service.storage_dir == Path("data/missions")
        r_service = ReplayService()
        assert Path("data/missions") in r_service.search_dirs
        assert Path("data/telemetry_parquet") in r_service.search_dirs
    finally:
        settings.storage.base_dir = prev_base
        settings.storage.parquet_data_dir = prev_parquet


