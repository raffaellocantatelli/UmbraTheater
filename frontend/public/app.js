const API = "";

const map = L.map("map", { worldCopyJump: true, minZoom: 2 }).setView([20, 12], 3);
L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  attribution: "&copy; OSM &copy; CARTO",
  maxZoom: 19,
}).addTo(map);

const layers = {
  eq: L.layerGroup().addTo(map),
  sat: L.layerGroup().addTo(map),
  flt: L.layerGroup().addTo(map),
  shp: L.layerGroup(),
};

const toggles = {
  eq: document.getElementById("ly-eq"),
  sat: document.getElementById("ly-sat"),
  flt: document.getElementById("ly-flt"),
  shp: document.getElementById("ly-shp"),
};

Object.entries(toggles).forEach(([key, el]) => {
  el.addEventListener("change", () => {
    if (el.checked) map.addLayer(layers[key]);
    else map.removeLayer(layers[key]);
  });
});

function circle(lat, lon, color, radius, html) {
  return L.circleMarker([lat, lon], {
    radius,
    color,
    weight: 1,
    fillColor: color,
    fillOpacity: 0.75,
  }).bindPopup(html);
}


// Come si scrive un conteggio senza mentire.
//
// La regola: un layer che non ha dati non vale 0. Prima questa riga diceva
// `${eq.count ?? 0}`, e quel `?? 0` trasformava "non lo so" in "nessun evento" —
// che è esattamente il difetto per cui una dashboard OSINT smette di essere
// utile. Ora un layer senza dato mostra un trattino e il motivo.
//
// E un conteggio arrivato al tetto della query non è una misura: il valore
// reale è `total`, quindi si stampa "≥ N" e si dichiara il tetto.
const STATI = {
  errore: "errore",
  senza_chiave: "senza chiave",
  senza_propagatore: "senza propagatore",
};

function riga(nome, d) {
  const stato = d && d.status;
  if (stato && stato !== "ok") {
    const perche = d.error ? ` title="${String(d.error).replace(/"/g, "'")}"` : "";
    return `<div class="riga"${perche}><span>${nome}</span>` +
      `<span class="vuoto">— ${STATI[stato] || stato}</span></div>`;
  }
  if (!d || d.returned == null) {
    return `<div class="riga"><span>${nome}</span><span class="vuoto">—</span></div>`;
  }
  if (d.truncated) {
    return `<div class="riga" title="tetto ${d.cap}: la sorgente ne ha mandati ${d.total}">` +
      `<span>${nome}</span><span class="num">≥ ${d.returned}` +
      `<i class="tetto">tetto</i></span></div>`;
  }
  return `<div class="riga"><span>${nome}</span><span class="num">${d.returned}</span></div>`;
}

async function j(path) {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${path} ${r.status}`);
  return r.json();
}

async function refresh() {
  const status = document.getElementById("status");
  const meta = document.getElementById("meta");
  status.textContent = "sync…";
  try {
    const [eq, sat, flt, shp] = await Promise.all([
      j("/api/earthquakes"),
      j("/api/satellites"),
      j("/api/flights"),
      j("/api/ships"),
    ]);

    layers.eq.clearLayers();
    (eq.items || []).forEach((e) => {
      if (e.lat == null || e.lon == null) return;
      const mag = e.mag || 0;
      layers.eq.addLayer(
        circle(
          e.lat,
          e.lon,
          mag >= 5 ? "#ff5d5d" : "#ffb347",
          Math.max(3, mag * 2),
          `<b>M${mag}</b><br>${e.place || ""}<br>profondità ${e.depth_km ?? "?"} km`
        )
      );
    });

    layers.sat.clearLayers();
    (sat.items || []).forEach((s) => {
      if (s.lat == null || s.lon == null) return;
      layers.sat.addLayer(
        circle(
          s.lat,
          s.lon,
          "#7cffc4",
          3,
          `<b>${s.name}</b><br>NORAD ${s.norad_id || "—"}<br>` +
            `quota ${s.altitude_km ?? "?"} km · ${s.speed_kms ?? "?"} km/s<br>` +
            `<small>SGP4 · elementi del ${s.epoch || "?"}</small>`
        )
      );
    });

    layers.flt.clearLayers();
    (flt.items || []).forEach((f) => {
      layers.flt.addLayer(
        circle(
          f.lat,
          f.lon,
          "#6cb6ff",
          3,
          `<b>${f.callsign}</b><br>${f.origin || ""}<br>${f.on_ground ? "a terra" : "in volo"}`
        )
      );
    });

    meta.innerHTML =
      [
        riga("terremoti", eq),
        riga("satelliti", sat),
        riga("voli", flt),
        riga("navi", shp),
      ].join("") + `<div class="agg">agg: ${new Date().toLocaleTimeString()}</div>`;
    status.textContent = "live";
  } catch (err) {
    status.textContent = "errore backend";
    meta.textContent = String(err);
  }
}

refresh();
setInterval(refresh, 60000);
