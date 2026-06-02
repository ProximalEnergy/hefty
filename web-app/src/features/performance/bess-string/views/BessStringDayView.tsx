import { useGetEquipmentAnalysisBESS } from '@/api/v1/protected/web-application/projects/equipment-analysis/bess'
import CustomCard from '@/components/CustomCard'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useResizePlotlyCharts } from '@/hooks/useResizePlotlyCharts'
import { sortAndColorDevices } from '@/utils/colors'
import { Stack } from '@mantine/core'
import { useRef } from 'react'

import type { BessStringContext } from '@/features/performance/bess-string/hooks/use-bess-string-context'

const MAX_DAYS = 7

type BessStringDayViewProps = {
  context: BessStringContext
}

export function BessStringDayView({ context }: BessStringDayViewProps) {
  const tabPanelRef = useRef<HTMLDivElement>(null)
  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  const startRequest =
    start && context.project
      ? start.tz(context.project.time_zone, true).toISOString()
      : undefined
  const endRequest =
    end && context.project
      ? end.tz(context.project.time_zone, true).toISOString()
      : undefined

  const data = useGetEquipmentAnalysisBESS({
    pathParams: {
      project_id: context.projectId || '-1',
    },
    queryParams: {
      start: startRequest || '',
      end: endRequest || '',
    },
    queryOptions: {
      enabled: !!context.projectId && !!startRequest && !!endRequest,
    },
  })

  useResizePlotlyCharts({
    containerRef: tabPanelRef,
    enabled: true,
  })

  const chartData = data.data?.bess_string ?? []

  return (
    <Stack
      gap="md"
      ref={tabPanelRef}
      style={{ flex: 1, minHeight: 0, width: '100%' }}
    >
      <AdvancedDatePicker
        includeClearButton={false}
        includeTodayInDateRange
        limits={{
          day: 7,
          week: 1,
          month: 0,
          quarter: 0,
          year: 0,
        }}
        maxDays={MAX_DAYS}
        disableQuickActions
        defaultRange="past-3-days"
      />
      <CustomCard
        title="String Power (DC)"
        info="Positive values indicate discharging, negative values indicate charging."
        style={{ flex: 1 }}
      >
        <PlotlyPlot
          data={
            chartData.length > 0
              ? sortAndColorDevices(chartData).map((device) => ({
                  x: device.x,
                  y: device.y,
                  name: device.name,
                  line: { color: device.color },
                }))
              : undefined
          }
          layout={{
            yaxis: {
              title: { text: 'MW' },
            },
          }}
          isLoading={data.isLoading}
          error={data.error}
        />
      </CustomCard>
    </Stack>
  )
}
