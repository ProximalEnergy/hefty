import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions, useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type { Feature, FeatureCollection, MultiPolygon } from 'geojson'

const spcWxOutlooksEndpointUrl = [
  'https://mapservices.weather.noaa.gov/vector/rest/services/outlooks',
  'SPC_wx_outlks/MapServer',
].join('/')
const spcFireWxEndpointUrl = [
  'https://mapservices.weather.noaa.gov/vector/rest/services/fire_weather',
  'SPC_firewx/MapServer',
].join('/')

/** GeoJSON properties for SPC outlook polygons (NWS MapServer attributes). */
type SpcOutlookFeatureProps = {
  dn: number
  valid?: string
  expire?: string
  issue?: string
}

interface ArcGisFeature {
  attributes: {
    dn: number
    valid?: string
    expire?: string
    issue?: string
  }
  geometry: {
    rings: number[][][]
  }
}

interface ArcGisResponse {
  features: ArcGisFeature[]
}

interface ArcGisValidityFeature {
  attributes: {
    valid: string
    expire: string
  }
}

interface ArcGisValidityResponse {
  features: ArcGisValidityFeature[]
  error?: { code: number; message: string }
}

type GeoJsonFeatureCollection = FeatureCollection<
  GeoJsonMultiPolygon,
  SpcOutlookFeatureProps
>
type GeoJsonFeature = Feature<GeoJsonMultiPolygon, SpcOutlookFeatureProps>
type GeoJsonMultiPolygon = MultiPolygon

/** Parse NWS MapServer `valid` / `expire` strings (YYYYMMDDHHmm, UTC). */
export const parseNwsspcTimestamp = (s: string): Date | null => {
  if (!s || s.length < 12) return null
  const y = Number(s.slice(0, 4))
  const mo = Number(s.slice(4, 6)) - 1
  const d = Number(s.slice(6, 8))
  const h = Number(s.slice(8, 10))
  const min = Number(s.slice(10, 12))
  if ([y, mo, d, h, min].some((n) => Number.isNaN(n))) return null
  return new Date(Date.UTC(y, mo, d, h, min, 0, 0))
}

const getSPCForecastPolygons = async (
  endpointUrl: string,
  arcgis_layer_id: number,
): Promise<GeoJsonFeatureCollection> => {
  const query_url = `${endpointUrl}/${arcgis_layer_id}/query`

  const outFields = endpointUrl.includes('fire_weather')
    ? 'dn,valid,expire'
    : 'dn,valid,expire,issue'

  const params = {
    where: '1=1',
    outFields,
    returnGeometry: 'true',
    geometryPrecision: '3',
    outSR: 4326, // Request WGS84 coordinates (lat/lon) instead of Web Mercator
    f: 'json',
  }

  const response = await axios.get<ArcGisResponse>(query_url, { params })
  const data = response.data

  if ('error' in data) {
    throw new Error(`ArcGIS API error`)
  }

  const features: GeoJsonFeature[] = data.features.map((feature) => {
    // Convert rings to coordinate arrays
    const rings = feature.geometry.rings.map((ring) => {
      return ring.map((point) => [point[0], point[1]])
    })

    // ArcGIS: exterior = clockwise, holes = counter-clockwise.
    // GeoJSON: exterior = counter-clockwise, holes = clockwise.
    // Reverse each ring so Mapbox renders correctly.
    const polygons: number[][][][] = []

    rings.forEach((ring) => {
      let sum = 0
      for (let i = 0; i < ring.length - 1; i++) {
        sum += (ring[i + 1][0] - ring[i][0]) * (ring[i + 1][1] + ring[i][1])
      }
      const isExterior = sum > 0 // Clockwise = exterior in ArcGIS

      const ringGeoJson = [...ring].reverse()
      if (isExterior) {
        polygons.push([ringGeoJson])
      } else {
        if (polygons.length > 0) {
          polygons[polygons.length - 1].push(ringGeoJson)
        }
      }
    })

    const geometry: GeoJsonMultiPolygon = {
      type: 'MultiPolygon',
      coordinates: polygons,
    }

    const props: SpcOutlookFeatureProps = { dn: feature.attributes.dn }
    if (feature.attributes.valid != null) {
      props.valid = feature.attributes.valid
    }
    if (feature.attributes.expire != null) {
      props.expire = feature.attributes.expire
    }
    if (feature.attributes.issue != null) {
      props.issue = feature.attributes.issue
    }

    return {
      type: 'Feature',
      properties: props,
      geometry,
    }
  })

  return {
    type: 'FeatureCollection',
    features,
  }
}

const useGetSPCForecastPolygons = ({
  endpointUrl,
  arcgis_layer_id,
  queryKey,
  queryOptions = {},
}: {
  endpointUrl: string
  arcgis_layer_id: number
  queryKey: string
  queryOptions?: Partial<UseQueryOptions<GeoJsonFeatureCollection>>
}) => {
  const defaultQueryOptions = {
    staleTime: QUERY_TIME.FIVE_MINUTES,
    refetchInterval: QUERY_TIME.FIVE_MINUTES,
  }

  return useQuery<GeoJsonFeatureCollection>({
    queryKey: [queryKey, arcgis_layer_id],
    queryFn: () => getSPCForecastPolygons(endpointUrl, arcgis_layer_id),
    ...defaultQueryOptions,
    ...queryOptions,
  })
}

