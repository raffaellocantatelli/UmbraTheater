from __future__ import annotations

import math
from datetime import datetime, timezone

import httpx

from .cache import cache
from .settings import settings

USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
CELESTRAK = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=json"
OPENSKY = "https://opensky-network.org/api/states/all"

# Tetti applicati per non spedire al browser payload enormi. Ogni tetto e'
# dichiarato nella risposta: un conteggio tagliato non deve mai sembrare una
# misura. Se `truncated` e' vero, il valore reale e' `total`, non `returned`.
CAP_EARTHQUAKES = 250
CAP_SATELLITES = 180
CAP_FLIGHTS = 400

# Stati possibili di un layer. Nessuno di questi vale zero.
OK = "ok"
ERRORE = "errore"
SENZA_CHIAVE = "senza_chiave"
SENZA_PROPAGATORE = "senza_propagatore"

try:  # il propagatore e' un requisito, ma se manca non si inventano posizioni
    from sgp4 import omm
    from sgp4.api import Satrec, jday

    SGP4_DISPONIBILE = True
except ImportError:  # pragma: no cover
    SGP4_DISPONIBILE = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _envelope(
    *,
    name: str,
    url: str,
    coverage: str,
    items: list | None = None,
    total: int | None = None,
    cap: int | None = None,
    status: str = OK,
    error: str | None = None,
    **extra,
) -> dict:
    """Il contratto unico di ogni layer.

    Regole, applicate qui una volta sola invece che a ogni chiamata:

    - `total` e' quanti elementi ha mandato la sorgente, `returned` quanti ne
      restituiamo. Se differiscono, `truncated` e' vero e il client deve
      mostrare "almeno N", non N.
    - Quando lo stato non e' `ok`, `total` e `returned` sono **null**, mai 0:
      "nessun dato" e "nessun evento" sono cose diverse, e un layer spento che
      dichiara 0 e' la bugia piu' facile da stampare su una mappa.
    - `coverage` dice che pezzo di mondo copre davvero la sorgente.
    """
    lista = items if items is not None else []
    if status == OK:
        returned: int | None = len(lista)
        totale = total if total is not None else returned
        truncated = totale is not None and returned is not None and returned < totale
    else:
        returned = None
        totale = None
        truncated = False
    return {
        "updated": _now_iso(),
        "source": {"name": name, "url": url, "coverage": coverage},
        "status": status,
        "total": totale,
        "returned": returned,
        "cap": cap,
        "truncated": truncated,
        "error": error,
        "items": lista,
        **extra,
    }


async def _get_json(
    url: str, *, headers: dict | None = None, params: dict | None = None, timeout: float = 20.0
):
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url, headers=headers, params=params)
        r.raise_for_status()
        return r.json()


async def earthquakes() -> dict:
    cached = cache.get("eq")
    if cached:
        return cached
    try:
        raw = await _get_json(USGS)
    except httpx.HTTPError as exc:
        payload = _envelope(
            name="USGS",
            url=USGS,
            coverage="magnitudo >= 2.5, ultime 24 h, mondiale",
            status=ERRORE,
            error=f"USGS non disponibile: {exc.__class__.__name__}",
        )
        cache.set("eq", payload, 20)
        return payload

    tutte = raw.get("features", [])
    features = []
    for f in tutte[:CAP_EARTHQUAKES]:
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
    payload = _envelope(
        name="USGS",
        url=USGS,
        coverage="magnitudo >= 2.5, ultime 24 h, mondiale",
        items=features,
        total=len(tutte),
        cap=CAP_EARTHQUAKES,
    )
    cache.set("eq", payload, settings.cache_ttl_seconds)
    return payload


def _gmst_rad(jd: float, fr: float) -> float:
    """Tempo siderale medio di Greenwich, in radianti."""
    d = (jd - 2451545.0) + fr
    t = d / 36525.0
    g = 280.46061837 + 360.98564736629 * d + 0.000387933 * t * t - t * t * t / 38710000.0
    return math.radians(g % 360.0)


def _teme_to_geodetic(r_km: tuple, jd: float, fr: float) -> tuple[float, float, float]:
    """Da posizione TEME (km) a latitudine, longitudine e quota su ellissoide WGS84."""
    g = _gmst_rad(jd, fr)
    x = r_km[0] * math.cos(g) + r_km[1] * math.sin(g)
    y = -r_km[0] * math.sin(g) + r_km[1] * math.cos(g)
    z = r_km[2]

    a, f = 6378.137, 1 / 298.257223563
    e2 = f * (2 - f)
    lon = math.degrees(math.atan2(y, x))
    p = math.hypot(x, y)
    lat = math.atan2(z, p * (1 - e2))
    for _ in range(6):  # converge ben prima della sesta iterazione
        n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        lat = math.atan2(z + e2 * n * math.sin(lat), p)
    n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    alt = p / math.cos(lat) - n
    return math.degrees(lat), ((lon + 180) % 360) - 180, alt


