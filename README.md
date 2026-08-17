# Yangon Smart Traffic Management Agent

An AI-based Traffic Management Agent developed using Python and Prolog.

## Technologies

- Python
- SWI-Prolog
- pywebview
- Leaflet
- Three.js

## Team

University AI Agent Project

## Run

```powershell
cd "C:\Users\Lenovo\Documents\Codex\YangonTrafficAgent"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Route intelligence demonstrations

Open **Journey conditions** in the route planner to compare normal, peak-hour,
major-incident, road-closure, and emergency-response scenarios. Road closures
are matched only against English road names returned by the real-road provider;
the app explicitly says when no match was found instead of claiming a reroute.

After a route search, **View decision evaluation** shows candidate counts, the
decision engine, response time, closure evidence, and each option's score. The
deterministic ranking formula is:

`distance_km + (0.35 × estimated_minutes) + rule_penalty`

The live road geometry and alternatives still depend on the configured public
OSRM/Valhalla services. Condition-specific saved routes can be used when the
same request is temporarily offline; a normal cached route is never reused for
a road-closure scenario.

The active desktop entry point is `main.py`; window configuration lives in
`app/config.py`, startup in `app/startup.py`, validation and serialization in
`app/`, route orchestration in `services/route_service.py`, and real-road
routing in `services/osrm_service.py`. Browser responsibilities are separated
between `web/state.js`, `web/api.js`, `web/app.js`, `web/simulation3d.js`, and
the compatibility map controller still hosted in `web/app.html`.

Run checks with:

```powershell
python -m unittest -v test_architecture.py test_real_world_agent.py test_route_decision.py
node --check web\state.js
node --check web\api.js
node --check web\app.js
node --check web\simulation3d.js
```

## Hybrid route-decision engine

The active application uses a **real-world-only** route pipeline. Saved Yangon
places supply start/end coordinates, while OSRM generates alternative routes
from the OpenStreetMap road network. The local graph is retained for legacy
algorithm exercises/tests but is not used to invent UI route alternatives.
Every OSRM candidate includes its exact geometry, distance, duration, and road
names; that same geometry drives Leaflet and the Three.js simulation.

Native alternatives are de-duplicated by geometry. If OSRM supplies only one
meaningfully different route, the provider requests bounded north/south/east/
west via-corridor routes that OSRM snaps to mapped roads. Candidates exceeding
1.75× distance, 1.85× duration, or 90% geometry overlap are rejected. The app
does not fabricate an alternative when the road network has no safe, distinct
option.

An internet connection to `router.project-osrm.org` is required. The app reports
a routing-service error instead of silently substituting artificial graph paths.

Python generates at most 24 loop-free candidate paths (maximum depth 8), then
calculates distance and traffic-adjusted travel time. SWI-Prolog evaluates
one-way rules, prohibited vehicle/road combinations, congestion, peak time,
weather, incidents, heavy-vehicle suitability, and preferred roads.

The deterministic ranking formula is:

```text
total_score = 1.00 * distance_km
            + 0.35 * estimated_minutes
            + congestion_penalty
            + vehicle_restriction_penalty
            + time_penalty
            + weather_penalty
            + incident_penalty
            + preferred_road_adjustment
```

Lower scores win. Ties are resolved by distance, estimated time, then the
lexicographic route node sequence. Invalid candidates are excluded.

### SWI-Prolog setup

1. Install 64-bit SWI-Prolog from https://www.swi-prolog.org/download/stable.
2. Ensure `swipl` is available on `PATH` and its architecture matches Python.
3. Run `pip install -r requirements.txt` to install PySwip.
4. Start the application normally with `python main.py`; no separate Prolog
   server is required.

If SWI-Prolog or PySwip cannot load, the application remains usable and reports
`python-fallback`. The fallback implements the same restrictions, penalties,
formula, explanation fields, and deterministic ordering.

The rule base is `prolog/traffic_rules.pl`. Request facts are allowlisted,
serialized only from normalized internal values, guarded by a lock, and removed
after every evaluation to prevent cross-request state leakage.
