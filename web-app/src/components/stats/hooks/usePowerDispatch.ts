import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetPTPData } from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useMemo } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)

export function usePowerDispatch(projectId: string) {
  const project = useSelectProject(projectId)

  const { startDate, endDate } = useMemo(() => {
    if (!project.data?.time_zone) {
      return { startDate: null, endDate: null }
    }
    const tz = project.data.time_zone
    const now = dayjs().tz(tz)
    const todayStart = now.startOf('day')
    const tomorrowEnd = todayStart.add(2, 'day')
    return {
      startDate: todayStart.toDate(),
      endDate: tomorrowEnd.toDate(),
    }
  }, [project.data?.time_zone])

  const { data: powerData, isLoading: powerLoading } = useGetPTPData({
    pathParams: { projectId },
    queryParams: {
      endpoint: 'Real-Time-Unit-Position',
      category: 'analysis',
      start: startDate ? dayjs(startDate).toISOString() : undefined,
      end: endDate ? dayjs(endDate).toISOString() : undefined,
    },
    queryOptions: {
      enabled: !!projectId && !!startDate && !!endDate,
    },
  })

  const { currentNetDispatch, sparklineData, dispatchState } = useMemo(() => {
    if (!powerData?.data || powerData.data.length === 0) {
      return {
        currentNetDispatch: null,
        sparklineData: [] as number[],
        dispatchState: null,
      }
    }
    const element =
      powerData.data.find(
        (el) =>
          el.definition === 'Generator' &&
          el.dataPoints?.some((dp) => dp.keyName === 'GEN_Production'),
      ) || powerData.data[0]
    if (!element) {
      return {
        currentNetDispatch: null,
        sparklineData: [] as number[],
        dispatchState: null,
      }
    }
    const genDP = element.dataPoints?.find(
      (dp) => dp.keyName === 'GEN_Production',
    )
    if (!genDP?.values?.length) {
      return {
        currentNetDispatch: null,
        sparklineData: [] as number[],
        dispatchState: null,
      }
    }
    const allValues: number[] = []
    genDP.values.forEach((v) => {
      const valStr = v.data?.[0]?.value
      if (valStr !== null && valStr !== undefined) {
        const num = parseFloat(String(valStr))
        if (!isNaN(num)) allValues.push(num)
      }
    })
    const latest = allValues.length > 0 ? allValues[allValues.length - 1] : null
    const spark = allValues.slice(-15)
    let state: string | null = null
    if (latest !== null) {
      const poi = project.data?.poi ?? 0
      const abs = Math.abs(latest)
      if (poi > 0 && abs < poi * 0.01) {
        state = 'Idling'
      } else {
        state = latest > 0 ? 'Discharging' : 'Charging'
      }
    }
    return {
      currentNetDispatch: latest,
      sparklineData: spark,
      dispatchState: state,
    }
  }, [powerData, project.data?.poi])

  const currentNetDispatchValue = useMemo(() => {
    if (powerLoading) return null
    if (currentNetDispatch === null) return 'N/A'
    const sign = currentNetDispatch >= 0 ? '+' : ''
    return `${sign}${currentNetDispatch.toFixed(2)} MW`
  }, [powerLoading, currentNetDispatch])

  return {
    currentNetDispatchValue,
    sparklineData,
    dispatchState,
    isLoading: powerLoading,
  }
}
