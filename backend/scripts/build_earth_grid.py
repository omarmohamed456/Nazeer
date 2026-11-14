#!/usr/bin/env python3
"""Build the 5-degree Earth candidate grid from the GLiM 0.5-degree raster.

The source is the gridded GLiM v1.0 dataset from PANGAEA:

    Hartmann, J.; Moosdorf, N. (2012): Global Lithological Map Database v1.0
    (gridded to 0.5-degree spatial resolution). PANGAEA.
    https://doi.org/10.1594/PANGAEA.788537

GLiM is licensed under CC BY 3.0. The source ASCII grid is categorical: each
0.5-degree cell contains one lithological class. We aggregate those cells to
5-degree candidate tiles using cosine-latitude area weights, then normalize
the mapped classes over land.

Run from the repository root:

    python backend/scripts/build_earth_grid.py
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "geology" / "glim" / "glim_wgs84_0point5deg.txt.asc"
DEFAULT_CLASSNAMES = ROOT / "data" / "geology" / "glim" / "Classnames.txt"
DEFAULT_OUTPUT = ROOT / "data" / "geology" / "earth_tiles_5deg.csv"

SOURCE_RESOLUTION_DEG = 0.5
OUTPUT_RESOLUTION_DEG = 5.0
OUTPUT_ROWS = 36
OUTPUT_COLS = 72

CLASS_KEYS = (
    "volcanic",
    "metamorphic",
    "plutonic",
    "sedimentary",
    "surficial_unconsolidated",
    "ice",
)

# GLiM first-level classes -> the app's comparable Earth classes.
# Pyroclastics (py) are volcaniclastic material and are grouped with volcanic
# rocks for this heuristic composition comparison. Evaporites (ev) are
# chemical sedimentary rocks. Inland water (wb) and no-data (nd) are excluded
# from land coverage; ocean cells are marked -9999 in the raster.
GLIM_TO_EARTH = {
    "su": "surficial_unconsolidated",
    "vb": "volcanic",
    "ss": "sedimentary",
    "pb": "plutonic",
    "sm": "sedimentary",
    "sc": "sedimentary",
    "va": "volcanic",
    "mt": "metamorphic",
    "pa": "plutonic",
    "vi": "volcanic",
    "wb": None,
    "py": "volcanic",
    "pi": "plutonic",
    "ev": "sedimentary",
    "nd": None,
    "ig": "ice",
}

OUTPUT_FIELDS = (
    "tile_id",
    "lat_min",
    "lat_max",
    "lon_min",
    "lon_max",
    "earth_mapped_frac",
    "earth_dominant_class",
    *(f"earth_mapped_class_frac_{key}" for key in CLASS_KEYS),
)


def _read_class_codes(path: Path) -> dict[int, str]:
    codes: dict[int, str] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            value = int(row["Value_"])
            code = row["xx"].strip().strip('"').lower()
            codes[value] = code
    return codes


def _read_ascii_grid(path: Path) -> tuple[list[int], int, int, float]:
    header: dict[str, str] = {}
    values: list[int] = []

    with path.open(encoding="ascii") as handle:
        for _ in range(6):
            parts = handle.readline().split()
            header[parts[0].lower()] = parts[1]
        for line in handle:
            values.extend(int(token) for token in line.split())

    ncols = int(header["ncols"])
    nrows = int(header["nrows"])
    cellsize = float(header["cellsize"])
    if ncols * nrows != len(values):
        raise ValueError(
            f"ASCII grid header says {nrows}x{ncols}, found {len(values)} values."
        )
    if cellsize != SOURCE_RESOLUTION_DEG:
        raise ValueError(
            f"Expected a {SOURCE_RESOLUTION_DEG}-degree source grid, got {cellsize}."
        )
    return values, nrows, ncols, cellsize


def build_grid(source: Path, classnames: Path) -> list[dict[str, object]]:
    codes = _read_class_codes(classnames)
    unknown_codes = set(codes.values()) - set(GLIM_TO_EARTH)
    if unknown_codes:
        raise ValueError(f"Unmapped GLiM class codes: {sorted(unknown_codes)}")

    values, nrows, ncols, cellsize = _read_ascii_grid(source)

    class_weights: list[list[Counter[str]]] = [
        [Counter() for _ in range(OUTPUT_COLS)] for _ in range(OUTPUT_ROWS)
    ]
    total_weights = [[0.0] * OUTPUT_COLS for _ in range(OUTPUT_ROWS)]
    land_weights = [[0.0] * OUTPUT_COLS for _ in range(OUTPUT_ROWS)]

    # ESRI ASCII rows run north-to-south. The output grid runs south-to-north,
    # matching the Moon/Mars target table and the rest of the app.
    for index, value in enumerate(values):
        source_row, source_col = divmod(index, ncols)
        lat = 90.0 - (source_row + 0.5) * cellsize
        lon = -180.0 + (source_col + 0.5) * cellsize
        row = min(OUTPUT_ROWS - 1, max(0, int((lat + 90.0) // OUTPUT_RESOLUTION_DEG)))
        col = min(OUTPUT_COLS - 1, max(0, int((lon + 180.0) // OUTPUT_RESOLUTION_DEG)))
        weight = math.cos(math.radians(lat))

        total_weights[row][col] += weight
        if value == -9999:
            continue

        code = codes.get(value)
        if code is None:
            raise ValueError(f"Unknown GLiM raster value {value} at index {index}.")
        earth_class = GLIM_TO_EARTH[code]
        if earth_class is None:
            continue

        land_weights[row][col] += weight
        class_weights[row][col][earth_class] += weight

    output: list[dict[str, object]] = []
    for row in range(OUTPUT_ROWS):
        for col in range(OUTPUT_COLS):
            total = total_weights[row][col]
            land = land_weights[row][col]
            coverage = land / total if total else 0.0
            fractions = {
                key: (class_weights[row][col][key] / land if land else 0.0)
                for key in CLASS_KEYS
            }
            dominant = (
                max(CLASS_KEYS, key=lambda key: fractions[key])
                if land > 0
                else "no_data"
            )
            west = -180.0 + col * OUTPUT_RESOLUTION_DEG
            south = -90.0 + row * OUTPUT_RESOLUTION_DEG
            output.append(
                {
                    "tile_id": f"e{row:02d}c{col:02d}",
                    "lat_min": south,
                    "lat_max": south + OUTPUT_RESOLUTION_DEG,
                    "lon_min": west,
                    "lon_max": west + OUTPUT_RESOLUTION_DEG,
                    "earth_mapped_frac": round(coverage, 6),
                    "earth_dominant_class": dominant,
                    **{
                        f"earth_mapped_class_frac_{key}": round(fractions[key], 6)
                        for key in CLASS_KEYS
                    },
                }
            )
    return output


def write_csv(rows: list[dict[str, object]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--classnames", type=Path, default=DEFAULT_CLASSNAMES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rows = build_grid(args.source, args.classnames)
    write_csv(rows, args.output)

    candidates = [row for row in rows if float(row["earth_mapped_frac"]) >= 0.6]
    dominant = Counter(str(row["earth_dominant_class"]) for row in candidates)
    volcanic = sum(
        1 for row in candidates if float(row["earth_mapped_class_frac_volcanic"]) > 0.01
    )
    print(f"Wrote {len(rows)} cells to {args.output}")
    print(f"Coverage >= 0.6: {len(candidates)}")
    print(f"Dominant classes: {dict(sorted(dominant.items()))}")
    print(f"Volcanic-bearing candidates: {volcanic}")


if __name__ == "__main__":
    main()
