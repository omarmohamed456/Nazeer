"""STEP 2 - cut every polygon dataset into the SAME lat/lon tile grid and measure, per tile, how many km2 of
each source unit it contains. Areas are exact on a sphere: we project to a cylindrical equal-area system on each
body's own sphere, where lat/lon tiles are plain rectangles. Heavy step (Earth/GLiM takes a while); run once."""
import sys
import numpy as np, pandas as pd, geopandas as gpd, shapely, pyogrio, pyproj
from config import BODIES, OUT, STEP_DEG, CHUNK

def cea_crs(R):
    return pyproj.CRS.from_proj4(f"+proj=cea +R={R} +lon_0=0 +lat_ts=0 +units=m +no_defs")

def make_tiles(R):
    assert 180 % STEP_DEG == 0, "STEP_DEG must divide 180"
    rows = []
    for i, la in enumerate(np.arange(-90, 90, STEP_DEG)):
        for j, lo in enumerate(np.arange(-180, 180, STEP_DEG)):
            la1, lo1 = la + STEP_DEG, lo + STEP_DEG
            x0, x1 = R * np.radians(lo), R * np.radians(lo1)
            y0, y1 = R * np.sin(np.radians(la)), R * np.sin(np.radians(la1))
            rows.append(dict(tile_id=f"r{i:02d}c{j:02d}", lat_min=float(la), lat_max=float(la1),
                             lon_min=float(lo), lon_max=float(lo1),
                             tile_area_km2=(x1 - x0) * (y1 - y0) / 1e6, geometry=shapely.box(x0, y0, x1, y1)))
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=cea_crs(R))

def to_lonlat(gdf):
    if gdf.crs is None or gdf.crs.is_geographic:
        return gdf
    return gdf.to_crs(gdf.crs.geodetic_crs)       # undo whatever projection the file uses

def lonlat_to_cea(geoms, R):
    def f(xy):
        out = np.empty(xy.shape, dtype="float64")
        out[:, 0] = R * np.radians(xy[:, 0])
        out[:, 1] = R * np.sin(np.radians(np.clip(xy[:, 1], -90, 90)))
        return out
    return shapely.transform(geoms, f)

def process(body, cfg):
    R, fields = cfg["radius_m"], cfg["fields"]
    tiles = make_tiles(R)
    tiles.drop(columns="geometry").to_csv(OUT / f"{body}_tiles.csv", index=False)
    src_cols = list(dict.fromkeys(fields.values()))
    parts, start = [], 0
    while True:
        gdf = pyogrio.read_dataframe(cfg["path"], layer=cfg["layer"], columns=src_cols,
                                     skip_features=start, max_features=CHUNK)
        if len(gdf) == 0:
            break
        start += len(gdf)
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
        gdf = to_lonlat(gdf)
        minx, miny, maxx, maxy = gdf.total_bounds
        if minx < -180.5 or maxx > 180.5:
            sys.exit(f"{body}: longitudes run {minx:.1f}..{maxx:.1f}; this script expects -180..180. "
                     "Re-export with centre longitude 0 (or tell me and I'll add a 0-360 handler).")
        gdf["geometry"] = gdf.geometry.make_valid()
        gdf = gdf.rename(columns={v: k for k, v in fields.items()})
        for k in fields:
            gdf[k] = gdf[k].fillna("").astype(str).str.strip()
        g = gpd.GeoDataFrame(gdf.drop(columns="geometry"),
                             geometry=lonlat_to_cea(gdf.geometry.to_numpy(), R), crs=tiles.crs)
        ov = gpd.overlay(g, tiles[["tile_id", "geometry"]], how="intersection", keep_geom_type=True)
        ov["area_km2"] = ov.geometry.area / 1e6
        parts.append(ov.groupby(["tile_id", *fields.keys()])["area_km2"].sum().reset_index())
        print(f"  {body}: {start:,} polygons processed", flush=True)
    res = pd.concat(parts).groupby(["tile_id", *fields.keys()], as_index=False)["area_km2"].sum()
    res.to_csv(OUT / f"{body}_tile_unit_area.csv", index=False)
    total, sphere = res["area_km2"].sum(), 4 * np.pi * (R / 1000) ** 2
    print(f"  {body}: mapped {total:,.0f} km2 of {sphere:,.0f} km2 sphere ({100*total/sphere:.2f}%)")
    print(res.groupby("unit")["area_km2"].sum().sort_values(ascending=False).head(12).round(0).to_string())

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    only = sys.argv[1:] or list(BODIES)           # e.g.  python 02_tile_overlay.py mars moon
    for b in only:
        print(f"== {b}")
        process(b, BODIES[b])
