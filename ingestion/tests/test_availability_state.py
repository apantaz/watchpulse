from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from watchpulse.availability_state import AvailabilityStateRepository
from watchpulse.models import StreamingEvent


def _event(event_type: str) -> StreamingEvent:
    timestamp = datetime(2026, 8, 20, tzinfo=timezone.utc)
    return StreamingEvent(
        event_id=f"event-{event_type}",
        tmdb_id=597,
        content_type="movie",
        region="GR",
        provider_key="netflix",
        monetization_type="subscription",
        event_type=event_type,
        event_date=timestamp,
        available_from=timestamp if event_type == "upcoming" else None,
        expires_on=timestamp if event_type == "expiring" else None,
        source="streaming_availability",
        source_event_id=None,
        ingested_at=timestamp,
    )


def _state(database_path: Path) -> tuple:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        return connection.execute(
            """
            SELECT is_available, is_upcoming, available_since,
                   available_from, expires_on
            FROM streaming_availability_state
            """
        ).fetchone()


def test_new_then_removed_updates_current_state(tmp_path: Path) -> None:
    path = tmp_path / "warehouse.duckdb"
    state = AvailabilityStateRepository(path)

    assert state.apply([_event("new")]) == 1
    assert _state(path)[0:2] == (True, False)
    assert state.apply([_event("removed")]) == 1
    assert _state(path)[0:2] == (False, False)


def test_upcoming_is_not_currently_available(tmp_path: Path) -> None:
    path = tmp_path / "warehouse.duckdb"
    state = AvailabilityStateRepository(path)

    state.apply([_event("upcoming")])

    row = _state(path)
    assert row[0:2] == (False, True)
    assert row[3] is not None


def test_expiring_remains_available_and_duplicate_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "warehouse.duckdb"
    state = AvailabilityStateRepository(path)
    event = _event("expiring")

    assert state.apply([event]) == 1
    assert state.apply([event]) == 0

    row = _state(path)
    assert row[0:2] == (True, False)
    assert row[4] is not None


def test_state_is_isolated_by_region_and_provider(tmp_path: Path) -> None:
    path = tmp_path / "warehouse.duckdb"
    state = AvailabilityStateRepository(path)
    base = _event("new")
    events = [
        base,
        replace(base, event_id="event-us", region="US"),
        replace(base, event_id="event-disney", provider_key="disney_plus"),
    ]

    assert state.apply(events) == 3
    with duckdb.connect(str(path), read_only=True) as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM streaming_availability_state").fetchone()[0]
            == 3
        )
