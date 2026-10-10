"""Lazy group downloads, durable cache and conservative upstream requests."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from time import time

import httpx

GROUPS = {"stations": "Space stations", "starlink": "Starlink", "science": "Science", "gps-ops": "GPS"}
REFRESH_SECONDS = 2 * 60 * 60
MAX_ELEMENT_AGE_DAYS = 7
LOGGER = logging.getLogger(__name__)


class CatalogUnavailable(Exception):
    pass


class Catalog:
    def __init__(self, directory: Path, fetcher=None):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.fetcher = fetcher or self._download
        self.groups = {}
        self.retry_after = {}
        self.errors = {}
        self.lock = RLock()

    @staticmethod
    def _download(group):
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.get("https://celestrak.org/NORAD/elements/gp.php",
                                  params={"GROUP": group, "FORMAT": "JSON"},
                                  headers={"User-Agent": "retro-sat-track/0.1 (local desktop tracker)"})
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _validate(records):
        required = {"NORAD_CAT_ID", "OBJECT_NAME", "EPOCH", "MEAN_MOTION", "ECCENTRICITY",
                    "INCLINATION", "RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY",
                    "BSTAR", "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT"}
        if not isinstance(records, list) or not records:
            raise ValueError("CelesTrak returned an empty or invalid catalog")
        for record in records:
            if not isinstance(record, dict) or not required.issubset(record):
                raise ValueError("CelesTrak returned incomplete orbital elements")
            if int(record["NORAD_CAT_ID"]) <= 0 or float(record["MEAN_MOTION"]) <= 0:
                raise ValueError("CelesTrak returned invalid orbital elements")
            datetime.fromisoformat(record["EPOCH"].replace("Z", "+00:00"))
        return records

    def ensure(self, group):
        if group not in GROUPS:
            raise ValueError("Unknown satellite group")
        with self.lock:
            path = self.directory / f"{group}.json"
            if group not in self.groups and path.exists():
                try:
                    cached = json.loads(path.read_text())
                    self._validate(cached["records"])
                    cached["fetched_at"] = float(cached["fetched_at"])
                    self.groups[group] = cached
                except (OSError, ValueError, KeyError, TypeError):
                    LOGGER.warning("Ignoring invalid cache for %s", group)
            attempt_path = self.directory / f"{group}.attempt.json"
            if group not in self.retry_after and attempt_path.exists():
                try:
                    attempt = json.loads(attempt_path.read_text())
                    self.retry_after[group] = float(attempt["retry_after"])
                    if attempt.get("error"):
                        self.errors[group] = attempt["error"]
                except (OSError, ValueError, KeyError, TypeError):
                    pass
            cached, now = self.groups.get(group), time()
            if (cached and now - cached["fetched_at"] < REFRESH_SECONDS) or now < self.retry_after.get(group, 0):
                if cached:
                    return cached
                raise CatalogUnavailable(self.errors.get(group, "Catalog download is cooling down"))
            self.retry_after[group] = now + REFRESH_SECONDS
            attempt = {"retry_after": self.retry_after[group]}
            attempt_path.write_text(json.dumps(attempt))
            try:
                records = self._validate(self.fetcher(group))
                cached = {"fetched_at": now, "records": records}
                temp = path.with_suffix(".tmp")
                temp.write_text(json.dumps(cached))
                temp.replace(path)
                self.groups[group] = cached
                self.errors.pop(group, None)
            except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError) as exc:
                error = f"CelesTrak unavailable for {group}; next attempt after {datetime.fromtimestamp(self.retry_after[group], timezone.utc).isoformat()}"
                LOGGER.warning("%s: %s", error, exc)
                self.errors[group] = error
                attempt["error"] = error
                attempt_path.write_text(json.dumps(attempt))
                if not cached:
                    raise CatalogUnavailable(error) from exc
            return cached

    def record(self, satellite_id, group):
        for record in self.ensure(group)["records"]:
            if int(record["NORAD_CAT_ID"]) == satellite_id:
                return record
        raise KeyError(satellite_id)

    def freshness(self, group):
        cached = self.groups.get(group)
        if not cached:
            return {"loaded": False, "error": self.errors.get(group)}
        age = max(0, time() - cached["fetched_at"])
        return {"loaded": True, "count": len(cached["records"]),
                "fetched_at": datetime.fromtimestamp(cached["fetched_at"], timezone.utc).isoformat(),
                "download_age_seconds": round(age), "stale": age >= REFRESH_SECONDS,
                "error": self.errors.get(group)}
