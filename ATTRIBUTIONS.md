# Attribuzioni

UmbraTheater usa solo fonti pubbliche.

## Codice

- UmbraTheater è originale e rilasciato sotto MIT.
- Il concetto di dashboard OSINT geospaziale multi-feed self-hosted è ispirato a
  [ShadowBroker](https://github.com/bigbodycobain/Shadowbroker) (AGPL-3.0).
  Nessun file, immagine Docker o protocollo di quel progetto è stato copiato.

### Verifica della posizione clean-room

L'affermazione qui sopra non è solo dichiarata: è stata misurata, e chiunque
può ripetere la misura.

**Metodo.** Entrambi i repository vengono normalizzati riga per riga (commenti
e righe vuote rimossi, spaziatura collassata), si scartano le righe sotto i 25
caratteri, e si cerca ogni riga di UmbraTheater dentro l'insieme completo delle
righe di ShadowBroker. Si misura la percentuale di righe in comune e, soprattutto,
la lunghezza del più lungo **blocco contiguo** identico — che è il segnale che
distingue una copia da una coincidenza di linguaggio.

**Risultato, 1 settembre 2026** — UmbraTheater `bbaa588`+PR#1, ShadowBroker `cd6395f`:

| file | righe | in comune | blocco contiguo più lungo |
|---|---|---|---|
| `backend/app/settings.py` | 9 | 3 | 3 |
| `backend/app/main.py` | 14 | 2 | 2 |
| `backend/app/feeds.py` | 118 | 4 | 2 |
| `backend/app/cache.py` | 7 | 1 | 1 |
| `frontend/public/*` | 94 | 0 | 0 |

**Blocchi contigui identici di 6 o più righe: nessuno.**

Le dieci righe in comune, per intero, sono:

```
from __future__ import annotations
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
model_config = SettingsConfigDict(env_file=".env", extra="ignore")
def __init__(self) -> None:
return datetime.now(timezone.utc).isoformat()
except (TypeError, ValueError, KeyError):
```

Sono import di libreria e idiomi obbligati: non esiste un altro modo di
scrivere quelle righe in Python con quelle dipendenze. Non c'è espressione
originale, e quindi non c'è nulla di tutelabile che sia stato ripreso.

**Perché è scritto qui.** ShadowBroker è AGPL-3.0 e UmbraTheater è MIT. Se
anche un solo file fosse stato copiato, la copyleft si estenderebbe a questo
progetto. La verifica va rifatta a ogni contributo che tocchi il backend, ed è
la ragione per cui la dipendenza da ShadowBroker resta **concettuale** e
dichiarata, mai testuale.

## Dati e basemap

- USGS Earthquake Hazards Program — pubblico dominio (governo USA)
- CelesTrak / NORAD TLE — termini CelesTrak
- OpenSky Network — termini API OpenSky
- AISStream.io — termini del fornitore, chiave personale obbligatoria
- OpenStreetMap contributors
- CARTO basemap dark
