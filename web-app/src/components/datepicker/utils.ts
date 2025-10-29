import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useSearchParams } from 'react-router'

dayjs.extend(utc)
dayjs.extend(timezone)

export function useValidateDateRange({
  maxDays,
  timeZone,
}: {
  maxDays?: number
  timeZone?: string
} = {}) {
  const [searchParams] = useSearchParams()

  const startParam = searchParams.get('start')
  const endParam = searchParams.get('end')

  let start = startParam
    ? timeZone
      ? dayjs.tz(startParam, timeZone)
      : dayjs(startParam)
    : null
  let end = endParam
    ? timeZone
      ? dayjs.tz(endParam, timeZone)
      : dayjs(endParam)
    : null

  if (start && end) {
    if (start.isAfter(end)) {
      start = end
    } else if (maxDays && end.diff(start, 'days') > maxDays) {
      start = end.subtract(maxDays, 'days')
    }
    end = end.add(1, 'day')
  }

  return {
    start,
    end,
  }
}
