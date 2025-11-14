import { UseQueryOptions, useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { FeatureCollection, GeoJsonProperties, MultiPolygon } from 'geojson'

const spcWxOutlooksEndpointUrl =
  'https://mapservices.weather.noaa.gov/vector/rest/services/outlooks/SPC_wx_outlks/MapServer'
const spcFireWxEndpointUrl =
  'https://mapservices.weather.noaa.gov/vector/rest/services/fire_weather/SPC_firewx/MapServer'

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

const getSPCForecastPolygons = async (
  endpointUrl: string,
  arcgis_layer_id: number,
): Promise<FeatureCollection<MultiPolygon, GeoJsonProperties>> => {
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

  const features = data.features.map((feature) => {
    // Convert rings to coordinate arrays
    const rings = feature.geometry.rings.map((ring) => {
      return ring.map((point) => [point[0], point[1]])
    })

    // For ArcGIS, we need to group rings into polygons based on winding order
    // Exterior rings (clockwise) start new polygons, interior rings (counter-clockwise) are holes
    const polygons: number[][][][] = []

    rings.forEach((ring) => {
      // Calculate if ring is clockwise (exterior) or counter-clockwise (interior/hole)
      let sum = 0
      for (let i = 0; i < ring.length - 1; i++) {
        sum += (ring[i + 1][0] - ring[i][0]) * (ring[i + 1][1] + ring[i][1])
      }
      const isExterior = sum > 0 // Clockwise = exterior ring

      if (isExterior) {
        // Start new polygon with this exterior ring
        polygons.push([ring])
      } else {
        // Add as hole to the last polygon
        if (polygons.length > 0) {
          polygons[polygons.length - 1].push(ring)
        }
      }
    })

    return {
      type: 'Feature' as const,
      properties: {
        dn: feature.attributes.dn,
      },
      geometry: {
        type: 'MultiPolygon' as const,
        coordinates: polygons,
      },
    }
  })

  return {
    type: 'FeatureCollection' as const,
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
  queryOptions?: Partial<
    UseQueryOptions<FeatureCollection<MultiPolygon, GeoJsonProperties>>
  >
}) => {
  const defaultQueryOptions: Partial<
    UseQueryOptions<FeatureCollection<MultiPolygon, GeoJsonProperties>>
  > = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 30, // 30 minutes
  }

  return useQuery<FeatureCollection<MultiPolygon, GeoJsonProperties>>({
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
  queryOptions?: Partial<
    UseQueryOptions<FeatureCollection<MultiPolygon, GeoJsonProperties>>
  >
}) => {
  return useGetSPCForecastPolygons({
    endpointUrl: spcWxOutlooksEndpointUrl,
    arcgis_layer_id,
    queryKey: 'getHailForecastPolygons',
    queryOptions,
  })
}

export const useGetTornadoOutlook = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<
    UseQueryOptions<FeatureCollection<MultiPolygon, GeoJsonProperties>>
  >
}) => {
  return useGetSPCForecastPolygons({
    endpointUrl: spcWxOutlooksEndpointUrl,
    arcgis_layer_id: 3,
    queryKey: 'getTornadoOutlook',
    queryOptions,
  })
}

export const useGetWindOutlook = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<
    UseQueryOptions<FeatureCollection<MultiPolygon, GeoJsonProperties>>
  >
}) => {
  return useGetSPCForecastPolygons({
    endpointUrl: spcWxOutlooksEndpointUrl,
    arcgis_layer_id: 7,
    queryKey: 'getWindOutlook',
    queryOptions,
  })
}

export const useGetFireOutlook = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<
    UseQueryOptions<FeatureCollection<MultiPolygon, GeoJsonProperties>>
  >
}) => {
  return useGetSPCForecastPolygons({
    endpointUrl: spcFireWxEndpointUrl,
    arcgis_layer_id: 1,
    queryKey: 'getFireOutlook',
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
