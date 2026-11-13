import type { BodiesResponse, EarthAnalog, TileResponse } from '../types'

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, {
    signal,
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: unknown }
      if (typeof payload.detail === 'string') {
        message = payload.detail
      }
    } catch {
      // Keep the status-based message when the body is not JSON.
    }
    throw new Error(message)
  }

  return (await response.json()) as T
}

export function fetchBodies(signal?: AbortSignal): Promise<BodiesResponse> {
  return request<BodiesResponse>('/api/bodies', signal)
}

export function fetchTile(
  body: string,
  z: number,
  x: number,
  y: number,
  signal?: AbortSignal,
): Promise<TileResponse> {
  return request<TileResponse>(`/api/tiles/${body}/${z}/${x}/${y}`, signal)
}

export function fetchEarthAnalog(signal?: AbortSignal): Promise<EarthAnalog> {
  return request<EarthAnalog>('/api/earth/random', signal)
}
