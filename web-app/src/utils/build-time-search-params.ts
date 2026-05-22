import dayjs from 'dayjs'

type BuildTimeSearchParamsReturn = {
  start: Date
  end: Date
}

export function buildTimeSearchParams(
  searchParams: URLSearchParams,
): BuildTimeSearchParamsReturn {
  const startParam = searchParams.get('start')
  const endParam = searchParams.get('end')

  const start = startParam
    ? dayjs(startParam).startOf('day').toDate()
    : new Date()
  const end = endParam
    ? dayjs(endParam).endOf('day').toDate()
    : dayjs(start).endOf('day').toDate()

  return { start, end }
}
