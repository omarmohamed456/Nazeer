"""Cross-body terrain-shape matcher, v2 (screening heuristic - NOT validated).

Changes relative to find_crossbody_matches.py:
  * scaling is fitted on the EARTH catalog only (robust median/MAD, std fallback)
  * relief / slope / local-std are log1p-transformed before scaling
  * default feature set "core4" (the 12-feature set is kept as "legacy12")
  * optional Mahalanobis (whitened) distance to absorb feature correlation
  * every match is calibrated against an Earth->Earth nearest-neighbour null
    distribution, and queries that fall outside the Earth range are flagged
  * explicit boolean parsing, duplicate removal, zero-variance handling
  * deterministic ordering, provenance JSON written next to the CSV
Elevation columns are never used in the score.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/planetary_gmt_pilot/csv_exports"

LEGACY12 = [
    "relief_p98_p02_m", "slope_median_deg", "slope_p90_deg", "slope_max_deg",
    "local_std_median_m", "local_std_p90_m",
    "slope_0_5_pct", "slope_5_10_pct", "slope_10_15_pct",
    "slope_15_20_pct", "slope_20_30_pct", "slope_30_90_pct",
]
CORE4 = [
    "relief_p98_p02_m", "slope_median_deg", "slope_p90_deg",
    "local_std_median_m",
]
FEATURE_SETS = {"core4": CORE4, "legacy12": LEGACY12}
LOG_COLS = {
    "relief_p98_p02_m", "slope_median_deg", "slope_p90_deg", "slope_max_deg",
    "local_std_median_m", "local_std_p90_m",
}
FORBIDDEN = ("elevation_",)          # raw heights must never enter the score
REQUIRED_META = ["window_id", "center_lon", "center_lat",
                 "eligible", "processing_status"]


# ----------------------------------------------------------------- loading
def parse_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    text = series.astype(str).str.strip().str.lower()
    return text.isin({"true", "1", "yes"})


def load_catalog(path, body, features):
    df = pd.read_csv(path)
    if "body" not in df.columns:
        df["body"] = body
    df["body"] = df["body"].astype(str).str.lower()
    missing = [c for c in [*REQUIRED_META, *features] if c not in df.columns]
    if missing:
        raise SystemExit(f"{path} is missing columns: {missing}")

    n_raw = len(df)
    df["eligible"] = parse_bool(df["eligible"])
    status_ok = df["processing_status"].astype(str).str.strip().str.lower().eq("ok")
    df = df[df["eligible"] & status_ok].copy()
    for c in features:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=features)
    for c in features:
        if c in LOG_COLS:
            df = df[df[c] >= 0]
    n_dup = int(df["window_id"].duplicated().sum())
    df = df.drop_duplicates("window_id", keep="last").reset_index(drop=True)
    info = {"rows_in_file": n_raw, "rows_usable": len(df),
            "duplicates_dropped": n_dup}
    return df, info


# ----------------------------------------------------------------- scaling
def to_matrix(df, features):
    X = df[features].to_numpy(dtype=float).copy()
    for j, f in enumerate(features):
        if f in LOG_COLS:
            X[:, j] = np.log1p(X[:, j])
    return X


class Scaler:
    """Fitted on Earth only. Drops zero-variance columns instead of dividing by 0."""

    def __init__(self, X, metric, floor=1e-9, ridge=1e-3):
        self.metric = metric
        med = np.median(X, axis=0)
        mad = 1.4826 * np.median(np.abs(X - med), axis=0)
        sd = X.std(axis=0, ddof=1)
        scale = np.where(mad > floor, mad, sd)       # MAD collapses on mostly-zero bins
        self.keep = scale > floor
        if not self.keep.any():
            raise SystemExit("All features have zero variance on Earth.")
        self.med, self.scale = med[self.keep], scale[self.keep]
        Z = (X[:, self.keep] - self.med) / self.scale
        self.whiten = None
        if metric == "mahalanobis":
            cov = np.atleast_2d(np.cov(Z, rowvar=False))
            cov = cov + ridge * np.mean(np.diag(cov)) * np.eye(cov.shape[0])
            L = np.linalg.cholesky(cov)
            self.whiten = np.linalg.inv(L).T         # Euclid(Z @ W) == Mahalanobis(Z)

    def transform(self, X):
        Z = (X[:, self.keep] - self.med) / self.scale
        return Z @ self.whiten if self.whiten is not None else Z


# ---------------------------------------------------------------- matching
def haversine_km(lat1, lon1, lat2, lon2):
    p = np.pi / 180.0
    a = (np.sin((lat2 - lat1) * p / 2) ** 2
         + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742.0 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def earth_null(Ze, earth, tree, min_sep_km, k=30):
    """Nearest-neighbour distance of each Earth window to another Earth window."""
    kk = min(k, len(Ze))
    d, idx = tree.query(Ze, k=kk)
    d, idx = d.reshape(len(Ze), -1), idx.reshape(len(Ze), -1)
    lat, lon = earth["center_lat"].to_numpy(), earth["center_lon"].to_numpy()
    null = np.empty(len(Ze))
    for i in range(len(Ze)):
        chosen = d[i, -1]                              # conservative fallback
        for dist, j in zip(d[i], idx[i]):
            if j == i:
                continue
            if haversine_km(lat[i], lon[i], lat[j], lon[j]) > min_sep_km:
                chosen = dist
                break
        null[i] = chosen
    return np.sort(null)


def run_matching(earth, queries, features, metric, top_n, min_sep_km):
    Xe = to_matrix(earth, features)
    sc = Scaler(Xe, metric)
    Ze = sc.transform(Xe)
    tree = cKDTree(Ze)
    k = min(top_n, len(earth))
    result = {"scaler": sc, "k": k, "queries": {}}
    result["null"] = earth_null(Ze, earth, tree, min_sep_km)
    norms_e = np.sort(np.linalg.norm(Ze, axis=1))
    ids = earth["window_id"].to_numpy()
    for body, qdf in queries.items():
        if qdf.empty:
            continue
        Zq = sc.transform(to_matrix(qdf, features))
        d, idx = tree.query(Zq, k=k)
        d, idx = d.reshape(len(qdf), -1), idx.reshape(len(qdf), -1)
        for r in range(len(qdf)):                      # deterministic tie-break
            order = np.lexsort((ids[idx[r]], d[r]))
            d[r], idx[r] = d[r][order], idx[r][order]
        ood = np.searchsorted(norms_e, np.linalg.norm(Zq, axis=1), side="right") / len(norms_e) * 100
        result["queries"][body] = {"d": d, "idx": idx, "ood_pct": ood}
    return result


def legacy_sets(earth, queries, top_n):
    """Re-implementation of the original matcher (pooled z-score, 12 features, Euclid)."""
    feats = LEGACY12
    pool = pd.concat([earth[feats], *[q[feats] for q in queries.values()]])
    mean, sd = pool.mean(), pool.std().replace(0, 1.0)
    Ze = ((earth[feats] - mean) / sd).to_numpy(float)
    out = {}
    for body, q in queries.items():
        Zq = ((q[feats] - mean) / sd).to_numpy(float)
        sets = []
        for z in Zq:
            dist = np.sqrt(((Ze - z) ** 2).sum(axis=1))
            sets.append(set(earth["window_id"].to_numpy()[np.argsort(dist)[:top_n]]))
        out[body] = sets
    return out


# -------------------------------------------------------------------- main
def build_output(earth, queries, res, features, top_n):
    rows = []
    null = res["null"]
    p95 = float(np.percentile(null, 95))
    for body, qdf in queries.items():
        if body not in res["queries"]:
            continue
        block = res["queries"][body]
        for r in range(len(qdf)):
            q = qdf.iloc[r]
            for rank, (dist, j) in enumerate(zip(block["d"][r], block["idx"][r]), 1):
                e = earth.iloc[j]
                row = {
                    "query_body": body, "query_window_id": q["window_id"],
                    "query_center_lat": q["center_lat"], "query_center_lon": q["center_lon"],
                    "rank": rank, "earth_window_id": e["window_id"],
                    "earth_center_lat": e["center_lat"], "earth_center_lon": e["center_lon"],
                    "distance": float(dist),
                    "null_percentile": float(np.searchsorted(null, dist, side="right") / len(null) * 100),
                    "poor_match": bool(dist > p95),
                    "query_range_percentile": float(block["ood_pct"][r]),
                    "query_outside_earth_range": bool(block["ood_pct"][r] >= 99.0),
                }
                for f in features:
                    row[f"q_{f}"], row[f"e_{f}"] = q[f], e[f]
                rows.append(row)
    out = pd.DataFrame(rows)
    return out.sort_values(["query_body", "query_window_id", "rank"], ignore_index=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--earth-csv", type=Path, required=True)
    ap.add_argument("--mars-csv", type=Path)
    ap.add_argument("--moon-csv", type=Path)
    ap.add_argument("--features", default="core4",
                    help="core4, legacy12 or a comma-separated column list")
    ap.add_argument("--metric", choices=["mahalanobis", "euclid"], default="mahalanobis")
    ap.add_argument("--top-n", type=int, default=10)
    ap.add_argument("--null-min-sep-km", type=float, default=12.0)
    ap.add_argument("--output-dir", type=Path, default=OUT)
    ap.add_argument("--legacy-compare", action="store_true",
                    help="report top-N overlap with the original pooled 12-feature matcher")
    a = ap.parse_args(argv)

    features = FEATURE_SETS.get(a.features) or [f.strip() for f in a.features.split(",") if f.strip()]
    bad = [f for f in features if f.startswith(FORBIDDEN)]
    if bad:
        raise SystemExit(f"Raw elevation features must not be used for cross-body scoring: {bad}")
    if a.legacy_compare:
        features_needed = sorted(set(features) | set(LEGACY12))
    else:
        features_needed = features
    if not (a.mars_csv or a.moon_csv):
        raise SystemExit("Provide --mars-csv and/or --moon-csv.")

    earth, e_info = load_catalog(a.earth_csv, "earth", features_needed)
    queries, q_info = {}, {}
    for body, p in (("mars", a.mars_csv), ("moon", a.moon_csv)):
        if p:
            queries[body], q_info[body] = load_catalog(p, body, features_needed)
    if earth.empty or all(q.empty for q in queries.values()):
        raise SystemExit("No usable Earth or query windows.")
    ids = pd.concat([earth["window_id"], *[q["window_id"] for q in queries.values()]])
    if ids.duplicated().any():
        raise SystemExit("window_id collisions across bodies; IDs must be body-unique.")
    if len(earth) < a.top_n:
        print(f"WARNING: only {len(earth)} Earth windows; fewer than top-n={a.top_n} matches per query.")

    res = run_matching(earth, queries, features, a.metric, a.top_n, a.null_min_sep_km)
    out = build_output(earth, queries, res, features, a.top_n)

    a.output_dir.mkdir(parents=True, exist_ok=True)
    path = a.output_dir / "crossbody_matches_v2.csv"
    out.to_csv(path, index=False, encoding="utf-8-sig")

    sc = res["scaler"]
    meta = {
        "method": "crossbody_matcher_v2_screening_heuristic",
        "features_requested": features,
        "features_used": [f for f, k in zip(features, sc.keep) if k],
        "features_dropped_zero_variance": [f for f, k in zip(features, sc.keep) if not k],
        "log1p_columns": sorted(set(features) & LOG_COLS),
        "metric": a.metric, "scaling": "median/MAD fitted on Earth only (std fallback)",
        "top_n": a.top_n, "earth_catalog": e_info, "query_catalogs": q_info,
        "earth_null_nn_distance_percentiles": {
            str(p): float(np.percentile(res["null"], p)) for p in (50, 90, 95, 99)},
        "poor_match_rule": "distance > 95th percentile of Earth->Earth NN distance",
        "outside_range_rule": "query norm in scaled space >= 99th percentile of Earth norms",
        "excluded_from_score": "all elevation_* columns; land_fraction",
    }
    if a.legacy_compare:
        legacy = legacy_sets(earth, queries, a.top_n)
        meta["legacy_overlap_mean_fraction"] = {}
        for body, sets in legacy.items():
            new = out[out.query_body == body].groupby("query_window_id")["earth_window_id"].apply(set)
            ordered = queries[body]["window_id"]
            ov = [len(sets[i] & new[w]) / a.top_n for i, w in enumerate(ordered)]
            meta["legacy_overlap_mean_fraction"][body] = float(np.mean(ov))
    (a.output_dir / "crossbody_matches_v2_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Earth windows: {len(earth)} | " + " | ".join(f"{b}: {len(q)}" for b, q in queries.items()))
    print(f"Match rows: {len(out)} | poor matches: {int(out.poor_match.sum())} "
          f"| queries outside Earth range: {int(out.loc[out['rank'] == 1, 'query_outside_earth_range'].sum())}")
    if a.legacy_compare:
        print("Overlap with legacy top-N:", meta["legacy_overlap_mean_fraction"])
    print(f"Saved: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())