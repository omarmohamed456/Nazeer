
from pathlib import Path
import pandas as pd
import numpy as np

OUT = Path("out")
MAPDIR = Path("mappings")

bodies = ["mars", "moon", "earth"]

print("\n" + "=" * 65)
print("1. MAPPING FILE VALIDATION")
print("=" * 65)

for body in bodies:
    path = MAPDIR / f"{body}_units.csv"
    df = pd.read_csv(path)

    print(f"\n{body.upper()}: {len(df)} unique mapping rows")
    print("\nClass distribution:")
    print(df["process_class"].value_counts(dropna=False).to_string())

    if "needs_review" in df:
        print("\nNeeds review:")
        print(df["needs_review"].value_counts(dropna=False).to_string())

    if body == "moon":
        print("\nMoon sample:")
        print(df[["unit", "name", "age", "process_class",
                  "age_min_Ga", "age_max_Ga"]].head(15).to_string(index=False))

        print("\nMoon units classified as unclassified:")
        print(df.loc[
            df["process_class"] == "unclassified",
            ["unit", "name", "age"]
        ].to_string(index=False))

print("\n" + "=" * 65)
print("2. TILE COVERAGE VALIDATION")
print("=" * 65)

wide = pd.read_csv(OUT / "tiles_wide.csv")

for body in bodies:
    col = f"{body}_mapped_frac"
    values = wide[col]

    print(f"\n{body.upper()}")
    print(f"Mean mapped coverage: {values.mean() * 100:.2f}%")
    print(f"Minimum: {values.min() * 100:.2f}%")
    print(f"Maximum: {values.max() * 100:.2f}%")
    print(f"Tiles above 100%: {(values > 1.001).sum()}")
    print(f"Tiles below 1%: {(values < 0.01).sum()}")

    if (values > 1.001).any():
        print("Problematic tiles:")
        print(wide.loc[values > 1.001, ["tile_id", col]].to_string(index=False))

print("\n" + "=" * 65)
print("3. CLASS FRACTION VALIDATION")
print("=" * 65)

for body in bodies:
    cols = [
        c for c in wide.columns
        if c.startswith(f"{body}_frac_")
    ]

    class_sum = wide[cols].sum(axis=1)
    mapped = wide[f"{body}_mapped_frac"]

    difference = (class_sum - mapped).abs()

    print(f"\n{body.upper()}")
    print(f"Mean absolute difference: {difference.mean():.8f}")
    print(f"Maximum absolute difference: {difference.max():.8f}")

print("\n" + "=" * 65)
print("4. TILE GRID VALIDATION")
print("=" * 65)

tile_sets = {}

for body in bodies:
    df = pd.read_csv(OUT / f"{body}_tiles.csv")
    tile_sets[body] = set(df["tile_id"])
    print(f"{body}: {len(df)} tiles")

print("Same tile IDs across all bodies:",
      tile_sets["mars"] == tile_sets["moon"] == tile_sets["earth"])

print("\n" + "=" * 65)
print("5. TOTAL MAPPED AREA")
print("=" * 65)

for body in bodies:
    df = pd.read_csv(OUT / f"{body}_tile_unit_area.csv")
    total = df["area_km2"].sum()
    print(f"{body}: {total:,.2f} km²")

print("\nValidation complete.")
