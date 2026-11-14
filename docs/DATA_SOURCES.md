# Data Sources

## Earth

- GMT product: `earth_relief_01m_p`
- Underlying source: SRTM15+
- Use: Earth candidate-window catalog
- Vertical reference: Earth-specific; not directly comparable with lunar or
  Martian elevation references

## Moon

- GMT product: `moon_relief_01m_p`
- Underlying source: `Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif`
- Provider: USGS Astrogeology / Lunar Reconnaissance Orbiter LOLA
- Elevation reference: lunar reference radius of 1,737.4 km
- Processing radius used: 1,737,400 m
- GMT filtering: 1.4 km full-width Gaussian filter for the 01-minute product

Moon elevations are heights relative to the lunar reference radius, not
distances from the Moon’s center.

## Mars

- GMT product: `mars_relief_01m_p`
- Underlying source: `Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.tif`
- Provider: USGS Astrogeology
- Elevation reference: MOLA areoid
- Processing radius used: 3,396,190 m
- GMT filtering: 2.8 km full-width Gaussian filter for the 01-minute product

Mars elevations are referenced to the MOLA areoid. They are not distances
from Mars’s center.

## How data is obtained

GMT’s remote-data mechanism downloads and caches the required source tiles.
The pipeline requests only the geographic area needed for a window and its
processing buffer.

No provider-side computation is used. All feature calculations occur locally
in Python after the source subset is available.

## Extraction workflow

For each selected Moon or Mars coordinate:

1. Normalize longitude to the range -180 to 180.
2. Define a local azimuthal-equidistant projection centered on the window.
3. Request a buffered source subset from the relevant GMT product.
4. Reproject the source subset into the local 2 km grid.
5. Extract the central 6 × 6 elevation grid.
6. Calculate slope and local elevation variation.
7. Write feature summaries, the 36-cell elevation grid, and a source manifest.

## Sampling limitation

Each 12 km × 12 km window contains only 36 elevation samples. It does not
exhaustively sample every pixel in the window.

Slope is calculated only for the 16 interior cells. Local variation is
calculated only for the 4 central interior values.

The 5 × 5 local-variation kernel has a 10 km footprint and an 8 km center
span. It is not a 150 m roughness measurement.

## Cross-body limitation

Earth, Moon, and Mars use different elevation reference systems. Therefore,
absolute elevation values are not directly comparable across bodies.

The cross-body matcher excludes raw elevation values and uses terrain-shape
features instead. Even those features are affected by source resolution,
filtering, quantization, and resampling.