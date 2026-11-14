import { describe, expect, it } from 'vitest'

import { parseCoordinatePair } from './coordinates'

describe('parseCoordinatePair', () => {
  it('accepts decimal degrees', () => {
    expect(parseCoordinatePair('12.5', '-45.25')).toEqual({
      ok: true,
      lat: 12.5,
      lon: -45.25,
    })
  })

  it('accepts poles and the dateline', () => {
    expect(parseCoordinatePair('90', '180')).toEqual({
      ok: true,
      lat: 90,
      lon: 180,
    })
    expect(parseCoordinatePair('-90', '-180')).toEqual({
      ok: true,
      lat: -90,
      lon: -180,
    })
  })

  it('trims whitespace and accepts a leading plus', () => {
    expect(parseCoordinatePair(' +12.5 ', ' 45 ')).toEqual({
      ok: true,
      lat: 12.5,
      lon: 45,
    })
  })

  it('rejects missing values', () => {
    expect(parseCoordinatePair('', '0')).toEqual({
      ok: false,
      field: 'lat',
      message: 'Enter a latitude.',
    })
    expect(parseCoordinatePair('0', '')).toEqual({
      ok: false,
      field: 'lon',
      message: 'Enter a longitude.',
    })
  })

  it('rejects non-numeric values', () => {
    expect(parseCoordinatePair('north', '0')).toEqual({
      ok: false,
      field: 'lat',
      message: 'Latitude must be a number.',
    })
  })

  it('rejects out-of-range values', () => {
    expect(parseCoordinatePair('91', '0')).toEqual({
      ok: false,
      field: 'lat',
      message: 'Latitude must be between -90 and 90.',
    })
    expect(parseCoordinatePair('0', '-181')).toEqual({
      ok: false,
      field: 'lon',
      message: 'Longitude must be between -180 and 180.',
    })
  })
})
