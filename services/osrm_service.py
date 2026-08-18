"""Timeout-bounded OSRM client with validated, diverse real-road alternatives."""
from __future__ import annotations

import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from threading import RLock

import requests

OSRM_URLS = (
    "https://router.project-osrm.org/route/v1/driving",
    "https://routing.openstreetmap.de/routed-car/route/v1/driving",
)
VALHALLA_URL = "https://valhalla.openstreetmap.de/route"
MAX_DETOUR_DISTANCE_RATIO = 1.75
MAX_DETOUR_DURATION_RATIO = 1.85
MAX_GEOMETRY_OVERLAP = 0.92
NEAR_POINT_KM = 0.025
TARGET_ROUTE_COUNT = 3
CACHE_TTL_SECONDS = 600
DEFAULT_SEARCH_BUDGET_SECONDS = 6.5
_CACHE, _CACHE_LOCK = {}, RLock()


class RoadRoutingUnavailable(RuntimeError):
    pass


def _decode_polyline6(encoded):
    coordinates=[]; index=0; latitude=0; longitude=0
    while index < len(encoded):
        values=[]
        for _ in range(2):
            result=0; shift=0
            while True:
                if index >= len(encoded): raise ValueError("Incomplete encoded route shape")
                byte=ord(encoded[index])-63; index+=1
                result |= (byte & 0x1F) << shift; shift += 5
                if byte < 0x20: break
            values.append(~(result >> 1) if result & 1 else result >> 1)
        latitude += values[0]; longitude += values[1]
        coordinates.append([latitude/1_000_000,longitude/1_000_000])
    return coordinates


def _request_valhalla(coordinates, timeout):
    payload={"locations":[{"lat":lat,"lon":lon} for lat,lon in coordinates],
        "costing":"auto","units":"kilometers","directions_options":{"units":"kilometers"}}
    try:
        response=requests.post(VALHALLA_URL,json=payload,timeout=max(0.8,float(timeout)))
        response.raise_for_status(); trip=response.json().get("trip",{})
        summary=trip.get("summary",{}); geometry=[]; steps=[]
        for leg in trip.get("legs",[]):
            shape=_decode_polyline6(leg.get("shape", ""))
            if geometry and shape: shape=shape[1:]
            geometry.extend(shape)
            for maneuver in leg.get("maneuvers",[]):
                names=maneuver.get("street_names") or []
                if names: steps.append({"name":names[0]})
        if len(geometry)<2: raise ValueError("Valhalla returned no usable geometry")
        return {"_valhalla":True,"distance":float(summary["length"])*1000,"duration":float(summary["time"]),
            "geometry":{"coordinates":[[lon,lat] for lat,lon in geometry]},"legs":[{"steps":steps}]}
    except (requests.RequestException,ValueError,KeyError,TypeError):
        raise RoadRoutingUnavailable("The real-road services are temporarily unavailable. Check your connection and try again.")


def _english_road_names(route):
    names, seen = [], set()
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            raw = str(step.get("name") or step.get("ref") or "").strip()
            english = raw.encode("ascii", "ignore").decode("ascii")
            english = re.sub(r"\s*[-|/]+\s*", " ", english)
            english = re.sub(r"\s+", " ", english).strip(" ,.-")
            if not re.search(r"[A-Za-z]", english):
                continue
            canonical = re.sub(r"\brd\b", "road", english.casefold())
            canonical = re.sub(r"\bst\b", "street", canonical)
            canonical = re.sub(r"\bave\b", "avenue", canonical)
            canonical = re.sub(r"\bblvd\b", "boulevard", canonical)
            key = re.sub(r"[^a-z0-9]", "", canonical)
            if key and key not in seen:
                seen.add(key); names.append(english)
    return names[:3]


def _request(coordinates, alternatives, timeout):
    coordinate_text = ";".join(f"{lon},{lat}" for lat, lon in coordinates)
    per_provider_timeout=max(0.65,float(timeout)/len(OSRM_URLS))
    for base_url in OSRM_URLS:
        try:
            response=requests.get(f"{base_url}/{coordinate_text}",params={
                "alternatives":alternatives,"steps":"true","overview":"full","geometries":"geojson"
            },timeout=per_provider_timeout)
            response.raise_for_status(); payload=response.json()
            if payload.get("code")=="Ok" and payload.get("routes"):
                return payload["routes"]
        except (requests.RequestException,ValueError):
            continue
    raise RoadRoutingUnavailable("The real-road service is temporarily unavailable. Check your internet connection and try again.")


def _route_record(route, provider_id, variant_label, source):
    geometry = route.get("geometry", {}).get("coordinates", [])
    if len(geometry) < 2:
        return None
    return {"provider_id": provider_id, "distance": round(float(route["distance"])/1000, 2),
        "duration": round(float(route["duration"])/60, 2),
        "geometry": [[lat,lon] for lon,lat in geometry], "road_names": _english_road_names(route),
        "variant_label": variant_label, "source": source}


def _km(a, b):
    lat = math.radians((a[0]+b[0])/2)
    return math.hypot((a[0]-b[0])*111.0, (a[1]-b[1])*111.0*math.cos(lat))


def _sample(points, count=24):
    if len(points) <= count: return points
    return [points[round(i*(len(points)-1)/(count-1))] for i in range(count)]


def _overlap(a, b):
    samples = _sample(a)
    close = sum(1 for point in samples if min(_km(point, other) for other in _sample(b, 40)) <= NEAR_POINT_KM)
    return close / max(1, len(samples))


