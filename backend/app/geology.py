from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode

from .models import (
    AgeSummary,
    BodyId,
    BodyInfo,
    Bounds,
    Center,
    ClassShare,
    ConfidenceLevel,
    EarthCandidate,
    EarthMatch,
    GeologySummary,
    MatchKind,
    MatchResponse,
    MatchStatus,
    MatchTarget,
    TileIndex,
)

DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "geology" / "tiles_wide.csv"
DATASET_RESOLUTION_DEG = 10.0
GRID_ROWS = 18
GRID_COLS = 36
MATCH_MIN_ZOOM = 2
EARTH_MIN_COVERAGE = 0.5
EARTH_MIN_REPRESENTABLE_MASS = 0.5
MAX_CANDIDATES = 3

REPRESENTABLE_KEYS = ("volcanic", "crystalline", "sedimentary", "surficial", "ice")

MOON_CLASS_KEYS = ("volcanic", "impact", "highlands", "plains")
MARS_CLASS_KEYS = (
    "volcanic",
    "impact",
    "surficial_unconsolidated",
    "undivided_terrain",
    "ice",
)
EARTH_CLASS_KEYS = (
    "volcanic",
    "metamorphic",
    "plutonic",
    "sedimentary",
    "surficial_unconsolidated",
    "ice",
    "water",
    "no_data",
)

MOON_AGE_KEYS = (
    "copernican",
    "eratosthenian",
    "eratosthenian_imbrian",
    "imbrian",
    "imbrian_nectarian",
    "nectarian",
    "pre_nectarian",
)
MARS_AGE_KEYS = (
    "a",
    "ah",
    "an",
    "h",
    "hn",
    "n",
    "ea",
    "eh",
    "en",
    "la",
    "lh",
    "ln",
    "ma",
    "mn",
)

MOON_CLASS_LABELS = {
    "volcanic": "Volcanic",
    "impact": "Impact",
    "highlands": "Highlands",
    "plains": "Plains",
}
MARS_CLASS_LABELS = {
    "volcanic": "Volcanic",
    "impact": "Impact",
    "surficial_unconsolidated": "Surficial",
    "undivided_terrain": "Undivided terrain",
    "ice": "Ice",
}
EARTH_CLASS_LABELS = {
    "volcanic": "Volcanic",
    "metamorphic": "Metamorphic",
    "plutonic": "Plutonic",
    "sedimentary": "Sedimentary",
    "surficial_unconsolidated": "Surficial",
    "ice": "Ice",
    "water": "Water",
    "no_data": "No data",
}
MATCH_CLASS_LABELS = {
    "volcanic": "Volcanic",
    "crystalline": "Crystalline",
    "sedimentary": "Sedimentary",
    "surficial": "Surficial",
    "ice": "Ice",
    "impact": "Impact",
    "undivided": "Undivided terrain",
}
MOON_AGE_LABELS = {
    "copernican": "Copernican",
    "eratosthenian": "Eratosthenian",
    "eratosthenian_imbrian": "Eratosthenian\u2013Imbrian",
    "imbrian": "Imbrian",
    "imbrian_nectarian": "Imbrian\u2013Nectarian",
    "nectarian": "Nectarian",
    "pre_nectarian": "Pre-Nectarian",
}
MARS_AGE_LABELS = {
    "a": "Amazonian",
    "ah": "Amazonian\u2013Hesperian",
    "an": "Amazonian\u2013Noachian",
    "h": "Hesperian",
    "hn": "Hesperian\u2013Noachian",
    "n": "Noachian",
    "ea": "Early Amazonian",
    "eh": "Early Hesperian",
    "en": "Early Noachian",
    "la": "Late Amazonian",
    "lh": "Late Hesperian",
    "ln": "Late Noachian",
    "ma": "Middle Amazonian",
    "mn": "Middle Noachian",
}

GIBS_WMS_URL = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
GIBS_LAYER = "BlueMarble_ShadedRelief_Bathymetry"
PREVIEW_ATTRIBUTION = "NASA GIBS \u00b7 Blue Marble Shaded Relief"
PREVIEW_ATTRIBUTION_URL = "https://gibs.earthdata.nasa.gov/"
PREVIEW_PADDING_DEG = 4.0


