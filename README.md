# ORBIT / Retro Satellite Tracking Terminal

A local PC satellite terminal with a phosphor-green globe, orbital telemetry and ground-station pass predictions. Python calculates orbits from **CelesTrak GP orbital elements**; a browser draws the terminal. The versioned JSON API can support an ESP32 display later.

![ORBIT terminal preview](docs/orbit-preview.jpg)

## Run on your PC

Requires Python **3.11+**, a modern browser and internet access for the first catalog download. No Node.js, API key, external fonts or frontend build step is required.

Linux, macOS or WSL, from this repository:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './backend[dev]'
python run.py
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
.\.venv\Scripts\python.exe run.py
```

Open **http://127.0.0.1:8000** if your browser does not open automatically. For WSL, use `python run.py --no-browser` and open that address in your Windows browser. Stop with Ctrl+C. Use `--port 8080` if port 8000 is busy.

Select **Set ground station** and enter your name, latitude, longitude and elevation. The app starts with the ISS and leaves coordinates unset until saved. Coordinates stay in the local data directory and are never sent to CelesTrak.

## Three displays

- **01 / Orbital situation:** rotating Earth with bundled coastlines, grid, actual-altitude orbit, spacecraft markers, telemetry, next-pass countdown and a compact scrolling event log. The separate ground-track map is omitted to suit the eventual embedded display. Drag to rotate, scroll to zoom, or select **Find object**.
- **02 / Telemetry:** altitude, inertial velocity, mean inclination, period, latitude/longitude, eccentricity, estimated mean orbital phase and observer look angles. Charts accumulate real samples during the current session.
- **03 / Pass prediction:** 48-hour forecast with rise, culmination and set, maximum elevation, compass directions, duration and a polar sky plot. Select a row to inspect its path; choose an elevation mask from 0 to 30 degrees.

Groups: **space stations, Starlink, science and operational GPS**. Search by name or NORAD ID and load more results. The globe shows up to 12 representative objects including the selection. OMM JSON supports six-digit and larger catalog IDs.

Keyboard: **1 / 2 / 3** switch pages; **left / right arrows** cycle listed objects. CRT texture and fullscreen are optional. Reduced-motion preferences disable automatic rotation. The layout adapts to narrower displays.

## Data and prediction behaviour

Positions are **SGP4 predictions for current UTC**, not measurements streamed from spacecraft. Telemetry refreshes every three seconds; paths and forecasts refresh every minute. Element age and catalog download age are shown separately. Elements more than seven days from their epoch and telemetry that stops updating trigger warnings.

CelesTrak is queried with `https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=JSON`. Groups download lazily and are cached for two hours. Failed attempts also trigger a persisted two-hour cooldown to prevent repeated requests on errors. Cached data remains available with a warning. With no successful download, the app shows an unavailable state and never substitutes simulated or fixture data.

Passes are **geometric** opportunities above the elevation mask. Sunlight, local darkness, terrain, refraction, clouds and optical visibility are not evaluated. Ongoing passes retain their actual rise time. A continuously above-mask object may have no complete rise-to-set window. This is a hobby display, not spacecraft navigation data.

Altitude is WGS84 ellipsoid height; speed is geocentric inertial velocity magnitude. Inclination and period come from mean elements. Estimated mean phase advances epoch mean anomaly using mean motion. Orbit samples use the Earth frame frozen at the track timestamp; ground-track samples account for Earth rotation at each timestamp.

## Architecture

```text
retro-sat-track/
├── run.py
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py            # FastAPI and saved observer
│   │   ├── models.py
│   │   ├── tracking/
│   │   │   ├── catalog.py     # CelesTrak, disk cache and cooldowns
│   │   │   ├── propagation.py # SGP4, state and paths
│   │   │   └── visibility.py  # Geometric passes and sky paths
│   │   └── static/            # Browser UI and bundled basemap
│   └── tests/                 # Offline regression checks
└── .github/workflows/ci.yml
```

Runtime files live in ignored `.data/`; override with `SAT_TRACK_DATA_DIR`. Firmware and printable enclosure design are future phases. This MVP runs on your PC.

## API for a future ESP client

Interactive docs: **http://127.0.0.1:8000/docs**. Fields include units in their names; UTC timestamps are ISO 8601. Satellite endpoints default to `group=stations`; use `group=starlink`, `science` or `gps-ops` as needed.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/status` | Health, UTC, saved observer, catalog freshness and errors |
| `GET /api/v1/satellites?group=stations&q=ISS&limit=150&offset=0` | Searchable, paginated catalog |
| `GET /api/v1/satellites/25544/state` | Current orbit, geography and observer look angles |
| `GET /api/v1/satellites/25544/track?samples=180` | Orbit vectors in Earth-fixed kilometres and timed ground track |
| `GET /api/v1/scene?selected_id=25544&limit=12` | Bounded set of current states for the globe |
| `GET /api/v1/passes?satellite_id=25544&hours=48&min_elevation=10` | Passes for the saved observer |
| `GET /api/v1/passes?satellite_id=25544&lat=51.5&lon=-0.12&elevation_m=0` | Passes for explicit coordinates without saving |
| `GET /api/v1/passes/{id}` | Detailed events and sky path; request the list first |
| `POST /api/v1/observer` | Save the observer locally |

Observer body:

```json
{"name":"Home station","latitude_deg":51.5,"longitude_deg":-0.12,"elevation_m":0}
```

Pass IDs belong to the in-memory forecast cache; request the list again after restart. The server binds to loopback by default. For a later ESP experiment, `python run.py --host 0.0.0.0 --no-browser` exposes the service on your LAN. The MVP has no API authentication and should not be exposed to the public internet.

## Checks

```sh
cd backend
python -m pytest -q
```

Offline checks cover published Skyfield position and pass examples, altitude/speed bounds, orbit versus ground-track coordinates, ongoing passes, persistent cache/cooldown behaviour, API responses, observer validation/persistence and extended catalog IDs. CI runs on Python 3.11 and 3.12.

## Attribution

- [CelesTrak GP documentation and request policy](https://celestrak.org/NORAD/documentation/gp-data-formats.php).
- [Skyfield satellite calculations](https://rhodesmill.org/skyfield/earth-satellites.html), using SGP4.
- Bundled [Natural Earth 1:110m land](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson) is [public domain](https://www.naturalearthdata.com/about/terms-of-use/).
- Retro inspiration: [trehn/termtrack](https://github.com/trehn/termtrack). This implementation uses its own interface and rendering code.
