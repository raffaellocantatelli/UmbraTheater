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
      layers.sat.addLayer(
        circle(s.lat, s.lon, "#7cffc4", 3, `<b>${s.name}</b><br>NORAD ${s.norad_id || "—"}`)
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

    meta.innerHTML = [
      `terremoti: ${eq.count ?? 0}`,
      `satelliti: ${sat.count ?? 0}`,
      `voli: ${flt.count ?? 0}${flt.error ? " (⚠️)" : ""}`,
      `ais: ${shp.enabled ? "chiave ok" : "disattivo"}`,
      `agg: ${new Date().toLocaleTimeString()}`,
    ].join("<br>");
    status.textContent = "live";
  } catch (err) {
    status.textContent = "errore backend";
    meta.textContent = String(err);
  }
}

refresh();
setInterval(refresh, 60000);
