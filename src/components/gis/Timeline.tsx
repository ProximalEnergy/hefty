import {
  Badge,
  Group,
  RangeSlider,
  SegmentedControl,
  Stack,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import dayjs from 'dayjs'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import timelineClasses from './Timeline.module.css'

const numDays = 30

const dateToNumber = (date: string) => {
  return dayjs(date).diff(dayjs(), 'day') + numDays + 1
}

const numberToDate = (number: number, format: string) => {
  return dayjs()
    .subtract(numDays + 1 - number, 'day')
    .format(format)
}

const Timeline = () => {
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme()
  const [searchParams, setSearchParams] = useSearchParams()

  // Parse start and end dates from URL
  // If not found default to the previous 7 days
  const paramStart = searchParams.get('start')
  const paramEnd = searchParams.get('end')
  const startNumber =
    paramStart !== null ? dateToNumber(paramStart) : numDays - 6
  const endNumber = paramEnd !== null ? dateToNumber(paramEnd) : numDays

  // Initialize the value of the slider
  const [value, setValue] = useState<[number, number]>([startNumber, endNumber])

  // On the first render, timeline is live if no start and end dates are provided
  const [isLive, setIsLive] = useState(paramStart === null && paramEnd === null)

  const segmentedData = ['Energy', 'Live Power']

  const [segmentedValue, setSegmentedValue] = useState(
    isLive ? segmentedData[1] : segmentedData[0],
  )

  // As the use changes the slider, the timeline is no longer live
  const handleOnChange = (value: [number, number]) => {
    setIsLive(false)
    setSegmentedValue(segmentedData[0])
    setValue(value)
  }

  // When the user stops changing the slider, update the URL
  const handleOnChangeEnd = (newEndValue: [number | null, number | null]) => {
    const newParams = new URLSearchParams(searchParams)
    if (newEndValue[0] !== null && newEndValue[1] !== null) {
      const start = numberToDate(newEndValue[0], 'YYYY-MM-DD')
      const end = numberToDate(newEndValue[1], 'YYYY-MM-DD')
      newParams.set('start', start)
      newParams.set('end', end)
    } else {
      newParams.delete('start')
      newParams.delete('end')
    }
    setSearchParams(newParams)
  }

  const handleSegmentedOnChange = (segmentedValue: string) => {
    setSegmentedValue(segmentedValue)
    if (segmentedValue === 'Live Power') {
      setIsLive(true)
      handleOnChangeEnd([null, null])
    } else {
      setIsLive(false)
      handleOnChangeEnd(value)
    }
  }

  const sliderColor = !isLive
    ? undefined
    : computedColorScheme === 'dark'
      ? theme.colors.dark[3]
      : theme.colors.gray[5]
  const badgeVariant = !isLive ? 'filled' : 'default'

  return (
    <Stack gap={5} align="center" w="100%">
      <RangeSlider
        color={sliderColor}
        w="100%"
        minRange={0}
        min={0}
        max={numDays}
        label={null}
        step={1}
        value={value}
        onChange={handleOnChange}
        onChangeEnd={handleOnChangeEnd}
        classNames={timelineClasses}
      />
      <Group w="100%" justify="space-between">
        <Badge variant={badgeVariant}>
          <span style={{ fontFamily: 'monospace' }}>
            {numberToDate(value[0], 'MM/DD')}
          </span>
        </Badge>
        <SegmentedControl
          size="xs"
          color={theme.primaryColor}
          value={segmentedValue}
          onChange={handleSegmentedOnChange}
          data={segmentedData}
        />
        <Badge variant={badgeVariant}>
          <span style={{ fontFamily: 'monospace' }}>
            {numberToDate(value[1], 'MM/DD')}
          </span>
        </Badge>
      </Group>
    </Stack>
  )
}

export default Timeline
