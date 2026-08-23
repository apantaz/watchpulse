"""Shared, typed filters for every WatchPulse discovery section."""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Self

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ContentType(str, Enum):
    """Content types stored by the serving catalog."""

    MOVIE = "movie"
    TV = "tv"


class CatalogScope(BaseModel):
    """Catalog scope used while a user is still choosing filter options."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    region: str = Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    providers: tuple[str, ...] = Field(default=(), max_length=20)
    content_type: ContentType | None = None

    @field_validator("region", mode="before")
    @classmethod
    def normalize_region(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("providers", mode="before")
    @classmethod
    def normalize_providers(cls, value: object) -> object:
        if not isinstance(value, (list, tuple)):
            return value
        normalized = tuple(
            dict.fromkeys(item.strip().lower() if isinstance(item, str) else item for item in value)
        )
        return normalized

    @field_validator("providers")
    @classmethod
    def validate_provider_keys(cls, providers: tuple[str, ...]) -> tuple[str, ...]:
        for provider in providers:
            if re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", provider) is None:
                raise ValueError(
                    "provider keys must contain only letters, numbers, and underscores"
                )
        return providers


class DiscoveryFilters(CatalogScope):
    """The global filter universe shared by all discovery sections."""

    providers: tuple[str, ...] = Field(min_length=1, max_length=20)
    genre_ids: tuple[int, ...] = Field(default=(), max_length=20)
    runtime_max: int | None = Field(default=None, ge=1, le=1440)
    release_year_from: int | None = Field(default=None, ge=1870, le=2200)
    release_year_to: int | None = Field(default=None, ge=1870, le=2200)
    rating_min: float | None = Field(default=None, ge=0, le=10)
    language: str | None = Field(default=None, pattern=r"^[a-z]{2,3}$")

    @field_validator("genre_ids", mode="before")
    @classmethod
    def deduplicate_genres(cls, value: object) -> object:
        if isinstance(value, (list, tuple)):
            return tuple(dict.fromkeys(value))
        return value

    @field_validator("genre_ids")
    @classmethod
    def validate_genre_ids(cls, genre_ids: tuple[int, ...]) -> tuple[int, ...]:
        if any(genre_id <= 0 for genre_id in genre_ids):
            raise ValueError("genre IDs must be positive")
        return genre_ids

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_release_year_range(self) -> Self:
        if (
            self.release_year_from is not None
            and self.release_year_to is not None
            and self.release_year_from > self.release_year_to
        ):
            raise ValueError("release_year_from must be less than or equal to release_year_to")
        return self


DiscoveryFiltersQuery = Annotated[DiscoveryFilters, Query()]
"""FastAPI query binding reused by every discovery endpoint."""

CatalogScopeQuery = Annotated[CatalogScope, Query()]
"""FastAPI query binding for region/provider-aware reference options."""
