import dayjs from 'dayjs'
import { useSearchParams } from 'react-router-dom'

export function useValidateDateRange({
  maxDays,
}: {
  maxDays?: number
} = {}) {
  const [searchParams] = useSearchParams()

  const startParam = searchParams.get('start')
  const endParam = searchParams.get('end')

  let start = startParam ? dayjs(startParam) : null
  let end = endParam ? dayjs(endParam) : null

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
