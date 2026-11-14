export type BodyId = 'moon' | 'mars'
export type MatchKind = 'tile' | 'point'
export type MatchStatus = 'match' | 'weak' | 'insufficient'
export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'insufficient'

export interface LayerInfo {
  label: string
  title: string
  instrument: string
  resolution: string
}

export interface BodyConfig {
  id: BodyId
  name: string
  tagline: string
  radius_km: number
  min_zoom: number
  max_zoom: number
  layer: LayerInfo
  attribution: string
  attribution_url: string
  tile_url_template: string
}

export interface BodiesResponse {
  bodies: BodyConfig[]
}

export interface SelectedTile {
  body: BodyId
  z: number
  x: number
  y: number
  kind: MatchKind
  lat?: number
  lon?: number
}

export interface TileBounds {
  west: number
  south: number
  east: number
  north: number
}

export interface TileCenter {
  lat: number
  lon: number
}

export interface SizeKm {
  width: number
  height: number
}

export interface ClassShare {
  key: string
  label: string
  fraction: number
}

export interface AgeSummary {
  dominant: ClassShare | null
  classes: ClassShare[]
  mean_min_ga: number | null
  mean_max_ga: number | null
  surely_old_fraction: number | null
  surely_young_fraction: number | null
}

export interface GeologySummary {
  dataset_tile_ids: string[]
  resolution_deg: number
  mapped_fraction: number
  dominant_class: string
  classes: ClassShare[]
  match_classes: ClassShare[]
  age: AgeSummary | null
  cell_bounds: TileBounds
}

export interface EarthCandidate {
  dataset_tile_id: string
  bounds: TileBounds
  center: TileCenter
  coverage: number
  dominant_class: string
  classes: ClassShare[]
  match_classes: ClassShare[]
  similarity: number
  preview_url: string
  preview_bounds: TileBounds
}

export interface EarthMatch {
  status: MatchStatus
  confidence: ConfidenceLevel
  confidence_score: number
  similarity: number
  shared_mass: number
  coverage: number
  reason: string
  candidates: EarthCandidate[]
}

export interface MatchTarget {
  kind: MatchKind
  body: BodyId
  tile: { z: number; x: number; y: number } | null
  point: TileCenter | null
  bounds: TileBounds
  geology: GeologySummary
}

export interface MatchResponse {
  body: BodyId
  body_name: string
  target: MatchTarget
  match: EarthMatch
  notes: string[]
  preview_attribution: string
  preview_attribution_url: string
}

export interface TileResponse {
  body: BodyId
  body_name: string
  layer: LayerInfo
  tile: { z: number; x: number; y: number }
  image_url: string
  bounds: TileBounds
  center: TileCenter
  approx_size_km: SizeKm
  geology: GeologySummary
}
