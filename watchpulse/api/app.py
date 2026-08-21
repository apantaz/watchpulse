"""FastAPI application factory for local catalog discovery."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status

from watchpulse.api.models import CatalogFreshnessResponse, HealthResponse
from watchpulse.api.repository import CatalogRepository, CatalogUnavailableError
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
        version="0.4.0",
        description="Read-only discovery over the locally published WatchPulse catalog.",
    )
    app.state.catalog_repository = catalog_repository

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/api/v1/catalog/freshness",
        response_model=CatalogFreshnessResponse,
        tags=["catalog"],
    )
    async def catalog_freshness(request: Request) -> CatalogFreshnessResponse:
        try:
            freshness = request.app.state.catalog_repository.get_freshness()
        except CatalogUnavailableError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error
        return CatalogFreshnessResponse.model_validate(freshness)

    return app
