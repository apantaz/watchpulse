from datetime import date

from ingestion.sources.tmdb.adapter import content_from_tmdb


def test_movie_payload_maps_to_internal_content() -> None:
    content = content_from_tmdb(
        {
            "id": 597,
            "title": "Titanic",
            "original_title": "Titanic",
            "overview": "A voyage.",
            "release_date": "1997-12-19",
            "runtime": 194,
            "original_language": "en",
            "vote_average": 7.9,
            "vote_count": 26000,
            "popularity": 99.5,
            "poster_path": "/poster.jpg",
            "backdrop_path": "/backdrop.jpg",
            "genres": [{"id": 18, "name": "Drama"}],
        },
        content_type="movie",
    )

    assert content.tmdb_id == 597
    assert content.release_date == date(1997, 12, 19)
    assert content.runtime_minutes == 194
    assert content.genres == ("Drama",)


def test_tv_payload_uses_first_episode_runtime() -> None:
    content = content_from_tmdb(
        {
            "id": 1399,
            "name": "Game of Thrones",
            "original_name": "Game of Thrones",
            "first_air_date": "2011-04-17",
            "episode_run_time": [60, 55],
            "vote_count": 25000,
            "genres": [],
        },
        content_type="tv",
    )

    assert content.title == "Game of Thrones"
    assert content.release_date == date(2011, 4, 17)
    assert content.runtime_minutes == 60
