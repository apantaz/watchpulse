"""Source abstraction. Per docs/architecture.md #11: a second source later
(editorial curation, another catalog API, ...) implements this same
interface and lands in the same raw-layer shape, without touching existing
TMDB data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import date

from ingestion.core.lake import RawRecord


class IngestionSource(ABC):
    name: str

    @abstractmethod
    def fetch_titles(
        self, *, entity_type: str, country: str, provider_id: int
    ) -> Iterator[RawRecord]:
        """Yield raw discover-page records: titles available on a given
        provider, in a given country, for a given entity type."""

    @abstractmethod
    def fetch_availability(self, *, entity_type: str, source_title_id: int) -> RawRecord:
        """Yield the raw watch-providers response for a single title
        (covers all countries in one payload)."""

    @abstractmethod
    def fetch_metadata(self, *, entity_type: str, source_title_id: int) -> RawRecord:
        """Return the source metadata response for one title."""

    @abstractmethod
    def fetch_changes(
        self, *, entity_type: str, start_date: date, end_date: date
    ) -> Iterator[RawRecord]:
        """Yield raw changes-feed pages, for incremental re-sync."""
