"""Translate TMDB payloads into WatchPulse-owned domain models."""

from __future__ import annotations

from datetime import date
from typing import Any

from watchpulse.models import Content, ContentType


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def content_from_tmdb(payload: dict[str, Any], *, content_type: ContentType) -> Content:
    is_movie = content_type == "movie"
    title_key = "title" if is_movie else "name"
    original_title_key = "original_title" if is_movie else "original_name"
    release_key = "release_date" if is_movie else "first_air_date"

    runtime = payload.get("runtime") if is_movie else None
    if not is_movie:
        runtimes = payload.get("episode_run_time") or []
        runtime = runtimes[0] if runtimes else None

    return Content(
        tmdb_id=int(payload["id"]),
        content_type=content_type,
        title=str(payload[title_key]),
        original_title=str(payload.get(original_title_key) or payload[title_key]),
        overview=payload.get("overview") or None,
        release_date=_date(payload.get(release_key)),
        runtime_minutes=int(runtime) if runtime is not None else None,
        original_language=payload.get("original_language") or None,
        tmdb_rating=(
            float(payload["vote_average"]) if payload.get("vote_average") is not None else None
        ),
        vote_count=int(payload.get("vote_count") or 0),
        tmdb_popularity=(
            float(payload["popularity"]) if payload.get("popularity") is not None else None
        ),
        poster_path=payload.get("poster_path"),
        backdrop_path=payload.get("backdrop_path"),
        genres=tuple(str(genre["name"]) for genre in payload.get("genres", [])),
    )
