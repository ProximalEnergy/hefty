import {
  OperationalKPIData,
  useGetOperationalKPIData,
} from '@/api/v1/operational/kpi_data'
import { useGetKPIInstances } from '@/api/v1/operational/kpi_instances'
import { useGetRoundTripEfficiency } from '@/api/v1/operational/project/kpi_data'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetDevicesV2 } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import {
  Box,
  Card,
  Group,
  LoadingOverlay,
  SimpleGrid,
  Stack,
  Text,
  Tooltip,
  useMantineTheme,
} from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'
import { IconBatteryCharging, IconBolt } from '@tabler/icons-react'
import { Data } from 'plotly.js'
import { ReactNode } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'

// MetricCard component for displaying key metrics
interface MetricCardProps {
  title: string
  value: string
  subtitle: string
  icon: ReactNode
  tooltip: string
  isLoading?: boolean
}

const CardValue = ({
  value,
  isLoading,
}: {
  value: string
  isLoading: boolean | undefined
}) => {
  return (
    <Box style={{ height: 48, position: 'relative' }}>
      {isLoading ? (
        <LoadingOverlay visible />
      ) : (
        <Text fz={32} fw={700} mt={15}>
          {value}
        </Text>
      )}
    </Box>
  )
}

const MetricCard = ({
  title,
  value,
  subtitle,
  icon,
  tooltip,
  isLoading,
}: MetricCardProps) => {
  return (
    <Tooltip label={tooltip} withArrow>
      <Card withBorder p="md" radius="md">
        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            {title}
          </Text>
          {icon}
        </Group>
        <CardValue value={value} isLoading={isLoading} />
        <Text size="xs" c="dimmed" mt={5}>
          {subtitle}
        </Text>
      </Card>
    </Tooltip>
  )
}

// KPI Type ID mappings for navigation
const KPI_TYPE_IDS = {
  ENERGY_CHARGED: 37, // BESS String Energy Charged
  ENERGY_DISCHARGED: 41, // BESS String Energy Discharged
  CYCLE_COUNT: 32, // BESS String Cycle Count
  VOLTAGE: 65, // BESS String Average Voltage
  SOC: 25, // BESS String Average SOC
} as const

