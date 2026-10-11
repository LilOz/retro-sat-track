const $ = (id) => document.getElementById(id);
const TAU = Math.PI * 2,
  RAD = Math.PI / 180,
  EARTH = 6378.137;
const colors = {
  green: "#b9f59f",
  grid: "#304837",
  land: "#73976c",
  amber: "#f5c778",
  muted: "#8b9c8b",
};
const state = {
  group: "stations",
  selected: null,
  satellites: [],
  total: 0,
  query: "",
  page: "orbit",
  scene: [],
  track: null,
  passes: [],
  pass: null,
  observer: null,
  history: [],
  token: 0,
  angle: 15 * RAD,
  tilt: 18 * RAD,
  zoom: 1,
  rotating: !matchMedia("(prefers-reduced-motion: reduce)").matches,
  land: [],
  errors: {},
  clockOffset: 0,
  lastScene: 0,
};
let sceneBusy = false,
  passBusy = false,
  catalogVersion = 0,
  searchTimer;
const fmt = (value, places = 1) =>
  value == null || !Number.isFinite(value) ? "—" : value.toFixed(places);
const utcTime = (date) => new Date(date).toISOString().slice(11, 19);
const utcDate = (date) =>
  new Date(date).toISOString().slice(0, 10).replaceAll("-", ".");
const now = () => Date.now() + state.clockOffset;
function pref(key, value) {
  try {
    if (value !== undefined) localStorage.setItem(key, value);
    else return localStorage.getItem(key);
  } catch {
    return null;
  }
}

