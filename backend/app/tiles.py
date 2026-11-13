from __future__ import annotations

import math

from .models import (
    BodyInfo,
    Bounds,
    Center,
    SizeKm,
    TileIndex,
    TileResponse,
)
from .simulated import build_analysis


def validate_tile(z: int, x: int, y: int, *, min_zoom: int, max_zoom: int) -> None:
    """Raise ValueError when a tile index does not exist in the pyramid."""
    if z < min_zoom or z > max_zoom:
        raise ValueError(
            f"Zoom {z} is outside the supported range {min_zoom}\u2013{max_zoom}."
        )

    cols = 2 ** (z + 1)
    rows = 2**z

    if not 0 <= x < cols:
        raise ValueError(f"Tile column {x} is outside 0\u2013{cols - 1} at zoom {z}.")
    if not 0 <= y < rows:
        raise ValueError(f"Tile row {y} is outside 0\u2013{rows - 1} at zoom {z}.")


def tile_bounds(z: int, x: int, y: int) -> Bounds:
    """Return the geographic bounds of a tile in the 2:1 equirectangular grid."""
    cols = 2 ** (z + 1)
    rows = 2**z

    west = -180.0 + (x / cols) * 360.0
    east = -180.0 + ((x + 1) / cols) * 360.0
    north = 90.0 - (y / rows) * 180.0
    south = 90.0 - ((y + 1) / rows) * 180.0

    return Bounds(
        west=round(west, 6),
        south=round(south, 6),
        east=round(east, 6),
        north=round(north, 6),
    )


def tile_center(bounds: Bounds) -> Center:
    return Center(
        lat=round((bounds.north + bounds.south) / 2.0, 6),
        lon=round((bounds.east + bounds.west) / 2.0, 6),
    )


def approx_tile_size_km(bounds: Bounds, radius_km: float) -> SizeKm:
    """Approximate ground size; width is measured at the tile's center latitude."""
    center_lat = (bounds.north + bounds.south) / 2.0
    width = (
        math.radians(bounds.east - bounds.west)
        * radius_km
        * math.cos(math.radians(center_lat))
    )
    height = math.radians(bounds.north - bounds.south) * radius_km
    return SizeKm(width=round(width, 1), height=round(height, 1))


def tile_image_url(template: str, z: int, x: int, y: int) -> str:
    return (
        template.replace("{z}", str(z))
        .replace("{x}", str(x))
        .replace("{y}", str(y))
    )


def build_tile_response(body: BodyInfo, z: int, x: int, y: int) -> TileResponse:
    validate_tile(z, x, y, min_zoom=body.min_zoom, max_zoom=body.max_zoom)

    bounds = tile_bounds(z, x, y)
    center = tile_center(bounds)

    return TileResponse(
        body=body.id,
        body_name=body.name,
        layer=body.layer,
        tile=TileIndex(z=z, x=x, y=y),
        image_url=tile_image_url(body.tile_url_template, z, x, y),
        bounds=bounds,
        center=center,
        approx_size_km=approx_tile_size_km(bounds, body.radius_km),
        analysis=build_analysis(body.id, z, x, y, center.lat),
    )
