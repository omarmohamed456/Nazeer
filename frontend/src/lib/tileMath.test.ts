import { describe, expect, it } from 'vitest'

import {
  datasetCellAtLatLng,
  formatLatLon,
  isInsideWorld,
  tileAtLatLng,
  tileBounds,
} from './tileMath'

describe('tileAtLatLng', () => {
  it('selects the western tile at level zero', () => {
    expect(tileAtLatLng(0, -90, 0)).toEqual({ z: 0, x: 0, y: 0 })
  })

  it('selects the eastern tile east of the prime meridian', () => {
    expect(tileAtLatLng(0, 1, 0)).toEqual({ z: 0, x: 1, y: 0 })
  })

  it('maps a coordinate into the zoom 2 grid', () => {
    expect(tileAtLatLng(45, -10, 2)).toEqual({ z: 2, x: 3, y: 1 })
  })

  it('clamps the outer edges to valid tile indexes', () => {
    expect(tileAtLatLng(90, 180, 3)).toEqual({ z: 3, x: 15, y: 0 })
    expect(tileAtLatLng(-90, -180, 3)).toEqual({ z: 3, x: 0, y: 7 })
  })

  it('rounds fractional map zooms', () => {
    expect(tileAtLatLng(0, 0, 2.4)).toEqual(tileAtLatLng(0, 0, 2))
  })
})

describe('tileBounds', () => {
  it('computes level zero bounds', () => {
    expect(tileBounds(0, 1, 0)).toEqual({
      west: 0,
      east: 180,
      north: 90,
      south: -90,
    })
  })

  it('computes a mid-latitude tile', () => {
    expect(tileBounds(2, 0, 0)).toEqual({
      west: -180,
      east: -135,
      north: 90,
      south: 45,
    })
  })
})

describe('display helpers', () => {
  it('formats hemispheres', () => {
    expect(formatLatLon(33.75, -123.75)).toBe('33.75°N 123.75°W')
    expect(formatLatLon(-12.5, 45)).toBe('12.50°S 45.00°E')
  })

  it('recognises points outside the world', () => {
    expect(isInsideWorld(0, 0)).toBe(true)
    expect(isInsideWorld(91, 0)).toBe(false)
    expect(isInsideWorld(0, -181)).toBe(false)
  })
})

describe('datasetCellAtLatLng', () => {
  it('maps the equator and prime meridian to r09c18', () => {
    expect(datasetCellAtLatLng(0, 0)).toEqual({
      row: 9,
      col: 18,
      tileId: 'r09c18',
      bounds: { west: 0, south: 0, east: 10, north: 10 },
    })
  })

  it('maps a mid-northern point to the correct south-to-north row', () => {
    expect(datasetCellAtLatLng(45, -10)).toEqual({
      row: 13,
      col: 17,
      tileId: 'r13c17',
      bounds: { west: -10, south: 40, east: 0, north: 50 },
    })
  })

  it('clamps the poles and dateline', () => {
    expect(datasetCellAtLatLng(90, 180).tileId).toBe('r17c35')
    expect(datasetCellAtLatLng(-90, -180).tileId).toBe('r00c00')
  })
})
