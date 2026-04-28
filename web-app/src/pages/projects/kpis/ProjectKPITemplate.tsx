import { DeviceTypeEnum, KPITypeEnum } from '@/api/enumerations'
import {
  OperationalKPIData,
  useGetKPIExcel,
  useGetOperationalKPIData,
} from '@/api/v1/operational/kpi_data'
import { useGetKPIInstances } from '@/api/v1/operational/kpi_instances'
import { KPIType, useGetProjectKPITypes } from '@/api/v1/operational/kpi_types'
import {
  Project,
  useGetProjects,
  useSelectProject,
} from '@/api/v1/operational/projects'
import { useGetUserProjectLabels } from '@/api/v1/operational/user_project_labels'
import CustomCard from '@/components/CustomCard'
import { ColorBar, MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { getQueryParamDateRange } from '@/components/datepicker/utils'
import Attribution from '@/components/gis/Attribution'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { GISContext } from '@/contexts/GISContext'
import { useGetDevicesV2 } from '@/hooks/api'
import { Device } from '@/hooks/types'
import * as gisUtils from '@/utils/GIS'
import {
  ActionIcon,
  Box,
  Button,
  Checkbox,
  Chip,
  Group,
  MantineTheme,
  Menu,
  Paper,
  SegmentedControl,
  Select,
  Stack,
  Text,
  Title,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import {
  IconArrowLeft,
  IconArrowRight,
  IconDots,
  IconDownload,
  IconExternalLink,
  IconInfoCircle,
} from '@tabler/icons-react'
import { AxiosError } from 'axios'
import type { Dayjs } from 'dayjs'
import { FeatureCollection } from 'geojson'
import { Data, PlotMouseEvent } from 'plotly.js'
import { ReactNode, useCallback, useContext, useState } from 'react'
import { Layer, Map, MapMouseEvent, Source } from 'react-map-gl/mapbox'
import {
  Link,
  NavigateFunction,
  useNavigate,
  useParams,
  useSearchParams,
} from 'react-router'

import { HoverInfo } from '../gis/utils'

const ICON_SIZE = 14
const MAX_DEVICES = 3000 // Do not render device visualizations for more than this many devices
const KPI_TYPE_IDS_REVERSE = [13, 14, 18, 19, 21, 22]
const ZERO_BASED_HOURS_KPI_IDS: Set<number> = new Set([
  KPITypeEnum.BESS_PROJECT_HOURS_CHARGING,
  KPITypeEnum.BESS_PROJECT_HOURS_DISCHARGING,
  KPITypeEnum.BESS_PROJECT_HOURS_IDLING,
])

const getYAxisRangeConfig = (kpiType: KPIType) => {
  if (kpiType.unit === '%') {
    return { range: [0, 1.05] as [number, number] }
  }
  if (ZERO_BASED_HOURS_KPI_IDS.has(kpiType.kpi_type_id)) {
    return { rangemode: 'tozero' as const }
  }
  return {}
}

const ProjectKPITemplatePage = () => {
  const { projectId, kpiTypeId } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const theme = useMantineTheme()

  const { start, end, startQuery, endQuery } = getQueryParamDateRange({
    searchParams,
  })

  // Query Project data
  const project = useSelectProject(projectId!)

  const kpiTypesWithContracts = useGetProjectKPITypes({
    pathParams: { projectId: projectId || '-1' },
  })

  // Query KPI data
  const kpiType = kpiTypesWithContracts.data?.find(
    (kpiType) => kpiType.kpi_type_id === Number(kpiTypeId),
  ) as KPIType

  const kpiInstanceData = useGetKPIInstances({
    queryParams: {
      project_ids: [projectId ?? '-1'],
      deep: true,
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })
  const kpiInstances = kpiInstanceData.data?.filter((instance) =>
    kpiTypesWithContracts.data?.find(
      (kpiType) =>
        kpiType.kpi_type_id.toString() === instance.kpi_type_id.toString() &&
        (!kpiType.contracts || kpiType.contracts.length === 0),
    ),
  )

  const sortedKpiInstances = kpiInstances
    ?.filter((instance) => instance.is_visible)
    .sort((a, b) => Number(a.kpi_type_id) - Number(b.kpi_type_id))

  const kpiInstanceIndex = sortedKpiInstances?.findIndex(
    (kpiInstance) => Number(kpiInstance.kpi_type_id) === Number(kpiTypeId),
  )

  const startStr = start?.format('YYYY-MM-DD')
  const endStr = end?.format('YYYY-MM-DD')

  const kpiTypeToUrl = (kpiTypeIdToNavigate: number) =>
    `/projects/${projectId}/kpis/type/${kpiTypeIdToNavigate}?start=${startStr}&end=${endStr}`

  const prevKpiTypeId =
    kpiInstanceIndex !== undefined
      ? sortedKpiInstances?.[kpiInstanceIndex - 1]?.kpi_type_id
      : undefined
  const nextKpiTypeId =
    kpiInstanceIndex !== undefined
      ? sortedKpiInstances?.[kpiInstanceIndex + 1]?.kpi_type_id
      : undefined

  const goToPrevKpiType = () => {
    if (prevKpiTypeId === undefined) return
    navigate(kpiTypeToUrl(prevKpiTypeId))
  }

  const goToNextKpiType = () => {
    if (nextKpiTypeId === undefined) return
    navigate(kpiTypeToUrl(nextKpiTypeId))
  }

  const atMaxKPIInstanceIndex =
    kpiInstanceIndex === (sortedKpiInstances?.length ?? 0) - 1

  // Query devices
  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [kpiType?.device_type_id],
    },
    queryOptions: { enabled: !!kpiType },
  })

  const kpiData = useGetOperationalKPIData({
    queryParams: {
      start: startQuery || '',
      end: endQuery || '',
      project_ids: [projectId || '-1'],
      kpi_type_ids: [Number(kpiTypeId) || -1],
      include_device_data: true,
    },
    queryOptions: {
      enabled: !!projectId && !!kpiTypeId && !!startQuery && !!endQuery,
    },
  })

  const kpiExcel = useGetKPIExcel({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      kpi_type_id: Number(kpiTypeId) || -1,
      start: startQuery || '',
      end: endQuery || '',
    },
    queryOptions: {
      enabled: false,
    },
  })

  const portfolioProjects = useGetProjects({
    queryOptions: {
      enabled: !!projectId && !!kpiTypeId && !!startQuery && !!endQuery,
    },
  })

  const userProjectLabels = useGetUserProjectLabels()
  const [selectedLabelName, setSelectedLabelName] = useState<string | null>(
    null,
  )

  const handleChipClick = (event: React.MouseEvent<HTMLInputElement>) => {
    if (event.currentTarget.value === selectedLabelName) {
      setSelectedLabelName(null)
    }
  }

  const portfolioKpiData = useGetOperationalKPIData({
    queryParams: {
      start: startQuery || '',
      end: endQuery || '',
      kpi_type_ids: [Number(kpiTypeId) || -1],
      include_device_data: true,
      project_ids:
        portfolioProjects.data?.map((project) => project.project_id) || [],
    },
    queryOptions: {
      enabled: !!projectId && !!kpiTypeId && !!startQuery && !!endQuery,
    },
  })

  const selectedLabelProjectIdSet = selectedLabelName
    ? new Set(
        userProjectLabels.data?.find(
          (label) => label.name === selectedLabelName,
        )?.project_ids ?? [],
      )
    : null

  const filteredPortfolioKpiData = portfolioKpiData.data?.filter((kpi) => {
    // Never include the current project in the "portfolio comparison" traces.
    if (kpi.project_id === projectId) return false

    // If a label is selected, only include projects assigned to it.
    if (!selectedLabelProjectIdSet) return true

    return selectedLabelProjectIdSet.has(kpi.project_id)
  })

  const data = kpiData.data?.[0]

  const isLoading =
    project.isLoading || kpiTypesWithContracts.isLoading || devices.isLoading
  const isError =
    project.isError ||
    kpiTypesWithContracts.isError ||
    devices.isError ||
    kpiData.isError

  const kpiDocUrl = kpiType?.doc_url

  if (isLoading) {
    return <PageLoader />
  }

  const showProjectData = true
  const showDeviceData =
    !!kpiType &&
    kpiType.device_type_id != DeviceTypeEnum.PROJECT &&
    !!devices.data &&
    devices.data.length <= MAX_DEVICES
  const showMapData =
    !!kpiType &&
    kpiType.device_type_id != DeviceTypeEnum.PROJECT &&
    !!devices.data &&
    devices.data.length <= MAX_DEVICES &&
    !!project.data &&
    project.data.spec.device_types_all_with_polygons?.includes(
      kpiType.device_type_id,
    )

  const dynamicHeight = !showDeviceData && !showMapData ? '100%' : 'auto'

  const downloadExcel = async () => {
    const { data: fetched } = await kpiExcel.refetch()
    if (fetched) {
      window.open(fetched, '_blank')
    }
  }

  return (
    <Stack p="md" h={dynamicHeight}>
      <Group gap="xs">
        <Title>{kpiType?.name_long}</Title>
        {kpiType?.description && (
          <Tooltip label={kpiType?.description}>
            <IconInfoCircle />
          </Tooltip>
        )}
      </Group>
      <Group justify="space-between">
        <AdvancedDatePicker
          includeClearButton={false}
          defaultRange="past-month"
        />
        {kpiInstanceIndex !== undefined && sortedKpiInstances && (
          <Paper withBorder p={6}>
            <Group>
              <ActionIcon
                variant="subtle"
                size="sm"
                onClick={goToPrevKpiType}
                disabled={kpiInstanceIndex === 0}
              >
                <IconArrowLeft />
              </ActionIcon>
              <Menu>
                <Menu.Target>
                  <ActionIcon variant="subtle" size="sm">
                    <IconDots />
                  </ActionIcon>
                </Menu.Target>
                <Menu.Dropdown>
                  {sortedKpiInstances?.map((kpiInstance) => (
                    <Link
                      key={kpiInstance.kpi_type_id}
                      to={kpiTypeToUrl(kpiInstance.kpi_type_id)}
                      style={{ textDecoration: 'none' }}
                    >
                      <Menu.Item key={kpiInstance.kpi_type_id}>
                        {kpiInstance.kpi_type?.name_long}
                      </Menu.Item>
                    </Link>
                  ))}
                </Menu.Dropdown>
              </Menu>
              <ActionIcon
                variant="subtle"
                size="sm"
                onClick={goToNextKpiType}
                disabled={atMaxKPIInstanceIndex}
              >
                <IconArrowRight />
              </ActionIcon>
            </Group>
          </Paper>
        )}

        <Group>
          <Tooltip
            label="Documentation for this KPI coming soon!"
            disabled={!!kpiDocUrl}
          >
            <Button
              variant="default"
              rightSection={<IconExternalLink size={ICON_SIZE} />}
              onClick={() =>
                window.open(
                  `https://docs.proximal.energy/kpi/${kpiDocUrl}`,
                  '_blank',
                )
              }
              disabled={!kpiDocUrl}
            >
              Documentation
            </Button>
          </Tooltip>

          <Button
            rightSection={<IconDownload size={ICON_SIZE} />}
            disabled={!kpiTypeId || !startQuery || !endQuery || !projectId}
            onClick={() => downloadExcel()}
            loading={kpiExcel.isLoading}
          >
            Download
          </Button>
        </Group>
      </Group>
      {userProjectLabels.data && userProjectLabels.data.length > 0 && (
        <Group>
          <Title order={4} size="h5">
            Compare with:
          </Title>
          <Chip.Group
            multiple={false}
            value={selectedLabelName}
            onChange={(value) => {
              setSelectedLabelName((prev) => (value === prev ? null : value))
            }}
          >
            {userProjectLabels.data.map((label) => (
              <Chip
                key={label.name}
                value={label.name}
                color={label.color}
                variant="filled"
                onClick={handleChipClick}
              >
                {label.name}
              </Chip>
            ))}
          </Chip.Group>
        </Group>
      )}
      {showProjectData && (
        <ProjectPlotCard
          data={data}
          kpiType={kpiType || ({} as KPIType)}
          cardTitle="Project Data"
          isLoading={kpiData.isLoading || portfolioKpiData.isLoading}
          isError={isError}
          height={!showDeviceData && !showMapData ? '100%' : '35vh'}
          portfolioKpiData={filteredPortfolioKpiData}
          portfolioProjects={portfolioProjects.data}
          theme={theme}
          navigate={navigate}
          kpiTypeId={kpiTypeId || ''}
          start={start}
          end={end}
        />
      )}
      {showDeviceData && (
        <DevicePlotCard
          data={data}
          devices={devices.data || []}
          kpiType={kpiType || ({} as KPIType)}
          cardTitle="Device Data"
          isLoading={kpiData.isLoading}
          isError={isError}
        />
      )}
      {showMapData && (
        <MapCard
          data={data}
          kpiType={kpiType || ({} as KPIType)}
          cardTitle="Map"
          devices={devices.data || []}
          isLoading={kpiData.isLoading}
          isError={isError}
        />
      )}
      {devices.data && devices.data.length > MAX_DEVICES && (
        <Group justify="center">
          <Text c="dimmed">
            Looking for more details? This KPI includes a large number of
            devices which cannot be displayed online. Click &apos;Download&apos;
            to view all device data.
          </Text>
        </Group>
      )}
    </Stack>
  )
}

