# Planetary Terrain-Analog Finder

A screening-grade geospatial tool that identifies candidate Earth terrain
windows with terrain-shape characteristics similar to a selected Moon or Mars
location.

The system compares 12 km × 12 km terrain windows using elevation-derived
features such as relief, slope, and local elevation variation. It does not
claim that matched locations are geologically equivalent or suitable for
landing, rover operations, or habitat placement.

## What it does

1. Builds an Earth catalog of candidate 12 km × 12 km terrain windows.
2. Processes a selected Moon or Mars 12 km × 12 km window on demand.
3. Calculates terrain-shape features using a consistent local-grid workflow.
4. Compares the extraterrestrial query window with eligible Earth windows.
5. Returns the closest Earth terrain-shape matches.

## Terrain window

Each candidate window is:

- 12 km × 12 km
- Sampled on a 2 km grid
- Represented by 36 elevation cells
- Described by 16 interior slope samples
- Described by 4 interior local-variation values

A CSV row describes a window, not a single coordinate.

## Data sources

| Body | GMT remote product | Underlying source |
|---|---|---|
| Earth | `earth_relief_01m_p` | SRTM15+ |
| Moon | `moon_relief_01m_p` | USGS Lunar LRO LOLA global DEM |
| Mars | `mars_relief_01m_p` | USGS Mars MGS MOLA and Mars Express HRSC blended DEM |

GMT downloads and caches the required source tiles. Python performs local
window extraction, reprojection, and feature calculation.

See `docs/DATA_SOURCES.md` for source details and limitations.

## Features

The cross-body matcher uses terrain-shape features, not absolute elevation:

- Relief: 98th elevation percentile minus 2nd percentile
- Median slope
- 90th-percentile slope
- Local elevation variation

Raw elevation minimum, maximum, median, and percentiles are retained in the
feature tables but excluded from cross-body similarity scoring because Earth,
Moon, and Mars use different vertical reference systems.

## Validation performed

- Synthetic tests for the shared feature-calculation functions.
- One-window processing tests for Moon and Mars.
- Excel checks confirming that exported 36-cell elevation grids reproduce
  the saved minimum, maximum, and median statistics.
- Independent GMT `grdtrack` sampling checks comparing the exported cells
  with the same GMT source product at calculated cell centers.
- Manual NASA Trek elevation-profile checks for selected Moon and Mars
  cell centers.

These checks verify extraction, orientation, and summary consistency.
They do not independently establish the absolute accuracy of the underlying
planetary elevation models or validate cross-body terrain analogs.

See `docs/VALIDATION.md`.

## Important limitation

This is a screening-grade demonstration. Matched Earth locations are
**candidate terrain analogs**, not validated scientific analogs, landing
sites, or operational test sites.

## Repository structure

```text
scripts/                  Processing, catalog, matching, and validation code
docs/                     Data-source, method, and validation documentation
data/planetary_gmt_pilot/ Moon and Mars pilot outputs and regional catalogs
```

## Status

- Earth regional catalog: available.
- Moon regional pilot catalog: available.
- Mars regional pilot catalog: available.
- Cross-body matching: available as a screening heuristic.
- Full Moon and Mars global catalogs: not built because they would require
  millions of windows at the current 2 km spacing.