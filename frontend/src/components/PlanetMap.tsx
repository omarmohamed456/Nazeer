import type { LatLngBoundsExpression } from 'leaflet'
import { CRS } from 'leaflet'
import { useEffect, useMemo, useState } from 'react'
import {
  MapContainer,
  Rectangle,
  TileLayer,
  ZoomControl,
  useMap,
  useMapEvents,
} from 'react-leaflet'

import { BODY_ACCENTS } from '../lib/theme'
import {
  formatLatLon,
  isInsideWorld,
  tileAtLatLng,
  tileBounds,
} from '../lib/tileMath'
import type { BodyConfig, BodyId, SelectedTile } from '../types'

const WORLD_BOUNDS: LatLngBoundsExpression = [
  [-90, -180],
  [90, 180],
]

interface HoverInfo {
  lat: number
  lon: number
  z: number
  x: number
  y: number
}

interface PlanetMapProps {
  body: BodyConfig
  selected: SelectedTile | null
  showGrid: boolean
  resetToken: number
  onSelect: (tile: SelectedTile) => void
}

function FitWorld({ resetToken }: { resetToken: number }) {
  const map = useMap()

  useEffect(() => {
    if (resetToken === 0) {
      return
    }
    map.invalidateSize()
    map.fitBounds(WORLD_BOUNDS, { padding: [4, 4], animate: false })
  }, [map, resetToken])

  return null
}

function BodyZoomLimit({ maxZoom }: { maxZoom: number }) {
  const map = useMap()

  useEffect(() => {
    map.setMaxZoom(maxZoom)
    if (map.getZoom() > maxZoom) {
      map.setZoom(maxZoom)
    }
  }, [map, maxZoom])

  return null
}

function MapInteraction({
  bodyId,
  maxZoom,
  onSelect,
  onHover,
}: {
  bodyId: BodyId
  maxZoom: number
  onSelect: (tile: SelectedTile) => void
  onHover: (hover: HoverInfo | null) => void
}) {
  const map = useMap()

  const readPoint = (lat: number, lon: number): HoverInfo | null => {
    if (!isInsideWorld(lat, lon)) {
      return null
    }
    const z = Math.min(maxZoom, Math.max(0, Math.round(map.getZoom())))
    return { lat, lon, ...tileAtLatLng(lat, lon, z) }
  }

  useMapEvents({
    click(event) {
      const point = readPoint(event.latlng.lat, event.latlng.lng)
      if (!point) {
        return
      }
      onSelect({
        body: bodyId,
        z: point.z,
        x: point.x,
        y: point.y,
      })
    },
    mousemove(event) {
      onHover(readPoint(event.latlng.lat, event.latlng.lng))
    },
    mouseout() {
      onHover(null)
    },
  })

  return null
}

export default function PlanetMap({
  body,
  selected,
  showGrid,
  resetToken,
  onSelect,
}: PlanetMapProps) {
  const [hover, setHover] = useState<HoverInfo | null>(null)

  const selectionBounds = useMemo<LatLngBoundsExpression | null>(() => {
    if (!selected) {
      return null
    }
    const bounds = tileBounds(selected.z, selected.x, selected.y)
    return [
      [bounds.south, bounds.west],
      [bounds.north, bounds.east],
    ]
  }, [selected])

  const accent = BODY_ACCENTS[body.id]

  return (
    <div className={`map-shell${showGrid ? ' show-grid' : ''}`}>
      <MapContainer
        className="planet-map"
        crs={CRS.EPSG4326}
        center={[0, 0]}
        zoom={2}
        minZoom={0}
        maxZoom={body.max_zoom}
        zoomControl={false}
        attributionControl={false}
        worldCopyJump={false}
        zoomSnap={1}
      >
        <TileLayer
          key={body.id}
          url={body.tile_url_template}
          className="tile-base"
          bounds={WORLD_BOUNDS}
          noWrap
          maxNativeZoom={body.max_zoom}
          detectRetina={false}
        />

        {selectionBounds && (
          <Rectangle
            bounds={selectionBounds}
            pathOptions={{
              color: accent,
              weight: 2.5,
              dashArray: '7 5',
              fillColor: accent,
              fillOpacity: 0.07,
            }}
            interactive={false}
          />
        )}

        <MapInteraction
          bodyId={body.id}
          maxZoom={body.max_zoom}
          onSelect={onSelect}
          onHover={setHover}
        />
        <BodyZoomLimit maxZoom={body.max_zoom} />
        <FitWorld resetToken={resetToken} />

        <ZoomControl position="bottomright" />
      </MapContainer>

      <div className="map-attribution">
        <a
          href="https://leafletjs.com"
          target="_blank"
          rel="noopener noreferrer"
        >
          Leaflet
        </a>
        <span aria-hidden="true">·</span>
        <a
          href={body.attribution_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          {body.attribution}
        </a>
      </div>

      {hover && (
        <div className="map-readout" aria-hidden="true">
          <span className="readout-tile">
            z{hover.z} · x{hover.x} · y{hover.y}
          </span>
          <span className="readout-coords">
            {formatLatLon(hover.lat, hover.lon)}
          </span>
        </div>
      )}

      <div className="map-hint">
        Click any tile to inspect it · drag to pan · scroll to zoom
      </div>
    </div>
  )
}
