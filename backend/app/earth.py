from __future__ import annotations

import math
import random

from .models import Center, EarthAnalogResponse, SizeKm, TileIndex

EARTH_RADIUS_KM = 6371.0088
EARTH_MIN_ZOOM = 4
EARTH_MAX_ZOOM = 6
GIBS_LAYER = "BlueMarble_ShadedRelief_Bathymetry"
GIBS_TILE_TEMPLATE = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/"
    f"{GIBS_LAYER}/default/500m/{{z}}/{{y}}/{{x}}.jpeg"
)

ANALOG_NOTE = (
    "Prototype only \u2014 this is a random NASA Blue Marble tile, "
    "not a real similarity match."
)


def earth_grid_size(z: int) -> tuple[int, int]:
    """GIBS 500m grid: 5 columns at z2, doubling thereafter."""
    if z < 2:
        raise ValueError("The Earth grid is only defined for zoom >= 2.")
    cols = 5 * 2 ** (z - 2)
    return cols, cols // 2


def random_earth_tile(seed: int | None = None) -> EarthAnalogResponse:
    if seed is None:
        seed = random.SystemRandom().randrange(0, 2**31)

    rng = random.Random(seed)
    z = rng.randint(EARTH_MIN_ZOOM, EARTH_MAX_ZOOM)
    cols, rows = earth_grid_size(z)
    x = rng.randrange(cols)
    # Avoid the extreme polar rows where the random preview is mostly ice.
    margin = max(1, int(rows * 0.08))
    y = rng.randint(margin, rows - margin - 1)

    west = -180.0 + (x / cols) * 360.0
    east = -180.0 + ((x + 1) / cols) * 360.0
    north = 90.0 - (y / rows) * 180.0
    south = 90.0 - ((y + 1) / rows) * 180.0

    center_lat = (north + south) / 2.0
    center_lon = (east + west) / 2.0

    width = (
        math.radians(east - west)
        * EARTH_RADIUS_KM
        * math.cos(math.radians(center_lat))
    )
    height = math.radians(north - south) * EARTH_RADIUS_KM

    return EarthAnalogResponse(
        note=ANALOG_NOTE,
        seed=seed,
        tile=TileIndex(z=z, x=x, y=y),
        image_url=(
            GIBS_TILE_TEMPLATE.replace("{z}", str(z))
            .replace("{x}", str(x))
            .replace("{y}", str(y))
        ),
        center=Center(lat=round(center_lat, 6), lon=round(center_lon, 6)),
        approx_size_km=SizeKm(width=round(width, 1), height=round(height, 1)),
        match_pct=rng.randint(64, 96),
    )
