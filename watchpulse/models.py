"""Source-independent domain models used at ingestion boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

ContentType = Literal["movie", "tv"]


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
