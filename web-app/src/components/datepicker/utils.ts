import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useSearchParams } from 'react-router'

dayjs.extend(utc)
dayjs.extend(timezone)

type QueryParamDateRangeOptions = {
  searchParams: URLSearchParams
  timeZone?: string
  maxDays?: number
  format?: string
  endExclusive?: boolean
}

type QueryParamDateRange = {
  start: dayjs.Dayjs | null
  end: dayjs.Dayjs | null
  startQuery?: string
  endQuery?: string
}

const DEFAULT_DATE_FORMAT = 'YYYY-MM-DD'

const parseQueryParamDate = (value: string | null, timeZone?: string) => {
  if (!value) {
    return null
  }
  return timeZone ? dayjs.tz(value, timeZone) : dayjs(value)
}

export function getQueryParamDateRange({
  searchParams,
  timeZone,
  maxDays,
  format = DEFAULT_DATE_FORMAT,
  endExclusive = true,
}: QueryParamDateRangeOptions): QueryParamDateRange {
  let start = parseQueryParamDate(searchParams.get('start'), timeZone)
  let end = parseQueryParamDate(searchParams.get('end'), timeZone)

  if (start && end) {
    if (start.isAfter(end)) {
      start = end
    } else if (maxDays && end.diff(start, 'days') > maxDays) {
      start = end.subtract(maxDays, 'days')
    }
  }

  const endAdjusted = endExclusive && end ? end.add(1, 'day') : end

  return {
    start,
    end,
    startQuery: start ? start.format(format) : undefined,
    endQuery: endAdjusted ? endAdjusted.format(format) : undefined,
  }
}

export function useValidateDateRange({
  maxDays,
  timeZone,
}: {
  maxDays?: number
  timeZone?: string
} = {}) {
  const [searchParams] = useSearchParams()

  const dateRange = getQueryParamDateRange({
    searchParams,
    timeZone,
    maxDays,
    endExclusive: false,
  })

  let end = dateRange.end
  if (dateRange.start && end) {
    end = end.add(1, 'day')
  }

  return {
    start: dateRange.start,
    end,
  }
}
