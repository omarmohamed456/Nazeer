# Nazeer — Geological Data Pipeline

## 1. Overview

This directory contains the geological data-processing pipeline used by the Planetary Analogue Finder project.

The objective of this pipeline is to prepare comparable geological datasets for three planetary bodies:

- **Earth:** Global Lithological Map (GLiM).
- **Moon:** USGS Unified Geologic Map of the Moon, GIS Version 2.
- **Mars:** USGS Geologic Map of Mars, Scientific Investigations Map 3292 (SIM 3292).

The original datasets were produced independently, use different geological classification systems, and have different spatial scales and attribute structures. They cannot be compared directly.

The pipeline processes these datasets into a common spatial grid, calculates the area occupied by each geological unit within each grid cell, assigns simplified geological classifications, and produces datasets suitable for further analysis and cross-planetary comparison.

The resulting data is intended for **regional geological analogue identification**. It is not a detailed geological survey, a mineralogical analysis, or a landing-site safety assessment.

## 2. Data Sources

### 2.1 Earth — Global Lithological Map (GLiM)

**Source:** University of Hamburg  
**Dataset:** Global Lithological Map Database (GLiM)  
**Version:** GLiM v1.0

- [Official GLiM project page](https://www.geo.uni-hamburg.de/en/geologie/forschung/aquatische-geochemie/glim.html)
- [GLiM research publication](https://doi.org/10.1029/2012GC004370)
- [GLiM gridded dataset — PANGAEA](https://doi.org/10.1594/PANGAEA.788537)

GLiM is a global lithological database assembled from existing regional geological maps and supporting geological literature.

The original database contains approximately 1.2 million polygons representing lithological units at Earth's surface. Its classification system has three levels:

- Level 1: 16 general lithological classes.
- Level 2: 12 subclasses providing additional lithological information.
- Level 3: 14 subclasses describing further characteristics.

The database was designed to represent the distribution of rock types globally. It is not a single geological survey conducted at a uniform scale: it combines information from different regional maps and sources.

The average mapping scale reported by the project is approximately 1:3,750,000.

**Why it is used**

GLiM provides a global representation of Earth's surface lithology. It allows geological units on Earth to be grouped into broad categories and compared with geological units identified on the Moon and Mars.

**Important source limitation**

GLiM's source maps were not fully harmonized at their original geological boundaries. Its authors also explain that the mapping of unconsolidated sediments varies between source maps. Therefore, the presence or absence of a sediment class should not automatically be interpreted as proof of the exact material exposed at the surface.

The original database and the gridded 0.5° product are different representations of the same dataset. The processing pipeline uses the GIS data available in the project rather than assuming that it uses the PANGAEA raster product.

### 2.2 Moon — Unified Geologic Map of the Moon

**Source:** USGS Astrogeology Science Center  
**Dataset:** Unified Geologic Map of the Moon, 1:5M, GIS Version 2  
**Publication date:** 2020

- [Official USGS dataset page](https://astrogeology.usgs.gov/search/map/Moon/Geology/Unified_Geologic_Map_of_the_Moon_GIS_v2)
- [Lunar and Planetary Institute repository](https://repository.hou.usra.edu/handle/20.500.11753/1598)

The Unified Geologic Map of the Moon is a globally consistent geological map at a scale of 1:5,000,000.

It was produced by combining six digitally renovated lunar geological maps into a unified product. The dataset contains geological unit polygons, unit contacts, linear features, and geological nomenclature annotations.

The map uses geological interpretations informed by lunar remote-sensing and topographic datasets, including:

- SELENE/Kaguya terrain-camera stereo data.
- Lunar Reconnaissance Orbiter Lunar Orbiter Laser Altimeter (LOLA) data.

The GIS Version 2 release also corrected polygon alignment issues and improved the representation of individual crater units.

**Why it is used**

The dataset provides the geological unit distribution needed to characterize lunar regions, including impact-related materials, volcanic terrains, plains, and highland units.

**Important source limitation**

This is a geological interpretation based on remote sensing, not direct sampling of every mapped unit. Geological unit boundaries and descriptions represent interpretations at the map's scale.

The dataset also contains geological periods and unit descriptions that must be interpreted separately. In the source attributes used by this pipeline, the Moon's geological period and geological unit description required correction before classification.

The pipeline standardizes these fields internally:

- `name`: geological unit description.
- `age`: geological period.

The original unit identifier is retained.

### 2.3 Mars — Geologic Map of Mars (SIM 3292)

**Source:** U.S. Geological Survey  
**Dataset:** Geologic Map of Mars  
**Publication:** Scientific Investigations Map 3292  
**Authors:** Tanaka et al.  
**Publication year:** 2014  
**Map scale:** 1:20,000,000

- [USGS publication page](https://pubs.usgs.gov/publication/sim3292)
- [USGS map and associated materials](https://pubs.usgs.gov/sim/3292/)

SIM 3292 is a global geological map of Mars. It represents the distribution of geological units and landforms across the Martian surface and their development through geological time.

The map was compiled using observations from multiple remote-sensing sources acquired since the Viking missions, including morphological, topographic, spectral, thermophysical, and radar observations.

The publication provides:

- A global geological map.
- A description of geological units.
- Geological mapping documentation.
- A GIS database and associated metadata.

**Why it is used**

SIM 3292 provides the geological unit distribution for Mars. Its unit descriptions and geological attributes are used to identify broad geological characteristics and assign simplified classes.

**Important source limitation**

SIM 3292 is a global geological synthesis at 1:20,000,000 scale. It is much more generalized than a local geological map. Some geological units combine or represent extensive terrains, so their classifications should not be treated as detailed descriptions of every location within the mapped polygon.

---

## 3. Processing Architecture

The geological processing pipeline is divided into four main stages.

```text
                ORIGINAL GEOLOGICAL DATA
                         |
          +--------------+--------------+
          |              |              |
        Earth           Moon           Mars
        GLiM          USGS UGM         SIM 3292
          |              |              |
          +--------------+--------------+
                         |
                         v
                 01_inspect.py
             Inspect source GIS data
             and available attributes
                         |
                         v
                02_tile_overlay.py
             Spatial intersection with
             the common planetary grid
                         |
                         v
                 Tile-unit area CSVs
                         |
                         v
                 03_assemble.py
             Geological unit mapping
             and feature aggregation
                         |
                         v
                tiles_long.csv
                tiles_wide.csv
                tiles.gpkg
                         |
                         v
                  04_validate.py
               Data consistency checks
```

The stages are intentionally separated.

The spatial overlay is the computationally expensive operation. Once its output has been generated, classification and aggregation can be changed without repeating the polygon intersections.

### 3.1 Repository structure

The relevant data branch is organized around the following files:

```text
data/
│
├── config.py
│
├── 01_inspect.py
├── 02_tile_overlay.py
├── 03_assemble.py
├── 04_validate.py
│
├── mappings/
│   ├── earth_units.csv
│   ├── moon_units.csv
│   └── mars_units.csv
│
└── out/
    ├── earth_tile_unit_area.csv
    ├── moon_tile_unit_area.csv
    ├── mars_tile_unit_area.csv
    │
    ├── earth_tiles.csv
    ├── moon_tiles.csv
    ├── mars_tiles.csv
    │
    ├── tiles_long.csv
    ├── tiles_wide.csv
    └── tiles.gpkg
```

The original source datasets and other large intermediate files may be stored separately and excluded from version control.

The exact directory names depend on the local configuration. `config.py` is the central place to inspect the configured input paths, output paths, grid parameters, and body-specific settings.

---

## 4. Common Spatial Grid

All three geological datasets are summarized using a shared global grid.

### 4.1 Grid definition

The current implementation uses a regular 10° latitude-by-longitude grid.

The grid contains:

- 18 latitude bands.
- 36 longitude columns per band.
- 648 tiles in total.

Each tile is identified by a unique `tile_id`.

The grid is shared across Earth, Moon, and Mars so that the resulting datasets have corresponding spatial indices.

### 4.2 Why use a common grid?

The source datasets have different polygon boundaries, mapping scales, and geological unit definitions.

Directly comparing individual source polygons would be difficult because:

- A geological unit on one body may cover an area much larger than a unit on another.
- The boundaries do not correspond between bodies.
- The number of polygons differs significantly.
- The source maps use different classification systems.

The common grid solves the spatial correspondence problem by summarizing each body's geology within the same set of tile identifiers.

Instead of comparing individual polygons, the pipeline compares the distribution of geological units within each tile.

### 4.3 Tile dimensions and area

Although the grid uses the same angular dimensions on all three bodies, its tiles do not represent equal physical areas.

A 10° by 10° tile has a different physical size depending on:

- The planetary body's radius.
- Its latitude.
- The longitude width of the tile.

Longitude distances become smaller toward the poles.

Consequently, a 10° tile should not be interpreted as a fixed-size physical region or as an equivalent rover-scale site.

The current grid is intended for broad regional comparisons.

### 4.4 Area calculations and projection

The overlay stage uses a body-specific spherical radius and a Cylindrical Equal Area (CEA) projection for area calculations.

The general processing sequence is:

1. Read source geological features.
2. Convert source geometries into the coordinate representation used by the overlay.
3. Transform geometries into the body-specific equal-area coordinate system.
4. Intersect geological polygons with the grid tiles.
5. Calculate the intersection area.
6. Aggregate the area by tile and geological unit.

The area is recorded in square kilometres.

Using a body-specific radius is important because Earth, Moon, and Mars do not have the same dimensions.

The equal-area projection is used to make the area calculations more appropriate for comparing polygon coverage. It does not make the underlying geological maps equally accurate or equally detailed.

---

## 5. Script Documentation

### 5.1 `config.py`

This file centralizes the configuration used by the processing scripts.

It is responsible for the shared settings required by the pipeline, such as:

- Input dataset locations.
- Output directory locations.
- Mapping file locations.
- Planetary body configuration.
- Grid parameters.
- Body-specific spatial parameters, including radii.
- Source-specific field configuration where defined.

Keeping these settings in one place avoids duplicating paths and spatial parameters across scripts.

If a source dataset is moved, its configured path should be updated here rather than manually changing every processing script.

### 5.2 `01_inspect.py` — Source inspection

The first stage inspects the source GIS datasets before spatial processing.

Its purpose is to understand the structure of each input dataset and identify the attributes required by the following stages.

Typical inspection targets include:

- Available GIS layers.
- Feature counts.
- Coordinate reference systems.
- Geometry types.
- Attribute names.
- Sample geological unit identifiers.
- Geological descriptions.
- Geological age or period fields.
- Missing or empty attribute values.

This stage is important because the three datasets do not use a common schema.

For example, the Moon dataset contains unit identifiers, descriptions, and geological periods. Mars has its own geological unit attributes, while GLiM uses lithological classification codes.

The inspection stage helps identify which fields should be retained and how each source should be interpreted.

**Output:** Inspection information used to configure and understand the input datasets.

This script does not perform the final geological classification or generate the final comparison dataset.

### 5.3 `02_tile_overlay.py` — Spatial overlay and area calculation

This is the main spatial-processing stage.

It reads the source geological polygons and calculates how much of each grid tile is occupied by each geological unit.

Because the source datasets can contain large numbers of features, the script processes the data in chunks rather than requiring every feature to be loaded and intersected at once.

The general procedure is:

1. Load the common grid.
2. Load the geological source data for a body.
3. Convert the source geometries into the coordinate system required for area calculations.
4. Process source features in manageable chunks.
5. Intersect the features with the grid tiles.
6. Calculate the intersection area in square kilometres.
7. Aggregate areas by `tile_id` and source geological unit.
8. Write the aggregated results to CSV.

The resulting files are:

```text
out/
├── earth_tile_unit_area.csv
├── moon_tile_unit_area.csv
└── mars_tile_unit_area.csv
```

The script also produces tile-level intermediate summaries:

```text
out/
├── earth_tiles.csv
├── moon_tiles.csv
└── mars_tiles.csv
```

These are intermediate products used by the assembly stage.

#### Why the overlay is performed separately from classification

Spatial intersection is relatively expensive.

The overlay results contain the measured areas of the original geological units. These measurements do not depend on how a unit is later classified.

This separation allows the classification rules to be modified without repeating the spatial overlay.

For example, changing a Moon unit from `plains` to `impact` only requires regenerating the mapping and assembled outputs. It does not require recalculating the polygon intersections.

**Important:** Changes to the grid definition, source geometries, spatial transformations, or area calculation method require rerunning this stage.

### 5.4 `03_assemble.py` — Classification and dataset assembly

This stage converts the spatial overlay outputs into the final geological feature datasets.

It performs three main operations:

1. Creates or loads geological unit mappings.
2. Joins those mappings to the tile-unit area measurements.
3. Aggregates the results into tile-level geological features.

#### A. Geological unit mappings

The overlay stage identifies source geological units but does not decide what each unit means for cross-planetary comparison.

That interpretation is handled by mapping files.

```text
mappings/
├── earth_units.csv
├── moon_units.csv
└── mars_units.csv
```

Each mapping file associates an original source unit with a simplified geological classification.

The mapping process retains the original source identifiers and descriptions so that the simplified classification can be traced back to the source data.

The current mapping structure includes fields such as:

| Field | Description |
|---|---|
| `unit` | Original geological unit identifier |
| `name` | Geological unit description |
| `age` | Geological age or period information from the source |
| `process_class` | Simplified geological process classification |
| `terrain_group` | Broader terrain grouping |
| `age_label` | Categorical geological age label, when available |
| `age_max_Ga` | Upper numerical age bound in billions of years, when available |
| `age_min_Ga` | Lower numerical age bound in billions of years, when available |
| `needs_review` | Indicates that the unit mapping needs further inspection |

Not every source provides all types of age information. Missing numerical values are therefore expected.

The mapping files are particularly important because they contain the interpretive decisions that connect three different geological classification systems.

#### B. Earth classification

Earth uses GLiM's lithological classes.

The original GLiM classification distinguishes lithologies such as:

- Unconsolidated sediments.
- Siliciclastic sedimentary rocks.
- Carbonate sedimentary rocks.
- Mixed sedimentary rocks.
- Evaporites.
- Pyroclastics.
- Acid, intermediate, and basic volcanic rocks.
- Acid, intermediate, and basic plutonic rocks.
- Metamorphic rocks.
- Ice and glaciers.
- Water bodies.
- No data.

The pipeline groups these source lithologies into broader classes for the project.

The resulting Earth process classes include:

- `sedimentary`
- `volcanic`
- `plutonic`
- `metamorphic`
- `ice`
- `water`
- `no_data`

These are simplified categories, not replacements for the original GLiM classification.

The original source unit information is retained in the mapping table.

#### C. Moon classification

The Moon mapping uses the original unit identifiers and geological descriptions from the Unified Geologic Map.

The current simplified classification includes:

- `impact`
- `volcanic`
- `plains`
- `highlands`
- `unclassified`

These categories are assigned using the unit descriptions and geological context.

The Moon dataset also contains geological period labels, including:

- Copernican.
- Eratosthenian.
- Imbrian.
- Nectarian.
- Pre-Nectarian.

These labels are retained as categorical age information.

They should not be confused with numerical age measurements. A period label does not provide a precise numerical formation age for an individual geological unit.

#### D. Mars classification

Mars unit descriptions and identifiers are interpreted using the geological information provided by SIM 3292.

The pipeline uses a simplified process classification rather than attempting to preserve every distinction in the original Martian geological map as a separate comparison class.

The current mapping includes broad categories such as:

- `impact`
- `volcanic`
- `ice`
- `surficial_unconsolidated`
- `undivided_terrain`

The exact assignment depends on the original geological unit attributes and the mapping rules in the script.

Some units are inherently difficult to reduce to one broad process category. The mapping therefore retains review flags and the original unit descriptions.

#### E. Area aggregation

Once the mapping is available, the script joins it to the tile-unit area data.

For each tile, the pipeline can calculate:

- Total mapped geological area.
- Area occupied by each geological unit.
- Area occupied by each simplified geological class.
- Fraction of the entire tile occupied by each class.
- Fraction of the mapped area occupied by each class.
- Dominant geological unit.
- Dominant geological class.
- Available geological age summaries.

Two area fractions are especially important.

**Fraction of tile area**

\[
f_{\text{tile}} =
\frac{A_{\text{class}}}{A_{\text{tile}}}
\]

This expresses the area of a geological class relative to the entire grid tile.

**Fraction of mapped area**

\[
f_{\text{mapped}} =
\frac{A_{\text{class}}}{A_{\text{mapped}}}
\]

This expresses the class area relative to the geological area successfully mapped within that tile.

These two values answer different questions.

The first describes how much of the tile is represented by a particular class. The second describes the composition of the mapped geology, independently of the amount of mapped coverage.

This distinction matters when comparing bodies or tiles with different geological coverage.

#### F. Mapping regeneration

The script supports regenerating mappings when classification rules change.

Mars and Moon mappings are regenerated by the current workflow, while the existing Earth mapping is preserved and missing entries can be added.

This behavior is important when editing the classification logic: an old mapping file should not silently prevent updated classification rules from being applied.

The final outputs are:

```text
out/
├── tiles_long.csv
├── tiles_wide.csv
└── tiles.gpkg
```

### 5.5 `04_validate.py` — Data validation

The validation stage checks the consistency of the assembled geological datasets.

It is intended to catch structural and numerical errors before the data is used by the similarity engine.

Validation includes checks such as:

- Mapping coverage.
- Unclassified or missing geological units.
- Tile coverage.
- Class fraction consistency.
- Mapped-area fraction consistency.
- Grid consistency between bodies.
- Unexpected area values.

An important check is whether the geological class fractions sum to the expected value.

For mapped-area fractions:

\[
\sum_{i=1}^{n} f_{\text{mapped},i} = 1
\]

This should hold for a tile with mapped geological area, subject to the aggregation and classification rules.

The pipeline also checks the relationship between class area and total tile area.

A successful validation does not prove that the geological interpretations are scientifically correct. It verifies that the calculations and data transformations are internally consistent.

---

## 6. Intermediate Data Formats

### 6.1 `*_tile_unit_area.csv`

These files are the direct output of the spatial overlay stage.

There is one row for each tile and source geological unit combination that has an intersection area.

The important fields are:

| Field | Meaning |
|---|---|
| `tile_id` | Grid tile identifier |
| `unit` | Original source geological unit identifier |
| `name` | Source geological unit name or description |
| `age` | Source geological age or period attribute |
| `area_km2` | Area of the unit inside the tile, in km² |

The exact contents depend on the source dataset and its available attributes.

**Example structure:**

| tile_id | unit | name | age | area_km2 |
|---|---|---|---|---:|
| r05c12 | Unit_A | Example unit | Example period | 125000 |
| r05c12 | Unit_B | Another unit | Example period | 83000 |
| r05c13 | Unit_A | Example unit | Example period | 91000 |

The values above are illustrative.

This format is useful for tracing the final geological fractions back to individual source units.

### 6.2 Mapping CSV files

The mapping files contain the interpretation of each source geological unit.

They are separate from the spatial overlay results so that classification decisions can be reviewed and modified independently.

A mapping row should retain the original unit identifier and descriptive information alongside its simplified class.

The `needs_review` field allows uncertain or heuristic classifications to be identified without removing them from the working dataset.

### 6.3 `tiles_long.csv`

This is the normalized, long-format dataset.

It retains the relationship between individual tiles and their geological units, together with their area and classification information.

It is useful for:

- Inspecting the composition of individual tiles.
- Filtering specific geological classes.
- Tracing a class fraction to its contributing source units.
- Producing new summaries without repeating the spatial overlay.

The last successful assembly produced 19,198 rows.

### 6.4 `tiles_wide.csv`

This is the main tabular dataset intended for downstream analysis.

It contains one row per grid tile, with separate columns for the geological features of Earth, Moon, and Mars.

The last successful assembly produced:

- 648 rows.
- 76 columns.

The dataset includes tile identifiers and body-specific geological summaries.

Its columns include features such as:

- Mapped-area coverage.
- Geological class fractions.
- Mapped-area-normalized class fractions.
- Dominant geological units.
- Dominant geological classes.
- Available age summaries.

The class fraction columns distinguish between the fraction of the full tile and the fraction of the mapped geological area.

The exact column names are generated by the assembly script and should be inspected from the current output rather than assumed to remain unchanged between versions.

### 6.5 `tiles.gpkg`

This is the spatial output.

It stores the grid geometry together with the assembled tile attributes in a GeoPackage.

It can be opened using GIS software such as QGIS and is useful for:

- Visualizing the grid.
- Inspecting geological class distributions.
- Checking tile coverage.
- Joining the generated features to other spatial datasets.
- Exporting the data for mapping applications.

The GeoPackage is the spatial counterpart of the wide CSV dataset.

---

## 7. Running the Pipeline

Run the scripts in the following order.

### Step 1 — Inspect the source datasets

```powershell
python .\01_inspect.py
```

Review the source layers, coordinate reference systems, attributes, and unit descriptions.

### Step 2 — Perform the spatial overlay

```powershell
python .\02_tile_overlay.py
```

This stage generates the per-body tile-unit area files.

It is the most computationally expensive stage.

**It does not need to be rerun when only classification rules or mapping files change.**

Rerun it when the source GIS data, spatial transformation, grid, or area calculation method changes.

### Step 3 — Assemble the geological features

```powershell
python .\03_assemble.py
```

This stage generates or updates the mapping files and creates:

```text
out/tiles_long.csv
out/tiles_wide.csv
out/tiles.gpkg
```

It should be rerun after changes to geological classification rules or mapping files.

### Step 4 — Validate the results

```powershell
python .\04_validate.py
```

Review the classification, coverage, and fraction checks.

Do not treat successful numerical validation as proof of geological accuracy.

---

## 8. Scientific Interpretation and Limitations

The output is a simplified representation of geological distributions across three planetary bodies. Several limitations should be considered when using it.

### 8.1 Different source maps and mapping scales

The source maps were created for different scientific purposes and at different scales.

| Body | Source | Map scale |
|---|---|---:|
| Earth | GLiM | Approximately 1:3,750,000 average |
| Moon | Unified Geologic Map of the Moon | 1:5,000,000 |
| Mars | USGS SIM 3292 | 1:20,000,000 |

The maps therefore do not provide equivalent spatial detail.

A geological unit mapped on Mars may represent a much larger generalized region than a unit mapped on the Moon or Earth.

The grid aggregation makes the data spatially comparable at a broad regional level, but it does not eliminate differences in source-map resolution or geological interpretation.

### 8.2 Geological classifications are not equivalent between bodies

Earth, Moon, and Mars do not share a single geological classification system.

GLiM classifies Earth according to lithological properties. The lunar and Martian maps use planetary geological units, stratigraphic relationships, landforms, and geological interpretations.

Consequently, the simplified classes are a practical harmonization layer.

For example:

- An Earth volcanic unit and a lunar mare basalt unit may share a broad volcanic classification.
- A lunar crater-related unit and a Martian impact-related unit may share a broad impact classification.
- A lunar highland unit and an Earth plutonic or metamorphic unit should not be considered geologically identical simply because they are assigned to a broad crystalline or highland-related category.

The simplified categories indicate broad resemblance, not identical mineralogy, composition, origin, or geological history.

The original geological identifiers and descriptions must remain available for interpretation.

### 8.3 Heuristic classification

Some source units cannot be mapped cleanly into a single simplified category.

A unit description may contain several geological processes or represent a complex geological history.

The mapping rules therefore use simplified interpretations based on source descriptions and attributes.

The `needs_review` flag is intended to identify units where the assignment may require further inspection.

These classifications should be treated as a first-pass analytical grouping rather than a definitive geological interpretation.

### 8.4 Geological age is not directly comparable

The source datasets do not provide age information in a consistent format.

The Moon dataset uses geological periods such as Imbrian and Nectarian. Mars provides geological unit and age information in its own stratigraphic framework. GLiM is primarily a lithological dataset rather than a common planetary chronology.

The pipeline retains available age information, but missing numerical ages should not be interpreted as zero or as evidence that a unit has no geological age.

Comparisons between age fields require additional work to establish a consistent chronological interpretation.

### 8.5 Coverage and unmapped areas

A tile's mapped geological area may not equal its total area.

The pipeline therefore retains both tile-relative and mapped-area-relative class fractions.

A low mapped fraction means that only part of the tile is represented by the polygons contributing to the calculation.

It should not automatically be interpreted as a single geological type, a completely unclassified region, or an area with no geology.

Coverage must be considered when comparing two tiles.

### 8.6 Area and geometry limitations

The area calculations use body-specific spherical parameters and an equal-area projection.

This is an approximation of planetary geometry.

Potential sources of error include:

- Source geometry inaccuracies.
- Differences in coordinate conventions.
- Polygon boundary generalization.
- Projection and transformation errors.
- Overlaps or gaps in the original geometries.
- Numerical effects during chunked intersections.

Earth's source geometry may also contain overlaps or other inconsistencies that cause summed polygon areas to exceed a tile's nominal area.

The pipeline's normalized mapped-area fractions are useful for comparing class composition, but they do not automatically resolve every source geometry problem.

### 8.7 Grid resolution is regional, not local

The current grid uses 10° by 10° angular tiles.

These represent very large geographical regions.

They are useful for identifying broad geological similarities but are not suitable for evaluating a specific rover traverse, landing ellipse, or local geological exposure.

A future implementation could use smaller, physically defined tiles or local regions after the broad global comparison is working.

### 8.8 Geological similarity is not landing-site suitability

The geological data pipeline does not evaluate all the conditions required to select a landing site or establish a lunar or Martian base.

It does not independently establish:

- Surface slope and local roughness.
- Boulder density.
- Regolith thickness.
- Soil bearing strength.
- Subsurface structure.
- Radiation exposure.
- Thermal conditions.
- Local illumination and shadowing.
- Communications availability.
- Landing hazards.

A geological analogue is not necessarily an operationally suitable location.

The current output should be interpreted as a way to identify regions with potentially comparable geological characteristics, not as a recommendation to land or construct infrastructure there.

---

## 9. Recommended Use of the Outputs

The generated datasets are intended to serve as inputs to the next stage of the Planetary Analogue Finder.

A typical workflow is:

1. Select a Moon or Mars tile.
2. Retrieve its geological feature distribution.
3. Compare it with the corresponding feature distributions of Earth tiles.
4. Rank Earth tiles according to geological similarity.
5. Display the best candidates and their geological characteristics.
6. Allow users to inspect the original unit descriptions and mapping assumptions.

The geological class fractions are especially useful because they represent the relative composition of a tile rather than relying only on its dominant geological unit.

A tile containing 60% volcanic terrain and 40% impact-related material should remain distinguishable from a tile containing 100% volcanic terrain, even if both have volcanic as their dominant class.

The distinction between tile coverage and mapped-area composition should also be retained in the similarity calculations.

The scoring method should account for missing coverage rather than treating missing data as a geological class.

---

## 10. Reproducibility and Data Management

The original source datasets, intermediate overlay files, mapping tables, and final outputs should be kept distinguishable.

Recommended data-management practices:

- Preserve original source datasets without modifying them.
- Keep the mapping CSVs under version control.
- Document changes to classification rules.
- Preserve the overlay outputs so that classification changes do not require expensive spatial processing.
- Regenerate the final assembled datasets after mapping changes.
- Record the source version and processing date when generating a new release.
- Validate the generated files before using them in the application.

Large source datasets and intermediate files may be excluded from Git if their size makes repository storage impractical.

The repository should retain enough configuration and documentation for another user to understand where the input datasets belong and how to regenerate the outputs.

---

## 11. Data Sources and References

### Earth

Hartmann, J., and Moosdorf, N. (2012). *The new global lithological map database GLiM: A representation of rock properties at the Earth surface.* Geochemistry, Geophysics, Geosystems, 13, Q12004.

https://doi.org/10.1029/2012GC004370

Hartmann, J., and Moosdorf, N. (2012). *Global Lithological Map Database v1.0 (gridded to 0.5° spatial resolution).* PANGAEA.

https://doi.org/10.1594/PANGAEA.788537

### Moon

Fortezzo, C. M., Spudis, P. D., and Harrel, S. L. (2020). *Unified Geologic Map of the Moon, 1:5M.*

USGS Astrogeology Science Center, GIS Version 2.

https://astrogeology.usgs.gov/search/map/Moon/Geology/Unified_Geologic_Map_of_the_Moon_GIS_v2

### Mars

Tanaka, K. L., Skinner, J. A., Jr., Dohm, J. M., Irwin, R. P., III, Kolb, E. J., Fortezzo, C. M., Platz, T., Michael, G. G., and Hare, T. M. (2014). *Geologic Map of Mars.* U.S. Geological Survey Scientific Investigations Map 3292.

https://doi.org/10.3133/sim3292

---

## 12. Current Pipeline Status

The current implementation has completed the geological overlay, classification, and assembly stages for all three bodies.

The latest successful assembly produced:

| Output | Result |
|---|---:|
| Grid tiles | 648 |
| Long-format rows | 19,198 |
| Wide-format rows | 648 |
| Wide-format columns | 76 |
| Mars unclassified mapped area | 0% |
| Moon unclassified mapped area | 0% |
| Earth unclassified mapped area | 0% |

The assembly script also reported zero maximum difference in its class-fraction and mapped-class-fraction consistency checks for all three bodies.

These results confirm that the current classification and aggregation pipeline is operating consistently. They do not establish that every individual geological unit has been interpreted correctly.

The next stage is to use the assembled geological features for cross-planetary analogue comparison.