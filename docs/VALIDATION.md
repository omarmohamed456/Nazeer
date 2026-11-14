# Validation and Manual Checks

## What has been checked

### 1. Shared feature-function tests

The Earth feature-calculation module includes synthetic self-tests. These
check basic mathematical behaviour of the shared feature functions.

These tests verify implementation logic. They do not validate real-world
terrain accuracy.

### 2. One-window processing

One Moon window and multiple Mars windows were processed successfully.

Each output includes:

- `features.csv`
- `features.parquet`
- `elevation_36_cells.csv`
- `source_manifest.json`

A successful run confirms that the pipeline completed, not that its terrain
values are independently accurate.

### 3. Excel summary check

For pilot Moon and Mars windows, the exported 36-cell elevation grid was
opened in Excel.

The following formulas were calculated:

```text
=COUNT(A1:F6)
=MIN(A1:F6)
=MAX(A1:F6)
=MEDIAN(A1:F6)
```

The results matched:

- `elevation_valid_count`
- `elevation_min_m`
- `elevation_max_m`
- `elevation_median_m`

This verifies that the saved summary statistics are reproducible from the
exported grid.

It does not validate the source elevation data, reprojection, slope, or
local-variation calculations.

### 4. GMT grdtrack extraction check

`scripts/check_cells_with_gmt.py` independently samples the same GMT product
at the calculated latitude/longitude of all 36 cell centers.

It uses GMT `grdtrack` with bilinear interpolation and compares the result
with `elevation_36_cells.csv`.

It also tests flipped, transposed, and rotated grid layouts to detect
orientation errors.

A passing result indicates that the exported grid is consistent with direct
GMT sampling at the intended cell centers.

It does not validate the underlying GMT elevation data itself.

### 5. NASA Trek manual check

Selected Moon and Mars cell-center coordinates were checked manually in NASA
Solar System Treks.

For each point:

1. The coordinate was copied from `cells_check.csv`.
2. A short elevation-profile line was drawn in Moon Trek or Mars Trek.
3. The elevation at the profile center was recorded.
4. The value was compared with the pipeline’s exported elevation.

Trek is an independent external visualization and profiling check. Small
differences are expected because Trek may use a different DEM layer,
resampling method, and profile interpolation.

This check does not establish absolute elevation accuracy.

## What is not yet validated

- Absolute accuracy of Earth, Moon, or Mars elevations.
- Equivalence of source filtering and quantization across bodies.
- Accuracy of slope and local-variation features against reference data.
- Cross-body terrain-analog validity.
- The appropriateness of the Mahalanobis distance for all terrain types.
- Sensitivity of rankings to feature selection and scaling.
- Global coverage or unbiased sampling.
- Landing-site safety or operational suitability.

## Safe claims

> “For pilot Moon and Mars windows, Excel checks confirmed that exported
> 36-cell elevation grids reproduce the saved minimum, maximum, and median
> statistics.”

> “An independent GMT `grdtrack` check reproduced the exported elevation
> grids at calculated cell centers, verifying extraction and orientation
> against the same GMT source product.”

> “Selected cell-center elevations were manually cross-checked in NASA Trek
> and were broadly consistent with pipeline outputs.”

## Claims to avoid

> “The elevation data are accurate.”

> “The Moon and Mars terrain has been validated.”

> “The Earth matches are scientifically validated terrain analogs.”

> “The system identifies safe landing sites.”

## Current status

The pipeline is suitable for a screening-grade demonstration of terrain-shape
matching. It is not yet a validated scientific terrain-analog system.