async function api(path, options = {}) {
  const response = await fetch(`/api/v1/${path}`, {
    ...options,
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const error = await response.json();
      message =
        typeof error.detail === "string"
          ? error.detail
          : "Check the entered values.";
    } catch {
      /* retain HTTP error */
    }
    throw new Error(message);
  }
  return response.json();
}
function error(scope, message) {
  if (message) state.errors[scope] = message;
  else delete state.errors[scope];
  const messages = [...new Set(Object.values(state.errors))];
  $("error-banner").textContent = messages.join(" / ");
  $("error-banner").hidden = !messages.length;
}
function log(message, emphasis = false) {
  const row = document.createElement("div");
  row.className = `log-row${emphasis ? " emphasis" : ""}`;
  const time = document.createElement("time");
  time.textContent = utcTime(now());
  const text = document.createElement("span");
  text.textContent = message;
  row.append(time, text);
  $("event-log").append(row);
  while ($("event-log").children.length > 80)
    $("event-log").firstChild.remove();
  $("event-log").scrollTop = $("event-log").scrollHeight;
}
function page(name) {
  state.page = name;
  document
    .querySelectorAll(".page")
    .forEach((el) => el.classList.toggle("active", el.id === `page-${name}`));
  document.querySelectorAll(".page-tab").forEach((el) => {
    el.classList.toggle("active", el.dataset.page === name);
    if (el.dataset.page === name) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  requestAnimationFrame(drawAuxiliary);
}
function setRotation(value) {
  state.rotating = value;
  $("rotate-button").setAttribute("aria-pressed", String(value));
}
function stationLabel() {
  $("station-label").textContent = state.observer
    ? state.observer.name.toUpperCase()
    : "SET GROUND STATION";
  $("station-button").title = state.observer
    ? `${state.observer.latitude_deg}°, ${state.observer.longitude_deg}°`
    : "Configure your location";
}
async function status() {
  try {
    const start = Date.now(),
      data = await api("status");
    state.clockOffset = Date.parse(data.utc) - (start + Date.now()) / 2;
    state.observer = data.observer;
    stationLabel();
    error("connection");
    error("provider", data.provider_error);
    $("connection").textContent = data.provider_configured ? "BACKEND ONLINE" : "API KEY REQUIRED";
    $("connection").className = data.provider_configured ? "status-light" : "status-light pending";
  } catch (exc) {
    $("connection").textContent = "BACKEND OFFLINE";
    $("connection").className = "status-light offline";
    error(
      "connection",
      "Tracking service unavailable. Keep the local Python server running.",
    );
  }
}
function freshness(catalog) {
  const minutes = Math.floor(catalog.download_age_seconds / 60);
  $("freshness").textContent =
    `N2YO / CATALOG ${catalog.stale ? "CACHED · " : ""}${minutes}m AGO`;
  error(
    "catalog",
    catalog.error ||
      (catalog.stale
        ? "Using cached orbital elements while the catalog refreshes."
        : null),
  );
}
function renderCatalog() {
  const list = $("satellite-list");
  list.replaceChildren();
  $("catalog-count").textContent =
    `${state.satellites.length} OF ${state.total.toLocaleString()} OBJECTS / ${state.group.toUpperCase()}`;
  if (!state.satellites.length) {
    const empty = document.createElement("p");
    empty.textContent = "No matching spacecraft.";
    list.append(empty);
  }
  state.satellites.forEach((sat) => {
    const button = document.createElement("button");
    button.className = sat.id === state.selected?.id ? "active" : "";
    const name = document.createElement("span");
    name.textContent = sat.name;
    const id = document.createElement("span");
    id.textContent = `${sat.id} ↗`;
    button.append(name, id);
    button.onclick = () => {
      $("catalog-dialog").close();
      selectSatellite(sat);
    };
    list.append(button);
  });
  $("load-more").hidden = state.satellites.length >= state.total;
}
async function loadCatalog({ append = false, choose = false } = {}) {
  const version = ++catalogVersion,
    group = state.group;
  const query = new URLSearchParams({
    group,
    q: state.query,
    limit: "150",
    offset: String(append ? state.satellites.length : 0),
  });
  $("load-more").disabled = true;
  try {
    const data = await api(`satellites?${query}`);
    if (version !== catalogVersion || group !== state.group) return;
    state.satellites = append
      ? [...state.satellites, ...data.satellites]
      : data.satellites;
    state.total = data.total;
    freshness(data.catalog);
    renderCatalog();
    if (choose && data.satellites.length) {
      const saved = Number(pref(`satellite-${group}`));
      let sat =
        data.satellites.find((item) => item.id === saved) || data.satellites[0];
      // Only restore selections present in the currently loaded group.
      selectSatellite(sat);
    }
  } catch (exc) {
    if (version !== catalogVersion) return;
    error("catalog", exc.message);
    log(exc.message);
    if (choose) {
      $("target-name").textContent = "Catalog unavailable";
      $("globe-empty").textContent = "NO ORBITAL ELEMENTS / CHECK CONNECTION";
    }
    $("catalog-count").textContent = exc.message;
  } finally {
    if (version === catalogVersion) $("load-more").disabled = false;
  }
}
function clearSelection() {
  state.token++;
  state.selected = null;
  state.scene = [];
  state.track = null;
  state.passes = [];
  state.pass = null;
  state.history = [];
  state.lastScene = 0;
  $("track-window").textContent = "PATH / UP TO 5 MIN";
  document.querySelectorAll("[data-value]").forEach((el) => {
    el.textContent = "—";
  });
  $("target-id").textContent = "-----";
  $("element-age").textContent = "—";
  $("epoch-time").textContent = "—";
  $("horizon-status").textContent = "AWAITING STATE";
  $("scene-count").textContent = "0 OBJECTS IN VIEW";
  $("globe-empty").hidden = false;
  ["track", "scene", "elements", "passes"].forEach((scope) => error(scope));
  renderPasses();
  tickClock();
  drawAuxiliary();
}
async function selectSatellite(satellite) {
  clearSelection();
  state.selected = satellite;
  pref(`satellite-${state.group}`, String(satellite.id));
  $("target-name").textContent = satellite.name;
  $("target-id").textContent = satellite.id;
  $("target-group").textContent =
    $("group-select").selectedOptions[0].text.toUpperCase();
  $("globe-empty").textContent = "ACQUIRING N2YO POSITIONS…";
  log(`Tracking ${satellite.name} / NORAD ${satellite.id}`, true);
  renderCatalog();
  await Promise.allSettled([
    refreshScene(true),
    refreshTrack(),
    refreshPasses(true),
  ]);
}
function formatValue(key, value) {
  if (value == null || !Number.isFinite(value)) return "—";
  if (key === "latitude_deg")
    return `${fmt(Math.abs(value), 3)}° ${value >= 0 ? "N" : "S"}`;
  if (key === "longitude_deg")
    return `${fmt(Math.abs(value), 3)}° ${value >= 0 ? "E" : "W"}`;
  return fmt(
    value,
    key === "velocity_km_s"
      ? 3
      : key === "eccentricity"
        ? 7
        : key === "inclination_deg"
          ? 2
          : 1,
  );
}
async function refreshScene(force = false) {
  if (!state.selected || (sceneBusy && !force)) return;
  const token = state.token,
    group = state.group,
    id = state.selected.id;
  sceneBusy = true;
  try {
    const data = await api(`scene?group=${group}&selected_id=${id}`);
    if (token !== state.token) return;
    state.scene = data.states;
    freshness(data.catalog);
    error("scene");
    const selected = data.states.find((item) => item.id === id);
    if (!selected)
      throw new Error("Selected satellite has no current provider position.");
    state.lastScene = Date.parse(selected.utc);
    $("globe-empty").hidden = true;
    document.querySelectorAll("[data-value]").forEach((el) => {
      const key = el.dataset.value;
      el.textContent =
        !state.observer &&
        ["azimuth_deg", "elevation_deg", "range_km"].includes(key)
          ? "—"
          : formatValue(key, selected[key]);
    });
    $("element-age").textContent =
      `${fmt(selected.element_age_hours)} h${selected.elements_stale ? " / STALE" : ""}`;
    $("epoch-time").textContent =
      `${utcDate(selected.element_epoch)} ${utcTime(selected.element_epoch)}`;
    $("horizon-status").textContent = state.observer
      ? selected.above_horizon
        ? "ABOVE HORIZON"
        : "BELOW HORIZON"
      : "SET LOCATION";
    $("scene-count").textContent = `${data.states.length} SELECTED OBJECT / N2YO`;
    error(
      "elements",
      selected.elements_stale
        ? "CelesTrak catalog metadata is over 7 days from its epoch. N2YO uses its own elements for positions and forecasts."
        : null,
    );
    state.history.push(selected);
    if (state.history.length > 180) state.history.shift();
    log(
      `ALT ${fmt(selected.altitude_km)} km · N2YO ${utcTime(selected.utc)}`,
    );
    drawAuxiliary();
  } catch (exc) {
    if (token !== state.token) return;
    error("scene", exc.message);
    if (!state.scene.length) {
      $("globe-empty").textContent = "ORBIT UNAVAILABLE / SEE STATUS";
      $("globe-empty").hidden = false;
    }
  } finally {
    sceneBusy = false;
  }
}
async function refreshTrack() {
  if (!state.selected) return;
  const token = state.token,
    id = state.selected.id,
    group = state.group;
  try {
    const data = await api(`satellites/${id}/track?group=${group}`);
    if (token !== state.token) return;
    state.track = data;
    $("track-window").textContent = `PATH / NEXT ${data.window_seconds}s`;
    error("track");
  } catch (exc) {
    if (token === state.token) error("track", exc.message);
  }
}
async function refreshPasses(force = false) {
  if (!state.selected || !state.observer || (passBusy && !force)) {
    if (!state.observer) renderPasses();
    return;
  }
  const token = state.token,
    id = state.selected.id,
    group = state.group,
    mask = $("elevation-mask").value;
  passBusy = true;
  try {
    const data = await api(
      `passes?satellite_id=${id}&group=${group}&min_elevation=${mask}`,
    );
    if (token !== state.token || mask !== $("elevation-mask").value) return;
    const previouslySelected = state.pass?.id;
    state.passes = data.passes;
    state.pass =
      data.passes.find((p) => p.id === previouslySelected) ||
      data.passes[0] ||
      null;
    state.passNote = null;
    error("passes");
    renderPasses();
    tickClock();
    log(`Pass forecast ready / ${data.passes.length} contacts in 48h`, true);
  } catch (exc) {
    if (token !== state.token) return;
    state.passes = [];
    state.pass = null;
    error("passes", exc.message);
    renderPasses(exc.message);
  } finally {
    passBusy = false;
  }
}
function renderPasses(message) {
  $("pass-table").hidden = !state.passes.length;
  $("pass-empty").hidden = !!state.passes.length;
  $("pass-detail").hidden = !state.pass;
  $("pass-count").textContent = `${state.passes.length} WINDOWS / 48h`;
  if (!state.passes.length) {
    const empty = $("pass-empty");
    empty.querySelector("h3").textContent = state.observer
      ? message
        ? "Forecast unavailable."
        : "No contacts in this window."
      : "Establish your ground station.";
    empty.querySelector("p").textContent =
      message ||
      (state.observer
        ? state.passNote ||
          "Try a lower minimum peak elevation or select another satellite. Forecasts cover the next 48 hours."
        : "Enter your location to calculate rise, culmination and set times for this spacecraft.");
    empty.querySelector("button").textContent = state.observer
      ? "EDIT GROUND STATION ↗"
      : "SET LOCATION ↗";
  }
  $("pass-rows").replaceChildren();
  state.passes.forEach((pass) => {
    const row = document.createElement("tr");
    row.className = state.pass?.id === pass.id ? "selected" : "";
    const rise = document.createElement("td"),
      button = document.createElement("button"),
      date = document.createElement("small");
    date.textContent = utcDate(pass.rise_utc);
    button.append(date, document.createTextNode(utcTime(pass.rise_utc)));
    rise.append(button);
    row.append(rise);
    [
      `${fmt(pass.max_elevation_deg)}°`,
      `${pass.rise_direction} → ${pass.set_direction}`,
      `${Math.floor(pass.duration_seconds / 60)}m ${pass.duration_seconds % 60}s`,
    ].forEach((value) => {
      const td = document.createElement("td");
      td.textContent = value;
      row.append(td);
    });
    row.onclick = () => {
      state.pass = pass;
      renderPasses();
    };
    $("pass-rows").append(row);
  });
  if (state.pass) {
    $("pass-detail").replaceChildren();
    [
      ["RISE / UTC", utcTime(state.pass.rise_utc)],
      ["CULMINATION / UTC", utcTime(state.pass.culmination_utc)],
      ["SET / UTC", utcTime(state.pass.set_utc)],
    ].forEach(([label, value]) => {
      const block = document.createElement("div"),
        title = document.createElement("span"),
        text = document.createElement("strong");
      title.textContent = label;
      text.textContent = value;
      block.append(title, text);
      $("pass-detail").append(block);
    });
  }
  $("sky-direction").textContent = state.pass
    ? `${state.pass.rise_direction} → ${state.pass.set_direction}`
    : "AWAITING FORECAST";
  $("sky-peak").textContent = state.pass
    ? `MAX ${fmt(state.pass.max_elevation_deg)}°`
    : "—";
  drawSky();
}
function tickClock() {
  $("utc-clock").textContent = utcTime(now());
  $("utc-date").textContent = utcDate(now());
  if (state.track?.ground_track.length) {
    const end = Date.parse(state.track.ground_track.at(-1).utc);
    const remaining = Math.max(0, Math.floor((end - now()) / 1000));
    $("track-window").textContent = remaining ? `PATH / NEXT ${remaining}s` : "PATH EXPIRED";
  }
  const next = state.passes.find((pass) => Date.parse(pass.set_utc) > now());
  $("pass-led").classList.toggle("ready", !!next);
  if (next) {
    const remaining = Math.max(
      0,
      Math.floor((Date.parse(next.rise_utc) - now()) / 1000),
    );
    $("next-pass-label").textContent = remaining
      ? `NEXT ${state.selected?.name || "SPACECRAFT"} PASS`
      : "CONTACT IN PROGRESS";
    $("pass-countdown").textContent = remaining
      ? [
          Math.floor(remaining / 3600),
          Math.floor(remaining / 60) % 60,
          remaining % 60,
        ]
          .map((v) => String(v).padStart(2, "0"))
          .join(":")
      : "IN RANGE";
    $("next-pass-time").textContent =
      `${utcDate(next.rise_utc)} / ${utcTime(next.rise_utc).slice(0, 5)} UTC`;
    $("next-pass-elevation").textContent =
      `MAX ${fmt(next.max_elevation_deg)}°`;
  } else {
    $("next-pass-label").textContent = state.observer
      ? "NO UPCOMING CONTACT"
      : "SET YOUR GROUND STATION";
    $("pass-countdown").textContent = "--:--:--";
    $("next-pass-time").textContent = state.observer
      ? "48h geometric forecast"
      : "Local horizon forecast";
    $("next-pass-elevation").textContent = "—";
  }
  if (state.lastScene && now() - state.lastScene > 15000) {
    error(
      "age",
      "Telemetry has stopped updating. Last received values remain on screen.",
    );
    $("connection").textContent = "TELEMETRY STALE";
    $("connection").className = "status-light pending";
  } else error("age");
}

// Canvas drawing projects provider latitude/longitude/altitude onto a spherical Earth.
function canvas(id) {
  const element = $(id),
    rect = element.getBoundingClientRect();
  if (rect.width < 1 || rect.height < 1) return null;
  const dpr = Math.min(devicePixelRatio || 1, 2),
    w = rect.width,
    h = rect.height;
  if (
    element.width !== Math.round(w * dpr) ||
    element.height !== Math.round(h * dpr)
  ) {
    element.width = Math.round(w * dpr);
    element.height = Math.round(h * dpr);
  }
  const ctx = element.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return { ctx, w, h };
}
function xyz(lon, lat, radius = 1) {
  const a = lon * RAD,
    b = lat * RAD;
  return [
    radius * Math.cos(b) * Math.cos(a),
    radius * Math.cos(b) * Math.sin(a),
    radius * Math.sin(b),
  ];
}
function project(vector) {
  const [x, y, z] = vector,
    c = Math.cos(state.angle),
    s = Math.sin(state.angle),
    front = x * c + y * s;
  return {
    x: -x * s + y * c,
    y: z * Math.cos(state.tilt) - front * Math.sin(state.tilt),
    z: z * Math.sin(state.tilt) + front * Math.cos(state.tilt),
  };
}
function globeLine(
  ctx,
  points,
  cx,
  cy,
  r,
  color,
  width = 1,
  dashed = false,
  orbital = false,
) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.setLineDash(dashed ? [3, 4] : []);
  ctx.beginPath();
  let drawing = false;
  for (const v of points) {
    const p = project(v),
      visible = p.z >= -0.006 || (orbital && Math.hypot(p.x, p.y) > 1.007);
    if (visible) {
      if (!drawing) ctx.moveTo(cx + p.x * r, cy - p.y * r);
      else ctx.lineTo(cx + p.x * r, cy - p.y * r);
    }
    drawing = visible;
  }
  ctx.stroke();
  ctx.setLineDash([]);
}
function drawGlobe() {
  if (state.page !== "orbit") return;
  const box = canvas("globe");
  if (!box) return;
  const { ctx, w, h } = box,
    cx = w / 2,
    cy = h / 2 - 2;
  const trackVectors =
    state.track?.path_globe_km
      .filter((v, index) => Date.parse(state.track.ground_track[index].utc) >= now())
      .map((v) => v.map((n) => n / EARTH)) || [];
  const maxRadius = trackVectors.length
    ? Math.max(1.22, ...trackVectors.map((v) => Math.hypot(...v)))
    : 1.22;
  const r = (Math.min(w * 0.39, h * 0.39) * state.zoom) / maxRadius;
  ctx.strokeStyle = "#34433955";
  ctx.lineWidth = 1;
  for (const [x, y] of [
    [20, 20],
    [w - 20, 20],
    [20, h - 20],
    [w - 20, h - 20],
  ]) {
    ctx.beginPath();
    ctx.moveTo(x, y + (y < h / 2 ? 7 : -7));
    ctx.lineTo(x, y);
    ctx.lineTo(x + (x < w / 2 ? 7 : -7), y);
    ctx.stroke();
  }
  ctx.strokeStyle = "#34433970";
  ctx.setLineDash([2, 5]);
  ctx.beginPath();
  ctx.moveTo(cx, 44);
  ctx.lineTo(cx, h - 44);
  ctx.moveTo(35, cy);
  ctx.lineTo(w - 35, cy);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.strokeStyle = "#6a806655";
  ctx.beginPath();
  ctx.arc(cx, cy, r + 9, 0, TAU);
  ctx.stroke();
  const gradient = ctx.createRadialGradient(
    cx - r * 0.35,
    cy - r * 0.45,
    0,
    cx,
    cy,
    r,
  );
  gradient.addColorStop(0, "#253b2a");
  gradient.addColorStop(0.7, "#172a1d");
  gradient.addColorStop(1, "#111c14");
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, TAU);
  ctx.fill();
  for (let lat = -60; lat <= 60; lat += 30)
    globeLine(
      ctx,
      Array.from({ length: 181 }, (_, i) => xyz(i * 2 - 180, lat)),
      cx,
      cy,
      r,
      lat === 0 ? "#4c684c" : colors.grid,
    );
  for (let lon = -180; lon < 180; lon += 30)
    globeLine(
      ctx,
      Array.from({ length: 91 }, (_, i) => xyz(lon, i * 2 - 90)),
      cx,
      cy,
      r,
      colors.grid,
    );
  for (const ring of state.land)
    globeLine(
      ctx,
      ring.map(([lon, lat]) => xyz(lon, lat)),
      cx,
      cy,
      r,
      colors.land,
      0.8,
    );
  ctx.strokeStyle = "#91b17e88";
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, TAU);
  ctx.stroke();
  if (trackVectors.length) {
    globeLine(ctx, trackVectors, cx, cy, r, colors.green, 1.2, false, true);
    globeLine(
      ctx,
      state.track.ground_track
        .filter((p) => Date.parse(p.utc) >= now())
        .map((p) => xyz(p.longitude_deg, p.latitude_deg, 1.002)),
      cx,
      cy,
      r,
      "#769c6977",
      0.9,
      true,
    );
  }
  if (state.observer) {
    const p = project(
      xyz(state.observer.longitude_deg, state.observer.latitude_deg, 1.003),
    );
    if (p.z > 0) {
      ctx.strokeStyle = colors.green;
      ctx.lineWidth = 1;
      ctx.strokeRect(cx + p.x * r - 3, cy - p.y * r - 3, 6, 6);
      ctx.font = "8px Consolas, monospace";
      ctx.fillStyle = colors.muted;
      ctx.fillText("GROUND STATION", cx + p.x * r + 9, cy - p.y * r + 3);
    }
  }
  const states = [...state.scene].sort(
    (a, b) =>
      Number(a.id === state.selected?.id) - Number(b.id === state.selected?.id),
  );
  for (const satellite of states) {
    const selected = satellite.id === state.selected?.id,
      p = project(satellite.position_globe_km.map((v) => v / EARTH));
    if (p.z < 0 && Math.hypot(p.x, p.y) < 1) continue;
    const x = cx + p.x * r,
      y = cy - p.y * r;
    ctx.fillStyle = selected ? colors.amber : colors.green;
    ctx.beginPath();
    ctx.arc(x, y, selected ? 3.5 : 1.8, 0, TAU);
    ctx.fill();
    if (selected) {
      ctx.strokeStyle = "#f5c77870";
      ctx.beginPath();
      ctx.arc(x, y, 10, 0, TAU);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x + 12, y);
      ctx.lineTo(x + 25, y - 13);
      ctx.lineTo(x + 47, y - 13);
      ctx.stroke();
      ctx.font = "9px Consolas, monospace";
      ctx.textAlign = x > w - 170 ? "right" : "left";
      const labelX = x > w - 170 ? x - 14 : x + 29;
      ctx.fillText(satellite.name, labelX, y - 21);
      ctx.fillStyle = colors.muted;
      ctx.fillText(`${fmt(satellite.altitude_km)} km`, labelX, y - 7);
      ctx.textAlign = "left";
    }
  }
  ctx.fillStyle = "#647b60";
  ctx.font = "8px Consolas, monospace";
  ctx.fillText("N", cx - 3, cy - r - 15);
  ctx.fillText("S", cx - 3, cy + r + 23);
}
function drawSky() {
  const box = canvas("sky-plot");
  if (!box) return;
  const { ctx, w, h } = box,
    cx = w / 2,
    cy = h / 2,
    r = Math.min(w, h) * 0.36;
  ctx.strokeStyle = "#3c5340";
  ctx.lineWidth = 0.7;
  [1, 2 / 3, 1 / 3].forEach((fraction) => {
    ctx.beginPath();
    ctx.arc(cx, cy, r * fraction, 0, TAU);
    ctx.stroke();
  });
  ctx.beginPath();
  ctx.moveTo(cx - r, cy);
  ctx.lineTo(cx + r, cy);
  ctx.moveTo(cx, cy - r);
  ctx.lineTo(cx, cy + r);
  ctx.stroke();
  ctx.fillStyle = colors.muted;
  ctx.font = "9px Consolas, monospace";
  ctx.textAlign = "center";
  ctx.fillText("N", cx, cy - r - 18);
  ctx.fillText("S", cx, cy + r + 23);
  ctx.fillText("E", cx + r + 18, cy + 3);
  ctx.fillText("W", cx - r - 18, cy + 3);
  ctx.font = "7px Consolas, monospace";
  ctx.fillStyle = "#657e63";
  ctx.fillText("30°", cx + 13, cy - (r * 2) / 3 + 11);
  ctx.fillText("60°", cx + 13, cy - r / 3 + 11);
  ctx.fillText("90°", cx + 13, cy + 11);
  if (state.pass) {
    const points = state.pass.sky_path.map((p) => {
      const radius = (r * (90 - p.elevation_deg)) / 90;
      return [
        cx + radius * Math.sin(p.azimuth_deg * RAD),
        cy - radius * Math.cos(p.azimuth_deg * RAD),
      ];
    });
    ctx.strokeStyle = colors.green;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    points.forEach(([x, y], i) => {
      if (i) ctx.lineTo(x, y);
      else ctx.moveTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
    points.forEach(([x, y]) => {
      ctx.fillStyle = colors.amber;
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, TAU);
      ctx.fill();
    });
    ctx.fillStyle = colors.amber;
    ctx.font = "8px Consolas, monospace";
    ctx.fillText("RISE", points[0][0], points[0][1] + 15);
    ctx.fillText("SET", points.at(-1)[0], points.at(-1)[1] - 10);
    ctx.fillText("PEAK", points[1][0], points[1][1] - 10);
  }
  ctx.textAlign = "left";
}
function chart(id, key) {
  const box = canvas(id);
  if (!box) return;
  const { ctx, w, h } = box,
    samples = state.history.map((s) => s[key]).filter((value) => value != null && Number.isFinite(value));
  ctx.strokeStyle = "#344339";
  ctx.lineWidth = 0.6;
  ctx.beginPath();
  ctx.moveTo(0, h - 12);
  ctx.lineTo(w, h - 12);
  ctx.stroke();
  ctx.font = "7px Consolas, monospace";
  ctx.fillStyle = colors.muted;
  if (samples.length < 2) {
    ctx.fillText(key === "velocity_km_s" ? "NOT PROVIDED BY N2YO" : "COLLECTING SESSION SAMPLES…", 0, h - 2);
    return;
  }
  const min = Math.min(...samples),
    max = Math.max(...samples),
    delta = Math.max(max - min, key === "altitude_km" ? 0.01 : 0.00001);
  ctx.strokeStyle = colors.green;
  ctx.lineWidth = 1;
  ctx.beginPath();
  samples.forEach((value, i) => {
    const x = (i / (samples.length - 1)) * w,
      y = 7 + (1 - (value - min) / delta) * (h - 26);
    if (i) ctx.lineTo(x, y);
    else ctx.moveTo(x, y);
  });
  ctx.stroke();
  ctx.fillText(
    `${samples.length} SAMPLES / ${fmt(min, 3)} – ${fmt(max, 3)}`,
    0,
    h - 2,
  );
}
function drawAuxiliary() {
  drawSky();
  chart("altitude-chart", "altitude_km");
  chart("velocity-chart", "velocity_km_s");
}

document.querySelectorAll(".page-tab").forEach((button) => {
  button.onclick = () => page(button.dataset.page);
});
$("view-passes").onclick = () => page("passes");
$("catalog-button").onclick = () => {
  $("catalog-dialog").showModal();
  $("satellite-search").focus();
};
document.querySelectorAll(".close-dialog").forEach((button) => {
  button.onclick = () => button.closest("dialog").close();
});
function openStation() {
  $("observer-name").value = state.observer?.name || "Home station";
  $("observer-lat").value = state.observer?.latitude_deg ?? "";
  $("observer-lon").value = state.observer?.longitude_deg ?? "";
  $("observer-elevation").value = state.observer?.elevation_m ?? 0;
  $("station-error").textContent = "";
  $("station-dialog").showModal();
}
$("station-button").onclick = openStation;
document.querySelectorAll(".configure-station").forEach((button) => {
  button.onclick = openStation;
});
$("station-form").onsubmit = async (event) => {
  event.preventDefault();
  $("save-station").disabled = true;
  const value = {
    name: $("observer-name").value.trim(),
    latitude_deg: Number($("observer-lat").value),
    longitude_deg: Number($("observer-lon").value),
    elevation_m: Number($("observer-elevation").value),
  };
  try {
    state.observer = await api("observer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(value),
    });
    state.token++;
    state.passes = [];
    state.pass = null;
    stationLabel();
    $("station-dialog").close();
    log(`Ground station saved / ${value.name}`, true);
    await Promise.allSettled([
      refreshScene(true),
      refreshTrack(),
      refreshPasses(true),
    ]);
  } catch (exc) {
    $("station-error").textContent = exc.message;
  } finally {
    $("save-station").disabled = false;
  }
};
$("group-select").onchange = async () => {
  clearSelection();
  state.group = $("group-select").value;
  state.query = "";
  state.satellites = [];
  state.total = 0;
  $("satellite-search").value = "";
  $("target-name").textContent = "Acquiring catalog…";
  $("target-group").textContent =
    $("group-select").selectedOptions[0].text.toUpperCase();
  $("globe-empty").textContent = "ACQUIRING SATELLITE CATALOG…";
  renderCatalog();
  await loadCatalog({ choose: true });
};
$("satellite-search").oninput = () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.query = $("satellite-search").value.trim();
    loadCatalog();
  }, 250);
};
$("load-more").onclick = () => loadCatalog({ append: true });
function cycleSatellite(delta) {
  if (!state.satellites.length) return;
  const i = state.satellites.findIndex((sat) => sat.id === state.selected?.id);
  selectSatellite(
    state.satellites[
      (i + delta + state.satellites.length) % state.satellites.length
    ],
  );
}
$("previous-satellite").onclick = () => cycleSatellite(-1);
$("next-satellite").onclick = () => cycleSatellite(1);
$("elevation-mask").onchange = () => {
  state.passes = [];
  state.pass = null;
  renderPasses();
  refreshPasses(true);
};
$("rotate-button").onclick = () => setRotation(!state.rotating);
setRotation(state.rotating);
$("focus-button").onclick = () => {
  const selected = state.scene.find((s) => s.id === state.selected?.id);
  if (selected) {
    state.angle = selected.longitude_deg * RAD;
    state.tilt = selected.latitude_deg * RAD;
    setRotation(false);
  }
};
function effects(value) {
  document.body.classList.toggle("crt", value);
  $("effects-button").textContent = value ? "CRT ON" : "CRT OFF";
  $("effects-button").setAttribute("aria-pressed", String(value));
  pref("crt", value ? "on" : "off");
}
effects(pref("crt") !== "off");
$("effects-button").onclick = () =>
  effects(!document.body.classList.contains("crt"));
