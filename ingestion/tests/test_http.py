import httpx
import pytest

from ingestion.core.http import RateLimitedClient, TooManyRetriesError


def _client(handler) -> RateLimitedClient:
    return RateLimitedClient(
        base_url="https://example.test",
        min_interval_seconds=0,
        max_attempts=3,
        retry_wait_max_seconds=0.01,
        transport=httpx.MockTransport(handler),
    )


def test_get_json_returns_payload_on_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    with _client(handler) as client:
        assert client.get_json("/thing") == {"ok": True}
        assert client.request_count == 1


def test_get_json_retries_on_5xx_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 2:
            return httpx.Response(500)
        return httpx.Response(200, json={"ok": True})

    with _client(handler) as client:
        assert client.get_json("/thing") == {"ok": True}
        assert client.request_count == 2
    assert calls["n"] == 2


def test_get_json_raises_after_exhausting_retries() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with _client(handler) as client:
        with pytest.raises(TooManyRetriesError):
            client.get_json("/thing")


def test_get_json_does_not_retry_on_4xx_other_than_429() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404)

    with _client(handler) as client:
        with pytest.raises(TooManyRetriesError):
            client.get_json("/thing")
    assert calls["n"] == 1
