import type { ForecastResponse } from '@/hooks/types'
import dayjs from 'dayjs'

// Type for DataTimeSeriesLast with optional tag property
export interface DataTimeSeriesLastWithTag {
  value_integer: number | null
  value_bigint: number | null
  value_real: number | null
  value_double: number | null
  tag?: {
    unit_scale: number | null
    unit_offset: number | null
  }
}

// Type for forecast list item
export type ForecastListItem = ForecastResponse['list'][number]

// Helper to extract numeric value from DataTimeSeriesLast
// NOTE: The backend endpoint get_data_timeseries_last already applies unit_scale
// and unit_offset before returning values, so we should NOT apply scaling again here.
// The tag metadata is included for reference but scaling has already been applied.
const getNumericValue = (
  item: DataTimeSeriesLastWithTag | null,
): number | null => {
  if (!item) return null
  const rawValue =
    item.value_double ??
    item.value_real ??
    item.value_bigint ??
    item.value_integer ??
    null

  if (rawValue === null) return null

  // Backend already applied unit_scale and unit_offset, so return the value as-is
  return rawValue
}

// Calculate averages
export const calculateAverage = (
  data: DataTimeSeriesLastWithTag[] | null | undefined,
): number | null => {
  if (!data || data.length === 0) return null
  const values = data
    .map(getNumericValue)
    .filter((v): v is number => v !== null)
  if (values.length === 0) return null
  return values.reduce((sum, val) => sum + val, 0) / values.length
}

// Get all forecast entries for a specific day
export const getForecastsForDay = (
  forecastData: ForecastResponse | null | undefined,
  targetDate: dayjs.Dayjs,
  timezoneOffsetSeconds?: number,
): ForecastListItem[] => {
  if (!forecastData?.list || forecastData.list.length === 0) return []

  // Get offset from forecastData.city.timezone (seconds) or fallback to parameter or 0
  const offsetSeconds =
    forecastData.city?.timezone ?? timezoneOffsetSeconds ?? 0
  const offsetMinutes = offsetSeconds / 60

  // Convert targetDate to the same timezone offset for comparison
  const targetDateInOffset = targetDate.utcOffset(offsetMinutes)

  return forecastData.list
    .filter((item) => {
      const itemDate = dayjs
        .unix(item.dt)
        .utcOffset(offsetMinutes)
        .startOf('day')
      return itemDate.isSame(targetDateInOffset, 'day')
    })
    .sort((a, b) => a.dt - b.dt) // Sort by timestamp
}