const YAxisConfig = (kpiType: KPIType) => {
  const yAxisTickFormat = kpiType.unit === '%' ? ',.0%' : ',.2f'
  let unit_str = ''
  if (kpiType.unit) {
    unit_str = ' (' + kpiType.unit + ')'
  }
  const yAxisTitle = kpiType.name_metric + unit_str
  return { yAxisTickFormat, yAxisTitle }
}

interface DevicePlotCardProps {
  data: OperationalKPIData | undefined
  devices: Device[]
  kpiType: KPIType
  cardTitle: string
  isLoading: boolean
  isError: boolean
}

const SelectableChartCard = ({
  parsedData,
  cardTitle,
  plotType,
  setPlotType,
  kpiType,
  dates,
}: {
  parsedData: Data[] | undefined
  cardTitle: string
  plotType: string
  setPlotType: (value: string) => void
  kpiType: KPIType
  dates?: string[]
}) => {
  const computedColorScheme = useComputedColorScheme('dark')
  const { yAxisTickFormat, yAxisTitle } = YAxisConfig(kpiType)

  const plotLayout =
    plotType === 'bar'
      ? {
          xaxis: {
            type: 'category' as const,
            title: {
              text: 'Device',
            },
          },
          yaxis: {
            ...getYAxisRangeConfig(kpiType),
            tickformat: yAxisTickFormat,
            title: {
              text: yAxisTitle,
            },
          },
        }
      : plotType === 'line'
        ? {
            yaxis: {
              ...getYAxisRangeConfig(kpiType),
              tickformat: yAxisTickFormat,
              title: {
                text: yAxisTitle,
              },
            },
          }
        : plotType === 'box'
          ? {
              xaxis: {
                type: 'category' as const,
                categoryorder: 'array' as const,
                categoryarray: dates,
                range: [-0.5, (dates?.length || 0) - 0.5],
              },
              yaxis: {
                ...getYAxisRangeConfig(kpiType),
                tickformat: yAxisTickFormat,
                title: {
                  text: yAxisTitle,
                },
              },
            }
          : {
              yaxis: {
                type: 'category' as const,
                title: {
                  text: 'Device',
                },
              },
              margin: {
                b: 80,
              },
              plot_bgcolor:
                computedColorScheme === 'dark' ? '#2C2E33' : '#F8F9FA',
              // Theme-aware background for null values.
            }

  return (
    <>
      <CustomCard
        title={cardTitle}
        style={{ height: '50vh' }}
        headerChildren={
          <>
            <SegmentedControl
              size="xs"
              value={plotType}
              onChange={setPlotType}
              data={[
                { label: 'Heatmap', value: 'heatmap' },
                { label: 'Bar', value: 'bar' },
                { label: 'Line', value: 'line' },
                {
                  label: (
                    <Tooltip label="Each box plot summarizes the daily KPI distribution across all individual devices.">
                      <span>Box</span>
                    </Tooltip>
                  ),
                  value: 'box',
                },
              ]}
            />
          </>
        }
        key={plotType}
      >
        <PlotlyPlot
          data={parsedData}
          layout={plotLayout}
          colorscale={
            // For temperature heatmaps, use custom colorscale from data
            // (undefined = use data colorscale). For all other plots, use
            // the red-green scale from PlotlyPlot.
            plotType === 'heatmap' && kpiType.unit === 'C'
              ? undefined
              : KPI_TYPE_IDS_REVERSE.includes(kpiType.kpi_type_id)
                ? 'good-bad-reversed'
                : 'good-bad'
          }
        />
      </CustomCard>
    </>
  )
}

