import { SensorTypeEnum } from '@/api/enumerations'
import { Project } from '@/api/v1/operational/projects'
import { useProjectWeatherData } from '@/hooks/useProjectWeatherData'
import {
  type ForecastListItem,
  getAggregatedForecastForDay,
  getForecastsForDay,
} from '@/utils/weatherUtils'
import {
  Anchor,
  Divider,
  Group,
  HoverCard,
  Stack,
  Tabs,
  Text,
} from '@mantine/core'
import { IconSun, IconTemperature, IconWind } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useState } from 'react'

import { ForecastSlider } from './ForecastSlider'
import { WeatherContent } from './WeatherContent'

interface WeatherHoverCardProps {
  project: Project
}

export const WeatherHoverCard = ({ project }: WeatherHoverCardProps) => {
  const {
    weather,
    weatherLoading,
    forecast,
    forecastLoading,
    sensorLoading,
    avgGHI,
    avgTemp,
    avgWind,
    avgMeterPowerMW,
  } = useProjectWeatherData(project.project_id)

  const [selectedTomorrowForecast, setSelectedTomorrowForecast] =
    useState<ForecastListItem | null>(null)

  // Get timezone offset from forecast or weather (in seconds)
  const timezoneOffsetSeconds =
    forecast?.city?.timezone ?? (weather as { timezone?: number })?.timezone

  // Compute day buckets using project timezone offset
  const offsetMinutes =
    timezoneOffsetSeconds !== undefined ? timezoneOffsetSeconds / 60 : 0
  const now = dayjs().utcOffset(offsetMinutes).startOf('day')
  const tomorrow = now.add(1, 'day').startOf('day')
  const dayAfterTomorrow = now.add(2, 'day').startOf('day')
  const threeDaysOut = now.add(3, 'day').startOf('day')

  // Get all tomorrow forecasts for the slider
  const tomorrowForecasts = getForecastsForDay(
    forecast,
    tomorrow,
    timezoneOffsetSeconds,
  )
  const dayAfterTomorrowForecast = getAggregatedForecastForDay(
    forecast,
    dayAfterTomorrow,
    timezoneOffsetSeconds,
  )
  const threeDaysOutForecast = getAggregatedForecastForDay(
    forecast,
    threeDaysOut,
    timezoneOffsetSeconds,
  )

  const hasGhiSensor = project.spec.used_sensor_type_ids?.includes(
    SensorTypeEnum.MET_STATION_GHI,
  )
  const hasTempSensor = project.spec.used_sensor_type_ids?.includes(
    SensorTypeEnum.MET_STATION_AMBIENT_TEMPERATURE,
  )
  const hasWindSensor = project.spec.used_sensor_type_ids?.includes(
    SensorTypeEnum.MET_STATION_WIND_SPEED,
  )
  const hasAnySensor = hasGhiSensor || hasTempSensor || hasWindSensor

  // Helper to normalize weather data for WeatherContent
  const normalizeWeatherData = (
    data: typeof weather | ForecastListItem | null,
    isForecast: boolean,
    popOverride: number | null = null,
  ) => {
    if (!data) return null

    const weatherItem = isForecast
      ? (data as ForecastListItem)?.weather?.[0]
      : (data as typeof weather)?.weather?.[0]
    const main = isForecast
      ? (data as ForecastListItem)?.main
      : (data as typeof weather)?.main
    const wind = isForecast
      ? (data as ForecastListItem)?.wind
      : (data as typeof weather)?.wind
    const clouds = isForecast
      ? (data as ForecastListItem)?.clouds
      : (data as typeof weather)?.clouds
    const pop =
      popOverride !== null
        ? popOverride
        : isForecast && data && 'pop' in data
          ? (data as ForecastListItem).pop
          : null

    return {
      weather: weatherItem || null,
      main: main || null,
      wind: wind || null,
      clouds: clouds || null,
      pop,
      isForecast,
    }
  }

  // Helper to render weather content with null handling
  const renderWeatherContent = (
    data: typeof weather | ForecastListItem | null,
    isForecast: boolean,
  ) => {
    const normalized = normalizeWeatherData(data, isForecast)
    return normalized ? (
      <WeatherContent {...normalized} />
    ) : (
      <Text size="xs" c="dimmed">
        Weather data unavailable
      </Text>
    )
  }

  return (
    <HoverCard.Dropdown
      maw={450}
      w={450}
      onClick={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.stopPropagation()}
    >
      <Stack gap="sm">
        <Group justify="space-between" align="center">
          <Text size="sm" fw={600}>
            {project.name_long}
          </Text>
          {sensorLoading ? (
            <Text size="xs" c="dimmed">
              Loading...
            </Text>
          ) : avgMeterPowerMW !== null ? (
            <Text size="sm" fw={500}>
              Meter Power:{' '}
              {(() => {
                // Backend always returns meter power in MW
                const absValue = Math.abs(avgMeterPowerMW)
                const sign = avgMeterPowerMW >= 0 ? '' : '-'
                return `${sign}${absValue.toFixed(2)} MW`
              })()}
            </Text>
          ) : (
            <Text size="xs" c="dimmed">
              N/A
            </Text>
          )}
        </Group>
        <Divider />
        <Tabs defaultValue="now">
          <Tabs.List>
            <Tabs.Tab value="now">Now</Tabs.Tab>
            <Tabs.Tab value="tomorrow">Tomorrow</Tabs.Tab>
            <Tabs.Tab value="dayAfter">
              {dayAfterTomorrow.format('MMM D')}
            </Tabs.Tab>
            <Tabs.Tab value="day3">{threeDaysOut.format('MMM D')}</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="now" pt="sm">
            {weatherLoading ? (
              <Text size="xs" c="dimmed">
                Loading weather data...
              </Text>
            ) : (
              (() => {
                // Get precipitation from the nearest forecast for "Now" tab
                const nearestForecastPop =
                  forecast?.list && forecast.list.length > 0
                    ? forecast.list[0].pop
                    : null
                const normalized = normalizeWeatherData(
                  weather,
                  false,
                  nearestForecastPop,
                )
                return normalized ? (
                  <WeatherContent {...normalized} />
                ) : (
                  <Text size="xs" c="dimmed">
                    Weather data unavailable
                  </Text>
                )
              })()
            )}
            {/* Sensor Data Section - Only show for "Now" */}
            {hasAnySensor && (
              <>
                <Divider my="sm" />
                <Stack gap="xs">
                  <Text size="sm" fw={600}>
                    Site Sensor Data
                  </Text>
                  {sensorLoading ? (
                    <Text size="xs" c="dimmed">
                      Loading sensor data...
                    </Text>
                  ) : (
                    <Group gap="md" grow>
                      {hasGhiSensor ? (
                        <Stack gap={4}>
                          <Group gap={4} align="center">
                            <IconSun size={14} />
                            <Text size="xs" c="dimmed">
                              GHI
                            </Text>
                          </Group>
                          <Text size="sm" fw={500}>
                            {avgGHI !== null && avgGHI >= 0
                              ? `${Math.round(avgGHI)} W/m²`
                              : 'N/A'}
                          </Text>
                        </Stack>
                      ) : null}
                      {hasTempSensor ? (
                        <Stack gap={4}>
                          <Group gap={4} align="center">
                            <IconTemperature size={14} />
                            <Text size="xs" c="dimmed">
                              Temp
                            </Text>
                          </Group>
                          <Text size="sm" fw={500}>
                            {avgTemp !== null
                              ? `${Math.round(avgTemp)}°F`
                              : 'N/A'}
                          </Text>
                        </Stack>
                      ) : null}
                      {hasWindSensor ? (
                        <Stack gap={4}>
                          <Group gap={4} align="center">
                            <IconWind size={14} />
                            <Text size="xs" c="dimmed">
                              Wind
                            </Text>
                          </Group>
                          <Text size="sm" fw={500}>
                            {avgWind !== null && avgWind >= 0
                              ? `${Math.round(avgWind)} mph`
                              : 'N/A'}
                          </Text>
                        </Stack>
                      ) : null}
                    </Group>
                  )}
                </Stack>
              </>
            )}
          </Tabs.Panel>

          <Tabs.Panel value="tomorrow" pt="sm">
            {forecastLoading ? (
              <Text size="xs" c="dimmed">
                Loading forecast data...
              </Text>
            ) : tomorrowForecasts.length > 0 ? (
              <Stack gap="sm">
                <ForecastSlider
                  forecasts={tomorrowForecasts}
                  onForecastChange={setSelectedTomorrowForecast}
                  timezoneOffsetSeconds={timezoneOffsetSeconds}
                />
                {selectedTomorrowForecast &&
                  (() => {
                    const normalized = normalizeWeatherData(
                      selectedTomorrowForecast,
                      true,
                    )
                    return normalized ? (
                      <WeatherContent {...normalized} />
                    ) : (
                      <Text size="xs" c="dimmed">
                        Weather data unavailable
                      </Text>
                    )
                  })()}
              </Stack>
            ) : (
              <Text size="xs" c="dimmed">
                Forecast data unavailable
              </Text>
            )}
          </Tabs.Panel>

          <Tabs.Panel value="dayAfter" pt="sm">
            {forecastLoading ? (
              <Text size="xs" c="dimmed">
                Loading forecast data...
              </Text>
            ) : (
              renderWeatherContent(dayAfterTomorrowForecast, true)
            )}
          </Tabs.Panel>

          <Tabs.Panel value="day3" pt="sm">
            {forecastLoading ? (
              <Text size="xs" c="dimmed">
                Loading forecast data...
              </Text>
            ) : (
              renderWeatherContent(threeDaysOutForecast, true)
            )}
          </Tabs.Panel>
        </Tabs>
        <Divider />
        <Text size="xs" c="dimmed">
          Weather data from{' '}
          <Anchor
            href="https://openweathermap.org/"
            target="_blank"
            rel="noopener noreferrer"
            size="xs"
          >
            OpenWeather
          </Anchor>
        </Text>
      </Stack>
    </HoverCard.Dropdown>
  )
}
