import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { MetStationIssuesTable } from '@/features/performance/met-station/components/MetStationIssuesTable'
import { MetStationTimeseries } from '@/features/performance/met-station/components/MetStationTimeseries'
import { MetStationWindRose } from '@/features/performance/met-station/components/MetStationWindRose'
import { useMetStationDayViewModel } from '@/features/performance/met-station/hooks/use-met-station-day-view-model'
import type { MetStationContext } from '@/features/performance/met-station/types/met-station'
import { buildTimeSearchParams } from '@/features/performance/met-station/utils/build-time-search-params'
import { Group, Stack, Switch } from '@mantine/core'
import { useState } from 'react'
import { useSearchParams } from 'react-router'

type DayViewProps = { context: MetStationContext }

export function MetStationDayView({ context }: DayViewProps) {
  const [searchParams] = useSearchParams()
  const [averageTimeseries, setAverageTimeseries] = useState(false)

  const { start, end } = buildTimeSearchParams(searchParams)

  const data = useMetStationDayViewModel({ context, start, end })

  return (
    <Stack h="100%" p="md">
      <Group align="center">
        <AdvancedDatePicker
          maxDays={1}
          includeTodayInDateRange
          disableQuickActions
          defaultRange="today"
          includeClearButton={false}
        />
        <Switch
          label="Average Timeseries"
          checked={averageTimeseries}
          onChange={(event) =>
            setAverageTimeseries(event.currentTarget.checked)
          }
        />
      </Group>
      <Group flex={1} align="stretch">
        <MetStationTimeseries
          title={'POA'}
          flex={2}
          data={data.poa}
          isLoading={data.timeseriesLoading}
          average={averageTimeseries}
        />
        <MetStationTimeseries
          title={'Wind Speed'}
          flex={2}
          data={data.windSpeed}
          isLoading={data.timeseriesLoading}
          average={averageTimeseries}
        />
        <MetStationWindRose
          title={'Wind Rose'}
          flex={1}
          windDirectionData={data.windDirection}
          windSpeedData={data.windSpeed}
          isLoading={data.timeseriesLoading}
        />
      </Group>
      <Group flex={1} align="stretch">
        <MetStationTimeseries
          title={'GHI'}
          flex={2}
          data={data.ghi}
          isLoading={data.timeseriesLoading}
          average={averageTimeseries}
        />
        <MetStationTimeseries
          title={'Temperature'}
          flex={2}
          data={data.temperature}
          isLoading={data.timeseriesLoading}
          average={averageTimeseries}
        />
        <MetStationIssuesTable
          title="Issues"
          flex={1}
          isLoading={data.activeIssues.isLoading}
          data={data.activeIssues.data}
        />
      </Group>
    </Stack>
  )
}
