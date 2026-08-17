"""Client for Movie of the Night's Streaming Availability API v4."""

from __future__ import annotations

from collections.abc import Iterator

from ingestion.core.http import RateLimitedClient
from ingestion.core.lake import RawRecord


class StreamingAvailabilitySource:
    name = "streaming_availability"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.movieofthenight.com/v4",
        http_client: RateLimitedClient | None = None,
        max_requests: int | None = None,
    ) -> None:
        self._client = http_client or RateLimitedClient(
            base_url=base_url,
            min_interval_seconds=0.3,
            headers={"X-API-Key": api_key},
            max_requests=max_requests,
        )

    @property
    def request_count(self) -> int:
        return self._client.request_count

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> StreamingAvailabilitySource:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def fetch_changes(
        self,
        *,
        country: str,
        catalogs: tuple[str, ...],
        change_type: str,
        show_type: str | None = None,
        include_unknown_dates: bool = True,
        max_pages: int | None = None,
    ) -> Iterator[RawRecord]:
        """Yield every cursor page for show-level lifecycle changes."""
        params: dict[str, str] = {
            "country": country.lower(),
            "catalogs": ",".join(catalogs),
            "change_type": change_type,
            "item_type": "show",
            "include_unknown_dates": str(include_unknown_dates).lower(),
            "order_direction": "asc",
        }
        if show_type:
            params["show_type"] = show_type

        page = 0
        while True:
            payload = self._client.get_json("/changes", params=params)
            page += 1
            yield RawRecord(request_params=dict(params), payload=payload)
            if not payload.get("hasMore") or (max_pages is not None and page >= max_pages):
                return
            cursor = payload.get("nextCursor")
            if not cursor:
                raise ValueError("Changes response hasMore=true without nextCursor")
            params["cursor"] = str(cursor)
