from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS
from rasterio.enums import Resampling
from rasterio.transform import from_origin, rowcol
from rasterio.warp import reproject
from scipy.ndimage import convolve


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "earth_gmt_demo_v1"
CACHE = BASE / "regional_cache"
PARTS = BASE / "parts"

METHOD = "earth-gmt-coarse-demo-v1"
SOURCE = "earth_relief_01m_p"
SPACING_KM = 48.0
CELL = 2000
SIZE = 12000
HALO = 2
N = SIZE // CELL
LAND_THRESHOLD = 0.98
VALID_THRESHOLD = 0.98
GMT = shutil.which("gmt")

SETTINGS = {
    "method_version": METHOD,
    "source": SOURCE,
    "sampling": "spherical_fibonacci",
    "sampling_area_density_parameter_km": SPACING_KM,
    "window_size_m": SIZE,
    "grid_spacing_m": CELL,
    "halo_cells": HALO,
    "land_threshold": LAND_THRESHOLD,
    "elevation_valid_threshold": VALID_THRESHOLD,
    "preliminary_landmask_spacing": "10m",
    "window_landmask_spacing": "1m",
    "shoreline_resolution": "low",
    "latitude_limit_deg": 84,
    "dateline_center_limit_deg": 179.5,
    "comparison_group": "coarse_demo_not_crossplanet_validated",
}


