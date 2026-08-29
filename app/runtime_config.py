"""Runtime configuration shared by desktop and HTTP deployments."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_TIMEZONE = "Asia/Yangon"
VALID_TRAFFIC_MODES = frozenset({"real", "simulation", "real_with_simulation_fallback"})


def traffic_mode() -> str:
    value = os.getenv("TRAFFIC_MODE", "real").strip().lower()
    return value if value in VALID_TRAFFIC_MODES else "real"


def traffic_cache_seconds() -> int:
    try:
        return max(30, min(300, int(os.getenv("TRAFFIC_CACHE_SECONDS", "60"))))
    except ValueError:
        return 60


def app_timezone() -> ZoneInfo:
    name = os.getenv("APP_TIMEZONE", DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        # Windows Python installations may not include the IANA database.
        # Myanmar has observed UTC+06:30 year-round since 1945, so this fixed
        # offset is a safe runtime fallback until the tzdata package is present.
        if name == DEFAULT_TIMEZONE:
            return timezone(timedelta(hours=6, minutes=30), DEFAULT_TIMEZONE)
        try:
            return ZoneInfo(DEFAULT_TIMEZONE)
        except ZoneInfoNotFoundError:
            return timezone(timedelta(hours=6, minutes=30), DEFAULT_TIMEZONE)


def yangon_now(value: datetime | None = None) -> datetime:
    zone = app_timezone()
    if value is None:
        return datetime.now(zone)
    if value.tzinfo is None:
        return value.replace(tzinfo=zone)
    return value.astimezone(zone)
