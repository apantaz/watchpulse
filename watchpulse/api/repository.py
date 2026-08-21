"""Read-only access to the published DuckDB serving database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb


class CatalogUnavailableError(RuntimeError):
    """Raised when the published catalog cannot safely serve a request."""


@dataclass(frozen=True)
class CatalogFreshness:
    catalog_name: str
    warehouse_built_at: datetime
    latest_source_updated_at: datetime
    catalog_row_count: int
    current_row_count: int
    upcoming_row_count: int


class CatalogRepository:
    """Repository boundary for local, read-only catalog queries."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def get_freshness(self) -> CatalogFreshness:
        if not self.database_path.is_file():
            raise CatalogUnavailableError("The serving catalog is not available")

        try:
            with duckdb.connect(str(self.database_path), read_only=True) as connection:
                row = connection.execute(
                    """
                    select
                        catalog_name,
                        warehouse_built_at,
                        latest_source_updated_at,
                        catalog_row_count,
                        current_row_count,
                        upcoming_row_count
                    from main_marts.catalog_freshness
                    """
                ).fetchone()
        except duckdb.Error as error:
            raise CatalogUnavailableError("The serving catalog could not be read") from error

        if row is None:
            raise CatalogUnavailableError("Catalog freshness metadata is missing")

        return CatalogFreshness(*row)
