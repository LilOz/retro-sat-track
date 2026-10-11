# ORBIT / Retro Satellite Tracking Terminal

A PC satellite terminal with a phosphor-green globe, telemetry and local pass forecasts. **N2YO provides positions and pass predictions**; CelesTrak supplies the searchable catalog and basic orbital metadata. The local Python service handles requests, caching and API-key storage, and a browser renders the terminal. The versioned JSON API can serve an ESP32 later.

![ORBIT terminal preview](docs/orbit-preview.jpg)

The preview image shows the earlier local-solver display; the current globe shows a short predicted path and the selected satellite.

## Run on your PC

Requirements: Python **3.14**, [uv](https://docs.astral.sh/uv/getting-started/installation/), a modern browser, internet access and a free **[N2YO API key](https://www.n2yo.com/api/)**. Register with N2YO and generate a key on your account profile. Do not commit or paste the key into frontend code.

From the repository root on Linux, macOS or WSL:

```sh
uv sync --locked
export N2YO_API_KEY='your-key'
uv run --locked run.py
```

On Windows PowerShell:

```powershell
uv sync --locked
$env:N2YO_API_KEY = 'your-key'
uv run --locked run.py
```

The environment variable applies to that terminal session. Set it again when starting a new session. The app reads it at startup; restart after changing it. Without a key, the terminal shows **API KEY REQUIRED** and tracking routes return a clear configuration error. The key is never returned through the local API.

uv creates `.venv` using `.python-version` and the committed `uv.lock`; manual activation is optional. Open **http://127.0.0.1:8000** if the browser does not open automatically. For WSL, use `uv run --locked run.py --no-browser` and open the address in your Windows browser. Stop with Ctrl+C; use `--port 8080` if necessary.

Select **Set ground station** to save your name, latitude, longitude and elevation. Coordinates are stored locally and **sent to N2YO** for observer look angles and pass forecasts. They are not sent to CelesTrak. Positions can be shown before saving a location, using an equator reference internally; observer readouts and forecasts require your own coordinates.

## Three displays

- **01 / Orbital situation:** rotating Earth with local coastlines and a grid, the selected spacecraft, its upcoming path, altitude/position readouts, next-pass countdown and event log. Drag to rotate, scroll to zoom or select **Find object**. There is no separate ground-track map.
- **02 / Telemetry:** N2YO altitude, latitude/longitude and observer azimuth/elevation; CelesTrak inclination, eccentricity, period and element epoch. The altitude chart records predictions during the current session.
- **03 / Pass prediction:** a 48-hour forecast with rise, peak and set, maximum elevation, directions, duration and a schematic sky diagram. The diagram connects the three events supplied by N2YO; it is not a sampled trajectory.

Groups: **space stations, Starlink, science and operational GPS**. Search by name/NORAD ID and load more results. The globe tracks one selected object to keep upstream request use predictable. CelesTrak OMM JSON supports extended catalog IDs, and N2YO accepts numeric NORAD IDs.

Keyboard: **1 / 2 / 3** switch pages; **left / right arrows** cycle listed objects. CRT texture and fullscreen are optional. Reduced-motion preferences disable automatic rotation.

## Data and provider limits

N2YO positions are predictions evaluated at timestamps, not measurements streamed from spacecraft. The backend requests **300 consecutive one-second positions** and shares the batch between `/state`, `/scene` and `/track`. The browser polls every three seconds; a stationary selection normally needs about **12 position requests per hour**. Track refreshes reuse the same batch.

A batch covers up to five minutes, so the globe shows the **remaining predicted segment**, not a complete orbit. API samples include timestamps and `window_seconds`; a cached batch's displayed window shrinks until it is refreshed. Longitude/latitude/altitude are projected onto the spherical globe for display. These vectors are labeled `position_globe_km` and `path_globe_km`, not navigation-grade reference-frame coordinates.

N2YO's positions response does not supply **velocity, orbital phase or slant range**. Those fields are `null` in the API and show an em dash in the terminal; they are not estimated from a different orbit model. Inclination and eccentricity come from CelesTrak; period is `1440 / mean_motion` minutes. The displayed CelesTrak epoch describes this metadata, not necessarily the elements N2YO used.

Pass forecasts use N2YO's **radio-pass** endpoint and a 30-minute cache. **Minimum peak elevation** filters the pass's highest elevation; rise/set remain horizon crossings. This differs from predicting crossings of a raised elevation mask. Returned events that have ended are filtered out, and forecasts are clipped by rise time to the requested window. Ongoing passes are retained if present in the upstream response; the provider may omit a pass already in progress.

Sunlight, local darkness, terrain and weather are not evaluated. A geometric pass does not guarantee optical visibility. The sky diagram uses horizon/peak/horizon markers with dashed connecting lines to indicate its schematic nature.

[N2YO documents](https://www.n2yo.com/api/) hourly limits of 1,000 position requests and 100 radio-pass requests. The backend conservatively caps itself at 900 and 90 respectively per rolling hour within a process. Rapid selection changes and other applications using the same key also affect upstream limits. Provider errors pause that endpoint for five minutes; quota errors pause it for an hour. Invalid keys, mismatched data, invalid payloads and expired position batches produce availability errors. There is **no automatic switch to local propagation**.

Internet access is needed when a position batch expires or a forecast needs refreshing. The UI warns when position timestamps become stale and leaves the last received values visible. It does not silently replace them with fixtures or label expired samples as current.

CelesTrak catalogs download lazily using `gp.php?GROUP=...&FORMAT=JSON`, with the existing two-hour disk cache and persisted failure cooldown. A cached catalog can remain usable with a warning. Catalog download age and metadata element age are separate from N2YO position freshness.

## Architecture

```text
CelesTrak catalog -> catalog.py -> selection and orbital metadata
N2YO REST API     -> n2yo.py    -> position batches and radio passes
                                  |
Saved observer ------------------+-> FastAPI -> browser terminal
                                             -> future ESP32 client
```

| File | Responsibility |
| --- | --- |
| `run.py` | Local Uvicorn launcher and optional browser opening. |
| `backend/app/main.py` | FastAPI routes, static assets and observer persistence. |
| `backend/app/tracking/catalog.py` | CelesTrak catalog validation, disk cache and cooldowns. |
| `backend/app/tracking/n2yo.py` | Typed N2YO responses, batching, forecast cache, request budgets and safe error messages. |
| `backend/app/tracking/common.py` | UTC formatting and spherical display-coordinate conversion. |
| `backend/app/models.py` / `schemas.py` | Observer validation and typed JSON payloads. |
| `backend/app/static/` | Plain HTML, CSS and Canvas JavaScript with local basemap assets. |

Runtime libraries are **FastAPI**, **Uvicorn** and **HTTPX**, with Pydantic supplied through FastAPI. No frontend framework, Node.js or build step is required. Regular locks coordinate shared caches and settings within the backend process. Runtime files live in ignored `.data/`; override with `SAT_TRACK_DATA_DIR`.

The previous `propagation.py`, `visibility.py`, Skyfield stubs and their regression checks are retained but are **not wired into the application**. Skyfield is now a development dependency for those existing checks. Adding local propagation again requires an explicit implementation decision if provider limits or missing metrics justify it.

## API for a future ESP client

Interactive docs: **http://127.0.0.1:8000/docs**. Fields include units; timestamps are ISO 8601 UTC. Satellite routes default to `group=stations`; other groups are `starlink`, `science` and `gps-ops`.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/status` | UTC, observer, provider configuration status and catalog freshness. |
| `GET /api/v1/satellites?group=stations&q=ISS&limit=150&offset=0` | Searchable, paginated catalog. |
| `GET /api/v1/satellites/25544/state` | Current N2YO sample plus catalog metadata; unavailable metrics are null. |
| `GET /api/v1/satellites/25544/track?samples=180` | Remaining five-minute segment, timed surface path and spherical display vectors. May return fewer samples near batch expiry. |
| `GET /api/v1/scene?selected_id=25544` | Current selected state for the globe; no background objects. |
| `GET /api/v1/passes?satellite_id=25544&hours=48&min_elevation=10` | Horizon-to-horizon passes with a minimum peak elevation. |
| `GET /api/v1/passes?satellite_id=25544&lat=51.5&lon=-0.12&elevation_m=0` | Forecast for explicit coordinates without saving. |
| `GET /api/v1/passes/{id}` | Cached event details; request the list first. |
| `POST /api/v1/observer` | Save the observer locally. |

Observer body:

```json
{"name":"Home station","latitude_deg":51.5,"longitude_deg":-0.12,"elevation_m":0}
```

Pass IDs belong to the in-memory forecast cache; request the list again after restart. The service binds to loopback by default. A later ESP can use `uv run --locked run.py --host 0.0.0.0 --no-browser` to access it on your LAN. The MVP is unauthenticated and should not be publicly exposed. ESP firmware and a printable enclosure remain future phases.

## Development and CI

```sh
uv sync --locked --dev
uv run --locked ruff check --fix .
uv run --locked black .
```

CI checks Black formatting, Ruff lint/import ordering/annotations and Pyright types before running the existing offline backend suite. It uses Python 3.14 and locked dependencies. Existing API fixtures now mock N2YO; catalog and retained solver checks remain offline.

```sh
uv run --locked black --check --diff .
uv run --locked ruff check .
uv run --locked pyright
uv run --locked pytest -q
```

Pyright settings in `pyproject.toml` cover the backend import path, `.venv`, Python version and retained Skyfield stubs. For an editor using the Pyright language server, use `uv run --locked pyright-langserver --stdio` from the repository root. For VS Code/Pylance in WSL, select `.venv/bin/python` and reload the language server after configuration changes.

## Attribution

- [N2YO API documentation](https://www.n2yo.com/api/) for position and radio-pass predictions.
- [CelesTrak GP documentation](https://celestrak.org/NORAD/documentation/gp-data-formats.php) for catalog metadata.
- [Skyfield](https://rhodesmill.org/skyfield/earth-satellites.html) supports the retained, inactive local solver.
- Bundled [Natural Earth 1:110m land](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson) is [public domain](https://www.naturalearthdata.com/about/terms-of-use/).
- Retro inspiration: [trehn/termtrack](https://github.com/trehn/termtrack). This implementation uses its own interface and rendering code.
