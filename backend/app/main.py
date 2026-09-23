"""AeroTwin AI Backend Application Composition Root."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.errors import register_exception_handlers
from app.api.middleware.request_id import RequestIdMiddleware
from app.api.routes.health import router as health_router
from app.api.routes.mission import router as mission_router
from app.api.routes.ml import router as ml_router
from app.api.routes.physics import router as physics_router
from app.api.routes.prognostics import router as prognostics_router
from app.api.routes.replay import router as replay_router
from app.api.routes.simulation import router as simulation_router
from app.api.routes.websocket import router as websocket_router
from app.config import settings
from app.infrastructure.logging.logger import get_logger, setup_logging

logger = get_logger("aerotwin.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and clean resource shutdown."""
    logger.info("AeroTwin AI application initialized.")
    yield
    logger.info("AeroTwin AI application shutting down. Cleaning up background tasks...")
    try:
        from app.api.dependencies import get_realtime_service

        realtime_service = get_realtime_service()
        if realtime_service.state in ("running", "paused"):
            await realtime_service.stop()
    except Exception as e:
        logger.error(f"Error during realtime service shutdown: {e}")


def create_app() -> FastAPI:
    """Application factory configuring middleware, exception handlers, and API routers."""
    # 1. Initialize logging
    setup_logging(settings.server.log_level)
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version} [{settings.server.environment}]"
    )
    logger.info(
        f"Engine Baseline: {settings.simulation.engine_model} | Nominal Telemetry Rate: {settings.telemetry.rate_hz} Hz"
    )

    # 2. Instantiate FastAPI with lifespan
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # 3. Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 4. Attach Request ID Middleware
    app.add_middleware(RequestIdMiddleware)

    # 5. Register Centralized Exception Handlers
    register_exception_handlers(app)

    # 6. Include API Routers
    app.include_router(health_router)
    app.include_router(simulation_router)
    app.include_router(websocket_router)
    app.include_router(physics_router)
    app.include_router(ml_router)
    app.include_router(prognostics_router)
    app.include_router(mission_router)
    app.include_router(replay_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.environment == "development",
    )
