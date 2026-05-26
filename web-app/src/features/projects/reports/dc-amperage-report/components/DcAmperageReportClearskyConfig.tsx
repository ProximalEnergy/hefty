import CustomCard from '@/components/CustomCard'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import {
  Button,
  Checkbox,
  Group,
  ScrollArea,
  Select,
  Skeleton,
  Slider,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core'
import { useEffect } from 'react'
import type { DcAmperageReportPoaTraceOption } from '@/features/projects/reports/dc-amperage-report/types/dc-amperage-report-types'
import { DcAmperageReportTextWithInfo } from '@/features/projects/reports/dc-amperage-report/components/DcAmperageReportTextWithInfo'

const MAX_POA_DERIVATIVE_INFO =
  'The maximum allowed POA derivative for the report. This is a measure of ' +
  'how quickly the POA is changing, with higher values representing ' +
  'fast-changing conditions such as moving clouds. Recommended value is ' +
  '1 W/m^2/minute.'

const MAX_POA_DERIVATIVE_STD_DEV_INFO =
  'The maximum allowed POA derivative standard deviation for the report. ' +
  'This is a measure of the coherence of meteorological stations in ' +
  'different locations onsite. Recommended value is 1 W/m^2/minute.'

type DcAmperageReportClearskyConfigProps = {
  flex: number
  poaTraceOptions: DcAmperageReportPoaTraceOption[]
  selectedPoaTraceKeys: string[]
  setSelectedPoaTraceKeys: (selectedPoaTraceKeys: string[]) => void
  resampleRate: string
  setResampleRate: (resampleRate: string) => void
  minPoa: number
  setMinPoa: (minPoa: number) => void
  maxPoaDerivative: number
  setMaxPoaDerivative: (maxPoaDerivative: number) => void
  maxPoaDerivativeStdDev: number
  setMaxPoaDerivativeStdDev: (maxPoaDerivativeStdDev: number) => void
  usePoaDerivative: boolean
  setUsePoaDerivative: (usePoaDerivative: boolean) => void
  usePoaDerivativeStdDev: boolean
  setUsePoaDerivativeStdDev: (usePoaDerivativeStdDev: boolean) => void
  validPoints: number
  isGenerating: boolean
  isLoadingPoaTraceOptions: boolean
  onGenerateReport: () => void
}

export function DcAmperageReportClearskyConfig({
  flex,
  poaTraceOptions,
  selectedPoaTraceKeys,
  setSelectedPoaTraceKeys,
  resampleRate,
  setResampleRate,
  minPoa,
  setMinPoa,
  maxPoaDerivative,
  setMaxPoaDerivative,
  maxPoaDerivativeStdDev,
  setMaxPoaDerivativeStdDev,
  usePoaDerivative,
  setUsePoaDerivative,
  usePoaDerivativeStdDev,
  setUsePoaDerivativeStdDev,
  validPoints,
  isGenerating,
  isLoadingPoaTraceOptions,
  onGenerateReport,
}: DcAmperageReportClearskyConfigProps) {
  const generateButtonText =
    validPoints > 0
      ? `Generate Data (${validPoints} points)`
      : 'No valid points'
  const isPoaDerivativeStdDevDisabled = selectedPoaTraceKeys.length < 2

  useEffect(() => {
    if (isPoaDerivativeStdDevDisabled && usePoaDerivativeStdDev) {
      setUsePoaDerivativeStdDev(false)
    }
  }, [
    isPoaDerivativeStdDevDisabled,
    setUsePoaDerivativeStdDev,
    usePoaDerivativeStdDev,
  ])

  return (
    <CustomCard
      title="Clearsky Config"
      bodyStyle={{ flex, height: 'auto', minHeight: 0, overflow: 'hidden' }}
      style={{ flex, height: '100%', minHeight: 0, overflow: 'hidden' }}
      allowFullscreen={false}
    >
      <Stack h="100%" gap="md" style={{ minHeight: 0 }}>
        <ScrollArea style={{ flex: 1, minHeight: 0 }}>
          <Stack gap="md" pr="sm">
            <Text>Date</Text>
            <AdvancedDatePicker
              maxDays={1}
              includeTodayInDateRange
              disableQuickActions
              defaultRange="today"
              includeClearButton={false}
            />

            <DcAmperageReportTextWithInfo
              text="Sample Rate"
              info="The data sampling rate to use for the report."
            />
            <Select
              data={['1min', '5min', '10min', '15min', '30min', '60min']}
              value={resampleRate}
              onChange={(value) => setResampleRate(value ?? '5min')}
            />
            <DcAmperageReportTextWithInfo
              text={`Minimum POA (${minPoa} W/m^2)`}
              info="The minimum mean POA value to use for the report."
            />
            <Slider
              min={0}
              max={1000}
              step={50}
              value={minPoa}
              onChange={setMinPoa}
            />
            <Group justify="space-between">
              <DcAmperageReportTextWithInfo
                text="Max. POA Derivative"
                subText="1-Hour Rolling Average"
                subTextProps={{ size: 'xs', c: 'dimmed' }}
                info={MAX_POA_DERIVATIVE_INFO}
              />
              <Checkbox
                label="Use"
                checked={usePoaDerivative}
                onChange={(event) =>
                  setUsePoaDerivative(event.currentTarget.checked)
                }
              />
            </Group>
            <Slider
              min={0}
              max={10}
              step={0.1}
              value={maxPoaDerivative}
              onChange={setMaxPoaDerivative}
              disabled={!usePoaDerivative}
            />
            <Group justify="space-between">
              <DcAmperageReportTextWithInfo
                text="Max. POA Derivative Std Dev"
                subText="1-Hour Rolling Average"
                subTextProps={{ size: 'xs', c: 'dimmed' }}
                info={MAX_POA_DERIVATIVE_STD_DEV_INFO}
              />
              <Tooltip
                label="Standard Deviation requires at least 2 POA traces."
                disabled={!isPoaDerivativeStdDevDisabled}
              >
                <span>
                  <Checkbox
                    label="Use"
                    checked={usePoaDerivativeStdDev}
                    disabled={isPoaDerivativeStdDevDisabled}
                    onChange={(event) =>
                      setUsePoaDerivativeStdDev(event.currentTarget.checked)
                    }
                  />
                </span>
              </Tooltip>
            </Group>
            <Slider
              min={0}
              max={10}
              step={0.1}
              value={maxPoaDerivativeStdDev}
              onChange={setMaxPoaDerivativeStdDev}
              disabled={!usePoaDerivativeStdDev}
            />
            <Stack gap="xs" style={{ flex: 1, minHeight: 160 }}>
              <Text>POA Traces</Text>
              {isLoadingPoaTraceOptions ? (
                <Skeleton style={{ flex: 1, minHeight: 120 }} />
              ) : poaTraceOptions.length === 0 ? (
                <Text c="dimmed" size="sm">
                  No POA traces returned for the selected date.
                </Text>
              ) : (
                <Checkbox.Group
                  value={selectedPoaTraceKeys}
                  onChange={setSelectedPoaTraceKeys}
                >
                  <Stack gap="xs">
                    {poaTraceOptions.map((traceOption) => (
                      <Checkbox
                        key={traceOption.key}
                        value={traceOption.key}
                        label={traceOption.label}
                      />
                    ))}
                  </Stack>
                </Checkbox.Group>
              )}
            </Stack>
          </Stack>
        </ScrollArea>
        <Button
          fullWidth
          disabled={validPoints === 0}
          loading={isGenerating}
          onClick={onGenerateReport}
        >
          {generateButtonText}
        </Button>
      </Stack>
    </CustomCard>
  )
}
