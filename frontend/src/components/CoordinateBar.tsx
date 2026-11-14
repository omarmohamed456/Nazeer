import { useEffect, useState, type FormEvent } from 'react'

import { parseCoordinatePair } from '../lib/coordinates'

interface CoordinateBarProps {
  bodyName: string
  lat: string
  lon: string
  onLatChange: (value: string) => void
  onLonChange: (value: string) => void
  onSubmit: (lat: number, lon: number) => void
  disabled?: boolean
}

interface FormError {
  field: 'lat' | 'lon'
  message: string
}

function GoIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 12h15" />
      <path d="m13 6 6 6-6 6" />
    </svg>
  )
}

export default function CoordinateBar({
  bodyName,
  lat,
  lon,
  onLatChange,
  onLonChange,
  onSubmit,
  disabled = false,
}: CoordinateBarProps) {
  const [error, setError] = useState<FormError | null>(null)

  useEffect(() => {
    setError(null)
  }, [lat, lon])

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const parsed = parseCoordinatePair(lat, lon)
    if (!parsed.ok) {
      setError({ field: parsed.field, message: parsed.message })
      return
    }
    setError(null)
    onSubmit(parsed.lat, parsed.lon)
  }

  return (
    <form
      className="coordinate-bar"
      onSubmit={handleSubmit}
      aria-label={`${bodyName} coordinate entry`}
    >
      <div className="coordinate-label">
        <span className="eyebrow">Coordinates</span>
        <span className="coordinate-help">Decimal degrees · east-positive</span>
      </div>

      <label
        className={`coordinate-field${error?.field === 'lat' ? ' has-error' : ''}`}
      >
        <span>Lat</span>
        <input
          type="text"
          inputMode="decimal"
          value={lat}
          onChange={(event) => {
            onLatChange(event.target.value)
            setError(null)
          }}
          placeholder="e.g. 12.5"
          aria-label={`${bodyName} latitude`}
          aria-invalid={error?.field === 'lat'}
          autoComplete="off"
          spellCheck={false}
        />
      </label>

      <label
        className={`coordinate-field${error?.field === 'lon' ? ' has-error' : ''}`}
      >
        <span>Lon</span>
        <input
          type="text"
          inputMode="decimal"
          value={lon}
          onChange={(event) => {
            onLonChange(event.target.value)
            setError(null)
          }}
          placeholder="e.g. -45.2"
          aria-label={`${bodyName} longitude`}
          aria-invalid={error?.field === 'lon'}
          autoComplete="off"
          spellCheck={false}
        />
      </label>

      <button type="submit" className="coordinate-go" disabled={disabled}>
        <GoIcon />
        Go
      </button>

      {error && (
        <p className="coordinate-error" role="alert">
          {error.message}
        </p>
      )}
    </form>
  )
}
