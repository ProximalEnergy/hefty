import { useGetUserType } from '@/api/admin'
import {
  DeviceTypeEnum,
  KPITypeEnum,
  ProjectTypeEnum,
  UserTypeEnumEnum,
} from '@/api/enumerations'
import { useGetDeviceModels } from '@/api/v1/operational/device_models'
import { useGetKPISummaryCards } from '@/api/v1/operational/project/kpi_data'
import { useGetOMContractorScopes } from '@/api/v1/operational/project/om_contractors'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetInverters } from '@/api/v1/operational/pv_inverters'
import { useGetEquipmentAnalysisPCSv2 } from '@/api/v1/protected/web-application/projects/equipment-analysis/pv_inverter'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetDevicesV2, useGetHeatmap } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import * as types from '@/hooks/types'
import { useResizePlotlyCharts } from '@/hooks/useResizePlotlyCharts'
import {
  getDeviceModelImagePublicUrl,
  getDeviceModelImageUrl,
} from '@/utils/cdn'
import { QUERY_TIME } from '@/utils/queryTiming'
import {
  ActionIcon,
  Box,
  Button,
  Checkbox,
  Group,
  Image,
  Modal,
  RingProgress,
  SimpleGrid,
  Skeleton,
  Slider,
  Stack,
  Tabs,
  Text,
  useComputedColorScheme,
} from '@mantine/core'
import {
  IconEdit,
  IconExternalLink,
  IconInfoCircle,
  IconMail,
  IconPhone,
  IconPlayerPauseFilled,
  IconPlayerPlayFilled,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { PlotType } from 'plotly.js'
import { SyntheticEvent, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'

import RealtimeTab from './RealtimeTab'

dayjs.extend(utc)
dayjs.extend(timezone)

const colorFromPercent = (numerator: number, denominator: number) => {
  const percent = (numerator / denominator) * 100
  if (percent >= 90) {
    return 'green'
  } else if (percent >= 75) {
    return 'yellow'
  } else {
    return 'red'
  }
}

const PCSHeatmap = ({
  startQuery,
  endQuery,
}: {
  startQuery: string | undefined
  endQuery: string | undefined
}) => {
  const { projectId } = useParams<{ projectId: string }>()

  const { data, isLoading, error } = useGetHeatmap({
    pathParams: {
      projectId: projectId || '-1',
      sensorTypeName: 'pv_inverter_ac_power',
    },
    queryParams: {
      start: startQuery,
      end: endQuery,
    },
  })

  return (
    <PlotlyPlot
      data={[
        {
          z: data?.z,
          x: data?.x,
          y: data?.y,
          type: 'heatmap',
          colorbar: {
            title: {
              text: 'Power (MW)',
            },
            ticksuffix: ' MW',
          },
        },
      ]}
      layout={{
        xaxis: {
          tickangle: -45,
        },
        yaxis: {
          type: 'category',
          dtick: 1,
          tick0: 0,
          title: {
            text: 'Inverter Name',
          },
        },
        height: 450,
      }}
      colorscale={'primary'}
      isLoading={isLoading}
      error={error}
    />
  )
}

interface RingProgressCardProps {
  title: string
  subtitle: string
  value: number | null
  total: number | null
  color?: string
  isLoading: boolean
  size?: number
  skeletonHeight?: number
  skeletonMargin?: number
}

const RingProgressCard: React.FC<RingProgressCardProps> = ({
  title,
  subtitle,
  value,
  total,
  color = 'grey',
  isLoading,
  size = 150,
  skeletonHeight = 111,
  skeletonMargin = 19.5,
}) => {
  return (
    <Stack align="center" gap={0}>
      <Text>{title}</Text>
      <Text size="sm">{subtitle}</Text>
      {isLoading ? (
        <Skeleton height={skeletonHeight} circle m={skeletonMargin} />
      ) : (
        <RingProgress
          size={size}
          thickness={Math.max(4, Math.floor(size / 16))}
          style={{ '--rp-size': `${size}px` } as React.CSSProperties}
          label={
            <Text size="lg" fw={700} ta="center">
              {value !== null && total !== null
                ? `${value}/${total}`
                : 'No Data'}
            </Text>
          }
          sections={[
            {
              value:
                value !== null && total !== null ? (value / total) * 100 : 0,
              color,
            },
          ]}
        />
      )}
    </Stack>
  )
}

const PCSEquipmentAnalysis = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeEnum.PV, ProjectTypeEnum.PVS],
  })

  const { projectId } = useParams<{ projectId: string }>()
  const userType = useGetUserType({})
  const colorScheme = useComputedColorScheme()
  const isSuperadmin =
    userType.data?.user_type_id === UserTypeEnumEnum.SUPERADMIN
  const isAdmin =
    userType.data?.user_type_id === UserTypeEnumEnum.ADMIN ||
    userType.data?.user_type_id === UserTypeEnumEnum.SUPERADMIN
  const [sliderValue, setSliderValue] = useState(0)
  const [initialSliderValueSet, setInitialSliderValueSet] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const intervalRef = useRef<number | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = useMemo(() => {
    const tab = searchParams.get('tab')
    if (tab === 'realtime' || tab === 'current-day') {
      return tab
    }
    if (isSuperadmin && tab === 'long-term') {
      return tab
    }
    return 'current-day'
  }, [isSuperadmin, searchParams])
  const setTab = (value: string | null) => {
    const nextTab = value || 'current-day'
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('tab', nextTab)
    setSearchParams(nextParams, { replace: true })
  }
  const tabPanelRef = useRef<HTMLDivElement>(null)
  const { start, end } = useValidateDateRange({})

  const [blockNormalize, setBlockNormalize] = useState(false)
  const [pcsNormalize, setPcsNormalize] = useState(false)
  const [imageModalOpened, setImageModalOpened] = useState(false)
  const [modalActiveTab, setModalActiveTab] = useState<string>('overview')
  const modalContentRef = useRef<HTMLDivElement>(null)

  // Get all PV Inverter devices for header
  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [DeviceTypeEnum.PV_INVERTER],
    },
    queryOptions: {
      enabled: !!projectId,
      staleTime: QUERY_TIME.NEVER, // Never refetch - header data should be static
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  // Get unique device_model_ids from devices
  const deviceModelIds = useMemo(() => {
    if (!devices.data || devices.data.length === 0) return []
    const modelIds = new Set<number>()
    devices.data.forEach((device: types.Device) => {
      if (
        device.device_model_id !== null &&
        device.device_model_id !== undefined
      ) {
        modelIds.add(device.device_model_id)
      }
    })
    return Array.from(modelIds).sort()
  }, [devices.data])

  // Memoize query params to ensure stable reference
  const deviceModelsQueryParams = useMemo(
    () => ({
      device_model_ids: deviceModelIds,
    }),
    [deviceModelIds],
  )

  // Get device models
  const deviceModels = useGetDeviceModels({
    queryParams: deviceModelsQueryParams,
    queryOptions: {
      enabled: deviceModelIds.length > 0,
      staleTime: QUERY_TIME.NEVER, // Never refetch - header data should be static
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  // Get O&M contractor scopes
  const omContractorScopes = useGetOMContractorScopes({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
      staleTime: QUERY_TIME.NEVER, // Never refetch - header data should be static
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  // Filter contractors that have PV_INVERTER (device_type_id 2) in their scope
  const pcsContractors = useMemo(() => {
    if (!omContractorScopes.data) return []
    return omContractorScopes.data.filter((scope) =>
      scope.scope_json?.device_type_ids?.includes(DeviceTypeEnum.PV_INVERTER),
    )
  }, [omContractorScopes.data])

  // Get O&M and EPC contractors (first as O&M, second as EPC)
  const omContractor = pcsContractors[0] || null
  const epcContractor = pcsContractors[1] || null

  // Get the most common brand/model (or first one if all are unique)
  const pcsBrandModel = useMemo(() => {
    if (!deviceModels.data || deviceModels.data.length === 0) return null

    // Count occurrences of each brand/model combination
    const brandModelCounts = new Map<string, number>()
    devices.data?.forEach((device: types.Device) => {
      if (device.device_model_id) {
        const deviceModel = deviceModels.data?.find(
          (dm) => dm.device_model_id === device.device_model_id,
        )
        if (deviceModel) {
          const key = `${deviceModel.brand}|${deviceModel.model}`
          brandModelCounts.set(key, (brandModelCounts.get(key) || 0) + 1)
        }
      }
    })

    if (brandModelCounts.size === 0) return null

    // Get the most common brand/model
    let mostCommon = ''
    let maxCount = 0
    brandModelCounts.forEach((count, key) => {
      if (count > maxCount) {
        maxCount = count
        mostCommon = key
      }
    })

    if (mostCommon) {
      const [brand, model] = mostCommon.split('|')
      return `${brand} ${model}`
    }

    return null
  }, [devices.data, deviceModels.data])

  // Get the most common device_model_id for image lookup
  const mostCommonDeviceModelId = useMemo(() => {
    if (!devices.data || devices.data.length === 0) return null

    // Count occurrences of each device_model_id
    const modelIdCounts = new Map<number, number>()
    devices.data.forEach((device: types.Device) => {
      if (
        device.device_model_id !== null &&
        device.device_model_id !== undefined
      ) {
        modelIdCounts.set(
          device.device_model_id,
          (modelIdCounts.get(device.device_model_id) || 0) + 1,
        )
      }
    })

    if (modelIdCounts.size === 0) return null

    // Get the most common device_model_id
    let mostCommonId: number | null = null
    let maxCount = 0
    modelIdCounts.forEach((count, id) => {
      if (count > maxCount) {
        maxCount = count
        mostCommonId = id
      }
    })

    return mostCommonId
  }, [devices.data])

  const deviceModelImageUrl = useMemo(
    () => getDeviceModelImageUrl(mostCommonDeviceModelId),
    [mostCommonDeviceModelId],
  )
  const deviceModelImageFallbackUrl = useMemo(
    () => getDeviceModelImagePublicUrl(mostCommonDeviceModelId),
    [mostCommonDeviceModelId],
  )
  const deviceModelIconUrl = '/icon_pv_pcs.svg'

  const matchesAssetUrl = (currentUrl: string, expectedUrl: string) => {
    if (!expectedUrl) {
      return false
    }
    return currentUrl === expectedUrl || currentUrl.endsWith(expectedUrl)
  }

  const handleDeviceModelImageError = (
    event: SyntheticEvent<HTMLImageElement>,
  ) => {
    const target = event.currentTarget
    const shouldTryFallback =
      deviceModelImageFallbackUrl &&
      !matchesAssetUrl(target.src, deviceModelImageFallbackUrl) &&
      !matchesAssetUrl(target.src, deviceModelIconUrl)

    if (shouldTryFallback) {
      target.src = deviceModelImageFallbackUrl
      return
    }

    if (!matchesAssetUrl(target.src, deviceModelIconUrl)) {
      target.src = deviceModelIconUrl
    }
  }

  // Get inverters for the most common device_model_id
  const inverters = useGetInverters({
    queryParams: {
      device_model_ids: mostCommonDeviceModelId
        ? [mostCommonDeviceModelId]
        : [],
    },
    queryOptions: {
      enabled: mostCommonDeviceModelId !== null,
      staleTime: QUERY_TIME.NEVER, // Never refetch - header data should be static
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  })

  // Get the first inverter for technical information (if available)
  const inverter =
    inverters.data && inverters.data.length > 0 ? inverters.data[0] : null

  let startQuery: string | undefined = undefined
  let endQuery: string | undefined = undefined

  const project = useSelectProject(projectId!)

  if (project.data) {
    if (start) {
      startQuery = start.tz(project.data.time_zone, true).format('YYYY-MM-DD')
    }
    if (end) {
      endQuery = end.tz(project.data.time_zone, true).toISOString()
    }
  }

  const includeEnergy =
    (start && !start.isSame(dayjs().startOf('day'))) || false

  const { data: produced } = useGetKPISummaryCards({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { kpi_type_ids: [KPITypeEnum.PROJECT_ENERGY_PRODUCTION] },
    queryOptions: {
      enabled: includeEnergy,
    },
  })

  const data = useGetEquipmentAnalysisPCSv2({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { start: startQuery, end: endQuery },
    queryOptions: { enabled: !!projectId },
  })

  const dataLength = data.data?.total_power_output.value.length

  const startISO = start?.toISOString()

  useEffect(() => {
    queueMicrotask(() => setInitialSliderValueSet(false))
    queueMicrotask(() => setSliderValue(0))
  }, [startISO])

  useEffect(() => {
    if (data.isLoading || initialSliderValueSet) {
      return
    }
    if (!dataLength) {
      queueMicrotask(() => setSliderValue(0))
      return
    }

    // Check if we're looking at today's data
    const isToday = start && start.isSame(dayjs().startOf('day'))

    if (isToday) {
      // For today, show the most current available time
      queueMicrotask(() => setSliderValue(dataLength - 1))
    } else {
      // For previous days, show middle of the day
      queueMicrotask(() => setSliderValue(Math.floor(dataLength / 2)))
    }
    queueMicrotask(() => setInitialSliderValueSet(true))
  }, [dataLength, data.isLoading, initialSliderValueSet, start, startISO])

  useEffect(() => {
    if (dataLength === 1) {
      queueMicrotask(() => setSliderValue(0))
    }
    if (isPlaying && dataLength) {
      intervalRef.current = window.setInterval(() => {
        queueMicrotask(() =>
          setSliderValue((prevValue) => (prevValue + 1) % dataLength),
        )
      }, 5000 / dataLength)
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [isPlaying, dataLength])

  useResizePlotlyCharts({
    containerRef: tabPanelRef,
    enabled: activeTab === 'current-day',
  })

  useResizePlotlyCharts({
    containerRef: modalContentRef,
    enabled: imageModalOpened,
    dependency: modalActiveTab,
  })

  const togglePlay = () => {
    setIsPlaying((prev) => !prev)
  }

  // Calculate header values - MUST be before early return
  const deviceCount = devices.data?.length || 0

  // Calculate total MWac as the sum of all PCS devices on site
  // capacity_ac is in kWac, so we convert to MWac by dividing by 1000
  const totalMWac = useMemo(() => {
    if (!devices.data || devices.data.length === 0) {
      return null
    }
    // Sum all PCS device capacities (devices are already filtered to PV_INVERTER type)
    const totalKWac = devices.data.reduce((sum, device) => {
      return sum + (device.capacity_ac || 0)
    }, 0)
    return totalKWac / 1000 // Convert kWac to MWac
  }, [devices.data])

  // Calculate MWac per device (average)
  const mwacPerDevice = useMemo(() => {
    if (!totalMWac || deviceCount === 0) {
      return null
    }
    return totalMWac / deviceCount
  }, [totalMWac, deviceCount])

  // Early return - MUST be after all hooks
  if (project.isLoading) {
    return <PageLoader />
  }

  let hasPCSModules = false
  if (project.data?.spec.used_sensor_type_ids?.includes(3)) {
    hasPCSModules = true
  }

  const getTimeFromSliderValue = (value: number) => {
    const startOfDay = dayjs().tz(project.data?.time_zone).startOf('day')
    const currentTime = startOfDay.add(value * 5, 'minute')
    return currentTime.format('HH:mm')
  }
  const blockData = blockNormalize
    ? data.data?.block_power_distribution_norm
    : data.data?.block_power_distribution
  const pcsData = pcsNormalize
    ? data.data?.pcs_power_distribution_norm
    : data.data?.pcs_power_distribution
  const startLink = start?.subtract(3, 'day').format('YYYY-MM-DD')
  const endLink = dayjs(end).add(2, 'day').isBefore(dayjs())
    ? dayjs(end).add(2, 'day').format('YYYY-MM-DD')
    : dayjs().subtract(1, 'day').format('YYYY-MM-DD')

  return (
    <Stack p="md" h="100%">
      <PageTitle>PV Inverter Performance</PageTitle>

      {/* Common Header - Visible across all tabs */}
      <Stack gap="md">
        <Group justify="space-between" align="flex-start">
          <Group gap="md" align="flex-start">
            {/* Brand/Model Image - Load from CDN or public folder */}
            {mostCommonDeviceModelId !== null ? (
              <>
                <Box
                  w={100}
                  h={100}
                  style={{
                    flexShrink: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Image
                    src={deviceModelImageUrl}
                    alt={pcsBrandModel || 'Device Model'}
                    w="100%"
                    h="100%"
                    fit="contain"
                    radius="md"
                    style={{
                      objectFit: 'contain',
                      cursor: 'pointer',
                    }}
                    onClick={() => setImageModalOpened(true)}
                    onError={handleDeviceModelImageError}
                  />
                </Box>
                <Modal
                  opened={imageModalOpened}
                  onClose={() => setImageModalOpened(false)}
                  title={pcsBrandModel || 'Device Model'}
                  size="xl"
                  centered
                >
                  <div ref={modalContentRef}>
                    {inverters.isLoading ? (
                      <Skeleton height={400} />
                    ) : inverter ? (
                      <Tabs
                        value={modalActiveTab}
                        onChange={(value) =>
                          setModalActiveTab(value || 'overview')
                        }
                        defaultValue="overview"
                        variant="outline"
                      >
                        <Tabs.List>
                          <Tabs.Tab value="overview">Overview</Tabs.Tab>
                          <Tabs.Tab value="power-temp">
                            Power & Temperature
                          </Tabs.Tab>
                          <Tabs.Tab value="efficiency">Efficiency</Tabs.Tab>
                          <Tabs.Tab value="sandia">Sandia Parameters</Tabs.Tab>
                        </Tabs.List>

                        <Tabs.Panel value="overview" pt="md">
                          <Stack gap="md">
                            <Image
                              src={deviceModelImageUrl}
                              alt={pcsBrandModel || 'Device Model'}
                              style={{
                                filter:
                                  colorScheme === 'dark'
                                    ? 'invert(1) brightness(0.7)'
                                    : 'none',
                              }}
                              maw={280}
                              mah={280}
                              fit="contain"
                              radius="md"
                              mx="auto"
                              onError={handleDeviceModelImageError}
                            />
                            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                              <Text size="sm" c="dimmed">
                                Manufacturer:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.manufacturer}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                Model:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.model}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                Rated AC power:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.power_ac_nominal
                                    ? `${(inverter.power_ac_nominal / 1000000).toFixed(2)} MWac`
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                Rated DC power:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.power_dc_nominal
                                    ? `${(inverter.power_dc_nominal / 1000000).toFixed(2)} MWdc`
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                DC input voltage range:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.voltage_min && inverter.voltage_max
                                    ? `${inverter.voltage_min.toFixed(0)} - ${inverter.voltage_max.toFixed(0)} Vdc`
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                DC nominal voltage:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.voltage_dc_nominal
                                    ? `${inverter.voltage_dc_nominal.toFixed(0)} Vdc`
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                MPP voltage range:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.voltage_mpp_min &&
                                  inverter.voltage_mpp_max
                                    ? `${inverter.voltage_mpp_min.toFixed(0)} - ${inverter.voltage_mpp_max.toFixed(0)} Vdc`
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                Max DC current:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.current_max
                                    ? `${inverter.current_max.toFixed(1)} A`
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                Voltage start-up:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.voltage_start_up
                                    ? `${inverter.voltage_start_up.toFixed(0)} Vdc`
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                Power start-up:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.power_start_up
                                    ? `${(inverter.power_start_up / 1000).toFixed(1)} kW`
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                Night tare loss:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.night_tare
                                    ? `${(inverter.night_tare / 1000).toFixed(2)} kW`
                                    : 'N/A'}
                                </Text>
                              </Text>
                            </SimpleGrid>
                          </Stack>
                        </Tabs.Panel>

                        <Tabs.Panel value="power-temp" pt="md">
                          <Stack gap="md">
                            <Text size="sm" c="dimmed">
                              Power vs Temperature Characteristics
                            </Text>
                            {inverter.power_max_at_reference_temp &&
                            inverter.reference_temp &&
                            inverter.power_max_at_reference_temp.length > 0 &&
                            inverter.reference_temp.length > 0 ? (
                              <Box
                                w="100%"
                                maw="100%"
                                mx="auto"
                                style={{ overflow: 'hidden' }}
                              >
                                <PlotlyPlot
                                  data={[
                                    (() => {
                                      // Convert power values from W to MW and multiply by 1000
                                      const powerValues =
                                        inverter.power_max_at_reference_temp.map(
                                          (p) => (p / 1000000) * 1000,
                                        )
                                      const temperatures = [
                                        ...inverter.reference_temp,
                                      ]

                                      // Add a point at 0°C with the first power value
                                      if (
                                        temperatures.length > 0 &&
                                        powerValues.length > 0
                                      ) {
                                        temperatures.unshift(0)
                                        powerValues.unshift(powerValues[0])
                                      }

                                      return {
                                        x: temperatures,
                                        y: powerValues,
                                        type: 'scatter' as PlotType,
                                        mode: 'lines+markers' as const,
                                        name: 'Max Power',
                                        line: { color: '#228be6' },
                                        marker: { size: 8 },
                                      }
                                    })(),
                                  ]}
                                  layout={{
                                    title: {
                                      text: 'Maximum Power vs Temperature',
                                      font: { size: 12 },
                                    },
                                    xaxis: {
                                      title: { text: 'Temperature (°C)' },
                                      range: [0, undefined], // Start at 0°C
                                    },
                                    yaxis: {
                                      title: { text: 'Power (MW)' },
                                      range: [0, undefined], // Start at 0 MW
                                    },
                                    height: 300,
                                    margin: { l: 55, r: 40, t: 40, b: 45 },
                                    autosize: true,
                                  }}
                                  config={{
                                    displayModeBar: true,
                                    responsive: true,
                                  }}
                                />
                              </Box>
                            ) : (
                              <Text
                                size="sm"
                                c="dimmed"
                                style={{ fontStyle: 'italic' }}
                              >
                                No power vs temperature data available
                              </Text>
                            )}
                          </Stack>
                        </Tabs.Panel>

                        <Tabs.Panel value="efficiency" pt="md">
                          <Stack gap="md">
                            <Text size="sm" c="dimmed">
                              Efficiency Characteristics
                            </Text>
                            {(() => {
                              // Helper function to calculate efficiency from [DC, AC] pairs
                              const calculateEfficiency = (
                                efficiencyData: number[][],
                              ): { x: number[]; y: number[] } | null => {
                                if (
                                  !efficiencyData ||
                                  efficiencyData.length === 0 ||
                                  !efficiencyData[0] ||
                                  efficiencyData[0].length < 2
                                ) {
                                  return null
                                }

                                const x: number[] = []
                                const y: number[] = []

                                // Process each row which contains [DC, AC] pairs
                                for (const row of efficiencyData) {
                                  // Each row should have pairs: [DC1, AC1, DC2, AC2, ...]
                                  for (let i = 0; i < row.length; i += 2) {
                                    if (i + 1 < row.length) {
                                      const dc = row[i]
                                      const ac = row[i + 1]
                                      if (dc > 0) {
                                        // DC input on x-axis (converted to MW), efficiency % on y-axis
                                        x.push(dc / 1000000) // Convert W to MW
                                        y.push((ac / dc) * 100)
                                      }
                                    }
                                  }
                                }

                                return x.length > 0 ? { x, y } : null
                              }

                              const lowVoltageData = calculateEfficiency(
                                inverter.efficiency_at_low_voltage,
                              )
                              const midVoltageData = calculateEfficiency(
                                inverter.efficiency_at_mid_voltage,
                              )
                              const highVoltageData = calculateEfficiency(
                                inverter.efficiency_at_high_voltage,
                              )

                              // Get voltage labels from voltage_nominal_efficiency array
                              const voltageLabels =
                                inverter.voltage_nominal_efficiency || []
                              const lowVoltageLabel =
                                voltageLabels.length > 0
                                  ? `Low Voltage (${voltageLabels[0].toFixed(0)} V)`
                                  : 'Low Voltage'
                              const midVoltageLabel =
                                voltageLabels.length > 1
                                  ? `Medium Voltage (${voltageLabels[1].toFixed(0)} V)`
                                  : 'Medium Voltage'
                              const highVoltageLabel =
                                voltageLabels.length > 2
                                  ? `High Voltage (${voltageLabels[2].toFixed(0)} V)`
                                  : 'High Voltage'

                              if (
                                !lowVoltageData &&
                                !midVoltageData &&
                                !highVoltageData
                              ) {
                                return (
                                  <Text
                                    size="sm"
                                    c="dimmed"
                                    style={{ fontStyle: 'italic' }}
                                  >
                                    No efficiency data available
                                  </Text>
                                )
                              }

                              return (
                                <Box
                                  w="100%"
                                  maw="100%"
                                  mx="auto"
                                  style={{ overflow: 'hidden' }}
                                >
                                  <PlotlyPlot
                                    data={[
                                      ...(lowVoltageData
                                        ? [
                                            {
                                              x: lowVoltageData.x,
                                              y: lowVoltageData.y,
                                              type: 'scatter' as PlotType,
                                              mode: 'lines+markers' as const,
                                              name: lowVoltageLabel,
                                              line: { color: '#fa5252' },
                                              marker: { size: 6 },
                                            },
                                          ]
                                        : []),
                                      ...(midVoltageData
                                        ? [
                                            {
                                              x: midVoltageData.x,
                                              y: midVoltageData.y,
                                              type: 'scatter' as PlotType,
                                              mode: 'lines+markers' as const,
                                              name: midVoltageLabel,
                                              line: { color: '#51cf66' },
                                              marker: { size: 6 },
                                            },
                                          ]
                                        : []),
                                      ...(highVoltageData
                                        ? [
                                            {
                                              x: highVoltageData.x,
                                              y: highVoltageData.y,
                                              type: 'scatter' as PlotType,
                                              mode: 'lines+markers' as const,
                                              name: highVoltageLabel,
                                              line: { color: '#339af0' },
                                              marker: { size: 6 },
                                            },
                                          ]
                                        : []),
                                    ]}
                                    layout={{
                                      title: {
                                        text: 'Efficiency vs DC Input Power',
                                        font: { size: 12 },
                                      },
                                      xaxis: {
                                        title: { text: 'DC Input Power (MW)' },
                                      },
                                      yaxis: {
                                        title: { text: 'Efficiency (%)' },
                                        range: [0, 105], // Efficiency typically 0-100%
                                      },
                                      height: 300,
                                      margin: { l: 55, r: 40, t: 40, b: 45 },
                                      autosize: true,
                                    }}
                                    config={{
                                      displayModeBar: true,
                                      responsive: true,
                                    }}
                                  />
                                </Box>
                              )
                            })()}
                          </Stack>
                        </Tabs.Panel>

                        <Tabs.Panel value="sandia" pt="md">
                          <Stack gap="md">
                            <Text size="sm" c="dimmed">
                              Sandia Inverter Model Parameters
                            </Text>
                            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                              <Text size="sm" c="dimmed">
                                C0:{' '}
                                <Text
                                  component="span"
                                  fw={500}
                                  style={{ fontFamily: 'monospace' }}
                                >
                                  {inverter.c0 !== null &&
                                  inverter.c0 !== undefined
                                    ? inverter.c0.toExponential(4)
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                C1:{' '}
                                <Text
                                  component="span"
                                  fw={500}
                                  style={{ fontFamily: 'monospace' }}
                                >
                                  {inverter.c1 !== null &&
                                  inverter.c1 !== undefined
                                    ? inverter.c1.toExponential(4)
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                C2:{' '}
                                <Text
                                  component="span"
                                  fw={500}
                                  style={{ fontFamily: 'monospace' }}
                                >
                                  {inverter.c2 !== null &&
                                  inverter.c2 !== undefined
                                    ? inverter.c2.toExponential(4)
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                C3:{' '}
                                <Text
                                  component="span"
                                  fw={500}
                                  style={{ fontFamily: 'monospace' }}
                                >
                                  {inverter.c3 !== null &&
                                  inverter.c3 !== undefined
                                    ? inverter.c3.toExponential(4)
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                Power AC Nominal:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.power_ac_nominal
                                    ? `${(inverter.power_ac_nominal / 1000).toFixed(1)} kW`
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                Power DC Nominal:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.power_dc_nominal
                                    ? `${(inverter.power_dc_nominal / 1000).toFixed(1)} kW`
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                Voltage DC Nominal:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.voltage_dc_nominal
                                    ? `${inverter.voltage_dc_nominal.toFixed(1)} V`
                                    : 'N/A'}
                                </Text>
                              </Text>
                              <Text size="sm" c="dimmed">
                                Night Tare:{' '}
                                <Text component="span" fw={500}>
                                  {inverter.night_tare
                                    ? `${inverter.night_tare.toFixed(1)} W`
                                    : 'N/A'}
                                </Text>
                              </Text>
                            </SimpleGrid>
                          </Stack>
                        </Tabs.Panel>
                      </Tabs>
                    ) : (
                      <Stack gap="md">
                        <Image
                          src={deviceModelImageUrl}
                          alt={pcsBrandModel || 'Device Model'}
                          style={{
                            filter:
                              colorScheme === 'dark'
                                ? 'invert(1) brightness(0.7)'
                                : 'none',
                          }}
                          maw={280}
                          mah={280}
                          fit="contain"
                          radius="md"
                          mx="auto"
                          onError={handleDeviceModelImageError}
                        />
                        <Text
                          size="sm"
                          c="dimmed"
                          style={{ fontStyle: 'italic' }}
                          ta="center"
                        >
                          No technical information available
                        </Text>
                      </Stack>
                    )}
                  </div>
                </Modal>
              </>
            ) : deviceModels.isLoading ? (
              <Skeleton w={100} h={100} radius="md" />
            ) : (
              <Box
                w={100}
                h={100}
                style={{
                  flexShrink: 0,
                  padding: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Image
                  src="/icon_pv_pcs.svg"
                  alt="Device Type Icon"
                  w="100%"
                  h="100%"
                  fit="contain"
                  radius="md"
                  style={{
                    objectFit: 'contain',
                    filter:
                      colorScheme === 'dark'
                        ? 'invert(1) brightness(0.7)'
                        : 'none',
                  }}
                />
              </Box>
            )}
            <Stack gap="xs">
              <Group gap="md">
                <Text
                  fw={600}
                  size="lg"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setImageModalOpened(true)}
                >
                  {deviceModels.isLoading ? (
                    'Loading...'
                  ) : pcsBrandModel ? (
                    <>
                      {pcsBrandModel}
                      <Text
                        component="span"
                        c="dimmed"
                        fw={400}
                        ml="xs"
                        mr="xs"
                      >
                        (x {deviceCount})
                      </Text>
                      <ActionIcon
                        variant="transparent"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          setImageModalOpened(true)
                        }}
                        style={{
                          display: 'inline-flex',
                          verticalAlign: 'middle',
                          cursor: 'pointer',
                        }}
                      >
                        <IconInfoCircle size={18} />
                      </ActionIcon>
                    </>
                  ) : null}
                </Text>
              </Group>
              <Group gap="lg">
                <Text size="sm" c="dimmed">
                  MWac per device:{' '}
                  <Text component="span" fw={500}>
                    {mwacPerDevice !== null ? mwacPerDevice.toFixed(2) : 'N/A'}
                  </Text>
                </Text>
                <Text size="sm" c="dimmed">
                  Total MWac:{' '}
                  <Text component="span" fw={500}>
                    {totalMWac !== null ? totalMWac.toFixed(2) : 'N/A'}
                  </Text>
                  {project.data?.poi && (
                    <>
                      {' '}
                      <Text component="span" c="dimmed" size="xs">
                        (POI limit: {project.data.poi.toFixed(2)} MWac)
                      </Text>
                    </>
                  )}
                </Text>
              </Group>
            </Stack>
          </Group>

          <Group gap="xl" align="flex-start">
            {/* Left Section: Installed, Placed In Service, and EPC */}
            <Stack gap="xs" align="flex-start">
              <Text size="md" fw={500}>
                Installed:
              </Text>
              <Group gap="xs" align="center">
                <Text size="sm" c="dimmed">
                  Placed in Service:{' '}
                  {project.isLoading ? (
                    <Text component="span" fw={500}>
                      Loading...
                    </Text>
                  ) : project.data?.placed_in_service_date ? (
                    <Text component="span" fw={500}>
                      {dayjs(project.data.placed_in_service_date).format(
                        'MMM D, YYYY',
                      )}
                    </Text>
                  ) : isAdmin ? (
                    <Link
                      to={`/projects/${projectId}/settings?tab=project-info`}
                      style={{ textDecoration: 'none', color: 'inherit' }}
                    >
                      <Text
                        component="span"
                        fw={500}
                        style={{ cursor: 'pointer' }}
                      >
                        Set
                      </Text>
                    </Link>
                  ) : (
                    <Text component="span" fw={500}>
                      Not set
                    </Text>
                  )}
                </Text>
                {isAdmin && (
                  <ActionIcon
                    variant="transparent"
                    size="sm"
                    component={Link}
                    to={`/projects/${projectId}/settings?tab=project-info`}
                    style={{ cursor: 'pointer' }}
                  >
                    <IconEdit size={16} />
                  </ActionIcon>
                )}
              </Group>
              <Group gap="xs" align="center">
                <Text size="sm" c="dimmed">
                  EPC:{' '}
                  {omContractorScopes.isLoading ? (
                    <Text component="span" fw={500}>
                      Loading...
                    </Text>
                  ) : epcContractor ? (
                    <Text component="span" fw={500}>
                      {epcContractor.company_name_long ||
                        epcContractor.company_name_short ||
                        'Unknown'}
                    </Text>
                  ) : isAdmin ? (
                    <Link
                      to={`/projects/${projectId}/settings?tab=om-contractors`}
                      style={{ textDecoration: 'none', color: 'inherit' }}
                    >
                      <Text
                        component="span"
                        fw={500}
                        style={{ cursor: 'pointer' }}
                      >
                        Set
                      </Text>
                    </Link>
                  ) : (
                    <Text component="span" fw={500}>
                      Not set
                    </Text>
                  )}
                </Text>
                {isAdmin && (
                  <ActionIcon
                    variant="transparent"
                    size="sm"
                    component={Link}
                    to={`/projects/${projectId}/settings?tab=om-contractors`}
                    style={{ cursor: 'pointer' }}
                  >
                    <IconEdit size={16} />
                  </ActionIcon>
                )}
              </Group>
            </Stack>

            {/* Right Section: Service by, Name, and Contact */}
            <Stack gap="xs" align="flex-start">
              <Group gap="xs" align="center">
                <Text size="md" fw={500}>
                  Service by:
                </Text>
                {isAdmin && (
                  <ActionIcon
                    variant="transparent"
                    size="sm"
                    component={Link}
                    to={`/projects/${projectId}/settings?tab=om-contractors`}
                    style={{ cursor: 'pointer' }}
                  >
                    <IconEdit size={16} />
                  </ActionIcon>
                )}
              </Group>
              {omContractor?.contractor_addressee ? (
                <>
                  <Text size="sm" c="dimmed">
                    Name:{' '}
                    <Text component="span" fw={500}>
                      {omContractor.contractor_addressee}
                      {omContractor.company_name_long ||
                      omContractor.company_name_short
                        ? ` (${omContractor.company_name_long || omContractor.company_name_short})`
                        : ''}
                    </Text>
                  </Text>
                  {(omContractor?.contractor_phone ||
                    omContractor?.contractor_email) && (
                    <Group gap="xs" align="center">
                      <Text size="sm" c="dimmed">
                        Contact:
                      </Text>
                      {omContractor?.contractor_phone && (
                        <Group gap={4} align="center">
                          <IconPhone size={14} />
                          <Text size="sm" fw={500}>
                            {omContractor.contractor_phone}
                          </Text>
                        </Group>
                      )}
                      {omContractor?.contractor_email && (
                        <Group gap={4} align="center">
                          <IconMail size={14} />
                          <Text size="sm" fw={500}>
                            {omContractor.contractor_email}
                          </Text>
                        </Group>
                      )}
                    </Group>
                  )}
                </>
              ) : (
                <Group gap="xs" align="center">
                  <Text size="sm" c="dimmed" style={{ fontStyle: 'italic' }}>
                    O&M provider scope not set
                  </Text>
                  {isAdmin && (
                    <Link
                      to={`/projects/${projectId}/settings?tab=om-contractors`}
                      style={{ textDecoration: 'none', color: 'inherit' }}
                    >
                      <Text
                        component="span"
                        size="sm"
                        fw={500}
                        style={{ cursor: 'pointer' }}
                      >
                        Set
                      </Text>
                    </Link>
                  )}
                </Group>
              )}
            </Stack>
          </Group>
        </Group>
      </Stack>

      <Tabs
        value={activeTab}
        onChange={setTab}
        variant="outline"
        keepMounted={false}
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
          width: '100%',
        }}
      >
        <Tabs.List>
          <Tabs.Tab value="realtime">Real-time</Tabs.Tab>
          <Tabs.Tab value="current-day">Day View</Tabs.Tab>
          {isSuperadmin && <Tabs.Tab value="long-term">Long Term</Tabs.Tab>}
        </Tabs.List>

        <Tabs.Panel value="realtime" pt="md">
          <RealtimeTab />
        </Tabs.Panel>

        <Tabs.Panel value="current-day" pt="md" ref={tabPanelRef}>
          <Stack gap="md" style={{ flex: 1, minHeight: 0 }}>
            <Skeleton visible={data.isLoading}>
              <Group>
                <AdvancedDatePicker
                  maxDays={1}
                  includeTodayInDateRange
                  disableQuickActions
                  defaultRange="today"
                  includeClearButton={false}
                />
                {includeEnergy && produced?.[0]?.value ? (
                  <Link
                    to={`/projects/${projectId}/kpis/type/6?start=${startLink}&end=${endLink}`}
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
                    <Button rightSection={<IconExternalLink size={16} />}>
                      Daily Energy: {produced?.[0]?.value} MWh
                    </Button>
                  </Link>
                ) : null}
                {dataLength && dataLength > 1 && (
                  <>
                    <Slider
                      value={sliderValue}
                      label={getTimeFromSliderValue(sliderValue)}
                      onChange={setSliderValue}
                      min={0}
                      max={
                        data.data?.total_power_output.value.length
                          ? data.data.total_power_output.value.length - 1
                          : 0
                      }
                      step={1}
                      style={{ flex: 1 }}
                    />
                    <ActionIcon onClick={togglePlay}>
                      {isPlaying ? (
                        <IconPlayerPauseFilled size={16} />
                      ) : (
                        <IconPlayerPlayFilled size={16} />
                      )}
                    </ActionIcon>
                  </>
                )}
              </Group>
            </Skeleton>
            <Group w="100%" justify="space-evenly" align="flex-end">
              <RingProgressCard
                title="AC Capacity (MW)"
                subtitle="Out of nameplate capacity"
                value={
                  data.data?.total_power_output.value[
                    dataLength && dataLength > 1 ? sliderValue : 0
                  ] ?? null
                }
                total={data.data?.total_power_output.total_nameplate ?? null}
                isLoading={data.isLoading}
                color="grey"
              />
              <RingProgressCard
                title="Blocks"
                subtitle="Generating Power"
                value={
                  data.data?.generating_power_block.value[
                    dataLength && dataLength > 1 ? sliderValue : 0
                  ] ?? null
                }
                total={data.data?.generating_power_block.total ?? null}
                isLoading={data.isLoading}
                color={
                  data.data
                    ? colorFromPercent(
                        data.data.generating_power_block.value[
                          dataLength && dataLength > 1 ? sliderValue : 0
                        ],
                        data.data.generating_power_block.total,
                      )
                    : 'grey'
                }
              />
              <RingProgressCard
                title="PCSs"
                subtitle="Generating Power"
                value={
                  data.data?.generating_power_pcs.value[
                    dataLength && dataLength > 1 ? sliderValue : 0
                  ] ?? null
                }
                total={data.data?.generating_power_pcs.total ?? null}
                isLoading={data.isLoading}
                color={
                  data.data
                    ? colorFromPercent(
                        data.data.generating_power_pcs.value[
                          dataLength && dataLength > 1 ? sliderValue : 0
                        ],
                        data.data.generating_power_pcs.total,
                      )
                    : 'grey'
                }
              />
              {hasPCSModules && (
                <RingProgressCard
                  title="PCS Modules"
                  subtitle="Generating Power"
                  value={
                    data.data?.generating_power_pcs_module?.value[
                      dataLength && dataLength > 1 ? sliderValue : 0
                    ] ?? null
                  }
                  total={data.data?.generating_power_pcs_module?.total ?? null}
                  isLoading={data.isLoading}
                  color={
                    data.data
                      ? colorFromPercent(
                          data.data.generating_power_pcs_module?.value[
                            dataLength && dataLength > 1 ? sliderValue : 0
                          ] ?? 0,
                          data.data.generating_power_pcs_module?.total ?? 0,
                        )
                      : 'grey'
                  }
                />
              )}
            </Group>
            <CustomCard
              title="Block Output Distribution"
              style={{ height: '250px' }}
              info="This plot shows the power output of each block. Clicking the 'Normalize by DC Input' button will equalize the performance of each block against its installed DC capacity, which is useful since installed capacity often differs per block. Look for large differences in performance between equipment to narrow down possible issues."
              headerChildren={
                <Checkbox
                  label="Normalize by DC Input"
                  value={blockNormalize ? 'true' : 'false'}
                  onChange={(event) =>
                    setBlockNormalize(event.currentTarget.checked)
                  }
                />
              }
            >
              <PlotlyPlot
                data={
                  data.data && [
                    {
                      x: blockData?.x,
                      y: blockData?.y[
                        dataLength && dataLength > 1 ? sliderValue : 0
                      ],
                      customdata: blockData?.customdata,
                      type: 'bar',
                    },
                  ]
                }
                layout={
                  data.data && {
                    xaxis: { type: 'category', title: { text: 'Block' } },
                    yaxis: {
                      range: [
                        0,
                        blockData ? blockData.yaxis_range_max * 1.05 : 1.05,
                      ],
                      title: {
                        text: blockNormalize ? 'Power (%)' : 'Power (MW)',
                      },
                    },
                  }
                }
                isLoading={data.isLoading}
                error={data.error}
              />
            </CustomCard>
            <CustomCard
              title="PCS Output Distribution"
              style={{ height: '250px' }}
              info="This plot shows the power output of each PCS. Clicking the 'Normalize by DC Input' button will equalize the performance of each inverter against its installed DC capacity, which is useful since installed capacity is often different per equipment. Look for large differences in performance between equipment to narrow down possible issues."
              headerChildren={
                <Checkbox
                  label="Normalize by DC Input"
                  value={pcsNormalize ? 'true' : 'false'}
                  onChange={(event) =>
                    setPcsNormalize(event.currentTarget.checked)
                  }
                />
              }
            >
              <PlotlyPlot
                data={
                  data.data && [
                    {
                      x: pcsData?.x,
                      y: pcsData?.y[
                        dataLength && dataLength > 1 ? sliderValue : 0
                      ],
                      customdata: pcsData?.customdata,
                      type: 'bar',
                    },
                  ]
                }
                layout={
                  data.data && {
                    xaxis: { type: 'category', title: { text: 'PCS' } },
                    yaxis: {
                      range: [
                        0,
                        pcsData ? pcsData.yaxis_range_max * 1.05 : 1.05,
                      ],
                      title: {
                        text: pcsNormalize ? 'Power (%)' : 'Power (MW)',
                      },
                    },
                  }
                }
                isLoading={data.isLoading}
                error={data.error}
              />
            </CustomCard>
            {hasPCSModules && (
              <CustomCard
                title="PCS Module Output Distribution"
                style={{ height: '250px' }}
              >
                <PlotlyPlot
                  data={
                    data.data && [
                      {
                        x: data.data.pcs_module_power_distribution?.x,
                        y: data.data.pcs_module_power_distribution?.y[
                          dataLength && dataLength > 1 ? sliderValue : 0
                        ],
                        customdata:
                          data.data.pcs_module_power_distribution?.customdata,
                        type: 'bar',
                      },
                    ]
                  }
                  layout={
                    data.data && {
                      xaxis: {
                        type: 'category',
                        title: { text: 'PCS Module' },
                      },
                      yaxis: {
                        range: [
                          0,
                          (data.data.pcs_module_power_distribution
                            ?.yaxis_range_max ?? 1) * 1.05,
                        ],
                        title: { text: 'Power (MW)' },
                      },
                    }
                  }
                  isLoading={data.isLoading}
                  error={data.error}
                />
              </CustomCard>
            )}
            <CustomCard
              title={
                'PCS Power Heatmap' +
                (dataLength && dataLength > 1 ? '' : ' (Last 24 hours)')
              }
              style={{ height: '500px' }}
              info="This plot shows the power output of each PCS over time. Look for large differences in performance between equipment to narrow down possible issues."
            >
              <PCSHeatmap startQuery={startQuery} endQuery={endQuery} />
            </CustomCard>
          </Stack>
        </Tabs.Panel>

        {isSuperadmin && (
          <Tabs.Panel value="long-term" pt="md">
            <Text c="dimmed">
              This tab and page are still under development and are only visible
              to superadmins. The long-term PV Inverter performance view needs
              to be created.
            </Text>
          </Tabs.Panel>
        )}
      </Tabs>
    </Stack>
  )
}

export default PCSEquipmentAnalysis
