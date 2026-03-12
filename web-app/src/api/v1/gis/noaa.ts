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

interface ArcGisFeature {
  attributes: {
    dn: number
  }
  geometry: {
    rings: number[][][]
  }
}

interface ArcGisResponse {
  features: ArcGisFeature[]
}

type GeoJsonFeatureCollection = FeatureCollection<
  GeoJsonMultiPolygon,
  { dn: number }
>
type GeoJsonFeature = Feature<GeoJsonMultiPolygon, { dn: number }>
type GeoJsonMultiPolygon = MultiPolygon

const getSPCForecastPolygons = async (
  endpointUrl: string,
  arcgis_layer_id: number,
): Promise<GeoJsonFeatureCollection> => {
  const query_url = `${endpointUrl}/${arcgis_layer_id}/query`

  const params = {
    where: '1=1',
    outFields: 'dn',
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

    return {
      type: 'Feature',
      properties: {
        dn: feature.attributes.dn,
      },
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
    staleTime: 1000 * 60 * 5,
    refetchInterval: 1000 * 60 * 5,
  }

  return useQuery<GeoJsonFeatureCollection>({
    queryKey: [queryKey, arcgis_layer_id],
    queryFn: () => getSPCForecastPolygons(endpointUrl, arcgis_layer_id),
    ...defaultQueryOptions,
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