async def satellites(limit: int = CAP_SATELLITES) -> dict:
    """Posizioni reali, propagate con SGP4 dagli elementi OMM di CelesTrak.

    Se il propagatore non e' installato NON si disegna niente: prima questa
    funzione produceva coordinate da una formula decorativa
    (`lat = inclinazione * sin(anomalia media)`), che sulla mappa diventavano
    puntini indistinguibili da posizioni vere. Meglio un layer che dichiara di
    non poter calcolare, che una mappa che afferma piu' di quanto sa.
    """
    cached = cache.get("sat")
    if cached:
        return cached

    if not SGP4_DISPONIBILE:
        payload = _envelope(
            name="CelesTrak GP",
            url=CELESTRAK,
            coverage="catalogo oggetti attivi",
            status=SENZA_PROPAGATORE,
            error="il pacchetto 'sgp4' non e' installato: senza propagatore non "
            "esistono posizioni da mostrare, e non ne vengono inventate",
            propagator=None,
        )
        cache.set("sat", payload, 300)
        return payload

    try:
        raw = await _get_json(CELESTRAK, timeout=30.0)
    except httpx.HTTPError as exc:
        payload = _envelope(
            name="CelesTrak GP",
            url=CELESTRAK,
            coverage="catalogo oggetti attivi",
            status=ERRORE,
            error=f"CelesTrak non disponibile: {exc.__class__.__name__}",
        )
        cache.set("sat", payload, 20)
        return payload

    adesso = datetime.now(timezone.utc)
    jd, fr = jday(
        adesso.year,
        adesso.month,
        adesso.day,
        adesso.hour,
        adesso.minute,
        adesso.second + adesso.microsecond / 1e6,
    )

    items = []
    scartati = 0
    for row in raw[:limit]:
        try:
            sat = Satrec()
            omm.initialize(sat, row)
            errore, r, v = sat.sgp4(jd, fr)
            if errore:
                scartati += 1
                continue
            lat, lon, alt = _teme_to_geodetic(r, jd, fr)
        except (TypeError, ValueError, KeyError):
            scartati += 1
            continue
        items.append(
            {
                "name": row.get("OBJECT_NAME") or "SAT",
                "norad_id": row.get("NORAD_CAT_ID"),
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "altitude_km": round(alt, 1),
                "speed_kms": round(math.sqrt(sum(c * c for c in v)), 3),
                "inclination": row.get("INCLINATION"),
                "epoch": row.get("EPOCH"),
            }
        )

    payload = _envelope(
        name="CelesTrak GP",
        url=CELESTRAK,
        coverage="catalogo oggetti attivi",
        items=items,
        total=len(raw),
        cap=limit,
        propagator="SGP4 (pacchetto sgp4), elementi OMM CelesTrak",
        discarded=scartati,
        note="posizioni propagate all'istante della richiesta; la precisione "
        "degrada con l'eta' degli elementi orbitali (campo 'epoch')",
    )
    cache.set("sat", payload, max(settings.cache_ttl_seconds, 120))
    return payload


async def flights() -> dict:
    cached = cache.get("flights")
    if cached:
        return cached
    auth = None
    if settings.opensky_client_id and settings.opensky_client_secret:
        auth = (settings.opensky_client_id, settings.opensky_client_secret)
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            r = await client.get(OPENSKY, auth=auth)
            r.raise_for_status()
            raw = r.json()
    except httpx.HTTPError as exc:
        # prima qui c'era "count": 0. Un feed caduto non ha zero aerei:
        # non ha nessun dato, ed e' un'altra cosa.
        payload = _envelope(
            name="OpenSky Network",
            url=OPENSKY,
            coverage="ADS-B collaborativo, copertura disomogenea per regione",
            status=ERRORE,
            error=f"OpenSky non disponibile: {exc.__class__.__name__}",
        )
        cache.set("flights", payload, 20)
        return payload

    stati = raw.get("states") or []
    items = []
    for s in stati[:CAP_FLIGHTS]:
        # OpenSky state vector: icao24, callsign, origin, time, last, lon, lat, ...
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
    payload = _envelope(
        name="OpenSky Network",
        url=OPENSKY,
        coverage="ADS-B collaborativo, copertura disomogenea per regione",
        items=items,
        total=len(stati),
        cap=CAP_FLIGHTS,
    )
    cache.set("flights", payload, settings.cache_ttl_seconds)
    return payload


async def ships_status() -> dict:
    attiva = bool(settings.ais_api_key)
    return _envelope(
        name="AISStream.io",
        url="wss://stream.aisstream.io/v0/stream",
        coverage="AIS terrestre e satellitare, secondo il fornitore",
        status=OK if attiva else SENZA_CHIAVE,
        enabled=attiva,
        error=None
        if attiva
        else "AIS live richiede AIS_API_KEY (aisstream.io); il client websocket "
        "va collegato a parte",
        note="chiave presente: collegare un client websocket AISStream per le "
        "posizioni live" if attiva else None,
    )
