"""HERE traffic-aware routing provider.

Only provider-reported road geometry and traffic durations are returned. The
API key is read from the server environment and is never sent to the browser.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
import re

import requests


HERE_ROUTES_URL = "https://router.hereapi.com/v8/routes"
HERE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
HERE_DECODE = {character: index for index, character in enumerate(HERE_ALPHABET)}
DEFAULT_TIMEOUT_SECONDS = 8.0


class TrafficDataUnavailable(RuntimeError):
    pass


def _decode_unsigned(encoded: str, index: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while index < len(encoded):
        chunk = HERE_DECODE.get(encoded[index])
        index += 1
        if chunk is None:
            raise ValueError("Invalid HERE flexible polyline character")
        value |= (chunk & 0x1F) << shift
        if not chunk & 0x20:
            return value, index
        shift += 5
    raise ValueError("Incomplete HERE flexible polyline")


def _decode_signed(value: int) -> int:
    return -(value >> 1) - 1 if value & 1 else value >> 1


def decode_flexible_polyline(encoded: str) -> list[list[float]]:
    """Decode HERE Flexible Polyline into ``[latitude, longitude]`` pairs."""
    index = 0
    version, index = _decode_unsigned(encoded, index)
    if version != 1:
        raise ValueError(f"Unsupported HERE flexible polyline version: {version}")
    header, index = _decode_unsigned(encoded, index)
    precision = header & 15
    third_dimension = (header >> 4) & 7
    third_precision = (header >> 7) & 15
    factor = 10**precision
    third_factor = 10**third_precision
    latitude = longitude = third = 0
    coordinates: list[list[float]] = []
    while index < len(encoded):
        value, index = _decode_unsigned(encoded, index)
        latitude += _decode_signed(value)
        value, index = _decode_unsigned(encoded, index)
        longitude += _decode_signed(value)
        point = [latitude / factor, longitude / factor]
        if third_dimension:
            value, index = _decode_unsigned(encoded, index)
            third += _decode_signed(value)
            _ = third / third_factor
        coordinates.append(point)
    return coordinates


def _english_road_names(route: dict) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for section in route.get("sections", []):
        for action in section.get("actions", []):
            road = action.get("nextRoad") or action.get("currentRoad") or {}
            localized = road.get("name") or []
            for item in localized:
                value = str(item.get("value", "") if isinstance(item, dict) else item).strip()
                english = value.encode("ascii", "ignore").decode("ascii").strip()
                key = re.sub(r"[^a-z0-9]", "", english.casefold())
                if key and re.search(r"[A-Za-z]", english) and key not in seen:
                    seen.add(key)
                    names.append(english)
    return names[:3]


def _traffic_level(duration_seconds: float, base_seconds: float) -> str:
    if base_seconds <= 0:
        return "Light"
    delay_ratio = max(0.0, duration_seconds / base_seconds - 1.0)
    if delay_ratio >= 0.35:
        return "Heavy"
    if delay_ratio >= 0.12:
        return "Moderate"
    return "Light"


def _route_record(route: dict, provider_id: int, retrieved_at: str, provider_timestamp: str | None = None) -> dict:
    geometry: list[list[float]] = []
    traffic_geometry: list[list[list[float]]] = []
    distance = duration = base_duration = 0.0
    section_levels: list[str] = []
    for section in route.get("sections", []):
        shape = decode_flexible_polyline(section.get("polyline", ""))
        if len(shape) >= 2:
            traffic_geometry.append(shape)
        if geometry and shape:
            shape = shape[1:]
        geometry.extend(shape)
        summary = section.get("summary") or section.get("travelSummary") or {}
        section_distance = float(summary.get("length", 0))
        section_duration = float(summary.get("duration", 0))
        section_base = float(summary.get("baseDuration", section_duration))
        distance += section_distance
        duration += section_duration
        base_duration += section_base
        section_levels.append(_traffic_level(section_duration, section_base))
    if len(geometry) < 2 or distance <= 0 or duration <= 0:
        raise ValueError("HERE returned an incomplete route")
    level = _traffic_level(duration, base_duration)
    return {
        "provider_id": provider_id,
        "distance": round(distance / 1000, 2),
        "duration": round(duration / 60, 2),
        "base_duration": round(base_duration / 60, 2),
        "traffic_delay": round(max(0.0, duration - base_duration) / 60, 2),
        "route_duration_seconds": round(duration),
        "base_duration_seconds": round(base_duration),
        "traffic_delay_seconds": round(max(0.0, duration - base_duration)),
        "traffic_level": level,
        "segment_traffic": section_levels or [level],
        "traffic_geometry": traffic_geometry,
        "traffic_data_available": True,
        "traffic_source": "HERE Traffic",
        "retrieved_at": retrieved_at,
        # HERE Routing does not guarantee a source-update timestamp. Keep the
        # application retrieval time separate and never invent provider time.
        "provider_timestamp": provider_timestamp,
        "provider": "HERE Routing API",
        "geometry": geometry,
        "road_names": _english_road_names(route),
        "source": "here-traffic",
    }


def fetch_traffic_aware_routes(start_coord, destination_coord, alternatives=3, timeout=DEFAULT_TIMEOUT_SECONDS):
    api_key = os.environ.get("HERE_API_KEY", "").strip()
    if not api_key:
        raise TrafficDataUnavailable(
            "Real traffic routing is not configured. Set the server-side HERE_API_KEY environment variable."
        )
    params = {
        "apiKey": api_key,
        "transportMode": "car",
        "origin": f"{start_coord[0]},{start_coord[1]}",
        "destination": f"{destination_coord[0]},{destination_coord[1]}",
        "routingMode": "fast",
        "departureTime": "now",
        "alternatives": max(0, min(5, int(alternatives))),
        "return": "polyline,summary,travelSummary,actions,instructions",
    }
    try:
        response = requests.get(HERE_ROUTES_URL, params=params, timeout=max(1.0, float(timeout)))
        response.raise_for_status()
        payload = response.json()
        retrieved_at = datetime.now(timezone.utc).isoformat()
        provider_timestamp = payload.get("sourceUpdated")
        routes = [
            _route_record(route, index, retrieved_at, provider_timestamp)
            for index, route in enumerate(payload.get("routes", []))
        ]
        if not routes:
            raise ValueError("HERE returned no traffic-aware route")
        return routes
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        raise TrafficDataUnavailable(
            "The real traffic service is temporarily unavailable. Try again later."
        ) from exc
