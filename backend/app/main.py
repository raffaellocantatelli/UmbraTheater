from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import feeds
from .settings import settings

app = FastAPI(
    title="UmbraTheater API",
    description="Proxy OSINT pubblico per la dashboard UmbraTheater.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list or ["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "service": "umbra-backend",
        "version": "0.1.0",
        "layers": ["earthquakes", "satellites", "flights", "ships"],
        # dichiarato qui perche' senza propagatore il layer satelliti non
        # produce posizioni: meglio saperlo dall'health che dalla mappa
        "sgp4": feeds.SGP4_DISPONIBILE,
    }


@app.get("/api/earthquakes")
async def earthquakes():
    return await feeds.earthquakes()


@app.get("/api/satellites")
async def satellites():
    return await feeds.satellites()


@app.get("/api/flights")
async def flights():
    return await feeds.flights()


@app.get("/api/ships")
async def ships():
    return await feeds.ships_status()
