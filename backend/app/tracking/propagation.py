"""SGP4 states with WGS84 geography and explicitly named reference frames."""

import math
from datetime import UTC, datetime, timedelta
from threading import RLock

import numpy as np
from skyfield.api import EarthSatellite, load, wgs84
from skyfield.framelib import itrs

from app.models import Observer
from app.tracking.catalog import MAX_ELEMENT_AGE_DAYS


class PropagationError(Exception):
    pass


def utcnow():
    return datetime.now(UTC)


def iso(value):
    return value.isoformat().replace("+00:00", "Z")


def compass(degrees):
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int((degrees + 22.5) // 45) % 8]


class Tracker:
    def __init__(self):
        self.ts = load.timescale(builtin=True)
        self.satellites = {}
        self.lock = RLock()

    def satellite(self, record):
        key = (int(record["NORAD_CAT_ID"]), record["EPOCH"])
        with self.lock:
            if key not in self.satellites:
                if len(self.satellites) > 512:
                    self.satellites.clear()
                self.satellites[key] = EarthSatellite.from_omm(self.ts, record)
            return self.satellites[key]

    @staticmethod
    def check(position):
        messages = np.asarray(position.message, dtype=object).reshape(-1)
        if any(message for message in messages) or not np.all(
            np.isfinite(position.position.km)
        ):
            raise PropagationError(
                "Orbit cannot be propagated with these elements; select another spacecraft"
            )

    def state(self, record, observer: Observer, now=None):
        now = now or utcnow()
        sat, t = self.satellite(record), self.ts.from_datetime(now)
        position = sat.at(t)
        self.check(position)
        subpoint = wgs84.geographic_position_of(position)
        ground = wgs84.latlon(
            observer.latitude_deg,
            observer.longitude_deg,
            elevation_m=observer.elevation_m,
        )
        altitude, azimuth, distance = (sat - ground).at(t).altaz()
        epoch_age = (now - sat.epoch.utc_datetime()).total_seconds()
        phase = math.degrees(sat.model.mo + sat.model.no_kozai * epoch_age / 60) % 360
        return {
            "id": int(record["NORAD_CAT_ID"]),
            "name": record["OBJECT_NAME"],
            "utc": iso(now),
            "latitude_deg": round(float(subpoint.latitude.degrees), 5),
            "longitude_deg": round(float(subpoint.longitude.degrees), 5),
            "altitude_km": round(float(subpoint.elevation.km), 3),
            "velocity_km_s": round(
                float(np.linalg.norm(position.velocity.km_per_s)), 5
            ),
            "inclination_deg": float(record["INCLINATION"]),
            "period_minutes": round(1440 / float(record["MEAN_MOTION"]), 3),
            "eccentricity": float(record["ECCENTRICITY"]),
            "mean_orbital_phase_deg": round(phase, 3),
            "element_epoch": iso(sat.epoch.utc_datetime()),
            "element_age_hours": round(epoch_age / 3600, 2),
            "elements_stale": abs(epoch_age) > MAX_ELEMENT_AGE_DAYS * 86400,
            "azimuth_deg": round(float(azimuth.degrees), 2),
            "elevation_deg": round(float(altitude.degrees), 2),
            "range_km": round(float(distance.km), 2),
            "above_horizon": bool(altitude.degrees > 0),
            "position_ecef_km": [
                round(float(v), 3) for v in position.frame_xyz(itrs).km
            ],
        }

    def track(self, record, samples=180, now=None):
        now = now or utcnow()
        sat, period = self.satellite(record), 86400 / float(record["MEAN_MOTION"])
        dates = [
            now + timedelta(seconds=float(offset))
            for offset in np.linspace(-period * 0.2, period * 0.8, samples)
        ]
        position = sat.at(self.ts.from_datetimes(dates))
        self.check(position)
        subpoints = wgs84.geographic_position_of(position)
        frozen_xyz = itrs.rotation_at(self.ts.from_datetime(now)) @ position.position.km
        return {
            "id": int(record["NORAD_CAT_ID"]),
            "utc": iso(now),
            "period_seconds": period,
            "orbit_ecef_km": np.round(frozen_xyz.T, 3).tolist(),
            "ground_track": [
                {
                    "utc": iso(date),
                    "latitude_deg": round(float(lat), 4),
                    "longitude_deg": round(float(lon), 4),
                    "altitude_km": round(float(alt), 3),
                }
                for date, lat, lon, alt in zip(
                    dates,
                    subpoints.latitude.degrees,
                    subpoints.longitude.degrees,
                    subpoints.elevation.km,
                )
            ],
        }
