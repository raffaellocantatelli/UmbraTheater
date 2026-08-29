# UmbraTheater

**Teatro globale dell'OSINT — mappa unificata, self-hosted, senza account.**

UmbraTheater aggrega feed pubblici in tempo (quasi) reale su una sola interfaccia scura:
terremoti USGS, satelliti CelesTrak, voli OpenSky, navi AIS (opzionale).

Ispirata all'idea di [ShadowBroker](https://github.com/bigbodycobain/Shadowbroker)
(dashboard geospaziale multi-feed + Docker), ma **codice originale**, stack ridotto
e pronta da avviare in un comando.

> Non è un fork e non include mesh InfoNet, recon toolkit o layer proprietari.
> Solo dati pubblici. Nessun tracking. Nessun account.

---

## Avvio rapido (Docker)

```bash
git clone https://github.com/raffaellocantatelli/UmbraTheater.git
cd UmbraTheater
cp .env.example .env
docker compose up -d --build
```

Apri **http://localhost:3000**

Backend API: `http://localhost:8000/docs`

Aggiornare:

```bash
git pull
docker compose up -d --build
```

---

## Cosa fa

| Layer        | Sorgente              | Chiave API      |
|--------------|-----------------------|-----------------|
| Terremoti    | USGS FDSN GeoJSON     | no              |
| Satelliti    | CelesTrak GP          | no              |
| Voli         | OpenSky Network       | opzionale       |
| Navi         | AISStream.io          | `AIS_API_KEY`   |

Il frontend è una mappa Leaflet tema dark-ops con toggle layer, polling e popup.
Il backend FastAPI fa da proxy: il browser non parla mai diretto con le API esterne.

---

## Architettura

```
browser  →  frontend :3000 (nginx + static)
                 ↓ /api/*
             backend :8000 (FastAPI)
                 ↓
             USGS / CelesTrak / OpenSky / AISStream
```

- `backend/` — Python 3.12, FastAPI, httpx, cache in-memory
- `frontend/` — HTML/JS/CSS, Leaflet + Carto Dark
- `docker-compose.yml` — build locale, nessuna immagine di terzi obbligatoria

---

## Variabili d'ambiente

Vedi `.env.example`.

| Variabile              | Default | Note |
|------------------------|---------|------|
| `BACKEND_PORT`         | 8000    | Porta host API |
| `FRONTEND_PORT`        | 3000    | Porta dashboard |
| `AIS_API_KEY`          | vuoto   | Gratis su [aisstream.io](https://aisstream.io) |
| `OPENSKY_CLIENT_ID`    | vuoto   | Aumenta i limiti OpenSky |
| `OPENSKY_CLIENT_SECRET`| vuoto   | |
| `CACHE_TTL_SECONDS`    | 45      | Cache feed |

Senza chiavi i layer terremoti e satelliti funzionano subito.
Voli e navi sono best-effort / opzionali.

---

## Sviluppo locale (senza Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In un altro terminale servi `frontend/` (es. `python -m http.server 3000`)
e imposta `window.UMBRA_API = "http://localhost:8000"`.

---

## Licenza e attribuzioni

- Codice UmbraTheater: **MIT** (vedi `LICENSE`)
- Dati: rispettare i ToS di USGS, CelesTrak, OpenSky, AISStream, OSM
- Basemap: © OpenStreetMap contributors, © CARTO
- Concetto di dashboard OSINT unificata: ispirato a ShadowBroker (AGPL-3.0).
  Nessun file di quel repository è stato copiato.

Uso previsto: ricerca personale e didattica. Non è uno strumento di sorveglianza.
