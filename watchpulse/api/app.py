"""FastAPI application factory for local catalog discovery."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from watchpulse.api.models import CatalogFreshnessResponse, HealthResponse
from watchpulse.api.repository import CatalogRepository, CatalogUnavailableError
from watchpulse.api.routers.catalog import router as catalog_router
from watchpulse.api.routers.discovery import router as discovery_router
from watchpulse.config import Settings


def create_app(
    settings: Settings | None = None,
    repository: CatalogRepository | None = None,
) -> FastAPI:
    """Create an API instance without opening the database at import time."""

    resolved_settings = settings or Settings.from_env()
    catalog_repository = repository or CatalogRepository(resolved_settings.serving_database_path)

    app = FastAPI(
        title="WatchPulse API",
        version="0.5.0",
        description="Read-only discovery over the locally published WatchPulse catalog.",
    )
    app.state.catalog_repository = catalog_repository
    app.state.settings = resolved_settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.frontend_origins),
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )

    @app.exception_handler(CatalogUnavailableError)
    async def catalog_unavailable(
        _request: Request, error: CatalogUnavailableError
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/api/v1/catalog/freshness",
        response_model=CatalogFreshnessResponse,
        tags=["catalog"],
    )
    async def catalog_freshness(request: Request) -> CatalogFreshnessResponse:
        freshness = request.app.state.catalog_repository.get_freshness()
        return CatalogFreshnessResponse.model_validate(freshness)

    app.include_router(catalog_router)
    app.include_router(discovery_router)

    return app
