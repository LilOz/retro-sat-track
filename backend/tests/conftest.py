from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sgp4.api import Satrec
from sgp4.exporter import export_omm

from app.main import create_app
from app.models import Observer
from app.tracking.catalog import Catalog
from app.tracking.propagation import Tracker


@pytest.fixture
def record():
    # Published Skyfield example; kept only in tests, never served as live data.
    satellite = Satrec.twoline2rv(
        "1 25544U 98067A   14020.93268519  .00009878  00000-0  18200-3 0  5082",
        "2 25544  51.6498 109.4756 0003572  55.9686 274.8005 15.49815350868473",
    )
    return export_omm(satellite, "ISS (ZARYA)")


@pytest.fixture
def tracker():
    return Tracker()


@pytest.fixture
def instant():
    return datetime(2014, 1, 23, 11, 18, 7, tzinfo=timezone.utc)


@pytest.fixture
def observer():
    return Observer(name="Bluffton", latitude_deg=40.8939, longitude_deg=-83.8917)


@pytest.fixture
def client(tmp_path, record):
    catalog = Catalog(tmp_path / "catalog", fetcher=lambda _: [record])
    with TestClient(create_app(tmp_path, catalog)) as value:
        yield value
