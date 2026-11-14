from typing import Literal

from pydantic import BaseModel, Field

BodyId = Literal["moon", "mars"]
MatchKind = Literal["tile", "point"]
MatchStatus = Literal["match", "weak", "insufficient"]
ConfidenceLevel = Literal["high", "medium", "low", "insufficient"]


class LayerInfo(BaseModel):
    label: str
    title: str
    instrument: str
    resolution: str


class BodyInfo(BaseModel):
    id: BodyId
    name: str
    tagline: str
    radius_km: float
    min_zoom: int
    max_zoom: int
    layer: LayerInfo
    attribution: str
    attribution_url: str
    tile_url_template: str


class BodiesResponse(BaseModel):
    bodies: list[BodyInfo]


class TileIndex(BaseModel):
    z: int
    x: int
    y: int


class Bounds(BaseModel):
    west: float
    south: float
    east: float
    north: float


class Center(BaseModel):
    lat: float
    lon: float


class SizeKm(BaseModel):
    width: float
    height: float


class ClassShare(BaseModel):
    key: str
    label: str
    fraction: float = Field(ge=0, le=1)


class AgeSummary(BaseModel):
    dominant: ClassShare | None = None
    classes: list[ClassShare]
    mean_min_ga: float | None = None
    mean_max_ga: float | None = None
    surely_old_fraction: float | None = Field(default=None, ge=0, le=1)
    surely_young_fraction: float | None = Field(default=None, ge=0, le=1)


class GeologySummary(BaseModel):
    dataset_tile_ids: list[str]
    resolution_deg: float
    mapped_fraction: float = Field(ge=0, le=1)
    dominant_class: str
    classes: list[ClassShare]
    match_classes: list[ClassShare]
    age: AgeSummary | None = None
    cell_bounds: Bounds


class EarthCandidate(BaseModel):
    dataset_tile_id: str
    bounds: Bounds
    center: Center
    coverage: float = Field(ge=0, le=1)
    dominant_class: str
    match_dominant_class: str
    classes: list[ClassShare]
    match_classes: list[ClassShare]
    similarity: float = Field(ge=0, le=1)
    preview_url: str
    preview_bounds: Bounds


class EarthMatch(BaseModel):
    status: MatchStatus
    confidence: ConfidenceLevel
    confidence_score: float = Field(ge=0, le=100)
    similarity: float = Field(ge=0, le=1)
    shared_mass: float = Field(ge=0, le=1)
    coverage: float = Field(ge=0, le=1)
    reason: str
    geographic_tiebreak: bool = False
    candidates: list[EarthCandidate]


class MatchTarget(BaseModel):
    kind: MatchKind
    body: BodyId
    tile: TileIndex | None = None
    point: Center | None = None
    bounds: Bounds
    geology: GeologySummary


class MatchResponse(BaseModel):
    body: BodyId
    body_name: str
    target: MatchTarget
    match: EarthMatch
    notes: list[str]
    preview_attribution: str
    preview_attribution_url: str


class TileResponse(BaseModel):
    body: BodyId
    body_name: str
    layer: LayerInfo
    tile: TileIndex
    image_url: str
    bounds: Bounds
    center: Center
    approx_size_km: SizeKm
    geology: GeologySummary
