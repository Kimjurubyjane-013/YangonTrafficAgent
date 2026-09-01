import json
from algorithms.graph import LOCATION_COORDS
from services.osrm_service import fetch_real_routes

start = LOCATION_COORDS["Hledan Centre"]
dest = LOCATION_COORDS["Junction Square"]

fwd = fetch_real_routes(start, dest)
print("\n--- Hledan -> JS ---")
for r in fwd:
    print(r["distance"], r["duration"], r["road_names"])

rev = fetch_real_routes(dest, start)
print("\n--- JS -> Hledan ---")
for r in rev:
    print(r["distance"], r["duration"], r["road_names"])
