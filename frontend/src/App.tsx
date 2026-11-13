import { useEffect, useState } from 'react'

import { fetchBodies, fetchTile } from './api/client'
import Header from './components/Header'
import PlanetMap from './components/PlanetMap'
import TilePanel from './components/TilePanel'
import { isAbortError, toMessage } from './lib/errors'
import type {
  BodyConfig,
  BodyId,
  SelectedTile,
  TileResponse,
} from './types'

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

  const body = bodies.find((candidate) => candidate.id === bodyId) ?? null

  function handleSelect(next: SelectedTile) {
    setSelected(next)
    setTile(null)
    setTileError(null)
    setTileLoading(true)
  }

  function handleBodyChange(id: BodyId) {
    if (id === bodyId) {
      return
    }
    setBodyId(id)
    setSelected(null)
    setTile(null)
    setTileError(null)
    setTileLoading(false)
  }

  function handleRetry() {
    setTileError(null)
    setTileLoading(true)
    setRetryNonce((value) => value + 1)
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
        onReset={() => setResetToken((value) => value + 1)}
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
              <PlanetMap
                body={body}
                selected={selected}
                showGrid={showGrid}
                resetToken={resetToken}
                onSelect={handleSelect}
              />
            ) : (
              <div className="map-placeholder">
                <span className="planet-loader" aria-hidden="true" />
                <p>{bodiesLoading ? 'Loading planetary basemap…' : 'No basemap available'}</p>
              </div>
            )}
          </section>

          <TilePanel
            body={body}
            selected={selected}
            tile={tile}
            loading={tileLoading}
            error={tileError}
            onRetry={handleRetry}
          />
        </main>
      )}
    </div>
  )
}
