"""N2YO positions and radio passes, with shared batches and bounded request use."""

import hashlib
import math
import os
from collections import OrderedDict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock
from time import monotonic
from typing import cast
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field, FiniteFloat, ValidationError, model_validator

from app.models import Observer
from app.schemas import (
    GroundTrackPoint,
    ObserverData,
    OrbitalElements,
    ProviderForecast,
    ProviderState,
    ProviderTrack,
    SatellitePass,
)
from app.tracking.catalog import MAX_ELEMENT_AGE_DAYS
from app.tracking.common import compass, globe_xyz, iso, utcnow

BASE_URL = "https://api.n2yo.com/rest/v1/satellite"
BATCH_SECONDS = 300
FORECAST_TTL = 30 * 60
REQUEST_LIMITS = {"positions": 900, "radiopasses": 90}

type PositionKey = tuple[int, float, float, float]
type ForecastKey = tuple[int, float, float, float, int, int]


class ProviderUnavailable(Exception):
    """A configuration, quota or upstream error safe to expose to clients."""


class ProviderInfo(BaseModel):
    satid: int = Field(ge=1)
    satname: str


class Position(BaseModel):
    satlatitude: FiniteFloat = Field(ge=-90, le=90)
    satlongitude: FiniteFloat = Field(ge=-180, le=180)
    sataltitude: FiniteFloat = Field(ge=-500, le=1000000)
    azimuth: FiniteFloat = Field(ge=0, le=360)
    elevation: FiniteFloat = Field(ge=-90, le=90)
    timestamp: int = Field(ge=0, le=4102444800)


class PositionBatch(BaseModel):
    info: ProviderInfo
    positions: list[Position] = Field(min_length=1, max_length=BATCH_SECONDS)

    @model_validator(mode="after")
    def ordered_positions(self) -> PositionBatch:
        if any(
            b.timestamp != a.timestamp + 1
            for a, b in zip(self.positions, self.positions[1:])
        ):
            raise ValueError("Position samples must be consecutive seconds")
        return self


class RadioPass(BaseModel):
    startAz: FiniteFloat = Field(ge=0, le=360)
    startUTC: int = Field(ge=0, le=4102444800)
    maxAz: FiniteFloat = Field(ge=0, le=360)
    maxEl: FiniteFloat = Field(ge=0, le=90)
    maxUTC: int = Field(ge=0, le=4102444800)
    endAz: FiniteFloat = Field(ge=0, le=360)
    endUTC: int = Field(ge=0, le=4102444800)

    @model_validator(mode="after")
    def ordered_events(self) -> RadioPass:
        if (
            not self.startUTC <= self.maxUTC <= self.endUTC
            or self.startUTC == self.endUTC
        ):
            raise ValueError("Pass events must be ordered")
        return self


class RadioForecast(BaseModel):
    info: ProviderInfo
    passes: list[RadioPass] = Field(max_length=2000)