const BESSOperationDataPage = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.BESS, ProjectTypeId.PV_BESS],
  })

  const { projectId } = useParams()
  const [searchParams] = useSearchParams()

  const start = searchParams.get('start')
  const end = searchParams.get('end')

  // Parse query params for date range

  const kpiInstances = useGetKPIInstances({
    queryParams: {
      project_ids: [projectId || '-1'],
      deep: true,
      kpi_type_ids: [
        KPI_TYPE_IDS.ENERGY_CHARGED,
        KPI_TYPE_IDS.ENERGY_DISCHARGED,
        KPI_TYPE_IDS.CYCLE_COUNT,
        KPI_TYPE_IDS.VOLTAGE,
        KPI_TYPE_IDS.SOC,
      ],
    },
    queryOptions: { enabled: !!projectId },
  })

  // Fetch devices for name lookup
  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      deep: true,
      device_type_ids: [27, 32, 33], // BESS device types
    },
    queryOptions: { enabled: !!projectId },
  })

  const hasEnergyCharged = kpiInstances.data?.some(
    (instance) => instance.kpi_type_id === KPI_TYPE_IDS.ENERGY_CHARGED,
  )
  const hasEnergyDischarged = kpiInstances.data?.some(
    (instance) => instance.kpi_type_id === KPI_TYPE_IDS.ENERGY_DISCHARGED,
  )

  const hasCycleCount = kpiInstances.data?.some(
    (instance) => instance.kpi_type_id === KPI_TYPE_IDS.CYCLE_COUNT,
  )

  // TODO: Use kpiData for charts and analytics
  const kpiData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || '-1'],
      kpi_type_ids: kpiInstances.data?.map((instance) => instance.kpi_type_id),
      include_device_data: true,
      start: start || undefined,
      end: end || undefined,
    },
    queryOptions: {
      enabled: !!projectId && !!kpiInstances.data && !!start && !!end,
    },
  })

  // Round trip efficiency data
  const rteData = useGetRoundTripEfficiency({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: start || '',
      end: end || '',
    },
    queryOptions: {
      enabled: !!projectId && !!start && !!end,
    },
  })
  const theme = useMantineTheme()
  const themeColor = theme.colors[theme.primaryColor]?.[7] || '#1f77b4'

  const opacityHex = ({ opacity }: { opacity: number }) => {
    return Math.round(opacity * 255)
      .toString(16)
      .padStart(2, '0')
  }

  const opacity = ({ numTraces }: { numTraces: number | null }) => {
    return 1 / Math.sqrt(numTraces ?? 1)
  }

  // format x and y to be in the Data format expected for plotly traces
  const createPlotlyTrace = (
    x: string[],
    y: number[],
    name: string,
    opacity: number,
  ): Data => ({
    x,
    y,
    type: 'scatter',
    mode: 'lines+markers',
    name,
    hoverlabel: { namelength: -1 },
    line: { width: 2, color: themeColor + opacityHex({ opacity }) },
    marker: {
      color: themeColor + opacityHex({ opacity }),
    },
  })

  const generateTraces = (
    x: string[],
    y_data: Record<string, (number | null)[]>,
    devices_data: typeof devices.data,
  ): Data[] => {
    const numTraces = Object.keys(y_data).length
    const op = opacity({ numTraces })
    return Object.entries(y_data).map(([key, y]) => {
      // Look up device name_long using device_id
      const deviceName =
        devices_data?.find((device) => device.device_id.toString() === key)
          ?.name_long || `Device ${key}`

      return createPlotlyTrace(
        x,
        y.filter((val): val is number => val !== null),
        deviceName,
        op,
      )
    })
  }

  const parseKpiData = (kpiData: OperationalKPIData): Data[] => {
    const x = kpiData.data.dates
    const y_data = kpiData.data.device_data_obj?.device_values
    if (!y_data) {
      return []
    }
    return generateTraces(x, y_data, devices.data)
  }

  if (kpiInstances.isLoading || devices.isLoading) {
    return <PageLoader />
  }

  const sumArray = (numbers: (number | null)[]): number => {
    return numbers.reduce((sum: number, num) => sum + (num ?? 0), 0)
  }

  const energyChargedData = kpiData.data?.find(
    (data) => data.kpi_type_id === KPI_TYPE_IDS.ENERGY_CHARGED,
  )

  const totalEnergyCharged = sumArray(
    energyChargedData?.data.project_data || [],
  )
  const energyDischargedData = kpiData.data?.find(
    (data) => data.kpi_type_id === KPI_TYPE_IDS.ENERGY_DISCHARGED,
  )
  const totalEnergyDischarged = sumArray(
    energyDischargedData?.data.project_data || [],
  )

  const cycleCountData = kpiData.data?.find(
    (data) => data.kpi_type_id === KPI_TYPE_IDS.CYCLE_COUNT,
  )

  const totalCycleCount = sumArray(cycleCountData?.data.project_data || [])

  const roundTripEfficiency = rteData.data?.rte

  if (kpiInstances.data && kpiInstances.data.length > 0) {
    return (
      <>
        {/* Key Metrics Cards */}
        <SimpleGrid cols={{ base: 1, xs: 2, md: 4 }} mb="sm">
          {/* make sure that energy charged is in the kpi instances */}
          {hasEnergyCharged && (
            <MetricCard
              title="Energy Charged"
              value={`${totalEnergyCharged.toFixed(1)} MWh`}
              subtitle=""
              icon={<IconBatteryCharging size="1.2rem" stroke={1.5} />}
              tooltip="Total energy charged by BESS strings"
              isLoading={kpiData.isLoading}
            />
          )}
          {/* make sure that energy discharged is in the kpi instances */}
          {hasEnergyDischarged && (
            <MetricCard
              title="Energy Discharged"
              value={`${totalEnergyDischarged.toFixed(1)} MWh`}
              subtitle=""
              icon={<IconBolt size="1.2rem" stroke={1.5} />}
              tooltip="Total energy discharged by BESS strings"
              isLoading={kpiData.isLoading}
            />
          )}

          {/* make sure that energy discharged and energy charged are in the
            kpi instances */}
          {roundTripEfficiency && (
            <MetricCard
              title="Round Trip Efficiency"
              value={`${(roundTripEfficiency * 100).toFixed(1)}%`}
              subtitle=""
              icon={<IconBolt size="1.2rem" stroke={1.5} />}
              tooltip="Round trip efficiency of BESS strings"
              isLoading={rteData.isLoading}
            />
          )}

          {hasCycleCount && (
            <MetricCard
              title="Cycle Count"
              value={`${totalCycleCount.toFixed(1)} cycles`}
              subtitle=""
              icon={<IconBatteryCharging size="1.2rem" stroke={1.5} />}
              tooltip="Total cycle count of BESS strings"
              isLoading={kpiData.isLoading}
            />
          )}
        </SimpleGrid>

        <Stack gap="md" style={{ flex: 1 }}>
          {kpiInstances.data?.map((instance) => (
            <CustomCard
              title={instance.kpi_type?.name_long}
              info={instance.kpi_type?.description}
              key={instance.kpi_type_id}
              style={{ minHeight: '300px' }}
            >
              <PlotlyPlot
                data={(() => {
                  const foundData = kpiData.data?.find(
                    (data) => data.kpi_type_id === instance.kpi_type_id,
                  )
                  return foundData ? parseKpiData(foundData) : []
                })()}
                layout={{
                  xaxis: {
                    title: { text: 'Date' },
                    type: 'date',
                  },
                  yaxis: {
                    title: {
                      text: `${instance.kpi_type?.name_metric || 'BESS Data'}${
                        instance.kpi_type?.unit
                          ? ` [${instance.kpi_type.unit}]`
                          : ''
                      }`,
                    },
                  },
                  showlegend: false,
                }}
                isLoading={kpiData.isLoading}
                error={kpiData.error}
              />
            </CustomCard>
          ))}
        </Stack>
      </>
    )
  }
  return (
    <Card
      withBorder
      p="lg"
      style={{ backgroundColor: '#fff3cd', borderColor: '#ffeaa7' }}
    >
      <Group gap="sm">
        <IconAlertTriangle size={24} color="#856404" />
        <div>
          <Text size="md" fw={600} c="#856404">
            Data Configuration Required
          </Text>
          <Text size="sm" c="#856404" mt={4}>
            The tags to display this data are not yet configured. Reach out to
            the Proximal team about setting up tags for "String Total Charged
            Energy", "String Total Discharged Energy", and "String SOC".
          </Text>
        </div>
      </Group>
    </Card>
  )
}

const BESSOperation = () => {
  const pageInfo =
    'This page provides BESS operation insights and analysis for ' +
    'battery energy storage systems. It compares multiple KPIs ' +
    '(energy charged/discharged, cycle count, voltage, and SOC) ' +
    'and shows summary statistic cards for the selected date range.'

  return (
    <Stack h="100%" p="md" gap="lg">
      <Group justify="space-between" align="center" mb="sm">
        <Box px="md" pt="md">
          <PageTitle order={1} info={pageInfo}>
            BESS Operation
          </PageTitle>
        </Box>
        <AdvancedDatePicker
          defaultRange="past-month"
          includeTodayInDateRange={true}
          maxDays={30}
          includeClearButton={false}
        />
      </Group>

      <BESSOperationDataPage />
    </Stack>
  )
}

export default BESSOperation