def gmt(*arguments):
    result = subprocess.run(
        [GMT, *map(str, arguments)],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"GMT command failed: {arguments}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result.stdout.strip()


def atomic_parquet(frame, path):
    temporary = path.with_suffix(".tmp.parquet")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def prepare_manifest():
    path = BASE / "settings.json"
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous != SETTINGS:
            raise RuntimeError(
                "Existing build settings differ. Use a new build folder."
            )
    else:
        path.write_text(
            json.dumps(SETTINGS, indent=2), encoding="utf-8"
        )


def derivatives(z, cell):
    valid = np.isfinite(z)
    slope = np.full(z.shape, np.nan, dtype=np.float64)

    dx = (z[1:-1, 2:] - z[1:-1, :-2]) / (2 * cell)
    dy = (z[2:, 1:-1] - z[:-2, 1:-1]) / (2 * cell)

    support = (
        valid[1:-1, 1:-1]
        & valid[1:-1, 2:]
        & valid[1:-1, :-2]
        & valid[2:, 1:-1]
        & valid[:-2, 1:-1]
    )
    values = np.degrees(np.arctan(np.hypot(dx, dy)))
    slope[1:-1, 1:-1] = np.where(support, values, np.nan)

    kernel = np.ones((5, 5), dtype=np.float64)
    safe = np.where(valid, z, 0.0)
    count = convolve(
        valid.astype(float), kernel, mode="constant", cval=0
    )
    mean = convolve(safe, kernel, mode="constant", cval=0) / 25
    mean2 = convolve(safe * safe, kernel, mode="constant", cval=0) / 25

    local = np.sqrt(np.maximum(mean2 - mean * mean, 0))
    local[count != 25] = np.nan
    return slope, local


def self_tests():
    flat = np.full((11, 11), 100.0)
    slope, local = derivatives(flat, 30)
    assert np.allclose(slope[1:-1, 1:-1], 0)
    assert np.allclose(local[2:-2, 2:-2], 0)

    y, x = np.indices((11, 11), dtype=float)
    plane = x * 30 * np.tan(np.radians(10))
    slope, _ = derivatives(plane, 30)
    assert np.allclose(slope[1:-1, 1:-1], 10)

    # For a 5-cell linear sequence, population variance is 2*a^2.
    _, local = derivatives(3 * x, 30)
    assert np.allclose(local[2:-2, 2:-2], 3 * np.sqrt(2))

    broken = flat.copy()
    broken[5, 5] = np.nan
    slope, local = derivatives(broken, 30)
    assert np.isnan(slope[5, 5])
    assert np.isnan(slope[5, 4])
    assert np.isnan(local[3:8, 3:8]).all()
    assert np.isfinite(local[2, 2])

    assert N * N == 36
    assert (N - 2) ** 2 == 16
    assert (N - 4) ** 2 == 4
    print("Synthetic mathematical tests passed.", flush=True)


def sample_grid(path, lon, lat):
    with rasterio.open(path) as src:
        values = src.read(1)
        rows, columns = rowcol(src.transform, lon, lat)
        rows = np.asarray(rows)
        columns = np.asarray(columns)
        inside = (
            (rows >= 0) & (rows < src.height)
            & (columns >= 0) & (columns < src.width)
        )
        result = np.zeros(len(lon), dtype=float)
        result[inside] = values[rows[inside], columns[inside]]
        return result


def make_catalog():
    path = BASE / "catalog.parquet"
    if path.exists():
        return pd.read_parquet(path)

    mask = CACHE / "global_landmask_10m.nc"
    if not mask.exists():
        gmt(
            "grdlandmask", "-Rg", "-I10m", "-r", "-Dl",
            "-N0/1/0/1/0", f"-G{mask}",
        )

    radius_km = 6371.0088
    count = math.ceil(
        4 * math.pi * radius_km**2 / SPACING_KM**2
    )
    index = np.arange(count)
    z = 1 - 2 * (index + 0.5) / count
    lat = np.degrees(np.arcsin(z))
    lon = (
        np.degrees(index * math.pi * (3 - math.sqrt(5))) + 180
    ) % 360 - 180

    center_land = sample_grid(mask, lon, lat) > 0.5

    catalog = pd.DataFrame({
        "window_id": [
            f"earth_fib48_v1_{i:07d}" for i in index
        ],
        "center_lon": lon,
        "center_lat": lat,
        "center_land_preliminary": center_land,
    })

    catalog["tile_x"] = np.floor((lon + 180) / 10).astype(int)
    catalog["tile_y"] = np.floor((lat + 90) / 10).astype(int)
    catalog["batch_id"] = [
        f"region_{x:02d}_{y:02d}"
        for x, y in zip(catalog.tile_x, catalog.tile_y)
    ]

    assert not catalog.window_id.duplicated().any()
    atomic_parquet(catalog, path)
    return catalog


def region_files(tile_x, tile_y):
    key = f"{tile_x:02d}_{tile_y:02d}"
    dem = CACHE / f"dem_{key}.nc"
    mask = CACHE / f"land_{key}.nc"

    west = max(-180, -180 + tile_x * 10 - 2)
    east = min(180, -180 + (tile_x + 1) * 10 + 2)
    south = max(-90, -90 + tile_y * 10 - 2)
    north = min(90, -90 + (tile_y + 1) * 10 + 2)
    region = f"-R{west}/{east}/{south}/{north}"

    if not dem.exists():
        gmt(
            "grdcut", f"@{SOURCE}", region,
            f"-G{dem}", "-Vw",
        )
    if not mask.exists():
        gmt(
            "grdlandmask", region, "-I1m", "-r", "-Dl",
            "-N0/1/0/1/0", f"-G{mask}",
        )
    return dem, mask


def load_grid(path):
    with rasterio.open(path) as src:
        data = src.read(1, masked=True).astype("float64").filled(np.nan)
        return data, src.transform


def warp_grid(data, source_transform, crs, transform, mask=False):
    output = np.full((N + 2 * HALO, N + 2 * HALO), np.nan)
    reproject(
        source=data,
        destination=output,
        src_transform=source_transform,
        src_crs="EPSG:4326",
        src_nodata=np.nan,
        dst_transform=transform,
        dst_crs=crs,
        dst_nodata=np.nan,
        resampling=Resampling.nearest if mask else Resampling.bilinear,
        init_dest_nodata=True,
    )
    return output


def base_record(row):
    return {
        "window_id": row.window_id,
        "batch_id": row.batch_id,
        "body": "earth",
        "center_lon": float(row.center_lon),
        "center_lat": float(row.center_lat),
        "window_size_m": SIZE,
        "grid_spacing_m": CELL,
        "source_collection": SOURCE,
        "source_registry_id": "gmt-earth-relief-01m-p",
        "source_asset_ids_ref": row.batch_id,
        "method_version": METHOD,
        "dataset_build": BASE.name,
        "comparison_group": SETTINGS["comparison_group"],
        "local_std_kernel_cells": 5,
        "local_std_footprint_m": 5 * CELL,
        "local_std_center_span_m": 4 * CELL,
        "elevation_expected_count": N * N,
        "slope_interior_expected_count": (N - 2) ** 2,
        "local_std_interior_expected_count": (N - 4) ** 2,
        "eligible": False,
        "exclusion_reason": "",
        "processing_status": "ok",
    }


def calculate(row, dem_data, land_data):
    record = base_record(row)

    crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={row.center_lat:.10f} "
        f"+lon_0={row.center_lon:.10f} "
        "+datum=WGS84 +units=m +no_defs"
    )
    extent = SIZE / 2 + HALO * CELL
    transform = from_origin(-extent, extent, CELL, CELL)
    record["analysis_crs"] = crs.to_wkt()

    z = warp_grid(*dem_data, crs, transform)
    land = warp_grid(*land_data, crs, transform, mask=True)

    # Conservative pilot rule: a missing buffered elevation rejects
    # the window rather than silently trusting interpolation near gaps.
    if not np.isfinite(z).all():
        record["exclusion_reason"] = "incomplete_buffered_elevation"
        return record

    study = z[HALO:HALO + N, HALO:HALO + N]
    land_study = land[HALO:HALO + N, HALO:HALO + N]

    record["land_fraction_sampled_grid"] = float(
        np.mean(np.isfinite(land_study) & (land_study > 0.5))
    )
    record["elevation_valid_count"] = int(np.isfinite(study).sum())
    record["elevation_valid_fraction"] = float(np.isfinite(study).mean())

    # Do not summarize bathymetry as terrestrial terrain.
    if record["land_fraction_sampled_grid"] < LAND_THRESHOLD:
        record["exclusion_reason"] = "insufficient_land_fraction"
        return record

    slope, local = derivatives(z, CELL)

    s = slope[
        HALO + 1:HALO + N - 1,
        HALO + 1:HALO + N - 1,
    ]
    v = local[
        HALO + 2:HALO + N - 2,
        HALO + 2:HALO + N - 2,
    ]
    e = study[np.isfinite(study)]
    s = s[np.isfinite(s)]
    v = v[np.isfinite(v)]

    p02, median, p98 = np.percentile(e, [2, 50, 98])
    record.update({
        "elevation_min_m": float(e.min()),
        "elevation_max_m": float(e.max()),
        "elevation_median_m": float(median),
        "elevation_p02_m": float(p02),
        "elevation_p98_m": float(p98),
        "relief_p98_p02_m": float(p98 - p02),
        "slope_valid_count": int(s.size),
        "slope_valid_fraction_of_interior": float(s.size / 16),
        "local_std_valid_count": int(v.size),
        "local_std_valid_fraction_of_interior": float(v.size / 4),
    })

    if s.size:
        record.update({
            "slope_median_deg": float(np.median(s)),
            "slope_p90_deg": float(np.percentile(s, 90)),
            "slope_max_deg": float(s.max()),
        })
        edges = [0, 5, 10, 15, 20, 30, 90]
        counts, _ = np.histogram(s, bins=edges)
        for lo, hi, count in zip(edges[:-1], edges[1:], counts):
            record[f"slope_{lo}_{hi}_pct"] = float(
                100 * count / s.size
            )
        assert np.isclose(sum(
            record[f"slope_{a}_{b}_pct"]
            for a, b in zip(edges[:-1], edges[1:])
        ), 100)
        assert 0 <= s.min() <= s.max() <= 90

    if v.size:
        record["local_std_median_m"] = float(np.median(v))
        record["local_std_p90_m"] = float(np.percentile(v, 90))
        assert v.min() >= 0

    assert e.min() <= p02 <= median <= p98 <= e.max()
    assert record["relief_p98_p02_m"] >= 0

    record["eligible"] = bool(
        record["elevation_valid_fraction"] >= VALID_THRESHOLD
        and s.size == 16
        and v.size == 4
    )
    if not record["eligible"]:
        record["exclusion_reason"] = "insufficient_valid_feature_support"
    return record