const DevicePlotCard = ({
  data,
  devices,
  kpiType,
  cardTitle,
  isLoading,
  isError,
}: DevicePlotCardProps) => {
  const [plotType, setPlotType] = useState('heatmap')
  const context = useContext(GISContext)

  if (isLoading || isError || !data) {
    return (
      <CustomCard title={cardTitle} style={{ height: '50vh' }}>
        <PlotlyPlot
          data={[]}
          layout={{}}
          isLoading={isLoading}
          error={isError ? new AxiosError() : undefined}
        />
      </CustomCard>
    )
  }

  const device_values = data?.data.device_data_obj?.device_values

  const parseData = (data: OperationalKPIData, yAxisTitle: string) => {
    switch (plotType) {
      case 'bar': {
        const x = Object.keys(device_values || {}).map(
          (key) =>
            devices.find((device) => device.device_id.toString() === key)
              ?.name_long,
        )
        let aggregation: number[] = []
        if (kpiType.aggregation_method == 'average') {
          aggregation = Object.values(device_values || {}).map((values) =>
            values
              .filter((v): v is number => v !== null)
              .reduce((acc, val) => acc + val, 0),
          )
          aggregation = aggregation.map(
            (val, idx) =>
              val /
              (device_values?.[Object.keys(device_values || {})[idx]].length ??
                1),
          )
        } else if (kpiType.aggregation_method == 'sum') {
          aggregation = Object.values(device_values || {}).map((values) =>
            values
              .filter((v): v is number => v !== null)
              .reduce((acc, val) => acc + val, 0),
          )
        }

        return [
          {
            x: x,
            y: aggregation,
            type: 'bar',
            hovertemplate:
              kpiType.unit === null
                ? `%{x}<br>%{y:.2f}<extra></extra>`
                : kpiType.unit === '%'
                  ? `%{x}<br>%{y:.2%}<extra></extra>`
                  : `%{x}<br>%{y:.2f} ${kpiType.unit}<extra></extra>`,
          },
        ] as Data[]
      }

      case 'heatmap': {
        const x = data.data.dates
        const y = Object.keys(device_values || {}).map(
          (key) =>
            devices.find((device) => device.device_id.toString() === key)
              ?.name_long,
        )

        // Keep null values as null - Plotly will render them as transparent
        const z = Object.values(device_values || {}).map(
          (values) => values.map((value) => value), // Keep null values as null
        )

        // Calculate min/max values excluding nulls for proper color scaling
        const allValues = z.flat().filter((v): v is number => v !== null)
        const minValue = allValues.length > 0 ? Math.min(...allValues) : 0
        const maxValue = allValues.length > 0 ? Math.max(...allValues) : 1

        return [
          {
            x: x,
            y: y,
            z: z,
            type: 'heatmap',
            hovertemplate:
              kpiType.unit === null
                ? `%{x}<br>%{y}<br>%{z:.2f}<extra></extra>`
                : kpiType.unit === '%'
                  ? `%{x}<br>%{y}<br>%{z:.2%}<extra></extra>`
                  : `%{x}<br>%{y}<br>%{z:.2f} ${kpiType.unit}<extra></extra>`,
            colorbar: {
              tickformat: kpiType.unit === '%' ? ',.0%' : ',.2f',
              title: {
                text: yAxisTitle,
                side: 'top',
              },
              orientation: 'h',
              x: 0.5,
              xanchor: 'center',
              y: -0.1,
              yanchor: 'top',
              len: 0.6,
              thickness: 12,
            },
            // Use a custom colorscale only for temperature KPIs (Celsius)
            // For non-temperature KPIs, the colorscale prop will apply the red-green scale
            colorscale:
              kpiType.unit === 'C' && context
                ? [
                    [0, context.colorsTemperature[0].value], // Blue for minimum value (cold)
                    [0.33, context.colorsTemperature[1].value], // Light blue for lower-middle
                    [0.67, context.colorsTemperature[2].value], // Orange for upper-middle
                    [1, context.colorsTemperature[3].value], // Red for maximum value (hot)
                  ]
                : undefined,
            zmin: minValue,
            zmax: maxValue,
            showscale: true,
            connectgaps: false, // Don't connect gaps (null values)
          },
        ] as unknown as Data[]
      }

      case 'line': {
        // Create an array of traces, one for each device
        const traces = Object.entries(device_values || {}).map(
          ([deviceId, values]) => {
            const deviceName = devices.find(
              (device) => device.device_id.toString() === deviceId,
            )?.name_long

            return {
              x: data.data.dates,
              y: values,
              type: 'scatter',
              mode: 'lines+markers',
              connectgaps: false,
              name: deviceName,
              hovertemplate:
                kpiType.unit === null
                  ? `%{y:.2f}<extra>${deviceName}</extra>`
                  : kpiType.unit === '%'
                    ? `%{y:.2%}<extra>${deviceName}</extra>`
                    : `%{y:.2f} ${kpiType.unit}<extra>${deviceName}</extra>`,
            }
          },
        )
        return traces // PlotlyPlot will spread this in the data array
      }

      case 'box': {
        // Create box plots for each date, showing distribution of device values
        const dates = data.data.dates
        const boxTraces = dates.map((date, dateIndex) => {
          // Collect all device values for this specific date
          const dateValues: number[] = []

          Object.values(device_values || {}).forEach((deviceValues) => {
            const value = deviceValues[dateIndex]
            if (value !== null && value !== undefined) {
              dateValues.push(value)
            }
          })

          // Return box plot trace for every date, even if no data
          return {
            y: dateValues, // Empty array if no data
            type: 'box',
            name: date,
            showlegend: false,
            jitter: 0.3,
            pointpos: 0,
            marker: {
              color: '#228BE6', // Use a consistent blue color for all boxes
            },
            line: {
              color: '#228BE6', // Consistent color for box outlines
            },
          }
        })
        return boxTraces
      }
    }
  }

  const { yAxisTitle } = YAxisConfig(kpiType)
  const parsedData = data.data && parseData(data, yAxisTitle)

  return (
    <SelectableChartCard
      parsedData={parsedData as Data[]}
      plotType={plotType}
      setPlotType={setPlotType}
      cardTitle={cardTitle}
      kpiType={kpiType}
      dates={data.data?.dates}
    />
  )
}

