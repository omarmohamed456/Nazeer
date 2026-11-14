# Method

## Window definition

Each terrain window is 12 km × 12 km and is sampled on a 2 km grid.

This produces:

- 6 × 6 = 36 elevation cells
- 4 × 4 = 16 interior slope cells
- 2 × 2 = 4 interior local-variation values

## Features

### Elevation statistics

The pipeline calculates:

- Minimum elevation
- Maximum elevation
- Median elevation
- 2nd-percentile elevation
- 98th-percentile elevation

### Relief

Relief is:

```text
relief = elevation 98th percentile - elevation 2nd percentile
```

This measures elevation spread within the window.

### Slope

Slope is calculated for the 16 interior cells.

The pipeline reports:

- Median slope
- 90th-percentile slope
- Maximum slope
- Percentage of samples in slope bins

### Local elevation variation

Local elevation variation is calculated using a 5 × 5 neighbourhood.

At 2 km spacing, this neighbourhood has:

- A 10 km footprint
- An 8 km center span

It is reported for the 4 central interior values.

## Cross-body matching

The matcher excludes raw elevation values because Earth, Moon, and Mars use
different vertical reference systems.

It uses terrain-shape features:

- Relief
- Median slope
- 90th-percentile slope
- Local elevation variation

The default `core4` feature set uses those four features.

Relief, slope, and local variation are transformed using `log1p` before
scaling. Scaling statistics are fitted only on the Earth catalog.

The matcher supports:

- Euclidean distance
- Mahalanobis distance with covariance whitening

For each Mars or Moon query window, it returns the closest eligible Earth
windows.

## Match interpretation

A lower distance means more similar terrain-shape characteristics.

A rank of 1 means the closest Earth match among the available eligible Earth
windows.

The Earth-only null distribution compares each match distance with distances
between spatially separated Earth windows. It helps identify unusually poor
matches.

This does not prove that a match is a scientifically valid terrain analog.