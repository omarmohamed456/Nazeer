"""STEP 1 - look inside each dataset before building anything.
Prints layers, CRS, columns, the most common values of coded columns, and area sums
so you can confirm the field names in config.py."""
import numpy as np, pandas as pd, pyogrio
from config import BODIES

pd.set_option("display.width", 200, "display.max_columns", 50, "display.max_colwidth", 60)
AREA_COLS = ("SphArea_km", "Area_Geo", "Shape_Area")

for body, cfg in BODIES.items():
    print("\n" + "=" * 90 + f"\n{body.upper()}  ->  {cfg['path']}")
    try:
        layers = pyogrio.list_layers(cfg["path"])
    except Exception as e:
        print("  !! cannot open:", e); continue
    for name, gtype in layers:
        print(f"\n  layer: {name!r}  geometry: {gtype}")
        if gtype is None or "Polygon" not in str(gtype):
            continue
        info = pyogrio.read_info(cfg["path"], layer=name)
        print("  features:", info["features"])
        print("  CRS:", (info["crs"] or "none")[:120])
        df = pyogrio.read_dataframe(cfg["path"], layer=name, read_geometry=False)
        print("  columns:", list(df.columns))
        for c in df.columns:
            if df[c].dtype == object or str(df[c].dtype).startswith(("string", "int")):
                n = df[c].nunique()
                if 1 < n <= 300:
                    print(f"\n  -- {c}  ({n} distinct)")
                    print(df[c].value_counts(dropna=False).head(60).to_string())
        for a in AREA_COLS:
            if a in df.columns:
                print(f"\n  SUM of {a}: {df[a].sum():,.1f}")
                for u in cfg["fields"].values():
                    if u in df.columns and df[u].nunique() < 300:
                        print(df.groupby(u)[a].sum().sort_values(ascending=False).head(12).round(0).to_string())
                        break