@dataclass(frozen=True)
class GeologyCell:
    tile_id: str
    row: int
    col: int
    bounds: Bounds
    moon_classes: dict[str, float]
    mars_classes: dict[str, float]
    earth_classes: dict[str, float]
    moon_mapped_fraction: float
    mars_mapped_fraction: float
    earth_mapped_fraction: float
    earth_dominant_class: str
    moon_age: dict[str, float]
    mars_age: dict[str, float]
    mars_mean_age_min_ga: float | None
    mars_mean_age_max_ga: float | None
    mars_surely_old_fraction: float | None
    mars_surely_young_fraction: float | None


def _float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in ("", None) else 0.0


def _optional_float(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "")
    return float(value) if value not in ("", None) else None


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def load_cells(path: Path = DATASET_PATH) -> dict[str, GeologyCell]:
    """Load and validate the 18x36, 10-degree joined geology table."""
    cells: dict[str, GeologyCell] = {}

    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            tile_id = row["tile_id"]
            parsed = re.fullmatch(r"r(\d{2})c(\d{2})", tile_id)
            if parsed is None:
                raise ValueError(f"Invalid dataset tile id '{tile_id}'.")

            row_index = int(parsed.group(1))
            col_index = int(parsed.group(2))
            if not (0 <= row_index < GRID_ROWS and 0 <= col_index < GRID_COLS):
                raise ValueError(f"Dataset tile id '{tile_id}' is outside the 18x36 grid.")

            cells[tile_id] = GeologyCell(
                tile_id=tile_id,
                row=row_index,
                col=col_index,
                bounds=Bounds(
                    west=_float(row, "lon_min"),
                    south=_float(row, "lat_min"),
                    east=_float(row, "lon_max"),
                    north=_float(row, "lat_max"),
                ),
                moon_classes={key: _float(row, f"moon_frac_{key}") for key in MOON_CLASS_KEYS},
                mars_classes={key: _float(row, f"mars_frac_{key}") for key in MARS_CLASS_KEYS},
                earth_classes={
                    key: _float(row, f"earth_mapped_class_frac_{key}")
                    for key in EARTH_CLASS_KEYS
                },
                moon_mapped_fraction=_float(row, "moon_mapped_frac"),
                mars_mapped_fraction=_float(row, "mars_mapped_frac"),
                earth_mapped_fraction=_float(row, "earth_mapped_frac"),
                earth_dominant_class=row.get("earth_dominant_class", ""),
                moon_age={key: _float(row, f"moon_age_frac_{key}") for key in MOON_AGE_KEYS},
                mars_age={key: _float(row, f"mars_age_frac_{key}") for key in MARS_AGE_KEYS},
                mars_mean_age_min_ga=_optional_float(row, "mars_mean_age_min_Ga"),
                mars_mean_age_max_ga=_optional_float(row, "mars_mean_age_max_Ga"),
                mars_surely_old_fraction=_optional_float(
                    row, "mars_frac_surely_old_gt3p5Ga"
                ),
                mars_surely_young_fraction=_optional_float(
                    row, "mars_frac_surely_young_lt1Ga"
                ),
            )

    expected = GRID_ROWS * GRID_COLS
    if len(cells) != expected:
        raise ValueError(f"Expected {expected} dataset cells, found {len(cells)}.")
    return cells


@lru_cache(maxsize=1)
def get_cells() -> dict[str, GeologyCell]:
    return load_cells()


def cell_for_point(lat: float, lon: float) -> GeologyCell:
    """Return the 10-degree dataset cell containing a coordinate.

    Dataset rows run south-to-north (r00 is the south pole); map tile rows run
    north-to-south. Keep that distinction explicit.
    """
    if not -90.0 <= lat <= 90.0:
        raise ValueError("Latitude must be between -90 and 90.")
    if not -180.0 <= lon <= 180.0:
        raise ValueError("Longitude must be between -180 and 180.")

    row_index = min(
        GRID_ROWS - 1,
        max(0, int(math.floor((lat + 90.0) / DATASET_RESOLUTION_DEG))),
    )
    col_index = min(
        GRID_COLS - 1,
        max(0, int(math.floor((lon + 180.0) / DATASET_RESOLUTION_DEG))),
    )
    return get_cells()[f"r{row_index:02d}c{col_index:02d}"]


