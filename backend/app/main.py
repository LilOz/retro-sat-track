import os
from pathlib import Path
from threading import Lock
from typing import Annotated, cast

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.models import Observer
from app.schemas import (
    Group,
    ObserverData,
    OrbitalElements,
    ProviderForecast,
    ProviderScene,
    ProviderState,
    ProviderTrack,
    SatelliteList,
    SatellitePass,
    StatusResponse,
)
from app.tracking.catalog import GROUPS, Catalog, CatalogUnavailable
from app.tracking.common import iso, utcnow
from app.tracking.n2yo import N2YO, ProviderUnavailable

STATIC = Path(__file__).parent / "static"
DEFAULT_DATA = Path(__file__).resolve().parents[2] / ".data"


def create_app(
    data_dir: str | Path | None = None,
    catalog: Catalog | None = None,
    provider: N2YO | None = None,
) -> FastAPI:
    directory = Path(data_dir or os.environ.get("SAT_TRACK_DATA_DIR", DEFAULT_DATA))
    directory.mkdir(parents=True, exist_ok=True)
    catalog = catalog or Catalog(directory / "catalog")
    provider = provider or N2YO()
    observer_path, lock = directory / "observer.json", Lock()
    observer: Observer | None = None
    if observer_path.exists():
        try:
            observer = Observer.model_validate_json(observer_path.read_text())
        except ValueError, OSError:
            pass
    app = FastAPI(title="ORBIT / Retro Satellite Terminal", version="0.1.0")
    app.state.catalog, app.state.provider = catalog, provider

    @app.exception_handler(CatalogUnavailable)
    async def catalog_error(request: Request, exc: CatalogUnavailable) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(ProviderUnavailable)
    async def provider_error(
        request: Request, exc: ProviderUnavailable
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    def record_for(satellite_id: int, group: Group) -> OrbitalElements:
        try:
            return catalog.record(satellite_id, group)
        except KeyError:
            raise HTTPException(404, "Satellite is not in the selected group")

    def current_observer() -> Observer:
        with lock:
            return observer or Observer(
                name="Unset (equator reference)", latitude_deg=0, longitude_deg=0
            )

    @app.get("/api/v1/status")
    def status() -> StatusResponse:
        with lock:
            saved = cast(ObserverData, observer.model_dump()) if observer else None
        return {
            "status": "ok",
            "utc": iso(utcnow()),
            "source": "N2YO positions and radio passes / CelesTrak catalog",
            "provider_configured": provider.configured,
            "provider_error": (
                None
                if provider.configured
                else "Set N2YO_API_KEY on the backend and restart to enable tracking."
            ),
            "observer": saved,
            "groups": [
                {"id": key, "name": name, **catalog.freshness(key)}
                for key, name in GROUPS.items()
            ],
        }

    @app.post("/api/v1/observer")
    def save_observer(value: Observer) -> Observer:
        nonlocal observer
        with lock:
            temp = observer_path.with_suffix(".tmp")
            temp.write_text(value.model_dump_json())
            temp.replace(observer_path)
            observer = value
        return value

    def catalog_order(record: OrbitalElements) -> tuple[bool, str]:
        return int(record["NORAD_CAT_ID"]) != 25544, record["OBJECT_NAME"]

    @app.get("/api/v1/satellites")
    def satellites(
        group: Group = "stations",
        q: str = Query(default="", max_length=100),
        limit: int = Query(default=200, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> SatelliteList:
        records = catalog.ensure(group)["records"]
        records = sorted(records, key=catalog_order)
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
    ) -> ProviderScene:
        # Track only the selection to keep the upstream request budget predictable.
        selected = record_for(selected_id, group)
        now, location = utcnow(), current_observer()
        return {
            "utc": iso(now),
            "states": [provider.state(selected, location, now)],
            "catalog": catalog.freshness(group),
            "observer_configured": observer is not None,
        }

    @app.get("/api/v1/satellites/{satellite_id}/state")
    def state(satellite_id: int, group: Group = "stations") -> ProviderState:
        return provider.state(record_for(satellite_id, group), current_observer())

    @app.get("/api/v1/satellites/{satellite_id}/track")
    def track(
        satellite_id: int,
        group: Group = "stations",
        samples: int = Query(default=180, ge=24, le=360),
    ) -> ProviderTrack:
        return provider.track(
            record_for(satellite_id, group), current_observer(), samples
        )

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
        min_elevation: float = Query(
            default=10,
            ge=0,
            le=80,
            allow_inf_nan=False,
            description="Minimum pass peak elevation; rise/set remain horizon crossings",
        ),
    ) -> ProviderForecast:
        if (lat is None) != (lon is None):
            raise HTTPException(422, "Provide both lat and lon")
        if lat is not None and lon is not None:
            location = Observer(
                latitude_deg=lat, longitude_deg=lon, elevation_m=elevation_m
            )
        elif observer is not None:
            location = current_observer()
        else:
            raise HTTPException(
                409, "Set your ground station location to predict passes"
            )
        return provider.predict(
            record_for(satellite_id, group), location, hours, min_elevation
        )

    @app.get("/api/v1/passes/{pass_id}")
    def pass_detail(pass_id: str) -> SatellitePass:
        detail = provider.detail(pass_id)
        if detail is None:
            raise HTTPException(404, "Pass not found; request the pass list first")
        return detail

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
