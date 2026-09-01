import json
from algorithms.graph import LOCATION_COORDS
from services.osrm_service import fetch_real_routes

start = LOCATION_COORDS["Hledan Centre"]
dest = LOCATION_COORDS["Junction Square"]

routes = fetch_real_routes(start, dest, alternatives=3, timeout=10)
print(f"Hledan -> Junction Square: {len(routes)} routes")
for idx, r in enumerate(routes):
    print(f"  {idx}: {r['distance']}km, {r['duration']}min, {r['road_names']}")

routes_rev = fetch_real_routes(dest, start, alternatives=3, timeout=10)
print(f"Junction Square -> Hledan: {len(routes_rev)} routes")
for idx, r in enumerate(routes_rev):
    print(f"  {idx}: {r['distance']}km, {r['duration']}min, {r['road_names']}")
