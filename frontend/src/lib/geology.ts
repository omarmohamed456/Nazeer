import type { BodyId, ClassShare, TileBounds } from '../types'

const CLASS_COLORS: Record<string, string> = {
  volcanic: '#ff8a5c',
  crystalline: '#9ec1ff',
  highlands: '#c6d8f5',
  plains: '#a8b6cc',
  sedimentary: '#e8c97a',
  surficial: '#b7a6ff',
  surficial_unconsolidated: '#b7a6ff',
  ice: '#8fe3f2',
  impact: '#ff6b8a',
  undivided: '#7d8aa3',
  undivided_terrain: '#7d8aa3',
  metamorphic: '#8fa8d8',
  plutonic: '#6f8fc9',
  water: '#4d8fd6',
  no_data: '#4a5365',
}

const AGE_COLORS = [
  '#ffb86b',
  '#ff8a5c',
  '#e8c97a',
  '#9ec1ff',
  '#8fa8d8',
  '#b7a6ff',
  '#8fe3f2',
  '#c6d8f5',
]

const MOON_CLASS_LABELS: Record<string, string> = {
  volcanic: 'Volcanic',
  impact: 'Impact',
  highlands: 'Highlands',
  plains: 'Plains',
}

const MARS_CLASS_LABELS: Record<string, string> = {
  volcanic: 'Volcanic',
  impact: 'Impact',
  surficial_unconsolidated: 'Surficial',
  undivided_terrain: 'Undivided terrain',
  ice: 'Ice',
}

const EARTH_CLASS_LABELS: Record<string, string> = {
  volcanic: 'Volcanic',
  crystalline: 'Crystalline',
  metamorphic: 'Metamorphic',
  plutonic: 'Plutonic',
  sedimentary: 'Sedimentary',
  surficial_unconsolidated: 'Surficial',
  ice: 'Ice',
  water: 'Water',
  no_data: 'No data',
}

function fallbackLabel(key: string): string {
  return key
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

export function classColor(key: string): string {
  return CLASS_COLORS[key] ?? '#8b96ad'
}

export function ageColor(index: number): string {
  return AGE_COLORS[index % AGE_COLORS.length]
}

export function bodyClassLabel(body: BodyId, key: string): string {
  const labels = body === 'moon' ? MOON_CLASS_LABELS : MARS_CLASS_LABELS
  return labels[key] ?? fallbackLabel(key)
}

export function earthClassLabel(key: string): string {
  return EARTH_CLASS_LABELS[key] ?? fallbackLabel(key)
}

const EARTH_CLASS_FAMILIES: Record<string, string> = {
  volcanic: 'volcanic',
  crystalline: 'crystalline',
  metamorphic: 'crystalline',
  plutonic: 'crystalline',
  sedimentary: 'sedimentary',
  surficial_unconsolidated: 'surficial',
  ice: 'ice',
}

export function earthTerrainLabel(
  dominant: string,
  matchDominant: string,
): string {
  const sourceFamily = EARTH_CLASS_FAMILIES[dominant] ?? dominant
  const matchFamily = EARTH_CLASS_FAMILIES[matchDominant] ?? matchDominant
  if (sourceFamily === matchFamily) {
    return earthClassLabel(dominant)
  }
  return `${earthClassLabel(dominant)} / ${earthClassLabel(matchDominant)}`
}

export function clampFraction(value: number): number {
  return Math.max(0, Math.min(1, value))
}

export function formatPercent(fraction: number, digits = 0): string {
  const percent = clampFraction(fraction) * 100
  if (digits === 0 && percent > 0 && percent < 1) {
    return '<1%'
  }
  return `${percent.toFixed(digits)}%`
}

export function topShares(shares: ClassShare[], limit = 5): ClassShare[] {
  return [...shares].sort((a, b) => b.fraction - a.fraction).slice(0, limit)
}

export function datasetCellIdsLabel(ids: string[], limit = 3): string {
  if (ids.length <= limit) {
    return ids.join(', ')
  }
  return `${ids.slice(0, limit).join(', ')} +${ids.length - limit} more`
}

export function overlayStyle(
  bounds: TileBounds,
  preview: TileBounds,
): { left: string; top: string; width: string; height: string } {
  const width = preview.east - preview.west
  const height = preview.north - preview.south
  const left = ((bounds.west - preview.west) / width) * 100
  const top = ((preview.north - bounds.north) / height) * 100
  const rectWidth = ((bounds.east - bounds.west) / width) * 100
  const rectHeight = ((bounds.north - bounds.south) / height) * 100

  return {
    left: `${Math.max(0, Math.min(100, left))}%`,
    top: `${Math.max(0, Math.min(100, top))}%`,
    width: `${Math.max(0, Math.min(100, rectWidth))}%`,
    height: `${Math.max(0, Math.min(100, rectHeight))}%`,
  }
}
