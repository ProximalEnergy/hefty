import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { Text, useComputedColorScheme, useMantineTheme } from '@mantine/core'
import { useMemo } from 'react'
import type { DcAmperageReportState } from '@/features/projects/reports/dc-amperage-report/types/dc-amperage-report-types'
import { DcAmperageReportAnalysisGuide } from '@/features/projects/reports/dc-amperage-report/components/DcAmperageReportAnalysisGuide'
import { buildDcAmperageHeatmapTrace } from '@/features/projects/reports/dc-amperage-report/utils/dc-amperage-report-utils'

type DcAmperageReportAnalysisDataProps = {
  flex: number
  reportState: DcAmperageReportState
}

export function DcAmperageReportAnalysisData({
  flex,
  reportState,
}: DcAmperageReportAnalysisDataProps) {
  const theme = useComputedColorScheme()
  const colors = useMantineTheme()
  const heatmapColorscale = useMemo<[number, string][]>(() => {
    return [
      [0, colors.colors.blue[6]],
      [0.5, colors.colors.gray[5]],
      [1, colors.colors.orange[6]],
    ]
  }, [colors])
  const reportData = reportState.reportQuery.data
  const heatmapSource =
    reportState.normalization === 'inv' ? reportData?.inv : reportData?.proj
  const plotData = useMemo(() => {
    return buildDcAmperageHeatmapTrace({
      data: heatmapSource,
      normalization: reportState.normalization,
      deviationThreshold: reportState.deviationThreshold,
      colorscale: heatmapColorscale,
    })
  }, [
    heatmapSource,
    reportState.normalization,
    reportState.deviationThreshold,
    heatmapColorscale,
  ])

  return (
    <CustomCard
      title="Analysis Data"
      info={<DcAmperageReportAnalysisGuide />}
      bodyStyle={{ flex, height: 'auto', minHeight: 0, overflow: 'hidden' }}
      style={{ flex, height: '100%', minHeight: 0, overflow: 'hidden' }}
    >
      {reportData ? (
        <PlotlyPlot
          isLoading={reportState.reportQuery.isFetching}
          data={plotData}
          layout={{
            xaxis: {
              title: { text: 'Inverter' },
              side: 'top',
              tickangle: -45,
              showgrid: false,
              type: 'category',
            },
            yaxis: {
              title: { text: 'Combiner' },
              autorange: 'reversed',
              showgrid: false,
            },
            plot_bgcolor:
              theme === 'light' ? colors.white : colors.colors.dark[6],
          }}
          error={reportState.reportQuery.error as never}
        />
      ) : (
        <Text c="dimmed" p="md">
          Generate data from the Clearsky tab to populate the analysis heatmap.
        </Text>
      )}
    </CustomCard>
  )
}
