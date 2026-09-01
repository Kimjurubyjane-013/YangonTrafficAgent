"""Timeout-bounded OSRM client with validated, diverse real-road alternatives."""
from __future__ import annotations

import math
import re
import time
from copy import deepcopy
from threading import RLock

import requests

OSRM_URLS = (
    "https://router.project-osrm.org/route/v1/driving",
    "https://routing.openstreetmap.de/routed-car/route/v1/driving",
)
VALHALLA_URL = "https://valhalla.openstreetmap.de/route"
MAX_GEOMETRY_OVERLAP = 0.92
NEAR_POINT_KM = 0.025
MAX_CORRIDOR_DISTANCE_RATIO = 1.65
MAX_CORRIDOR_DURATION_RATIO = 1.80
TARGET_ROUTE_COUNT = 3
CACHE_TTL_SECONDS = 600
DEFAULT_SEARCH_BUDGET_SECONDS = 6.5
_CACHE, _CACHE_LOCK = {}, RLock()
_REVERSE_CORRIDOR_CHECKED = set()


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
    alt_param = "true" if alternatives is True else "false" if alternatives is False else str(alternatives).lower()
    per_provider_timeout=max(0.65,float(timeout)/len(OSRM_URLS))
    for base_url in OSRM_URLS:
        try:
            response=requests.get(f"{base_url}/{coordinate_text}",params={
                "alternatives":alt_param,"steps":"true","overview":"full","geometries":"geojson"
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
    duration_seconds = float(route["duration"])
    return {"provider_id": provider_id, "distance": round(float(route["distance"])/1000, 2),
        "duration": round(duration_seconds/60, 2), "base_duration": round(duration_seconds/60, 2),
        "route_duration_seconds": round(duration_seconds), "base_duration_seconds": round(duration_seconds),
        "traffic_delay_seconds": None, "traffic_delay": None,
        "traffic_level": "Unavailable", "segment_traffic": ["Unavailable"],
        "traffic_data_available": False, "traffic_source": "Real-time provider unavailable",
        "provider": "OSRM/OpenStreetMap", "provider_timestamp": None,
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


def _corridor_hints(start_coord, destination_coord):
    """Return two generic side-corridor hints without claiming road geometry."""
    direct = _km(start_coord, destination_coord)
    if direct < 0.35:
        return []
    mid_lat = (start_coord[0] + destination_coord[0]) / 2
    mid_lon = (start_coord[1] + destination_coord[1]) / 2
    north = destination_coord[0] - start_coord[0]
    east = (destination_coord[1] - start_coord[1]) * math.cos(math.radians(mid_lat))
    length = max(1e-9, math.hypot(north, east))
    offset_km = min(1.4, max(0.3, direct * 0.18))
    lat_offset = (-east / length) * offset_km / 111.0
    lon_offset = (north / length) * offset_km / (111.0 * math.cos(math.radians(mid_lat)))
    return [
        (mid_lat + lat_offset, mid_lon + lon_offset),
        (mid_lat - lat_offset, mid_lon - lon_offset),
    ]


def _is_practical_corridor(candidate, primary, start_coord, destination_coord):
    geometry = candidate.get("geometry") or []
    if len(geometry) < 2:
        return False
    if _km(geometry[0], start_coord) > 0.2 or _km(geometry[-1], destination_coord) > 0.2:
        return False
    return (
        float(candidate["distance"]) <= float(primary["distance"]) * MAX_CORRIDOR_DISTANCE_RATIO + 1.5
        and float(candidate["duration"]) <= float(primary["duration"]) * MAX_CORRIDOR_DURATION_RATIO + 4.5
    )


def _fetch_real_routes_uncached(start_coord, destination_coord, alternatives=3, timeout=DEFAULT_SEARCH_BUDGET_SECONDS):
    deadline = time.monotonic() + max(2.0, float(timeout))
    native_timeout = min(3.2, max(1.4, float(timeout) * 0.45)) # Budget split
    
    # 1 & 2. Get forward and reverse natively
    try:
        fwd_raw = _request([start_coord, destination_coord], alternatives, native_timeout)
    except RoadRoutingUnavailable:
        try:
            remaining = max(0.8, deadline - time.monotonic())
            fwd_raw = [_request_valhalla([start_coord, destination_coord], remaining)]
        except RoadRoutingUnavailable:
            fwd_raw = []

    try:
        rev_raw = _request([destination_coord, start_coord], alternatives, native_timeout)
    except RoadRoutingUnavailable:
        rev_raw = []

    if not fwd_raw:
        raise RoadRoutingUnavailable("OSRM returned routes without usable geometry.")

    accepted = []
    for index, raw in enumerate(fwd_raw):
        source = "valhalla" if len(fwd_raw) == 1 and raw.get("_valhalla") else "osrm-native"
        record = _route_record(raw, index, "Fastest real-road corridor" if index == 0 else f"OSRM alternative {index}", source)
        if record and (not accepted or _is_diverse(record, accepted)):
            accepted.append(record)

    if not accepted:
        raise RoadRoutingUnavailable("OSRM returned routes without usable geometry.")
        
    target_count = min(TARGET_ROUTE_COUNT, max(1, int(alternatives)))
    
    # 3 & 4. Extract corridor signatures (midpoints) from BOTH sets
    midpoints = []
    for raw in fwd_raw + rev_raw:
        geom = raw.get("geometry", {}).get("coordinates", []) if isinstance(raw.get("geometry"), dict) else raw.get("geometry", [])
        if len(geom) < 3: continue
        
        # OSRM geojson is [lon, lat], but _request_valhalla is also mapped to [[lon, lat]... ] wait, _route_record flips it?
        # Let's extract midpoints from the raw geometry using the same format as _request expects (lat, lon)
        if isinstance(geom[0], list) and len(geom[0]) == 2:
            lon, lat = geom[len(geom)//2]
            midpoint = (lat, lon)
            
            # Ensure it's not basically the start/end point
            if _km(start_coord, midpoint) > 0.35 and _km(midpoint, destination_coord) > 0.35:
                # Ensure it's diverse from other midpoints
                if not any(_km(m, midpoint) < 0.25 for m in midpoints):
                    midpoints.append(midpoint)

    # Add the generic offset hints as fallbacks
    for hint in _corridor_hints(start_coord, destination_coord):
        if not any(_km(m, hint) < 0.25 for m in midpoints):
            midpoints.append(hint)

    # 5. Fresh-route A->B through the combined corridor hints
    primary = accepted[0]
    for midpoint in midpoints:
        if len(accepted) >= target_count or deadline - time.monotonic() < 0.7:
            break
        try:
            raw_routes = _request([start_coord, midpoint, destination_coord], False, min(1.4, max(0.7, deadline - time.monotonic())))
            record = _route_record(raw_routes[0], len(accepted), "Validated alternate corridor", "osrm-via-corridor")
        except (RoadRoutingUnavailable, IndexError, KeyError, TypeError, ValueError):
            continue
            
        if record and _is_practical_corridor(record, primary, start_coord, destination_coord) and _is_diverse(record, accepted):
            accepted.append(record)
            
    return accepted[:TARGET_ROUTE_COUNT]

def fetch_real_routes(start_coord,destination_coord,alternatives=3,timeout=DEFAULT_SEARCH_BUDGET_SECONDS):
    key=(tuple(start_coord),tuple(destination_coord),int(alternatives))
    now=time.monotonic()
    with _CACHE_LOCK:
        cached=_CACHE.get(key)
        routes = deepcopy(cached[1]) if cached and now-cached[0]<CACHE_TTL_SECONDS else None
    if routes is None:
        routes=_fetch_real_routes_uncached(start_coord,destination_coord,alternatives,timeout)
    with _CACHE_LOCK: _CACHE[key]=(time.monotonic(),deepcopy(routes))
    return routes
