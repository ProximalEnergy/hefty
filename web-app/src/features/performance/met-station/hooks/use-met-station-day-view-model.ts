import { IssueCategoryEnum, SensorTypeEnum } from '@/api/enumerations'
import {
  type ProjectIssue,
  useGetProjectIssues,
} from '@/api/v1/operational/project/issues'
import { useGetDataTimeSeriesV3 } from '@/api/v1/operational/project/project_data'
import type { MetStationContext } from '@/features/performance/met-station/types/met-station'
import { DataTimeSeries } from '@/hooks/types'

type DayViewData = {
  poa: DataTimeSeries[]
  ghi: DataTimeSeries[]
  temperature: DataTimeSeries[]
  windSpeed: DataTimeSeries[]
  windDirection: DataTimeSeries[]
  timeseriesLoading: boolean
  activeIssues: {
    data: ProjectIssue[]
    isLoading: boolean
  }
}

export function useMetStationDayViewModel({
  context,
  start,
  end,
}: {
  context: MetStationContext
  start: Date
  end: Date
}) {
  const metStationDayViewData = useGetDataTimeSeriesV3({
    pathParams: { projectId: context.projectId },
    queryParams: {
      sensor_type_ids: [
        SensorTypeEnum.MET_STATION_POA,
        SensorTypeEnum.MET_STATION_GHI,
        SensorTypeEnum.MET_STATION_AMBIENT_TEMPERATURE,
        SensorTypeEnum.MET_STATION_WIND_SPEED,
        SensorTypeEnum.MET_STATION_WIND_DIRECTION,
      ],
      start: start.toISOString(),
      end: end.toISOString(),
    },
    queryOptions: {
      enabled: context.projectId.length > 0,
    },
  })
  const issues = useGetProjectIssues({
    pathParams: { project_id: context.projectId },
    queryParams: {
      active_only: false,
      end: end.toISOString(),
      issue_category_ids: [IssueCategoryEnum.MET_STATION_NON_COMMUNICATING],
      start: start.toISOString(),
    },
    queryOptions: {
      enabled: context.projectId.length > 0,
    },
  })
  const poa: DataTimeSeries[] = []
  const ghi: DataTimeSeries[] = []
  const temperature: DataTimeSeries[] = []
  const windSpeed: DataTimeSeries[] = []
  const windDirection: DataTimeSeries[] = []

  for (const d of metStationDayViewData.data || []) {
    switch (d.sensor_type_id) {
      case SensorTypeEnum.MET_STATION_POA:
        poa.push(d)
        break
      case SensorTypeEnum.MET_STATION_GHI:
        ghi.push(d)
        break
      case SensorTypeEnum.MET_STATION_AMBIENT_TEMPERATURE:
        temperature.push(d)
        break
      case SensorTypeEnum.MET_STATION_WIND_SPEED:
        windSpeed.push(d)
        break
      case SensorTypeEnum.MET_STATION_WIND_DIRECTION:
        windDirection.push(d)
        break
    }
  }

  const dataOut: DayViewData = {
    poa,
    ghi,
    temperature,
    windSpeed,
    windDirection,
    timeseriesLoading: metStationDayViewData.isLoading,
    activeIssues: { data: issues.data || [], isLoading: issues.isLoading },
  }
  return dataOut
}
