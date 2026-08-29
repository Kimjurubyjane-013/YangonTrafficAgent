"""HTTP entry point for browser and Vercel deployments.

The desktop entry point remains ``main.py``. This module only adapts the
existing application facade to HTTP; route calculation stays in RouteService.
"""
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api import Api


PROJECT_ROOT = Path(__file__).resolve().parent
WEB_ROOT = PROJECT_ROOT / "web"

app = FastAPI(title="Yangon Traffic Agent API", version="1.0.0")
application_api = Api()


class RoutePayload(BaseModel):
    vehicle: Any = None
    start: Any = None
    destination: Any = None
    conditions: Any = None


@app.get("/api/health")
def api_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health", include_in_schema=False)
def railway_health() -> dict[str, str]:
    """Lightweight root probe used by Railway without touching the GUI."""
    return {"status": "ok", "service": "Yangon Traffic Intelligence"}


@app.get("/api/locations")
def locations() -> list[str]:
    return application_api.get_locations()


@app.get("/api/vehicles")
def vehicles() -> list[str]:
    return application_api.get_vehicles()


@app.get("/api/graph")
def graph() -> dict[str, Any]:
    return application_api.get_graph_data()


@app.get("/api/traffic")
def traffic_overview(refresh: bool = False):
    result = application_api.get_traffic_overview(refresh)
    if result.get("error"):
        return JSONResponse(status_code=503, content=result)
    return result


@app.get("/api/traffic/hotspots")
def traffic_hotspots(limit: int = 8):
    result = application_api.get_congestion_hotspots(limit)
    return JSONResponse(status_code=503, content=result) if result.get("error") else result


@app.get("/api/traffic/best-flowing")
def best_flowing_roads(limit: int = 8):
    result = application_api.get_best_flowing_roads(limit)
    return JSONResponse(status_code=503, content=result) if result.get("error") else result


@app.get("/api/traffic/{road_id}")
def road_traffic(road_id: str):
    result = application_api.get_road_traffic(road_id)
    if not result.get("error"):
        return result
    code = result.get("error_details", {}).get("code")
    return JSONResponse(status_code=404 if code == "unknown_road" else 400, content=result)


@app.post("/api/route")
def route(payload: RoutePayload):
    result = application_api.find_route(
        payload.vehicle,
        payload.start,
        payload.destination,
        payload.conditions,
    )
    if not result.get("error"):
        return result

    code = result.get("error_details", {}).get("code", "routing_error")
    if code in {
        "invalid_type", "unknown_vehicle", "unknown_location", "same_location",
        "invalid_conditions", "invalid_closed_road",
    }:
        status = 400
    elif code == "internal_error":
        status = 500
    else:
        status = 503
    return JSONResponse(status_code=status, content=result)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "app.html")


# Defined last so explicit /api routes always win over static-file handling.
app.mount("/", StaticFiles(directory=WEB_ROOT), name="web")
