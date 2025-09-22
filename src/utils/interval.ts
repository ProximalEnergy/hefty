export const getInterval = (start: string, end: string): string => {
  const startTime = new Date(start)
  const endTime = new Date(end)

  const diffInMinutes = (endTime.getTime() - startTime.getTime()) / (1000 * 60)

  if (diffInMinutes <= 300) {
    return '1min'
  } else if (diffInMinutes <= 300 * 5) {
    return '5min'
  } else {
    return '15min'
  }
}

export const roundTime = (
  time: string,
  interval: string,
  direction: 'up' | 'down',
): string => {
  const date = new Date(time)
  const intervalValue = interval === '1min' ? 1 : interval === '5min' ? 5 : 15
  const minutes = date.getMinutes()
  const roundedMinutes =
    direction === 'down'
      ? Math.floor(minutes / intervalValue) * intervalValue
      : Math.ceil(minutes / intervalValue) * intervalValue
  date.setMinutes(roundedMinutes)
  date.setSeconds(0)
  date.setMilliseconds(0)
  return date.toISOString()
}
