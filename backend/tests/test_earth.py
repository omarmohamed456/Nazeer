from fastapi.testclient import TestClient

from app.earth import EARTH_MAX_ZOOM, EARTH_MIN_ZOOM, earth_grid_size, random_earth_tile
from app.main import app

client = TestClient(app)


def test_grid_dimensions() -> None:
    assert earth_grid_size(4) == (20, 10)
    assert earth_grid_size(5) == (40, 20)
    assert earth_grid_size(6) == (80, 40)


def test_seeded_result_is_reproducible() -> None:
    assert random_earth_tile(1234) == random_earth_tile(1234)


def test_random_tiles_stay_inside_the_grid() -> None:
    for seed in range(50):
        analog = random_earth_tile(seed)
        cols, rows = earth_grid_size(analog.tile.z)

        assert EARTH_MIN_ZOOM <= analog.tile.z <= EARTH_MAX_ZOOM
        assert 0 <= analog.tile.x < cols
        assert 0 <= analog.tile.y < rows
        assert -180 <= analog.center.lon <= 180
        assert -90 <= analog.center.lat <= 90
        assert abs(analog.center.lat) < 80
        assert analog.image_url.startswith("https://gibs.earthdata.nasa.gov/")
        assert analog.image_url.endswith(".jpeg")
        assert 0 <= analog.match_pct <= 100
        assert analog.simulated is True


def test_earth_random_endpoint() -> None:
    response = client.get("/api/earth/random?seed=42")
    assert response.status_code == 200

    data = response.json()
    assert data["seed"] == 42
    assert data["image_url"].startswith("https://gibs.earthdata.nasa.gov/")
    assert data["note"].startswith("Prototype only")
    assert len(data["tile"]) == 3


def test_earth_random_endpoint_rejects_negative_seed() -> None:
    response = client.get("/api/earth/random?seed=-1")
    assert response.status_code == 422
