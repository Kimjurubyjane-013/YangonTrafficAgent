"""Cached Open-Meteo weather observations for Yangon.

Weather observations are provider data. The traffic-risk classification is a
small, transparent rule layer and is never presented as measured traffic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from threading import RLock
from time import monotonic
from typing import Any, Callable

import requests


LOGGER = logging.getLogger(__name__)
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
YANGON_LATITUDE = 16.8409
YANGON_LONGITUDE = 96.1735
YANGON_TIMEZONE = "Asia/Yangon"
WEATHER_CACHE_SECONDS = 600
WEATHER_TIMEOUT_SECONDS = 4
YANGON_UTC_OFFSET = timezone(timedelta(hours=6, minutes=30))
CURRENT_FIELDS = (
    "temperature_2m", "relative_humidity_2m", "precipitation", "rain",
    "weather_code", "wind_speed_10m",
)


class WeatherUnavailable(RuntimeError):
    """Raised when a valid provider observation cannot be obtained."""


@dataclass(frozen=True)
class WeatherRisk:
    condition: str
    risk: str
    prolog_atom: str
    reason: str


def _condition_for_code(code: int) -> str:
    if code == 0:
        return "Clear"
    if code in {1, 2, 3}:
        return "Partly Cloudy" if code < 3 else "Overcast"
    if code in {45, 48}:
        return "Fog"
    if code in {51, 53, 55, 56, 57}:
        return "Drizzle"
    if code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "Rain"
    if code in {71, 73, 75, 77, 85, 86}:
        return "Snow"
    if code in {95, 96, 99}:
        return "Thunderstorm"
    return "Unknown"


def classify_weather_risk(code: int, precipitation_mm: float, rain_mm: float,
                          wind_speed_kmh: float) -> WeatherRisk:
    """Map provider observations to conservative, explainable route-risk facts."""
    wet_amount = max(precipitation_mm, rain_mm)
    if code in {95, 96, 99} or wet_amount >= 7.5 or wind_speed_kmh >= 50:
        return WeatherRisk(
            "adverse", "High", "storm",
            "Thunderstorm, heavy precipitation, or strong-wind conditions may reduce effective road speed.",
        )
    if code in {45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82} or wet_amount > 0:
        return WeatherRisk(
            "wet", "Moderate", "rain",
            "Wet-road or reduced-visibility conditions may require more cautious travel.",
        )
    return WeatherRisk("normal", "Low", "clear", "No adverse weather rule is active for this observation.")


class WeatherService:
    def __init__(self, request_get: Callable[..., Any] | None = None,
                 cache_seconds: int = WEATHER_CACHE_SECONDS):
        self._get = request_get or requests.get
        self._cache_seconds = max(60, int(cache_seconds))
        self._lock = RLock()
        self._cached: dict[str, Any] | None = None
        self._cached_at = 0.0

    def current(self, force: bool = False) -> dict[str, Any]:
        with self._lock:
            if not force and self._cached and monotonic() - self._cached_at < self._cache_seconds:
                return dict(self._cached)
        try:
            response = self._get(
                OPEN_METEO_URL,
                params={
                    "latitude": YANGON_LATITUDE,
                    "longitude": YANGON_LONGITUDE,
                    "current": ",".join(CURRENT_FIELDS),
                    "timezone": YANGON_TIMEZONE,
                },
                timeout=WEATHER_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            normalized = self._normalize(response.json())
        except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
            LOGGER.warning("Open-Meteo weather unavailable: %s", exc)
            raise WeatherUnavailable("Weather temporarily unavailable.") from exc
        with self._lock:
            self._cached = normalized
            self._cached_at = monotonic()
        return dict(normalized)

    @staticmethod
    def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
        current = payload.get("current")
        if not isinstance(current, dict):
            raise ValueError("Open-Meteo response has no current observation")
        required = set(CURRENT_FIELDS) | {"time"}
        if not required.issubset(current):
            raise ValueError("Open-Meteo current observation is incomplete")
        temperature = float(current["temperature_2m"])
        humidity = float(current["relative_humidity_2m"])
        precipitation = max(0.0, float(current["precipitation"]))
        rain = max(0.0, float(current["rain"]))
        wind = max(0.0, float(current["wind_speed_10m"]))
        code = int(current["weather_code"])
        if not (-80 <= temperature <= 65 and 0 <= humidity <= 100 and 0 <= code <= 99):
            raise ValueError("Open-Meteo current observation is outside valid bounds")
        # Open-Meteo returns local wall time because the request explicitly
        # specifies Asia/Yangon. Myanmar has used UTC+06:30 year-round since
        # 1945, so this normalization does not require an OS timezone database.
        observed = datetime.fromisoformat(str(current["time"])).replace(
            tzinfo=YANGON_UTC_OFFSET
        ).isoformat()
        risk = classify_weather_risk(code, precipitation, rain, wind)
        return {
            "location": "Yangon",
            "latitude": YANGON_LATITUDE,
            "longitude": YANGON_LONGITUDE,
            "timezone": YANGON_TIMEZONE,
            "temperature_c": round(temperature, 1),
            "humidity_percent": round(humidity),
            "precipitation_mm": round(precipitation, 2),
            "rain_mm": round(rain, 2),
            "wind_speed_kmh": round(wind, 1),
            "weather_code": code,
            "condition": _condition_for_code(code),
            "observed_at": observed,
            "source": "Open-Meteo",
            "status": "live",
            "traffic_impact": {
                "risk": risk.risk,
                "condition": risk.condition,
                "prolog_weather": risk.prolog_atom,
                "reason": risk.reason,
                "source": "INFERRED / RULE-BASED",
            },
        }


WEATHER_SERVICE = WeatherService()