def _overlap(a: Bounds, b: Bounds) -> Bounds | None:
    west = max(a.west, b.west)
    east = min(a.east, b.east)
    south = max(a.south, b.south)
    north = min(a.north, b.north)
    if west >= east or south >= north:
        return None
    return Bounds(west=west, south=south, east=east, north=north)


def _spherical_rect_area(bounds: Bounds) -> float:
    """Spherical area on a unit sphere; the radius cancels in weighted sums."""
    return math.radians(bounds.east - bounds.west) * (
        math.sin(math.radians(bounds.north)) - math.sin(math.radians(bounds.south))
    )


def cells_for_bounds(bounds: Bounds) -> list[tuple[GeologyCell, float]]:
    """Return overlapping dataset cells with spherical-area weights."""
    cells = get_cells()
    row_start = max(
        0,
        int(math.floor((bounds.south + 90.0) / DATASET_RESOLUTION_DEG)),
    )
    row_end = min(
        GRID_ROWS - 1,
        int(math.floor((bounds.north + 90.0 - 1e-9) / DATASET_RESOLUTION_DEG)),
    )
    col_start = max(
        0,
        int(math.floor((bounds.west + 180.0) / DATASET_RESOLUTION_DEG)),
    )
    col_end = min(
        GRID_COLS - 1,
        int(math.floor((bounds.east + 180.0 - 1e-9) / DATASET_RESOLUTION_DEG)),
    )

    weighted: list[tuple[GeologyCell, float]] = []
    for row_index in range(row_start, row_end + 1):
        for col_index in range(col_start, col_end + 1):
            cell = cells[f"r{row_index:02d}c{col_index:02d}"]
            overlap = _overlap(bounds, cell.bounds)
            if overlap is None:
                continue
            weight = _spherical_rect_area(overlap)
            if weight > 0:
                weighted.append((cell, weight))

    if not weighted:
        center_lat = (bounds.north + bounds.south) / 2.0
        center_lon = (bounds.east + bounds.west) / 2.0
        weighted.append((cell_for_point(center_lat, center_lon), 1.0))
    return weighted


def _shares(values: dict[str, float], labels: dict[str, str]) -> list[ClassShare]:
    shares = [
        ClassShare(
            key=key,
            label=labels.get(key, key.replace("_", " ").title()),
            fraction=round(_clamp(value), 4),
        )
        for key, value in values.items()
        if value > 0.0005
    ]
    shares.sort(key=lambda share: (-share.fraction, share.key))
    return shares


def _weighted_average(
    weighted: list[tuple[GeologyCell, float]], selector
) -> float:
    total = sum(weight for _, weight in weighted)
    return sum(weight * selector(cell) for cell, weight in weighted) / total


def _match_vector(body: BodyId, classes: dict[str, float]) -> dict[str, float]:
    if body == "moon":
        return {
            "volcanic": classes["volcanic"],
            "crystalline": classes["highlands"],
            "sedimentary": classes["plains"],
            "surficial": 0.0,
            "ice": 0.0,
            "impact": classes["impact"],
            "undivided": 0.0,
        }
    return {
        "volcanic": classes["volcanic"],
        "crystalline": 0.0,
        "sedimentary": 0.0,
        "surficial": classes["surficial_unconsolidated"],
        "ice": classes["ice"],
        "impact": classes["impact"],
        "undivided": classes["undivided_terrain"],
    }


def _age_summary(
    body: BodyId, weighted: list[tuple[GeologyCell, float]]
) -> AgeSummary | None:
    if body == "moon":
        values = {
            key: _weighted_average(weighted, lambda cell, key=key: cell.moon_age[key])
            for key in MOON_AGE_KEYS
        }
        shares = _shares(values, MOON_AGE_LABELS)
        return AgeSummary(dominant=shares[0] if shares else None, classes=shares)

    values = {
        key: _weighted_average(weighted, lambda cell, key=key: cell.mars_age[key])
        for key in MARS_AGE_KEYS
    }
    shares = _shares(values, MARS_AGE_LABELS)

    def optional_average(selector) -> float | None:
        pairs = [
            (weight, selector(cell))
            for cell, weight in weighted
            if selector(cell) is not None
        ]
        if not pairs:
            return None
        total = sum(weight for weight, _ in pairs)
        return sum(weight * value for weight, value in pairs) / total

    mean_min = optional_average(lambda cell: cell.mars_mean_age_min_ga)
    mean_max = optional_average(lambda cell: cell.mars_mean_age_max_ga)
    surely_old = optional_average(lambda cell: cell.mars_surely_old_fraction)
    surely_young = optional_average(lambda cell: cell.mars_surely_young_fraction)

    return AgeSummary(
        dominant=shares[0] if shares else None,
        classes=shares,
        mean_min_ga=round(mean_min, 3) if mean_min is not None else None,
        mean_max_ga=round(mean_max, 3) if mean_max is not None else None,
        surely_old_fraction=round(_clamp(surely_old), 4) if surely_old is not None else None,
        surely_young_fraction=(
            round(_clamp(surely_young), 4) if surely_young is not None else None
        ),
    )


