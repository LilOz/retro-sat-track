from datetime import datetime, timezone

import pytest

from app.tracking.visibility import PassPredictor


def test_pass_matches_published_rise_peak_set(tracker, record, observer):
    predictor = PassPredictor(tracker)
    start = datetime(2014, 1, 23, tzinfo=timezone.utc)
    result = predictor.predict(record, observer, hours=24, min_elevation=30, now=start)
    first = result["passes"][0]
    for key, expected in [("rise_utc", "2014-01-23T06:25:37+00:00"),
                          ("culmination_utc", "2014-01-23T06:26:58+00:00"),
                          ("set_utc", "2014-01-23T06:28:19+00:00")]:
        actual = datetime.fromisoformat(first[key].replace("Z", "+00:00"))
        assert abs((actual - datetime.fromisoformat(expected)).total_seconds()) < 2
    assert first["max_elevation_deg"] >= 30
    assert len(first["sky_path"]) == 49
    assert first["sky_path"][0]["elevation_deg"] == pytest.approx(30, abs=.1)
    assert first["sky_path"][-1]["elevation_deg"] == pytest.approx(30, abs=.1)
    assert predictor.detail(first["id"]) == first
    assert "geometric" in first["visibility"]


def test_ongoing_pass_retains_actual_rise(tracker, record, observer):
    start = datetime(2014, 1, 23, 6, 26, 30, tzinfo=timezone.utc)
    first = PassPredictor(tracker).predict(record, observer, hours=3, min_elevation=30, now=start)["passes"][0]
    assert first["in_progress"]
    assert datetime.fromisoformat(first["rise_utc"].replace("Z", "+00:00")) < start


def test_high_mask_can_return_no_passes(tracker, record, observer):
    result = PassPredictor(tracker).predict(record, observer, hours=1, min_elevation=80,
                                           now=datetime(2014, 1, 23, tzinfo=timezone.utc))
    assert result["passes"] == []


def test_pass_rising_near_window_end_is_completed(tracker, record, observer):
    # A one-hour window ends at 06:26:00, between rise and culmination.
    start = datetime(2014, 1, 23, 5, 26, tzinfo=timezone.utc)
    result = PassPredictor(tracker).predict(record, observer, hours=1, min_elevation=30, now=start)
    assert len(result["passes"]) == 1
    assert result["passes"][0]["rise_utc"] < result["window_end_utc"]
    assert result["passes"][0]["set_utc"] > result["window_end_utc"]
