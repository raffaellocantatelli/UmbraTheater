from __future__ import annotations

import math
from datetime import datetime, timezone

import httpx

from .cache import cache
from .settings import settings

USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
CELESTRAK = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=json"
OPENSKY = "https://opensky-network.org/api/states/all"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _get_json(url: str, *, headers: dict | None = None, params: dict | None = None, timeout: float = 20.0):
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url, headers=headers, params=params)
        r.raise_for_status()
        return r.json()


async def earthquakes() -> dict:
    cached = cache.get("eq")
    if cached:
        return cached
    raw = await _get_json(USGS)
    features = []
    for f in raw.get("features", [])[:250]:
        props = f.get("properties") or {}
        geom = f.get("geometry") or {}
        coords = geom.get("coordinates") or [None, None, None]
        features.append(
            {
                "id": f.get("id"),
                "mag": props.get("mag"),
                "place": props.get("place"),
                "time": props.get("time"),
                "url": props.get("url"),
                "lon": coords[0],
                "lat": coords[1],
                "depth_km": coords[2],
            }
        )
    payload = {"updated": _now_iso(), "count": len(features), "items": features}
    cache.set("eq", payload, settings.cache_ttl_seconds)
    return payload


def _tle_to_approx_latlon(incl_deg: float, raan_deg: float, mean_anomaly_deg: float) -> tuple[float, float]:
    """Posizione grezza da elementi kepleriani — solo visualizzazione, non predizione orbitale."""
    lat = incl_deg * math.sin(math.radians(mean_anomaly_deg))
    lat = max(-80.0, min(80.0, lat))
    lon = ((raan_deg + mean_anomaly_deg + 180) % 360) - 180
    return lat, lon


async def satellites(limit: int = 180) -> dict:
    cached = cache.get("sat")
    if cached:
        return cached
    raw = await _get_json(CELESTRAK, timeout=30.0)
    items = []
    for row in raw[:limit]:
        try:
            incl = float(row.get("INCLINATION") or 0)
            raan = float(row.get("RA_OF_ASC_NODE") or 0)
            ma = float(row.get("MEAN_ANOMALY") or 0)
            lat, lon = _tle_to_approx_latlon(incl, raan, ma)
        except (TypeError, ValueError):
            continue
        items.append(
            {
                "name": row.get("OBJECT_NAME") or "SAT",
                "norad_id": row.get("NORAD_CAT_ID"),
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "inclination": incl,
            }
        )
    payload = {
        "updated": _now_iso(),
        "count": len(items),
        "note": "Posizioni approssimate da TLE, non predizione SGP4.",
        "items": items,
    }
    cache.set("sat", payload, max(settings.cache_ttl_seconds, 120))
    return payload


async def flights() -> dict:
    cached = cache.get("flights")
    if cached:
        return cached
    headers = {}
    auth = None
    if settings.opensky_client_id and settings.opensky_client_secret:
        auth = (settings.opensky_client_id, settings.opensky_client_secret)
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            r = await client.get(OPENSKY, headers=headers, auth=auth)
            r.raise_for_status()
            raw = r.json()
    except httpx.HTTPError as exc:
        payload = {
            "updated": _now_iso(),
            "count": 0,
            "items": [],
            "error": f"OpenSky non disponibile: {exc.__class__.__name__}",
        }
        cache.set("flights", payload, 20)
        return payload

    items = []
    for s in (raw.get("states") or [])[:400]:
        # OpenSky state vector: ica024, callsign, origin, time, last, lon, lat, baro, on_ground, vel, heading
        lon, lat = s[5], s[6]
        if lon is None or lat is None:
            continue
        items.append(
            {
                "icao24": s[0],
                "callsign": (s[1] or "").strip() or s[0],
                "origin": s[2],
                "lon": lon,
                "lat": lat,
                "altitude_m": s[7],
                "on_ground": s[8],
                "velocity_ms": s[9],
                "heading": s[10],
            }
        )
    payload = {"updated": _now_iso(), "count": len(items), "items": items}
    cache.set("flights", payload, settings.cache_ttl_seconds)
    return payload


async def ships_status() -> dict:
    return {
        "updated": _now_iso(),
        "enabled": bool(settings.ais_api_key),
        "note": (
            "AIS live richiede AIS_API_KEY (aisstream.io). "
            "Questo endpoint conferma solo lo stato: il client WS va collegato a parte."
            if not settings.ais_api_key
            else "Chiave AIS presente. Collegare un client websocket AISStream per le posizioni live."
        ),
    }