// Get aggregated forecast for a day (for day after tomorrow)
export const getAggregatedForecastForDay = (
  forecastData: ForecastResponse | null | undefined,
  targetDate: dayjs.Dayjs,
  timezoneOffsetSeconds?: number,
): ForecastListItem | null => {
  if (!forecastData) return null

  // Get offset from forecastData.city.timezone (seconds) or fallback to parameter or 0
  const offsetSeconds =
    forecastData.city?.timezone ?? timezoneOffsetSeconds ?? 0
  const offsetMinutes = offsetSeconds / 60

  const dayForecasts = getForecastsForDay(
    forecastData,
    targetDate,
    timezoneOffsetSeconds,
  )
  if (dayForecasts.length === 0) return null

  // Aggregate all forecasts for the day
  const temps = dayForecasts.map((f) => f.main.temp)
  const tempMins = dayForecasts.map((f) => f.main.temp_min)
  const tempMaxs = dayForecasts.map((f) => f.main.temp_max)
  const humidities = dayForecasts.map((f) => f.main.humidity)
  const windSpeeds = dayForecasts.map((f) => f.wind?.speed || 0)
  const windGusts = dayForecasts.map((f) => f.wind?.gust || 0)
  const pops = dayForecasts.map((f) => f.pop || 0)
  const cloudCovers = dayForecasts.map((f) => f.clouds?.all || 0)

  // Find the forecast closest to noon (12:00) for icon and description
  // Convert targetDate to the same timezone offset before creating noon reference
  const targetDateInOffset = targetDate.utcOffset(offsetMinutes)
  const noon = targetDateInOffset.hour(12).minute(0)
  const representativeForecast = dayForecasts.reduce((closest, current) => {
    const closestDate = dayjs.unix(closest.dt).utcOffset(offsetMinutes)
    const currentDate = dayjs.unix(current.dt).utcOffset(offsetMinutes)
    const closestDiff = Math.abs(closestDate.diff(noon, 'hour'))
    const currentDiff = Math.abs(currentDate.diff(noon, 'hour'))
    return currentDiff < closestDiff ? current : closest
  })

  // Create aggregated forecast object
  return {
    ...representativeForecast,
    main: {
      ...representativeForecast.main,
      temp: Math.round(temps.reduce((sum, t) => sum + t, 0) / temps.length), // Average temp
      temp_min: Math.min(...tempMins), // Daily min
      temp_max: Math.max(...tempMaxs), // Daily max
      humidity: Math.round(
        humidities.reduce((sum, h) => sum + h, 0) / humidities.length,
      ), // Average humidity
    },
    wind: {
      ...representativeForecast.wind,
      speed: Math.round(
        windSpeeds.reduce((sum, w) => sum + w, 0) / windSpeeds.length,
      ), // Average wind speed
      gust: Math.max(...windGusts), // Max wind gust
    },
    clouds: {
      all: Math.round(
        cloudCovers.reduce((sum, c) => sum + c, 0) / cloudCovers.length,
      ), // Average cloud cover
    },
    pop: Math.max(...pops), // Max precipitation probability for the day
  }
}

// Interpolate forecast values between timestamps
export const getInterpolatedForecast = (
  tomorrowForecasts: ForecastListItem[],
  sliderValue: number,
): ForecastListItem | null => {
  if (tomorrowForecasts.length === 0) return null
  if (tomorrowForecasts.length === 1) return tomorrowForecasts[0]

  const maxSliderValue = Math.max(0, tomorrowForecasts.length - 1)
  const clampedValue = Math.max(0, Math.min(sliderValue, maxSliderValue))
  const lowerIndex = Math.floor(clampedValue)
  const upperIndex = Math.min(
    Math.ceil(clampedValue),
    tomorrowForecasts.length - 1,
  )
  const t = clampedValue - lowerIndex

  // If exactly on a timestamp, return that forecast
  if (t === 0) return tomorrowForecasts[lowerIndex]
  if (lowerIndex === upperIndex) return tomorrowForecasts[lowerIndex]

  const lower = tomorrowForecasts[lowerIndex]
  const upper = tomorrowForecasts[upperIndex]

  // Interpolate numeric values
  const interpolate = (a: number, b: number) => a + (b - a) * t

  return {
    ...lower,
    dt: Math.round(interpolate(lower.dt, upper.dt)),
    main: {
      ...lower.main,
      temp: interpolate(lower.main.temp, upper.main.temp),
      feels_like: interpolate(lower.main.feels_like, upper.main.feels_like),
      temp_min: interpolate(lower.main.temp_min, upper.main.temp_min),
      temp_max: interpolate(lower.main.temp_max, upper.main.temp_max),
      humidity: Math.round(
        interpolate(lower.main.humidity, upper.main.humidity),
      ),
      pressure: Math.round(
        interpolate(lower.main.pressure, upper.main.pressure),
      ),
    },
    wind: {
      speed: interpolate(lower.wind?.speed || 0, upper.wind?.speed || 0),
      deg: Math.round(interpolate(lower.wind?.deg || 0, upper.wind?.deg || 0)),
      gust: interpolate(lower.wind?.gust || 0, upper.wind?.gust || 0),
    },
    clouds: {
      all: Math.round(
        interpolate(lower.clouds?.all || 0, upper.clouds?.all || 0),
      ),
    },
    pop: interpolate(lower.pop || 0, upper.pop || 0),
    // Use weather from the closest timestamp (round to nearest)
    weather:
      Math.round(clampedValue) === lowerIndex ? lower.weather : upper.weather,
  }
}