def summarize_cells(
    weighted: list[tuple[GeologyCell, float]], body: BodyId
) -> GeologySummary:
    if not weighted:
        raise ValueError("No dataset cells overlap the target.")

    total = sum(weight for _, weight in weighted)
    if total <= 0:
        raise ValueError("Dataset overlap weights are zero.")

    if body == "moon":
        raw = {
            key: _weighted_average(weighted, lambda cell, key=key: cell.moon_classes[key])
            for key in MOON_CLASS_KEYS
        }
        mapped_fraction = _weighted_average(weighted, lambda cell: cell.moon_mapped_fraction)
    else:
        raw = {
            key: _weighted_average(weighted, lambda cell, key=key: cell.mars_classes[key])
            for key in MARS_CLASS_KEYS
        }
        mapped_fraction = _weighted_average(weighted, lambda cell: cell.mars_mapped_fraction)

    raw_total = sum(raw.values())
    if raw_total > 0:
        raw = {key: value / raw_total for key, value in raw.items()}

    dominant = max(raw, key=raw.get) if raw else "unknown"
    match_vector = _match_vector(body, raw)

    west = min(cell.bounds.west for cell, _ in weighted)
    east = max(cell.bounds.east for cell, _ in weighted)
    south = min(cell.bounds.south for cell, _ in weighted)
    north = max(cell.bounds.north for cell, _ in weighted)
    cell_ids = [
        cell.tile_id
        for cell, _ in sorted(weighted, key=lambda item: (-item[1], item[0].tile_id))
    ]

    return GeologySummary(
        dataset_tile_ids=cell_ids,
        resolution_deg=DATASET_RESOLUTION_DEG,
        mapped_fraction=round(_clamp(mapped_fraction), 4),
        dominant_class=dominant,
        classes=_shares(raw, MOON_CLASS_LABELS if body == "moon" else MARS_CLASS_LABELS),
        match_classes=_shares(match_vector, MATCH_CLASS_LABELS),
        age=_age_summary(body, weighted),
        cell_bounds=Bounds(west=west, south=south, east=east, north=north),
    )


def build_tile_geology(body: BodyId, bounds: Bounds) -> GeologySummary:
    return summarize_cells(cells_for_bounds(bounds), body)


def _earth_match_vector(classes: dict[str, float]) -> dict[str, float]:
    return {
        "volcanic": classes["volcanic"],
        "crystalline": classes["plutonic"] + classes["metamorphic"],
        "sedimentary": classes["sedimentary"],
        "surficial": classes["surficial_unconsolidated"],
        "ice": classes["ice"],
        "impact": 0.0,
        "undivided": 0.0,
    }


def _preview_bounds(bounds: Bounds) -> Bounds:
    return Bounds(
        west=round(max(-180.0, bounds.west - PREVIEW_PADDING_DEG), 4),
        south=round(max(-90.0, bounds.south - PREVIEW_PADDING_DEG), 4),
        east=round(min(180.0, bounds.east + PREVIEW_PADDING_DEG), 4),
        north=round(min(90.0, bounds.north + PREVIEW_PADDING_DEG), 4),
    )


def _preview_url(bounds: Bounds) -> str:
    params = {
        "SERVICE": "WMS",
        "REQUEST": "GetMap",
        "VERSION": "1.1.1",
        "LAYERS": GIBS_LAYER,
        "STYLES": "",
        "FORMAT": "image/jpeg",
        "TRANSPARENT": "FALSE",
        "HEIGHT": "256",
        "WIDTH": "256",
        "SRS": "EPSG:4326",
        "BBOX": f"{bounds.west:.4f},{bounds.south:.4f},{bounds.east:.4f},{bounds.north:.4f}",
    }
    return f"{GIBS_WMS_URL}?{urlencode(params)}"


