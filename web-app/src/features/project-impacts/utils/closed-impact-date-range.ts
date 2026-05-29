import dayjs from 'dayjs'

type ClosedImpactDateRange = {
  start: Date | dayjs.Dayjs | null | undefined
  end: Date | dayjs.Dayjs | null | undefined
}

export function buildClosedImpactDateRangeKey({
  start,
  end,
}: ClosedImpactDateRange) {
  if (!start || !end) {
    return null
  }

  return `${dayjs(start).format('YYYY-MM-DD')}:${dayjs(end).format(
    'YYYY-MM-DD',
  )}`
}

export function dateRangeDefaultsToIncludingClosed({
  start,
  end,
  today = dayjs(),
}: ClosedImpactDateRange & {
  today?: Date | dayjs.Dayjs
}) {
  if (!start || !end) {
    return false
  }

  return !(
    dayjs(start).isSame(dayjs(today), 'day') &&
    dayjs(end).isSame(dayjs(today), 'day')
  )
}
