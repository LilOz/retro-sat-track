from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sgp4.api import Satrec
from sgp4.exporter import export_omm

from app.main import create_app
from app.models import Observer
from app.schemas import OrbitalElements
from app.tracking.catalog import Catalog
from app.tracking.propagation import Tracker


@pytest.fixture
def record() -> OrbitalElements:
    # Published Skyfield example; kept only in tests, never served as live data.
    satellite = Satrec.twoline2rv(
        "1 25544U 98067A   14020.93268519  .00009878  00000-0  18200-3 0  5082",
        "2 25544  51.6498 109.4756 0003572  55.9686 274.8005 15.49815350868473",
    )
    return cast(OrbitalElements, export_omm(satellite, "ISS (ZARYA)"))


@pytest.fixture
def tracker() -> Tracker:
    return Tracker()


@pytest.fixture
def instant() -> datetime:
    return datetime(2014, 1, 23, 11, 18, 7, tzinfo=timezone.utc)


@pytest.fixture
def observer() -> Observer:
    return Observer(name="Bluffton", latitude_deg=40.8939, longitude_deg=-83.8917)


@pytest.fixture
def client(tmp_path: Path, record: OrbitalElements) -> Iterator[TestClient]:
    def catalog_records(group: str) -> list[OrbitalElements]:
        return [record]

    catalog = Catalog(tmp_path / "catalog", fetcher=catalog_records)
    with TestClient(create_app(tmp_path, catalog)) as value:
        yield value
