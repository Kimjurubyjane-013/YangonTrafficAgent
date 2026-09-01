# Yangon Traffic Intelligence

Yangon Traffic Intelligence is an explainable route-planning and city-traffic analysis project. It combines real OpenStreetMap road geometry, optional HERE traffic observations, a deterministic traffic-inference model, numeric route ranking, and SWI-Prolog rules. The same application logic serves the pywebview desktop client and FastAPI web deployment.

## Capabilities

- Finds provider-validated road routes between verified Yangon landmarks.
- Requests directional alternatives and rejects duplicate or materially identical geometry.
- Ranks routes by traffic-adjusted ETA, severe congestion exposure, vehicle suitability, distance, and rule preferences.
- Supports Car, Bus, Taxi, Ambulance, Fire Truck, and Police profiles.
- Shows Light, Moderate, and Heavy consistently on route lines, cards, legends, analysis, and navigation.
- Provides Current, Off-Peak, Peak-Hour, closure, and emergency scenarios without presenting hypothetical output as live telemetry.
- Exposes a city dashboard using the same cached traffic snapshot as routing.
- Shows cached live Yangon weather from Open-Meteo with a separate rule-based traffic-risk interpretation.
- Explains recommendations without using an LLM for the core decision.

## Architecture

```text
Desktop:  main.py -> app.startup -> pywebview -> Api -> RouteService
Web:      web_api.py -> FastAPI -> Api -> RouteService
Routing:  RouteService -> real_world_agent -> OSRM/HERE road providers
Traffic:  traffic_backend -> HERE observations or traffic_service inference
Weather:  weather_service -> Open-Meteo -> normalized cached Yangon observation
Decision: RouteDecisionEngine -> SWI-Prolog, with deterministic Python fallback
UI:       app.html + styles.css + app.js + api.js + state.js
          + dashboard.js + simulation3d.js + traffic-colors.js
```

Canonical landmark and modeled-road data live in `data/locations.json` and `data/roads.json`. `algorithms.graph` and `algorithms.road_metadata` are derived compatibility views, not separate sources.

Every successful option follows one contract. Important fields include `route_id`, `route_type`, `geometry`, `traffic_geometry`, `major_roads`, `distance_km`, `free_flow_eta`, `traffic_adjusted_eta`, second-based ETA aliases, `traffic_delay`, segment traffic/source arrays, provider coverage, decision score, recommendation reason, and a backend-generated comparison to the recommended route.

## Traffic truth model

The interface distinguishes evidence instead of silently substituting sources:

- **HERE**: provider-backed traffic evidence is available.
- **Inferred**: deterministic estimate using road metadata, Yangon time, context, and scenario.
- **Mixed**: the route contains provider-backed and inferred segments.
- **Unknown**: neither provider evidence nor a valid estimate is available.

`TRAFFIC_MODE` controls behavior:

- `real`: provider evidence when available, with truthful missing-evidence states.
- `simulation`: deterministic inferred data for demonstrations and tests.
- `real_with_simulation_fallback`: provider first, then visibly labelled inference.

The application remains usable without a HERE key: OSRM supplies real mapped-road geometry and the model supplies clearly labelled estimates. Missing optional credentials never crash startup.

## Weather intelligence

`services/weather_service.py` retrieves the following Open-Meteo current fields for Yangon: temperature, relative humidity, precipitation, rain, 10-metre wind speed, WMO weather code, and observation time. The request explicitly uses `Asia/Yangon`; normalized timestamps include Myanmar's UTC+06:30 offset. Valid observations are cached for ten minutes and provider calls have a four-second timeout.

`GET /api/weather` returns one normalized snapshot used by the Dashboard and Route Planner. If Open-Meteo times out or returns malformed data, the endpoint returns a structured unavailable state and the rest of the application continues normally. No fallback weather value is invented.

Weather observation and traffic interpretation are intentionally separate:

```text
LIVE / Open-Meteo observation
        -> conservative weather classification
        -> INFERRED / RULE-BASED traffic-risk fact
        -> Prolog or deterministic Python rule evaluation
```

Clear/normal weather maps to `clear`; rain, drizzle, fog, or wet conditions map to `rain`; thunderstorm, at least 7.5 mm current precipitation, or at least 50 km/h wind maps to `storm`. These are transparent project rules, not a claim that Open-Meteo measured traffic. Weather adds only a small bounded rule cost (maximum `0.6`) and a fired-rule explanation. It does not apply an undocumented congestion percentage or change traffic provenance.

**Real weather is not real traffic. Inferred traffic is not provider-measured traffic.**

### Deterministic model

Snapshots use `Asia/Yangon` time, a 15-minute bucket, traffic mode, and scenario in their cache identity. Time periods are early morning, morning rush, daytime, evening rush, and night. Off-Peak and Peak are explicit hypothetical scenarios with separate snapshot identities.

The model computes density from base congestion, road-type-sensitive time effects, context, capacity pressure, and seeded local variation. The centralized score configuration is in `app/traffic_config.py`:

```text
raw_score = 0.30 * base_congestion
          + 0.22 * vehicle_density
          + 0.10 * normalized_pressure
          + bounded_overload
          + time_effect + context_effect + road_type_effect

traffic_score = clamp(0, 100, 50 + 1.40 * (raw_score - 50))
```

