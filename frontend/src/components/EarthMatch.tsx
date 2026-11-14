import { useId } from 'react'

import {
  earthTerrainLabel,
  formatPercent,
  overlayStyle,
} from '../lib/geology'
import { formatLatLon } from '../lib/tileMath'
import type {
  BodyConfig,
  ConfidenceLevel,
  EarthCandidate,
  MatchResponse,
  MatchStatus,
  SelectedTile,
} from '../types'
import ClassBars from './ClassBars'

interface EarthMatchProps {
  body: BodyConfig | null
  selected: SelectedTile | null
  match: MatchResponse | null
  loading: boolean
  error: string | null
  disabledReason: string | null
  onRetry: () => void
}

function statusTitle(status: MatchStatus): string {
  if (status === 'match') {
    return 'Analog match'
  }
  if (status === 'weak') {
    return 'Weak analog'
  }
  return 'No reliable analog'
}

function confidenceTitle(confidence: ConfidenceLevel): string {
  if (confidence === 'high') {
    return 'High confidence'
  }
  if (confidence === 'medium') {
    return 'Medium confidence'
  }
  if (confidence === 'low') {
    return 'Low confidence'
  }
  return 'Insufficient confidence'
}

function StatusBadge({ status }: { status: MatchStatus }) {
  return (
    <span className={`badge badge-${status}`}>
      {statusTitle(status)}
    </span>
  )
}

function CandidatePreview({
  candidate,
  compact = false,
}: {
  candidate: EarthCandidate
  compact?: boolean
}) {
  const style = overlayStyle(candidate.bounds, candidate.preview_bounds)

  return (
    <a
      className={`earth-preview${compact ? ' earth-preview-compact' : ''}`}
      href={candidate.preview_url}
      target="_blank"
      rel="noreferrer"
      title="Open the NASA GIBS preview in a new tab"
    >
      <img
        src={candidate.preview_url}
        alt={`NASA Blue Marble preview around Earth tile ${candidate.dataset_tile_id}`}
        loading="lazy"
      />
      <span className="earth-cell-overlay" style={style} aria-hidden="true" />
      {!compact && (
        <span className="earth-coords">{candidate.dataset_tile_id}</span>
      )}
    </a>
  )
}

