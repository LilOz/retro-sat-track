"""Geometric passes above an observer's elevation mask (no optical guarantee)."""

import hashlib
from datetime import timedelta
from threading import RLock
from time import monotonic

import numpy as np
from skyfield.api import wgs84

from app.tracking.propagation import compass, iso, utcnow


class PassPredictor:
    def __init__(self, tracker):
        self.tracker, self.cache, self.details = tracker, {}, {}
        self.lock = RLock()

    def predict(self, record, observer, hours=48, min_elevation=10, now=None):
        now = now or utcnow()
        key = (
            record["NORAD_CAT_ID"],
            record["EPOCH"],
            observer.latitude_deg,
            observer.longitude_deg,
            observer.elevation_m,
            hours,
            min_elevation,
        )
        with self.lock:
            hit = self.cache.get(key)
            if hit and monotonic() - hit[0] < 120:
                return {
                    **hit[1],
                    "passes": [
                        {**p, "in_progress": p["rise_utc"] <= iso(now) < p["set_utc"]}
                        for p in hit[1]["passes"]
                        if p["set_utc"] > iso(now)
                    ],
                }
        sat = self.tracker.satellite(record)
        self.tracker.check(sat.at(self.tracker.ts.from_datetime(now)))
        ground = wgs84.latlon(
            observer.latitude_deg,
            observer.longitude_deg,
            elevation_m=observer.elevation_m,
        )
        difference, end = sat - ground, now + timedelta(hours=hours)
        # Looking behind NOW preserves the actual rise time for an ongoing pass.
        start = now - timedelta(hours=24)
        # Search one additional period to complete passes rising near the window boundary.
        search_end = end + timedelta(seconds=86400 / float(record["MEAN_MOTION"]))
        times, events = sat.find_events(
            ground,
            self.tracker.ts.from_datetime(start),
            self.tracker.ts.from_datetime(search_end),
            altitude_degrees=min_elevation,
        )
        result, rise, peaks = [], None, []
        for t, event in zip(times, events):
            if event == 0:
                rise, peaks = t, []
            elif event == 1 and rise is not None:
                peaks.append(t)
            elif event == 2:
                if (
                    rise is not None
                    and peaks
                    and t.utc_datetime() > now
                    and rise.utc_datetime() < end
                ):
                    peak = max(
                        peaks,
                        key=lambda value: float(
                            difference.at(value).altaz()[0].degrees
                        ),
                    )
                    _, rise_az, _ = difference.at(rise).altaz()
                    peak_alt, _, _ = difference.at(peak).altaz()
                    _, set_az, _ = difference.at(t).altaz()
                    rise_date, set_date = rise.utc_datetime(), t.utc_datetime()
                    pass_id = hashlib.sha256(
                        f"{key}:{iso(rise_date)}".encode()
                    ).hexdigest()[:20]
                    item = {
                        "id": pass_id,
                        "satellite_id": int(record["NORAD_CAT_ID"]),
                        "name": record["OBJECT_NAME"],
                        "rise_utc": iso(rise_date),
                        "culmination_utc": iso(peak.utc_datetime()),
                        "set_utc": iso(set_date),
                        "max_elevation_deg": round(float(peak_alt.degrees), 2),
                        "rise_azimuth_deg": round(float(rise_az.degrees), 2),
                        "set_azimuth_deg": round(float(set_az.degrees), 2),
                        "rise_direction": compass(float(rise_az.degrees)),
                        "set_direction": compass(float(set_az.degrees)),
                        "duration_seconds": round(
                            (set_date - rise_date).total_seconds()
                        ),
                        "in_progress": rise_date <= now < set_date,
                        "min_elevation_deg": min_elevation,
                        "visibility": "geometric; sunlight and weather not evaluated",
                    }
                    sample_times = self.tracker.ts.from_datetimes(
                        [
                            rise_date + (set_date - rise_date) * float(fraction)
                            for fraction in np.linspace(0, 1, 49)
                        ]
                    )
                    alt, az, distance = difference.at(sample_times).altaz()
                    item["sky_path"] = [
                        {
                            "azimuth_deg": round(float(a), 2),
                            "elevation_deg": round(float(e), 2),
                            "range_km": round(float(r), 2),
                        }
                        for a, e, r in zip(az.degrees, alt.degrees, distance.km)
                    ]
                    result.append(item)
                rise, peaks = None, []
        above_mask = (
            float(difference.at(self.tracker.ts.from_datetime(now)).altaz()[0].degrees)
            >= min_elevation
        )
        response = {
            "satellite_id": int(record["NORAD_CAT_ID"]),
            "observer": observer.model_dump(),
            "generated_utc": iso(now),
            "window_end_utc": iso(end),
            "min_elevation_deg": min_elevation,
            "passes": result,
            "above_mask_now": above_mask,
            "note": "Geometric passes. Optical visibility, cloud cover and terrain are not evaluated.",
        }
        with self.lock:
            if len(self.cache) >= 64:
                self.cache.clear()
            self.details = {
                k: v for k, v in self.details.items() if v["set_utc"] > iso(now)
            }
            if len(self.details) > 2000:
                self.details.clear()
            self.details.update({p["id"]: p for p in result})
            self.cache[key] = (monotonic(), response)
        return response

    def detail(self, pass_id):
        with self.lock:
            return self.details.get(pass_id)
