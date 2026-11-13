export type BodyId = 'moon' | 'mars'

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

export interface AnalysisField {
  label: string
  value: string
  unit?: string | null
}

export interface TileAnalysis {
  simulated: boolean
  summary: string
  confidence_pct: number
  fields: AnalysisField[]
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
  analysis: TileAnalysis
}

export interface EarthAnalog {
  simulated: boolean
  note: string
  seed: number
  tile: { z: number; x: number; y: number }
  image_url: string
  center: TileCenter
  approx_size_km: SizeKm
  match_pct: number
}
