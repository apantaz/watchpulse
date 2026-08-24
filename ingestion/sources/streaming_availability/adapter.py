"""Translate Streaming Availability changes into WatchPulse events."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, cast
from urllib.parse import urlparse

from ingestion.sources.streaming_availability.config import PROVIDER_MAP
from watchpulse.models import (
    ContentType,
    MonetizationType,
    StreamingEvent,
    StreamingEventType,
)


def events_from_changes(
    payload: dict[str, Any],
    *,
    region: str,
    ingested_at: datetime | None = None,
) -> list[StreamingEvent]:
    shows = payload.get("shows") or {}
    observed_at = ingested_at or datetime.now(timezone.utc)
    events = []

    for change in payload.get("changes", []):
        show_id = str(change["showId"])
        show = shows.get(show_id)
        if not show or not show.get("tmdbId"):
            raise ValueError(f"Change show {show_id} has no TMDB mapping")

        source_provider_id = str(change["service"]["id"])
        provider_key = PROVIDER_MAP.get(source_provider_id)
        if not provider_key:
            raise ValueError(f"Unknown Streaming Availability provider: {source_provider_id}")

        event_type = cast(StreamingEventType, str(change["changeType"]))
        event_date = _timestamp(change.get("timestamp"))
        identity = "|".join(
            (
                show_id,
                region.upper(),
                source_provider_id,
                str(change["streamingOptionType"]),
                event_type,
                str(change.get("timestamp") or "unknown"),
                str(change.get("link") or ""),
            )
        )
        events.append(
            StreamingEvent(
                event_id=hashlib.sha256(identity.encode()).hexdigest(),
                tmdb_id=parse_tmdb_id(str(show["tmdbId"]), show_type=str(change["showType"])),
                content_type=_content_type(str(change["showType"])),
                region=region.upper(),
                provider_key=provider_key,
                monetization_type=cast(MonetizationType, str(change["streamingOptionType"])),
                event_type=event_type,
                event_date=event_date,
                available_from=event_date if event_type == "upcoming" else None,
                expires_on=event_date if event_type == "expiring" else None,
                source="streaming_availability",
                source_event_id=None,
                ingested_at=observed_at,
                watch_url=_watch_url(change.get("link")),
            )
        )
    return events


def _watch_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        return None
    return value.strip()


def _timestamp(value: int | None) -> datetime | None:
    return datetime.fromtimestamp(value, tz=timezone.utc) if value is not None else None


def _content_type(show_type: str) -> ContentType:
    if show_type == "movie":
        return "movie"
    if show_type == "series":
        return "tv"
    raise ValueError(f"Unknown show type: {show_type}")


def parse_tmdb_id(value: str, *, show_type: str) -> int:
    """Parse v4 IDs such as ``movie/9430`` while accepting legacy bare IDs."""
    if "/" not in value:
        return int(value)
    prefix, identifier = value.split("/", maxsplit=1)
    expected_prefix = "movie" if show_type == "movie" else "tv"
    if prefix != expected_prefix:
        raise ValueError(f"TMDB identifier {value!r} does not match show type {show_type!r}")
    return int(identifier)
