import { Group, Stack } from '@mantine/core'
import { DcAmperageReportAnalysisConfig } from '@/features/projects/reports/dc-amperage-report/components/DcAmperageReportAnalysisConfig'
import { DcAmperageReportAnalysisData } from '@/features/projects/reports/dc-amperage-report/components/DcAmperageReportAnalysisData'
import type { DcAmperageReportState } from '@/features/projects/reports/dc-amperage-report/types/dc-amperage-report-types'
import { DcAmperageReportAnalysisSummary } from '@/features/projects/reports/dc-amperage-report/components/DcAmperageReportAnalysisSummary'

type DcAmperageReportAnalysisViewProps = {
  reportState: DcAmperageReportState
}

export function DcAmperageReportAnalysisView({
  reportState,
}: DcAmperageReportAnalysisViewProps) {
  return (
    <Stack h="100%" style={{ flex: 1, minHeight: 0 }}>
      <Group h="100%" style={{ flex: 1, minHeight: 0 }}>
        <DcAmperageReportAnalysisConfig flex={1} reportState={reportState} />
        <Stack flex={4} h="100%">
          <DcAmperageReportAnalysisSummary reportState={reportState} />
          <DcAmperageReportAnalysisData flex={1} reportState={reportState} />
        </Stack>
      </Group>
    </Stack>
  )
}
