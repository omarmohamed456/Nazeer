from app.simulated import build_analysis


def test_same_tile_is_stable() -> None:
    first = build_analysis("moon", 6, 17, 22, center_lat=-12.5)
    second = build_analysis("moon", 6, 17, 22, center_lat=-12.5)
    assert first == second


def test_moon_fields_and_ranges() -> None:
    analysis = build_analysis("moon", 3, 2, 1, center_lat=45.0)
    labels = [field.label for field in analysis.fields]

    assert "Terrain class" in labels
    assert "Crater density" in labels
    assert 0 <= analysis.confidence_pct <= 100


def test_mars_polar_terrain() -> None:
    analysis = build_analysis("mars", 3, 1, 0, center_lat=84.0)
    terrain = next(field.value for field in analysis.fields if field.label == "Terrain class")

    assert terrain in {
        "Polar layered deposits",
        "Ice-rich polar terrain",
        "Frozen dune field",
    }


def test_mars_fields_include_dust_and_thermal_inertia() -> None:
    analysis = build_analysis("mars", 4, 5, 4, center_lat=10.0)
    labels = [field.label for field in analysis.fields]

    assert "Dust cover" in labels
    assert "Thermal inertia" in labels
