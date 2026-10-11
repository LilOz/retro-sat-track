import math
from datetime import datetime
from typing import cast

import numpy as np
import pytest
from skyfield.positionlib import Geocentric

from app.models import Observer
from app.schemas import OrbitalElements
from app.tracking.propagation import PropagationError, Tracker


def test_matches_published_skyfield_position(
    tracker: Tracker, record: OrbitalElements, instant: datetime, observer: Observer
) -> None:
    position = tracker.satellite(record).at(tracker.ts.from_datetime(instant))
    # https://rhodesmill.org/skyfield/earth-satellites.html
    np.testing.assert_allclose(
        position.position.km, [-3918.8765, -1887.6484, 5209.0880], atol=0.1
    )
    state = tracker.state(record, observer, instant)
    assert state["latitude_deg"] == pytest.approx(50.24372, abs=0.02)
    assert state["longitude_deg"] == pytest.approx(-86.3953, abs=0.02)
    assert 380 < state["altitude_km"] < 450
    assert 7 < state["velocity_km_s"] < 8
    assert 0 <= state["mean_orbital_phase_deg"] < 360
    assert not state["elements_stale"]


def test_track_has_distinct_orbit_and_ground_path(
    tracker: Tracker, record: OrbitalElements, instant: datetime
) -> None:
    track = tracker.track(record, 120, instant)
    assert len(track["orbit_ecef_km"]) == len(track["ground_track"]) == 120
    assert 5400 < track["period_seconds"] < 6000
    for point, xyz in zip(track["ground_track"], track["orbit_ecef_km"]):
        assert -90 <= point["latitude_deg"] <= 90
        assert -180 <= point["longitude_deg"] <= 180
        assert 6700 < math.hypot(*xyz) < 6900
    # Future Earth rotation changes longitude on the ground track.
    xyz = track["orbit_ecef_km"][-1]
    frozen_longitude = math.degrees(math.atan2(xyz[1], xyz[0]))
    assert abs(frozen_longitude - track["ground_track"][-1]["longitude_deg"]) > 10


def test_invalid_propagation_is_rejected(tracker: Tracker) -> None:
    class BadPosition:
        message = "satellite has decayed"

        class position:
            km = np.array([1.0, 2.0, 3.0])

    with pytest.raises(PropagationError):
        tracker.check(cast(Geocentric, BadPosition()))
