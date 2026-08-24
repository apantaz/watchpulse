"""Controlled, parameterized query construction for local discovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from watchpulse.api.filters import DiscoveryFilters


class AvailabilityState(str, Enum):
    CURRENT = "current"
    UPCOMING = "upcoming"
    ANY = "any"


class DiscoverySort(str, Enum):
    POPULARITY = "popularity"
    RELEASE_DATE = "release_date"
    NEW_RELEASES = "new_releases"
    RECENTLY_ADDED = "recently_added"
    AVAILABLE_FROM = "available_from"
    EXPIRATION = "expiration"


@dataclass(frozen=True)
class DiscoveryRequest:
    filters: DiscoveryFilters
    availability: AvailabilityState = AvailabilityState.CURRENT
    sort: DiscoverySort = DiscoverySort.POPULARITY
    limit: int = 20
    offset: int = 0
    release_date_from: date | None = None
    release_date_to: date | None = None
    available_since_from: datetime | None = None
    available_since_to: datetime | None = None
    available_from_after: datetime | None = None
    expires_from: datetime | None = None
    expires_to: datetime | None = None
    tmdb_id: int | None = None
    title_query: str | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if self.offset < 0:
            raise ValueError("offset must be zero or greater")
        if self.tmdb_id is not None and self.tmdb_id <= 0:
            raise ValueError("tmdb_id must be positive")
        if self.title_query is not None and not 2 <= len(self.title_query.strip()) <= 100:
            raise ValueError("title_query must contain between 2 and 100 characters")
        if (
            self.release_date_from is not None
            and self.release_date_to is not None
            and self.release_date_from > self.release_date_to
        ):
            raise ValueError("release_date_from must be before or equal to release_date_to")
        if (
            self.available_since_from is not None
            and self.available_since_to is not None
            and self.available_since_from > self.available_since_to
        ):
            raise ValueError("available_since_from must be before or equal to available_since_to")
        if (
            self.expires_from is not None
            and self.expires_to is not None
            and self.expires_from > self.expires_to
        ):
            raise ValueError("expires_from must be before or equal to expires_to")


@dataclass(frozen=True)
class ParameterizedQuery:
    sql: str
    parameters: tuple[Any, ...]


class DiscoveryQueryBuilder:
    """Build discovery SQL using only fixed fragments and bound values."""

    _availability_predicates = {
        AvailabilityState.CURRENT: "catalog.is_available = true",
        AvailabilityState.UPCOMING: "catalog.is_upcoming = true",
        AvailabilityState.ANY: "true",
    }
    _sort_expressions = {
        DiscoverySort.POPULARITY: "catalog.popularity_score desc nulls last",
        DiscoverySort.RELEASE_DATE: "catalog.release_date desc nulls last",
        DiscoverySort.NEW_RELEASES: (
            "catalog.popularity_score desc nulls last, "
            "catalog.tmdb_rating desc nulls last, "
            "catalog.vote_count desc nulls last, "
            "catalog.release_date desc nulls last"
        ),
        DiscoverySort.RECENTLY_ADDED: "max(catalog.available_since) desc nulls last",
        DiscoverySort.AVAILABLE_FROM: "min(catalog.available_from) asc nulls last",
        DiscoverySort.EXPIRATION: "min(catalog.expires_on) asc nulls last",
    }

    def build(self, request: DiscoveryRequest) -> ParameterizedQuery:
        filters = request.filters
        provider_placeholders = ", ".join("?" for _ in filters.providers)
        predicates = [
            "catalog.region = ?",
            f"catalog.provider_key in ({provider_placeholders})",
            self._availability_predicates[request.availability],
        ]
        parameters: list[Any] = [filters.region, *filters.providers]

        if filters.content_type is not None:
            predicates.append("catalog.content_type = ?")
            parameters.append(filters.content_type.value)
        if filters.genre_ids:
            genre_placeholders = ", ".join("?" for _ in filters.genre_ids)
            predicates.append(
                f"""
                exists (
                    select 1
                    from main_marts.content_genres as genre
                    where genre.tmdb_id = catalog.tmdb_id
                      and genre.content_type = catalog.content_type
                      and genre.genre_id in ({genre_placeholders})
                )
                """
            )
            parameters.extend(filters.genre_ids)
        if filters.runtime_max is not None:
            predicates.append("catalog.runtime_minutes <= ?")
            parameters.append(filters.runtime_max)
        if filters.release_year_from is not None:
            predicates.append("catalog.release_year >= ?")
            parameters.append(filters.release_year_from)
        if filters.release_year_to is not None:
            predicates.append("catalog.release_year <= ?")
            parameters.append(filters.release_year_to)
        if filters.rating_min is not None:
            predicates.append("catalog.tmdb_rating >= ?")
            parameters.append(filters.rating_min)
        if filters.language is not None:
            predicates.append("catalog.original_language = ?")
            parameters.append(filters.language)
        if request.release_date_from is not None:
            predicates.append("catalog.release_date >= ?")
            parameters.append(request.release_date_from)
        if request.release_date_to is not None:
            predicates.append("catalog.release_date <= ?")
            parameters.append(request.release_date_to)
        if request.available_since_from is not None:
            predicates.append("catalog.available_since >= ?")
            parameters.append(request.available_since_from)
        if request.available_since_to is not None:
            predicates.append("catalog.available_since <= ?")
            parameters.append(request.available_since_to)
        if request.available_from_after is not None:
            predicates.append("catalog.available_from > ?")
            parameters.append(request.available_from_after)
        if request.expires_from is not None:
            predicates.append("catalog.expires_on >= ?")
            parameters.append(request.expires_from)
        if request.expires_to is not None:
            predicates.append("catalog.expires_on <= ?")
            parameters.append(request.expires_to)
        if request.tmdb_id is not None:
            predicates.append("catalog.tmdb_id = ?")
            parameters.append(request.tmdb_id)
        if request.title_query is not None:
            predicates.append(
                "(contains(lower(catalog.title), lower(?)) "
                "or contains(lower(coalesce(catalog.original_title, '')), lower(?)))"
            )
            normalized_query = request.title_query.strip()
            parameters.extend((normalized_query, normalized_query))

        parameters.extend((request.limit, request.offset))
        sql = f"""
            select
                catalog.tmdb_id,
                catalog.content_type,
                catalog.title,
                catalog.original_title,
                catalog.overview,
                catalog.release_date,
                catalog.release_year,
                catalog.runtime_minutes,
                catalog.original_language,
                catalog.genre_ids,
                coalesce((
                    select list(genre.genre_name order by genre.genre_name)
                    from main_marts.content_genres as genre
                    where genre.tmdb_id = catalog.tmdb_id
                      and genre.content_type = catalog.content_type
                ), []) as genre_names,
                catalog.tmdb_rating,
                catalog.vote_count,
                catalog.popularity_score,
                catalog.poster_path,
                catalog.backdrop_path,
                catalog.metadata_source,
                max(catalog.last_updated_at) as last_updated_at,
                list(
                    struct_pack(
                        provider_key := catalog.provider_key,
                        provider_name := catalog.provider_name,
                        monetization_type := catalog.monetization_type,
                        available_since := catalog.available_since,
                        available_from := catalog.available_from,
                        expires_on := catalog.expires_on,
                        is_available := catalog.is_available,
                        is_upcoming := catalog.is_upcoming,
                        source := catalog.availability_source,
                        watch_url := catalog.watch_url
                    )
                    order by catalog.provider_name, catalog.provider_key,
                             catalog.monetization_type
                ) as availabilities,
                catalog.episode_count,
                catalog.season_count
            from main_marts.catalog_availability as catalog
            where {" and ".join(predicates)}
            group by
                catalog.tmdb_id,
                catalog.content_type,
                catalog.title,
                catalog.original_title,
                catalog.overview,
                catalog.release_date,
                catalog.release_year,
                catalog.runtime_minutes,
                catalog.original_language,
                catalog.genre_ids,
                catalog.tmdb_rating,
                catalog.vote_count,
                catalog.popularity_score,
                catalog.poster_path,
                catalog.backdrop_path,
                catalog.metadata_source,
                catalog.episode_count,
                catalog.season_count
            order by {self._sort_expressions[request.sort]},
                     catalog.tmdb_id, catalog.content_type
            limit ? offset ?
        """
        return ParameterizedQuery(sql=sql, parameters=tuple(parameters))
