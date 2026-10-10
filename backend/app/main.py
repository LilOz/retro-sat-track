import os
from pathlib import Path
from threading import RLock
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.models import Observer
from app.tracking.catalog import GROUPS, Catalog, CatalogUnavailable
from app.tracking.propagation import PropagationError, Tracker, iso, utcnow
from app.tracking.visibility import PassPredictor

Group = Literal["stations", "starlink", "science", "gps-ops"]
STATIC = Path(__file__).parent / "static"
DEFAULT_DATA = Path(__file__).resolve().parents[2] / ".data"


def create_app(data_dir=None, catalog=None):
    directory = Path(data_dir or os.environ.get("SAT_TRACK_DATA_DIR", DEFAULT_DATA))
    directory.mkdir(parents=True, exist_ok=True)
    catalog = catalog or Catalog(directory / "catalog")
    tracker, observer_path, lock = Tracker(), directory / "observer.json", RLock()
    predictor, observer = PassPredictor(tracker), None
    if observer_path.exists():
        try:
            observer = Observer.model_validate_json(observer_path.read_text())
        except ValueError, OSError:
            pass
    app = FastAPI(title="ORBIT / Retro Satellite Terminal", version="0.1.0")
    app.state.catalog, app.state.tracker, app.state.predictor = (
        catalog,
        tracker,
        predictor,
    )

    @app.exception_handler(CatalogUnavailable)
    async def catalog_error(request, exc):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(PropagationError)
    async def propagation_error(request, exc):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    def record_for(satellite_id, group):
        try:
            return catalog.record(satellite_id, group)
        except KeyError:
            raise HTTPException(404, "Satellite is not in the selected group")

    def current_observer():
        with lock:
            return observer or Observer(
                name="Unset (equator reference)", latitude_deg=0, longitude_deg=0
            )

    @app.get("/api/v1/status")
    def status():
        with lock:
            saved = observer.model_dump() if observer else None
        return {
            "status": "ok",
            "utc": iso(utcnow()),
            "source": "CelesTrak GP / OMM JSON",
            "propagator": "SGP4 / Skyfield",
            "observer": saved,
            "groups": [
                {"id": key, "name": name, **catalog.freshness(key)}
                for key, name in GROUPS.items()
            ],
        }

    @app.post("/api/v1/observer")
    def save_observer(value: Observer):
        nonlocal observer
        with lock:
            temp = observer_path.with_suffix(".tmp")
            temp.write_text(value.model_dump_json())
            temp.replace(observer_path)
            observer = value
        return value

    @app.get("/api/v1/satellites")
    def satellites(
        group: Group = "stations",
        q: str = Query(default="", max_length=100),
        limit: int = Query(default=200, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        records = catalog.ensure(group)["records"]
        records = sorted(
            records, key=lambda r: (int(r["NORAD_CAT_ID"]) != 25544, r["OBJECT_NAME"])
        )
        if q:
            records = [
                r
                for r in records
                if q.lower() in r["OBJECT_NAME"].lower() or q in str(r["NORAD_CAT_ID"])
            ]
        return {
            "group": group,
            "total": len(records),
            "offset": offset,
            "catalog": catalog.freshness(group),
            "satellites": [
                {
                    "id": int(r["NORAD_CAT_ID"]),
                    "name": r["OBJECT_NAME"],
                    "epoch": r["EPOCH"],
                    "inclination_deg": r["INCLINATION"],
                }
                for r in records[offset : offset + limit]
            ],
        }

    @app.get("/api/v1/scene")
    def scene(
        group: Group = "stations",
        selected_id: int = Query(default=25544, ge=1),
        limit: int = Query(default=12, ge=1, le=24),
    ):
        records = catalog.ensure(group)["records"]
        selected = record_for(selected_id, group)
        stride = max(1, len(records) // max(1, limit - 1))
        preview = [selected] + [
            r
            for r in records[::stride]
            if r["NORAD_CAT_ID"] != selected["NORAD_CAT_ID"]
        ][: limit - 1]
        now, location, states = utcnow(), current_observer(), []
        for record in preview:
            try:
                states.append(tracker.state(record, location, now))
            except PropagationError:
                if record is selected:
                    raise
        return {
            "utc": iso(now),
            "states": states,
            "catalog": catalog.freshness(group),
            "observer_configured": observer is not None,
        }

    @app.get("/api/v1/satellites/{satellite_id}/state")
    def state(satellite_id: int, group: Group = "stations"):
        return tracker.state(record_for(satellite_id, group), current_observer())

    @app.get("/api/v1/satellites/{satellite_id}/track")
    def track(
        satellite_id: int,
        group: Group = "stations",
        samples: int = Query(default=180, ge=24, le=360),
    ):
        return tracker.track(record_for(satellite_id, group), samples)

    @app.get("/api/v1/passes")
    def passes(
        satellite_id: int = Query(default=25544, ge=1),
        group: Group = "stations",
        lat: Annotated[float | None, Query(ge=-90, le=90, allow_inf_nan=False)] = None,
        lon: Annotated[
            float | None, Query(ge=-180, le=180, allow_inf_nan=False)
        ] = None,
        elevation_m: float = Query(default=0, ge=-500, le=9000, allow_inf_nan=False),
        hours: int = Query(default=48, ge=1, le=72),
        min_elevation: float = Query(default=10, ge=0, le=80),
    ):
        if (lat is None) != (lon is None):
            raise HTTPException(422, "Provide both lat and lon")
        if lat is not None:
            location = Observer(
                latitude_deg=lat, longitude_deg=lon, elevation_m=elevation_m
            )
        elif observer is not None:
            location = current_observer()
        else:
            raise HTTPException(
                409, "Set your ground station location to predict passes"
            )
        return predictor.predict(
            record_for(satellite_id, group), location, hours, min_elevation
        )

    @app.get("/api/v1/passes/{pass_id}")
    def pass_detail(pass_id: str):
        detail = predictor.detail(pass_id)
        if detail is None:
            raise HTTPException(404, "Pass not found; request the pass list first")
        return detail

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
