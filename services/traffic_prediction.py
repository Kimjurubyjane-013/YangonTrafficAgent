"""Deterministic, explicitly inferred traffic prediction views."""

from __future__ import annotations

from datetime import timedelta

from app.runtime_config import yangon_now
from services.traffic_service import TRAFFIC_ENGINE
from services.traffic_service import classify_traffic
from app.traffic_config import TRAFFIC_SPEED_MULTIPLIERS

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


def predict_route_traffic(route: dict, period: str, now=None, engine=None) -> dict:
    """Project a selected route using the change in city traffic pressure.

    This preserves the route geometry and ranking.  The route score moves by the
    same number of points as the deterministic city average, and ETA changes by
    the documented speed-multiplier ratio for the resulting severity band.
    """
    if period not in PREDICTION_PERIODS:
        raise ValueError("Prediction period must be now, plus_30, plus_60, or evening_rush.")
    if not isinstance(route, dict):
        raise ValueError("A selected route is required.")
    try:
        current_eta = max(0.0, float(route.get("time")))
        level_score = {"light": 25.0, "moderate": 52.5, "heavy": 82.5}
        fallback_score = level_score.get(str(route.get("traffic", "")).casefold(), 50.0)
        current_score = max(0.0, min(100.0, float(route.get("traffic_score", fallback_score))))
    except (TypeError, ValueError):
        raise ValueError("The selected route does not contain valid traffic and ETA values.")

    engine = engine or TRAFFIC_ENGINE
    current = predict_traffic("now", now=now, engine=engine)
    future = predict_traffic(period, now=now, engine=engine)
    projected_score = max(0.0, min(100.0, current_score + future["average_traffic_score"] - current["average_traffic_score"]))
    current_level = classify_traffic(current_score)
    expected_level = classify_traffic(projected_score)
    current_speed = TRAFFIC_SPEED_MULTIPLIERS[current_level]
    expected_speed = TRAFFIC_SPEED_MULTIPLIERS[expected_level]
    estimated_eta = current_eta if period == "now" else current_eta * current_speed / expected_speed
    current_delay = max(0.0, float(route.get("traffic_delay") or 0.0))
    free_flow_eta = float(route.get("free_flow_eta") or max(0.0, current_eta - current_delay) or current_eta)
    delay = max(0.0, estimated_eta - free_flow_eta)

    reason = "Current conditions along this route"
    if period != "now":
        if future.get("rush_hour") or "rush" in str(future.get("time_period", "")).lower():
            reason = "Higher demand is expected during the rush-hour period"
        elif projected_score < current_score - 5:
            reason = "Traffic is expected to ease during this period"
        elif projected_score > current_score + 5:
            reason = "Traffic is expected to build during this period"
        else:
            reason = "Conditions are expected to remain steady"
    return {
        "period": str(period),
        "traffic": str(expected_level),
        "estimated_eta": round(float(estimated_eta), 2),
        "expected_delay": round(float(delay), 2),
        "reason": str(reason),
        "traffic_source": "INFERRED",
        "forecast_type": "CURRENT_ROUTE" if period == "now" else "INFERRED_ROUTE_FORECAST",
        "is_live": False,
    }
