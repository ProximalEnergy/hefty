import { Divider, Group, Image, Stack, Text } from '@mantine/core'
import {
  IconCloudRain,
  IconDroplet,
  IconTemperature,
  IconWind,
} from '@tabler/icons-react'

interface WeatherContentProps {
  weather: {
    id: number
    main: string
    description: string
    icon: string
  } | null
  main: {
    temp: number
    feels_like?: number
    temp_min?: number
    temp_max?: number
    humidity?: number
  } | null
  wind: {
    speed: number
    gust?: number
  } | null
  clouds: {
    all: number
  } | null
  pop: number | null
  isForecast: boolean
}

export const WeatherContent = ({
  weather,
  main,
  wind,
  clouds,
  pop,
  isForecast,
}: WeatherContentProps) => {
  if (!main || !weather) {
    return (
      <Text size="xs" c="dimmed">
        Weather data unavailable
      </Text>
    )
  }

  // Both APIs use units=imperial, so temperatures are in Fahrenheit and wind
  // in mph
  const temp = main.temp
  const feelsLike = 'feels_like' in main ? main.feels_like : temp
  const tempMin = 'temp_min' in main ? main.temp_min : null
  const tempMax = 'temp_max' in main ? main.temp_max : null
  const humidity = 'humidity' in main ? main.humidity : null
  const windSpeed = wind?.speed || 0
  const windGust = wind?.gust
  const cloudCover = clouds?.all || 0

  return (
    <Stack gap="xs">
      <Group gap="sm" align="center">
        {weather && (
          <Image
            src={`https://openweathermap.org/img/wn/${weather.icon}@2x.png`}
            alt={weather.description}
            style={{ width: '40px', height: '40px' }}
          />
        )}
        <Stack gap={2}>
          <Text size="xs" c="dimmed" tt="capitalize">
            {weather.description}
          </Text>
          <Group gap="xs" align="center">
            <IconTemperature size={16} />
            <Text size="sm" fw={500}>
              {Math.round(temp)}°F
            </Text>
            {isForecast && tempMin && tempMax && (
              <Text size="xs" c="dimmed">
                ({Math.round(tempMin)}° / {Math.round(tempMax)}°)
              </Text>
            )}
            {!isForecast && feelsLike !== undefined && (
              <Text size="xs" c="dimmed">
                (feels like {Math.round(feelsLike)}°F)
              </Text>
            )}
          </Group>
        </Stack>
      </Group>
      <Divider />
      <Group gap="md" grow align="flex-start">
        <Stack gap={4}>
          <Group gap={4} align="center">
            <IconWind size={14} />
            <Text size="xs" c="dimmed">
              Wind Speed
            </Text>
          </Group>
          <Text size="sm" fw={500}>
            {Math.round(windSpeed)} mph
          </Text>
          {windGust && (
            <Text size="xs" c="dimmed">
              Gusts: {Math.round(windGust)} mph
            </Text>
          )}
        </Stack>
        {humidity !== null && (
          <Stack gap={4}>
            <Group gap={4} align="center">
              <IconDroplet size={14} />
              <Text size="xs" c="dimmed">
                Humidity
              </Text>
            </Group>
            <Text size="sm" fw={500}>
              {humidity}%
            </Text>
          </Stack>
        )}
        {pop !== null && (
          <Stack gap={4}>
            <Group gap={4} align="center">
              <IconCloudRain size={14} />
              <Text size="xs" c="dimmed">
                Precipitation
              </Text>
            </Group>
            <Text size="sm" fw={500}>
              {Math.round(pop * 100)}%
            </Text>
          </Stack>
        )}
      </Group>
      <Group gap="xs" mt={4}>
        <Text size="xs" c="dimmed">
          Clouds: {cloudCover}%
        </Text>
      </Group>
    </Stack>
  )
}
