"""Deterministic, explicitly inferred traffic prediction views."""

from __future__ import annotations

from datetime import timedelta

from app.runtime_config import yangon_now
from services.traffic_service import TRAFFIC_ENGINE

PREDICTION_PERIODS = ("now", "plus_30", "plus_60", "evening_rush")


def prediction_time(period: str, now=None):
    current = yangon_now(now)
    if period == "now":
        return current
    if period == "plus_30":
        return current + timedelta(minutes=30)
    if period == "plus_60":
        return current + timedelta(hours=1)
    if period == "evening_rush":
        target = current.replace(hour=17, minute=30, second=0, microsecond=0)
        return target if target > current else target + timedelta(days=1)
    raise ValueError("Unknown prediction period.")


def predict_traffic(period: str, now=None, engine=None) -> dict:
    if period not in PREDICTION_PERIODS:
        raise ValueError("Prediction period must be now, plus_30, plus_60, or evening_rush.")
    engine = engine or TRAFFIC_ENGINE
    at = prediction_time(period, now)
    overview = engine.overview(at=at)
    hotspots = overview.get("hotspots", [])[:3]
    reasons = [f"Yangon time period: {str(overview['time_period']).replace('_', ' ').title()}"]
    if overview.get("rush_hour"):
        reasons.append("Rush-hour demand increases pressure on sensitive corridors")
    if hotspots:
        reasons.append(f"Highest inferred pressure: {hotspots[0]['road_name']}")
    return {
        "period": period,
        "forecast_for": at.isoformat(timespec="minutes"),
        "forecast_type": "INFERRED_FORECAST",
        "traffic_source": "INFERRED",
        "is_live": False,
        "time_period": overview["time_period"],
        "traffic_health_score": overview["traffic_health_score"],
        "traffic_health_label": overview["traffic_health_label"],
        "light_count": overview["light_count"],
        "moderate_count": overview["moderate_count"],
        "heavy_count": overview["heavy_count"],
        "average_traffic_score": overview["average_traffic_score"],
        "hotspots": hotspots,
        "reasons": reasons,
    }


def prediction_series(now=None, engine=None) -> dict:
    return {
        "source": "INFERRED",
        "forecast_type": "INFERRED_FORECAST",
        "timezone": "Asia/Yangon",
        "predictions": [predict_traffic(period, now=now, engine=engine) for period in PREDICTION_PERIODS],
    }