const getSpcOutlookValiditySample = async (
  endpointUrl: string,
  arcgis_layer_id: number,
): Promise<{ valid: string; expire: string } | null> => {
  const query_url = `${endpointUrl}/${arcgis_layer_id}/query`
  const params = {
    where: '1=1',
    outFields: 'valid,expire',
    returnGeometry: 'false',
    resultRecordCount: 1,
    f: 'json',
  }
  const response = await axios.get<ArcGisValidityResponse>(query_url, {
    params,
  })
  const data = response.data
  if ('error' in data && data.error) return null
  const row = data.features?.[0]
  if (!row?.attributes?.valid || !row?.attributes?.expire) return null
  return { valid: row.attributes.valid, expire: row.attributes.expire }
}

type SpcOutlookDayValidity = { valid: string; expire: string }

/** Day 1 / Day 2 validity rows from representative hail outlook layers. */
export const useSpcHailOutlookDayValidityPair = (
  day1HailLayerId: number,
  day2HailLayerId: number,
  queryOptions: Partial<
    UseQueryOptions<{
      day1: SpcOutlookDayValidity | null
      day2: SpcOutlookDayValidity | null
    }>
  > = {},
) => {
  const defaults = {
    staleTime: 1000 * 60 * 5,
    refetchInterval: 1000 * 60 * 5,
  }
  return useQuery({
    queryKey: [
      'spcHailOutlookDayValidityPair',
      day1HailLayerId,
      day2HailLayerId,
    ],
    queryFn: async () => ({
      day1: await getSpcOutlookValiditySample(
        spcWxOutlooksEndpointUrl,
        day1HailLayerId,
      ),
      day2: await getSpcOutlookValiditySample(
        spcWxOutlooksEndpointUrl,
        day2HailLayerId,
      ),
    }),
    ...defaults,
    ...queryOptions,
  })
}

export const useGetHailForecastPolygons = ({
  arcgis_layer_id,
  queryOptions = {},
}: {
  arcgis_layer_id: number
  queryOptions?: Partial<UseQueryOptions<GeoJsonFeatureCollection>>
}) => {
  return useGetSPCForecastPolygons({
    endpointUrl: spcWxOutlooksEndpointUrl,
    arcgis_layer_id,
    queryKey: 'getHailForecastPolygons',
    queryOptions,
  })
}

export const useGetTornadoOutlook = ({
  arcgis_layer_id,
  queryOptions = {},
}: {
  arcgis_layer_id: number
  queryOptions?: Partial<UseQueryOptions<GeoJsonFeatureCollection>>
}) => {
  return useGetSPCForecastPolygons({
    endpointUrl: spcWxOutlooksEndpointUrl,
    arcgis_layer_id,
    queryKey: 'getTornadoOutlook',
    queryOptions,
  })
}

export const useGetWindOutlook = ({
  arcgis_layer_id,
  queryOptions = {},
}: {
  arcgis_layer_id: number
  queryOptions?: Partial<UseQueryOptions<GeoJsonFeatureCollection>>
}) => {
  return useGetSPCForecastPolygons({
    endpointUrl: spcWxOutlooksEndpointUrl,
    arcgis_layer_id,
    queryKey: 'getWindOutlook',
    queryOptions,
  })
}

export const useGetFireOutlook = ({
  arcgis_layer_id,
  queryOptions = {},
}: {
  arcgis_layer_id: number
  queryOptions?: Partial<UseQueryOptions<GeoJsonFeatureCollection>>
}) => {
  return useGetSPCForecastPolygons({
    endpointUrl: spcFireWxEndpointUrl,
    arcgis_layer_id,
    queryKey: 'getFireOutlook',
    queryOptions,
  })
}

export const useGetThunderstormOutlook = ({
  arcgis_layer_id,
  queryOptions = {},
}: {
  arcgis_layer_id: number
  queryOptions?: Partial<UseQueryOptions<GeoJsonFeatureCollection>>
}) => {
  return useGetSPCForecastPolygons({
    endpointUrl: spcWxOutlooksEndpointUrl,
    arcgis_layer_id,
    queryKey: 'getThunderstormOutlook',
    queryOptions,
  })
}

// NWS/NOAA tile services
// Note: NWS doesn't provide direct tile services for radiation/windspeed
// Using OpenWeatherMap as alternative since NWS services aren't available
// OpenWeatherMap provides these layers and is already configured in the app
export const getNWSWindspeedTileUrl = (): string => {
  // Using OpenWeatherMap wind speed layer as NWS doesn't provide tile service
  // Alternative would be NWS NDFD WMS which requires server-side conversion
  const appid = import.meta.env.VITE_OPENWEATHERMAP_APP_ID
  return `https://tile.openweathermap.org/map/wind_new/{z}/{x}/{y}.png?appid=${appid}`
}

export const getTemperatureTileUrl = (): string => {
  // OpenWeatherMap temperature layer
  const appid = import.meta.env.VITE_OPENWEATHERMAP_APP_ID
  return `https://tile.openweathermap.org/map/temp_new/{z}/{x}/{y}.png?appid=${appid}`
}