def merge_outputs(catalog):
    paths = sorted(PARTS.glob("part_*.parquet"))
    if not paths:
        return pd.DataFrame()

    frame = pd.concat(
        [pd.read_parquet(path) for path in paths],
        ignore_index=True,
    )
    if frame.window_id.duplicated().any():
        raise RuntimeError("Duplicate output window IDs.")
    if not frame.method_version.eq(METHOD).all():
        raise RuntimeError("Incompatible method versions.")
    if not set(frame.window_id).issubset(set(catalog.window_id)):
        raise RuntimeError("Output contains unknown window IDs.")

    atomic_parquet(frame, BASE / "features.parquet")
    frame.to_csv(BASE / "features.csv", index=False)
    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit", type=int, default=100,
        help="Maximum new center-land windows. 0 means all remaining.",
    )
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must be zero or positive")

    if GMT is None:
        raise SystemExit("GMT is not available on PATH.")

    for directory in (BASE, CACHE, PARTS):
        directory.mkdir(parents=True, exist_ok=True)

    prepare_manifest()
    self_tests()
    print(f"GMT version: {gmt('--version')}", flush=True)

    started = time.perf_counter()
    catalog = make_catalog()
    previous = merge_outputs(catalog)
    done = set(previous.window_id) if not previous.empty else set()

    candidates = catalog[
        catalog.center_land_preliminary
        & ~catalog.window_id.isin(done)
    ].copy()

    # Start near the verified Chile pilot, then expand.
    candidates["priority"] = (
        abs(candidates.center_lat + 24.2)
        + abs(
            (candidates.center_lon + 68.2 + 180) % 360 - 180
        )
    )
    region_order = (
        candidates.groupby("batch_id").priority.min()
        .sort_values().index
    )

    count = 0
    buffer = []
    part_number = len(list(PARTS.glob("part_*.parquet")))

    def flush():
        nonlocal part_number
        if not buffer:
            return
        path = PARTS / f"part_{part_number:06d}.parquet"
        if path.exists():
            raise RuntimeError(f"Refusing to overwrite {path}")
        atomic_parquet(pd.DataFrame(buffer), path)
        buffer.clear()
        part_number += 1

    try:
        for batch_id in region_order:
            group = candidates[candidates.batch_id == batch_id]
            group = group.sort_values("priority")
            dem_data = land_data = None

            for row in group.itertuples():
                if args.limit and count >= args.limit:
                    break

                if (
                    abs(row.center_lat) > 84
                    or abs(row.center_lon) > 179.5
                ):
                    record = base_record(row)
                    record["exclusion_reason"] = (
                        "polar_or_dateline_not_implemented"
                    )
                else:
                    if dem_data is None:
                        dem_path, mask_path = region_files(
                            int(row.tile_x), int(row.tile_y)
                        )
                        dem_data = load_grid(dem_path)
                        land_data = load_grid(mask_path)
                    record = calculate(row, dem_data, land_data)

                buffer.append(record)
                count += 1

                if len(buffer) >= 100:
                    flush()
                    print(
                        f"Saved {count} new windows; "
                        f"elapsed {(time.perf_counter()-started)/60:.1f} min",
                        flush=True,
                    )

            if args.limit and count >= args.limit:
                break

    except BaseException as exc:
        flush()
        (BASE / "last_failure.txt").write_text(
            f"{type(exc).__name__}: {exc}", encoding="utf-8"
        )
        raise
    finally:
        flush()

    final = merge_outputs(catalog)
    eligible = int(final.eligible.fillna(False).sum()) if len(final) else 0

    manifest = {
        "settings": SETTINGS,
        "gmt_version": gmt("--version"),
        "catalog_count": len(catalog),
        "preliminary_center_land_count": int(
            catalog.center_land_preliminary.sum()
        ),
        "processed_count": len(final),
        "eligible_count": eligible,
        "new_windows_this_run": count,
        "elapsed_seconds_this_run": time.perf_counter() - started,
        "remaining_center_land_windows": int(
            catalog.center_land_preliminary.sum() - len(final)
        ),
        "regional_source_files": [
            str(p.relative_to(BASE))
            for p in sorted(CACHE.glob("dem_*.nc"))
        ],
        "settings_sha256": hashlib.sha256(
            json.dumps(SETTINGS, sort_keys=True).encode()
        ).hexdigest(),
        "limitations": [
            "Sparse sampled centers, not exhaustive area coverage.",
            "Coarse preliminary land mask can miss small islands.",
            "Sampled-grid land fraction is not exact polygon area fraction.",
            "Poles and date-line-adjacent centers explicitly excluded.",
            "Source gaps within coarse cells may not be observable.",
            "No cross-planet resolution/filter harmonization yet.",
            "Vertical datum and dataset revision require source-registry review.",
            "Only 36 elevation, 16 slope, and 4 local-variation cells.",
        ],
        "official_source": (
            "https://www.generic-mapping-tools.org/"
            "remote-datasets/earth-relief.html"
        ),
    }
    (BASE / "build_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print(f"\nProcessed records: {len(final)}")
    print(f"Eligible records: {eligible}")
    print(
        "Remaining preliminary center-land windows:",
        manifest["remaining_center_land_windows"],
    )
    print(f"Outputs: {BASE}")
    print("Main artifact: features.parquet")


if __name__ == "__main__":
    main()