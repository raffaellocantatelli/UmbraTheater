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

Le posizioni dei satelliti sono propagate con **SGP4** dagli elementi OMM di CelesTrak
(pacchetto `sgp4`). Senza quel pacchetto il layer dichiara `senza_propagatore` e non
disegna niente: non esistono posizioni approssimate da mostrare.

---

## Il contratto delle risposte

Ogni endpoint restituisce la stessa busta. Tre campi contano più degli altri, e
servono a non far dire alla mappa più di quanto sa:

```json
{
  "source":    { "name": "CelesTrak GP", "url": "…", "coverage": "catalogo oggetti attivi" },
  "status":    "ok",          // oppure errore | senza_chiave | senza_propagatore
  "total":     16469,         // quanti ne ha mandati la sorgente
  "returned":  180,           // quanti ne restituiamo
  "cap":       180,
  "truncated": true,          // allora il valore vero è `total`, non `returned`
  "items":     [ … ]
}
```

- **`truncated`** — se è vero, il conteggio è arrivato al tetto della query e la UI
  mostra `≥ 180` con l'etichetta TETTO. Un numero tagliato non è una misura.
- **`status`** diverso da `ok` → **`total` e `returned` sono `null`, mai `0`.**
  «Nessun dato» e «nessun evento» sono cose diverse, e un layer spento che stampa
  `0` è la bugia più facile da mettere su una mappa.
- **`coverage`** dice che pezzo di mondo copre davvero la sorgente: USGS è
  magnitudo ≥ 2.5 nelle ultime 24 h, non «tutti i terremoti».

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
