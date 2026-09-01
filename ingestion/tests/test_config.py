from pathlib import Path

import pytest

from watchpulse.config import Settings


def test_settings_load_product_defaults() -> None:
    settings = Settings.from_env({})

    assert settings.default_region == "GR"
    assert settings.supported_regions == ("GR",)
    assert settings.lake_root == Path("data/lake")
    assert settings.new_release_days == 90
    assert settings.streaming_availability_max_requests_per_run == 80
    assert settings.tmdb_enrichment_max_titles_per_run == 250
    assert settings.tmdb_enrichment_movie_refresh_days == 180


def test_default_region_must_be_supported() -> None:
    with pytest.raises(ValueError, match="DEFAULT_REGION"):
        Settings.from_env({"DEFAULT_REGION": "US", "SUPPORTED_REGIONS": "GR,GB"})


def test_windows_must_be_positive() -> None:
    with pytest.raises(ValueError, match="NEW_RELEASE_DAYS"):
        Settings.from_env({"NEW_RELEASE_DAYS": "0"})
