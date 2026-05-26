import { Group, Stack } from '@mantine/core'
import { DcAmperageReportClearskyConfig } from '@/features/projects/reports/dc-amperage-report/components/DcAmperageReportClearskyConfig'
import { DcAmperageReportClearskyPoaData } from '@/features/projects/reports/dc-amperage-report/components/DcAmperageReportClearskyPoaData'
import type { DcAmperageReportState } from '@/features/projects/reports/dc-amperage-report/types/dc-amperage-report-types'

type DcAmperageReportClearskyViewProps = {
  reportState: DcAmperageReportState
  onGenerateReport: () => void
}

export function DcAmperageReportClearskyView({
  reportState,
  onGenerateReport,
}: DcAmperageReportClearskyViewProps) {
  return (
    <Stack h="100%" style={{ flex: 1, minHeight: 0 }}>
      <Group h="100%" style={{ flex: 1, minHeight: 0 }}>
        <DcAmperageReportClearskyConfig
          flex={1}
          poaTraceOptions={reportState.poaTraceOptions}
          selectedPoaTraceKeys={reportState.selectedPoaTraceKeys}
          setSelectedPoaTraceKeys={reportState.setSelectedPoaTraceKeys}
          resampleRate={reportState.resampleRate}
          setResampleRate={reportState.setResampleRate}
          minPoa={reportState.minPoa}
          setMinPoa={reportState.setMinPoa}
          maxPoaDerivative={reportState.maxPoaDerivative}
          setMaxPoaDerivative={reportState.setMaxPoaDerivative}
          maxPoaDerivativeStdDev={reportState.maxPoaDerivativeStdDev}
          setMaxPoaDerivativeStdDev={reportState.setMaxPoaDerivativeStdDev}
          usePoaDerivative={reportState.usePoaDerivative}
          setUsePoaDerivative={reportState.setUsePoaDerivative}
          usePoaDerivativeStdDev={reportState.usePoaDerivativeStdDev}
          setUsePoaDerivativeStdDev={reportState.setUsePoaDerivativeStdDev}
          validPoints={reportState.poaProcessingResult.validPoints}
          isGenerating={reportState.reportQuery.isFetching}
          isLoadingPoaTraceOptions={reportState.poaDataQuery.isLoading}
          onGenerateReport={onGenerateReport}
        />
        <DcAmperageReportClearskyPoaData flex={3} reportState={reportState} />
      </Group>
    </Stack>
  )
}
