"""Application configuration managed via Pydantic Settings with explicit categories."""

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def is_serverless_environment() -> bool:
    """Detect whether running inside Vercel, AWS Lambda, or a serverless container."""
    return bool(
        os.environ.get("VERCEL")
        or os.environ.get("VERCEL_ENV")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("LAMBDA_TASK_ROOT")
    )


def resolve_storage_root(
    environment: str = "development",
    custom_root: str | Path | None = None,
) -> Path:
    """Resolve the writable runtime storage root directory based on environment.

    - Explicit custom root via argument or env (AEROTWIN_STORAGE_ROOT / STORAGE_ROOT) takes precedence.
    - Serverless runtimes (Vercel / Lambda) or production environment use /tmp/aerotwin.
    - Default local development uses data/.
    """
    if custom_root:
        return Path(custom_root)
    env_override = os.environ.get("AEROTWIN_STORAGE_ROOT") or os.environ.get("STORAGE_ROOT")
    if env_override:
        return Path(env_override)
    if is_serverless_environment() or environment.lower() == "production":
        return Path("/tmp/aerotwin")
    return Path("data")


class ServerConfig(BaseModel):
    """Network and web transport configuration."""

    environment: str = Field(
        default="development", description="development | testing | production"
    )
    host: str = Field(default="0.0.0.0", description="API server bind host")
    port: int = Field(default=8000, description="API server bind port")
    log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated CORS origins",
    )

    @field_validator("port", mode="before")
    @classmethod
    def assemble_port(cls, v: Any) -> int:
        if v is None or v == "" or (isinstance(v, str) and not v.strip()):
            return 8000
        return int(v)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


class TelemetryConfig(BaseModel):
    """Telemetry ingestion and streaming configuration (Rate-Configurable)."""

    rate_hz: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Nominal telemetry streaming and processing frequency (Hz). Configurable.",
    )
    buffer_capacity: int = Field(default=1000, description="In-memory frame buffer capacity")
    strict_validation: bool = Field(default=True, description="Strict aerospace bound rejection")

    @property
    def dt_seconds(self) -> float:
        return 1.0 / self.rate_hz


class StorageConfig(BaseModel):
    """Persistence and flight logging configuration."""

    base_dir: str = Field(
        default_factory=lambda: resolve_storage_root().as_posix(),
        description="Root directory for runtime writable data (e.g. data or /tmp/aerotwin)",
    )
    sqlite_db_path: str = Field(
        default="",
        description="Path to SQLite database",
    )
    parquet_data_dir: str = Field(
        default="",
        description="Directory for Parquet flight dumps",
    )

    def model_post_init(self, __context: Any) -> None:
        """Initialize derived storage paths if not explicitly provided."""
        root = Path(self.base_dir)
        if not self.sqlite_db_path:
            self.sqlite_db_path = (root / "aerotwin.db").as_posix()
        if not self.parquet_data_dir:
            self.parquet_data_dir = (root / "telemetry_parquet").as_posix()

    @property
    def missions_dir(self) -> Path:
        return Path(self.base_dir) / "missions"

    @property
    def sqlite_dir(self) -> Path:
        return Path(self.base_dir) / "sqlite"

    @property
    def parquet_dir(self) -> Path:
        return Path(self.parquet_data_dir)


class DiagnosticsConfig(BaseModel):
    """Machine learning and explainability parameters."""

    anomaly_detector_path: str = Field(default="models/anomaly_detector.joblib")
    fault_classifier_path: str = Field(default="models/fault_classifier.joblib")
    shap_background_samples: int = Field(default=100)
    shap_inference_interval_sec: float = Field(default=1.0)


class SimulationConfig(BaseModel):
    """Physics simulation baseline configuration."""

    engine_model: str = Field(
        default="GENERIC_4CYL_BOXER_TURBO_PROTOTYPE",
        description="Generic 4-cyl opposed aero-piston twin inspired by Rotax 914/915 class",
    )
    default_mission_profile: str = Field(default="STANDARD_SURVEILLANCE")


class WebSocketConfig(BaseModel):
    """Realtime WebSocket streaming and backpressure configuration."""

    enabled: bool = Field(default=True, description="Enable WebSocket realtime telemetry stream")
    max_clients: int = Field(
        default=50, ge=1, le=500, description="Maximum concurrent WebSocket clients"
    )
    max_message_size: int = Field(
        default=65536,
        ge=1024,
        le=1048576,
        description="Maximum inbound payload size in bytes (64 KB)",
    )
    queue_size: int = Field(
        default=100, ge=10, le=1000, description="Per-client bounded queue capacity"
    )
    telemetry_stale_after_ms: int = Field(
        default=1500, ge=100, description="Threshold after which telemetry is considered stale"
    )
    heartbeat_interval_sec: float = Field(
        default=5.0, ge=1.0, description="Periodic heartbeat emission interval (seconds)"
    )


class AppSettings(BaseSettings):
    """Root application configuration composed of categorized sub-configurations."""

    app_name: str = "AeroTwin AI Ground Station API"
    app_version: str = "0.1.0"
    app_description: str = (
        "MALE UAV Aero-Piston Engine Digital Twin & Health Monitoring Foundation (SIH26054)"
    )

    # Categories
    server: ServerConfig = Field(default_factory=ServerConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    diagnostics: DiagnosticsConfig = Field(default_factory=DiagnosticsConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)

    # Top-level environment variable overrides for flat .env files
    environment: str = "development"
    port: int = 8000
    telemetry_rate_hz: int = 10

    @field_validator("port", mode="before")
    @classmethod
    def assemble_port(cls, v: Any) -> int:
        if v is None or v == "" or (isinstance(v, str) and not v.strip()):
            return 8000
        return int(v)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context: object) -> None:
        """Propagate flat environment overrides to categorized sub-configs."""
        if self.environment != "development":
            self.server.environment = self.environment
        if self.port != 8000:
            self.server.port = self.port
        if self.telemetry_rate_hz != 10:
            self.telemetry.rate_hz = self.telemetry_rate_hz

        # Propagate environment or serverless status to storage configuration
        resolved_root = resolve_storage_root(environment=self.environment).as_posix()
        if self.storage.base_dir != resolved_root:
            self.storage.base_dir = resolved_root
            self.storage.sqlite_db_path = (Path(resolved_root) / "aerotwin.db").as_posix()
            self.storage.parquet_data_dir = (Path(resolved_root) / "telemetry_parquet").as_posix()


settings = AppSettings()
