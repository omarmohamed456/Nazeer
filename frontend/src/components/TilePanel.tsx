import type { ReactNode } from 'react'

import {
  bodyClassLabel,
  datasetCellIdsLabel,
  formatPercent,
} from '../lib/geology'
import { formatLat, formatLatLon, formatLon } from '../lib/tileMath'
import type {
  AgeSummary,
  BodyConfig,
  GeologySummary,
  MatchResponse,
  SelectedTile,
  TileResponse,
} from '../types'
import ClassBars from './ClassBars'
import EarthMatch from './EarthMatch'

interface TilePanelProps {
  body: BodyConfig | null
  selected: SelectedTile | null
  tile: TileResponse | null
  loading: boolean
  error: string | null
  onRetry: () => void
  match: MatchResponse | null
  matchLoading: boolean
  matchError: string | null
  matchDisabledReason: string | null
  onMatchRetry: () => void
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
      <h3>Pick a tile or enter coordinates</h3>
      <p>
        Click anywhere on the {bodyName.toLowerCase()} map or use the coordinate
        bar. The 10° geology cell and its closest Earth analog will appear here.
      </p>
      <ul className="empty-tips">
        <li>Click a tile for an area-weighted match</li>
        <li>Enter lat/lon for a single 10° cell</li>
        <li>Zoom to level 2 or deeper for a meaningful match</li>
      </ul>
    </div>
  )
}

function LoadingState({ selected }: { selected: SelectedTile }) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <div className="loading-coords">
        {selected.kind === 'point' &&
        selected.lat != null &&
        selected.lon != null
          ? formatLatLon(selected.lat, selected.lon, 4)
          : `z${selected.z} · x${selected.x} · y${selected.y}`}
      </div>
      <div className="skeleton skeleton-preview" />
      <div className="skeleton skeleton-line" />
      <div className="skeleton skeleton-line short" />
      <span className="sr-only">Loading tile data…</span>
    </div>
  )
}

function AgeBlock({ age }: { age: AgeSummary }) {
  return (
    <div className="age-block">
      <div className="age-head">
        <span>Age</span>
        <strong>{age.dominant?.label ?? '—'}</strong>
      </div>
      <ClassBars
        shares={age.classes}
        limit={4}
        variant="age"
        ariaLabel="Age composition"
      />
      <div className="age-meta">
        {age.mean_min_ga != null && age.mean_max_ga != null && (
          <span>
            Mean {age.mean_min_ga.toFixed(2)}–{age.mean_max_ga.toFixed(2)} Ga
          </span>
        )}
        {age.surely_old_fraction != null && (
          <span>{formatPercent(age.surely_old_fraction)} &gt;3.5 Ga</span>
        )}
        {age.surely_young_fraction != null && (
          <span>{formatPercent(age.surely_young_fraction)} &lt;1 Ga</span>
        )}
      </div>
      <p className="panel-note">Age fractions from the supplied 10° dataset.</p>
    </div>
  )
}

function GeologySection({
  body,
  geology,
  note,
}: {
  body: BodyConfig
  geology: GeologySummary | null
  note: string
}) {
  return (
    <section className="geology-section" aria-labelledby="geology-title">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Geology</span>
          <h3 id="geology-title">Surface composition</h3>
        </div>
        <span className="badge badge-data">10° data</span>
      </div>

      {!geology ? (
        <div className="loading-state" role="status" aria-live="polite">
          <div className="skeleton skeleton-line" />
          <div className="skeleton skeleton-line short" />
          <span className="sr-only">Loading geology…</span>
        </div>
      ) : (
        <>
          <dl className="meta-list">
            <MetaRow
              label="Dataset cell"
              value={datasetCellIdsLabel(geology.dataset_tile_ids)}
            />
            <MetaRow
              label="Resolution"
              value={`${geology.resolution_deg}° × ${geology.resolution_deg}°`}
            />
            <MetaRow
              label="Mapped"
              value={formatPercent(geology.mapped_fraction, 1)}
            />
            <MetaRow
              label="Dominant"
              value={bodyClassLabel(body.id, geology.dominant_class)}
            />
          </dl>

          <ClassBars
            shares={geology.classes}
            limit={5}
            ariaLabel={`${body.name} geology composition`}
          />

          {geology.age && <AgeBlock age={geology.age} />}

          <p className="panel-note">{note}</p>
          <p className="panel-note">
            {body.id === 'moon'
              ? 'Earth comparison: highlands → crystalline crust, plains → sedimentary, volcanic → volcanic; impact has no Earth equivalent.'
              : 'Earth comparison: volcanic → volcanic, ice → ice, surficial → surficial; undivided terrain and impact have no Earth equivalent.'}
          </p>
        </>
      )}
    </section>
  )
}

