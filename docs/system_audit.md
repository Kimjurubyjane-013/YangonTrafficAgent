# Yangon Traffic Intelligence — System Audit

Baseline: `8cb7384` (`main`, synchronized with `origin/main`).

## Runtime entry points

- Desktop: `python main.py` → `app.startup.run()` → pywebview. GUI startup is guarded.
- Production: `uvicorn web_api:app --host 0.0.0.0 --port $PORT`.
- Browser/desktop contract: `Api` in `api.py`; HTTP and pywebview use the same facade.

## Route data flow

User request → validation → `RouteService` → real-road provider (HERE when configured,
otherwise OSRM) → deterministic segment traffic inference/fusion → Prolog policy
evaluation (or explicit Python fallback) → numeric dominance/ranking → normalized
serialization → Leaflet route rendering and the selected-route simulation.

## Data ownership

- Location/road graph: `data/*.json`, loaded by graph and road-repository modules.
- Real geometry: routing provider responses; reverse geometry is never synthesized.
- Traffic severity: provider evidence where present, otherwise deterministic academic
  inference using Asia/Yangon time and road context.
- Eligibility/policy: `prolog/traffic_rules.pl`; Python fallback uses the same contract.
- Ranking: Python numeric ranking in `services/route_ranking.py`; ETA is dominant and
  dominated slower-and-longer routes cannot win without a meaningful advantage.

## Baseline verification

- Pytest: 108 passed, 2 skipped, 10 subtests passed.
- Python: all source files compiled with `py_compile`.
- JavaScript: every `.js` file and both inline scripts parsed successfully.
- Prolog: both knowledge bases loaded successfully with SWI-Prolog.
- Deployment: Railway targets `web_api:app`; Vercel targets the same FastAPI module.

## Audit findings

1. The route result already carries most normalized ETA, traffic, provenance, geometry,
   decision, and segment fields, but comparison labels and confidence are absent.
2. Peak/off-peak and closure controls exist, but there is no explicit deterministic
   prediction contract for Now, +30 min, +1 hour, and Evening Rush.
3. Incident/weather inputs exist at rule level, but no complete before/after scenario
   response contract is exposed.
4. Prolog rule identifiers are returned, but the normal explanation flow does not yet
   present a concise input → analysis → rules → decision structure.
5. Dashboard analytics are calculable and restrained; no fake CCTV/incidents/weather
   are present in this baseline.
6. Route Planner logic remains concentrated in a large inline script in `app.html`.
   Extraction should be incremental because the existing no-build pywebview packaging
   and tests depend on its global functions.
7. ETA and traffic-delay calculation is backend-owned. Frontend formatting should
   continue consuming these values and must not introduce independent ranking logic.
