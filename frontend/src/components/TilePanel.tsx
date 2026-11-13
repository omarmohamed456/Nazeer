import type { ReactNode } from 'react'

import { formatLat, formatLatLon, formatLon } from '../lib/tileMath'
import type { BodyConfig, SelectedTile, TileResponse } from '../types'
import EarthAnalog from './EarthAnalog'

interface TilePanelProps {
  body: BodyConfig | null
  selected: SelectedTile | null
  tile: TileResponse | null
  loading: boolean
  error: string | null
  onRetry: () => void
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function MetaRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="meta-row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}

function ExternalIcon() {
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
      <path d="M14 3h7v7" />
      <path d="M10 14 21 3" />
      <path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" />
    </svg>
  )
}

function TargetIcon() {
  return (
    <svg
      className="empty-icon"
      viewBox="0 0 48 48"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      aria-hidden="true"
    >
      <rect x="7" y="7" width="34" height="34" rx="3" opacity=".45" />
      <rect x="7" y="7" width="17" height="17" rx="2" fill="currentColor" opacity=".12" />
      <circle cx="24" cy="24" r="7" opacity=".9" />
      <circle cx="24" cy="24" r="2.2" fill="currentColor" stroke="none" />
      <path d="M24 3v7M24 38v7M3 24h7M38 24h7" opacity=".8" />
    </svg>
  )
}

function EmptyState({ bodyName }: { bodyName: string }) {
  return (
    <div className="empty-state">
      <TargetIcon />
      <h3>Pick a tile to begin</h3>
      <p>
        Click anywhere on the {bodyName.toLowerCase()} map. The tile beneath your
        cursor will be highlighted and its details will appear here.
      </p>
      <ul className="empty-tips">
        <li>Scroll to zoom in or out</li>
        <li>Turn on the tile grid for exact boundaries</li>
        <li>Switch bodies from the header</li>
      </ul>
    </div>
  )
}

function LoadingState({ selected }: { selected: SelectedTile }) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <div className="loading-coords">
        z{selected.z} · x{selected.x} · y{selected.y}
      </div>
      <div className="skeleton skeleton-preview" />
      <div className="skeleton skeleton-line" />
      <div className="skeleton skeleton-line short" />
      <span className="sr-only">Loading tile data…</span>
    </div>
  )
}

function TileDetails({ tile }: { tile: TileResponse }) {
  const { analysis, approx_size_km: size, bounds, layer } = tile

  return (
    <div className="tile-details">
      <a
        className="tile-preview"
        href={tile.image_url}
        target="_blank"
        rel="noreferrer"
        title="Open the raw NASA tile in a new tab"
      >
        <img
          src={tile.image_url}
          alt={`${tile.body_name} imagery at zoom ${tile.tile.z}, column ${tile.tile.x}, row ${tile.tile.y}`}
        />
        <span className="preview-tag">
          z{tile.tile.z} · x{tile.tile.x} · y{tile.tile.y}
        </span>
        <span className="preview-open" aria-hidden="true">
          <ExternalIcon />
        </span>
      </a>

      <div className="tile-source">
        <span>{layer.title}</span>
        <span className="source-dot" aria-hidden="true" />
        <span>{layer.resolution}</span>
      </div>

      <div className="tile-stats">
        <Stat label="Zoom" value={String(tile.tile.z)} />
        <Stat label="Column" value={String(tile.tile.x)} />
        <Stat label="Row" value={String(tile.tile.y)} />
      </div>

      <dl className="meta-list">
        <MetaRow
          label="Center"
          value={formatLatLon(tile.center.lat, tile.center.lon)}
        />
        <MetaRow
          label="Longitude"
          value={`${formatLon(bounds.west)} → ${formatLon(bounds.east)}`}
        />
        <MetaRow
          label="Latitude"
          value={`${formatLat(bounds.south)} → ${formatLat(bounds.north)}`}
        />
        <MetaRow
          label="Approx. size"
          value={`${Math.round(size.width).toLocaleString()} × ${Math.round(
            size.height,
          ).toLocaleString()} km`}
        />
        <MetaRow label="Instrument" value={layer.instrument} />
      </dl>

      <div className="section-heading">
        <div>
          <span className="eyebrow">Analysis</span>
          <h3>Tile profile</h3>
        </div>
        <span className="badge badge-sim">Simulated</span>
      </div>

      <div className="analysis-grid">
        {analysis.fields.map((field) => (
          <div className="analysis-item" key={field.label}>
            <span>{field.label}</span>
            <strong>
              {field.value}
              {field.unit ? <em>{field.unit}</em> : null}
            </strong>
          </div>
        ))}
      </div>

      <div className="confidence">
        <div className="confidence-label">
          <span>Model confidence (simulated)</span>
          <b>{analysis.confidence_pct}%</b>
        </div>
        <div className="confidence-bar">
          <span style={{ width: `${analysis.confidence_pct}%` }} />
        </div>
      </div>

      <p className="panel-note">
        These values are generated deterministically from the tile coordinates.
        They are placeholders, not science data.
      </p>
    </div>
  )
}

export default function TilePanel({
  body,
  selected,
  tile,
  loading,
  error,
  onRetry,
}: TilePanelProps) {
  return (
    <aside className="tile-panel" aria-label="Tile inspector">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Tile inspector</span>
          <h2>{body ? body.name : '—'}</h2>
        </div>
        {body && <span className="body-chip">{body.tagline}</span>}
      </div>

      <div className="panel-scroll">
        {!body ? (
          <div className="loading-state" aria-busy="true">
            <div className="skeleton skeleton-preview" />
            <div className="skeleton skeleton-line" />
            <div className="skeleton skeleton-line short" />
          </div>
        ) : error ? (
          <div className="error-card" role="alert">
            <p>{error}</p>
            <button type="button" className="secondary-button" onClick={onRetry}>
              Try again
            </button>
          </div>
        ) : !selected ? (
          <EmptyState bodyName={body.name} />
        ) : loading || !tile ? (
          <LoadingState selected={selected} />
        ) : (
          <TileDetails tile={tile} />
        )}

        <EarthAnalog
          key={
            selected
              ? `${selected.body}:${selected.z}:${selected.x}:${selected.y}`
              : 'none'
          }
          body={body}
          selected={selected}
        />
      </div>

      <footer className="panel-footer">
        <span>Imagery served by NASA · simulated fields are placeholders.</span>
        <span>Prototype · not affiliated with NASA</span>
      </footer>
    </aside>
  )
}
