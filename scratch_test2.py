import json
import time
from algorithms.graph import LOCATION_COORDS
from services.osrm_service import _fetch_real_routes_uncached, _corridor_hints, _request, _route_record, _is_practical_corridor, _is_diverse, _km

start = LOCATION_COORDS["Hledan Centre"]
dest = LOCATION_COORDS["Junction Square"]

routes = _fetch_real_routes_uncached(start, dest, alternatives=3, timeout=10)
print(f"Accepted: {len(routes)}")

# Debug discover:
deadline = time.monotonic() + 10
hints = _corridor_hints(start, dest)
print(f"Hints: {hints}")
primary = routes[0]
for idx, hint in enumerate(hints):
    raw_routes = _request([start, hint, dest], False, 5)
    rec = _route_record(raw_routes[0], 1, "test", "test")
    print(f"Hint {idx} distance: {rec['distance']} (max {primary['distance']*1.65})")
    print(f"Hint {idx} duration: {rec['duration']} (max {primary['duration']*1.80})")
    
    start_dist = _km(rec['geometry'][0], start)
    end_dist = _km(rec['geometry'][-1], dest)
    print(f"Start dist: {start_dist}, End dist: {end_dist}")
    
    practical = _is_practical_corridor(rec, primary, start, dest)
    diverse = _is_diverse(rec, routes)
    print(f"Practical: {practical}, Diverse: {diverse}")

