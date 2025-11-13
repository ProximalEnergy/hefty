import {
  type ForecastListItem,
  getInterpolatedForecast,
} from '@/utils/weatherUtils'
import { Group, Slider, Stack, Switch, Text } from '@mantine/core'
import dayjs from 'dayjs'
import { useEffect, useRef, useState } from 'react'

export interface ForecastSliderProps {
  forecasts: ForecastListItem[]
  onForecastChange: (forecast: ForecastListItem | null) => void
  timezoneOffsetSeconds?: number
}

export const ForecastSlider = ({
  forecasts,
  onForecastChange,
  timezoneOffsetSeconds,
}: ForecastSliderProps) => {
  const [sliderValue, setSliderValue] = useState(0)
  const [isAnimating, setIsAnimating] = useState(true)
  const onForecastChangeRef = useRef(onForecastChange)
  const forecastsRef = useRef(forecasts)

  // Keep refs up to date
  useEffect(() => {
    onForecastChangeRef.current = onForecastChange
  }, [onForecastChange])

  useEffect(() => {
    forecastsRef.current = forecasts
  }, [forecasts])

  const maxSliderValue = Math.max(0, forecasts.length - 1)

  // Animate slider throughout the day (animate over 30 seconds, then loop)
  useEffect(() => {
    if (!isAnimating || forecasts.length === 0) return

    const animationDuration = 30000 // 30 seconds to animate through the day
    const startTime = Date.now()

    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = (elapsed / animationDuration) % 1 // Loop continuously (0 to 1)
      const newValue = progress * maxSliderValue
      setSliderValue(newValue)
    }

    const interval = setInterval(animate, 16) // ~60fps
    return () => clearInterval(interval)
  }, [isAnimating, forecasts.length, maxSliderValue])

  // Notify parent of selected forecast
  useEffect(() => {
    const selectedForecast = getInterpolatedForecast(
      forecastsRef.current,
      sliderValue,
    )
    onForecastChangeRef.current(selectedForecast)
  }, [sliderValue])

  if (forecasts.length === 0) return null

  const roundedIndex = Math.round(sliderValue)
  const clampedIndex = Math.max(0, Math.min(roundedIndex, forecasts.length - 1))
  const selectedForecast = forecasts[clampedIndex]

  // Format time using project timezone offset if provided
  const formatTime = (timestamp: number) => {
    const offsetMinutes =
      timezoneOffsetSeconds !== undefined
        ? timezoneOffsetSeconds / 60
        : undefined
    const time =
      offsetMinutes !== undefined
        ? dayjs.unix(timestamp).utcOffset(offsetMinutes)
        : dayjs.unix(timestamp)
    return time.format('h:mm A')
  }

  const formatTimeShort = (timestamp: number) => {
    const offsetMinutes =
      timezoneOffsetSeconds !== undefined
        ? timezoneOffsetSeconds / 60
        : undefined
    const time =
      offsetMinutes !== undefined
        ? dayjs.unix(timestamp).utcOffset(offsetMinutes)
        : dayjs.unix(timestamp)
    const minutes = time.minute()
    return minutes === 0 ? time.format('h A') : time.format('h:mm A')
  }

  return (
    <Stack gap="md" py="xs">
      <Group justify="space-between" align="center">
        <Text size="xs" c="dimmed">
          {selectedForecast ? formatTime(selectedForecast.dt) : '--'}
        </Text>
        <Group gap="xs">
          <Text size="xs" c="dimmed">
            {isAnimating ? 'Auto' : 'Manual'}
          </Text>
          <Switch
            size="xs"
            checked={isAnimating}
            onChange={(e) => setIsAnimating(e.currentTarget.checked)}
            label="Animate"
          />
        </Group>
      </Group>
      <Slider
        value={sliderValue}
        onChange={(value) => {
          setSliderValue(value)
          setIsAnimating(false) // Stop animation when user manually adjusts
        }}
        min={0}
        max={maxSliderValue}
        step={0.01}
        marks={forecasts.map((forecast, index) => {
          const label = formatTimeShort(forecast.dt)
          return {
            value: index,
            label,
          }
        })}
        size="sm"
        label={null}
        styles={{
          markLabel: {
            fontSize: '10px',
            marginTop: '4px',
          },
          track: {
            marginTop: '8px',
            marginBottom: '8px',
          },
        }}
      />
    </Stack>
  )
}
