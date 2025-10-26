import { GeoJSONFeature } from 'mapbox-gl'

export type HoverInfo = {
  feature: GeoJSONFeature | null
  x: number
  y: number
}
