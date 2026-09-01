import json
from algorithms.graph import LOCATION_COORDS
import services.osrm_service as osrm

start = LOCATION_COORDS["Junction Square"]
dest = LOCATION_COORDS["Hledan Centre"]

print("Calling _fetch_real_routes_uncached...")
res = osrm._fetch_real_routes_uncached(start, dest, 3)
for r in res:
    print(r["distance"], r["road_names"])
