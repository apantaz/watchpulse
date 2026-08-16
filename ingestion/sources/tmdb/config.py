"""TMDB source configuration for the launch scope: Greece, four providers.

Provider TMDB ids below are the commonly documented ones (verified via
TMDB's /watch/providers/movie and /watch/providers/tv list endpoints as of
this writing). TMDB occasionally adjusts provider ids per region — run
`python -m ingestion.sources.tmdb.list_providers` against a live API key
before a real backfill to confirm these still match GR.
"""

from __future__ import annotations

TMDB_BASE_URL = "https://api.themoviedb.org/3"

ENTITY_TYPES: tuple[str, ...] = ("movie", "tv")

DEFAULT_COUNTRIES: tuple[str, ...] = ("GR",)

# provider slug (our dim_provider) -> TMDB watch-provider id
PROVIDERS: dict[str, int] = {
    "netflix": 8,
    "disney_plus": 337,
    "prime_video": 119,
    "apple_tv_plus": 350,
}

# TMDB paginates discover results and caps total_pages at 500.
MAX_DISCOVER_PAGES = 500
