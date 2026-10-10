import json
from pathlib import Path
from time import time
from typing import Never

import httpx
import pytest

from app.schemas import OrbitalElements
from app.tracking.catalog import REFRESH_SECONDS, Catalog, CatalogUnavailable


def test_group_download_is_cached_on_disk_and_across_restart(
    tmp_path: Path, record: OrbitalElements
) -> None:
    calls: list[str] = []

    def fetch(group: str) -> list[OrbitalElements]:
        calls.append(group)
        return [record]

    catalog = Catalog(tmp_path, fetch)
    assert catalog.record(25544, "stations") == record
    catalog.ensure("stations")
    Catalog(tmp_path, fetch).ensure("stations")
    assert calls == ["stations"]


def test_failed_upstream_preserves_old_catalog_and_cools_down(
    tmp_path: Path, record: OrbitalElements
) -> None:
    cached = {"fetched_at": time() - REFRESH_SECONDS - 1, "records": [record]}
    (tmp_path / "stations.json").write_text(json.dumps(cached))
    calls: list[str] = []

    def offline(group: str) -> Never:
        calls.append(group)
        raise httpx.ConnectError("offline")

    catalog = Catalog(tmp_path, offline)
    assert catalog.ensure("stations") == cached
    assert catalog.freshness("stations").get("stale")
    assert catalog.freshness("stations")["error"]
    Catalog(tmp_path, offline).ensure("stations")
    assert calls == ["stations"]


def test_first_download_failure_does_not_fake_live_data(tmp_path: Path) -> None:
    calls: list[str] = []

    def blocked(group: str) -> Never:
        calls.append(group)
        raise httpx.HTTPStatusError(
            "403",
            request=httpx.Request("GET", "https://celestrak.org"),
            response=httpx.Response(403),
        )

    catalog = Catalog(tmp_path, blocked)
    for instance in [catalog, catalog, Catalog(tmp_path, blocked)]:
        with pytest.raises(CatalogUnavailable):
            instance.ensure("stations")
    assert calls == ["stations"]


def test_invalid_payload_is_rejected(tmp_path: Path) -> None:
    def invalid_payload(group: str) -> dict[str, str]:
        return {"error": "bad response"}

    with pytest.raises(CatalogUnavailable):
        Catalog(tmp_path, invalid_payload).ensure("stations")
