from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "data/planetary_gmt_pilot"
EXPORTS = ROOT / "data/planetary_gmt_pilot/csv_exports"
PARTS = ROOT / "data/planetary_gmt_pilot/parts"

RADIUS = {
    "moon": 1737400.0,
    "mars": 3396190.0,
}


def count_windows(body, west, east, south, north, spacing):
    radius = RADIUS[body]
    lat_step = math.degrees(spacing / radius)
    lats = np.arange(
        south + lat_step / 2,
        north - lat_step / 2 + lat_step / 2,
        lat_step,
    )
    total = 0
    for lat in lats:
        lon_step = math.degrees(
            spacing / (radius * math.cos(math.radians(lat)))
        )
        total += max(
            0,
            int(math.floor((east - west) / lon_step)),
        )
    return total


def find_existing(body, lat, lon):
    body_dir = PILOT / body
    if not body_dir.exists():
        return None

    for path in body_dir.glob("*/features.csv"):
        try:
            row = pd.read_csv(path).iloc[0]
        except Exception:
            continue

        if (
            abs(float(row["center_lat"]) - lat) < 1e-9
            and abs(float(row["center_lon"]) - lon) < 1e-9
        ):
            return path

    return None


def process_window(python_exe, body, lat, lon):
    command = [
        python_exe,
        str(ROOT / "scripts/process_planet_window.py"),
        "--body", body,
        "--lat", f"{lat:.10f}",
        "--lon", f"{lon:.10f}",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        shell=False,
    )

    if result.returncode:
        return False, result.stderr.strip()[-1000:]

    return True, ""


def export_catalog(body):
    files = sorted((PILOT / body).glob("*/features.csv"))
    if not files:
        raise SystemExit(f"No processed {body} windows found.")

    frames = []
    for path in files:
        try:
            frames.append(pd.read_csv(path))
        except Exception as error:
            print(f"Skipping unreadable file {path}: {error}")

    if not frames:
        raise SystemExit("No readable feature CSV files found.")

    catalog = pd.concat(frames, ignore_index=True)

    required = [
        "window_id", "body", "center_lon", "center_lat",
        "elevation_min_m", "elevation_max_m", "elevation_median_m",
        "relief_p98_p02_m", "slope_median_deg", "slope_max_deg",
        "local_std_median_m", "eligible", "processing_status",
    ]
    missing = [column for column in required if column not in catalog]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    catalog = catalog.drop_duplicates(
        subset=["window_id"], keep="last"
    )
    catalog = catalog.sort_values(
        ["center_lat", "center_lon"], ignore_index=True
    )

    PARTS.mkdir(parents=True, exist_ok=True)
    EXPORTS.mkdir(parents=True, exist_ok=True)

    part_path = PARTS / f"{body}_catalog_latest.parquet"
    catalog.to_parquet(part_path, index=False)

    csv_path = EXPORTS / f"{body}_windows.csv"
    catalog.to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(f"Catalog rows: {len(catalog)}")
    print(f"Parquet: {part_path}")
    print(f"CSV: {csv_path}")
    print(
        "Eligible rows: "
        f"{int(catalog['eligible'].astype(bool).sum())}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", choices=RADIUS, required=True)
    parser.add_argument("--west", type=float, required=True)
    parser.add_argument("--east", type=float, required=True)
    parser.add_argument("--south", type=float, required=True)
    parser.add_argument("--north", type=float, required=True)
    parser.add_argument("--spacing", type=float, default=2000)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--fail-limit", type=int, default=10)
    parser.add_argument("--export-only", action="store_true")
    args = parser.parse_args()

    if not -180 <= args.west < args.east <= 180:
        parser.error("Use west < east within -180 to 180.")
    if not -84 <= args.south < args.north <= 84:
        parser.error("Use south < north within -84 to 84.")
    if args.spacing <= 0:
        parser.error("Spacing must be positive.")

    python_exe = sys.executable

    if args.export_only:
        export_catalog(args.body)
        return

    planned = count_windows(
        args.body, args.west, args.east,
        args.south, args.north, args.spacing,
    )
    print(f"Planned window centers: {planned}")

    if planned > 50000 and not args.max_windows:
        raise SystemExit(
            "This region would create more than 50,000 windows. "
            "Use a smaller region or set --max-windows for a test."
        )

    radius = RADIUS[args.body]
    lat_step = math.degrees(args.spacing / radius)

    lats = np.arange(
        args.south + lat_step / 2,
        args.north - lat_step / 2 + lat_step / 2,
        lat_step,
    )

    completed = 0
    failures = 0
    processed = 0

    for lat in lats:
        lon_step = math.degrees(
            args.spacing / (radius * math.cos(math.radians(lat)))
        )
        lons = np.arange(
            args.west + lon_step / 2,
            args.east - lon_step / 2 + lon_step / 2,
            lon_step,
        )

        for lon in lons:
            if args.max_windows and completed >= args.max_windows:
                break

            existing = find_existing(args.body, float(lat), float(lon))
            if existing is not None:
                completed += 1
                continue

            ok, error = process_window(
                python_exe, args.body, float(lat), float(lon)
            )

            if ok:
                completed += 1
                processed += 1
                if processed % 25 == 0:
                    print(
                        f"Processed {processed}; "
                        f"completed total {completed}"
                    )
            else:
                failures += 1
                print(f"FAILED at {lat:.6f}, {lon:.6f}")
                print(error)
                if failures >= args.fail_limit:
                    raise SystemExit(
                        "Failure limit reached. Existing windows "
                        "remain usable; rerun later to resume."
                    )

    export_catalog(args.body)


if __name__ == "__main__":
    main()