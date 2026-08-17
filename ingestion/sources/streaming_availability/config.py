"""Stable WatchPulse mappings for Streaming Availability service IDs."""

from __future__ import annotations

PROVIDER_MAP: dict[str, str] = {
    "netflix": "netflix",
    "disney": "disney_plus",
    "prime": "prime_video",
    "apple": "apple_tv_plus",
}

CHANGE_TYPES: tuple[str, ...] = (
    "new",
    "removed",
    "updated",
    "expiring",
    "upcoming",
)


def subscription_catalogs(provider_keys: tuple[str, ...]) -> tuple[str, ...]:
    reverse_map = {internal: source for source, internal in PROVIDER_MAP.items()}
    unknown = set(provider_keys) - reverse_map.keys()
    if unknown:
        raise ValueError(f"No Streaming Availability mapping for: {sorted(unknown)}")
    return tuple(f"{reverse_map[key]}.subscription" for key in provider_keys)
