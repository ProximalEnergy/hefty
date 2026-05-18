import { KPITypeEnum } from '@/api/enumerations'
import { useGetKPISummaryCards } from '@/api/v1/operational/project/kpi_data'
import { useGetEquipmentAnalysisPCSv2 } from '@/api/v1/protected/web-application/projects/equipment-analysis/pv_inverter'
import { useValidateDateRange } from '@/components/datepicker/utils'
import { useResizePlotlyCharts } from '@/hooks/useResizePlotlyCharts'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useEffect, useMemo, useRef, useState } from 'react'

import type { PvInverterContext } from './use-pv-inverter-context'

dayjs.extend(utc)
dayjs.extend(timezone)

type UsePvInverterDayViewModelProps = {
  context: PvInverterContext
}

export function usePvInverterDayViewModel({
  context,
}: UsePvInverterDayViewModelProps) {
  const [sliderValue, setSliderValue] = useState(0)
  const [initialSliderValueSet, setInitialSliderValueSet] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [blockNormalize, setBlockNormalize] = useState(false)
  const [pcsNormalize, setPcsNormalize] = useState(false)
  const intervalRef = useRef<number | null>(null)
  const tabPanelRef = useRef<HTMLDivElement>(null)
  const { start, end } = useValidateDateRange({})

  const startQuery = useMemo(() => {
    if (!context.project || !start) {
      return undefined
    }
    return start.tz(context.project.time_zone, true).format('YYYY-MM-DD')
  }, [context.project, start])

  const endQuery = useMemo(() => {
    if (!context.project || !end) {
      return undefined
    }
    return end.tz(context.project.time_zone, true).toISOString()
  }, [context.project, end])

  const includeEnergy =
    (start && !start.isSame(dayjs().startOf('day'))) || false

  const { data: produced } = useGetKPISummaryCards({
    pathParams: { projectId: context.projectId || '-1' },
    queryParams: { kpi_type_ids: [KPITypeEnum.PROJECT_ENERGY_PRODUCTION] },
    queryOptions: { enabled: includeEnergy },
  })

  const data = useGetEquipmentAnalysisPCSv2({
    pathParams: { projectId: context.projectId || '-1' },
    queryParams: { start: startQuery, end: endQuery },
    queryOptions: { enabled: !!context.projectId },
  })

  const dataLength = data.data?.total_power_output.value.length
  const startISO = start?.toISOString()

  useEffect(() => {
    queueMicrotask(() => setInitialSliderValueSet(false))
    queueMicrotask(() => setSliderValue(0))
  }, [startISO])

  useEffect(() => {
    if (data.isLoading || initialSliderValueSet) {
      return
    }
    if (!dataLength) {
      queueMicrotask(() => setSliderValue(0))
      return
    }

    const isToday = start && start.isSame(dayjs().startOf('day'))
    if (isToday) {
      queueMicrotask(() => setSliderValue(dataLength - 1))
    } else {
      queueMicrotask(() => setSliderValue(Math.floor(dataLength / 2)))
    }
    queueMicrotask(() => setInitialSliderValueSet(true))
  }, [dataLength, data.isLoading, initialSliderValueSet, start, startISO])

  useEffect(() => {
    if (dataLength === 1) {
      queueMicrotask(() => setSliderValue(0))
    }
    if (isPlaying && dataLength) {
      intervalRef.current = window.setInterval(() => {
        queueMicrotask(() =>
          setSliderValue((prevValue) => (prevValue + 1) % dataLength),
        )
      }, 5000 / dataLength)
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [isPlaying, dataLength])

  useResizePlotlyCharts({
    containerRef: tabPanelRef,
    enabled: true,
  })

  const hasPCSModules =
    context.project?.spec.used_sensor_type_ids?.includes(3) ?? false
  const blockData = blockNormalize
    ? data.data?.block_power_distribution_norm
    : data.data?.block_power_distribution
  const pcsData = pcsNormalize
    ? data.data?.pcs_power_distribution_norm
    : data.data?.pcs_power_distribution

  const startLink = start?.subtract(3, 'day').format('YYYY-MM-DD')
  const endLink = dayjs(end).add(2, 'day').isBefore(dayjs())
    ? dayjs(end).add(2, 'day').format('YYYY-MM-DD')
    : dayjs().subtract(1, 'day').format('YYYY-MM-DD')

  const getTimeFromSliderValue = (value: number) => {
    const startOfDay = dayjs().tz(context.project?.time_zone).startOf('day')
    return startOfDay.add(value * 5, 'minute').format('HH:mm')
  }

  const togglePlay = () => {
    setIsPlaying((prev) => !prev)
  }

  return {
    tabPanelRef,
    startQuery,
    endQuery,
    data,
    dataLength,
    sliderValue,
    setSliderValue,
    getTimeFromSliderValue,
    isPlaying,
    togglePlay,
    blockNormalize,
    setBlockNormalize,
    pcsNormalize,
    setPcsNormalize,
    blockData,
    pcsData,
    hasPCSModules,
    includeEnergy,
    produced,
    startLink,
    endLink,
  }
}
