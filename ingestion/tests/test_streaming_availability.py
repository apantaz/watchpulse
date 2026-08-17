import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from ingestion.core.events import read_streaming_events, write_streaming_events
from ingestion.core.http import RateLimitedClient
from ingestion.sources.streaming_availability.adapter import events_from_changes
from ingestion.sources.streaming_availability.client import StreamingAvailabilitySource
from ingestion.sources.streaming_availability.config import subscription_catalogs

FIXTURE = Path(__file__).parent / "fixtures" / "streaming_availability_changes.json"


def test_changes_map_to_region_scoped_events() -> None:
    payload = json.loads(FIXTURE.read_text())
    observed_at = datetime(2026, 8, 17, tzinfo=timezone.utc)

    events = events_from_changes(payload, region="gr", ingested_at=observed_at)

    assert len(events) == 2
    assert events[0].tmdb_id == 597
    assert events[0].provider_key == "netflix"
    assert events[0].region == "GR"
    assert events[0].event_type == "new"
    assert events[1].content_type == "tv"
    assert events[1].event_type == "upcoming"
    assert events[1].event_date is None
    assert events[1].available_from is None


def test_event_identity_is_deterministic() -> None:
    payload = json.loads(FIXTURE.read_text())

    first = events_from_changes(payload, region="GR")[0]
    second = events_from_changes(payload, region="GR")[0]

    assert first.event_id == second.event_id


def test_events_are_written_to_region_partition(tmp_path: Path) -> None:
    payload = json.loads(FIXTURE.read_text())
    events = events_from_changes(payload, region="GR")

    written = write_streaming_events(
        events,
        lake_root=tmp_path,
        source="streaming_availability",
        region="GR",
        run_id="test-run",
    )

    assert written is not None
    assert "events/source=streaming_availability/region=GR" in str(written)
    restored = read_streaming_events(
        lake_root=tmp_path, source="streaming_availability", region="GR"
    )
    assert restored == events


def test_subscription_catalogs_reject_unknown_provider() -> None:
    assert subscription_catalogs(("netflix", "prime_video")) == (
        "netflix.subscription",
        "prime.subscription",
    )
    with pytest.raises(ValueError, match="unknown"):
        subscription_catalogs(("unknown",))


def test_changes_client_follows_cursor_without_leaking_key() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page = len(requests)
        return httpx.Response(
            200,
            json={
                "changes": [],
                "shows": {},
                "hasMore": page == 1,
                **({"nextCursor": "next?cursor"} if page == 1 else {}),
            },
        )

    http = RateLimitedClient(
        "https://example.test",
        min_interval_seconds=0,
        headers={"X-API-Key": "secret-key"},
        transport=httpx.MockTransport(handler),
    )
    with StreamingAvailabilitySource("secret-key", http_client=http) as source:
        records = list(
            source.fetch_changes(
                country="GR",
                catalogs=("netflix.subscription",),
                change_type="new",
            )
        )

    assert len(records) == 2
    assert records[1].request_params["cursor"] == "next?cursor"
    assert "secret-key" not in json.dumps(records[0].request_params)
    assert requests[0].headers["X-API-Key"] == "secret-key"


def test_changes_client_can_stop_after_bounded_page_count() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200, json={"changes": [], "shows": {}, "hasMore": True, "nextCursor": "next"}
        )

    http = RateLimitedClient(
        "https://example.test",
        min_interval_seconds=0,
        headers={"X-API-Key": "secret-key"},
        transport=httpx.MockTransport(handler),
    )
    with StreamingAvailabilitySource("secret-key", http_client=http) as source:
        records = list(
            source.fetch_changes(
                country="GR",
                catalogs=("netflix.subscription",),
                change_type="new",
                max_pages=1,
            )
        )

    assert len(records) == 1
    assert calls == 1
