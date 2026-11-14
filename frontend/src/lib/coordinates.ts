export type CoordinateParseResult =
  | { ok: true; lat: number; lon: number }
  | { ok: false; field: 'lat' | 'lon'; message: string }

type SingleResult =
  | { ok: true; value: number }
  | { ok: false; message: string }

function parseOne(
  text: string,
  min: number,
  max: number,
  label: string,
): SingleResult {
  const trimmed = text.trim()
  if (!trimmed) {
    return { ok: false, message: `Enter a ${label.toLowerCase()}.` }
  }

  const value = Number(trimmed)
  if (!Number.isFinite(value)) {
    return { ok: false, message: `${label} must be a number.` }
  }
  if (value < min || value > max) {
    return { ok: false, message: `${label} must be between ${min} and ${max}.` }
  }
  return { ok: true, value }
}

export function parseCoordinatePair(
  latText: string,
  lonText: string,
): CoordinateParseResult {
  const lat = parseOne(latText, -90, 90, 'Latitude')
  if (!lat.ok) {
    return { ok: false, field: 'lat', message: lat.message }
  }

  const lon = parseOne(lonText, -180, 180, 'Longitude')
  if (!lon.ok) {
    return { ok: false, field: 'lon', message: lon.message }
  }

  return { ok: true, lat: lat.value, lon: lon.value }
}
