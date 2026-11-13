import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tiles import approx_tile_size_km, tile_bounds, tile_image_url

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_bodies_lists_moon_and_mars() -> None:
    response = client.get("/api/bodies")
    assert response.status_code == 200

    bodies = response.json()["bodies"]
    assert [body["id"] for body in bodies] == ["moon", "mars"]

    moon, mars = bodies
    assert moon["max_zoom"] == 8
    assert mars["max_zoom"] == 7
    assert moon["attribution_url"].startswith("https://trek.nasa.gov/")
    assert "{z}" in moon["tile_url_template"]
    assert "{y}" in moon["tile_url_template"]
    assert "{x}" in moon["tile_url_template"]


def test_moon_level_zero_tile() -> None:
    response = client.get("/api/tiles/moon/0/0/0")
    assert response.status_code == 200

    data = response.json()
    assert data["body"] == "moon"
    assert data["tile"] == {"z": 0, "x": 0, "y": 0}
    assert data["bounds"] == {
        "west": -180.0,
        "south": -90.0,
        "east": 0.0,
        "north": 90.0,
    }
    assert data["center"] == {"lat": 0.0, "lon": -90.0}
    assert data["image_url"].endswith("/default028mm/0/0/0.jpg")
    assert data["analysis"]["simulated"] is True
    assert data["analysis"]["fields"]
    assert 0 <= data["analysis"]["confidence_pct"] <= 100


def test_mars_bottom_right_max_zoom_tile() -> None:
    response = client.get("/api/tiles/mars/7/255/127")
    assert response.status_code == 200

    data = response.json()
    assert data["bounds"]["east"] == 180.0
    assert data["bounds"]["south"] == -90.0
    assert data["image_url"].endswith("/default028mm/7/127/255.jpg")


def test_unknown_body_returns_404() -> None:
    response = client.get("/api/tiles/earth/4/1/1")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/api/tiles/moon/9/0/0",
        "/api/tiles/moon/4/32/0",
        "/api/tiles/moon/4/0/16",
        "/api/tiles/mars/8/0/0",
        "/api/tiles/moon/-1/0/0",
    ],
)
def test_invalid_tile_index_returns_422(path: str) -> None:
    response = client.get(path)
    assert response.status_code == 422


def test_analysis_is_deterministic() -> None:
    first = client.get("/api/tiles/mars/5/12/9").json()["analysis"]
    second = client.get("/api/tiles/mars/5/12/9").json()["analysis"]
    assert first == second


def test_analysis_changes_between_tiles() -> None:
    first = client.get("/api/tiles/moon/4/3/3").json()["analysis"]
    second = client.get("/api/tiles/moon/4/3/4").json()["analysis"]
    assert first != second


def test_tile_bounds_direct() -> None:
    bounds = tile_bounds(1, 1, 0)
    assert bounds.model_dump() == {
        "west": -90.0,
        "south": 0.0,
        "east": 0.0,
        "north": 90.0,
    }


def test_tile_size_is_positive() -> None:
    bounds = tile_bounds(4, 2, 3)
    size = approx_tile_size_km(bounds, radius_km=1737.4)
    assert size.width > 0
    assert size.height > 0


def test_image_url_template_replacement() -> None:
    url = tile_image_url("https://example.test/{z}/{y}/{x}.jpg", 4, 9, 3)
    assert url == "https://example.test/4/3/9.jpg"