def _road_signature(route):
    signature=[]
    for name in route.get("road_names", []):
        normalized=name.casefold()
        normalized=re.sub(r"\brd\b", "road", normalized)
        normalized=re.sub(r"\bst\b", "street", normalized)
        normalized=re.sub(r"\bave\b", "avenue", normalized)
        key=re.sub(r"[^a-z0-9]", "", normalized)
        if key and key not in signature: signature.append(key)
    return tuple(signature)


def _is_diverse(candidate, accepted):
    candidate_signature=_road_signature(candidate)
    for route in accepted:
        # If both cards would show the same road sequence, presenting one as an
        # alternative is misleading even when the provider geometry has a
        # small different connector or GPS-level variation.
        if candidate_signature and candidate_signature == _road_signature(route):
            return False
        forward=_overlap(candidate["geometry"],route["geometry"])
        reverse=_overlap(route["geometry"],candidate["geometry"])
        # Both routes naturally share their endpoints. Requiring high overlap
        # in both directions avoids rejecting a different middle corridor just
        # because the shorter route's endpoints lie on the longer route.
        if min(forward,reverse) >= MAX_GEOMETRY_OVERLAP:
            return False
    return True


def _corridor_points(start, destination):
    mid_lat=(start[0]+destination[0])/2; mid_lon=(start[1]+destination[1])/2
    cos_lat=max(0.2,math.cos(math.radians(mid_lat)))
    north=destination[0]-start[0]; east=(destination[1]-start[1])*cos_lat
    length=max(1e-9,math.hypot(north,east)); straight_km=_km(start,destination)
    # Short urban journeys need nearby parallel streets, not a waypoint more
    # than half a kilometre away. Longer journeys can use wider corridors.
    offset_km=min(1.4,max(0.10,straight_km*0.20)); degrees=offset_km/111
    perp_lat=east/length; perp_lon=-north/(length*cos_lat)
    variants=[]
    for sign in (1,-1):
        for scale in (1.0,1.45):
            via=(mid_lat+sign*perp_lat*degrees*scale,mid_lon+sign*perp_lon*degrees*scale)
            delta_lat=via[0]-mid_lat; delta_east=(via[1]-mid_lon)*cos_lat
            if abs(delta_lat)>=abs(delta_east): direction="Northern" if delta_lat>0 else "Southern"
            else: direction="Eastern" if delta_east>0 else "Western"
            descriptor=f"{direction} road corridor" if scale==1.0 else f"Outer {direction.lower()} road corridor"
            variants.append((via,descriptor))
    return variants


def _detour_limits(primary_distance):
    if primary_distance < 1.0:
        return 3.5, 3.5
    if primary_distance < 3.0:
        return 2.4, 2.6
    return MAX_DETOUR_DISTANCE_RATIO, MAX_DETOUR_DURATION_RATIO


def _fetch_real_routes_uncached(start_coord, destination_coord, alternatives=3, timeout=DEFAULT_SEARCH_BUDGET_SECONDS):
    deadline = time.monotonic() + max(2.0, float(timeout))
    native_timeout = min(3.2, max(1.4, float(timeout) * 0.68))
    try:
        native = _request([start_coord,destination_coord], alternatives, native_timeout)
    except RoadRoutingUnavailable:
        remaining=max(0.8,deadline-time.monotonic())
        native=[_request_valhalla([start_coord,destination_coord],remaining)]
    accepted=[]
    for index, raw in enumerate(native):
        source="valhalla" if len(native)==1 and raw.get("_valhalla") else "osrm-native"
        record=_route_record(raw,index,"Fastest real-road corridor" if index==0 else f"OSRM alternative {index}",source)
        if record and (not accepted or _is_diverse(record,accepted)):
            accepted.append(record)
    if not accepted:
        raise RoadRoutingUnavailable("OSRM returned routes without usable geometry.")

    primary=accepted[0]
    if len(accepted)<TARGET_ROUTE_COUNT:
        remaining = max(0.7, deadline - time.monotonic())
        # One corridor on each side is more reliable with public services than
        # four simultaneous requests, which commonly trigger throttling.
        all_corridors = _corridor_points(start_coord,destination_coord)
        corridors = [all_corridors[0], all_corridors[2]]
        distance_ratio, duration_ratio = _detour_limits(primary["distance"])
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures={pool.submit(_request,[start_coord,via,destination_coord],False,remaining):(label,via)
                for via,label in corridors}
            for future in as_completed(futures):
                if len(accepted)>=TARGET_ROUTE_COUNT: break
                label,_=futures[future]
                try: raw=future.result()[0]; record=_route_record(raw,len(accepted),label,"osrm-via-corridor")
                except (RoadRoutingUnavailable,IndexError): continue
                if not record: continue
                if record["distance"]>primary["distance"]*distance_ratio: continue
                if record["duration"]>primary["duration"]*duration_ratio: continue
                if _is_diverse(record,accepted): accepted.append(record)
    return accepted[:TARGET_ROUTE_COUNT]


def fetch_real_routes(start_coord,destination_coord,alternatives=3,timeout=DEFAULT_SEARCH_BUDGET_SECONDS):
    key=(tuple(start_coord),tuple(destination_coord),int(alternatives))
    now=time.monotonic()
    with _CACHE_LOCK:
        cached=_CACHE.get(key)
        if cached and now-cached[0]<CACHE_TTL_SECONDS: return deepcopy(cached[1])
    routes=_fetch_real_routes_uncached(start_coord,destination_coord,alternatives,timeout)
    with _CACHE_LOCK: _CACHE[key]=(time.monotonic(),deepcopy(routes))
    return routes