def _earth_candidate(
    cell: GeologyCell, target_repr: dict[str, float]
) -> EarthCandidate | None:
    raw_coverage = cell.earth_mapped_fraction
    if raw_coverage < EARTH_MIN_COVERAGE:
        return None
    if cell.earth_dominant_class in ("", "water", "no_data"):
        return None

    match_vector = _earth_match_vector(cell.earth_classes)
    representable_mass = sum(match_vector[key] for key in REPRESENTABLE_KEYS)
    if representable_mass < EARTH_MIN_REPRESENTABLE_MASS:
        return None

    candidate_repr = {
        key: match_vector[key] / representable_mass for key in REPRESENTABLE_KEYS
    }
    similarity = sum(
        target_repr[key] * candidate_repr[key] for key in REPRESENTABLE_KEYS
    )

    center = Center(
        lat=round((cell.bounds.south + cell.bounds.north) / 2.0, 6),
        lon=round((cell.bounds.west + cell.bounds.east) / 2.0, 6),
    )
    preview_bounds = _preview_bounds(cell.bounds)

    return EarthCandidate(
        dataset_tile_id=cell.tile_id,
        bounds=cell.bounds,
        center=center,
        coverage=round(_clamp(raw_coverage), 4),
        dominant_class=cell.earth_dominant_class,
        classes=_shares(cell.earth_classes, EARTH_CLASS_LABELS),
        match_classes=_shares(match_vector, MATCH_CLASS_LABELS),
        similarity=round(_clamp(similarity), 4),
        preview_url=_preview_url(preview_bounds),
        preview_bounds=preview_bounds,
    )


def _confidence_label(
    score: float, shared_mass: float, similarity: float
) -> ConfidenceLevel:
    if score >= 75.0 and shared_mass >= 0.6 and similarity >= 0.7:
        return "high"
    if score >= 55.0 and shared_mass >= 0.4 and similarity >= 0.55:
        return "medium"
    if score >= 35.0 and shared_mass >= 0.2 and similarity >= 0.4:
        return "low"
    return "insufficient"


def _status_for(confidence: ConfidenceLevel) -> MatchStatus:
    if confidence in ("high", "medium"):
        return "match"
    if confidence == "low":
        return "weak"
    return "insufficient"


def _unmatched_mass(geology: GeologySummary) -> float:
    target = {share.key: share.fraction for share in geology.match_classes}
    return target.get("impact", 0.0) + target.get("undivided", 0.0)


def match_geology(body: BodyId, geology: GeologySummary) -> EarthMatch:
    target = {share.key: share.fraction for share in geology.match_classes}
    shared_mass = _clamp(sum(target.get(key, 0.0) for key in REPRESENTABLE_KEYS))

    if shared_mass <= 0.01:
        return EarthMatch(
            status="insufficient",
            confidence="insufficient",
            confidence_score=0.0,
            similarity=0.0,
            shared_mass=round(shared_mass, 4),
            coverage=0.0,
            reason=(
                "This target is dominated by impact or undivided terrain. "
                "The supplied Earth table has no equivalent class for that material, "
                "so no reliable Earth analog can be ranked."
            ),
            candidates=[],
        )

    target_repr = {
        key: target.get(key, 0.0) / shared_mass for key in REPRESENTABLE_KEYS
    }
    candidates = [
        candidate
        for cell in get_cells().values()
        if (candidate := _earth_candidate(cell, target_repr)) is not None
    ]

    if not candidates:
        return EarthMatch(
            status="insufficient",
            confidence="insufficient",
            confidence_score=0.0,
            similarity=0.0,
            shared_mass=round(shared_mass, 4),
            coverage=0.0,
            reason=(
                "No Earth land tile passed the coverage filter for this target. "
                "Try a different location or zoom in."
            ),
            candidates=[],
        )

    candidates.sort(key=lambda item: (-item.similarity, -item.coverage, item.dataset_tile_id))
    top = candidates[:MAX_CANDIDATES]
    similarity = top[0].similarity
    coverage = top[0].coverage
    margin = similarity - top[1].similarity if len(top) > 1 else 1.0
    score = 100.0 * min(
        1.0,
        math.sqrt(max(0.0, similarity) * shared_mass * coverage)
        + 0.05 * min(margin / 0.15, 1.0),
    )
    confidence = _confidence_label(score, shared_mass, similarity)
    status = _status_for(confidence)

    if status == "match":
        reason = (
            f"The best Earth tile shares a comparable composition across "
            f"{shared_mass * 100:.0f}% of the target area, with "
            f"{coverage * 100:.0f}% land coverage in the matched cell."
        )
    elif status == "weak":
        reason = (
            f"Closest available analog. Only {shared_mass * 100:.0f}% of the target "
            "area has a class that can be compared with the Earth table, so treat "
            "this as a weak match."
        )
    else:
        reason = (
            f"Too little of the target area ({shared_mass * 100:.0f}%) has a "
            "comparable Earth class. The candidates below are the closest "
            "available tiles, not a reliable analog."
        )

    return EarthMatch(
        status=status,
        confidence=confidence,
        confidence_score=round(score, 1),
        similarity=round(similarity, 4),
        shared_mass=round(shared_mass, 4),
        coverage=round(coverage, 4),
        reason=reason,
        candidates=top,
    )