function TileDetails({
  body,
  selected,
  tile,
  match,
  matchError,
}: {
  body: BodyConfig
  selected: SelectedTile
  tile: TileResponse
  match: MatchResponse | null
  matchError: string | null
}) {
  const isPoint = selected.kind === 'point'
  const geology = isPoint
    ? match?.target.geology ?? tile.geology
    : tile.geology
  const geologyNote = isPoint
    ? match
      ? 'Composition of the 10° dataset cell containing the point.'
      : matchError
        ? 'Point cell unavailable; showing the containing map tile.'
        : 'Showing the containing map tile while the point cell loads.'
    : `Area-weighted composition of ${tile.geology.dataset_tile_ids.length} overlapping 10° dataset cell${
        tile.geology.dataset_tile_ids.length === 1 ? '' : 's'
      }.`

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
        <span>{tile.layer.title}</span>
        <span className="source-dot" aria-hidden="true" />
        <span>{tile.layer.resolution}</span>
      </div>

      <div className="tile-stats">
        <Stat label="Zoom" value={String(tile.tile.z)} />
        <Stat label="Column" value={String(tile.tile.x)} />
        <Stat label="Row" value={String(tile.tile.y)} />
      </div>

      <dl className="meta-list">
        {selected.lat != null && selected.lon != null && (
          <MetaRow
            label={isPoint ? 'Point' : 'Clicked at'}
            value={formatLatLon(selected.lat, selected.lon, 4)}
          />
        )}
        <MetaRow
          label="Center"
          value={formatLatLon(tile.center.lat, tile.center.lon)}
        />
        <MetaRow
          label="Longitude"
          value={`${formatLon(tile.bounds.west)} → ${formatLon(tile.bounds.east)}`}
        />
        <MetaRow
          label="Latitude"
          value={`${formatLat(tile.bounds.south)} → ${formatLat(tile.bounds.north)}`}
        />
        <MetaRow
          label="Approx. size"
          value={`${Math.round(tile.approx_size_km.width).toLocaleString()} × ${Math.round(
            tile.approx_size_km.height,
          ).toLocaleString()} km`}
        />
        <MetaRow label="Instrument" value={tile.layer.instrument} />
      </dl>

      <GeologySection
        body={body}
        geology={geology}
        note={geologyNote}
      />
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
  match,
  matchLoading,
  matchError,
  matchDisabledReason,
  onMatchRetry,
}: TilePanelProps) {
  return (
    <aside className="tile-panel" aria-label="Tile inspector">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Inspector</span>
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
        ) : !selected ? (
          <EmptyState bodyName={body.name} />
        ) : (
          <>
            <EarthMatch
              body={body}
              selected={selected}
              match={match}
              loading={matchLoading}
              error={matchError}
              disabledReason={matchDisabledReason}
              onRetry={onMatchRetry}
            />

            <div className="panel-divider" />

            {error ? (
              <div className="error-card" role="alert">
                <p>{error}</p>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={onRetry}
                >
                  Try again
                </button>
              </div>
            ) : loading || !tile ? (
              <LoadingState selected={selected} />
            ) : (
              <TileDetails
                body={body}
                selected={selected}
                tile={tile}
                match={match}
                matchError={matchError}
              />
            )}
          </>
        )}
      </div>

      <footer className="panel-footer">
        <span>Imagery served by NASA · geology matching is a heuristic prototype.</span>
        <span>Not affiliated with NASA</span>
      </footer>
    </aside>
  )
}