Public classification is Light (`0-35`), Moderate (`36-70`), or Heavy (`71-100`). Route traffic is distance-weighted from segments. Average speed uses centralized factors `0.90`, `0.65`, and `0.40` with a 4 km/h floor. Delay is exact and nonnegative:

```text
traffic_delay = max(0, traffic_adjusted_eta - free_flow_eta)
```

## Routing and decision logic

OSRM/OpenStreetMap supplies mapped geometry and directional alternatives. HERE routing can provide traffic-aware duration when configured. Alternatives must be geometrically distinct; the application never fabricates one merely to fill the panel.

Provider road duration is authoritative for motor vehicles. Transparent vehicle profiles then apply operating differences, so a Bus is slower than a Car and emergency vehicles can be faster. Walking and Bicycle retain physical speed floors internally, although the UI exposes the six motor profiles above.

The lower-is-better score in `services/route_ranking.py` is:

```text
route_cost = traffic_adjusted_eta
           + severe_congestion_exposure
           + min(0.50, 0.08 * traffic_delay)
           + min(0.50, 0.002 * cumulative_traffic_impact)
           + 0.20 * vehicle_restriction_penalty
           + min(0.60, 0.05 * weather_rule_penalty)
           + 0.02 * distance_km
           + bounded_preferred_road_adjustment
```

Severe-congestion weights are smaller for emergency vehicles. A dominance guard prevents a route that is both slower and longer from winning unless it has a documented material traffic/safety advantage. Ties are deterministic.

SWI-Prolog evaluates eligibility, restrictions, suitability, penalties, and reasons. Request facts are allowlisted and cleared after evaluation. If SWI-Prolog or PySwip is unavailable, the engine reports `python-fallback` and uses the same deterministic scoring contract; it never claims Prolog was used.

## Run locally

### Web

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn web_api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`; API documentation is at `/docs`.

### Desktop

```powershell
python -m venv .venv-desktop
.\.venv-desktop\Scripts\Activate.ps1
python -m pip install -r requirements-desktop.txt
python main.py
```

Desktop startup is guarded by `if __name__ == "__main__"`; importing FastAPI never creates a window or requires a graphical display.

### Optional settings

Use server/deployment environment variables; never put provider keys in frontend code.

```text
HERE_API_KEY=optional-server-side-key
TRAFFIC_MODE=real_with_simulation_fallback
TRAFFIC_CACHE_SECONDS=60
APP_TIMEZONE=Asia/Yangon
```

For Prolog mode, install SWI-Prolog and `pyswip`, then confirm `swipl --version`. Otherwise deterministic fallback is automatic and non-fatal.

## HTTP API

- `GET /health` and `GET /api/health`
- `GET /api/locations`, `/api/vehicles`, and `/api/graph`
- `GET /api/traffic`
- `GET /api/traffic/hotspots?limit=8`
- `GET /api/traffic/best-flowing?limit=8`
- `GET /api/traffic/{road_id}`
- `GET /api/weather`
- `POST /api/route`

Inputs are validated server-side. Errors use structured codes and user-safe messages.

## Deployment

### Railway

`railway.json` starts the real ASGI entry point on Railway's assigned port:

```text
uvicorn web_api:app --host 0.0.0.0 --port $PORT
```

The health probe is `/health`. Remove any stale dashboard override such as `main:app`; `main.py` is desktop-only.

### Vercel

Import the repository with Framework Preset **Other**. `vercel.json` sends API requests to `web_api.py` and static assets to `web/`. Vercel generally lacks native SWI-Prolog, so it truthfully reports `python-fallback`. Add `HERE_API_KEY` only as a server-side environment variable if provider traffic is required.

## Verification

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q .
node --check web/app.js
node --check web/api.js
node --check web/state.js
node --check web/dashboard.js
node --check web/simulation3d.js
```

Tests cover graph validation, provider routing/deduplication, traffic calibration/scenarios, all vehicles, ranking/dominance, Prolog/fallback, API serialization, evidence truthfulness, colors, simulation lifecycle contracts, deployment entry points, and repeated calls without fact leakage.

## Demonstration flow

1. Choose a vehicle and locations in **Route Planner**.
2. Open the command-center Dashboard to inspect the real network map, severity distribution, evidence coverage, and live Yangon weather.
3. Find a Current route and inspect segment colors, evidence labels, and the shared weather rule.
4. Select an alternative and verify map, card, ETA, and comparison update together.
5. Compare Off-Peak and Peak-Hour snapshots.
6. Open **Route Analysis** for the Input â†’ Traffic â†’ Weather â†’ Rules â†’ Decision explanation.
7. Start navigation, pause/restart it, and confirm the vehicle follows selected mapped geometry and segment traffic.

## Limitations

- Public routing and optional traffic providers need network access and may rate-limit or time out.
- Open-Meteo requires internet access; weather failure is isolated and never fabricates observations.
- Provider coverage is not guaranteed on every Yangon road; Mixed and Inferred labels are intentional.
- The deterministic model is an explainable university-project estimate, not transport-authority telemetry or safety-critical navigation.
- Closure matching uses English provider road names and reports when no candidate matched.
- ETA is an estimate, not a live-arrival guarantee.
- Procedural visual elements are illustrative and do not claim building-level geographic accuracy.
