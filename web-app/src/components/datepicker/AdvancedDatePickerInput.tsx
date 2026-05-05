import {
  Button,
  Group,
  MantineSize,
  MantineStyleProps,
  Popover,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core'
import { DatePicker, DatesProvider } from '@mantine/dates'
import {
  IconChevronLeft,
  IconChevronRight,
  IconChevronsLeft,
  IconChevronsRight,
  IconX,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import duration from 'dayjs/plugin/duration'
import quarterOfYear from 'dayjs/plugin/quarterOfYear'
import updateLocale from 'dayjs/plugin/updateLocale'
import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'

import DateCombobox, { DurationUnit, Limits } from './CustomCombobox'

dayjs.extend(duration)
dayjs.extend(quarterOfYear)
dayjs.extend(updateLocale)
dayjs.updateLocale('en', {
  weekStart: 1,
})

type DurationTerms =
  | 'today'
  | 'yesterday'
  | 'past-2-days'
  | 'past-3-days'
  | 'past-week'
  | 'past-month'
  | 'past-year'
  | 'last-week'
  | 'last-month'
  | 'last-quarter'
  | 'last-year'
  | 'ytd'

const durationTermToName: Record<DurationTerms, string> = {
  today: 'Today',
  yesterday: 'Yesterday',
  'past-2-days': 'Past 2 Days',
  'past-3-days': 'Past 3 Days',
  'past-week': 'Past Week',
  'past-month': 'Past Month',
  'past-year': 'Past Year',
  'last-week': 'Last Week',
  'last-month': 'Last Month',
  'last-quarter': 'Last Quarter',
  'last-year': 'Last Year',
  ytd: 'YTD',
}

const defaultLimits: Limits = {
  day: 365,
  week: 52,
  month: 12,
  quarter: 4,
  year: 1,
}

const INCREMENT_SMALL = 1
const INCREMENT_LARGE_MIN = 2
const PX = 0
const POPOVER_Z_INDEX = 500
const STROKE = 1.5
const QUICK_ACTION_BUTTON_VARIANT = 'light'
const EMPTY_STRING = ''

export function AdvancedDatePicker({
  includeClearButton = true,
  includeIncrementButtons = true,
  includeTodayInDateRange = false,
  size = 'sm',
  width,
  limits = defaultLimits,
  maxDays,
  disableInput = false,
  disableQuickActions = false,
  defaultRange,
  startParamKey = 'start',
  endParamKey = 'end',
}: {
  includeClearButton?: boolean
  includeIncrementButtons?: boolean
  includeTodayInDateRange?: boolean
  size?: MantineSize | `compact-${MantineSize}`
  width?: MantineStyleProps['w']
  limits?: Partial<Limits>
  maxDays?: number
  disableInput?: boolean
  disableQuickActions?: boolean | DurationTerms[]
  defaultRange?: DurationTerms
  startParamKey?: string
  endParamKey?: string
}) {
  // State used to manage Popover containing DatePicker
  // NOTE: Because we are using a DatePicker instead of a DatePickerInput, we
  // don't get automatic Popover auto-close behavior after selecting a date
  // range.
  const [popoverOpened, setPopoverOpened] = useState(false)

  const [searchParams, setSearchParams] = useSearchParams()

  // Parse start and end dates from URL search params
  const startParam = searchParams.get(startParamKey)
  const endParam = searchParams.get(endParamKey)

  // Convert start and end dates to Date objects, or null if not present
  const start = startParam ? dayjs(startParam).toDate() : null
  const end = endParam ? dayjs(endParam).toDate() : null

  // State to manage *just* the DatePicker UI
  const [dateRange, setDateRange] = useState<[Date | null, Date | null]>([
    start,
    end,
  ])

  let maxDate
  let minDate

  // If only one date is selected, base maxDate and minDate on that date
  // NOTE: maxDate and minDate are used for Mantine calendar UI
  if (dateRange[0] && !dateRange[1]) {
    const endDate = dayjs()
      .startOf('day')
      .subtract(includeTodayInDateRange ? 0 : 1, 'day')

    if (
      dayjs(dateRange[0])
        .add(maxDays ?? 0, 'day')
        .isAfter(endDate)
    ) {
      maxDate = endDate.toDate()
    } else {
      if (maxDays === undefined) {
        maxDate = endDate.toDate()
      } else {
        maxDate = dayjs(dateRange[0])
          .add(maxDays, 'day')
          .subtract(1, 'day')
          .toDate()
      }
    }

    if (maxDays === undefined) {
      minDate = undefined
    } else {
      minDate = dayjs(dateRange[0])
        .subtract(maxDays ?? 0, 'day')
        .add(1, 'day')
        .toDate()
    }
  } else {
    minDate = undefined
    maxDate = dayjs()
      .startOf('day')
      .subtract(includeTodayInDateRange ? 0 : 1, 'day')
      .toDate()
  }

  const defaultQuickActions: DurationTerms[] = [
    'past-week',
    'past-month',
    'last-week',
    'last-month',
    'last-quarter',
    'last-year',
    'ytd',
  ]

  const quickActions =
    disableQuickActions === true
      ? []
      : Array.isArray(disableQuickActions)
        ? defaultQuickActions.filter(
            (term) => !disableQuickActions.includes(term),
          )
        : defaultQuickActions

  const setDateParams = useCallback(
    ([startDate, endDate]: [Date | null, Date | null]) => {
      const nextParams = new URLSearchParams(searchParams)
      if (startDate) {
        nextParams.set(startParamKey, dayjs(startDate).format('YYYY-MM-DD'))
      } else {
        nextParams.delete(startParamKey)
      }
      if (endDate) {
        nextParams.set(endParamKey, dayjs(endDate).format('YYYY-MM-DD'))
      } else {
        nextParams.delete(endParamKey)
      }

      setSearchParams(nextParams, { replace: true })
    },
    [endParamKey, searchParams, setSearchParams, startParamKey],
  )

  const setDateRangeByTerm = useCallback(
    (term: DurationTerms) => {
      let today = dayjs().startOf('day')
      if (!includeTodayInDateRange) {
        today = today.subtract(1, 'day')
      }
      let startValue: Date | null = null
      let endValue: Date | null = null

      switch (term) {
        case 'today':
          startValue = today.toDate()
          endValue = today.toDate()
          break
        case 'yesterday':
          startValue = today.subtract(1, 'day').toDate()
          endValue = today.subtract(1, 'day').toDate()
          break
        case 'past-2-days':
          // Explicitly set to yesterday through today, regardless of includeTodayInDateRange
          startValue = today.subtract(1, 'day').toDate()
          endValue = today.toDate()
          break
        case 'past-3-days':
          startValue = today.subtract(3, 'day').add(1, 'day').toDate()
          endValue = today.toDate()
          break
        case 'past-week':
          startValue = today.subtract(1, 'week').add(1, 'day').toDate()
          endValue = today.toDate()
          break
        case 'past-month':
          startValue = today.subtract(1, 'month').add(1, 'day').toDate()
          endValue = today.toDate()
          break
        case 'past-year':
          startValue = today.subtract(1, 'year').add(1, 'day').toDate()
          endValue = today.toDate()
          break
        case 'last-week':
          startValue = today.subtract(1, 'week').startOf('week').toDate()
          endValue = today.subtract(1, 'week').endOf('week').toDate()
          break
        case 'last-month':
          startValue = today.subtract(1, 'month').startOf('month').toDate()
          endValue = today.subtract(1, 'month').endOf('month').toDate()
          break
        case 'last-quarter':
          startValue = today.subtract(1, 'quarter').startOf('quarter').toDate()
          endValue = today.subtract(1, 'quarter').endOf('quarter').toDate()
          break
        case 'last-year':
          startValue = today.subtract(1, 'year').startOf('year').toDate()
          endValue = today.subtract(1, 'year').endOf('year').toDate()
          break
        case 'ytd':
          startValue = today.startOf('year').toDate()
          endValue = today.toDate()
          break
      }

      setPopoverOpened(false)
      setDateParams([startValue, endValue])
    },
    [includeTodayInDateRange, setDateParams],
  )

  useEffect(() => {
    // If no start and end are present, set them based on defaultRange
    if (!startParam && !endParam && defaultRange) {
      queueMicrotask(() => setDateRangeByTerm(defaultRange))
    } else {
      queueMicrotask(() => setDateRange([start, end]))
    }
    // oxlint-disable-next-line react/exhaustive-deps
  }, [startParam, endParam, defaultRange, setDateRangeByTerm])

  function onDateRangeChange(value: [Date | null, Date | null]) {
    setDateRange(value)
    if (value[0] && value[1]) {
      setDateParams(value)
      setPopoverOpened(false)
    }
  }

  function incrementDateRange(days: number) {
    const newStart =
      dateRange[0] && dayjs(dateRange[0]).add(days, 'day').toDate()
    const newEnd = dateRange[1] && dayjs(dateRange[1]).add(days, 'day').toDate()
    if (newStart && newEnd) {
      setDateParams([newStart, newEnd])
    }
  }

  const handleComboboxSubmit = (value: string) => {
    const match = value.match(/^(\d+)\s*([a-zA-Z]*)$/)
    if (match) {
      let number = parseInt(match[1], 10)
      let unit = match[2] as DurationUnit

      if (unit === 'week') {
        unit = 'day'
        number *= 7
      }
      if (unit === 'quarter') {
        unit = 'month'
        number *= 3
      }

      let today = dayjs().startOf('day')
      if (!includeTodayInDateRange) {
        today = today.subtract(1, 'day')
      }

      const newStart = today.subtract(number, unit).add(1, 'day').toDate()
      const newEnd = today.toDate()
      setDateParams([newStart, newEnd])
      setPopoverOpened(false)
    }
  }

  const mergedLimits = { ...defaultLimits, ...limits }

  const empty = start === null && end === null

  // Add this helper function to format the date display
  function formatDateDisplay() {
    if (empty) {
      if (maxDays === 1) {
        return 'Select Date'
      } else {
        return 'Select Date Range'
      }
    }

    if (maxDays === 1) {
      return start
        ? dayjs(start).format('YYYY/MM/DD')
        : EMPTY_STRING.padEnd(10, '\u00A0')
    }

    return (
      (start && dayjs(start).format('YYYY/MM/DD')) +
      ' - ' +
      (end
        ? dayjs(end).format('YYYY/MM/DD')
        : EMPTY_STRING.padEnd(10, '\u00A0'))
    )
  }

  // Add this helper function to check if the range ends today
  const isEndToday = () => {
    if (!end) return false
    const today = dayjs().startOf('day')
    const endDate = dayjs(end).startOf('day')
    return (
      endDate.isSame(today) ||
      (!includeTodayInDateRange && endDate.isSame(today.subtract(1, 'day')))
    )
  }

  const getRangeShiftDays = () => {
    if (maxDays === 1) {
      return INCREMENT_SMALL
    }

    if (!start || !end) {
      return INCREMENT_SMALL
    }

    return (
      dayjs(end).startOf('day').diff(dayjs(start).startOf('day'), 'day') + 1
    )
  }

  const getMaxForwardDays = (desiredDays: number) => {
    if (!end) return desiredDays
    const today = dayjs().startOf('day')
    const endDate = dayjs(end).startOf('day')
    const adjustedToday = includeTodayInDateRange
      ? today
      : today.subtract(1, 'day')

    if (endDate.isAfter(adjustedToday)) return 0

    const daysUntilToday = adjustedToday.diff(endDate, 'day')
    return Math.min(desiredDays, daysUntilToday)
  }

  const rangeShiftDays = Math.max(INCREMENT_LARGE_MIN, getRangeShiftDays())

  return (
    <Button.Group w={width}>
      {includeIncrementButtons && (
        <>
          <Tooltip
            label={`Shift ${
              maxDays === 1 ? 'date' : 'range'
            } back by ${rangeShiftDays} ${
              rangeShiftDays === 1 ? 'day' : 'days'
            }`}
            disabled={empty}
          >
            <Button
              size={size}
              px={PX}
              variant="default"
              disabled={empty}
              onClick={() => {
                incrementDateRange(-rangeShiftDays)
              }}
            >
              <IconChevronsLeft stroke={STROKE} />
            </Button>
          </Tooltip>
          <Tooltip
            label={`Shift ${
              maxDays === 1 ? 'date' : 'range'
            } back by ${INCREMENT_SMALL} day`}
            disabled={empty}
          >
            <Button
              size={size}
              px={PX}
              variant="default"
              disabled={empty}
              onClick={() => {
                incrementDateRange(-INCREMENT_SMALL)
              }}
            >
              <IconChevronLeft stroke={STROKE} />
            </Button>
          </Tooltip>
        </>
      )}
      <Popover
        opened={popoverOpened}
        onChange={setPopoverOpened}
        zIndex={POPOVER_Z_INDEX}
      >
        <Popover.Target>
          <Button
            size={size}
            flex={width ? 1 : undefined}
            px={'xs'}
            variant="default"
            ff="monospace"
            disabled={disableInput}
            onClick={() => setPopoverOpened((o) => !o)}
          >
            <Text w="23ch" size={size}>
              {formatDateDisplay()}
            </Text>
          </Button>
        </Popover.Target>
        <Popover.Dropdown>
          <Stack gap="xs">
            <Group gap="xs">
              <DatesProvider settings={{ consistentWeeks: true }}>
                {maxDays === 1 ? (
                  <DatePicker
                    minDate={minDate}
                    maxDate={maxDate}
                    value={dateRange[0]}
                    onChange={(value) =>
                      onDateRangeChange([
                        value ? new Date(value) : null,
                        value ? new Date(value) : null,
                      ])
                    }
                  />
                ) : (
                  <DatePicker
                    type="range"
                    allowSingleDateInRange
                    minDate={minDate}
                    maxDate={maxDate}
                    value={dateRange}
                    onChange={(values) =>
                      onDateRangeChange([
                        values[0] ? new Date(values[0]) : null,
                        values[1] ? new Date(values[1]) : null,
                      ])
                    }
                  />
                )}
              </DatesProvider>
              <Stack gap="xs" align="center">
                {quickActions.map((term) => (
                  <Button
                    key={term}
                    size="compact-xs"
                    variant={QUICK_ACTION_BUTTON_VARIANT}
                    fullWidth
                    onClick={() => setDateRangeByTerm(term)}
                  >
                    {durationTermToName[term]}
                  </Button>
                ))}
              </Stack>
            </Group>
            <DateCombobox
              limits={mergedLimits}
              onOptionSubmit={handleComboboxSubmit} // Pass the handler to the DateCombobox
              activate={popoverOpened} // Add this prop to control activation
            />
          </Stack>
        </Popover.Dropdown>
      </Popover>
      {includeClearButton && (
        <Button
          size={size}
          px={PX}
          variant="default"
          disabled={empty}
          onClick={() => {
            setDateParams([null, null])
          }}
        >
          <IconX stroke={1} />
        </Button>
      )}
      {includeIncrementButtons && (
        <>
          <Tooltip
            label={`Shift ${
              maxDays === 1 ? 'date' : 'range'
            } forward by ${INCREMENT_SMALL} day`}
            disabled={empty || isEndToday()}
          >
            <Button
              size={size}
              px={PX}
              variant="default"
              disabled={empty || isEndToday()}
              onClick={() => {
                incrementDateRange(INCREMENT_SMALL)
              }}
            >
              <IconChevronRight stroke={STROKE} />
            </Button>
          </Tooltip>
          <Tooltip
            label={`Shift ${
              maxDays === 1 ? 'date' : 'range'
            } forward by up to ${rangeShiftDays} ${
              rangeShiftDays === 1 ? 'day' : 'days'
            }`}
            disabled={empty || isEndToday()}
          >
            <Button
              size={size}
              px={PX}
              variant="default"
              disabled={empty || isEndToday()}
              onClick={() => {
                const forwardDays = getMaxForwardDays(rangeShiftDays)
                incrementDateRange(forwardDays)
              }}
            >
              <IconChevronsRight stroke={STROKE} />
            </Button>
          </Tooltip>
        </>
      )}
    </Button.Group>
  )
}
