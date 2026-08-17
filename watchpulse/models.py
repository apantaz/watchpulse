"""Source-independent domain models used at ingestion boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

ContentType = Literal["movie", "tv"]
StreamingEventType = Literal["new", "removed", "updated", "expiring", "upcoming"]
MonetizationType = Literal["subscription", "free", "rent", "buy", "addon"]


@dataclass(frozen=True)
class Content:
    tmdb_id: int
    content_type: ContentType
    title: str
    original_title: str
    overview: str | None
    release_date: date | None
    runtime_minutes: int | None
    original_language: str | None
    tmdb_rating: float | None
    vote_count: int
    tmdb_popularity: float | None
    poster_path: str | None
    backdrop_path: str | None
    genres: tuple[str, ...]


@dataclass(frozen=True)
class Provider:
    provider_key: str
    provider_name: str
    source: str
    source_provider_id: str


@dataclass(frozen=True)
class StreamingEvent:
    event_id: str
    tmdb_id: int
    content_type: ContentType
    region: str
    provider_key: str
    monetization_type: MonetizationType
    event_type: StreamingEventType
    event_date: datetime | None
    available_from: datetime | None
    expires_on: datetime | None
    source: str
    source_event_id: str | None
    ingested_at: datetime
