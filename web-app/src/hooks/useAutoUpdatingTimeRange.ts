import { getLast24HourTimeRange } from '@/utils/interval'
import { type Dispatch, type SetStateAction, useEffect } from 'react'

type UseAutoUpdatingTimeRangeOptions = {
  isAutoUpdating: boolean
  setEndTime: Dispatch<SetStateAction<string>>
  setStartTime: Dispatch<SetStateAction<string>>
  setTimeSeriesInterval: Dispatch<SetStateAction<string>>
}

export const useAutoUpdatingTimeRange = ({
  isAutoUpdating,
  setEndTime,
  setStartTime,
  setTimeSeriesInterval,
}: UseAutoUpdatingTimeRangeOptions) => {
  useEffect(() => {
    if (!isAutoUpdating) return

    const updateTimeRange = () => {
      const {
        startTime: newStartTime,
        endTime: newEndTime,
        interval: newInterval,
      } = getLast24HourTimeRange()

      setEndTime(newEndTime)
      setStartTime(newStartTime)
      setTimeSeriesInterval(newInterval)
    }

    updateTimeRange()

    const intervalId = window.setInterval(updateTimeRange, 60 * 1000)

    return () => window.clearInterval(intervalId)
  }, [isAutoUpdating, setEndTime, setStartTime, setTimeSeriesInterval])
}
