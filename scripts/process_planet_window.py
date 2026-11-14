from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject


ROOT = Path(__file__).resolve().parents[1]
METHOD = "planet-gmt-coarse-window-v1"

SIZE = 12000
CELL = 2000
N = SIZE // CELL
HALO = 2

BODIES = {
    "moon": {
        "radius_m": 1737400.0,
        "source": "moon_relief_01m_p",
        "upstream": "Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif",
        "documentation": (
            "https://www.generic-mapping-tools.org/"
            "remote-datasets/moon-relief.html"
        ),
    },
    "mars": {
        "radius_m": 3396190.0,
        "source": "mars_relief_01m_p",
        "upstream": "Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.tif",
        "documentation": (
            "https://www.generic-mapping-tools.org/"
            "remote-datasets/mars-relief.html"
        ),
    },
}


def load_earth_functions():
    path = ROOT / "scripts/build_earth_gmt_database.py"
    if not path.is_file():
        raise SystemExit(f"Required existing script missing:\n{path}")

    spec = importlib.util.spec_from_file_location(
        "earth_feature_functions", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_gmt(gmt, *arguments):
    result = subprocess.run(
        [gmt, *map(str, arguments)],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"GMT failed:\n{result.stdout}\n{result.stderr}"
        )
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", choices=BODIES, required=True)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    args = parser.parse_args()

    if not np.isfinite([args.lat, args.lon]).all():
        parser.error("Coordinates must be finite.")
    if not -84 <= args.lat <= 84:
        parser.error("This pilot supports latitudes between -84 and 84.")
    if not -180 <= args.lon <= 360:
        parser.error("Longitude must be between -180 and 360.")

    lon = (args.lon + 180) % 360 - 180
    lat = args.lat

    gmt = shutil.which("gmt")
    if gmt is None:
        raise SystemExit("GMT is not available on PATH.")

    earth = load_earth_functions()
    earth.self_tests()

    settings = BODIES[args.body]
    radius = settings["radius_m"]

    geographic = CRS.from_proj4(
        f"+proj=longlat +R={radius} +no_defs"
    )
    projected = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat:.10f} "
        f"+lon_0={lon:.10f} +R={radius} +units=m +no_defs"
    )

    extent = SIZE / 2 + HALO * CELL
    transform = from_origin(-extent, extent, CELL, CELL)

    # Densify the buffered square boundary for the source request.
    edge = np.linspace(-extent, extent, 101)
    xs = np.concatenate([
        edge, edge,
        np.full_like(edge, -extent),
        np.full_like(edge, extent),
    ])
    ys = np.concatenate([
        np.full_like(edge, -extent),
        np.full_like(edge, extent),
        edge, edge,
    ])

    inverse = Transformer.from_crs(
        projected, geographic, always_xy=True
    )
    longitudes, latitudes = inverse.transform(xs, ys)
    longitudes = np.asarray(longitudes)
    latitudes = np.asarray(latitudes)

    # Express longitude offsets relative to the window center.
    offsets = (longitudes - lon + 180) % 360 - 180
    margin = 0.1
    west = lon + float(offsets.min()) - margin
    east = lon + float(offsets.max()) + margin
    south = float(latitudes.min()) - margin
    north = float(latitudes.max()) + margin

    if west < -180 or east > 180:
        raise SystemExit(
            "This window crosses the date line. "
            "Choose another pilot center; wrapping is not implemented."
        )
    if south <= -90 or north >= 90:
        raise SystemExit("Polar crossing is not supported in this pilot.")

    configuration = {
        "body": args.body,
        "center_lon": lon,
        "center_lat": lat,
        "radius_m": radius,
        "window_size_m": SIZE,
        "grid_spacing_m": CELL,
        "source": settings["source"],
        "method_version": METHOD,
    }
    digest = hashlib.sha256(
        json.dumps(configuration, sort_keys=True).encode()
    ).hexdigest()[:16]
    window_id = f"{args.body}_{digest}"

    output = ROOT / "data/planetary_gmt_pilot" / args.body / window_id
    output.mkdir(parents=True, exist_ok=True)

    source_path = output / "source_subset.nc"
    feature_path = output / "features.csv"

    if feature_path.exists():
        raise SystemExit(
            f"This window already has outputs:\n{output}\n"
            "Existing results were not overwritten."
        )

    if not source_path.exists():
        print(f"Retrieving {settings['source']}...", flush=True)
        run_gmt(
            gmt,
            "grdcut",
            f"@{settings['source']}",
            f"-R{west:.10f}/{east:.10f}/{south:.10f}/{north:.10f}",
            f"-G{source_path}",
            "-Vw",
        )

    source, source_transform = earth.load_grid(source_path)

    if not np.isfinite(source).all():
        raise SystemExit(
            "The source subset contains invalid elevations. "
            "This pilot stops rather than interpolate across gaps."
        )

    buffered = np.full(
        (N + 2 * HALO, N + 2 * HALO),
        np.nan,
        dtype=np.float64,
    )

    reproject(
        source=source,
        destination=buffered,
        src_transform=source_transform,
        src_crs=geographic,
        dst_transform=transform,
        dst_crs=projected,
        src_nodata=np.nan,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
        init_dest_nodata=True,
    )

    if not np.isfinite(buffered).all():
        raise SystemExit(
            "The projected buffer contains invalid elevations. "
            "No feature table was written."
        )

    study = buffered[HALO:HALO + N, HALO:HALO + N]
    slope, local = earth.derivatives(buffered, CELL)

    slope_values = slope[
        HALO + 1:HALO + N - 1,
        HALO + 1:HALO + N - 1,
    ].ravel()

    local_values = local[
        HALO + 2:HALO + N - 2,
        HALO + 2:HALO + N - 2,
    ].ravel()

    assert study.shape == (6, 6)
    assert slope_values.size == 16
    assert local_values.size == 4
    assert np.isfinite(slope_values).all()
    assert np.isfinite(local_values).all()

    p02, median, p98 = np.percentile(study, [2, 50, 98])

    record = {
        "window_id": window_id,
        "batch_id": f"{args.body}_pilot_v1",
        "body": args.body,
        "center_lon": lon,
        "center_lat": lat,
        "window_size_m": SIZE,
        "grid_spacing_m": CELL,
        "analysis_crs": projected.to_wkt(),
        "analysis_reference_radius_m": radius,
        "source_collection": settings["source"],
        "source_registry_id": f"gmt-{args.body}-relief-01m-p",
        "source_asset_ids_ref": "source_manifest.json",
        "method_version": METHOD,
        "dataset_build": "planetary_gmt_pilot_v1",
        "comparison_group": "coarse_demo_not_crossplanet_validated",
        "elevation_expected_count": 36,
        "elevation_valid_count": 36,
        "elevation_valid_fraction": 1.0,
        "slope_interior_expected_count": 16,
        "slope_valid_count": 16,
        "slope_valid_fraction_of_interior": 1.0,
        "local_std_interior_expected_count": 4,
        "local_std_valid_count": 4,
        "local_std_valid_fraction_of_interior": 1.0,
        "elevation_min_m": float(study.min()),
        "elevation_max_m": float(study.max()),
        "elevation_median_m": float(median),
        "elevation_p02_m": float(p02),
        "elevation_p98_m": float(p98),
        "relief_p98_p02_m": float(p98 - p02),
        "slope_median_deg": float(np.median(slope_values)),
        "slope_p90_deg": float(np.percentile(slope_values, 90)),
        "slope_max_deg": float(slope_values.max()),
        "local_std_median_m": float(np.median(local_values)),
        "local_std_p90_m": float(np.percentile(local_values, 90)),
        "local_std_kernel_cells": 5,
        "local_std_footprint_m": 10000,
        "local_std_center_span_m": 8000,
        "land_fraction_sampled_grid": np.nan,
        "eligible": True,
        "exclusion_reason": "",
        "processing_status": "ok",
    }

    edges = [0, 5, 10, 15, 20, 30, 90]
    counts, _ = np.histogram(slope_values, bins=edges)
    for low, high, count in zip(edges[:-1], edges[1:], counts):
        record[f"slope_{low}_{high}_pct"] = float(
            100 * count / slope_values.size
        )

    assert study.min() <= p02 <= median <= p98 <= study.max()
    assert 0 <= slope_values.min() <= slope_values.max() <= 90
    assert local_values.min() >= 0
    assert np.isclose(counts.sum() / 16 * 100, 100)

    frame = pd.DataFrame([record])
    frame.to_csv(feature_path, index=False, encoding="utf-8-sig")
    frame.to_parquet(output / "features.parquet", index=False)

    pd.DataFrame(study).to_csv(
        output / "elevation_36_cells.csv",
        index=False,
        header=False,
        encoding="utf-8-sig",
    )

    manifest = {
        **configuration,
        "source_upstream": settings["upstream"],
        "documentation": settings["documentation"],
        "gmt_version": run_gmt(gmt, "--version"),
        "source_file_sha256": hashlib.sha256(
            source_path.read_bytes()
        ).hexdigest(),
        "source_request_bounds_deg": [west, east, south, north],
        "source_geographic_crs": geographic.to_wkt(),
        "analysis_crs": projected.to_wkt(),
        "buffer_transform": list(transform)[:6],
        "resampling": "bilinear",
        "vertical_operation": "none; source heights retained",
        "source_vertical_reference_status": (
            "Must be verified in upstream documentation; "
            "not inferred from horizontal radius."
        ),
        "filter_width_full_6sigma_km": 2.8,
        "method_checks": "shared Earth synthetic tests passed",
        "limitations": [
            "Coarse screening-grade measurements.",
            "Spherical horizontal geometry is an explicit assumption.",
            "No cross-planet preprocessing harmonization yet.",
            "Only 36 elevation, 16 slope and 4 local-variation values.",
            "No date-line or polar-crossing handling.",
            "Source elevation gaps are rejected, not filled.",
        ],
    }
    (output / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print("\nWINDOW PROCESSING PASSED")
    for field in [
        "body",
        "window_id",
        "elevation_min_m",
        "elevation_max_m",
        "elevation_median_m",
        "relief_p98_p02_m",
        "slope_median_deg",
        "local_std_median_m",
    ]:
        print(f"{field}: {record[field]}")

    print(f"\nOutputs:\n{output}")
    print("Excel grid: elevation_36_cells.csv")
    print("This window is not yet validated for cross-planet ranking.")


if __name__ == "__main__":
    main()