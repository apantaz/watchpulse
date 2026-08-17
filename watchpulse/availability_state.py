"""Idempotent application of lifecycle events to current availability state."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb

from watchpulse.models import StreamingEvent


class AvailabilityStateRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(self._database_path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS streaming_availability_state (
                    tmdb_id BIGINT NOT NULL,
                    content_type VARCHAR NOT NULL,
                    region VARCHAR NOT NULL,
                    provider_key VARCHAR NOT NULL,
                    monetization_type VARCHAR NOT NULL,
                    available_since TIMESTAMPTZ,
                    available_from TIMESTAMPTZ,
                    expires_on TIMESTAMPTZ,
                    is_available BOOLEAN NOT NULL,
                    is_upcoming BOOLEAN NOT NULL,
                    source VARCHAR NOT NULL,
                    last_updated_at TIMESTAMPTZ NOT NULL,
                    PRIMARY KEY (
                        tmdb_id, content_type, region, provider_key, monetization_type
                    )
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS applied_streaming_events (
                    event_id VARCHAR PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL
                )
                """
            )

    def apply(self, events: list[StreamingEvent]) -> int:
        """Apply unseen events transactionally and return the applied count."""
        self.initialize()
        applied = 0
        with duckdb.connect(str(self._database_path)) as connection:
            connection.begin()
            try:
                for event in events:
                    exists = connection.execute(
                        "SELECT 1 FROM applied_streaming_events WHERE event_id = ?",
                        [event.event_id],
                    ).fetchone()
                    if exists:
                        continue
                    self._apply_event(connection, event)
                    connection.execute(
                        "INSERT INTO applied_streaming_events VALUES (?, ?)",
                        [event.event_id, datetime.now(timezone.utc)],
                    )
                    applied += 1
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return applied

    def _apply_event(self, connection: duckdb.DuckDBPyConnection, event: StreamingEvent) -> None:
        key = [
            event.tmdb_id,
            event.content_type,
            event.region,
            event.provider_key,
            event.monetization_type,
        ]
        if event.event_type == "updated":
            connection.execute(
                """
                UPDATE streaming_availability_state
                SET last_updated_at = ?, source = ?
                WHERE tmdb_id = ? AND content_type = ? AND region = ?
                  AND provider_key = ? AND monetization_type = ?
                """,
                [event.ingested_at, event.source, *key],
            )
            return

        is_available = event.event_type in {"new", "expiring"}
        is_upcoming = event.event_type == "upcoming"
        available_since = event.event_date if event.event_type == "new" else None
        available_from = event.available_from if is_upcoming else None
        expires_on = (
            event.expires_on
            if event.event_type == "expiring"
            else event.event_date
            if event.event_type == "removed"
            else None
        )
        connection.execute(
            """
            INSERT INTO streaming_availability_state (
                tmdb_id, content_type, region, provider_key, monetization_type,
                available_since, available_from, expires_on, is_available,
                is_upcoming, source, last_updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (
                tmdb_id, content_type, region, provider_key, monetization_type
            ) DO UPDATE SET
                available_since = COALESCE(excluded.available_since,
                                           streaming_availability_state.available_since),
                available_from = excluded.available_from,
                expires_on = excluded.expires_on,
                is_available = excluded.is_available,
                is_upcoming = excluded.is_upcoming,
                source = excluded.source,
                last_updated_at = excluded.last_updated_at
            """,
            [
                *key,
                available_since,
                available_from,
                expires_on,
                is_available,
                is_upcoming,
                event.source,
                event.ingested_at,
            ],
        )
