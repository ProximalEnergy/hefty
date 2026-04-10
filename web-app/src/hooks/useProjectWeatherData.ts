import { SensorTypeEnum } from '@/api/enumerations'
import type { DataTimeSeriesLast } from '@/api/v1/protected/web-application/projects/real_time'
import { useGetDataTimeseriesLast } from '@/api/v1/protected/web-application/projects/real_time'
import { useGetForecast, useGetTags, useGetWeather } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import {
  type DataTimeSeriesLastWithTag,
  calculateAverage,
} from '@/utils/weatherUtils'
import { useMemo } from 'react'

// Conversion constants
const TEMPERATURE_C_TO_F_MULTIPLIER = 9 / 5
const TEMPERATURE_C_TO_F_OFFSET = 32
const MPS_TO_MPH = 2.23694

interface ProjectWeatherData {
  // Current weather
  weather: ReturnType<typeof useGetWeather>['data']
  weatherLoading: boolean
  weatherError: ReturnType<typeof useGetWeather>['error'] | null

  // Forecast
  forecast: ReturnType<typeof useGetForecast>['data']
  forecastLoading: boolean
  forecastError: ReturnType<typeof useGetForecast>['error'] | null

  // Sensor data
  sensorLoading: boolean
  sensorError: ReturnType<typeof useGetWeather>['error'] | null

  // Calculated values
  avgGHI: number | null
  avgTemp: number | null
  avgWind: number | null
  avgMeterPowerMW: number | null
}

export const useProjectWeatherData = (
  projectId: string,
): ProjectWeatherData => {
  const {
    data: weatherData,
    isLoading: weatherLoading,
    error: weatherError,
  } = useGetWeather({
    pathParams: { projectId },
    queryOptions: {
      staleTime: QUERY_TIME.FIFTEEN_MINUTES, // 15 minutes
    },
  })

  // Only fetch forecast when hover card is open
  const {
    data: forecastData,
    isLoading: forecastLoading,
    error: forecastError,
  } = useGetForecast({
    pathParams: { projectId },
    queryOptions: {
      staleTime: QUERY_TIME.FIFTEEN_MINUTES, // 15 minutes
    },
  })

  // Fetch data for each sensor type separately to calculate accurate averages
  // Only fetch when hover card is open
  const {
    data: ghiData,
    isLoading: ghiLoading,
    error: ghiError,
  } = useGetDataTimeseriesLast({
    pathParams: { projectId },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.MET_STATION_GHI],
    },
    queryOptions: {
      staleTime: QUERY_TIME.ONE_MINUTE,
    },
  })

  const {
    data: tempData,
    isLoading: tempLoading,
    error: tempError,
  } = useGetDataTimeseriesLast({
    pathParams: { projectId },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.MET_STATION_AMBIENT_TEMPERATURE],
    },
    queryOptions: {
      staleTime: QUERY_TIME.ONE_MINUTE,
    },
  })

  const {
    data: windData,
    isLoading: windLoading,
    error: windError,
  } = useGetDataTimeseriesLast({
    pathParams: { projectId },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.MET_STATION_WIND_SPEED],
    },
    queryOptions: {
      staleTime: QUERY_TIME.ONE_MINUTE,
    },
  })

  const {
    data: meterPowerData,
    isLoading: meterPowerLoading,
    error: meterPowerError,
  } = useGetDataTimeseriesLast({
    pathParams: { projectId },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.METER_ACTIVE_POWER],
    },
    queryOptions: {
      staleTime: QUERY_TIME.ONE_MINUTE,
    },
  })

  // Fetch tags to get unit_scale and unit_offset metadata
  const { data: tagsData } = useGetTags({
    pathParams: { projectId },
    queryOptions: {
      staleTime: QUERY_TIME.NEVER,
    },
  })

  // Create a map of tag_id -> tag metadata for efficient lookup
  const tagMetadataMap = useMemo(() => {
    if (!tagsData)
      return new Map<
        number,
        { unit_scale: number | null; unit_offset: number | null }
      >()
    const map = new Map<
      number,
      { unit_scale: number | null; unit_offset: number | null }
    >()
    tagsData.forEach((tag) => {
      map.set(tag.tag_id, {
        unit_scale: tag.unit_scale,
        unit_offset: tag.unit_offset,
      })
    })
    return map
  }, [tagsData])

  // Transform DataTimeSeriesLast[] to DataTimeSeriesLastWithTag[]
  const transformTimeseriesData = (
    data: DataTimeSeriesLast[] | null | undefined,
  ): DataTimeSeriesLastWithTag[] | null | undefined => {
    if (!data) return data
    return data.map((item) => ({
      ...item,
      tag: tagMetadataMap.get(item.tag_id),
    }))
  }

  const sensorLoading =
    ghiLoading || tempLoading || windLoading || meterPowerLoading

  // Combine sensor errors - return first error found, or null if none
  const sensorError =
    ghiError || tempError || windError || meterPowerError || null

  // Transform timeseries data to include tag metadata
  const ghiDataWithTags = transformTimeseriesData(ghiData)
  const tempDataWithTags = transformTimeseriesData(tempData)
  const windDataWithTags = transformTimeseriesData(windData)
  const meterPowerDataWithTags = transformTimeseriesData(meterPowerData)

  // Calculate averages
  const avgGHI = calculateAverage(ghiDataWithTags)
  // Convert temperature from Celsius to Fahrenheit
  const avgTempCelsius = calculateAverage(tempDataWithTags)
  const avgTemp =
    avgTempCelsius !== null
      ? avgTempCelsius * TEMPERATURE_C_TO_F_MULTIPLIER +
        TEMPERATURE_C_TO_F_OFFSET
      : null
  // Convert wind speed from m/s to mph
  const avgWindMps = calculateAverage(windDataWithTags)
  const avgWind = avgWindMps !== null ? avgWindMps * MPS_TO_MPH : null
  // Meter power: unit scaling is applied via getNumericValue based on tag.unit_scale
  const avgMeterPowerMW = calculateAverage(meterPowerDataWithTags)

  return {
    weather: weatherData,
    weatherLoading,
    weatherError: weatherError || null,
    forecast: forecastData,
    forecastLoading,
    forecastError: forecastError || null,
    sensorLoading,
    sensorError,
    avgGHI,
    avgTemp,
    avgWind,
    avgMeterPowerMW,
  }
}
