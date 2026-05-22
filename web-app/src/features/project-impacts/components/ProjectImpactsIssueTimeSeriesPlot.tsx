import { useGetDataTimeSeriesV3 } from '@/api/v1/operational/project/project_data'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { Box } from '@mantine/core'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type { Data, Layout } from 'plotly.js'
import { useMemo } from 'react'
import type { ProjectIssueRow } from '@/features/project-impacts/hooks/use-project-impacts-issues-view-model'

dayjs.extend(timezone)
dayjs.extend(utc)

const ISSUE_PLOT_PADDING_HOURS = 24
const ISSUE_PLOT_HEIGHT = 320

const formatIssuePlotTime = (value: dayjs.Dayjs) => {
  return value.format('YYYY-MM-DD HH:mm:ss')
}

const getIssuePlotRange = (timeStart: string, timeZone: string) => {
  const issueStart = dayjs(timeStart).tz(timeZone)

  return {
    issueStart,
    plotStart: issueStart.subtract(ISSUE_PLOT_PADDING_HOURS, 'hour'),
    plotEnd: issueStart.add(ISSUE_PLOT_PADDING_HOURS, 'hour'),
  }
}

const getIssuePlotBoxEnd = ({
  timeEnd,
  timeZone,
  plotEnd,
}: {
  timeEnd: string | null | undefined
  timeZone: string
  plotEnd: dayjs.Dayjs
}) => {
  const issueEnd = timeEnd ? dayjs(timeEnd).tz(timeZone) : null

  if (issueEnd?.isValid() && issueEnd <= plotEnd) {
    return issueEnd
  }

  return plotEnd
}

type ProjectImpactsIssueTimeSeriesPlotProps = {
  issue: ProjectIssueRow
  projectId: string
  timeZone: string
}

export function ProjectImpactsIssueTimeSeriesPlot({
  issue,
  projectId,
  timeZone,
}: ProjectImpactsIssueTimeSeriesPlotProps) {
  const { issueStart, plotStart, plotEnd } = useMemo(
    () => getIssuePlotRange(issue.time_start, timeZone),
    [issue.time_start, timeZone],
  )
  const issueBoxEnd = useMemo(
    () =>
      getIssuePlotBoxEnd({
        timeEnd: issue.time_end,
        timeZone,
        plotEnd,
      }),
    [issue.time_end, plotEnd, timeZone],
  )
  const timeSeries = useGetDataTimeSeriesV3({
    pathParams: { projectId },
    queryParams: {
      tag_ids: issue.tag_id === null ? [] : [issue.tag_id],
      start: plotStart.toISOString(),
      end: plotEnd.toISOString(),
      ensure_full_range: true,
      cutoff_now: true,
    },
    queryOptions: {
      enabled: issue.tag_id !== null,
    },
  })
  const plotData = useMemo<Data[]>(() => {
    return (timeSeries.data ?? []).map((trace) => ({
      x: trace.x,
      y: trace.y,
      name: trace.name || trace.tag_name_long || trace.tag_name_scada,
      type: 'scatter',
      mode: 'lines',
      hoverlabel: {
        namelength: -1,
      },
    }))
  }, [timeSeries.data])
  const plotLayout = useMemo<Partial<Layout>>(
    () => ({
      shapes: [
        {
          type: 'rect',
          x0: formatIssuePlotTime(issueStart),
          x1: formatIssuePlotTime(issueBoxEnd),
          y0: 0,
          y1: 1,
          xref: 'x',
          yref: 'paper',
          fillcolor: 'rgba(255, 0, 0, 0.3)',
          line: { width: 0 },
        },
      ],
      xaxis: {
        type: 'date',
        range: [formatIssuePlotTime(plotStart), formatIssuePlotTime(plotEnd)],
        autorange: false,
      },
      yaxis: {
        title: {
          text: issue.sensor_type_name_long || 'Value',
        },
      },
    }),
    [issue.sensor_type_name_long, issueBoxEnd, issueStart, plotEnd, plotStart],
  )

  return (
    <Box h={ISSUE_PLOT_HEIGHT} w="100%">
      <PlotlyPlot
        data={plotData}
        error={timeSeries.error}
        isLoading={timeSeries.isFetching}
        layout={plotLayout}
        noDataMessage="No tag data found for this issue window."
        xAxisTimeZone={timeZone}
      />
    </Box>
  )
}
