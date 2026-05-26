import CustomCard from '@/components/CustomCard'
import { Stack, Text } from '@mantine/core'
import { useMemo } from 'react'
import type { DcAmperageReportState } from '@/features/projects/reports/dc-amperage-report/types/dc-amperage-report-types'
import { buildDcAmperageAnalysisSummaryCounts } from '@/features/projects/reports/dc-amperage-report/utils/dc-amperage-report-utils'

type DcAmperageReportAnalysisSummaryProps = {
  reportState: DcAmperageReportState
}

export function DcAmperageReportAnalysisSummary({
  reportState,
}: DcAmperageReportAnalysisSummaryProps) {
  const reportData = reportState.reportQuery.data
  const analysisData =
    reportState.normalization === 'inv' ? reportData?.inv : reportData?.proj
  const summaryCounts = useMemo(() => {
    return buildDcAmperageAnalysisSummaryCounts({
      data: analysisData,
      deviationThreshold: reportState.deviationThreshold,
    })
  }, [analysisData, reportState.deviationThreshold])
  const formattedSummaryCounts = {
    numberBelow: summaryCounts.numberBelow.toLocaleString(),
    numberAbove: summaryCounts.numberAbove.toLocaleString(),
    numberWithin: summaryCounts.numberWithin.toLocaleString(),
  }

  return (
    <CustomCard
      title="Analysis Summary"
      bodyStyle={{ minHeight: 0, overflow: 'hidden' }}
      style={{ minHeight: 0, overflow: 'hidden' }}
      allowFullscreen={false}
    >
      {reportData ? (
        <Stack gap="xs">
          <Text>
            {formattedSummaryCounts.numberBelow} Below Peers |{' '}
            {formattedSummaryCounts.numberAbove} Above Peers
          </Text>
          <Text>{formattedSummaryCounts.numberWithin} Within Expectation</Text>
        </Stack>
      ) : (
        <Text c="dimmed">
          Generate data from the Clearsky tab to populate the analysis summary.
        </Text>
      )}
    </CustomCard>
  )
}