$("fullscreen-button").onclick = async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch (exc) {
    log("Fullscreen unavailable in this browser.");
  }
};
document.addEventListener("keydown", (event) => {
  if (
    event.target.matches("input, select, textarea") ||
    document.querySelector("dialog[open]")
  )
    return;
  if (["1", "2", "3"].includes(event.key))
    page(["orbit", "telemetry", "passes"][Number(event.key) - 1]);
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    cycleSatellite(-1);
  }
  if (event.key === "ArrowRight") {
    event.preventDefault();
    cycleSatellite(1);
  }
});
let pointer = null;
$("globe").onpointerdown = (event) => {
  pointer = { x: event.clientX, y: event.clientY };
  $("globe").setPointerCapture(event.pointerId);
  setRotation(false);
};
$("globe").onpointermove = (event) => {
  if (!pointer) return;
  state.angle -= (event.clientX - pointer.x) * 0.007;
  state.tilt = Math.max(
    -1.4,
    Math.min(1.4, state.tilt + (event.clientY - pointer.y) * 0.007),
  );
  pointer = { x: event.clientX, y: event.clientY };
};
$("globe").onpointerup = $("globe").onpointercancel = () => {
  pointer = null;
};
$("globe").addEventListener(
  "wheel",
  (event) => {
    event.preventDefault();
    state.zoom = Math.max(
      0.5,
      Math.min(2.5, state.zoom - event.deltaY * 0.001),
    );
  },
  { passive: false },
);
window.addEventListener("resize", drawAuxiliary);
let lastFrame = 0;
function animate(time) {
  if (time - lastFrame >= 33) {
    const elapsed = Math.min(time - lastFrame, 100);
    if (state.rotating && state.page === "orbit")
      state.angle += elapsed * 0.000045;
    drawGlobe();
    lastFrame = time;
  }
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
tickClock();
setInterval(tickClock, 1000);
setInterval(() => {
  if (!document.hidden) refreshScene();
}, 3000);
setInterval(() => {
  if (!document.hidden) refreshTrack();
}, 60000);
setInterval(() => {
  if (!document.hidden) refreshPasses();
}, 60000);
setInterval(() => {
  if (!document.hidden) status();
}, 30000);
log("ORBIT terminal initialized.", true);
log("CelesTrak OMM / local SGP4 propagation.");
fetch("/static/land.geojson")
  .then((response) => response.json())
  .then((data) => {
    state.land = data.features.flatMap((feature) =>
      feature.geometry.type === "MultiPolygon"
        ? feature.geometry.coordinates.flatMap((p) => p)
        : feature.geometry.coordinates,
    );
    drawAuxiliary();
  })
  .catch(() => log("Basemap unavailable; coordinate grid remains active."));
await status();
await loadCatalog({ choose: true });
