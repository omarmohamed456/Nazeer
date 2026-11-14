import { ageColor, classColor, formatPercent, topShares } from '../lib/geology'
import type { ClassShare } from '../types'

interface ClassBarsProps {
  shares: ClassShare[]
  limit?: number
  variant?: 'class' | 'age'
  ariaLabel?: string
  emptyLabel?: string
}

export default function ClassBars({
  shares,
  limit = 5,
  variant = 'class',
  ariaLabel,
  emptyLabel = 'No composition data',
}: ClassBarsProps) {
  if (shares.length === 0) {
    return <p className="class-empty">{emptyLabel}</p>
  }

  const stackShares = topShares(shares, 8)
  const legendShares = topShares(shares, limit)
  const total = stackShares.reduce((sum, share) => sum + share.fraction, 0) || 1
  const label =
    ariaLabel ??
    `Composition: ${legendShares
      .map((share) => `${share.label} ${formatPercent(share.fraction)}`)
      .join(', ')}`

  function colorFor(share: ClassShare, index: number): string {
    return variant === 'age' ? ageColor(index) : classColor(share.key)
  }

  return (
    <div className="class-bars">
      <div className="class-stack" role="img" aria-label={label}>
        {stackShares.map((share, index) => (
          <span
            key={share.key}
            style={{
              width: `${Math.max((share.fraction / total) * 100, 1)}%`,
              background: colorFor(share, index),
            }}
            title={`${share.label}: ${formatPercent(share.fraction)}`}
          />
        ))}
      </div>

      <ul className="class-legend">
        {legendShares.map((share, index) => (
          <li key={share.key}>
            <i
              style={{ background: colorFor(share, index) }}
              aria-hidden="true"
            />
            <span>{share.label}</span>
            <b>{formatPercent(share.fraction)}</b>
          </li>
        ))}
      </ul>

      {shares.length > limit && (
        <p className="class-more">+{shares.length - limit} smaller classes</p>
      )}
    </div>
  )
}
