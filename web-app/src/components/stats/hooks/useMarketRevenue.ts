import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetPTPData } from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useMemo } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)

export function useMarketRevenue(projectId: string) {
  const project = useSelectProject(projectId)

  const { revenueStartDate, revenueEndDate } = useMemo(() => {
    if (!project.data?.time_zone) {
      return {
        revenueStartDate: null,
        revenueEndDate: null,
      }
    }
    const tz = project.data.time_zone
    const now = dayjs().tz(tz)
    return {
      revenueStartDate: now.startOf('day').toDate(),
      revenueEndDate: now.endOf('day').toDate(),
    }
  }, [project.data?.time_zone])

  const { data: batterySettlementData, isLoading } = useGetPTPData({
    pathParams: { projectId },
    queryParams: {
      endpoint: 'Battery-Settlement-Details',
      category: 'settlement',
      start: revenueStartDate
        ? dayjs(revenueStartDate).toISOString()
        : undefined,
      end: revenueEndDate ? dayjs(revenueEndDate).toISOString() : undefined,
    },
    queryOptions: {
      enabled: !!projectId && !!revenueStartDate && !!revenueEndDate,
    },
  })

  const {
    rtRevenue,
    daRevenue,
    daASRevenue,
    realizedRevenue,
    unrealizedRevenue,
  } = useMemo(() => {
    const empty = {
      rtRevenue: null as number | null,
      daRevenue: null as number | null,
      daASRevenue: null as number | null,
      realizedRevenue: null as number | null,
      unrealizedRevenue: null as number | null,
    }
    if (!batterySettlementData?.data?.length) return empty
    const el = batterySettlementData.data[0]
    if (!el?.dataPoints) return empty

    const rtDP = el.dataPoints.find((dp) => dp.keyName === 'RT_Energy_Amt')
    const daDP = el.dataPoints.find((dp) => dp.keyName === 'DA_Energy_Amt')
    const asKeys = [
      'DA_Reg_Up_Amt',
      'DA_Reg_Down_Amt',
      'DA_RRS_Amt',
      'DA_NS_Amt',
      'DA_ECRS_Amt',
    ]
    const asDPs = asKeys.map((k) =>
      el.dataPoints?.find((dp) => dp.keyName === k),
    )

    const tz = project.data?.time_zone
    const nowTz = tz ? dayjs().tz(tz) : dayjs()
    const nowUtc = dayjs.utc()
    const dayStart = nowTz.startOf('day')
    const dayEnd = nowTz.endOf('day')

    let rtTotal = 0
    let daRealized = 0
    let daUnrealized = 0
    let daASRealized = 0
    let daASUnrealized = 0

    const sumVals = (
      dp: typeof rtDP,
      cb: (v: number, isRealized: boolean) => void,
    ) => {
      dp?.values?.forEach((val) => {
        const intStart = tz
          ? dayjs(val.intervalStartUtc).tz(tz)
          : dayjs(val.intervalStartUtc)
        if (intStart.isBefore(dayStart) || intStart.isAfter(dayEnd)) return
        const str = val.data?.[0]?.value
        if (str === null || str === undefined) return
        const n = parseFloat(String(str))
        if (isNaN(n)) return
        const realized = dayjs.utc(val.intervalStartUtc).isBefore(nowUtc)
        cb(n, realized)
      })
    }

    sumVals(rtDP, (n) => {
      rtTotal += n
    })
    sumVals(daDP, (n, realized) => {
      if (realized) daRealized += n
      else daUnrealized += n
    })
    asDPs.forEach((dp) => {
      sumVals(dp, (n, realized) => {
        if (realized) daASRealized += n
        else daASUnrealized += n
      })
    })

    const daTotal = daRealized + daUnrealized + daASRealized + daASUnrealized
    return {
      rtRevenue: rtTotal,
      daRevenue: daTotal,
      daASRevenue: daASRealized + daASUnrealized,
      realizedRevenue: rtTotal + daRealized + daASRealized,
      unrealizedRevenue: daUnrealized + daASUnrealized,
    }
  }, [batterySettlementData, project.data])

  const revenueDate = useMemo(() => {
    if (!project.data?.time_zone) return ''
    const tz = project.data.time_zone
    const now = dayjs().tz(tz)
    let operatingDay = now.startOf('day')
    if (now.hour() < 6) {
      operatingDay = operatingDay.subtract(1, 'day')
    }
    return operatingDay.format('MMM D')
  }, [project.data])

  return {
    rtRevenue,
    daRevenue,
    daASRevenue,
    realizedRevenue,
    unrealizedRevenue,
    revenueDate,
    isLoading,
  }
}
