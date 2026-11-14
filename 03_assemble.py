
"""
STEP 3 - Harmonise geological units and assemble the final tile dataset.

Reads existing STEP 2 outputs:
    out/<body>_tile_unit_area.csv
    out/<body>_tiles.csv

Writes:
    out/tiles_long.csv
    out/tiles_wide.csv
    out/tiles.gpkg

Mapping behavior:
    Mars: regenerated automatically on every run.
    Moon: regenerated automatically on every run.
    Earth: existing mapping CSV is preserved; missing units are added.

No need to rerun STEP 2.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import shapely

from config import BODIES, OUT, MAPDIR


NAN = np.nan

# ============================================================
# MARS
# ============================================================

MARS_RE = re.compile(r"^([eml]?)([NHA]{1,2})([abhilptv])([cdefmou]?)$")

# (oldest possible Ga, youngest possible Ga)
MARS_EPOCH = {
    "eN": (NAN, 3.94),
    "mN": (3.94, 3.83),
    "lN": (3.83, 3.71),
    "eH": (3.71, 3.61),
    "lH": (3.61, 3.37),
    "eA": (3.37, 1.23),
    "mA": (1.23, 0.328),
    "lA": (0.328, 0.0),
}

MARS_PERIOD = {
    "N": (NAN, 3.71),
    "H": (3.71, 3.37),
    "A": (3.37, 0.0),
}

MARS_GROUP = {
    "a": "apron",
    "b": "basin",
    "h": "highland",
    "i": "impact",
    "l": "lowland",
    "p": "polar",
    "t": "transition",
    "v": "volcanic",
}


def mars_row(unit):
    unit = str(unit).strip()
    m = MARS_RE.match(unit)

    if not m:
        return dict(
            process_class="unparsed",
            terrain_group="",
            age_label="",
            age_max_Ga=NAN,
            age_min_Ga=NAN,
            needs_review=True,
        )

    ep, per, grp, sub = m.groups()

    if len(per) == 1:
        mx, mn = MARS_EPOCH[ep + per] if ep else MARS_PERIOD[per]
    else:
        mx = MARS_PERIOD[per[1]][0]
        mn = MARS_PERIOD[per[0]][1]

    if grp == "i":
        pc = "impact"
    elif grp == "v":
        pc = "volcanic"
    elif grp == "p" and sub == "c":
        pc = "ice"
    elif grp == "p" and sub == "d":
        pc = "surficial_unconsolidated"
    else:
        pc = "undivided_terrain"

    return dict(
        process_class=pc,
        terrain_group=MARS_GROUP[grp],
        age_label=ep + per,
        age_max_Ga=mx,
        age_min_Ga=mn,
        needs_review=False,
    )


# ============================================================
# MOON
# ============================================================

def moon_row(unit, name, age):
    """
    Simplified keyword-based classification.

    These categories are intended for an initial comparison,
    not as a definitive geological interpretation.

    Original unit codes, names, and age labels are preserved.
    Numerical lunar ages are deliberately not assigned here.
    """

    n = str(name).lower()
    age = str(age).strip()

    # Impact-related terrain and deposits
    impact_keywords = [
        "crater",
        "basin",
        "secondary",
        "orientale",
        "imbrium",
        "imbrium",
        "fra mauro",
        "apenninus",
        "alpes formation",
        "nectaris",
        "rook formation",
    ]

    # Volcanic terrain
    volcanic_keywords = [
        "mare",
        "volcan",
        "mare dome",
        "dark mantling",
    ]

    # Plains and plateaus
    plains_keywords = [
        "plains",
        "plateau",
    ]

    # Highland terrain
    highland_keywords = [
        "terra",
        "highland",
        "massif",
        "grooved terrain",
    ]

    if any(k in n for k in impact_keywords):
        pc = "impact"
        terrain = "impact_terrain"

    elif any(k in n for k in volcanic_keywords):
        pc = "volcanic"
        terrain = "volcanic_terrain"

    elif any(k in n for k in plains_keywords):
        pc = "plains"
        terrain = "plains"

    elif any(k in n for k in highland_keywords):
        pc = "highlands"
        terrain = "highlands"

    else:
        pc = "unclassified"
        terrain = "other"

    # Keep the original period label as a categorical feature.
    age_label = age

    return dict(
        process_class=pc,
        terrain_group=terrain,
        age_label=age_label,
        age_max_Ga=NAN,
        age_min_Ga=NAN,
        needs_review=(pc == "unclassified"),
    )


# ============================================================
# EARTH - GLiM
# ============================================================

GLIM = {
    "su": "surficial_unconsolidated",
    "ss": "sedimentary",
    "sc": "sedimentary",
    "sm": "sedimentary",
    "ev": "sedimentary",

    "vb": "volcanic",
    "va": "volcanic",
    "vi": "volcanic",
    "py": "volcanic",

    "pb": "plutonic",
    "pi": "plutonic",
    "pa": "plutonic",

    "mt": "metamorphic",

    "ig": "ice",
    "wb": "water",
    "nd": "no_data",
}


def earth_row(unit, name, age):
    pc = GLIM.get(str(unit).lower(), "unmapped")

    return dict(
        process_class=pc,
        terrain_group="",
        age_label="",
        age_max_Ga=NAN,
        age_min_Ga=NAN,
        needs_review=(pc == "unmapped"),
    )


# ============================================================
# MAPPING TABLES
# ============================================================

KEYS = ["unit", "name", "age"]


def build_mapping(body, units):
    rows = []

    for _, u in units.iterrows():
        unit = str(u["unit"])
        name = str(u.get("name", ""))
        age = str(u.get("age", ""))

        if body == "mars":
            result = mars_row(unit)

        elif body == "moon":
            result = moon_row(unit, name, age)

        else:
            result = earth_row(unit, name, age)

        rows.append({
            "unit": unit,
            "name": name,
            "age": age,
            **result,
        })

    return pd.DataFrame(rows)


def load_mapping(body, units):
    """
    Mars and Moon are regenerated every run.
    Earth retains existing reviewed mappings.
    Missing Earth units are automatically added.
    """

    MAPDIR.mkdir(parents=True, exist_ok=True)
    path = MAPDIR / f"{body}_units.csv"

    if body in ("mars", "moon"):
        mapping = build_mapping(body, units)
        mapping.to_csv(path, index=False)
        print(f"  {body}: regenerated mapping -> {path}")

    elif path.exists():
        mapping = pd.read_csv(
            path,
            keep_default_na=False,
            dtype={"unit": str, "name": str, "age": str},
        )

        for c in KEYS:
            mapping[c] = mapping[c].fillna("").astype(str).str.strip()
        # Moon source fields are reversed in the current STEP 2 output.
        # The geological description is in age, and the period is in name.
        if body == "moon":
            tua[["name", "age"]] = tua[["age", "name"]].to_numpy()

        if mapping.duplicated(KEYS).any():
            raise ValueError(
                f"{path} contains duplicate unit/name/age combinations."
            )

        missing = units.merge(
            mapping[KEYS],
            on=KEYS,
            how="left",
            indicator=True,
        )

        missing = missing.loc[missing["_merge"] == "left_only", KEYS]

        if len(missing):
            additions = build_mapping("earth", missing)
            mapping = pd.concat(
                [mapping, additions],
                ignore_index=True,
            )
            mapping.to_csv(path, index=False)
            print(f"  earth: added {len(missing)} new mapping rows")

    else:
        mapping = build_mapping("earth", units)
        mapping.to_csv(path, index=False)
        print(f"  earth: created mapping -> {path}")

    return mapping


# ============================================================
# LOAD BODY DATA
# ============================================================

def load_body(body):
    tua = pd.read_csv(
        OUT / f"{body}_tile_unit_area.csv",
        keep_default_na=False,
        dtype={"unit": str, "name": str, "age": str},
    )

    for c in ("name", "age"):
        if c not in tua.columns:
            tua[c] = ""

    for c in KEYS:
        tua[c] = tua[c].fillna("").astype(str).str.strip()
        
    if body == "moon":
        # Correct the reversed Moon source fields:
        # name currently contains the geological period,
        # age currently contains the geological unit description.
        tua[["name", "age"]] = tua[["age", "name"]].to_numpy()

    tiles = pd.read_csv(OUT / f"{body}_tiles.csv")

    units = tua[KEYS].drop_duplicates().reset_index(drop=True)

    mapping = load_mapping(body, units)

    if mapping.duplicated(KEYS).any():
        raise ValueError(f"{body}: duplicate mapping keys detected.")

    df = tua.merge(
        mapping,
        on=KEYS,
        how="left",
        validate="many_to_one",
    )

    df["process_class"] = df["process_class"].fillna("unmapped")
    df["terrain_group"] = df["terrain_group"].fillna("")
    df["age_label"] = df["age_label"].fillna("")

    df["age_max_Ga"] = pd.to_numeric(
        df["age_max_Ga"], errors="coerce"
    )
    df["age_min_Ga"] = pd.to_numeric(
        df["age_min_Ga"], errors="coerce"
    )

    df = df.merge(tiles, on="tile_id", validate="many_to_one")

    # Area as a fraction of the complete tile.
    df["frac_of_tile"] = (
        df["area_km2"] / df["tile_area_km2"]
    )

    # Area as a fraction of all mapped geological area in that tile.
    mapped_area = df.groupby("tile_id")["area_km2"].transform("sum")

    df["frac_of_mapped_area"] = np.where(
        mapped_area > 0,
        df["area_km2"] / mapped_area,
        0.0,
    )

    df.insert(0, "body", body)

    bad = df.loc[
        df["process_class"].isin(
            ["unparsed", "unmapped", "unclassified"]
        ),
        "area_km2",
    ].sum()

    total = df["area_km2"].sum()

    bad_pct = 100 * bad / total if total > 0 else 0

    print(
        f"  {body}: {bad_pct:.2f}% of mapped area has "
        "unparsed/unmapped/unclassified classes"
    )

    return df, tiles


# ============================================================
# SUMMARISE ONE BODY
# ============================================================

def summarise(body, df, tiles):
    ta = tiles.set_index("tile_id")["tile_area_km2"]

    out = pd.DataFrame(index=tiles["tile_id"])

    out[f"{body}_tile_area_km2"] = ta

    mapped = df.groupby("tile_id")["area_km2"].sum()

    out[f"{body}_mapped_frac"] = mapped.div(ta)

    

    # --------------------------------------------------------
    # Geological class fractions
    # --------------------------------------------------------

    cls = df.pivot_table(
        index="tile_id",
        columns="process_class",
        values="area_km2",
        aggfunc="sum",
        fill_value=0,
    )

    # Fraction of entire tile.
    cls_tile = cls.div(ta, axis=0)
    cls_tile.columns = [
        f"{body}_frac_{c}" for c in cls_tile.columns
    ]

    # Fraction of mapped geological area.
    cls_mapped = cls.div(mapped, axis=0).fillna(0)
    cls_mapped.columns = [
        f"{body}_mapped_class_frac_{c}"
        for c in cls_mapped.columns
    ]

    out = out.join(cls_tile)
    out = out.join(cls_mapped)

    # --------------------------------------------------------
    # Dominant geological unit
    # --------------------------------------------------------

    dominant_idx = df.groupby("tile_id")["area_km2"].idxmax()

    dominant = df.loc[dominant_idx].set_index("tile_id")

    out[f"{body}_dominant_unit"] = dominant["unit"]
    out[f"{body}_dominant_class"] = dominant["process_class"]

    # --------------------------------------------------------
    # Categorical geological age distribution
    # --------------------------------------------------------

    age_data = df[
        df["age_label"].astype(str).str.strip().ne("")
    ].copy()
    

    if len(age_data):
        age_area = age_data.pivot_table(
            index="tile_id",
            columns="age_label",
            values="area_km2",
            aggfunc="sum",
            fill_value=0,
        )

        known_age_area = age_data.groupby("tile_id")[
            "area_km2"
        ].sum()

        age_frac = age_area.div(known_age_area, axis=0).fillna(0)

        for label in age_frac.columns:
            safe_label = re.sub(
                r"[^a-zA-Z0-9]+", "_", str(label)
            ).strip("_").lower()

            out[f"{body}_age_frac_{safe_label}"] = age_frac[label]

    # --------------------------------------------------------
    # Numerical age summaries (currently useful for Mars)
    # --------------------------------------------------------

    known_age = df[
        df["age_min_Ga"].notna()
        & df["age_max_Ga"].notna()
    ].copy()

    if len(known_age):
        groups = known_age.groupby("tile_id")

        def weighted_mean(group, column):
            valid = group[column].notna()

            if not valid.any():
                return np.nan

            return np.average(
                group.loc[valid, column],
                weights=group.loc[valid, "area_km2"],
            )

        out[f"{body}_mean_age_min_Ga"] = groups.apply(
            lambda g: weighted_mean(g, "age_min_Ga")
        )

        out[f"{body}_mean_age_max_Ga"] = groups.apply(
            lambda g: weighted_mean(g, "age_max_Ga")
        )

        # Denominator is only area with known numerical ages.
        known_area = groups["area_km2"].sum()

        surely_old = known_age[
            known_age["age_min_Ga"] >= 3.5
        ].groupby("tile_id")["area_km2"].sum()

        surely_young = known_age[
            known_age["age_max_Ga"] <= 1.0
        ].groupby("tile_id")["area_km2"].sum()

        out[f"{body}_frac_surely_old_gt3p5Ga"] = (
            surely_old / known_area
        )

        out[f"{body}_frac_surely_young_lt1Ga"] = (
            surely_young / known_area
        )

    # Fill missing fractions with zero.
    fraction_cols = [
        c for c in out.columns
        if "_frac_" in c or c.endswith("_mapped_frac")
    ]

    out[fraction_cols] = out[fraction_cols].fillna(0)

    # --------------------------------------------------------
    # Consistency checks
    # --------------------------------------------------------

    tile_fraction_cols = [
        c for c in cls_tile.columns
    ]

    mapped_fraction_cols = [
        c for c in cls_mapped.columns
    ]

    if tile_fraction_cols:
        class_sum = out[tile_fraction_cols].sum(axis=1)
        expected = out[f"{body}_mapped_frac"]

        difference = (class_sum - expected).abs()

        print(
            f"  {body}: class/tile fraction maximum difference = "
            f"{difference.max():.8f}"
        )

    if mapped_fraction_cols:
        class_sum = out[mapped_fraction_cols].sum(axis=1)

        # Align mapped coverage with the class fraction index.
        valid = mapped.reindex(class_sum.index).fillna(0) > 0

        difference = (class_sum.loc[valid] - 1.0).abs()

        if len(difference):
            print(
                f"  {body}: mapped class fraction maximum difference = "
                f"{difference.max():.8f}"
            )
    return out


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    OUT.mkdir(exist_ok=True)
    MAPDIR.mkdir(exist_ok=True)

    longs = []
    wides = []
    grid = None

    for body in BODIES:

        area_file = OUT / f"{body}_tile_unit_area.csv"

        if not area_file.exists():
            print(f"Skipping {body}: run STEP 2 first.")
            continue

        print(f"\n========== {body.upper()} ==========")

        df, tiles = load_body(body)

        longs.append(df)
        wides.append(summarise(body, df, tiles))

        if grid is None:
            grid = tiles[
                [
                    "tile_id",
                    "lat_min",
                    "lat_max",
                    "lon_min",
                    "lon_max",
                ]
            ].copy()

        else:
            if set(grid["tile_id"]) != set(tiles["tile_id"]):
                raise ValueError(
                    f"{body}: tile IDs do not match the other bodies."
                )

    if not longs:
        raise RuntimeError("No body datasets were loaded.")

    # Long dataset.
    long = pd.concat(longs, ignore_index=True)

    long.to_csv(
        OUT / "tiles_long.csv",
        index=False,
    )

    # Wide dataset.
    wide = grid.set_index("tile_id")

    for body_wide in wides:
        wide = wide.join(body_wide, how="left")

    wide = wide.reset_index()

    wide.to_csv(
        OUT / "tiles_wide.csv",
        index=False,
    )

    # Geographic tile outlines for QGIS display.
    geometries = [
        shapely.box(
            r.lon_min,
            r.lat_min,
            r.lon_max,
            r.lat_max,
        )
        for r in wide.itertuples()
    ]

    gpkg = OUT / "tiles.gpkg"

    if gpkg.exists():
        gpkg.unlink()

    gpd.GeoDataFrame(
        wide,
        geometry=geometries,
        crs="EPSG:4326",
    ).to_file(
        gpkg,
        driver="GPKG",
    )

    print("\n========== COMPLETE ==========")

    print(f"Long dataset: {len(long):,} rows")
    print(f"Wide dataset: {wide.shape[0]} tiles x {wide.shape[1]} columns")

    print("\nOutput files:")
    print("  out/tiles_long.csv")
    print("  out/tiles_wide.csv")
    print("  out/tiles.gpkg")

    print("\nMapping files:")
    print("  mappings/mars_units.csv (regenerated)")
    print("  mappings/moon_units.csv (regenerated)")
    print("  mappings/earth_units.csv (preserved)")
