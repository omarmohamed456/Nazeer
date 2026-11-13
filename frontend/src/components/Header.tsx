import type { BodyConfig, BodyId } from '../types'

interface HeaderProps {
  bodies: BodyConfig[]
  bodiesLoading: boolean
  bodyId: BodyId
  onBodyChange: (id: BodyId) => void
  showGrid: boolean
  onToggleGrid: () => void
  onReset: () => void
}

export default function Header({
  bodies,
  bodiesLoading,
  bodyId,
  onBodyChange,
  showGrid,
  onToggleGrid,
  onReset,
}: HeaderProps) {
  return (
    <header className="app-header">
      <div className="brand">
        <svg
          className="brand-mark"
          viewBox="0 0 48 48"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="24" cy="24" r="8" fill="currentColor" />
          <ellipse
            cx="24"
            cy="24"
            rx="18"
            ry="7"
            stroke="currentColor"
            strokeWidth="1.6"
            opacity=".65"
            transform="rotate(-24 24 24)"
          />
          <circle cx="39" cy="14" r="2.6" fill="#ff9a6b" />
        </svg>
        <div className="brand-text">
          <h1>Planet Explorer</h1>
          <p>NASA Trek tile atlas</p>
        </div>
      </div>

      <div className="header-tools">
        <div className="body-switch" role="group" aria-label="Solar system body">
          {bodies.length === 0 ? (
            <span className="body-switch-loading">
              {bodiesLoading ? 'Loading bodies…' : 'No bodies available'}
            </span>
          ) : (
            bodies.map((body) => (
              <button
                key={body.id}
                type="button"
                className={`body-option${bodyId === body.id ? ' is-active' : ''}`}
                aria-pressed={bodyId === body.id}
                onClick={() => onBodyChange(body.id)}
              >
                <span className={`body-dot body-dot-${body.id}`} aria-hidden="true" />
                {body.name}
              </button>
            ))
          )}
        </div>

        <label className="switch">
          <input type="checkbox" checked={showGrid} onChange={onToggleGrid} />
          <span className="switch-track" aria-hidden="true">
            <span className="switch-thumb" />
          </span>
          <span>Tile grid</span>
        </label>

        <button type="button" className="ghost-button" onClick={onReset}>
          Reset view
        </button>
      </div>
    </header>
  )
}
