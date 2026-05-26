import CustomCard from '@/components/CustomCard'
import { Button, NumberInput, SegmentedControl, Stack } from '@mantine/core'
import { IconFileTypeXls } from '@tabler/icons-react'
import type {
  DcAmperageReportNormalization,
  DcAmperageReportState,
} from '@/features/projects/reports/dc-amperage-report/types/dc-amperage-report-types'
import { DcAmperageReportTextWithInfo } from '@/features/projects/reports/dc-amperage-report/components/DcAmperageReportTextWithInfo'

const NORMALIZATION_INFO =
  'The normalization method to use for the displayed analysis. "Inverter" ' +
  'normalizes all combiner data to their peers within the same inverter, ' +
  'while "Project" normalizes all combiner data to the entire project median.'

const DEVIATION_THRESHOLD_INFO =
  'The deviation threshold for the displayed analysis. This is the maximum ' +
  'allowed deviation from the median combiner performance for the displayed ' +
  'analysis. The default is 5%.'

type DcAmperageReportAnalysisConfigProps = {
  flex: number
  reportState: DcAmperageReportState
}

export function DcAmperageReportAnalysisConfig({
  flex,
  reportState,
}: DcAmperageReportAnalysisConfigProps) {
  const reportData = reportState.reportQuery.data

  const openReportUrl = (url: string | undefined) => {
    if (url) {
      const newWindow = window.open(url, '_blank')
      if (newWindow) {
        newWindow.opener = null
      }
    }
  }

  return (
    <CustomCard
      title="Analysis Config"
      bodyStyle={{ flex, height: 'auto', minHeight: 0, overflow: 'hidden' }}
      style={{ flex, height: '100%', minHeight: 0, overflow: 'hidden' }}
      allowFullscreen={false}
    >
      <Stack h="100%" gap="md" style={{ minHeight: 0 }} justify="space-between">
        <Stack>
          <DcAmperageReportTextWithInfo
            text="Normalization"
            info={NORMALIZATION_INFO}
          />
          <SegmentedControl
            data={[
              { label: 'Inverter', value: 'inv' },
              { label: 'Project', value: 'proj' },
            ]}
            value={reportState.normalization}
            onChange={(value) =>
              reportState.setNormalization(
                (value ?? 'inv') as DcAmperageReportNormalization,
              )
            }
          />
          <DcAmperageReportTextWithInfo
            text="Deviation Threshold"
            info={DEVIATION_THRESHOLD_INFO}
          />
          <NumberInput
            min={0}
            max={100}
            value={reportState.deviationThreshold}
            onChange={(value) => {
              reportState.setDeviationThreshold(Number(value) || 0)
            }}
            suffix="%"
            step={1}
          />
        </Stack>
        <Stack gap="xs">
          <Button
            fullWidth
            leftSection={<IconFileTypeXls />}
            disabled={!reportData?.reports.excel}
            onClick={() => openReportUrl(reportData?.reports.excel)}
          >
            Download Excel Report
          </Button>
          <Button
            fullWidth
            variant="light"
            disabled={!reportData?.reports.poa}
            onClick={() => openReportUrl(reportData?.reports.poa)}
          >
            Download Raw POA
          </Button>
          <Button
            fullWidth
            variant="light"
            disabled={!reportData?.reports.cb}
            onClick={() => openReportUrl(reportData?.reports.cb)}
          >
            Download Raw Combiner Current
          </Button>
        </Stack>
      </Stack>
    </CustomCard>
  )
}