class N2YO:
    def __init__(
        self, api_key: str | None = None, transport: httpx.BaseTransport | None = None
    ) -> None:
        self.api_key = (
            api_key if api_key is not None else os.getenv("N2YO_API_KEY", "")
        ).strip()
        self.transport = transport
        self.positions: OrderedDict[PositionKey, PositionBatch] = OrderedDict()
        self.forecasts: OrderedDict[
            ForecastKey, tuple[float, datetime, RadioForecast]
        ] = OrderedDict()
        self.details: dict[str, SatellitePass] = {}
        self.requests: dict[str, deque[float]] = {
            name: deque() for name in REQUEST_LIMITS
        }
        self.cooldowns: dict[str, tuple[float, str]] = {}
        self.lock = Lock()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _request[Response: BaseModel](
        self, path: str, model: type[Response]
    ) -> Response:
        """Called under the provider lock to coalesce concurrent upstream requests."""
        if not self.configured:
            raise ProviderUnavailable(
                "Set N2YO_API_KEY on the backend and restart to enable tracking."
            )
        endpoint = path.split("/", 1)[0]
        clock = monotonic()
        retry = self.cooldowns.get(endpoint)
        if retry and clock < retry[0]:
            raise ProviderUnavailable(retry[1])
        attempts = self.requests[endpoint]
        while attempts and clock - attempts[0] >= 3600:
            attempts.popleft()
        if len(attempts) >= REQUEST_LIMITS[endpoint]:
            raise ProviderUnavailable(
                "N2YO hourly request budget reached. Tracking will resume when the budget resets."
            )
        attempts.append(clock)
        # N2YO documents /.../&apiKey=KEY rather than a conventional query string.
        url = f"{BASE_URL}/{path}/&apiKey={quote(self.api_key, safe='')}"
        cooldown = 300
        message = "N2YO is unavailable. Retrying in five minutes; expired positions are not reused."
        try:
            with httpx.Client(timeout=20, transport=self.transport) as client:
                response = client.get(url)
            if response.status_code in (401, 403):
                message = "N2YO rejected the API key. Check N2YO_API_KEY and restart the backend."
                raise ProviderUnavailable(message)
            if response.status_code == 429:
                cooldown = 3600
                message = (
                    "N2YO quota exceeded. Upstream requests are paused for one hour."
                )
                raise ProviderUnavailable(message)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict) and "error" in payload:
                # Never expose upstream messages or HTTP exceptions: they can contain the key.
                upstream = str(payload["error"]).lower()
                if any(word in upstream for word in ("limit", "quota", "transaction")):
                    cooldown = 3600
                    message = "N2YO quota exceeded. Upstream requests are paused for one hour."
                elif any(word in upstream for word in ("key", "license", "auth")):
                    message = "N2YO rejected the API key. Check N2YO_API_KEY and restart the backend."
                raise ProviderUnavailable(message)
            result = model.model_validate(payload)
        except httpx.HTTPError, ValidationError, ValueError, ProviderUnavailable:
            self.cooldowns[endpoint] = (monotonic() + cooldown, message)
            raise ProviderUnavailable(message) from None
        self.cooldowns.pop(endpoint, None)
        return result

    @staticmethod
    def _location(satellite_id: int, observer: Observer) -> PositionKey:
        return (
            satellite_id,
            observer.latitude_deg,
            observer.longitude_deg,
            observer.elevation_m,
        )

    def _batch(
        self, satellite_id: int, observer: Observer, now: datetime
    ) -> PositionBatch:
        key = self._location(satellite_id, observer)
        with self.lock:
            timestamp = max(now.timestamp(), utcnow().timestamp())
            batch = self.positions.get(key)
            if (
                batch
                and batch.positions[0].timestamp - 5
                <= timestamp
                <= batch.positions[-1].timestamp
            ):
                self.positions.move_to_end(key)
                return batch
            path = f"positions/{satellite_id}/{observer.latitude_deg}/{observer.longitude_deg}/{observer.elevation_m}/{BATCH_SECONDS}"
            batch = self._request(path, PositionBatch)
            timestamp = max(timestamp, utcnow().timestamp())
            if (
                batch.info.satid != satellite_id
                or not batch.positions[0].timestamp - 5
                <= timestamp
                <= batch.positions[-1].timestamp
            ):
                self.cooldowns["positions"] = (
                    monotonic() + 300,
                    "N2YO returned mismatched or expired positions. Retrying in five minutes.",
                )
                raise ProviderUnavailable(
                    "N2YO returned mismatched or expired positions. Retrying in five minutes."
                )
            self.positions[key] = batch
            self.positions.move_to_end(key)
            while len(self.positions) > 32:
                self.positions.popitem(last=False)
            return batch

    def state(
        self, record: OrbitalElements, observer: Observer, now: datetime | None = None
    ) -> ProviderState:
        now = now or utcnow()
        batch = self._batch(int(record["NORAD_CAT_ID"]), observer, now)
        sample_time = max(now.timestamp(), utcnow().timestamp())
        point = min(
            batch.positions, key=lambda value: abs(value.timestamp - sample_time)
        )
        epoch = datetime.fromisoformat(record["EPOCH"].replace("Z", "+00:00"))
        if epoch.tzinfo is None:
            epoch = epoch.replace(tzinfo=UTC)
        age = (now - epoch).total_seconds()
        return {
            "id": batch.info.satid,
            "name": batch.info.satname,
            "utc": iso(datetime.fromtimestamp(point.timestamp, UTC)),
            "latitude_deg": point.satlatitude,
            "longitude_deg": point.satlongitude,
            "altitude_km": point.sataltitude,
            "velocity_km_s": None,
            "inclination_deg": float(record["INCLINATION"]),
            "period_minutes": round(1440 / float(record["MEAN_MOTION"]), 3),
            "eccentricity": float(record["ECCENTRICITY"]),
            "mean_orbital_phase_deg": None,
            "element_epoch": iso(epoch),
            "element_age_hours": round(age / 3600, 2),
            "elements_stale": abs(age) > MAX_ELEMENT_AGE_DAYS * 86400,
            "azimuth_deg": point.azimuth,
            "elevation_deg": point.elevation,
            "range_km": None,
            "above_horizon": point.elevation > 0,
            "position_globe_km": globe_xyz(
                point.satlatitude, point.satlongitude, point.sataltitude
            ),
            "source": "N2YO",
        }

    def track(
        self,
        record: OrbitalElements,
        observer: Observer,
        samples: int = 180,
        now: datetime | None = None,
    ) -> ProviderTrack:
        now = now or utcnow()
        batch = self._batch(int(record["NORAD_CAT_ID"]), observer, now)
        now = max(now, utcnow())
        points = [p for p in batch.positions if p.timestamp >= int(now.timestamp())]
        count = min(samples, len(points))
        indices = sorted(
            {round(i * (len(points) - 1) / max(1, count - 1)) for i in range(count)}
        )
        ground: list[GroundTrackPoint] = [
            {
                "utc": iso(datetime.fromtimestamp(points[i].timestamp, UTC)),
                "latitude_deg": points[i].satlatitude,
                "longitude_deg": points[i].satlongitude,
                "altitude_km": points[i].sataltitude,
            }
            for i in indices
        ]
        return {
            "id": batch.info.satid,
            "utc": iso(now),
            "window_seconds": (
                points[-1].timestamp - points[0].timestamp if points else 0
            ),
            "path_globe_km": [
                globe_xyz(p["latitude_deg"], p["longitude_deg"], p["altitude_km"])
                for p in ground
            ],
            "ground_track": ground,
            "source": "N2YO",
        }

    def predict(
        self,
        record: OrbitalElements,
        observer: Observer,
        hours: int = 48,
        min_elevation: float = 10,
        now: datetime | None = None,
    ) -> ProviderForecast:
        now = now or utcnow()
        satellite_id = int(record["NORAD_CAT_ID"])
        # An extra day lets the moving UI window stay covered throughout the cache TTL.
        days, minimum = math.ceil((hours + FORECAST_TTL / 3600) / 24), math.ceil(
            min_elevation
        )
        key: ForecastKey = (*self._location(satellite_id, observer), days, minimum)
        with self.lock:
            cached = self.forecasts.get(key)
            if cached and monotonic() - cached[0] < FORECAST_TTL:
                _, fetched, forecast = cached
                self.forecasts.move_to_end(key)
            else:
                path = f"radiopasses/{satellite_id}/{observer.latitude_deg}/{observer.longitude_deg}/{observer.elevation_m}/{days}/{minimum}"
                forecast = self._request(path, RadioForecast)
                if forecast.info.satid != satellite_id:
                    self.cooldowns["radiopasses"] = (
                        monotonic() + 300,
                        "N2YO returned a forecast for another satellite. Retrying in five minutes.",
                    )
                    raise ProviderUnavailable(
                        "N2YO returned a forecast for another satellite. Retrying in five minutes."
                    )
                fetched = now
                self.forecasts[key] = (monotonic(), fetched, forecast)
                self.forecasts.move_to_end(key)
                while len(self.forecasts) > 64:
                    self.forecasts.popitem(last=False)
        end = now + timedelta(hours=hours)
        result: list[SatellitePass] = []
        for item in forecast.passes:
            if (
                item.endUTC <= now.timestamp()
                or item.startUTC >= end.timestamp()
                or item.maxEl < min_elevation
            ):
                continue
            rise, peak, setting = [
                datetime.fromtimestamp(t, UTC)
                for t in (item.startUTC, item.maxUTC, item.endUTC)
            ]
            pass_id = hashlib.sha256(f"{key}:{item.startUTC}".encode()).hexdigest()[:20]
            result.append(
                {
                    "id": pass_id,
                    "satellite_id": satellite_id,
                    "name": forecast.info.satname,
                    "rise_utc": iso(rise),
                    "culmination_utc": iso(peak),
                    "set_utc": iso(setting),
                    "max_elevation_deg": item.maxEl,
                    "rise_azimuth_deg": item.startAz,
                    "set_azimuth_deg": item.endAz,
                    "rise_direction": compass(item.startAz),
                    "set_direction": compass(item.endAz),
                    "duration_seconds": item.endUTC - item.startUTC,
                    "in_progress": rise <= now < setting,
                    "min_elevation_deg": 0,
                    "visibility": "N2YO radio pass; optical visibility not evaluated",
                    "sky_path": [
                        {
                            "azimuth_deg": item.startAz,
                            "elevation_deg": 0,
                            "range_km": None,
                        },
                        {
                            "azimuth_deg": item.maxAz,
                            "elevation_deg": item.maxEl,
                            "range_km": None,
                        },
                        {
                            "azimuth_deg": item.endAz,
                            "elevation_deg": 0,
                            "range_km": None,
                        },
                    ],
                }
            )
        result.sort(key=lambda item: item["rise_utc"])
        with self.lock:
            self.details = {
                key: value
                for key, value in self.details.items()
                if value["set_utc"] > iso(now)
            }
            if len(self.details) + len(result) > 2000:
                self.details.clear()
            self.details.update({p["id"]: p for p in result})
        return {
            "satellite_id": satellite_id,
            "observer": cast(ObserverData, observer.model_dump()),
            "generated_utc": iso(fetched),
            "window_end_utc": iso(end),
            "min_peak_elevation_deg": min_elevation,
            "passes": result,
            "note": "N2YO horizon-to-horizon radio passes, filtered by maximum elevation. Sky diagram joins rise/peak/set events; it is not a sampled trajectory. Optical visibility and weather are not evaluated.",
        }

    def detail(self, pass_id: str) -> SatellitePass | None:
        with self.lock:
            return self.details.get(pass_id)