def _notes(
    body: BodyId,
    geology: GeologySummary,
    result: EarthMatch,
    target_kind: MatchKind,
) -> list[str]:
    notes: list[str] = []
    if target_kind == "point":
        notes.append("The match uses the 10\u00b0 dataset cell containing the point.")
    else:
        count = len(geology.dataset_tile_ids)
        notes.append(
            f"The match area-weights {count} dataset cell"
            f"{'' if count == 1 else 's'} overlapping the selected map tile."
        )

    notes.append(
        "Earth candidates are land tiles with at least 50% mapped coverage; "
        "ocean and no-data tiles are excluded."
    )
    notes.append(
        "Similarity is a heuristic composition comparison at 10\u00b0 resolution, "
        "not a geologic provenance or formation model."
    )
    notes.append(
        "Moon highlands are compared with Earth plutonic/metamorphic crust; "
        "Moon plains with sedimentary units."
        if body == "moon"
        else "Mars volcanic, ice, and surficial classes are compared directly; "
        "undivided terrain and impact have no Earth equivalent."
    )

    unmatched = _unmatched_mass(geology)
    if unmatched > 0.05:
        notes.append(
            f"{unmatched * 100:.0f}% of the target is impact or undivided terrain; "
            "that material lowers confidence rather than being forced onto an "
            "Earth class."
        )
    if result.coverage and result.coverage < 0.8:
        notes.append(
            f"The best Earth candidate is only {result.coverage * 100:.0f}% mapped, "
            "which also lowers confidence."
        )
    if geology.mapped_fraction < 0.99:
        notes.append(
            f"{geology.mapped_fraction * 100:.0f}% of the target area is mapped "
            "in the dataset."
        )
    notes.append("Earth age data is not available in this dataset.")
    return notes


def build_tile_match(
    body: BodyInfo, z: int, x: int, y: int, bounds: Bounds
) -> MatchResponse:
    geology = build_tile_geology(body.id, bounds)
    result = match_geology(body.id, geology)
    return MatchResponse(
        body=body.id,
        body_name=body.name,
        target=MatchTarget(
            kind="tile",
            body=body.id,
            tile=TileIndex(z=z, x=x, y=y),
            bounds=bounds,
            geology=geology,
        ),
        match=result,
        notes=_notes(body.id, geology, result, "tile"),
        preview_attribution=PREVIEW_ATTRIBUTION,
        preview_attribution_url=PREVIEW_ATTRIBUTION_URL,
    )


def build_point_match(body: BodyInfo, lat: float, lon: float) -> MatchResponse:
    cell = cell_for_point(lat, lon)
    geology = summarize_cells([(cell, 1.0)], body.id)
    result = match_geology(body.id, geology)
    return MatchResponse(
        body=body.id,
        body_name=body.name,
        target=MatchTarget(
            kind="point",
            body=body.id,
            point=Center(lat=lat, lon=lon),
            bounds=cell.bounds,
            geology=geology,
        ),
        match=result,
        notes=_notes(body.id, geology, result, "point"),
        preview_attribution=PREVIEW_ATTRIBUTION,
        preview_attribution_url=PREVIEW_ATTRIBUTION_URL,
    )
