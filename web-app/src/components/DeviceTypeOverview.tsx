import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import { useGetKPIInstances } from '@/api/v1/operational/kpi_instances'
import { useGetEventsSummary } from '@/api/v1/operational/project/events'
import { useGetKPISummaryCards } from '@/api/v1/operational/project/kpi_data'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetDeviceTypePowerSummary } from '@/api/v1/protected/web-application/device-type-overview'
import {
  useGetDataTimeseriesLast,
  useGetRealTimeByDeviceTypeID,
} from '@/api/v1/protected/web-application/projects/real_time'
import RequiresUserType from '@/components/admin/RequiresUserType'
import { useGetDevicesV2, useGetPaginatedEvents, useGetTags } from '@/hooks/api'
import type { Device } from '@/hooks/types'
import {
  Badge,
  Box,
  Button,
  Card,
  Flex,
  Popover,
  Skeleton,
  Stack,
  Table,
  Text,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'

interface DeviceTypeOverviewProps {
  className?: string
  onDeviceTypeClick?: (deviceTypeId: number) => void
  selectedDeviceTypeId?: number | null
}

// Device type configuration with proper ordering and filtering
const DEVICE_TYPE_CONFIG: Record<
  number,
  {
    icon: string
    displayName: string
    order: number
    category: 'pv' | 'bess' | 'common'
    powerTooltip: string
    sensorTypes: Record<string, number[]>
  }
> = {
  // Common devices
  1: {
    icon: '/icon-substation.svg',
    displayName: 'Substation',
    order: 0,
    category: 'common',
    powerTooltip: 'Meter active power (substation meter)',
    sensorTypes: { substation: [1, 2, 10, 21, 22, 17, 18, 94] },
  },
  // PV devices
  23: {
    icon: '/icon_pv_circuit.svg',
    displayName: 'PV Circuit',
    order: 1,
    category: 'pv',
    powerTooltip: 'Total PV Circuit power (from meter or PCS data)',
    sensorTypes: {},
  },
  15: {
    icon: '/icon_pv_mvt.svg',
    displayName: 'PV MVT',
    order: 2,
    category: 'pv',
    powerTooltip: 'Total PV MVT AC Power output',
    sensorTypes: {},
  },
  2: {
    icon: '/icon_pv_pcs.svg',
    displayName: 'PV PCS',
    order: 3,
    category: 'pv',
    powerTooltip: 'Total PV PCS AC Power output',
    sensorTypes: { pcs: [2, 136, 144] },
  },
  9: {
    icon: '/icon_pv_dc_combiner.svg',
    displayName: 'PV DC Combiner',
    order: 4,
    category: 'pv',
    powerTooltip: 'Total PV DC Combiner power (voltage × current)',
    sensorTypes: { combiner: [27] },
  },
  29: {
    icon: '/icon_trackers.svg',
    displayName: 'PV Tracker',
    order: 5,
    category: 'pv',
    powerTooltip: 'Power reading for this device type',
    sensorTypes: {},
  },
  // BESS devices
  17: {
    icon: '/icon_bess_circuit.svg',
    displayName: 'BESS Circuit',
    order: 1,
    category: 'bess',
    powerTooltip: 'Total BESS Circuit power',
    sensorTypes: { bessCircuit: [41] },
  },
  25: {
    icon: '/icon_bess_mvt.svg',
    displayName: 'BESS MVT',
    order: 2,
    category: 'bess',
    powerTooltip: 'Total BESS MVT power',
    sensorTypes: {},
  },
  13: {
    icon: '/icon_bess_pcs.svg',
    displayName: 'BESS PCS',
    order: 3,
    category: 'bess',
    powerTooltip: 'Total BESS PCS power',
    sensorTypes: { bessPcs: [31, 106, 121, 68, 107] },
  },
  11: {
    icon: '/icon_bess_dc_enclosure.svg',
    displayName: 'BESS DC Enclosure',
    order: 4,
    category: 'bess',
    powerTooltip: 'Power reading for this device type',
    sensorTypes: {},
  },
  27: {
    icon: '/icon_bess_string.svg',
    displayName: 'BESS String',
    order: 5,
    category: 'bess',
    powerTooltip: 'Power reading for this device type',
    sensorTypes: {},
  },
  34: {
    icon: '/icon_bess_module.svg',
    displayName: 'BESS Module',
    order: 6,
    category: 'bess',
    powerTooltip: 'Power reading for this device type',
    sensorTypes: {},
  },
}

// Device types to exclude from display (Ghost, Project, etc.)
const EXCLUDED_DEVICE_TYPES: number[] = [
  0, // ghost
  31, // Exclude BESS Cell from data/UI
  // Note: We're using project (ID 1) as substation for now, so not excluding it
]

const DeviceTypeOverview = ({
  className,
  onDeviceTypeClick,
}: DeviceTypeOverviewProps) => {
  const { projectId } = useParams<{ projectId: string }>()
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()
  const cardRef = useRef<HTMLDivElement>(null)
  const [cardWidth, setCardWidth] = useState(1200) // Default fallback
  const [isBESSExpanded, setIsBESSExpanded] = useState(false)
  const [openedPopover, setOpenedPopover] = useState<number | null>(null)
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const closeTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Measure card width on mount and resize
  useEffect(() => {
    const updateCardWidth = () => {
      if (cardRef.current) {
        const width = cardRef.current.offsetWidth
        setCardWidth(width)
      }
    }

    updateCardWidth()
    window.addEventListener('resize', updateCardWidth)
    return () => window.removeEventListener('resize', updateCardWidth)
  }, [])

  const project = useSelectProject(projectId!)

  // Get device types used in this project
  const usedDeviceTypeIds = project.data?.spec?.used_device_type_ids || []
  const includedDeviceTypeIds = usedDeviceTypeIds.filter(
    (id: number) => !EXCLUDED_DEVICE_TYPES.includes(id),
  )

  // Get events summary for event counts
  const eventsSummary = useGetEventsSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: includedDeviceTypeIds,
      open: true, // Only get open events
    },
    queryOptions: {
      enabled: !!projectId && includedDeviceTypeIds.length > 0,
    },
  })

  // Get efficient power summary for all device types
  const powerSummary = useGetDeviceTypePowerSummary({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId && includedDeviceTypeIds.length > 0,
    },
  })

  const deviceTypes = useGetDeviceTypes({
    queryParams: {
      device_type_ids: includedDeviceTypeIds,
      // Some BESS device types (PCS, DC enclosure, string) may not be
      // marked include_by_default in the DB. Allow them by disabling the
      // default-only filter so they appear in the overview.
      only_included_by_default: false,
    },
    queryOptions: {
      enabled: includedDeviceTypeIds.length > 0,
    },
  })

  // Fetch all devices in project (once) to compute counts per device type
  const devicesQuery = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: includedDeviceTypeIds,
    },
    queryOptions: {
      enabled: !!projectId && includedDeviceTypeIds.length > 0,
      staleTime: Infinity,
    },
  })

  const deviceTypeCounts: Record<number, number> = (
    (devicesQuery.data as Device[] | undefined) || []
  ).reduce(
    (acc: Record<number, number>, device: Device) => {
      const dt = device.device_type_id
      acc[dt] = (acc[dt] || 0) + 1
      return acc
    },
    {} as Record<number, number>,
  )

  // Helper function to count events by device type
  const getEventCountByDeviceType = (deviceTypeId: number): number => {
    if (!eventsSummary.data) return 0
    const displayName = DEVICE_TYPE_CONFIG[deviceTypeId]?.displayName
    return deviceTypeId === 29
      ? eventsSummary.data.filter(
          (e) =>
            e.device_type_name === 'Tracker Row' ||
            e.device_type_name === 'Tracker Zone',
        ).length
      : eventsSummary.data.filter((e) => e.device_type_name === displayName)
          .length
  }

  // Helper function to get tooltip text for power readings
  const getPowerTooltipText = (deviceTypeId: number): string =>
    DEVICE_TYPE_CONFIG[deviceTypeId]?.powerTooltip ||
    'Power reading for this device type'

  // Helper function to get BESS power reading for collapsed view
  const getBESSPowerReading = (): number | null => {
    return bessDevices.find((dt) => getPowerReading(dt.device_type_id) !== null)
      ?.device_type_id
      ? getPowerReading(
          bessDevices.find((dt) => getPowerReading(dt.device_type_id) !== null)!
            .device_type_id,
        )
      : null
  }

  // Helper function to get power reading for device type
  const getPowerReading = (deviceTypeId: number): number | null => {
    if (deviceTypeId === 1) return null // Skip substation
    return powerSummary.data?.device_type_power?.[deviceTypeId] || null
  }

  // Filter and sort device types based on configuration
  const filteredAndSortedDeviceTypes =
    deviceTypes.data
      ?.filter((deviceType) => {
        // Only show device types that are:
        // 1. In our configuration
        // 2. Not in the excluded list
        // 3. Actually present in the project's used_device_type_ids
        return (
          DEVICE_TYPE_CONFIG[deviceType.device_type_id] &&
          !EXCLUDED_DEVICE_TYPES.includes(deviceType.device_type_id) &&
          usedDeviceTypeIds.includes(deviceType.device_type_id)
        )
      })
      ?.sort((a, b) => {
        const configA = DEVICE_TYPE_CONFIG[a.device_type_id]
        const configB = DEVICE_TYPE_CONFIG[b.device_type_id]

        if (!configA || !configB) return 0

        // First sort by category (common first, then by project type)
        if (configA.category !== configB.category) {
          if (configA.category === 'common') return -1
          if (configB.category === 'common') return 1
          return configA.category.localeCompare(configB.category)
        }

        // Then sort by order within category
        return configA.order - configB.order
      }) || []

  // Check if this is a PV + BESS project (has both PV and BESS device types)
  const hasPVDevices = filteredAndSortedDeviceTypes.some(
    (deviceType) =>
      DEVICE_TYPE_CONFIG[deviceType.device_type_id]?.category === 'pv',
  )
  const hasBESSDevices = filteredAndSortedDeviceTypes.some(
    (deviceType) =>
      DEVICE_TYPE_CONFIG[deviceType.device_type_id]?.category === 'bess',
  )
  const isPVBESSProject = hasPVDevices && hasBESSDevices

  // Separate devices by category for branching layout
  const commonDevices = filteredAndSortedDeviceTypes.filter(
    (deviceType) =>
      DEVICE_TYPE_CONFIG[deviceType.device_type_id]?.category === 'common',
  )
  const pvDevices = filteredAndSortedDeviceTypes.filter(
    (deviceType) =>
      DEVICE_TYPE_CONFIG[deviceType.device_type_id]?.category === 'pv',
  )
  const bessDevices = filteredAndSortedDeviceTypes.filter(
    (deviceType) =>
      DEVICE_TYPE_CONFIG[deviceType.device_type_id]?.category === 'bess',
  )

  // Helper functions for hover popup timeout management
  const clearHoverTimeout = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current)
      hoverTimeoutRef.current = null
    }
  }

  const clearCloseTimeout = () => {
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current)
      closeTimeoutRef.current = null
    }
  }

  const handleMouseEnter = (deviceTypeId: number) => {
    clearCloseTimeout()
    clearHoverTimeout()
    hoverTimeoutRef.current = setTimeout(() => {
      setOpenedPopover(deviceTypeId)
    }, 300) // 300ms delay before showing popup
  }

  const handleMouseLeave = () => {
    clearHoverTimeout()
    clearCloseTimeout()
    closeTimeoutRef.current = setTimeout(() => {
      setOpenedPopover(null)
    }, 200) // 200ms delay before hiding popup
  }

  const handlePopoverMouseEnter = () => {
    clearCloseTimeout()
  }

  const handlePopoverMouseLeave = () => {
    clearCloseTimeout()
    closeTimeoutRef.current = setTimeout(() => {
      setOpenedPopover(null)
    }, 200) // 200ms delay before hiding popup
  }

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      clearHoverTimeout()
      clearCloseTimeout()
    }
  }, [])

  // Popover content component (uses hooks safely)
  const PopoverContent = ({
    deviceTypeId,
    displayName,
    icon,
    eventCount,
    deviceCount,
  }: {
    deviceTypeId: number
    displayName: string
    icon?: string
    eventCount: number
    deviceCount: number | null
  }) => {
    const colorSchemeInner = useComputedColorScheme()

    // Fetch latest PCS data for current operation section
    const pcsData = useGetDataTimeseriesLast({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        device_type_ids: deviceTypeId === 2 ? [2] : [], // Only fetch for PCS (device type 2)
        sensor_type_ids:
          DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.pcs || [],
      },
      queryOptions: {
        enabled: !!projectId && deviceTypeId === 2,
        staleTime: 30 * 1000, // Cache for 30 seconds
      },
    })

    // Fetch latest BESS PCS data for current operation section using real-time endpoint
    const bessPcsRealtime = useGetRealTimeByDeviceTypeID({
      pathParams: {
        projectId: projectId || '-1',
        deviceTypeId: 13, // BESS PCS device type
      },
      queryParams: {
        sensor_type_ids:
          DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.bessPcs || [],
      },
      queryOptions: {
        enabled: !!projectId && deviceTypeId === 13,
        staleTime: 30 * 1000, // Cache for 30 seconds
      },
    })

    // Fetch latest Combiner data for current operation section
    const combinerData = useGetDataTimeseriesLast({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        device_type_ids: deviceTypeId === 9 ? [9] : [], // Only fetch for Combiners (device type 9)
        sensor_type_ids:
          DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.combiner || [],
      },
      queryOptions: {
        enabled: !!projectId && deviceTypeId === 9,
        staleTime: 30 * 1000, // Cache for 30 seconds
      },
    })

    // Fetch latest BESS Circuit data for current operation section
    const bessCircuitData = useGetDataTimeseriesLast({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        device_type_ids: deviceTypeId === 17 ? [17] : [], // Only fetch for BESS Circuit (device type 17)
        sensor_type_ids:
          DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.bessCircuit || [],
      },
      queryOptions: {
        enabled: !!projectId && deviceTypeId === 17,
        staleTime: 30 * 1000, // Cache for 30 seconds
      },
    })

    // Fetch tags to map tag_id to sensor_type_id
    const pcsTags = useGetTags({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        device_type_ids: deviceTypeId === 2 ? [2] : [],
        sensor_type_ids:
          DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.pcs || [],
      },
      queryOptions: {
        enabled: !!projectId && deviceTypeId === 2,
        staleTime: 5 * 60 * 1000, // Cache for 5 minutes
      },
    })

    // Fetch tags for combiner data
    const combinerTags = useGetTags({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        device_type_ids: deviceTypeId === 9 ? [9] : [],
        sensor_type_ids:
          DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.combiner || [],
      },
      queryOptions: {
        enabled: !!projectId && deviceTypeId === 9,
        staleTime: 5 * 60 * 1000, // Cache for 5 minutes
      },
    })

    // Fetch tags for BESS Circuit data
    const bessCircuitTags = useGetTags({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        device_type_ids: deviceTypeId === 17 ? [17] : [],
        sensor_type_ids:
          DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.bessCircuit || [],
      },
      queryOptions: {
        enabled: !!projectId && deviceTypeId === 17,
        staleTime: 5 * 60 * 1000, // Cache for 5 minutes
      },
    })

    // Fetch tags for substation data
    const substationTags = useGetTags({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        device_type_ids: deviceTypeId === 1 ? [1, 5] : [],
        sensor_type_ids:
          DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.substation || [],
      },
      queryOptions: {
        enabled: !!projectId && deviceTypeId === 1,
        staleTime: 5 * 60 * 1000, // Cache for 5 minutes
      },
    })

    // Preferred: fetch latest Substation data by exact tag_ids once tags are known
    const substationSensorTypeIds =
      DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.substation || []

    const substationTagIds: number[] =
      deviceTypeId === 1 && Array.isArray(substationTags.data)
        ? substationTags.data
            .filter((t: any) =>
              substationSensorTypeIds.includes(Number(t.sensor_type_id)),
            )
            .map((t: any) => Number(t.tag_id))
        : []

    const substationData = useGetDataTimeseriesLast({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        tag_ids: substationTagIds,
      },
      queryOptions: {
        enabled:
          !!projectId && deviceTypeId === 1 && substationTagIds.length > 0,
        staleTime: 30 * 1000, // Cache for 30 seconds
      },
    })

    // Generic calculation function for sensor data
    const calculateSensorValues = (
      data: any[],
      tags: any[],
      sensorTypeIds: number[],
      conversions: Record<number, number> = {},
    ) => {
      if (!data?.length || !tags?.length) return {}

      const tagToSensorType: Record<number, number> = {}
      tags.forEach((tag: any) => {
        if (tag.tag_id && tag.sensor_type_id) {
          tagToSensorType[tag.tag_id] = tag.sensor_type_id
        }
      })

      const dataBySensorType: Record<number, number[]> = {}
      sensorTypeIds.forEach((id) => (dataBySensorType[id] = []))

      data.forEach((item) => {
        const value = item.value_real || item.value_double || item.value_integer
        if (value !== null && value !== undefined) {
          const sensorTypeId = tagToSensorType[item.tag_id]
          if (sensorTypeId && dataBySensorType[sensorTypeId]) {
            dataBySensorType[sensorTypeId].push(Number(value))
          }
        }
      })

      const result: Record<string, any> = {}
      sensorTypeIds.forEach((id) => {
        const values = dataBySensorType[id] || []
        if (values.length > 0) {
          const conversion = conversions[id] || 1
          result[`sensor_${id}`] = {
            avg:
              values.reduce((sum, val) => sum + val, 0) /
              values.length /
              conversion,
            min: Math.min(...values) / conversion,
            max: Math.max(...values) / conversion,
          }
        }
      })
      return result
    }

    // Calculate PCS operation values
    const calculatePCSValues = () => {
      const sensorTypeIds =
        DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.pcs || []
      const conversions = { 2: 1000, 136: 1000, 144: 1 } // kW->MW, kVAR->MVAR, V->V
      const values = calculateSensorValues(
        pcsData.data || [],
        pcsTags.data || [],
        sensorTypeIds,
        conversions,
      )
      return {
        activePower: values.sensor_2 || null,
        reactivePower: values.sensor_136 || null,
        dcVoltage: values.sensor_144 || null,
      }
    }

    const pcsValues = calculatePCSValues()

    // Calculate BESS PCS operation values from real-time data
    const calculateBESSPCSValues = () => {
      if (!bessPcsRealtime.data?.traces?.length)
        return { activePower: null, reactivePower: null }

      const sensorTypeIds =
        DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.bessPcs || []
      const dataBySensorType: Record<number, number[]> = {}
      sensorTypeIds.forEach((id) => (dataBySensorType[id] = []))

      bessPcsRealtime.data.traces.forEach((trace) => {
        // Use sensor_type_id directly from the trace
        const sensorTypeId = trace.sensor_type_id

        if (sensorTypeId && dataBySensorType[sensorTypeId]) {
          const values = (trace.values || []).filter(
            (v): v is number => typeof v === 'number' && v !== null && v !== 0,
          )

          dataBySensorType[sensorTypeId].push(...values)
        }
      })

      const activePowerValues = dataBySensorType[31]?.length
        ? dataBySensorType[31]
        : dataBySensorType[106]?.length
          ? dataBySensorType[106]
          : dataBySensorType[121] || []
      const reactivePowerValues = dataBySensorType[68]?.length
        ? dataBySensorType[68]
        : dataBySensorType[107] || []

      const calculateStats = (values: number[]) => {
        // Filter out nulls, undefined, and zeros
        const validValues = values.filter(
          (val) => val !== null && val !== undefined && val !== 0,
        )
        return validValues.length > 0
          ? {
              avg:
                validValues.reduce((sum, val) => sum + val, 0) /
                validValues.length,
              min: Math.min(...validValues),
              max: Math.max(...validValues),
            }
          : null
      }

      return {
        activePower: calculateStats(activePowerValues),
        reactivePower: calculateStats(reactivePowerValues),
      }
    }

    const bessPcsValues = calculateBESSPCSValues()

    // Calculate Combiner operation values
    const calculateCombinerValues = () => {
      const sensorTypeIds =
        DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.combiner || []
      const values = calculateSensorValues(
        combinerData.data || [],
        combinerTags.data || [],
        sensorTypeIds,
      )
      return { current: values.sensor_27 || null }
    }

    const combinerValues = calculateCombinerValues()

    // Calculate BESS Circuit operation values
    const calculateBESSCircuitValues = () => {
      const sensorTypeIds =
        DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.bessCircuit || []
      const conversions = { 41: 1000 } // kW->MW
      const values = calculateSensorValues(
        bessCircuitData.data || [],
        bessCircuitTags.data || [],
        sensorTypeIds,
        conversions,
      )
      return { activePower: values.sensor_41 || null }
    }

    const bessCircuitValues = calculateBESSCircuitValues()

    // Realtime meter data (device_type_id 5) for substation power KPIs
    const meterRealtime = useGetRealTimeByDeviceTypeID({
      pathParams: {
        projectId: projectId || '-1',
        deviceTypeId: 5, // Meter device type
      },
      queryParams: {
        // Meter active power may be 1 or 2; apparent power is 10
        sensor_type_ids: [1, 2, 10],
      },
      queryOptions: {
        enabled: !!projectId && deviceTypeId === 1,
        staleTime: 30 * 1000,
      },
    })

    // Calculate Substation operation values
    const calculateSubstationValues = () => {
      const tagToSensorType: Record<number, number> = {}
      ;(substationTags.data || []).forEach((tag: any) => {
        if (tag.tag_id && tag.sensor_type_id) {
          tagToSensorType[tag.tag_id] = tag.sensor_type_id
        }
      })

      const sensorTypeIds =
        DEVICE_TYPE_CONFIG[deviceTypeId]?.sensorTypes.substation || []
      const dataBySensorType: Record<number, number[]> = {}
      sensorTypeIds.forEach((id) => (dataBySensorType[id] = []))
      ;(substationData.data || []).forEach((item) => {
        const value = item.value_real || item.value_double || item.value_integer
        if (value !== null && value !== undefined) {
          const sensorTypeId = tagToSensorType[item.tag_id]
          if (sensorTypeId && dataBySensorType[sensorTypeId]) {
            dataBySensorType[sensorTypeId].push(Number(value))
          }
        }
      })

      const calculateSensorValues = (sensorTypeId: number) => {
        const values = dataBySensorType[sensorTypeId] || []
        return values.length > 0
          ? {
              avg: values.reduce((sum, val) => sum + val, 0) / values.length,
              min: Math.min(...values),
              max: Math.max(...values),
            }
          : null
      }

      const parseSensorFromName = (name: string | undefined): number | null => {
        const n = String(name || '')
        return n.startsWith('Sensor ')
          ? Number(n.replace('Sensor ', '')) || null
          : null
      }

      const rtTraces = meterRealtime.data?.traces || []
      const rtActiveValues = rtTraces
        .filter((t) => {
          const id = parseSensorFromName(t.name)
          return id === 1 || id === 2
        })
        .flatMap((t) =>
          (t.values || []).filter((v): v is number => typeof v === 'number'),
        )

      const rtApparentValues = rtTraces
        .filter((t) => parseSensorFromName(t.name) === 10)
        .flatMap((t) =>
          (t.values || []).filter((v): v is number => typeof v === 'number'),
        )

      const summarize = (vals: number[]) =>
        vals.length > 0
          ? {
              avg: vals.reduce((s, v) => s + v, 0) / vals.length,
              min: Math.min(...vals),
              max: Math.max(...vals),
            }
          : null

      return {
        meterActivePower: summarize(rtActiveValues),
        apparentPower: summarize(rtApparentValues),
        ppcActiveSetpoint: calculateSensorValues(21),
        ppcReactiveSetpoint: calculateSensorValues(22),
        ppcActivePower: calculateSensorValues(17),
        ppcReactivePower: calculateSensorValues(18),
        ppcVoltage: calculateSensorValues(94),
      }
    }

    const substationValues = calculateSubstationValues()

    const recentEvents = useGetPaginatedEvents({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        page: 0,
        page_size: 5,
        open: true,
        sort_column: 'loss_daily',
        sort_direction: 'desc',
        device_type_ids: [deviceTypeId],
      },
      queryOptions: {
        enabled: !!projectId && !!deviceTypeId,
        staleTime: 60 * 1000,
      },
    })

    const kpiInstances = useGetKPIInstances({
      queryParams: {
        project_ids: projectId ? [projectId] : [],
        deep: true,
      },
      queryOptions: {
        enabled: !!projectId,
        staleTime: 5 * 60 * 1000,
      },
    })

    const deviceTypeKpiTypeIds = (kpiInstances.data || [])
      .filter((ki) => ki.kpi_type?.device_type_id === deviceTypeId)
      .map((ki) => ki.kpi_type_id)

    const kpiCards = useGetKPISummaryCards({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        kpi_type_ids: deviceTypeKpiTypeIds,
      },
      queryOptions: {
        enabled: !!projectId && deviceTypeKpiTypeIds.length > 0,
      },
    })

    return (
      <Stack gap="md" style={{ width: 400 }}>
        {/* Device icon and title */}
        <Flex align="center" gap="md">
          <Box
            style={{
              width: 40,
              height: 40,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
            }}
          >
            <img
              src={icon}
              alt={displayName}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain',
                filter:
                  colorSchemeInner === 'dark'
                    ? 'invert(1) brightness(0.7)'
                    : 'none',
              }}
            />
            {eventCount > 0 && (
              <Badge
                size="xs"
                color="red"
                style={{
                  position: 'absolute',
                  top: -4,
                  right: -4,
                  minWidth: 16,
                  height: 16,
                  borderRadius: '50%',
                  fontSize: '10px',
                  fontWeight: 600,
                }}
              >
                {eventCount}
              </Badge>
            )}
          </Box>
          <Text size="lg" fw={700}>
            {displayName} (
            {deviceCount !== null ? deviceCount.toLocaleString() : '0'}x)
          </Text>
        </Flex>

        {/* General Information - Only visible to Super Admins */}
        <RequiresUserType requiredUserType="superadmin" silent>
          <Box>
            <Flex align="center" gap="xs" mb="xs">
              <Text size="sm" fw={600}>
                General Information
              </Text>
              <Text size="xs" c="dimmed" style={{ fontStyle: 'italic' }}>
                (Super Admin only)
              </Text>
            </Flex>
            <Stack gap="xs">
              <Flex justify="space-between">
                <Text size="sm" c="dimmed">
                  Brand:
                </Text>
                <Text
                  size="sm"
                  c="blue"
                  style={{ textDecoration: 'underline' }}
                >
                  SunGrow
                </Text>
              </Flex>
              <Flex justify="space-between">
                <Text size="sm" c="dimmed">
                  Model:
                </Text>
                <Text size="sm">SG-3600</Text>
              </Flex>
              <Flex justify="space-between">
                <Text size="sm" c="dimmed">
                  Nominal Rating:
                </Text>
                <Text size="sm">3.6 MVA</Text>
              </Flex>
            </Stack>
          </Box>
        </RequiresUserType>

        {/* Current Operation - Only show for PCS devices */}
        {deviceTypeId === 2 && (
          <Box>
            <Flex align="center" justify="space-between" mb="xs">
              <Text size="sm" fw={600}>
                Current Operation
              </Text>
              <Button size="xs" variant="subtle">
                <IconChevronDown size={12} />
              </Button>
            </Flex>
            <Stack gap="xs">
              {pcsData.isLoading ? (
                <Text size="xs" c="dimmed">
                  Loading operation data...
                </Text>
              ) : (
                <>
                  <Flex justify="space-between">
                    <Text size="sm" c="dimmed">
                      Active Power:
                    </Text>
                    <Text size="sm">
                      {pcsValues.activePower !== null
                        ? `${pcsValues.activePower.avg.toFixed(3)} MW (avg), [${pcsValues.activePower.min.toFixed(3)} MW - ${pcsValues.activePower.max.toFixed(3)} MW]`
                        : 'N/A'}
                    </Text>
                  </Flex>
                  <Flex justify="space-between">
                    <Text size="sm" c="dimmed">
                      Reactive Power:
                    </Text>
                    <Text size="sm">
                      {pcsValues.reactivePower !== null
                        ? `${pcsValues.reactivePower.avg.toFixed(3)} MVAr (avg), [${pcsValues.reactivePower.min.toFixed(3)} MVAr - ${pcsValues.reactivePower.max.toFixed(3)} MVAr]`
                        : 'N/A'}
                    </Text>
                  </Flex>
                  <Flex justify="space-between">
                    <Text size="sm" c="dimmed">
                      DC Voltage:
                    </Text>
                    <Text size="sm">
                      {pcsValues.dcVoltage !== null
                        ? `${pcsValues.dcVoltage.avg.toFixed(1)} V DC (avg), [${pcsValues.dcVoltage.min.toFixed(1)} V - ${pcsValues.dcVoltage.max.toFixed(1)} V]`
                        : 'N/A'}
                    </Text>
                  </Flex>
                </>
              )}
            </Stack>
          </Box>
        )}

        {/* Current Operation - Only show for BESS PCS devices */}
        {deviceTypeId === 13 && (
          <Box>
            <Flex align="center" justify="space-between" mb="xs">
              <Text size="sm" fw={600}>
                Current Operation
              </Text>
              <Button size="xs" variant="subtle">
                <IconChevronDown size={12} />
              </Button>
            </Flex>
            <Stack gap="xs">
              {bessPcsRealtime.isLoading ? (
                <Text size="xs" c="dimmed">
                  Loading operation data...
                </Text>
              ) : (
                <>
                  <Flex justify="space-between">
                    <Text size="sm" c="dimmed">
                      Active Power:
                    </Text>
                    <Text size="sm">
                      {bessPcsValues.activePower !== null
                        ? `${bessPcsValues.activePower.avg.toFixed(3)} MW (avg), [${bessPcsValues.activePower.min.toFixed(3)} MW - ${bessPcsValues.activePower.max.toFixed(3)} MW]`
                        : 'N/A'}
                    </Text>
                  </Flex>
                  <Flex justify="space-between">
                    <Text size="sm" c="dimmed">
                      Reactive Power:
                    </Text>
                    <Text size="sm">
                      {bessPcsValues.reactivePower !== null
                        ? `${bessPcsValues.reactivePower.avg.toFixed(3)} MVAr (avg), [${bessPcsValues.reactivePower.min.toFixed(3)} MVAr - ${bessPcsValues.reactivePower.max.toFixed(3)} MVAr]`
                        : 'N/A'}
                    </Text>
                  </Flex>
                </>
              )}
            </Stack>
          </Box>
        )}

        {/* Current Operation - Only show for Combiner devices */}
        {deviceTypeId === 9 && (
          <Box>
            <Flex align="center" justify="space-between" mb="xs">
              <Text size="sm" fw={600}>
                Current Operation
              </Text>
              <Button size="xs" variant="subtle">
                <IconChevronDown size={12} />
              </Button>
            </Flex>
            <Stack gap="xs">
              {combinerData.isLoading ? (
                <Text size="xs" c="dimmed">
                  Loading operation data...
                </Text>
              ) : (
                <>
                  <Flex justify="space-between">
                    <Text size="sm" c="dimmed">
                      Current:
                    </Text>
                    <Text size="sm">
                      {combinerValues.current !== null
                        ? `${combinerValues.current.avg.toFixed(1)} A (avg), [${combinerValues.current.min.toFixed(1)} A - ${combinerValues.current.max.toFixed(1)} A]`
                        : 'N/A'}
                    </Text>
                  </Flex>
                </>
              )}
            </Stack>
          </Box>
        )}

        {/* Current Operation - Only show for BESS Circuit devices */}
        {deviceTypeId === 17 && (
          <Box>
            <Flex align="center" justify="space-between" mb="xs">
              <Text size="sm" fw={600}>
                Current Operation
              </Text>
              <Button size="xs" variant="subtle">
                <IconChevronDown size={12} />
              </Button>
            </Flex>
            <Stack gap="xs">
              {bessCircuitData.isLoading ? (
                <Text size="xs" c="dimmed">
                  Loading operation data...
                </Text>
              ) : (
                <>
                  <Flex justify="space-between">
                    <Text size="sm" c="dimmed">
                      Active Power:
                    </Text>
                    <Text size="sm">
                      {bessCircuitValues.activePower !== null
                        ? `${bessCircuitValues.activePower.avg.toFixed(3)} MW (avg), [${bessCircuitValues.activePower.min.toFixed(3)} MW - ${bessCircuitValues.activePower.max.toFixed(3)} MW]`
                        : 'N/A'}
                    </Text>
                  </Flex>
                </>
              )}
            </Stack>
          </Box>
        )}

        {/* Current Operation - Only show for Substation devices */}
        {deviceTypeId === 1 && (
          <Box>
            <Flex align="center" justify="space-between" mb="xs">
              <Text size="sm" fw={600}>
                Current Operation
              </Text>
              <Button size="xs" variant="subtle">
                <IconChevronDown size={12} />
              </Button>
            </Flex>
            <Stack gap="xs">
              {substationData.isLoading ? (
                <Text size="xs" c="dimmed">
                  Loading operation data...
                </Text>
              ) : (
                <>
                  {[
                    {
                      key: 'meterActivePower',
                      label: 'Meter Active Power',
                      unit: 'MW',
                    },
                    {
                      key: 'apparentPower',
                      label: 'Apparent Power',
                      unit: 'MVA',
                    },
                    {
                      key: 'ppcActiveSetpoint',
                      label: 'PPC Active Setpoint',
                      unit: 'MW',
                    },
                    {
                      key: 'ppcReactiveSetpoint',
                      label: 'PPC Reactive Setpoint',
                      unit: 'MVAR',
                    },
                    {
                      key: 'ppcActivePower',
                      label: 'PPC Active Power',
                      unit: 'MW',
                    },
                    {
                      key: 'ppcReactivePower',
                      label: 'PPC Reactive Power',
                      unit: 'MVAR',
                    },
                    { key: 'ppcVoltage', label: 'PPC Voltage', unit: 'V' },
                  ].map(({ key, label, unit }) => (
                    <Flex key={key} justify="space-between">
                      <Text size="sm" c="dimmed">
                        {label}:
                      </Text>
                      <Text size="sm">
                        {substationValues[
                          key as keyof typeof substationValues
                        ] !== null
                          ? `${(substationValues[key as keyof typeof substationValues] as any)?.avg?.toFixed(1)} ${unit}`
                          : 'N/A'}
                      </Text>
                    </Flex>
                  ))}
                </>
              )}
            </Stack>
          </Box>
        )}

        {/* KPIs */}
        <Box>
          <Text size="sm" fw={600} mb="xs">
            KPIs
          </Text>
          <Stack gap="xs">
            {kpiCards.isLoading && (
              <Text size="xs" c="dimmed">
                Loading KPIs...
              </Text>
            )}
            {!kpiCards.isLoading &&
              (kpiCards.data || [])
                .filter((k) =>
                  kpiInstances.data?.some(
                    (ki) => ki.kpi_type_id === k.kpi_type_id,
                  ),
                )
                .sort((a, b) => {
                  const favA = a.is_visible ? 1 : 0
                  const favB = b.is_visible ? 1 : 0
                  if (favA !== favB) return favB - favA
                  return a.title.localeCompare(b.title)
                })
                .map((k) => (
                  <Flex key={k.kpi_type_id} justify="space-between">
                    <Link
                      to={`/projects/${projectId}/kpis/type/${k.kpi_type_id}`}
                      style={{ textDecoration: 'none' }}
                    >
                      <Text
                        size="sm"
                        c="blue"
                        style={{ textDecoration: 'underline' }}
                      >
                        {k.title}
                      </Text>
                    </Link>
                    <Text size="sm">
                      {k.value ?? k.ytd_value ?? 'N/A'}
                      {k.unit ? ` ${k.unit}` : ''}
                    </Text>
                  </Flex>
                ))}
            {!kpiCards.isLoading && (kpiCards.data?.length ?? 0) === 0 && (
              <Text size="xs" c="dimmed">
                No KPIs
              </Text>
            )}
          </Stack>
        </Box>

        {/* Events */}
        {eventCount > 0 && (
          <Box>
            <Text size="sm" fw={600} mb="xs">
              Events ({eventCount} Total –{' '}
              <Link
                to={`/projects/${projectId}/events`}
                style={{ textDecoration: 'none' }}
              >
                <Text
                  component="span"
                  c="blue"
                  style={{ textDecoration: 'underline' }}
                >
                  see all
                </Text>
              </Link>
              )
            </Text>
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Device</Table.Th>
                  <Table.Th>Loss – Daily</Table.Th>
                  <Table.Th>Start</Table.Th>
                  <Table.Th>Cause</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {recentEvents.isLoading && (
                  <Table.Tr>
                    <Table.Td colSpan={4}>
                      <Text size="xs" c="dimmed">
                        Loading...
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                )}
                {!recentEvents.isLoading &&
                  recentEvents.data &&
                  recentEvents.data.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={4}>
                        <Text size="xs" c="dimmed">
                          No open events
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                {recentEvents.data?.map((evt) => (
                  <Table.Tr key={evt.event_id}>
                    <Table.Td>
                      <Link
                        to={`/projects/${projectId}/events/event/?eventId=${evt.event_id}`}
                        style={{ textDecoration: 'underline' }}
                      >
                        <Text size="xs" c="blue">
                          {evt.device_name_full}
                        </Text>
                      </Link>
                    </Table.Td>
                    <Table.Td>
                      {evt.loss_daily_financial === null ||
                      evt.loss_daily_financial === 0
                        ? '-'
                        : `$${evt.loss_daily_financial.toFixed(2)}`}
                    </Table.Td>
                    <Table.Td>{dayjs(evt.time_start).fromNow()}</Table.Td>
                    <Table.Td>{evt.root_cause || 'Unknown'}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Box>
        )}
      </Stack>
    )
  }

  // Helper function to render a group of devices horizontally
  const renderDeviceGroup = (devices: typeof filteredAndSortedDeviceTypes) => {
    return devices.map((deviceType, index) => {
      const totalItems = devices.length
      const isLastItem = index === totalItems - 1
      const isTracker = deviceType.device_type_id === 29
      const isNextItemTracker =
        index < totalItems - 1 && devices[index + 1]?.device_type_id === 29

      // Calculate connector width dynamically
      const estimatedCardWidth = 110
      const estimatedGap = 0
      const cardPadding = 0
      const availableSpace = cardWidth - cardPadding
      const usedSpace =
        totalItems * estimatedCardWidth + (totalItems - 1) * estimatedGap
      const remainingSpace = Math.max(0, availableSpace - usedSpace)
      const connectorWidth = (() => {
        const base = Math.max(40, remainingSpace / Math.max(1, totalItems - 1))
        return isLastItem || isTracker || isNextItemTracker ? 0 : base
      })()
      const connectorOffset =
        isLastItem || isTracker || isNextItemTracker ? 0 : -connectorWidth

      const config = DEVICE_TYPE_CONFIG[deviceType.device_type_id]
      const iconPath = config?.icon
      const displayName = config?.displayName || deviceType.name_long
      const powerReading = getPowerReading(deviceType.device_type_id)

      return (
        <Box key={deviceType.device_type_id} style={{ position: 'relative' }}>
          {/* Arrow connector (except for the last item and tracker) */}
          {!isLastItem && !isTracker && !isNextItemTracker && (
            <Box
              style={{
                position: 'absolute',
                right: connectorOffset,
                top: '50%',
                transform: 'translateY(-50%)',
                width: connectorWidth,
                height: 2,
                backgroundColor: theme.colors.gray[4],
                zIndex: 1,
              }}
            />
          )}

          <Stack align="center" gap={4} style={{ minWidth: 120 }}>
            {/* Power reading to the left of icon */}
            {powerReading !== null && deviceType.device_type_id !== 1 && (
              <Box
                style={{
                  position: 'absolute',
                  left: -60,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  zIndex: 2,
                }}
              >
                <Tooltip
                  label={getPowerTooltipText(deviceType.device_type_id)}
                  position="top"
                  withArrow
                  multiline
                  w={200}
                >
                  <Text
                    size="xs"
                    fw={600}
                    c={theme.colors.gray[7]}
                    style={{
                      backgroundColor: theme.colors.gray[0],
                      padding: '2px 6px',
                      borderRadius: '4px',
                      border: `1px solid ${theme.colors.gray[3]}`,
                      whiteSpace: 'nowrap',
                      cursor: 'help',
                    }}
                  >
                    {powerReading.toFixed(1)} MW
                  </Text>
                </Tooltip>
              </Box>
            )}

            {iconPath && (
              <Popover
                opened={openedPopover === deviceType.device_type_id}
                onChange={() => setOpenedPopover(null)}
                position="bottom"
                withArrow
                shadow="md"
                radius="md"
                withinPortal
              >
                <Popover.Target>
                  <Box
                    style={{
                      width: 80,
                      height: 80,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      position: 'relative',
                      cursor: 'pointer',
                      transition: 'transform 0.2s ease-in-out',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'scale(1.1)'
                      handleMouseEnter(deviceType.device_type_id)
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'scale(1)'
                      handleMouseLeave()
                    }}
                    onClick={() => {
                      onDeviceTypeClick?.(deviceType.device_type_id)
                    }}
                  >
                    <img
                      src={iconPath}
                      alt={displayName}
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'contain',
                        filter:
                          colorScheme === 'dark'
                            ? 'invert(1) brightness(0.7)'
                            : 'none',
                      }}
                    />
                    {/* Event count badge */}
                    {(() => {
                      const eventCount = getEventCountByDeviceType(
                        deviceType.device_type_id,
                      )
                      return eventCount > 0 ? (
                        <Badge
                          size="sm"
                          color="red"
                          style={{
                            position: 'absolute',
                            top: -8,
                            right: -8,
                            minWidth: 20,
                            height: 20,
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '12px',
                            fontWeight: 600,
                            zIndex: 2,
                          }}
                        >
                          {eventCount}
                        </Badge>
                      ) : null
                    })()}
                  </Box>
                </Popover.Target>
                <Popover.Dropdown>
                  <div
                    onMouseEnter={handlePopoverMouseEnter}
                    onMouseLeave={handlePopoverMouseLeave}
                  >
                    <PopoverContent
                      deviceTypeId={deviceType.device_type_id}
                      displayName={displayName}
                      icon={iconPath}
                      eventCount={getEventCountByDeviceType(
                        deviceType.device_type_id,
                      )}
                      deviceCount={
                        deviceTypeCounts[deviceType.device_type_id] ?? null
                      }
                    />
                  </div>
                </Popover.Dropdown>
              </Popover>
            )}

            <Text size="sm" fw={600} ta="center">
              {displayName}
            </Text>
          </Stack>
        </Box>
      )
    })
  }

  if (
    project.isLoading ||
    deviceTypes.isLoading ||
    eventsSummary.isLoading ||
    powerSummary.isLoading
  ) {
    return (
      <Card className={className} p="md" withBorder>
        <Skeleton height={120} radius="sm" />
      </Card>
    )
  }

  if (!project.data || filteredAndSortedDeviceTypes.length === 0) {
    return (
      <Box className={className}>
        <Text c="dimmed">No device types found for this project.</Text>
      </Box>
    )
  }

  return (
    <Card ref={cardRef} className={className} p="md" withBorder>
      {isPVBESSProject ? (
        // Collapsible layout for PV + BESS projects
        <Box>
          {/* Top row: Substation + PV Circuit and devices */}
          <Flex
            direction="row"
            align="center"
            justify="space-between"
            wrap="wrap"
            gap="sm"
            style={{ minHeight: 100, position: 'relative' }}
          >
            {renderDeviceGroup([...commonDevices, ...pvDevices])}
          </Flex>

          {/* BESS branching connector and controls */}
          <Box style={{ position: 'relative', marginTop: 0 }}>
            {/* Vertical connector line from PV Circuit to BESS */}
            <Box
              style={{
                position: 'absolute',
                left: 120 + 8 + 30, // Move further left (half of previous position)
                top: -40, // Move further up to better connect with horizontal connector
                width: 2,
                height: 50, // Shorter line
                backgroundColor: theme.colors.gray[4],
                zIndex: 1,
              }}
            />

            {/* BESS power reading and button at the vertical line */}
            <Flex
              align="center"
              gap="sm"
              style={{
                position: 'absolute',
                left: 120 + 8 + 30, // Same position as vertical line
                top: 0, // Move down a bit from device text
                transform: 'translateY(-50%)',
                zIndex: 2,
              }}
            >
              {/* BESS power reading */}
              {(() => {
                const bessPower = getBESSPowerReading()
                return bessPower !== null ? (
                  <Tooltip
                    label="Total BESS power"
                    position="top"
                    withArrow
                    multiline
                    w={200}
                  >
                    <Text
                      size="xs"
                      fw={600}
                      c={theme.colors.gray[7]}
                      style={{
                        backgroundColor: theme.colors.gray[0],
                        padding: '2px 6px',
                        borderRadius: '4px',
                        border: `1px solid ${theme.colors.gray[3]}`,
                        whiteSpace: 'nowrap',
                        cursor: 'help',
                      }}
                    >
                      {bessPower.toFixed(1)} MW
                    </Text>
                  </Tooltip>
                ) : null
              })()}

              {/* BESS chevron button */}
              <Button
                variant="subtle"
                size="xs"
                leftSection={
                  isBESSExpanded ? (
                    <IconChevronDown size={12} />
                  ) : (
                    <IconChevronRight size={12} />
                  )
                }
                onClick={() => setIsBESSExpanded(!isBESSExpanded)}
                style={{
                  padding: '4px 8px',
                  height: 'auto',
                  minHeight: 'auto',
                }}
              >
                BESS
              </Button>
            </Flex>
          </Box>

          {/* Collapsible BESS devices row */}
          {isBESSExpanded && (
            <Flex
              direction="row"
              align="center"
              justify="flex-start"
              wrap="wrap"
              gap="sm"
              style={{ minHeight: 100, marginTop: 20 }}
            >
              {/* Spacer to align BESS Circuit under PV Circuit (substation width + gap) */}
              <Box style={{ width: 120 + 8, height: 100 }} />
              {renderDeviceGroup(bessDevices)}
            </Flex>
          )}
        </Box>
      ) : (
        // Standard horizontal layout for single-type projects
        <Flex
          direction="row"
          align="center"
          justify="space-between"
          wrap="wrap"
          gap="sm"
          style={{ minHeight: 100 }}
        >
          {renderDeviceGroup(filteredAndSortedDeviceTypes)}
        </Flex>
      )}
    </Card>
  )
}

export default DeviceTypeOverview
