"""Stable API response contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Process liveness response that does not depend on the catalog."""

    status: str


class CatalogFreshnessResponse(BaseModel):
    """Freshness and validated row counts for the published catalog."""

    model_config = ConfigDict(from_attributes=True)

    catalog_name: str
    warehouse_built_at: datetime
    latest_source_updated_at: datetime
    catalog_row_count: int
    current_row_count: int
    upcoming_row_count: int
