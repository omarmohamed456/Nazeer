import { useEffect, useRef, useState } from 'react'

import { fetchEarthAnalog } from '../api/client'
import { isAbortError, toMessage } from '../lib/errors'
import { formatLatLon } from '../lib/tileMath'
import type { BodyConfig, EarthAnalog as EarthAnalogData, SelectedTile } from '../types'

interface EarthAnalogProps {
  body: BodyConfig | null
  selected: SelectedTile | null
}

function SearchIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="7" />
      <path d="m16.5 16.5 4 4" />
    </svg>
  )
}

function ShuffleIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M16 3h5v5" />
      <path d="M4 20 21 3" />
      <path d="M21 16v5h-5" />
      <path d="m15 15 6 6" />
      <path d="m4 4 5 5" />
    </svg>
  )
}

export default function EarthAnalog({ body, selected }: EarthAnalogProps) {
  const [data, setData] = useState<EarthAnalogData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const cardRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  useEffect(() => {
    if (data) {
      cardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [data])

  async function search() {
    if (!selected) {
      return
    }

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setLoading(true)
    setError(null)
    setData(null)

    try {
      const result = await fetchEarthAnalog(controller.signal)
      if (!controller.signal.aborted) {
        setData(result)
      }
    } catch (err) {
      if (!controller.signal.aborted && !isAbortError(err)) {
        setError(toMessage(err))
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false)
      }
    }
  }

  return (
    <section className="earth-section" aria-labelledby="earth-analog-title">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Earth analog</span>
          <h3 id="earth-analog-title">Find a similar place</h3>
        </div>
        <span className="badge badge-prototype">Prototype</span>
      </div>

      <p className="earth-context">
        {selected
          ? `A placeholder comparison for your ${body?.name ?? 'planet'} tile. Real similarity matching is not wired up yet.`
          : 'Select a tile on the planet map to enable the Earth comparison.'}
      </p>

      {!data && !loading && (
        <button
          type="button"
          className="primary-button"
          onClick={search}
          disabled={!selected}
        >
          <SearchIcon />
          {selected ? 'Find similar on Earth' : 'Select a planet tile first'}
        </button>
      )}

      {loading && (
        <div className="earth-loading" role="status">
          <span className="spinner" aria-hidden="true" />
          Searching Earth…
        </div>
      )}

      {error && (
        <div className="inline-error" role="alert">
          <p>{error}</p>
          <button type="button" className="secondary-button" onClick={search}>
            Try again
          </button>
        </div>
      )}

      {data && !loading && (
        <div className="earth-card" ref={cardRef}>
          <a
            className="earth-preview"
            href={data.image_url}
            target="_blank"
            rel="noreferrer"
            title="Open the raw NASA Blue Marble tile"
          >
            <img
              src={data.image_url}
              alt={`Random Earth imagery tile at zoom ${data.tile.z}`}
              loading="lazy"
            />
            <span className="earth-coords">
              z{data.tile.z} · x{data.tile.x} · y{data.tile.y}
            </span>
          </a>

          <div className="earth-meta">
            <div className="match-line">
              <span className="match-pct">{data.match_pct}%</span>
              <span>simulated match</span>
            </div>
            <p className="earth-terrain">Random Blue Marble tile</p>
            <p className="earth-center">
              {formatLatLon(data.center.lat, data.center.lon, 1)}
            </p>
            <p className="earth-size">
              ≈ {Math.round(data.approx_size_km.width).toLocaleString()} km wide
            </p>
          </div>

          <button type="button" className="secondary-button" onClick={search}>
            <ShuffleIcon />
            Try another tile
          </button>

          <p className="disclaimer">
            {data.note}{' '}
            <a
              href="https://gibs.earthdata.nasa.gov/"
              target="_blank"
              rel="noopener noreferrer"
            >
              NASA GIBS
            </a>
          </p>
        </div>
      )}
    </section>
  )
}
