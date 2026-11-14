import pytest
from fastapi.testclient import TestClient

from app.config import BODIES
from app.geology import (
    DATASET_RESOLUTION_DEG,
    GRID_COLS,
    GRID_ROWS,
    build_point_match,
    build_tile_match,
    cell_for_point,
    cells_for_bounds,
    get_cells,
)
from app.main import app
from app.tiles import tile_bounds

client = TestClient(app)


def test_dataset_shape_and_ids() -> None:
    cells = get_cells()
    assert len(cells) == GRID_ROWS * GRID_COLS == 648
    assert len({cell.tile_id for cell in cells.values()}) == 648
    assert {cell.row for cell in cells.values()} == set(range(18))
    assert {cell.col for cell in cells.values()} == set(range(36))
    assert DATASET_RESOLUTION_DEG == 10.0


def test_cell_for_point_uses_south_to_north_rows() -> None:
    cell = cell_for_point(0, 0)
    assert cell.tile_id == "r09c18"
    assert cell.bounds.model_dump() == {
        "west": 0.0,
        "south": 0.0,
        "east": 10.0,
        "north": 10.0,
    }

    north = cell_for_point(90, 180)
    assert north.tile_id == "r17c35"
    assert north.bounds.model_dump() == {
        "west": 170.0,
        "south": 80.0,
        "east": 180.0,
        "north": 90.0,
    }

    south = cell_for_point(-90, -180)
    assert south.tile_id == "r00c00"
    assert south.bounds.model_dump() == {
        "west": -180.0,
        "south": -90.0,
        "east": -170.0,
        "north": -80.0,
    }


@pytest.mark.parametrize("lat,lon", [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_cell_for_point_rejects_out_of_range(lat: float, lon: float) -> None:
    with pytest.raises(ValueError):
        cell_for_point(lat, lon)


def test_cells_for_bounds_cover_the_world() -> None:
    cells = cells_for_bounds(tile_bounds(0, 0, 0))
    assert len(cells) == 324
    assert sum(weight for _, weight in cells) == pytest.approx(2 * 3.141592653589793)


def test_cells_for_small_tile() -> None:
    cells = cells_for_bounds(tile_bounds(4, 3, 2))
    assert {cell.tile_id for cell, _ in cells} == {
        "r14c03",
        "r14c04",
        "r15c03",
        "r15c04",
    }


def test_cells_for_tile_inside_one_dataset_cell() -> None:
    cells = cells_for_bounds(tile_bounds(8, 10, 10))
    assert len(cells) == 1
    assert cells[0][0].tile_id == "r17c00"


def test_moon_point_match() -> None:
    response = client.get("/api/matches/moon/point?lat=0&lon=0")
    assert response.status_code == 200

    data = response.json()
    assert data["body"] == "moon"
    assert data["target"]["kind"] == "point"
    assert data["target"]["point"] == {"lat": 0.0, "lon": 0.0}
    assert data["target"]["geology"]["dataset_tile_ids"] == ["r09c18"]

    match = data["match"]
    assert match["status"] == "match"
    assert match["confidence"] == "medium"
    assert 0 <= match["confidence_score"] <= 100
    assert 0 <= match["similarity"] <= 1
    assert 0 <= match["shared_mass"] <= 1
    assert 0 <= match["coverage"] <= 1
    assert len(match["candidates"]) == 3
    assert match["candidates"][0]["dataset_tile_id"] == "r15c31"
    assert match["candidates"][0]["preview_url"].startswith(
        "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?"
    )
    assert "BBOX=" in match["candidates"][0]["preview_url"]


def test_moon_point_match_has_crosswalk_and_age() -> None:
    data = client.get("/api/matches/moon/point?lat=0&lon=0").json()
    geology = data["target"]["geology"]
    match_keys = {share["key"] for share in geology["match_classes"]}
    assert "crystalline" in match_keys or "sedimentary" in match_keys
    assert "impact" in match_keys
    assert geology["age"]["classes"]
    assert geology["age"]["dominant"] is not None


def test_mars_undivided_terrain_is_insufficient() -> None:
    response = client.get("/api/matches/mars/point?lat=-85&lon=-175")
    assert response.status_code == 200

    data = response.json()
    assert data["target"]["geology"]["dataset_tile_ids"] == ["r00c00"]
    match = data["match"]
    assert match["status"] == "insufficient"
    assert match["confidence"] == "insufficient"
    assert match["confidence_score"] == 0.0
    assert match["candidates"] == []
    assert "impact or undivided" in match["reason"]


def test_mars_age_summary_has_mean_ages() -> None:
    data = client.get("/api/matches/mars/point?lat=-85&lon=-175").json()
    age = data["target"]["geology"]["age"]
    assert age["classes"]
    assert age["mean_min_ga"] is not None
    assert age["mean_max_ga"] is not None
    assert age["mean_min_ga"] <= age["mean_max_ga"]


def test_tile_match_endpoint() -> None:
    response = client.get("/api/matches/moon/4/3/2")
    assert response.status_code == 200

    data = response.json()
    assert data["target"]["kind"] == "tile"
    assert data["target"]["tile"] == {"z": 4, "x": 3, "y": 2}
    assert len(data["target"]["geology"]["dataset_tile_ids"]) == 4
    assert data["match"]["candidates"]
    assert any("area-weights" in note for note in data["notes"])


def test_point_match_is_deterministic() -> None:
    first = build_point_match(BODIES["moon"], 12.5, 45.0)
    second = build_point_match(BODIES["moon"], 12.5, 45.0)
    assert first == second


def test_tile_match_rejects_coarse_zoom() -> None:
    response = client.get("/api/matches/moon/1/0/0")
    assert response.status_code == 422
    assert "too coarse" in response.json()["detail"]


def test_tile_match_rejects_invalid_tile() -> None:
    response = client.get("/api/matches/moon/4/32/0")
    assert response.status_code == 422


def test_match_unknown_body_returns_404() -> None:
    response = client.get("/api/matches/earth/point?lat=0&lon=0")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "query",
    ["lat=91&lon=0", "lat=-91&lon=0", "lat=0&lon=181", "lat=0&lon=-181"],
)
def test_point_match_validates_coordinates(query: str) -> None:
    response = client.get(f"/api/matches/moon/point?{query}")
    assert response.status_code == 422


def test_candidates_are_land_tiles_with_contained_previews() -> None:
    data = client.get("/api/matches/moon/point?lat=0&lon=0").json()
    for candidate in data["match"]["candidates"]:
        assert candidate["coverage"] >= 0.5
        assert candidate["dominant_class"] not in {"", "water", "no_data"}
        preview = candidate["preview_bounds"]
        bounds = candidate["bounds"]
        assert preview["west"] <= bounds["west"]
        assert preview["east"] >= bounds["east"]
        assert preview["south"] <= bounds["south"]
        assert preview["north"] >= bounds["north"]
        match_keys = {share["key"] for share in candidate["match_classes"]}
        assert "impact" not in match_keys
        assert "undivided" not in match_keys


def test_tile_match_uses_same_geology_as_tile_response() -> None:
    tile = client.get("/api/tiles/mars/5/12/9").json()
    match = client.get("/api/matches/mars/5/12/9").json()
    assert tile["geology"] == match["target"]["geology"]
