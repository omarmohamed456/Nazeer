from typing import Literal

from pydantic import BaseModel, Field

BodyId = Literal["moon", "mars"]


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


class AnalysisField(BaseModel):
    label: str
    value: str
    unit: str | None = None


class TileAnalysis(BaseModel):
    simulated: bool = True
    summary: str
    confidence_pct: int = Field(ge=0, le=100)
    fields: list[AnalysisField]


class TileResponse(BaseModel):
    body: BodyId
    body_name: str
    layer: LayerInfo
    tile: TileIndex
    image_url: str
    bounds: Bounds
    center: Center
    approx_size_km: SizeKm
    analysis: TileAnalysis


class EarthAnalogResponse(BaseModel):
    simulated: bool = True
    note: str
    seed: int
    tile: TileIndex
    image_url: str
    center: Center
    approx_size_km: SizeKm
    match_pct: int = Field(ge=0, le=100)
