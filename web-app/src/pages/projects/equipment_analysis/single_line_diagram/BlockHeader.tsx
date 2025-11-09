import { TimestampPicker } from '@/components/datepicker/TimestampPicker'
import { StatsGrid } from '@/components/stats/StatsGrid'
import { Device } from '@/hooks/types'
import {
  Box,
  Button,
  Group,
  Select,
  Slider,
  Stack,
  Title,
  Tooltip,
} from '@mantine/core'
import {
  IconGripHorizontal,
  IconInfoCircle,
  IconPlayerRecordFilled,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { Dispatch, SetStateAction, useEffect, useMemo, useRef } from 'react'

dayjs.extend(isSameOrBefore)
dayjs.extend(timezone)
dayjs.extend(utc)

const MIN_ZOOM_HOURS = 2
const MAX_ZOOM_DAYS = 30

const getSnapMinutes = (
  viewStartDate: dayjs.Dayjs,
  viewEndDate: dayjs.Dayjs,
): number => {
  const rangeInDays = viewEndDate.diff(viewStartDate, 'day')
  if (rangeInDays > 6) {
    return 10
  }
  if (rangeInDays > 1) {
    return 5
  }
  return 1
}

const snapValueToIncrement = (
  value: number,
  incrementMinutes: number,
  timezone: string,
): dayjs.Dayjs => {
  const d = dayjs.tz(value, timezone)
  const roundedMinutes =
    Math.round(d.minute() / incrementMinutes) * incrementMinutes
  return d.minute(roundedMinutes).second(0).millisecond(0)
}

type BlockHeaderProps = {
  timezone?: string
  blockDevices?: Device[]
  selectedBlockId?: number | null
  setSelectedBlockId?: Dispatch<SetStateAction<number | null>>
  timestamp: dayjs.Dayjs
  setTimestamp: Dispatch<SetStateAction<dayjs.Dayjs | null>>
  isLive: boolean
  setIsLive: Dispatch<SetStateAction<boolean>>
  viewStartDate: dayjs.Dayjs
  setViewStartDate: Dispatch<SetStateAction<dayjs.Dayjs | null>>
  hideTitle?: boolean
  viewEndDate: dayjs.Dayjs
  setViewEndDate: Dispatch<SetStateAction<dayjs.Dayjs | null>>
  projectAvgSoc: number | null
  socDelta: number | null
  projectAvgSoh: number | null
  sohDelta: number | null
  projectAvgCellTemp: number | null
  cellTempDelta: number | null
  isFetching: boolean
  activePcsCount: { active: number; total: number } | null
}

export const BlockHeader = ({
  timezone = 'America/Chicago',
  blockDevices,
  selectedBlockId,
  setSelectedBlockId,
  timestamp,
  setTimestamp,
  isLive,
  setIsLive,
  viewStartDate,
  setViewStartDate,
  hideTitle = false,
  viewEndDate,
  setViewEndDate,
  projectAvgSoc,
  socDelta,
  projectAvgSoh,
  sohDelta,
  projectAvgCellTemp,
  cellTempDelta,
  isFetching,
  activePcsCount,
}: BlockHeaderProps) => {
  const sliderContainerRef = useRef<HTMLDivElement>(null)

  // Reset selected block if it doesn't exist in the new project context
  useEffect(() => {
    if (
      selectedBlockId !== null &&
      setSelectedBlockId &&
      blockDevices &&
      !blockDevices.some((device) => device.device_id === selectedBlockId)
    ) {
      setSelectedBlockId(null)
    }
  }, [blockDevices, selectedBlockId, setSelectedBlockId])

  // This effect handles the "live" mode ticking
  useEffect(() => {
    if (isLive) {
      const interval = setInterval(() => {
        const newNow = dayjs().tz(timezone).second(0).millisecond(0)
        const range = viewEndDate.valueOf() - viewStartDate.valueOf()

        setTimestamp(newNow)
        setViewEndDate(newNow)
        setViewStartDate(newNow.subtract(range, 'ms'))
      }, 10000) // 10 seconds

      return () => clearInterval(interval)
    }
  }, [
    isLive,
    viewStartDate,
    viewEndDate,
    timezone,
    setTimestamp,
    setViewEndDate,
    setViewStartDate,
  ])

  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault()
      setIsLive(false) // Zooming disables live mode

      const zoomFactor = 1.1
      const currentRange = viewEndDate.valueOf() - viewStartDate.valueOf()
      const thumbRatio =
        currentRange > 0
          ? (timestamp.valueOf() - viewStartDate.valueOf()) / currentRange
          : 0.5

      let newRange: number
      if (e.deltaY < 0) {
        // Zoom in
        newRange = currentRange / zoomFactor
        if (newRange < MIN_ZOOM_HOURS * 60 * 60 * 1000) return
      } else {
        // Zoom out
        newRange = currentRange * zoomFactor
        if (newRange > MAX_ZOOM_DAYS * 24 * 60 * 60 * 1000) return
      }

      let newStartDate = dayjs.tz(
        timestamp.valueOf() - thumbRatio * newRange,
        timezone,
      )
      let newEndDate = newStartDate.add(newRange, 'ms')

      const freshNow = dayjs().tz(timezone)
      if (newEndDate.isAfter(freshNow)) {
        const offset = newEndDate.diff(freshNow)
        newEndDate = freshNow
        newStartDate = newStartDate.subtract(offset, 'ms')
      }

      setViewStartDate(newStartDate)
      setViewEndDate(newEndDate)
    }

    const sliderElement = sliderContainerRef.current
    if (sliderElement) {
      sliderElement.addEventListener('wheel', handleWheel as EventListener, {
        passive: false,
      })
    }

    return () => {
      if (sliderElement) {
        sliderElement.removeEventListener('wheel', handleWheel as EventListener)
      }
    }
  }, [
    timestamp,
    viewStartDate,
    viewEndDate,
    timezone,
    setIsLive,
    setViewStartDate,
    setViewEndDate,
  ])

  const marks = useMemo(() => {
    const marksArray: { value: number; label: string }[] = []
    const rangeHours = viewEndDate.diff(viewStartDate, 'hour')

    if (rangeHours <= 72) {
      // Up to 3 days
      const increment = rangeHours <= 12 ? 1 : 6 // 1hr for <12h, 6hrs for <72h
      const format =
        viewStartDate.format('M/D') === viewEndDate.format('M/D')
          ? 'HH:mm'
          : 'M/D HH:mm'

      const startHour = viewStartDate.hour()
      // Round up to the next mark
      let initialTime = viewStartDate
        .hour(Math.ceil(startHour / increment) * increment)
        .minute(0)
        .second(0)

      // If the first mark is before or at the start time, move to the next one
      if (initialTime.isSameOrBefore(viewStartDate)) {
        initialTime = initialTime.add(increment, 'hour')
      }

      for (
        let time = initialTime;
        time.isBefore(viewEndDate);
        time = time.add(increment, 'hour')
      ) {
        marksArray.push({
          value: time.valueOf(),
          label: time.format(format),
        })
      }
    } else {
      // More than 3 days
      const increment = 1 // days
      const format = 'M/D'
      const initialTime = viewStartDate.startOf('day').add(1, 'day')
      for (
        let time = initialTime;
        time.isBefore(viewEndDate);
        time = time.add(increment, 'day')
      ) {
        marksArray.push({
          value: time.valueOf(),
          label: time.format(format),
        })
      }
    }

    if (isLive) {
      // Remove last mark if it's too close to 'Now' to avoid overlap
      const lastMark = marksArray[marksArray.length - 1]
      if (lastMark) {
        const rangeMs = viewEndDate.valueOf() - viewStartDate.valueOf()
        if (
          rangeMs > 0 &&
          (viewEndDate.valueOf() - lastMark.value) / rangeMs < 0.05
        ) {
          marksArray.pop()
        }
      }
      marksArray.push({ value: viewEndDate.valueOf(), label: 'Now' })
    }

    return marksArray
  }, [viewStartDate, viewEndDate, isLive])

  const blockOptions = useMemo(() => {
    return (
      blockDevices?.map((device) => ({
        value: device.device_id.toString(),
        label: device.name_full || `Block ${device.device_id}`,
      })) || []
    )
  }, [blockDevices])

  return (
    <Stack>
      {/* Top Header */}
      <Group justify="space-between">
        <Group>
          {!hideTitle && (
            <>
              <Title order={1}>Snapshot</Title>
              <Tooltip
                label="Interactive Single-Line Diagram snapshot of your project's energy storage system. Select a block, choose a timestamp, or zoom to explore live or historical telemetry."
                withArrow
                multiline
              >
                <IconInfoCircle
                  size={18}
                  style={{ cursor: 'pointer' }}
                  stroke={1.5}
                />
              </Tooltip>
            </>
          )}
          {blockDevices && setSelectedBlockId && (
            <Select
              data={blockOptions}
              value={selectedBlockId?.toString() || null}
              onChange={(value) => {
                if (value) {
                  setSelectedBlockId(parseInt(value, 10))
                }
              }}
            />
          )}
        </Group>
        <Group>
          <TimestampPicker
            value={timestamp.toDate()}
            onChange={(date) => {
              if (date) {
                const newTimestamp = dayjs(date).tz(timezone, true)
                setTimestamp(newTimestamp)
                setIsLive(false)

                const currentRange = viewEndDate.diff(viewStartDate) // in ms
                let newViewStartDate = newTimestamp.subtract(
                  currentRange / 2,
                  'ms',
                )
                let newViewEndDate = newTimestamp.add(currentRange / 2, 'ms')

                const freshNow = dayjs().tz(timezone)
                if (newViewEndDate.isAfter(freshNow)) {
                  const offset = newViewEndDate.diff(freshNow)
                  newViewEndDate = freshNow
                  newViewStartDate = newViewStartDate.subtract(offset, 'ms')
                }

                setViewStartDate(newViewStartDate)
                setViewEndDate(newViewEndDate)
              }
            }}
            maxDate={dayjs().tz(timezone).toDate()}
            timezone={timezone}
          />
          <Button variant="default">SLD</Button>
        </Group>
      </Group>

      {/* Timeline Slider */}
      <Box ref={sliderContainerRef} px="xl" pt="xl" pb="xl">
        <Slider
          min={viewStartDate.valueOf()}
          max={viewEndDate.valueOf()}
          value={timestamp.valueOf()}
          onChange={(value) => {
            const snapMinutes = getSnapMinutes(viewStartDate, viewEndDate)
            const snappedTimestamp = snapValueToIncrement(
              value,
              snapMinutes,
              timezone,
            )
            setTimestamp(snappedTimestamp)
            if (value < viewEndDate.valueOf()) {
              setIsLive(false)
            }
          }}
          onChangeEnd={(value) => {
            const snapMinutes = getSnapMinutes(viewStartDate, viewEndDate)
            const snappedTimestamp = snapValueToIncrement(
              value,
              snapMinutes,
              timezone,
            )
            setTimestamp(snappedTimestamp) // Set final snapped value
            // If dragged to the very end (or slightly past due to float math), re-enable live
            if (value >= viewEndDate.valueOf()) {
              const isRangeCurrent =
                dayjs().tz(timezone).diff(viewEndDate, 'seconds') < 10
              if (isRangeCurrent) {
                setIsLive(true)
                setTimestamp(viewEndDate) // Snap to the end
              }
            }
          }}
          marks={marks}
          thumbChildren={
            isLive ? (
              <IconPlayerRecordFilled size="1.2rem" color="green" />
            ) : (
              <IconGripHorizontal size="1.2rem" stroke={1.5} />
            )
          }
          label={(value) =>
            isLive && value >= viewEndDate.valueOf() - 1000 // Tolerance
              ? 'Now'
              : dayjs.tz(value, timezone).format('YYYY-MM-DD HH:mm')
          }
        />
      </Box>

      {/* Stats Bar */}
      <StatsGrid
        data={[
          {
            title: 'Events',
            icon: 'events',
            value: '0',
            description: 'Total number of open events for this scope.',
          },
          {
            title: 'PCS Active',
            icon: 'pcs',
            value: activePcsCount
              ? `${activePcsCount.active}/${activePcsCount.total}`
              : 'N/A',
            description:
              'Number of active Power Conversion Systems (PCS) with non-zero active or reactive power.',
          },
          {
            title: 'Cell Temperature (avg)',
            icon: 'temp',
            value:
              projectAvgCellTemp !== null
                ? `${projectAvgCellTemp.toFixed(1)} °C`
                : 'N/A',
            diff: cellTempDelta ?? undefined,
            description:
              'Average cell temperature of all strings. The value next to it is the spread (max - min) between strings.',
          },
          {
            title: 'SOC (avg)',
            icon: 'soc',
            value:
              projectAvgSoc !== null
                ? `${(projectAvgSoc * 100).toFixed(1)}%`
                : 'N/A',
            diff: socDelta ?? undefined,
            description:
              'Average State of Charge (SOC) of all banks. The value next to it is the spread (max - min) between banks.',
          },
          {
            title: 'SOH (avg)',
            icon: 'soh',
            value:
              projectAvgSoh !== null ? `${projectAvgSoh.toFixed(1)}%` : 'N/A',
            diff: sohDelta ?? undefined,
            description:
              'Average State of Health (SOH) calculated from all bank-level SOH values. The value next to it is the spread (max - min) between banks.',
          },
        ]}
        isLoading={isFetching}
      />
    </Stack>
  )
}
