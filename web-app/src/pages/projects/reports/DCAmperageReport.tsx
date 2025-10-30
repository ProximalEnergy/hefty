import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import ClearskyFilter from '@/components/ClearskyFilter'
import CustomCard, { iconSize, iconStroke } from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetDCAmperageReportV2 } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import { CombinerHealth, DCAmperageDataV2 } from '@/hooks/types'
import {
  ActionIcon,
  Button,
  Group,
  NumberInput,
  Popover,
  SegmentedControl,
  Stack,
  Text,
  Title,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { IconFileTypeXls, IconSettings } from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router'

dayjs.extend(utc)
dayjs.extend(timezone)

interface HeatmapData {
  inverters: string[]
  combiners: string[]
  zValues: (1 | 0 | -1 | null)[][]
}

const DCAmperageReport: React.FC = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.PV, ProjectTypeId.PV_BESS],
  })

  const theme = useComputedColorScheme()
  const colors = useMantineTheme()
  const { projectId } = useParams<{ projectId: string }>()
  const { data: project, isLoading: projectLoading } = useSelectProject(
    projectId!,
  )

  const timezone = project?.time_zone

  function getYesterday(timezone: string) {
    return dayjs().tz(timezone).startOf('day').subtract(1, 'day')
  }

  // State variables
  const [date, setDate] = useState<dayjs.Dayjs | undefined>()

  useEffect(() => {
    if (timezone) {
      setDate(getYesterday(timezone))
    } else {
      setDate(undefined)
    }
  }, [projectId, timezone])

  const [minPOA, setMinPOA] = useState<number>(600)
  const [maxPOA1stDerivative, setMaxPOA1stDerivative] = useState<number>(1)
  const [maxPOA1stDerivativeStd, setMaxPOA1stDerivativeStd] =
    useState<number>(1)
  const [usePOA1d, setUsePOA1d] = useState<boolean>(true)
  const [usePOA1dStd, setUsePOA1dStd] = useState<boolean>(true)
  const [normalization, setNormalization] = useState<string>('inv')
  const [acceptanceThreshold, setAcceptanceThreshold] = useState<number>(5)
  const [resampleRate, setResampleRate] = useState<string>('5min')
  const [heatmapData, setHeatmapData] = useState<HeatmapData>({
    inverters: [],
    combiners: [],
    zValues: [],
  })

  useEffect(() => {
    // Reset data when projectId changes
    if (projectId) {
      setHeatmapData({ inverters: [], combiners: [], zValues: [] }) // Reset heatmap data if necessary
    }
  }, [projectId]) // Add projectId as a dependency

  // Fetch data hooks
  const {
    data: dcAmperageData,
    isLoading: dcAmperageDataLoading,
    error: dcAmperageDataError,
    refetch: refetchDcAmperageData,
  } = useGetDCAmperageReportV2({
    pathParams: { projectId: projectId || '' },
    queryParams: {
      start: date?.toISOString() ?? '',
      min_poa: minPOA,
      max_poa_1d: maxPOA1stDerivative,
      max_poa_std: maxPOA1stDerivativeStd,
      rolling_window: 12,
      use_poa_1d: usePOA1d,
      use_poa_std: usePOA1dStd,
      resample_rate: resampleRate,
    },
    queryOptions: { enabled: false },
  })
  const [excelLoading, setExcelLoading] = useState<boolean>(false)

  const handleExcelDownload2 = (dcAmperageData: DCAmperageDataV2) => {
    if (dcAmperageData.reports.excel) {
      setExcelLoading(true)
      try {
        window.open(dcAmperageData.reports.excel, '_blank') // Open the report link in a new tab
      } catch (error) {
        console.error('Error opening report link:', error) // Updated error message
      } finally {
        setExcelLoading(false)
      }
    }
  }

  const handlePOADownload = (dcAmperageData: DCAmperageDataV2) => {
    if (dcAmperageData.reports.poa) {
      window.open(dcAmperageData.reports.poa, '_blank') // Open the report link in a new tab
    }
  }

  const handleCurrentDownload = (dcAmperageData: DCAmperageDataV2) => {
    if (dcAmperageData.reports.cb) {
      window.open(dcAmperageData.reports.cb, '_blank') // Open the report link in a new tab
    }
  }

  useEffect(() => {
    const data =
      normalization === 'inv' ? dcAmperageData?.inv : dcAmperageData?.proj
    const newHeatmapData = processDcAmperageData(data, acceptanceThreshold)
    setHeatmapData(newHeatmapData)
  }, [dcAmperageData, acceptanceThreshold, normalization])

  const handleGenerateData = () => {
    refetchDcAmperageData()
  }

  if (projectLoading) return <PageLoader />

  return (
    <Stack h="100%" p="sm">
      <Group grow align="space-between">
        <Title order={1}>DC Amperage Report</Title>
        <Group justify="flex-end">
          <ActionIcon
            size="xl"
            onClick={
              dcAmperageData
                ? () => handleExcelDownload2(dcAmperageData)
                : undefined
            }
            loading={excelLoading}
            disabled={!dcAmperageData}
          >
            <IconFileTypeXls />
          </ActionIcon>
        </Group>
      </Group>
      {date && timezone && (
        <ClearskyFilter
          date={date}
          setDate={setDate}
          minPOA={minPOA}
          setMinPOA={setMinPOA}
          maxPOA1stDerivative={maxPOA1stDerivative}
          setMaxPOA1stDerivative={setMaxPOA1stDerivative}
          maxPOA1stDerivativeStd={maxPOA1stDerivativeStd}
          setMaxPOA1stDerivativeStd={setMaxPOA1stDerivativeStd}
          handleGenerateData={handleGenerateData}
          timezone={timezone}
          projectId={projectId || ''}
          usePOA1d={usePOA1d}
          usePOA1dStd={usePOA1dStd}
          setUsePOA1d={setUsePOA1d}
          setUsePOA1dStd={setUsePOA1dStd}
          resampleRate={resampleRate}
          setResampleRate={setResampleRate}
        />
      )}

      {/* DC Amperage Report */}
      <CustomCard
        title="DC Amperage Report"
        style={{ height: '100%' }}
        headerChildren={
          <Popover>
            <Popover.Target>
              <ActionIcon variant="default">
                <IconSettings size={iconSize} stroke={iconStroke} />
              </ActionIcon>
            </Popover.Target>
            <Popover.Dropdown>
              <Stack>
                <Group justify="space-between">
                  <Text>Normalization:</Text>
                  <SegmentedControl
                    data={[
                      { label: 'Inverter', value: 'inv' },
                      { label: 'Project', value: 'proj' },
                    ]}
                    value={normalization}
                    onChange={(value) => setNormalization(value ?? 'inv')}
                  />
                </Group>
                <Group justify="space-between">
                  <Text>Acceptance Threshold:</Text>
                  <NumberInput
                    min={0}
                    max={100}
                    value={acceptanceThreshold}
                    onChange={(value) =>
                      setAcceptanceThreshold(Number(value) ?? 0)
                    }
                    suffix="%"
                  />
                </Group>
                <Group>
                  <Button
                    disabled={!dcAmperageData}
                    onClick={
                      dcAmperageData
                        ? () => handlePOADownload(dcAmperageData)
                        : undefined
                    }
                  >
                    Download raw POA
                  </Button>
                  <Button
                    disabled={!dcAmperageData}
                    onClick={
                      dcAmperageData
                        ? () => handleCurrentDownload(dcAmperageData)
                        : undefined
                    }
                  >
                    Download raw current
                  </Button>
                </Group>
              </Stack>
            </Popover.Dropdown>
          </Popover>
        }
      >
        <PlotlyPlot
          isLoading={dcAmperageDataLoading}
          data={[
            {
              z: heatmapData.zValues,
              x: heatmapData.inverters,
              y: heatmapData.combiners,
              type: 'heatmap',
              colorscale: [
                [0, colors.colors.red[7]],
                [0.5, colors.colors.green[7]],
                [1, colors.colors.grape[4]],
              ],
              showscale: true,
              xgap: 1,
              ygap: 1,
              zmin: -1,
              zmax: 1,
              hoverinfo: 'text',
              // @ts-expect-error - Plotly types are not up to date
              text: heatmapData.zValues.map((row, i) =>
                row.map(
                  (_, j) =>
                    `Inverter: ${heatmapData.inverters[j]}<br>Combiner: ${
                      heatmapData.combiners[i]
                    }<br>Normalized Value: ${
                      normalization === 'inv'
                        ? (dcAmperageData?.inv.data[i][j]?.toFixed(2) ?? 'N/A')
                        : (dcAmperageData?.proj.data[i][j]?.toFixed(2) ?? 'N/A')
                    }`,
                ),
              ),
              hoverongaps: false,
            },
          ]}
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
              showticklabels: false,
            },
            plot_bgcolor: theme === 'light' ? 'white' : colors.colors.dark[6],
          }}
          error={dcAmperageDataError}
        />
      </CustomCard>
    </Stack>
  )
}

// Helper functions
const processDcAmperageData = (
  data: CombinerHealth | undefined,
  acceptanceThreshold: number,
) => {
  if (!data) return { inverters: [], combiners: [], zValues: [] } // Return empty HeatmapData if no data

  const inverters = data.columns
  const combiners = data.index
  const zValues = data.data
    .map((row) =>
      row.map((value) => {
        if (value === null) return null // Keep null values
        const diff = value - 1 // Calculate the difference from the acceptance threshold
        if (Math.abs(diff) <= acceptanceThreshold / 100) return 0 // Within threshold
        return diff > 0 ? 1 : -1 // Updated to allow 1 for over-performing
      }),
    )
    .map((row) => row.map((value) => (value === null ? null : value))) // Convert to HeatmapData format

  return { inverters, combiners, zValues } // Return HeatmapData directly
}

function DCAmperageReportWrapper() {
  const { projectId } = useParams<{ projectId: string }>()
  return <DCAmperageReport key={projectId} />
}

export default DCAmperageReportWrapper
