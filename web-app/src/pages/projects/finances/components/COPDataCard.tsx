import { useSelectProject } from '@/api/v1/operational/projects'
import {
  useGetPTPData,
  useGetPTPEndpoints,
} from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { Skeleton, Text, useMantineTheme } from '@mantine/core'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { Data, Layout } from 'plotly.js'
import { useMemo } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)

interface COPDataCardProps {
  projectId: string
  projectTimeZone?: string | null
  startDate: Date | null
  endDate: Date | null
}

export const COPDataCard = ({
  projectId,
  projectTimeZone,
  startDate,
  endDate,
}: COPDataCardProps) => {
  const theme = useMantineTheme()
  const { data: project } = useSelectProject(projectId)
  const { data: endpointsData } = useGetPTPEndpoints({
    pathParams: { projectId },
    queryOptions: { enabled: !!projectId },
  })
  const entityId = endpointsData?.identifiers?.entity_id

  const { data: copData, isLoading: copLoading } = useGetPTPData({
    pathParams: { projectId },
    queryParams: {
      endpoint: 'Submissions-Current-Operating-Plan-RTC',
      category: 'submissions',
      start: startDate ? dayjs(startDate).toISOString() : undefined,
      end: endDate ? dayjs(endDate).toISOString() : undefined,
      ...(entityId && { element_id: entityId }),
    },
    queryOptions: {
      enabled: !!projectId && !!startDate && !!endDate,
    },
  })

  // Extract earliest COP interval timestamp
  const copSubmissionTime = useMemo(() => {
    if (!copData?.data || copData.data.length === 0) {
      return null
    }

    const element =
      copData.data.find(
        (el) =>
          (el.definition === 'Generator Configuration' ||
            el.definition === 'Generator' ||
            el.definition === 'Entity') &&
          el.dataPoints?.some((dp) => dp.keyName !== 'Resource_ID'),
      ) || copData.data[0]

    if (!element) {
      return null
    }

    let earliestTimestamp: string | null = null
    for (const dp of element.dataPoints || []) {
      if (dp.keyName === 'Resource_ID') {
        continue
      }
      for (const val of dp.values || []) {
        const intervalStart = val.intervalStartUtc
        if (
          intervalStart &&
          !intervalStart.includes('1753') &&
          !intervalStart.includes('9998')
        ) {
          if (!earliestTimestamp || intervalStart < earliestTimestamp) {
            earliestTimestamp = intervalStart
          }
        }
      }
    }

    return earliestTimestamp
  }, [copData])

  // Format COP submission time for display
  const copSubmissionTimeFormatted = useMemo(() => {
    if (!copSubmissionTime || !projectTimeZone) {
      return null
    }
    return dayjs
      .utc(copSubmissionTime)
      .tz(projectTimeZone)
      .format('MMM D, YYYY h:mm A z')
  }, [copSubmissionTime, projectTimeZone])

  // Transform COP data for Plotly chart
  const copPlotData: Data[] = useMemo(() => {
    if (!copData?.data || copData.data.length === 0) {
      return []
    }

    const element =
      copData.data.find(
        (el) =>
          (el.definition === 'Generator Configuration' ||
            el.definition === 'Generator' ||
            el.definition === 'Entity') &&
          el.dataPoints?.some((dp) => dp.keyName !== 'Resource_ID'),
      ) || copData.data[0]

    if (!element) {
      return []
    }

    const traces: Data[] = []

    // Limits subplot fields (top)
    const limitsFields = {
      HSL: {
        name: 'High Sustained Limit (MW)',
        color: theme.colors?.green?.[6] || '#51cf66',
      },
      LSL: {
        name: 'Low Sustained Limit (MW)',
        color: theme.colors?.green?.[4] || '#69db7c',
      },
      HEL: {
        name: 'High Economic Limit (MW)',
        color: theme.colors?.orange?.[6] || '#fd7e14',
      },
      LEL: {
        name: 'Low Economic Limit (MW)',
        color: theme.colors?.orange?.[4] || '#ff922b',
      },
      Reg_Up: {
        name: 'Reg Up (MW)',
        color:
          theme.colors?.violet?.[6] || theme.colors?.grape?.[6] || '#845ef7',
      },
      Reg_Down: {
        name: 'Reg Down (MW)',
        color:
          theme.colors?.violet?.[4] || theme.colors?.grape?.[4] || '#9775fa',
      },
    }

    // SOC subplot fields (bottom)
    const socFields = {
      Max_SOC: {
        name: 'Max SOC (%)',
        color: theme.colors?.blue?.[6] || '#228be6',
      },
      Min_SOC: {
        name: 'Min SOC (%)',
        color: theme.colors?.blue?.[4] || '#339af0',
      },
      Target_Begin_SOC: {
        name: 'Target Begin SOC (%)',
        color: theme.colors?.cyan?.[6] || '#15aabf',
      },
    }

    element.dataPoints.forEach((dp) => {
      const limitsConfig = limitsFields[dp.keyName as keyof typeof limitsFields]
      const socConfig = socFields[dp.keyName as keyof typeof socFields]
      const fieldConfig = limitsConfig || socConfig

      if (!fieldConfig) return

      const x: string[] = []
      const y: (number | null)[] = []

      dp.values.forEach((v) => {
        if (
          v.intervalStartUtc.includes('1753') ||
          v.intervalStartUtc.includes('9998')
        ) {
          return
        }

        const timestamp = dayjs
          .utc(v.intervalStartUtc)
          .tz(projectTimeZone || 'UTC')
          .format()
        x.push(timestamp)

        const value = v.data[0]?.value ?? null
        const numValue =
          value !== null && value !== undefined
            ? parseFloat(String(value))
            : null
        y.push(numValue)
      })

      if (x.length > 0) {
        traces.push({
          x,
          y,
          type: 'scatter',
          mode: 'lines+markers',
          name: fieldConfig.name,
          line: {
            width: 2,
            color: fieldConfig.color,
          },
          marker: {
            size: 4,
            color: fieldConfig.color,
          },
          // Assign to subplot: 'x' for limits (top), 'x2' for SOC (bottom)
          xaxis: limitsConfig ? 'x' : 'x2',
          yaxis: limitsConfig ? 'y' : 'y2',
        } as Data)
      }
    })

    return traces
  }, [copData, projectTimeZone, theme])

  // Get current timestamp for vertical line
  const currentTimestamp = projectTimeZone
    ? dayjs().tz(projectTimeZone).format()
    : null

  const poi = project?.poi

  const layout: Partial<Layout> = useMemo(() => {
    const shapes: Partial<import('plotly.js').Shape>[] = []

    if (currentTimestamp) {
      // Vertical line for top subplot (limits)
      shapes.push({
        type: 'line',
        x0: currentTimestamp,
        x1: currentTimestamp,
        y0: 0,
        y1: 1,
        xref: 'x',
        yref: 'y domain',
        line: {
          color: theme.colors.red[6],
          width: 2,
          dash: 'dash',
        },
      })
      // Vertical line for bottom subplot (SOC)
      shapes.push({
        type: 'line',
        x0: currentTimestamp,
        x1: currentTimestamp,
        y0: 0,
        y1: 1,
        xref: 'x2',
        yref: 'y2 domain',
        line: {
          color: theme.colors.red[6],
          width: 2,
          dash: 'dash',
        },
      })
    }

    return {
      // Top subplot (limits) - occupies top portion of the plot
      xaxis: {
        title: { text: 'Time' },
        domain: [0, 1],
        anchor: 'y',
        showticklabels: true,
        side: 'bottom',
      },
      yaxis: {
        title: { text: 'Power (MW)' },
        domain: [0.6, 1],
        anchor: 'x',
        range: poi != null ? [-poi, poi] : undefined,
      },
      // Bottom subplot (SOC) - occupies bottom portion of the plot
      xaxis2: {
        title: { text: '' },
        domain: [0, 1],
        anchor: 'y2',
        showticklabels: false,
      },
      yaxis2: {
        title: { text: 'SOC (%)' },
        domain: [0, 0.5],
        anchor: 'x2',
      },
      hovermode: 'x unified',
      height: 600,
      legend: {
        orientation: 'h',
        y: -0.15,
        xanchor: 'center',
        x: 0.5,
      },
      shapes,
    }
  }, [currentTimestamp, theme, poi])

  return (
    <CustomCard
      title={
        copSubmissionTimeFormatted
          ? `Current Operating Plan (COP) - Limits & SOC (Submitted for: ${copSubmissionTimeFormatted})`
          : 'Current Operating Plan (COP) - Limits & SOC'
      }
    >
      {copLoading ? (
        <Skeleton height={600} radius="md" />
      ) : copPlotData.length === 0 ? (
        <Text c="dimmed" ta="center" py="xl">
          No COP data available. Make sure
          Submissions-Current-Operating-Plan-RTC data exists.
        </Text>
      ) : (
        <PlotlyPlot
          data={copPlotData}
          layout={layout}
          isLoading={copLoading}
          error={null}
        />
      )}
    </CustomCard>
  )
}
