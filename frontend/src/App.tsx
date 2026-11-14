import { useEffect, useState } from 'react'

import {
  fetchBodies,
  fetchPointMatch,
  fetchTile,
  fetchTileMatch,
} from './api/client'
import CoordinateBar from './components/CoordinateBar'
import Header from './components/Header'
import PlanetMap from './components/PlanetMap'
import TilePanel from './components/TilePanel'
import { COORDINATE_ZOOM, MATCH_MIN_ZOOM } from './lib/constants'
import { isAbortError, toMessage } from './lib/errors'
import { tileAtLatLng } from './lib/tileMath'
import type {
  BodyConfig,
  BodyId,
  MatchResponse,
  SelectedTile,
  TileResponse,
} from './types'

interface MapTarget {
  lat: number
  lon: number
  nonce: number
}

export default function App() {
  const [bodies, setBodies] = useState<BodyConfig[]>([])
  const [bodiesLoading, setBodiesLoading] = useState(true)
  const [bodiesError, setBodiesError] = useState<string | null>(null)
  const [bodiesNonce, setBodiesNonce] = useState(0)

  const [bodyId, setBodyId] = useState<BodyId>('moon')
  const [selected, setSelected] = useState<SelectedTile | null>(null)
  const [tile, setTile] = useState<TileResponse | null>(null)
  const [tileLoading, setTileLoading] = useState(false)
  const [tileError, setTileError] = useState<string | null>(null)

  const [match, setMatch] = useState<MatchResponse | null>(null)
  const [matchLoading, setMatchLoading] = useState(false)
  const [matchError, setMatchError] = useState<string | null>(null)
  const [matchNonce, setMatchNonce] = useState(0)

  const [point, setPoint] = useState<{ lat: number; lon: number } | null>(null)
  const [mapTarget, setMapTarget] = useState<MapTarget | null>(null)
  const [coordLat, setCoordLat] = useState('')
  const [coordLon, setCoordLon] = useState('')

  const [showGrid, setShowGrid] = useState(false)
  const [resetToken, setResetToken] = useState(0)
  const [retryNonce, setRetryNonce] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    fetchBodies(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setBodies(data.bodies)
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted && !isAbortError(err)) {
          setBodiesError(toMessage(err))
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setBodiesLoading(false)
        }
      })

    return () => controller.abort()
  }, [bodiesNonce])

  useEffect(() => {
    if (!selected) {
      return
    }

    const controller = new AbortController()

    setTileLoading(true)
    setTileError(null)

    fetchTile(
      selected.body,
      selected.z,
      selected.x,
      selected.y,
      controller.signal,
    )
      .then((data) => {
        if (!controller.signal.aborted) {
          setTile(data)
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted && !isAbortError(err)) {
          setTileError(toMessage(err))
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setTileLoading(false)
        }
      })

    return () => controller.abort()
  }, [selected, retryNonce])

  useEffect(() => {
    if (!selected) {
      return
    }
    if (selected.z < MATCH_MIN_ZOOM) {
      setMatch(null)
      setMatchError(null)
      setMatchLoading(false)
      return
    }

    const controller = new AbortController()

    setMatchLoading(true)
    setMatchError(null)
    setMatch(null)

    const request =
      selected.kind === 'point' &&
      selected.lat != null &&
      selected.lon != null
        ? fetchPointMatch(
            selected.body,
            selected.lat,
            selected.lon,
            controller.signal,
          )
        : fetchTileMatch(
            selected.body,
            selected.z,
            selected.x,
            selected.y,
            controller.signal,
          )

    request
      .then((data) => {
        if (!controller.signal.aborted) {
          setMatch(data)
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted && !isAbortError(err)) {
          setMatchError(toMessage(err))
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setMatchLoading(false)
        }
      })

    return () => controller.abort()
  }, [selected, matchNonce])

  const body = bodies.find((candidate) => candidate.id === bodyId) ?? null

  const matchDisabledReason =
    selected && selected.z < MATCH_MIN_ZOOM
      ? `Zoom to level ${MATCH_MIN_ZOOM} or deeper for a meaningful 10° geology comparison.`
      : null

  function clearSelection() {
    setSelected(null)
    setTile(null)
    setTileError(null)
    setTileLoading(false)
    setMatch(null)
    setMatchError(null)
    setMatchLoading(false)
    setPoint(null)
    setMapTarget(null)
  }

  function handleSelect(next: SelectedTile) {
    setSelected(next)
    setTile(null)
    setTileError(null)
    setTileLoading(true)
    setMatch(null)
    setMatchError(null)
    setMatchLoading(next.z >= MATCH_MIN_ZOOM)

    if (next.lat != null && next.lon != null) {
      setPoint({ lat: next.lat, lon: next.lon })
      setCoordLat(next.lat.toFixed(4))
      setCoordLon(next.lon.toFixed(4))
    } else {
      setPoint(null)
    }
  }

  function handleCoordinateSubmit(lat: number, lon: number) {
    const z = COORDINATE_ZOOM
    const { x, y } = tileAtLatLng(lat, lon, z)
    const next: SelectedTile = {
      body: bodyId,
      z,
      x,
      y,
      kind: 'point',
      lat,
      lon,
    }

    setCoordLat(lat.toFixed(4))
    setCoordLon(lon.toFixed(4))
    setMapTarget((current) => ({
      lat,
      lon,
      nonce: (current?.nonce ?? 0) + 1,
    }))
    handleSelect(next)
  }

  function handleBodyChange(id: BodyId) {
    if (id === bodyId) {
      return
    }
    setBodyId(id)
    clearSelection()
    setCoordLat('')
    setCoordLon('')
    setResetToken((value) => value + 1)
  }

  function handleReset() {
    clearSelection()
    setCoordLat('')
    setCoordLon('')
    setResetToken((value) => value + 1)
  }

  function handleTileRetry() {
    setTileError(null)
    setTileLoading(true)
    setRetryNonce((value) => value + 1)
  }

  function handleMatchRetry() {
    if (!selected) {
      return
    }
    setMatchError(null)
    setMatchLoading(selected.z >= MATCH_MIN_ZOOM)
    setMatchNonce((value) => value + 1)
  }

  function retryBodies() {
    setBodiesError(null)
    setBodiesLoading(true)
    setBodiesNonce((value) => value + 1)
  }

  return (
    <div className={`app theme-${bodyId}`}>
      <Header
        bodies={bodies}
        bodiesLoading={bodiesLoading}
        bodyId={bodyId}
        onBodyChange={handleBodyChange}
        showGrid={showGrid}
        onToggleGrid={() => setShowGrid((value) => !value)}
        onReset={handleReset}
      />

      {bodiesError ? (
        <main className="app-main app-main-error">
          <section className="fatal-error">
            <span className="eyebrow">Connection error</span>
            <h2>Can’t reach the API</h2>
            <p>{bodiesError}</p>
            <p className="muted">
              Start the FastAPI backend on port 8000, then try again.
            </p>
            <button type="button" className="primary-button" onClick={retryBodies}>
              Retry connection
            </button>
          </section>
        </main>
      ) : (
        <main className="app-main">
          <section className="map-column" aria-label="Planet map">
            {body ? (
              <CoordinateBar
                key={`${bodyId}:${resetToken}`}
                bodyName={body.name}
                lat={coordLat}
                lon={coordLon}
                onLatChange={setCoordLat}
                onLonChange={setCoordLon}
                onSubmit={handleCoordinateSubmit}
              />
            ) : null}

            {body ? (
              <PlanetMap
                body={body}
                selected={selected}
                point={point}
                mapTarget={mapTarget}
                showGrid={showGrid}
                resetToken={resetToken}
                onSelect={handleSelect}
              />
            ) : (
              <div className="map-placeholder">
                <span className="planet-loader" aria-hidden="true" />
                <p>
                  {bodiesLoading
                    ? 'Loading planetary basemap…'
                    : 'No basemap available'}
                </p>
              </div>
            )}
          </section>

          <TilePanel
            body={body}
            selected={selected}
            tile={tile}
            loading={tileLoading}
            error={tileError}
            onRetry={handleTileRetry}
            match={match}
            matchLoading={matchLoading}
            matchError={matchError}
            matchDisabledReason={matchDisabledReason}
            onMatchRetry={handleMatchRetry}
          />
        </main>
      )}
    </div>
  )
}
