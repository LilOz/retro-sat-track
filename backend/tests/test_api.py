from fastapi.testclient import TestClient

from app.main import create_app
from app.tracking.catalog import Catalog


def test_status_and_static_terminal(client):
    assert client.get("/api/v1/status").json()["observer"] is None
    assert "ORBIT" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/docs").status_code == 200


def test_catalog_search_and_unknown_satellite(client):
    listed = client.get("/api/v1/satellites?q=25544").json()
    assert listed["total"] == 1
    assert listed["satellites"][0]["id"] == 25544
    assert client.get("/api/v1/satellites?q=missing").json()["total"] == 0
    assert client.get("/api/v1/satellites/999/state").status_code == 404
    assert client.get("/api/v1/satellites?group=invalid").status_code == 422
    assert client.get("/api/v1/satellites?limit=100000").status_code == 422


def test_observer_validation_and_persistence(client, tmp_path, record):
    assert client.get("/api/v1/passes").status_code == 409
    assert client.post("/api/v1/observer", json={"latitude_deg": 91, "longitude_deg": 0}).status_code == 422
    location = {"name": "Desk", "latitude_deg": 51.5, "longitude_deg": -.12, "elevation_m": 18}
    assert client.post("/api/v1/observer", json=location).json() == location
    assert client.get("/api/v1/status").json()["observer"] == location
    with TestClient(create_app(tmp_path, Catalog(tmp_path / "catalog", lambda _: [record]))) as restarted:
        assert restarted.get("/api/v1/status").json()["observer"] == location
    assert client.get("/api/v1/passes?lat=51.5").status_code == 422
    assert client.get("/api/v1/passes?lat=nan&lon=0").status_code == 422
    assert client.get("/api/v1/passes/not-a-pass").status_code == 404


def test_catalog_supports_six_digit_ids(client, record):
    extended = {**record, "NORAD_CAT_ID": 100001, "OBJECT_NAME": "NEW SPACECRAFT"}
    client.get("/api/v1/satellites")
    client.app.state.catalog.groups["stations"]["records"].append(extended)
    assert client.get("/api/v1/satellites?q=100001").json()["satellites"][0]["id"] == 100001


def test_states_tracks_and_pass_details(client, monkeypatch, instant, observer):
    monkeypatch.setattr("app.main.utcnow", lambda: instant)
    monkeypatch.setattr("app.tracking.propagation.utcnow", lambda: instant)
    monkeypatch.setattr("app.tracking.visibility.utcnow", lambda: instant)
    client.post("/api/v1/observer", json=observer.model_dump())
    state = client.get("/api/v1/satellites/25544/state")
    assert state.status_code == 200
    assert 380 < state.json()["altitude_km"] < 450
    assert client.get("/api/v1/scene").json()["states"][0]["id"] == 25544
    assert len(client.get("/api/v1/satellites/25544/track?samples=60").json()["ground_track"]) == 60
    assert client.get("/api/v1/satellites/25544/track?samples=1").status_code == 422
    passes = client.get("/api/v1/passes").json()["passes"]
    assert passes
    assert client.get(f"/api/v1/passes/{passes[0]['id']}").json()["id"] == passes[0]["id"]
