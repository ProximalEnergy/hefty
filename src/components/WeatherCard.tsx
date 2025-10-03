import { useGetProject } from '@/api/v1/operational/projects'
import { useGetForecast, useGetWeather } from '@/hooks/api'
import { Group, HoverCard, Image, Stack, Text, Tooltip } from '@mantine/core'
import { IconSunOff } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { Link, useParams } from 'react-router-dom'

const WeatherCard = () => {
  const { projectId } = useParams()
  const {
    data: weatherData,
    isLoading: weatherLoading,
    error: weatherError,
  } = useGetWeather({
    pathParams: { projectId: projectId || '-1' },
  })
  const {
    data: forecastData,
    isLoading: forecastLoading,
    error: forecastError,
  } = useGetForecast({
    pathParams: { projectId: projectId || '-1' },
  })
  const { data: projectData, isLoading: projectLoading } = useGetProject({
    pathParams: { projectId: projectId || '-1' },
  })

  if (weatherLoading) return
  if (forecastLoading) return
  if (projectLoading) return
  if (projectData === undefined) return
  const tz = projectData.time_zone

  function extractTime(datetime: number, timeZone: string): string {
    return dayjs.unix(datetime).tz(timeZone).format('ha')
  }

  return (
    <>
      {weatherError ? (
        <Tooltip label="Error loading weather data">
          <IconSunOff />
        </Tooltip>
      ) : (
        <HoverCard>
          <HoverCard.Target>
            <Stack align="center" justify="center" gap={0}>
              <Image
                src={`https://openweathermap.org/img/wn/${weatherData?.weather[0].icon}@2x.png`}
                alt={weatherData?.weather[0].description}
                style={{ width: '25px', height: '25px' }}
                mt={-6}
              />
              <Group>
                <Text size="xs" lh={1}>
                  {`${Math.round(weatherData?.main.temp || 0)}°F`}
                </Text>
              </Group>
            </Stack>
          </HoverCard.Target>
          <HoverCard.Dropdown>
            <Stack>
              {!forecastError && (
                <Group gap="sm">
                  <Stack align="center" justify="center" gap={0}>
                    <Image
                      src={`https://openweathermap.org/img/wn/${weatherData?.weather[0].icon}@2x.png`}
                      alt={weatherData?.weather[0].description}
                      style={{ width: '50px', height: '50px' }}
                      mt={-12}
                    />
                    <Group>
                      <Text lh={1}>
                        {'Now'} {`${Math.round(weatherData?.main.temp || 0)}°F`}
                      </Text>
                    </Group>
                  </Stack>
                  {forecastData?.list.slice(0, 3).map((forecast, index) => (
                    <Stack align="center" justify="center" gap={0} key={index}>
                      <Image
                        src={`https://openweathermap.org/img/wn/${forecast.weather[0].icon}@2x.png`}
                        alt={forecast.weather[0].description}
                        style={{ width: '50px', height: '50px' }}
                        mt={-12}
                      />
                      <Text lh={1}>
                        {extractTime(forecast.dt, tz)}{' '}
                        {`${Math.round(forecast.main.temp || 0)}°F`}
                      </Text>
                    </Stack>
                  ))}
                </Group>
              )}
              <Stack gap={0}>
                <Text size="xs" c="dimmed">
                  Weather data provided by{' '}
                  <Link to="https://openweathermap.org/" target="_blank">
                    OpenWeather
                  </Link>
                </Text>
              </Stack>
            </Stack>
          </HoverCard.Dropdown>
        </HoverCard>
      )}
    </>
  )
}
export default WeatherCard