const ProjectPlotCard = ({
  data,
  kpiType,
  cardTitle,
  isLoading,
  isError,
  height,
  portfolioKpiData,
  portfolioProjects,
  theme,
  navigate,
  kpiTypeId,
  start,
  end,
}: {
  data: OperationalKPIData | undefined
  kpiType: KPIType
  cardTitle: ReactNode
  isLoading: boolean
  isError: boolean
  height: string
  portfolioKpiData: OperationalKPIData[] | undefined
  portfolioProjects: Project[] | undefined
  theme: MantineTheme
  navigate: NavigateFunction
  kpiTypeId: string
  start: Dayjs | null
  end: Dayjs | null
}) => {
  const [showComparison, setShowComparison] = useState(true)
  const [selectedAggregationType, setSelectedAggregationType] = useState<
    string | null
  >(null)
  if (isLoading || isError || !data) {
    return (
      <CustomCard title={cardTitle} style={{ height: height }}>
        <PlotlyPlot
          data={[]}
          layout={{}}
          isLoading={isLoading}
          error={isError ? new AxiosError() : undefined}
        />
      </CustomCard>
    )
  }
  const { yAxisTickFormat, yAxisTitle } = YAxisConfig(kpiType)

  const handleProjectKpiTemplateClick = (event: Readonly<PlotMouseEvent>) => {
    if (!event.points?.[0]) {
      return
    }
    const point = event.points[0]
    const clickedProjectId = point.data.customdata[0] as string

    // Navigate to the same page but with the clicked project's ID
    navigate(
      `/projects/${clickedProjectId}/kpis/type/${kpiTypeId}?start=${start?.format('YYYY-MM-DD')}&end=${end?.format('YYYY-MM-DD')}`,
    )
  }

  // Helper function to get the appropriate data source
  const getDataValues = (kpiData: OperationalKPIData) => {
    if (selectedAggregationType && kpiData.data.device_aggregation_obj) {
      const aggregationData =
        kpiData.data.device_aggregation_obj[
          selectedAggregationType as keyof typeof kpiData.data.device_aggregation_obj
        ]
      if (aggregationData) {
        return aggregationData
      }
    }
    return kpiData.data.project_data
  }

  // Get available aggregation types from the data, excluding problematic ones
  const problematicAggregations = ['sum', 'count', 'available_data']
  const availableAggregationTypes = data?.data.device_aggregation_obj
    ? Object.keys(data.data.device_aggregation_obj).filter(
        (key) =>
          data.data.device_aggregation_obj?.[
            key as keyof typeof data.data.device_aggregation_obj
          ] && !problematicAggregations.includes(key),
      )
    : []

  // Helper function to format aggregation type labels
  const formatAggregationLabel = (type: string) => {
    const labelMap: { [key: string]: string } = {
      sum: 'Sum',
      mean: 'Mean',
      std: 'Standard Deviation',
      min: 'Minimum',
      max: 'Maximum',
      median: 'Median',
      count: 'Count',
      range: 'Range',
      available_data: 'Available Data',
    }
    return (
      labelMap[type] ||
      type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')
    )
  }

  const aggregationOptions = [
    { value: 'default', label: 'Default' },
    ...availableAggregationTypes.map((type) => ({
      value: type,
      label: formatAggregationLabel(type),
    })),
  ]

  return (
    <CustomCard
      title={cardTitle}
      headerChildren={
        <Group gap="md">
          {availableAggregationTypes.length > 0 && (
            <Group gap="xs">
              <Select
                size="xs"
                placeholder="Select data source"
                value={selectedAggregationType || 'default'}
                onChange={(value) =>
                  setSelectedAggregationType(
                    value === 'project_data' ? null : value,
                  )
                }
                data={aggregationOptions}
              />
              <Tooltip
                label={
                  <>
                    <Text fw={600} size="sm">
                      Default
                    </Text>
                    <Text size="sm">Canonical aggregation across devices.</Text>
                    <Text fw={600} size="sm">
                      Other Aggregations
                    </Text>
                    <Text size="sm">
                      Standard statistical aggregations calculated across
                      devices (e.g., mean, minimum, maximum, median, standard
                      deviation).
                    </Text>
                  </>
                }
                multiline
                w={300}
              >
                <IconInfoCircle size={16} style={{ cursor: 'help' }} />
              </Tooltip>
            </Group>
          )}
          <Checkbox
            checked={showComparison}
            onChange={() => setShowComparison(!showComparison)}
            label="Show Portfolio Comparison"
          />
        </Group>
      }
      style={{ height: height }}
    >
      <PlotlyPlot
        // Key is used to force a re-render
        // Plotly does not resize the plot when the legend is shown/hidden or data source changes
        key={`${showComparison ? 'portfolio' : 'project'}-${selectedAggregationType || 'project'}`}
        data={[
          ...(showComparison
            ? portfolioKpiData?.map((kpi) => ({
                x: kpi.data.dates,
                y: getDataValues(kpi),
                type: 'scatter' as const,
                mode: 'lines' as const,
                connectgaps: false,
                customdata: [kpi.project_id as Plotly.Datum],
                opacity: 0.5,
                name: portfolioProjects?.find(
                  (project) => project.project_id === kpi.project_id,
                )?.name_long,
                hoverlabel: { namelength: -1 },
              })) || []
            : []),
          {
            x: data.data.dates,
            y: getDataValues(data),
            type: 'scatter',
            mode: 'lines+markers',
            customdata: [data.project_id as Plotly.Datum],
            connectgaps: false,
            name: portfolioProjects?.find(
              (project) => project.project_id === data.project_id,
            )?.name_long,
            line: { color: theme.colors[theme.primaryColor][7] },
            marker: { color: theme.colors[theme.primaryColor][7] },
            hoverlabel: { namelength: -1 },
          },
        ]}
        layout={{
          yaxis: {
            ...getYAxisRangeConfig(kpiType),
            title: {
              text: yAxisTitle,
            },
            tickformat: yAxisTickFormat,
          },
          legend: {
            traceorder: 'reversed',
          },
          hovermode: 'closest',
        }}
        onClick={handleProjectKpiTemplateClick}
      />
    </CustomCard>
  )
}

