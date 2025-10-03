import { FeatureCollection } from 'geojson'
import { useMemo } from 'react'
import { LayerProps, MapStyle } from 'react-map-gl'

export const OPACITY_DEFAULT = 0.75
export const COLOR_NON_COMM = '#1C7ED6'
export const OPACITY_NON_COMM = 0.5

export const colorBar = ({
  colors,
}: {
  colors: { id: number; value: string }[]
}) => {
  return `linear-gradient(to top, ${colors
    .map((color) => color.value)
    .join(', ')})`
}

export const colorLinear = ({
  colors,
  lowValue,
  highValue,
}: {
  colors: { id: number; value: string }[]
  lowValue: number
  highValue: number
}) => {
  // Return an array in the format of [number, string, number, string, ...]
  // The first color should match to the lowValue, and the last color should match to the highValue
  // The colors in between should be evenly distributed
  const colorArray = colors.map((color) => color.value)
  const colorCount = colorArray.length
  const colorStep = (highValue - lowValue) / (colorCount - 1)
  const colorLinearArray = []
  for (let i = 0; i < colorCount; i++) {
    colorLinearArray.push(lowValue + i * colorStep)
    colorLinearArray.push(colorArray[i])
  }
  return colorLinearArray
}

const blankMapStyle: MapStyle = {
  version: 8,
  name: 'Empty',
  metadata: {
    'mapbox:autocomposite': true,
    'mapbox:type': 'template',
  },
  glyphs: 'mapbox://fonts/mapbox/{fontstack}/{range}.pbf',
  sources: {},
  layers: [
    {
      id: 'background',
      type: 'background',
      paint: {
        'background-color': 'rgba(0,0,0,0)',
      },
    },
  ],
}

export const useBlankMapStyle = () => useMemo(() => blankMapStyle, [])

/**
 * Find the bounding box of a GeoJSON feature collection
 * @param geojsonData - The GeoJSON feature collection
 * @returns The bounding box as an array of four numbers, [minLng, minLat, maxLng, maxLat]
 */
export function findBoundingBox(
  geojsonData: FeatureCollection,
): [number, number, number, number] {
  let minLat = Infinity
  let maxLat = -Infinity
  let minLng = Infinity
  let maxLng = -Infinity

  geojsonData.features.forEach((feature) => {
    const geometry = feature.geometry

    if (geometry.type === 'MultiPolygon') {
      // MultiPolygon coordinates: [polygon1, polygon2, ...]
      // Each polygon contains [exterior_ring, hole1, hole2, ...]
      const coordinates = geometry.coordinates as number[][][][]
      coordinates.forEach((polygon) => {
        polygon.forEach((ring) => {
          ring.forEach(([lng, lat]) => {
            if (lat < minLat) minLat = lat
            if (lat > maxLat) maxLat = lat
            if (lng < minLng) minLng = lng
            if (lng > maxLng) maxLng = lng
          })
        })
      })
    } else if (geometry.type === 'Polygon') {
      // Polygon coordinates: [exterior_ring, hole1, hole2, ...]
      const coordinates = geometry.coordinates as number[][][]
      coordinates.forEach((ring) => {
        ring.forEach(([lng, lat]) => {
          if (lat < minLat) minLat = lat
          if (lat > maxLat) maxLat = lat
          if (lng < minLng) minLng = lng
          if (lng > maxLng) maxLng = lng
        })
      })
    }
  })

  return [minLng, minLat, maxLng, maxLat]
}

export function layerData({
  featureKey,
  colors,
  lowValue,
  highValue,
}: {
  featureKey: string
  colors: { id: number; value: string }[]
  lowValue: number
  highValue: number
}): LayerProps {
  return {
    id: 'data',
    type: 'fill',
    paint: {
      'fill-color': [
        'case',
        ['==', ['get', featureKey], null],
        COLOR_NON_COMM, // Default color for null values
        [
          'interpolate',
          ['linear'],
          ['get', featureKey],
          ...colorLinear({
            colors,
            lowValue,
            highValue,
          }),
        ],
      ],
      'fill-opacity': [
        'case',
        ['==', ['get', featureKey], null],
        OPACITY_NON_COMM,
        OPACITY_DEFAULT,
      ],
    },
  }
}

export function layerLabel({
  textField = 'name',
  textRotate = 0,
}: {
  textField?: string
  textRotate?: number
}): LayerProps {
  return {
    id: 'labels',
    type: 'symbol',
    layout: {
      'text-field': ['get', textField],
      'text-size': 14,
      'text-rotate': textRotate,
    },
    paint: {
      'text-color': '#000',
      'text-halo-color': '#fff',
      'text-halo-width': 1,
    },
  }
}

export function layerNonComm({
  featureKey,
}: {
  featureKey: string
}): LayerProps {
  return {
    id: 'non-comm',
    type: 'line',
    paint: {
      'line-color': COLOR_NON_COMM,
      'line-width': 1,
      'line-opacity': 1,
    },
    filter: ['all', ['==', ['get', featureKey], null]],
  }
}

export function layerRedOutline({
  featureKey,
}: {
  featureKey: string
}): LayerProps {
  return {
    id: 'red-outline',
    type: 'line',
    paint: {
      'line-color': '#F03E3E',
      'line-width': 1,
      'line-opacity': 1,
    },
    filter: ['all', ['==', ['get', featureKey], true]],
  }
}

/**
 * Get the Mapbox style URL for a given theme and satellite view. Parameters are checked in the following order: empty, satellite, theme. See https://docs.mapbox.com/api/maps/styles/ for more information.
 * @param empty - Whether to return undefined
 * @param satellite - Whether to use the satellite view
 * @param theme - The theme, either "light" or "dark"
 * @returns The Mapbox style URL
 */
export function mapStyle({
  empty = false,
  satellite = false,
  theme = 'light',
}: {
  empty?: boolean
  satellite?: boolean
  theme?: 'light' | 'dark'
}): string | undefined {
  if (empty) {
    return undefined
  } else if (satellite) {
    return 'mapbox://styles/mapbox/satellite-streets-v11'
  } else if (theme === 'light') {
    return 'mapbox://styles/mapbox/light-v10'
  } else {
    return 'mapbox://styles/mapbox/dark-v10'
  }
}
