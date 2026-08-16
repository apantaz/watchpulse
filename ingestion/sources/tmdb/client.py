"""TMDBSource: the IngestionSource implementation for TMDB.

Discovery strategy (see docs/architecture.md #11): rather than pulling
TMDB's entire catalog, `fetch_titles` uses `discover/{movie|tv}` filtered by
`watch_region` + `with_watch_providers` to get exactly the titles available
on a given provider in a given country — a few thousand rows, not millions.
Exact monetization type (subscription/rent/buy) is not in the discover
response, so `fetch_availability` is called per unique title afterward
(see ingestion/run.py) to get the authoritative watch/providers payload.
"""

from __future__ import annotations

from datetime import date
from typing import Iterator

from ingestion.core.http import RateLimitedClient
from ingestion.core.lake import RawRecord
from ingestion.core.source import IngestionSource
from ingestion.sources.tmdb.config import MAX_DISCOVER_PAGES, TMDB_BASE_URL


class TMDBSource(IngestionSource):
    name = "tmdb"

    def __init__(self, api_key: str, http_client: RateLimitedClient | None = None) -> None:
        self._api_key = api_key
        self._client = http_client or RateLimitedClient(
            base_url=TMDB_BASE_URL, min_interval_seconds=0.3
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "TMDBSource":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _get(self, path: str, params: dict) -> dict:
        # api_key is merged in only here so it never ends up in a RawRecord
        # written to the lake.
        return self._client.get_json(path, params={"api_key": self._api_key, **params})

    def fetch_titles(
        self, *, entity_type: str, country: str, provider_id: int
    ) -> Iterator[RawRecord]:
        page = 1
        total_pages = 1
        while page <= total_pages:
            params = {
                "watch_region": country,
                "with_watch_providers": str(provider_id),
                "sort_by": "popularity.desc",
                "page": page,
            }
            payload = self._get(f"/discover/{entity_type}", params)
            yield RawRecord(request_params=params, payload=payload)
            total_pages = min(int(payload.get("total_pages", 1) or 1), MAX_DISCOVER_PAGES)
            page += 1

    def fetch_availability(self, *, entity_type: str, source_title_id: int) -> RawRecord:
        payload = self._get(f"/{entity_type}/{source_title_id}/watch/providers", {})
        return RawRecord(
            request_params={"entity_type": entity_type, "tmdb_id": source_title_id},
            payload=payload,
        )

    def fetch_changes(
        self, *, entity_type: str, start_date: date, end_date: date
    ) -> Iterator[RawRecord]:
        page = 1
        total_pages = 1
        while page <= total_pages:
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "page": page,
            }
            payload = self._get(f"/{entity_type}/changes", params)
            yield RawRecord(request_params=params, payload=payload)
            total_pages = int(payload.get("total_pages", 1) or 1)
            page += 1
