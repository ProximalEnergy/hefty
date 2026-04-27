import { Text } from '@mantine/core'
import dayjs from 'dayjs'
import timezonePlugin from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useEffect, useState } from 'react'

dayjs.extend(utc)
dayjs.extend(timezonePlugin)

export const CurrentTime = ({ timezone }: { timezone: string }) => {
  const TIME_FORMAT = 'MMM D, YYYY HH:mm:ss'
  const [currentTime, setCurrentTime] = useState(() =>
    dayjs().tz(timezone).format(TIME_FORMAT),
  )

  useEffect(() => {
    const updateTime = () =>
      setCurrentTime(dayjs().tz(timezone).format(TIME_FORMAT))
    updateTime()
    const interval = setInterval(updateTime, 1000)

    return () => clearInterval(interval)
  }, [timezone])

  return (
    <Text size="sm" style={{ fontFamily: 'monospace' }}>
      {currentTime}
    </Text>
  )
}
