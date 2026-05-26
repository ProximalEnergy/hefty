import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import type { Data } from 'plotly.js'
import { useMemo } from 'react'
import type { DcAmperageReportState } from '@/features/projects/reports/dc-amperage-report/types/dc-amperage-report-types'
import { buildPoaPlotLayout } from '@/features/projects/reports/dc-amperage-report/utils/dc-amperage-report-utils'

const ACCEPTED_PERIODS_LEGEND_TRACE: Data = {
  x: [null],
  y: [null],
  type: 'bar',
  name: 'Accepted Periods',
  marker: { color: 'rgba(46, 204, 113, 0.2)' },
  hoverinfo: 'skip',
  showlegend: true,
}

type DcAmperageReportClearskyPoaDataProps = {
  flex: number
  reportState: DcAmperageReportState
}

export function DcAmperageReportClearskyPoaData({
  flex,
  reportState,
}: DcAmperageReportClearskyPoaDataProps) {
  const plotData = useMemo<Data[]>(() => {
    const poaTraces: Data[] = reportState.poaProcessingResult.plotData.map(
      (trace) => ({
        x: trace.x,
        y: trace.y,
        type: 'scatter',
        name: trace.name,
        yaxis: trace.yaxis,
        line: trace.yaxis === 'y2' ? { dash: 'dash' as const } : undefined,
      }),
    )

    return [...poaTraces, ACCEPTED_PERIODS_LEGEND_TRACE]
  }, [reportState.poaProcessingResult.plotData])

  const layout = useMemo(() => {
    return buildPoaPlotLayout(reportState.poaProcessingResult.shapes)
  }, [reportState.poaProcessingResult.shapes])

  return (
    <CustomCard
      title="POA Traces"
      style={{ flex, height: '100%', minHeight: 0, width: '100%' }}
    >
      <PlotlyPlot
        data={plotData}
        layout={layout}
        isLoading={reportState.poaDataQuery.isLoading}
        error={reportState.poaDataQuery.error as never}
      />
    </CustomCard>
  )
}