function MapHoverCard({
  hoverInfo,
  kpiType,
}: {
  hoverInfo: HoverInfo
  kpiType: KPIType
}) {
  const hoverValue = hoverInfo.feature?.properties?.value
  const hoverValueText =
    hoverValue != null
      ? kpiType.unit === '%'
        ? `${(hoverValue * 100).toFixed(2)}%`
        : `${hoverValue.toFixed(2)} ${kpiType.unit}`
      : 'No Data'

  return (
    <Paper
      p="xs"
      withBorder
      style={{
        left: hoverInfo.x,
        top: hoverInfo.y,
        position: 'absolute',
        zIndex: 9,
        pointerEvents: 'none',
      }}
    >
      <Text fw={700}>{hoverInfo.feature?.properties?.name}</Text>
      <Text>{hoverValueText}</Text>
    </Paper>
  )
}

const MapCard = ({
  data,
  kpiType,
  cardTitle,
  devices,
  isLoading,
  isError,
}: {
  data: OperationalKPIData | undefined
  kpiType: KPIType
  cardTitle: string
  devices: Device[]
  isLoading: boolean
  isError: boolean
}) => {
  const context = useContext(GISContext)
  const computedColorScheme = useComputedColorScheme('dark')
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })
  const blankMapStyle = gisUtils.useBlankMapStyle()

  const onHover = useCallback((event: MapMouseEvent) => {
    const {
      features,
      point: { x, y },
    } = event

    const hoveredFeature = features && features[0]

    if (hoveredFeature) {
      setHoverInfo({
        feature: hoveredFeature,
        x,
        y,
      })
    } else {
      setHoverInfo({
        feature: null,
        x: 0,
        y: 0,
      })
    }
  }, [])

  if (isLoading || isError || !data) {
    return (
      <CustomCard title={cardTitle} style={{ height: '50vh' }} fill={true}>
        <PlotlyPlot
          data={[]}
          layout={{}}
          isLoading={isLoading}
          error={isError ? new AxiosError() : undefined}
        />
      </CustomCard>
    )
  }

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, showSatellite, colorsGoodBad } = context

  const device_values = data?.data.device_data_obj?.device_values
  let aggregation: {
    [k: string]: number
  } = {}

  if (kpiType.aggregation_method === 'average') {
    aggregation = Object.fromEntries(
      Object.entries(device_values || {}).map(([key, arr]) => {
        // Filter out null or undefined entries
        const validValues = arr.filter((val) => val != null)
        // Compute average
        const average =
          validValues.reduce((sum, val) => sum + val, 0) / validValues.length ||
          0
        return [key, average]
      }),
    )
  } else if (kpiType.aggregation_method === 'sum') {
    aggregation = Object.fromEntries(
      Object.entries(device_values || {}).map(([key, arr]) => {
        return [key, arr.reduce((acc, val) => (acc ?? 0) + (val ?? 0), 0) || 0]
      }),
    )
  }

  const gisData: FeatureCollection = {
    type: 'FeatureCollection',
    features: devices?.map((device) => {
      return {
        type: 'Feature',
        properties: {
          name: device.name_long,
          value: aggregation[device.device_id],
        },
        geometry:
          typeof device.polygon === 'string'
            ? JSON.parse(device.polygon)
            : device.polygon,
      }
    }),
  } as FeatureCollection

  const mapStyleEmpty = false

  const values = Object.values(aggregation || {})
  const numberValues = values.flat().filter((v): v is number => v != null)

  let lowValue: number
  let highValue: number
  let lowLabel: string
  let highLabel: string
  switch (kpiType.unit) {
    case '%':
      lowValue = 0
      highValue = 1
      lowLabel = '0%'
      highLabel = '100%'
      break
    default:
      lowValue = Math.min(0, ...numberValues)
      highValue = Math.max(...numberValues)
      // Handle case where all values are null (Math.max([]) returns -Infinity)
      if (!isFinite(highValue)) {
        lowValue = 0
        highValue = 1
      }
      lowLabel = `${lowValue.toFixed(2)} ${kpiType.unit}`
      highLabel = `${highValue.toFixed(2)} ${kpiType.unit}`
  }

  // For temperature KPIs, use blue (cold) to red (hot) color scale
  // For other KPIs, use the standard good-bad color scale
  const colorsBadGood = [...colorsGoodBad].reverse()
  const colors =
    kpiType.unit === 'C'
      ? context.colorsTemperature
      : KPI_TYPE_IDS_REVERSE.includes(kpiType.kpi_type_id)
        ? colorsBadGood
        : colorsGoodBad

  return (
    <CustomCard
      title={cardTitle}
      style={{ height: '50vh' }}
      fill
      info="Map data is aggregated over the requested interval."
    >
      <div
        style={{
          position: 'relative',
          height: '100%',
          width: '100%',
        }}
      >
        <div style={{ height: '100%', width: '100%' }}>
          <>
            <Map
              key="map"
              initialViewState={{
                bounds: gisUtils.findBoundingBox(gisData),
                fitBoundsOptions: {
                  padding: {
                    top: 25,
                    bottom: 25,
                    left: 65,
                    right: 65,
                  },
                },
              }}
              style={{
                borderBottomLeftRadius: 'inherit',
                borderBottomRightRadius: 'inherit',
              }}
              mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
              interactiveLayerIds={['data']}
              onMouseMove={onHover}
              mapStyle={
                gisUtils.mapStyle({
                  empty: mapStyleEmpty,
                  satellite: showSatellite,
                  theme: computedColorScheme,
                }) ?? blankMapStyle
              }
            >
              <Source id="data" type="geojson" data={gisData}>
                <Layer
                  {...gisUtils.layerData({
                    featureKey: 'value',
                    colors: colors,
                    lowValue: lowValue,
                    highValue: highValue,
                  })}
                />
                <Layer {...gisUtils.layerNonComm({ featureKey: 'value' })} />
                {showLabels && (
                  <Layer {...gisUtils.layerLabel({ textField: 'name' })} />
                )}
              </Source>
              {hoverInfo.feature && (
                <MapHoverCard hoverInfo={hoverInfo} kpiType={kpiType} />
              )}
            </Map>
            <Box
              style={{
                position: 'absolute',
                top: 0,
                right: 0,
                zIndex: 1,
                height: '100%',
              }}
              px="md"
              py={75}
            >
              <ColorBar
                gradient={gisUtils.colorBar({ colors: colors })}
                lowLabel={lowLabel}
                highLabel={highLabel}
              />
            </Box>
          </>
        </div>
        <Box
          style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 10 }}
          px="md"
          py="md"
        >
          <MapSettings disableSatellite={mapStyleEmpty} />
        </Box>
        <Attribution />
      </div>
    </CustomCard>
  )
}

export default ProjectKPITemplatePage
