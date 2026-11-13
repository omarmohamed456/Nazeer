import type { TileBounds } from '../types'

export interface TileCoord {
  z: number
  x: number
  y: number
}

/**
 * Convert a geographic point to the tile containing it in the NASA Trek
 * 2:1 equirectangular grid. The same formula is used by the backend.
 */
export function tileAtLatLng(lat: number, lon: number, zoom: number): TileCoord {
  const z = Math.max(0, Math.round(zoom))
  const cols = 2 ** (z + 1)
  const rows = 2 ** z

  const rawX = Math.floor(((lon + 180) / 360) * cols)
  const rawY = Math.floor(((90 - lat) / 180) * rows)

  return {
    z,
    x: Math.min(cols - 1, Math.max(0, rawX)),
    y: Math.min(rows - 1, Math.max(0, rawY)),
  }
}

export function tileBounds(z: number, x: number, y: number): TileBounds {
  const cols = 2 ** (z + 1)
  const rows = 2 ** z

  return {
    west: -180 + (x / cols) * 360,
    east: -180 + ((x + 1) / cols) * 360,
    north: 90 - (y / rows) * 180,
    south: 90 - ((y + 1) / rows) * 180,
  }
}

export function formatLat(lat: number, digits = 2): string {
  const ns = lat >= 0 ? 'N' : 'S'
  return `${Math.abs(lat).toFixed(digits)}°${ns}`
}

export function formatLon(lon: number, digits = 2): string {
  const ew = lon >= 0 ? 'E' : 'W'
  return `${Math.abs(lon).toFixed(digits)}°${ew}`
}

export function formatLatLon(lat: number, lon: number, digits = 2): string {
  return `${formatLat(lat, digits)} ${formatLon(lon, digits)}`
}

export function isInsideWorld(lat: number, lon: number): boolean {
  return lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180
}
