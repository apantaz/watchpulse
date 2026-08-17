"""Rate-limited, retrying HTTP client shared by all ingestion sources.

See docs/architecture.md #11 (Ingestion Design): conservative throttling,
exponential backoff with jitter on 429/5xx, capped retries so a stuck run
fails loudly instead of hanging CI.
"""

from __future__ import annotations

import time

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)


class TooManyRetriesError(RuntimeError):
    pass


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return False


class RateLimitedClient:
    """Thin wrapper around httpx with a fixed min-interval throttle and
    capped exponential-backoff retries. Not thread-safe by design — each
    ingestion run uses one client sequentially, which keeps behavior
    predictable against TMDB's rate limits.
    """

    def __init__(
        self,
        base_url: str,
        *,
        min_interval_seconds: float = 0.25,
        timeout_seconds: float = 15.0,
        max_attempts: int = 5,
        headers: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
        retry_wait_max_seconds: float = 30.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            headers=headers or {},
            transport=transport,
        )
        self._min_interval = min_interval_seconds
        self._max_attempts = max_attempts
        self._retry_wait_max_seconds = retry_wait_max_seconds
        self._last_request_at: float | None = None
        self._request_count = 0

    @property
    def request_count(self) -> int:
        return self._request_count

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> RateLimitedClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _throttle(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = self._min_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def get_json(self, path: str, params: dict | None = None) -> dict:
        @retry(
            reraise=True,
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_random_exponential(multiplier=1, max=self._retry_wait_max_seconds),
            retry=retry_if_exception(_is_retryable),
        )
        def _do_get() -> dict:
            self._throttle()
            self._last_request_at = time.monotonic()
            self._request_count += 1
            response = self._client.get(path, params=params)
            response.raise_for_status()
            return response.json()

        try:
            return _do_get()
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            raise TooManyRetriesError(
                f"GET {path} failed after {self._max_attempts} attempts: {exc}"
            ) from exc