function MatchContent({
  body,
  match,
}: {
  body: BodyConfig | null
  match: MatchResponse
}) {
  const { target, match: result } = match
  const top = result.candidates[0] ?? null
  const bestSimilarity = result.candidates.length
    ? Math.max(...result.candidates.map((candidate) => candidate.similarity))
    : 0

  return (
    <>
      <div className="match-score">
        <span className="match-score-value">
          {Math.round(result.confidence_score)}%
        </span>
        <div className="match-score-copy">
          <strong>{statusTitle(result.status)}</strong>
          <span>{confidenceTitle(result.confidence)}</span>
        </div>
      </div>

      <p className="match-reason">{result.reason}</p>

      <div className="match-facts">
        <div>
          <span>Shared classes</span>
          <b>{formatPercent(result.shared_mass)}</b>
        </div>
        <div>
          <span>Analog similarity</span>
          <b>{formatPercent(result.similarity)}</b>
        </div>
        <div>
          <span>Earth tile coverage</span>
          <b>{formatPercent(result.coverage)}</b>
        </div>
      </div>

      <p className="match-target">
        {target.kind === 'point' && target.point
          ? `Point ${formatLatLon(target.point.lat, target.point.lon, 4)} · cell ${target.geology.dataset_tile_ids.join(', ')}`
          : `Tile z${target.tile?.z} · x${target.tile?.x} · y${target.tile?.y} · ${target.geology.dataset_tile_ids.length} dataset cells`}
      </p>

      {result.status === 'insufficient' && top && (
        <div className="match-warning" role="status">
          <strong>No reliable analog.</strong> The candidates below are the
          closest available tiles, shown for reference only.
        </div>
      )}

      {top ? (
        <>
          <div className="composition-compare">
            <div>
              <h4>{body?.name ?? 'Target'} comparable classes</h4>
              <ClassBars
                shares={target.geology.match_classes}
                limit={5}
                ariaLabel={`${body?.name ?? 'Target'} comparable geology composition`}
              />
            </div>
            <div>
              <h4>Earth candidate</h4>
              <ClassBars
                shares={top.match_classes}
                limit={5}
                ariaLabel={`Earth tile ${top.dataset_tile_id} comparable composition`}
              />
            </div>
          </div>

          <article className="earth-candidate">
            <CandidatePreview candidate={top} />
            <div className="earth-meta">
              <div className="match-line">
                <span className="match-pct">
                  {formatPercent(top.similarity)}
                </span>
                <span>composition similarity</span>
              </div>
              <p className="earth-terrain">
                {earthTerrainLabel(top.dominant_class, top.match_dominant_class)} ·{' '}
                {formatPercent(top.coverage)} mapped
              </p>
              {result.geographic_tiebreak && (
                <span
                  className="earth-tiebreak"
                  title="The featured tile is the geographically nearest of the closest composition matches. The highest-scoring tile is listed below."
                >
                  Geographic tie-break
                </span>
              )}
              <p className="earth-center">
                {formatLatLon(top.center.lat, top.center.lon, 1)}
              </p>
              <p className="earth-size">10° × 10° Earth dataset tile</p>
            </div>
          </article>

          {result.candidates.length > 1 && (
            <div className="earth-alts">
              <h4>Other close analogs</h4>
              {result.candidates.slice(1).map((candidate, index) => (
                <div className="earth-alt" key={candidate.dataset_tile_id}>
                  <span className="alt-rank">#{index + 2}</span>
                  <CandidatePreview candidate={candidate} compact />
                  <div className="alt-info">
                    <strong>
                      {candidate.dataset_tile_id} ·{' '}
                      {earthTerrainLabel(
                        candidate.dominant_class,
                        candidate.match_dominant_class,
                      )}
                    </strong>
                    <span>
                      {formatLatLon(candidate.center.lat, candidate.center.lon, 1)}{' '}
                      · {formatPercent(candidate.coverage)} mapped
                    </span>
                    {candidate.similarity >= bestSimilarity - 0.0001 &&
                      candidate.similarity > result.similarity + 0.0001 && (
                        <em className="alt-best">highest composition score</em>
                      )}
                  </div>
                  <span className="alt-score">
                    {formatPercent(candidate.similarity)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="match-empty">
          <strong>No Earth analog available</strong>
          <p>
            This target has no comparable Earth land tile in the supplied
            table. Choose a different tile or enter coordinates for a single
            10° cell.
          </p>
        </div>
      )}

      <ul className="match-notes">
        {match.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>

      <p className="disclaimer">
        Earth preview:{' '}
        <a
          href={match.preview_attribution_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          {match.preview_attribution}
        </a>
        . Imagery is loaded directly from NASA.
      </p>
    </>
  )
}

export default function EarthMatch({
  body,
  selected,
  match,
  loading,
  error,
  disabledReason,
  onRetry,
}: EarthMatchProps) {
  const titleId = useId()

  return (
    <section className="earth-section" aria-labelledby={titleId}>
      <div className="section-heading">
        <div>
          <span className="eyebrow">Earth analog</span>
          <h3 id={titleId}>Composition match</h3>
        </div>
        {match && <StatusBadge status={match.match.status} />}
      </div>

      {!selected && (
        <p className="earth-context">
          Select a tile or enter coordinates to compare its 10° geology with
          Earth land tiles.
        </p>
      )}

      {selected && disabledReason && (
        <div className="match-note">{disabledReason}</div>
      )}

      {selected && !disabledReason && loading && (
        <div className="earth-loading" role="status">
          <span className="spinner" aria-hidden="true" />
          Comparing geology with Earth…
        </div>
      )}

      {selected && !disabledReason && error && (
        <div className="inline-error" role="alert">
          <p>{error}</p>
          <button type="button" className="secondary-button" onClick={onRetry}>
            Try again
          </button>
        </div>
      )}

      {selected &&
        !disabledReason &&
        !loading &&
        !error &&
        !match && (
          <div className="earth-loading" role="status">
            <span className="spinner" aria-hidden="true" />
            Preparing match…
          </div>
        )}

      {selected && !disabledReason && !loading && !error && match && (
        <MatchContent body={body} match={match} />
      )}
    </section>
  )
}
