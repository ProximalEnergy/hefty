import { useSuggestRootCauses } from '@/api/v1/ai/root-cause'
import { DroneAnomaly } from '@/api/v1/operational/drone_integrations'
import { useBulkCreateEvents } from '@/api/v1/operational/project/events'
import { useSelectProject } from '@/api/v1/operational/projects'
import { PageError } from '@/components/Error'
import { MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
import { useGetDevicesV2, useGetRootCauses } from '@/hooks/api'
import * as gisUtils from '@/utils/GIS'
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Divider,
  Grid,
  Group,
  Menu,
  Modal,
  MultiSelect,
  Select,
  Stack,
  Tabs,
  Text,
  Tooltip,
  rem,
  useComputedColorScheme,
} from '@mantine/core'
import { DateTimePicker } from '@mantine/dates'
import { notifications } from '@mantine/notifications'
import {
  IconChevronDown,
  IconFilter,
  IconInfoCircle,
  IconLock,
  IconLockOpen,
  IconRobot,
} from '@tabler/icons-react'
import { Feature } from 'geojson'
import {
  type MRT_ColumnDef,
  MantineReactTable,
  useMantineReactTable,
} from 'mantine-react-table'
import { LngLatBoundsLike } from 'mapbox-gl'
import {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import {
  Layer,
  MapMouseEvent,
  Map as MapboxMap,
  Source,
} from 'react-map-gl/mapbox'
import { Link, useParams } from 'react-router'

interface DroneInspectionsMapProps {
  anomalies: DroneAnomaly[]
  inspectionTime?: string
}

interface HoverInfo {
  feature: Feature | null
  x: number
  y: number
}

// --- Zoom Level Definitions ---
const VERY_HIGH_ZOOM = 16
const HIGH_ZOOM = 14.6
const LOW_ZOOM = 9

// --- Helper Functions for Device Type Calculation ---
const calculateDeviceTypeIds = (zoom: number): number[] => {
  if (zoom >= VERY_HIGH_ZOOM) {
    return [29] // Tracker only
  } else if (zoom >= HIGH_ZOOM) {
    return [9] // DC Combiner only
  } else {
    return [2] // PCS only
  }
}

const calculatePowerDeviceTypeId = (zoom: number): number => {
  if (zoom >= VERY_HIGH_ZOOM) {
    return 29 // Tracker
  } else if (zoom >= HIGH_ZOOM) {
    return 9 // Combiner
  } else {
    return 2 // PCS
  }
}

// --- Mapping for Locked View Name ---
const viewNameMapping: { [key: number]: string } = {
  2: 'PCS',
  9: 'DC Combiner',
  29: 'Tracker',
}

// --- Layer Lock Configuration ---
const layerLockConfig = {
  PCS: {
    powerTypeId: 2,
    deviceTypeIds: [2], // PCS only
    zoom: LOW_ZOOM,
  },
  'DC Combiner': {
    powerTypeId: 9,
    deviceTypeIds: [9], // DC Combiner only
    zoom: HIGH_ZOOM,
  },
  Tracker: {
    powerTypeId: 29,
    deviceTypeIds: [29], // Tracker only
    zoom: VERY_HIGH_ZOOM,
  },
} as const

const DroneInspectionsMap = ({
  anomalies,
  inspectionTime,
}: DroneInspectionsMapProps) => {
  const { projectId } = useParams<{ projectId: string }>()
  const computedColorScheme = useComputedColorScheme('dark')
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })

  // Filter states
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [selectedRemediationCategories, setSelectedRemediationCategories] =
    useState<string[]>([])
  const [selectedSubsystems, setSelectedSubsystems] = useState<string[]>([])
  const [selectedIrSignals, setSelectedIrSignals] = useState<string[]>([])
  const [selectedRgbSignals, setSelectedRgbSignals] = useState<string[]>([])
  const [showAllRemediationCategories, setShowAllRemediationCategories] =
    useState(true)
  const [showAllSubsystems, setShowAllSubsystems] = useState(true)
  const [showAllIrSignals, setShowAllIrSignals] = useState(true)
  const [showAllRgbSignals, setShowAllRgbSignals] = useState(true)

  // Auto-hide timer for filter menu
  const filterMenuTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Auto-hide functions for filter menu
  const startFilterMenuHideTimer = useCallback(() => {
    if (filterMenuTimeoutRef.current) {
      clearTimeout(filterMenuTimeoutRef.current)
    }
    filterMenuTimeoutRef.current = setTimeout(() => {
      setShowFilterMenu(false)
    }, 2000) // 2 seconds delay
  }, [])

  const cancelFilterMenuHideTimer = useCallback(() => {
    if (filterMenuTimeoutRef.current) {
      clearTimeout(filterMenuTimeoutRef.current)
      filterMenuTimeoutRef.current = null
    }
  }, [])

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (filterMenuTimeoutRef.current) {
        clearTimeout(filterMenuTimeoutRef.current)
      }
    }
  }, [])

  // GIS context for settings
  const context = useContext(GISContext)
  if (!context) {
    throw new Error('GISContext is not provided')
  }
  const { showLabels, showSatellite } = context

  const blankMapStyle = gisUtils.useBlankMapStyle()
  const initialFitDoneRef = useRef(false)

  // --- Add Zoom State ---
  const [zoom, setZoom] = useState(LOW_ZOOM) // Initial zoom

  // --- Lock State ---
  const [isViewLocked, setIsViewLocked] = useState(false)
  const [lockedDeviceTypeIds, setLockedDeviceTypeIds] = useState<
    number[] | null
  >(null)

  const [lockedViewName, setLockedViewName] = useState<string | null>(null)

  // Image modal state
  const [imageModalOpen, setImageModalOpen] = useState(false)
  const [imageModalData, setImageModalData] = useState<{
    irUrl: string | null
    rgbUrl: string | null
    anomaly: DroneAnomaly | null
  }>({ irUrl: null, rgbUrl: null, anomaly: null })

  // --- Add Events Modal State ---
  const [addEventsOpen, setAddEventsOpen] = useState(false)
  const [openDate, setOpenDate] = useState<Date | null>(null)
  const [closeDate, setCloseDate] = useState<Date | null>(null)
  const bulkCreate = useBulkCreateEvents()

  // --- View State ---
  const [viewState, setViewState] = useState({
    longitude: 0,
    latitude: 0,
    zoom: 10,
    pitch: 0,
    bearing: 0,
  })

  // Fetch project data
  const project = useSelectProject(projectId!)

  // Calculate project bounds
  const projectBounds = useMemo(() => {
    if (project.data?.polygon) {
      try {
        let coordinates: number[][]
        const coords = project.data.polygon.coordinates

        // Handle different polygon types (Polygon vs MultiPolygon)
        // If it's deeply nested (4 levels), it's MultiPolygon format
        if (
          Array.isArray(coords[0]) &&
          Array.isArray(coords[0][0]) &&
          Array.isArray(coords[0][0][0])
        ) {
          // MultiPolygon: coordinates[0] is first polygon, [0] is outer ring
          coordinates = (coords as unknown as number[][][][])[0][0]
        }
        // If it's 3 levels deep, it's regular Polygon format
        else if (Array.isArray(coords[0]) && Array.isArray(coords[0][0])) {
          // Polygon: coordinates[0] is outer ring
          coordinates = (coords as unknown as number[][][])[0]
        } else {
          console.warn(
            'Unsupported project polygon coordinate structure:',
            coords,
          )
          return null
        }

        // Validate coordinates structure
        if (!Array.isArray(coordinates) || !Array.isArray(coordinates[0])) {
          console.warn(
            'Invalid project polygon coordinates structure:',
            coordinates,
          )
          return null
        }

        const lngs = coordinates.map((coord: number[]) => coord[0])
        const lats = coordinates.map((coord: number[]) => coord[1])

        // Validate that we have valid coordinates
        const validLngs = lngs.filter((lng) => !isNaN(lng) && isFinite(lng))
        const validLats = lats.filter((lat) => !isNaN(lat) && isFinite(lat))

        if (validLngs.length === 0 || validLats.length === 0) {
          console.warn('No valid coordinates found for project bounds')
          return null
        }

        return {
          west: Math.min(...validLngs),
          south: Math.min(...validLats),
          east: Math.max(...validLngs),
          north: Math.max(...validLats),
        }
      } catch (error) {
        console.warn(
          'Error calculating project bounds:',
          error,
          project.data.polygon,
        )
        return null
      }
    }
    return null
  }, [project.data?.polygon])

  // --- Determine Device Types to Fetch Based on Zoom ---
  const dynamicDeviceTypeIds = useMemo(
    () => calculateDeviceTypeIds(zoom),
    [zoom],
  )

  const deviceTypeIdsToFetch = isViewLocked
    ? (lockedDeviceTypeIds ?? dynamicDeviceTypeIds)
    : dynamicDeviceTypeIds

  // Fetch device data - just geometries, no power data
  const deviceData = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: deviceTypeIdsToFetch,
    },
    queryOptions: {
      enabled: !!projectId && (zoom >= LOW_ZOOM || isViewLocked),
      staleTime: Infinity, // Device geometries don't change
      gcTime: Infinity, // Keep in cache forever (renamed from cacheTime)
    },
  })

  // Device type name mapping
  const deviceTypeNames = useMemo(() => {
    return {
      2: 'PCS',
      9: 'DC Combiner',
      29: 'Tracker Row',
      4: 'Met Station',
    } as Record<number, string>
  }, [])

  // Get unique values for filter options
  const uniqueRemediationCategories = useMemo(() => {
    if (!anomalies) return []
    return [
      ...new Set(anomalies.map((a) => a.remediation_category).filter(Boolean)),
    ].filter((item): item is string => item !== undefined)
  }, [anomalies])

  const uniqueSubsystems = useMemo(() => {
    if (!anomalies) return []
    return [
      ...new Set(anomalies.map((a) => a.subsystem).filter(Boolean)),
    ].filter((item): item is string => item !== undefined)
  }, [anomalies])

  const uniqueIrSignals = useMemo(() => {
    if (!anomalies) return []
    return [
      ...new Set(anomalies.map((a) => a.ir_signal).filter(Boolean)),
    ].filter((item): item is string => item !== undefined)
  }, [anomalies])

  const uniqueRgbSignals = useMemo(() => {
    if (!anomalies) return []
    return [
      ...new Set(anomalies.map((a) => a.rgb_signal).filter(Boolean)),
    ].filter((item): item is string => item !== undefined)
  }, [anomalies])

  // Filter anomalies based on selected filters
  const filteredAnomalies = useMemo(() => {
    if (!anomalies) return []

    return anomalies.filter((anomaly) => {
      // Filter by remediation category
      if (
        !showAllRemediationCategories &&
        selectedRemediationCategories.length > 0
      ) {
        if (
          !selectedRemediationCategories.includes(
            anomaly.remediation_category || '',
          )
        ) {
          return false
        }
      }

      // Filter by subsystem
      if (!showAllSubsystems && selectedSubsystems.length > 0) {
        if (!selectedSubsystems.includes(anomaly.subsystem || '')) {
          return false
        }
      }

      // Filter by IR signal
      if (!showAllIrSignals && selectedIrSignals.length > 0) {
        if (!selectedIrSignals.includes(anomaly.ir_signal || '')) {
          return false
        }
      }

      // Filter by RGB signal
      if (!showAllRgbSignals && selectedRgbSignals.length > 0) {
        if (!selectedRgbSignals.includes(anomaly.rgb_signal || '')) {
          return false
        }
      }

      return true
    })
  }, [
    anomalies,
    showAllRemediationCategories,
    selectedRemediationCategories,
    showAllSubsystems,
    selectedSubsystems,
    showAllIrSignals,
    selectedIrSignals,
    showAllRgbSignals,
    selectedRgbSignals,
  ])

  // Convert filtered anomalies to GeoJSON points
  const anomalyGeoJSON = useMemo(() => {
    if (!filteredAnomalies?.length) return null

    const features = filteredAnomalies
      .filter((anomaly) => anomaly.location_lat && anomaly.location_lon)
      .map((anomaly) => ({
        type: 'Feature' as const,
        geometry: {
          type: 'Point' as const,
          coordinates: [anomaly.location_lon!, anomaly.location_lat!],
        },
        properties: {
          anomaly_uuid: anomaly.anomaly_uuid,
          subsystem: anomaly.subsystem,
          ir_signal: anomaly.ir_signal,
          rgb_signal: anomaly.rgb_signal,
          power_loss_kw: anomaly.power_loss_kw,
          remediation_category: anomaly.remediation_category,
          event_id: anomaly.event_id,
        },
      }))

    return {
      type: 'FeatureCollection' as const,
      features,
    }
  }, [filteredAnomalies])

  // Helper function to calculate distance between two points
  const calculateDistance = (
    lat1: number,
    lon1: number,
    lat2: number,
    lon2: number,
  ): number => {
    const R = 6371e3 // Earth's radius in meters
    const φ1 = (lat1 * Math.PI) / 180
    const φ2 = (lat2 * Math.PI) / 180
    const Δφ = ((lat2 - lat1) * Math.PI) / 180
    const Δλ = ((lon2 - lon1) * Math.PI) / 180

    const a =
      Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
      Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2)
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))

    return R * c // Distance in meters
  }

  // Helper function to check if a point is inside a polygon
  const pointInPolygon = (
    point: [number, number],
    polygon: number[][],
  ): boolean => {
    const [x, y] = point
    let inside = false

    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const [xi, yi] = polygon[i]
      const [xj, yj] = polygon[j]

      if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
        inside = !inside
      }
    }

    return inside
  }

  // Pre-calculate which device each anomaly belongs to (one-to-one mapping)
  const anomalyToDeviceMapping = useMemo(() => {
    if (!filteredAnomalies || !deviceData.data) return new Map<string, string>()

    const mapping = new Map<string, string>()

    // Pre-process all devices with polygons and calculate bounding boxes
    const devicesWithBounds = deviceData.data
      .filter((device) => device.polygon && device.device_type_id !== 29) // Skip tracker rows
      .map((device) => {
        let coordinates: number[][]

        try {
          // Parse polygon JSON string if it's a string, otherwise use as-is
          let polygonData = device.polygon!
          if (typeof device.polygon === 'string') {
            try {
              polygonData = JSON.parse(device.polygon)
            } catch (parseError) {
              console.warn(
                'Failed to parse polygon JSON:',
                parseError,
                device.polygon,
              )
              return null
            }
          }

          // Check the actual structure at runtime instead of relying on type
          const coords = polygonData.coordinates

          // If it's deeply nested (4 levels), it's MultiPolygon format
          if (
            Array.isArray(coords[0]) &&
            Array.isArray(coords[0][0]) &&
            Array.isArray(coords[0][0][0])
          ) {
            // MultiPolygon: coordinates[0] is first polygon, [0] is outer ring
            coordinates = (coords as unknown as number[][][][])[0][0]
          }
          // If it's 3 levels deep, it's regular Polygon format
          else if (Array.isArray(coords[0]) && Array.isArray(coords[0][0])) {
            // Polygon: coordinates[0] is outer ring
            coordinates = (coords as unknown as number[][][])[0]
          } else {
            console.warn('Unsupported coordinate structure:', coords)
            return null
          }

          // Validate final coordinates structure
          if (!Array.isArray(coordinates) || !Array.isArray(coordinates[0])) {
            console.warn('Invalid final coordinates structure:', coordinates)
            return null
          }

          // Calculate bounding box and centroid
          let minLon = Infinity,
            maxLon = -Infinity
          let minLat = Infinity,
            maxLat = -Infinity
          let sumLon = 0,
            sumLat = 0

          coordinates.forEach((coord) => {
            const lon = coord[0]
            const lat = coord[1]
            minLon = Math.min(minLon, lon)
            maxLon = Math.max(maxLon, lon)
            minLat = Math.min(minLat, lat)
            maxLat = Math.max(maxLat, lat)
            sumLon += lon
            sumLat += lat
          })

          const centroidLon = sumLon / coordinates.length
          const centroidLat = sumLat / coordinates.length

          return {
            device,
            coordinates,
            bounds: { minLon, maxLon, minLat, maxLat },
            centroid: { lon: centroidLon, lat: centroidLat },
          }
        } catch (error) {
          console.warn(
            'Error processing device polygon:',
            error,
            device.polygon,
          )
          return null
        }
      })
      .filter((item): item is NonNullable<typeof item> => item !== null)

    filteredAnomalies.forEach((anomaly) => {
      if (
        !anomaly.location_lat ||
        !anomaly.location_lon ||
        !anomaly.anomaly_uuid
      )
        return

      const anomalyLon = anomaly.location_lon
      const anomalyLat = anomaly.location_lat

      // Spatial pre-filtering: only check devices whose bounding box is within ~300m
      // (roughly 0.003 degrees at mid-latitudes)
      const buffer = 0.003
      const candidateDevices = devicesWithBounds.filter(
        ({ bounds }) =>
          anomalyLon >= bounds.minLon - buffer &&
          anomalyLon <= bounds.maxLon + buffer &&
          anomalyLat >= bounds.minLat - buffer &&
          anomalyLat <= bounds.maxLat + buffer,
      )

      let closestDevice: any = null
      let closestDistance = Infinity
      let isInsideAnyPolygon = false

      // Now only check the pre-filtered candidates
      for (const { device, coordinates, centroid } of candidateDevices) {
        // First check if anomaly is inside this polygon
        const isInside = pointInPolygon([anomalyLon, anomalyLat], coordinates)

        if (isInside) {
          closestDevice = device
          isInsideAnyPolygon = true
          break // Found inside, no need to check other devices
        }

        // If not inside any polygon yet, calculate distance to centroid
        if (!isInsideAnyPolygon) {
          const distance = calculateDistance(
            centroid.lat,
            centroid.lon,
            anomalyLat,
            anomalyLon,
          )

          if (distance < closestDistance && distance < 100) {
            // Within 100 meters
            closestDistance = distance
            closestDevice = device
          }
        }
      }

      // Map anomaly to the closest device (if any)
      if (closestDevice) {
        mapping.set(anomaly.anomaly_uuid, closestDevice.device_id.toString())
      }
    })

    return mapping
  }, [filteredAnomalies, deviceData.data])

  // Create device lookup map for reverse mapping
  const deviceLookup = useMemo(() => {
    if (!deviceData.data) return new Map<string, any>()

    const lookup = new Map<string, any>()
    deviceData.data.forEach((device) => {
      lookup.set(device.device_id.toString(), device)
    })
    return lookup
  }, [deviceData.data])

  // Function to get the device that an anomaly is mapped to
  const getAnomalyDevice = useCallback(
    (anomalyUuid: string) => {
      const deviceId = anomalyToDeviceMapping.get(anomalyUuid)
      if (!deviceId) return null
      return deviceLookup.get(deviceId) || null
    },
    [anomalyToDeviceMapping, deviceLookup],
  )

  // Deferred aggregation state (computed on-demand when opening modal)
  const [combinerAggregation, setCombinerAggregation] = useState(
    new Map<
      string, // Key format: "dc_field_id|signal_pair_key"
      {
        dcFieldId: number
        dcFieldName: string
        combinerName: string
        signalPairKey: string
        signalPairIr: string
        signalPairRgb: string
        lossKw: number
        anomalyCount: number
        anomalyUuids: string[]
      }
    >(),
  )
  // --- Summary metrics ---
  const totalFiltered = filteredAnomalies?.length ?? 0
  const totalAnomalies = anomalies?.length ?? 0
  const totalLossKw = useMemo(
    () =>
      Array.from(combinerAggregation.values()).reduce(
        (sum, v) => sum + (v.lossKw || 0),
        0,
      ),
    [combinerAggregation],
  )
  const totalWithExistingEvents = useMemo(
    () => filteredAnomalies?.filter((a) => a.event_id != null).length ?? 0,
    [filteredAnomalies],
  )
  const totalAvailableForEvents = totalFiltered - totalWithExistingEvents

  // --- Root Causes for DC Combiner (9), Tracker (29), and DC Field (30) ---
  const rootCausesQuery = useGetRootCauses({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { device_type_ids: [9, 29, 30] },
    queryOptions: { enabled: !!projectId },
  })
  const allowedRootCauses = rootCausesQuery.data || []

  // Build unique IR and RGB signal groups from filteredAnomalies
  const signalPairs = useMemo(() => {
    const s = new Map<string, { ir: string; rgb: string; count: number }>()
    filteredAnomalies.forEach((a) => {
      // Skip anomalies that already have an event associated
      if (a.event_id != null) return

      const ir = (a.ir_signal || '').trim() || '(none)'
      const rgb = (a.rgb_signal || '').trim() || '(none)'
      const key = `${ir}||${rgb}`
      const prev = s.get(key)
      if (prev) {
        prev.count += 1
      } else {
        s.set(key, { ir, rgb, count: 1 })
      }
    })
    return Array.from(s.entries()).map(([key, v]) => ({ key, ...v }))
  }, [filteredAnomalies])

  // Store selections per signal group for association during event creation
  const [pairSelections, setPairSelections] = useState<
    Record<string, { root_cause_id: number | null; confidence?: number | null }>
  >({})
  const rootCauseOptions = useMemo(
    () =>
      allowedRootCauses.map((rc: any) => ({
        value: String(rc.root_cause_id),
        label: rc.name_full || rc.name_long || rc.name_short,
      })),
    [allowedRootCauses],
  )
  const suggestRootCauses = useSuggestRootCauses()

  // --- Table state (filter/sort/selection) ---
  const [tableFilter] = useState('')
  const [sortBy] = useState<'name' | 'count' | 'loss'>('loss')
  const [sortDir] = useState<'asc' | 'desc'>('desc')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [rowSelection, setRowSelection] = useState<Record<string, boolean>>({})
  const [isMapping, setIsMapping] = useState(false)

  // Helper function to get confidence-based styling
  const getConfidenceStyle = (confidence: number | null | undefined) => {
    if (confidence === null || confidence === undefined) return {}

    if (confidence >= 0.9) {
      return { borderColor: 'var(--mantine-color-green-6)', borderWidth: 2 }
    } else if (confidence >= 0.8) {
      return { borderColor: 'var(--mantine-color-orange-6)', borderWidth: 2 }
    } else {
      return { borderColor: 'var(--mantine-color-red-6)', borderWidth: 2 }
    }
  }

  const getConfidenceTooltip = (confidence: number | null | undefined) => {
    if (confidence === null || confidence === undefined)
      return 'No confidence data'

    const percentage = Math.round(confidence * 100)
    if (confidence >= 0.8) {
      return `High confidence: ${percentage}%`
    } else if (confidence >= 0.6) {
      return `Medium confidence: ${percentage}%`
    } else {
      return `Low confidence: ${percentage}%`
    }
  }

  useEffect(() => {
    const all = new Set<string>(Array.from(combinerAggregation.keys()))
    queueMicrotask(() => setSelected(all))
    const rs: Record<string, boolean> = {}
    all.forEach((key) => (rs[key] = true))
    queueMicrotask(() => setRowSelection(rs))
  }, [combinerAggregation])

  const combinerRows = useMemo(() => {
    const rows = Array.from(combinerAggregation.entries()).map(([key, v]) => ({
      key,
      device_id: v.dcFieldId,
      name: v.dcFieldName,
      combinerName: v.combinerName,
      signalPairKey: v.signalPairKey,
      signalPairIr: v.signalPairIr,
      signalPairRgb: v.signalPairRgb,
      count: v.anomalyCount,
      loss: v.lossKw,
    }))
    const filtered = rows.filter((r) =>
      tableFilter
        ? r.name?.toLowerCase().includes(tableFilter.toLowerCase())
        : true,
    )
    const sorted = filtered.sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1
      if (sortBy === 'name') return a.name.localeCompare(b.name) * dir
      if (sortBy === 'count') return (a.count - b.count) * dir
      return (a.loss - b.loss) * dir
    })
    return sorted
  }, [combinerAggregation, tableFilter, sortBy, sortDir])

  // Legacy flags removed

  // MantineReactTable setup (unconditional to preserve hook order)
  const combinerColumns = useMemo(() => {
    return [
      {
        accessorKey: 'name',
        header: 'DC Field',
        Cell: ({ row }: any) => (
          <Text size="sm" fw={500}>
            {row.original.name}
          </Text>
        ),
      } as MRT_ColumnDef<any>,
      {
        accessorKey: 'signalPairIr',
        header: 'IR Signal',
        Cell: ({ row }: any) => (
          <Text size="sm">{row.original.signalPairIr}</Text>
        ),
      } as MRT_ColumnDef<any>,
      {
        accessorKey: 'signalPairRgb',
        header: 'RGB Signal',
        Cell: ({ row }: any) => (
          <Text size="sm">{row.original.signalPairRgb}</Text>
        ),
      } as MRT_ColumnDef<any>,
      {
        accessorKey: 'count',
        header: '# Anomalies',
        Cell: ({ cell }: any) => (
          <Text size="sm">
            {Number(cell.getValue())?.toLocaleString?.() ?? 0}
          </Text>
        ),
      } as MRT_ColumnDef<any>,
      {
        accessorKey: 'loss',
        header: 'Total DC Loss (kW)',
        Cell: ({ cell }: any) => (
          <Text size="sm">{Number(cell.getValue()).toFixed(2)}</Text>
        ),
      } as MRT_ColumnDef<any>,
    ] as MRT_ColumnDef<any>[]
  }, [])

  const combinerTable = useMantineReactTable({
    columns: combinerColumns,
    data: combinerRows,
    getRowId: (row) => row.key,
    enableRowSelection: true,
    enableMultiRowSelection: true,
    positionToolbarAlertBanner: 'top',
    renderToolbarAlertBannerContent: ({ table }) => {
      const allPageSelected = (table as any).getIsAllPageRowsSelected?.()
      const allSelected = (table as any).getIsAllRowsSelected?.()
      if (allPageSelected && !allSelected) {
        return (
          <Group gap={8}>
            <Text size="sm">All rows selected on this page.</Text>
            <Button
              variant="subtle"
              size="compact-sm"
              onClick={() => (table as any).toggleAllRowsSelected?.(true)}
            >
              Select All from All Pages
            </Button>
          </Group>
        )
      }
      return null
    },
    initialState: {
      density: 'xs',
      sorting: [{ id: sortBy, desc: sortDir === 'desc' }],
    },
    enableColumnDragging: false,
    mantineTableProps: {
      withTableBorder: true,
      withColumnBorders: true,
      striped: true,
    },
    state: { rowSelection },
    onRowSelectionChange: setRowSelection,
  })

  const handleConfirmAddEvents = async () => {
    if (!projectId || !openDate || combinerAggregation.size === 0) {
      setAddEventsOpen(false)
      return
    }

    // Create separate events for each selected signal pair group
    const items = Array.from(combinerAggregation.entries())
      .filter(([, v]) =>
        Boolean(rowSelection[v.dcFieldId + '|' + v.signalPairKey]),
      )
      .map(([, v]) => {
        // Get the root cause for this specific signal pair
        const signalPairSelection = pairSelections[v.signalPairKey]
        const rootCauseId = signalPairSelection?.root_cause_id || null

        const item = {
          device_id: v.dcFieldId,
          loss: Number(v.lossKw || 0),
          event_loss_type_id: 3,
          root_cause_id: rootCauseId,
          anomaly_uuids: v.anomalyUuids,
        }

        return item
      })

    // Group items by root_cause_id for batch processing
    const itemsByRootCause = new Map<number | null, typeof items>()
    items.forEach((item) => {
      const key = item.root_cause_id
      if (!itemsByRootCause.has(key)) {
        itemsByRootCause.set(key, [])
      }
      itemsByRootCause.get(key)!.push(item)
    })

    // Create events in batches by root cause
    for (const [rootCauseId, batchItems] of itemsByRootCause) {
      const requestPayload = {
        project_id: projectId,
        time_start: openDate.toISOString(),
        time_end: closeDate ? closeDate.toISOString() : null,
        items: batchItems.map(
          ({ root_cause_id, ...item }) => (void root_cause_id, item),
        ), // Remove root_cause_id from items
        root_cause_id: rootCauseId,
      }

      await bulkCreate.mutateAsync(requestPayload)
    }

    setAddEventsOpen(false)
    setOpenDate(null)
    setCloseDate(null)
  }

  // On-demand computation when opening the Add Events modal
  const handleOpenAddEvents = () => {
    setIsMapping(true)
    // Ensure both DC Combiner (9) and DC Field (30) layers are loaded
    // We need DC Combiners for geographic mapping and DC Fields for event creation
    const hasBothInView =
      lockedDeviceTypeIds &&
      lockedDeviceTypeIds.includes(9) &&
      lockedDeviceTypeIds.includes(30)

    if (!hasBothInView) {
      // Lock view to include both DC Combiners and DC Fields
      setIsViewLocked(true)
      setLockedDeviceTypeIds([9, 30])
      setLockedViewName('DC Combiner')
    }
  }

  // Build aggregation when mapping is requested and combiners are available
  useEffect(() => {
    if (!isMapping) return
    if (!filteredAnomalies || !deviceData.data) return

    const combiners = deviceData.data.filter(
      (d) => d.device_type_id === 9 && d.polygon,
    )
    if (combiners.length === 0) return

    // Get DC Fields (device_type_id = 30) that are children of the combiners
    const dcFields = deviceData.data.filter(
      (d) =>
        d.device_type_id === 30 &&
        combiners.some((c) => c.device_id === d.parent_device_id),
    )

    // Don't allow event creation if there are no DC Fields
    if (dcFields.length === 0) {
      queueMicrotask(() => setIsMapping(false))
      notifications.show({
        title: 'DC Fields Required',
        message:
          'No DC Field devices found. Please define DC Field devices (device_type_id = 30) as children of DC Combiners before creating events from drone inspections.',
        color: 'red',
      })
      return
    }

    // Allow spinner to render
    const id = setTimeout(() => {
      const combinerPolys = combiners
        .map((device) => {
          let polygonData = device.polygon as any
          if (typeof device.polygon === 'string') {
            try {
              polygonData = JSON.parse(device.polygon)
            } catch {
              return null
            }
          }

          let coordinates: number[][] | null = null
          const coords = polygonData?.coordinates
          if (
            Array.isArray(coords?.[0]) &&
            Array.isArray(coords?.[0]?.[0]) &&
            Array.isArray(coords?.[0]?.[0]?.[0])
          ) {
            coordinates = (coords as unknown as number[][][][])[0][0]
          } else if (
            Array.isArray(coords?.[0]) &&
            Array.isArray(coords?.[0]?.[0])
          ) {
            coordinates = (coords as unknown as number[][][])[0]
          }
          if (!coordinates) return null

          const centroidLon =
            coordinates.reduce((sum, c) => sum + c[0], 0) / coordinates.length
          const centroidLat =
            coordinates.reduce((sum, c) => sum + c[1], 0) / coordinates.length

          // Find the DC Field child for this combiner
          const dcField = dcFields.find(
            (df) => df.parent_device_id === device.device_id,
          )

          // Skip this combiner if it doesn't have a DC Field child
          if (!dcField) return null

          return {
            device_id: device.device_id,
            dc_field_id: dcField.device_id,
            name: device.name_long || 'Combiner',
            dc_field_name: dcField.name_long || 'DC Field',
            coordinates,
            centroidLat,
            centroidLon,
          }
        })
        .filter(Boolean) as Array<{
        device_id: number
        dc_field_id: number
        name: string
        dc_field_name: string
        coordinates: number[][]
        centroidLat: number
        centroidLon: number
      }>

      const totals = new Map<
        string, // Key format: "dc_field_id|signal_pair_key"
        {
          dcFieldId: number
          dcFieldName: string
          combinerName: string
          signalPairKey: string
          signalPairIr: string
          signalPairRgb: string
          lossKw: number
          anomalyCount: number
          anomalyUuids: string[]
        }
      >()

      filteredAnomalies.forEach((a) => {
        if (
          a.power_loss_kw == null ||
          a.location_lat == null ||
          a.location_lon == null
        )
          return

        // Skip anomalies that already have an event associated
        if (a.event_id != null) return

        // Create signal pair key for this anomaly
        const ir = (a.ir_signal || '').trim() || '(none)'
        const rgb = (a.rgb_signal || '').trim() || '(none)'
        const signalPairKey = `${ir}||${rgb}`

        let matched = false
        for (const comb of combinerPolys) {
          if (
            pointInPolygon([a.location_lon, a.location_lat], comb.coordinates)
          ) {
            const key = `${comb.dc_field_id}|${signalPairKey}`
            const prev = totals.get(key)
            if (prev) {
              const updated = {
                ...prev,
                lossKw: prev.lossKw + (a.power_loss_kw || 0),
                anomalyCount: prev.anomalyCount + 1,
                anomalyUuids: [...prev.anomalyUuids, a.anomaly_uuid!],
              }
              totals.set(key, updated)
            } else {
              const newGroup = {
                dcFieldId: comb.dc_field_id,
                dcFieldName: comb.dc_field_name,
                combinerName: comb.name,
                signalPairKey,
                signalPairIr: ir,
                signalPairRgb: rgb,
                lossKw: a.power_loss_kw || 0,
                anomalyCount: 1,
                anomalyUuids: [a.anomaly_uuid!],
              }
              totals.set(key, newGroup)
            }
            matched = true
            break
          }
        }

        if (matched) return

        let best: { id: number; name: string; combinerName: string } | null =
          null
        let bestDist = Infinity
        for (const comb of combinerPolys) {
          const dist = calculateDistance(
            a.location_lat,
            a.location_lon,
            comb.centroidLat,
            comb.centroidLon,
          )
          if (dist < bestDist) {
            bestDist = dist
            best = {
              id: comb.dc_field_id,
              name: comb.dc_field_name,
              combinerName: comb.name,
            }
          }
        }
        if (best && bestDist <= 300) {
          const key = `${best.id}|${signalPairKey}`
          const prev = totals.get(key)
          if (prev) {
            totals.set(key, {
              ...prev,
              lossKw: prev.lossKw + (a.power_loss_kw || 0),
              anomalyCount: prev.anomalyCount + 1,
              anomalyUuids: [...prev.anomalyUuids, a.anomaly_uuid!],
            })
          } else {
            totals.set(key, {
              dcFieldId: best.id,
              dcFieldName: best.name,
              combinerName: best.combinerName,
              signalPairKey,
              signalPairIr: ir,
              signalPairRgb: rgb,
              lossKw: a.power_loss_kw || 0,
              anomalyCount: 1,
              anomalyUuids: [a.anomaly_uuid!],
            })
          }
        }
      })

      setCombinerAggregation(totals)
      setAddEventsOpen(true)
      setIsMapping(false)
    }, 0)

    return () => clearTimeout(id)
  }, [isMapping, deviceData.data, filteredAnomalies])

  // Initialize Open Date to inspection timestamp when opening modal
  useEffect(() => {
    if (addEventsOpen && !openDate && inspectionTime) {
      const dt = new Date(inspectionTime)
      if (!isNaN(dt.getTime())) {
        queueMicrotask(() => setOpenDate(dt))
      }
    }
  }, [addEventsOpen, inspectionTime, openDate])

  // Function to get anomalies for a specific device
  const getDeviceAnomalies = useCallback(
    (deviceFeature: any) => {
      if (!filteredAnomalies || !deviceFeature?.properties?.device_id) return []

      const deviceId = deviceFeature.properties.device_id.toString()

      return filteredAnomalies.filter(
        (anomaly) =>
          anomaly.anomaly_uuid &&
          anomalyToDeviceMapping.get(anomaly.anomaly_uuid) === deviceId,
      )
    },
    [filteredAnomalies, anomalyToDeviceMapping],
  )

  const onHover = useCallback((event: MapMouseEvent) => {
    const {
      features,
      point: { x, y },
    } = event

    const hoveredFeature = features?.[0]
    setHoverInfo({ feature: hoveredFeature || null, x, y })
  }, [])

  // --- Current View Name ---
  const currentPowerTypeId = useMemo(
    () => calculatePowerDeviceTypeId(zoom),
    [zoom],
  )
  const currentViewName = viewNameMapping[currentPowerTypeId] || 'Overview'

  // --- Lock Toggle Handler ---
  const handleLockToggle = () => {
    if (isViewLocked) {
      // If it's already locked, unlock it.
      setIsViewLocked(false)
      setLockedDeviceTypeIds(null)
      setLockedViewName(null)
    } else {
      // If it's not locked, lock to the current view based on zoom.
      const currentPowerTypeId = calculatePowerDeviceTypeId(zoom)
      const currentDeviceTypeIds = calculateDeviceTypeIds(zoom)

      setIsViewLocked(true)
      setLockedDeviceTypeIds(currentDeviceTypeIds)
      setLockedViewName(viewNameMapping[currentPowerTypeId] || null)
    }
  }

  // --- Handler for Locking to a specific layer from the dropdown ---
  const handleLockToLayer = (layerName: keyof typeof layerLockConfig) => {
    const config = layerLockConfig[layerName]

    setIsViewLocked(true)
    setLockedDeviceTypeIds([...config.deviceTypeIds])
    setLockedViewName(layerName)
  }

  // Don't render the map until project data is loaded
  if (project.isLoading || !project.data) return <PageLoader />
  if (project.isError) return <PageError error={project.error} />

  // Determine if map should be empty based on project layout
  const mapStyleEmpty = !project.data.has_pv_pcs_layout

  return (
    <>
      <Box style={{ position: 'relative', height: '100%', width: '100%' }}>
        <MapboxMap
          {...viewState}
          onMove={(evt) => {
            setViewState(evt.viewState)
            setZoom(evt.viewState.zoom)
          }}
          onClick={(evt) => {
            const feature = (evt as any).features?.[0]
            const anomalyUuid = feature?.properties?.anomaly_uuid
            if (!anomalyUuid) return

            const hoveredAnomaly = filteredAnomalies.find(
              (a) => a.anomaly_uuid === anomalyUuid,
            )
            if (!hoveredAnomaly) return

            const irUrl = hoveredAnomaly.ir_image_url || null
            const rgbUrl = hoveredAnomaly.rgb_image_url || null
            if (!irUrl && !rgbUrl) return
            setImageModalData({ irUrl, rgbUrl, anomaly: hoveredAnomaly })
            setImageModalOpen(true)
          }}
          onLoad={(evt) => {
            if (!initialFitDoneRef.current && projectBounds) {
              const map = evt.target
              const boundsToFit: LngLatBoundsLike = [
                projectBounds.west,
                projectBounds.south,
                projectBounds.east,
                projectBounds.north,
              ]
              map.fitBounds(boundsToFit, {
                padding: 20,
                duration: 1000,
              })

              // Add y-offset and zoom adjustment after fitting bounds
              setTimeout(() => {
                const currentCenter = map.getCenter()
                const currentZoom = map.getZoom()

                // Adjust the latitude (y-offset) - positive moves up, negative moves down
                const yOffset = 0.005 // Adjust this value as needed (in degrees)
                const newLatitude = currentCenter.lat + yOffset

                // Adjust zoom to be more zoomed out (lower zoom = more zoomed out)
                const zoomOffset = -0.6 // Adjust this value as needed (negative = zoom out)
                const newZoom = currentZoom + zoomOffset

                map.easeTo({
                  center: [currentCenter.lng, newLatitude],
                  zoom: newZoom,
                  duration: 200,
                })

                // Update state with new zoom
                setZoom(newZoom)
              }, 1100) // Slight delay to ensure fitBounds completes

              initialFitDoneRef.current = true
            }
          }}
          style={{ width: '100%', height: '100%' }}
          mapStyle={
            gisUtils.mapStyle({
              empty: mapStyleEmpty,
              satellite: showSatellite,
              theme: computedColorScheme,
            }) ?? blankMapStyle
          }
          mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
          interactiveLayerIds={['anomaly-points', 'device-polygons']}
          onMouseMove={onHover}
          onMouseLeave={() => setHoverInfo({ feature: null, x: 0, y: 0 })}
        >
          {/* Anomaly Points - Add first to establish layer order */}
          {anomalyGeoJSON && (
            <Source id="anomaly-data" type="geojson" data={anomalyGeoJSON}>
              <Layer
                id="anomaly-points"
                type="circle"
                layout={{
                  'circle-sort-key': ['get', 'power_loss_kw'], // Sort by power loss for consistent layering
                }}
                paint={{
                  'circle-radius': [
                    'interpolate',
                    ['linear'],
                    ['get', 'power_loss_kw'],
                    0,
                    5, // Smaller minimum size
                    1,
                    7, // Smaller medium size
                    5,
                    9, // Smaller maximum size
                  ],
                  'circle-color': [
                    'case',
                    [
                      '==',
                      ['get', 'remediation_category'],
                      'Remediation Recommended',
                    ],
                    '#fa5252', // Red for urgent
                    [
                      '==',
                      ['get', 'remediation_category'],
                      'Long Term Monitoring',
                    ],
                    '#fd7e14', // Orange for monitoring
                    '#51cf66', // Green for others
                  ],
                  'circle-stroke-width': 1.5, // Reduced stroke width
                  'circle-stroke-color': '#ffffff',
                  'circle-opacity': 0.9, // Higher opacity
                  'circle-stroke-opacity': 1.0, // Full stroke opacity
                }}
              />
            </Source>
          )}

          {/* Device Polygons - Add after anomalies with beforeId to ensure proper ordering */}
          {deviceData.data && (
            <Source
              id="device-data"
              type="geojson"
              data={{
                type: 'FeatureCollection',
                features: deviceData.data
                  .filter((device) => device.polygon) // Only devices with polygons
                  .map((device) => {
                    // Parse polygon JSON string if it's a string, otherwise use as-is
                    let polygonGeometry = device.polygon
                    if (typeof device.polygon === 'string') {
                      try {
                        polygonGeometry = JSON.parse(device.polygon)
                      } catch (error) {
                        console.warn(
                          'Failed to parse polygon JSON:',
                          error,
                          device.polygon,
                        )
                        return null
                      }
                    }

                    // Skip if geometry is null
                    if (!polygonGeometry) {
                      return null
                    }

                    return {
                      type: 'Feature' as const,
                      geometry: polygonGeometry as GeoJSON.MultiPolygon,
                      properties: {
                        device_id: device.device_id,
                        device_type_id: device.device_type_id,
                        device_type_name:
                          deviceTypeNames[device.device_type_id] || 'Device',
                        name: device.name_long,
                      },
                    }
                  })
                  .filter(
                    (feature): feature is NonNullable<typeof feature> =>
                      feature !== null,
                  ), // Remove any null entries from failed parsing
              }}
            >
              <Layer
                id="device-polygons"
                type="fill"
                {...(anomalyGeoJSON && { beforeId: 'anomaly-points' })} // Only set beforeId if anomalies exist
                filter={[
                  'any',
                  ['==', ['geometry-type'], 'Polygon'],
                  ['==', ['geometry-type'], 'MultiPolygon'],
                ]}
                paint={{
                  'fill-color': [
                    'case',
                    ['==', ['get', 'device_type_id'], 2], // PCS
                    '#1f77b4',
                    ['==', ['get', 'device_type_id'], 9], // Combiner
                    '#ff7f0e',
                    ['==', ['get', 'device_type_id'], 29], // Tracker
                    '#9467bd',
                    '#cccccc', // Default
                  ],
                  'fill-opacity': [
                    'case',
                    ['==', ['get', 'device_type_id'], 2], // PCS - less transparent
                    0.6,
                    0.3, // Other device types - default transparency
                  ],
                }}
              />
              <Layer
                id="device-outlines"
                type="line"
                {...(anomalyGeoJSON && { beforeId: 'anomaly-points' })} // Only set beforeId if anomalies exist
                filter={[
                  'any',
                  ['==', ['geometry-type'], 'Polygon'],
                  ['==', ['geometry-type'], 'MultiPolygon'],
                ]}
                paint={{
                  'line-color': [
                    'case',
                    ['==', ['get', 'device_type_id'], 2], // PCS
                    '#1f77b4',
                    ['==', ['get', 'device_type_id'], 9], // Combiner
                    '#ff7f0e',
                    ['==', ['get', 'device_type_id'], 29], // Tracker
                    '#9467bd',
                    '#cccccc', // Default
                  ],
                  'line-width': 1,
                  'line-opacity': 0.8,
                }}
              />
              {/* Device Labels */}
              {showLabels && (
                <Layer
                  id="device-labels"
                  type="symbol"
                  {...(anomalyGeoJSON && { beforeId: 'anomaly-points' })} // Only set beforeId if anomalies exist
                  filter={[
                    'any',
                    ['==', ['geometry-type'], 'Polygon'],
                    ['==', ['geometry-type'], 'MultiPolygon'],
                  ]}
                  layout={{
                    'text-field': ['get', 'name'],
                    'text-size': 15,
                    'text-anchor': 'center',
                  }}
                  paint={{
                    'text-color': '#ffffff',
                    'text-halo-color': '#000000',
                    'text-halo-width': 2,
                  }}
                />
              )}
            </Source>
          )}

          {/* Hover Card */}
          {hoverInfo.feature && (
            <div
              style={{
                position: 'absolute',
                left: hoverInfo.x + 10,
                top: hoverInfo.y - 10,
                backgroundColor: 'rgba(0, 0, 0, 0.9)',
                color: 'white',
                padding: '12px',
                borderRadius: '6px',
                fontSize: '12px',
                pointerEvents: 'none',
                zIndex: 1,
                maxWidth: '280px',
                minWidth: '200px',
              }}
            >
              {hoverInfo.feature.properties?.anomaly_uuid
                ? (() => {
                    const anomalyDevice = getAnomalyDevice(
                      hoverInfo.feature.properties.anomaly_uuid,
                    )

                    const hoveredAnomaly = filteredAnomalies.find(
                      (a) =>
                        a.anomaly_uuid ===
                        hoverInfo.feature?.properties?.anomaly_uuid,
                    )

                    return (
                      <>
                        <Text size="sm" fw={600}>
                          Anomaly
                        </Text>
                        <Text size="xs">
                          Subsystem: {hoverInfo.feature.properties.subsystem}
                        </Text>
                        <Text size="xs">
                          IR: {hoverInfo.feature.properties.ir_signal}
                        </Text>
                        <Text size="xs">
                          DC Power Loss:{' '}
                          {hoverInfo.feature.properties.power_loss_kw?.toFixed(
                            2,
                          )}{' '}
                          kW
                        </Text>
                        <Text size="xs">
                          Category:{' '}
                          {hoverInfo.feature.properties.remediation_category}
                        </Text>
                        {hoveredAnomaly?.event_id && (
                          <Text size="xs" c="blue">
                            Event ID: {hoveredAnomaly.event_id}
                          </Text>
                        )}
                        {hoveredAnomaly?.event_id && (
                          <Text size="xs">
                            <Link
                              to={`/projects/${projectId}/events/event/?eventId=${hoveredAnomaly.event_id}`}
                              style={{
                                color: 'var(--mantine-color-blue-6)',
                                textDecoration: 'none',
                                fontWeight: 600,
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.textDecoration =
                                  'underline'
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.textDecoration = 'none'
                              }}
                            >
                              View Event →
                            </Link>
                          </Text>
                        )}
                        {anomalyDevice && (
                          <Text size="xs" c="dimmed" mt={4}>
                            Mapped to:{' '}
                            {deviceTypeNames[anomalyDevice.device_type_id] ||
                              'Device'}{' '}
                            {anomalyDevice.name_long}
                          </Text>
                        )}
                        {hoveredAnomaly?.ir_image_url && (
                          <Box mt={8}>
                            <img
                              src={hoveredAnomaly.ir_image_url}
                              alt="IR anomaly"
                              style={{
                                maxWidth: 260,
                                maxHeight: 200,
                                borderRadius: 4,
                              }}
                            />
                          </Box>
                        )}
                        {!hoveredAnomaly?.ir_image_url &&
                          hoveredAnomaly?.rgb_image_url && (
                            <Box mt={8}>
                              <img
                                src={hoveredAnomaly.rgb_image_url}
                                alt="RGB anomaly"
                                style={{
                                  maxWidth: 260,
                                  maxHeight: 200,
                                  borderRadius: 4,
                                }}
                              />
                            </Box>
                          )}
                      </>
                    )
                  })()
                : (() => {
                    const deviceAnomalies = getDeviceAnomalies(
                      hoverInfo.feature,
                    )

                    // Aggregate anomalies by subsystem
                    const subsystemAggregation = deviceAnomalies.reduce(
                      (acc, anomaly) => {
                        const subsystem = anomaly.subsystem || 'Unknown'
                        if (!acc[subsystem]) {
                          acc[subsystem] = {
                            count: 0,
                            totalPowerLoss: 0,
                          }
                        }
                        acc[subsystem].count += 1
                        acc[subsystem].totalPowerLoss +=
                          anomaly.power_loss_kw || 0
                        return acc
                      },
                      {} as Record<
                        string,
                        { count: number; totalPowerLoss: number }
                      >,
                    )

                    const totalPowerLoss = Object.values(
                      subsystemAggregation,
                    ).reduce((sum, item) => sum + item.totalPowerLoss, 0)

                    return (
                      <>
                        <Text size="sm" fw={600} mb={4}>
                          {hoverInfo.feature.properties?.device_type_name ||
                            'Device'}{' '}
                          {hoverInfo.feature.properties?.name || ''}
                        </Text>

                        {deviceAnomalies.length > 0 ? (
                          <>
                            <Text size="xs" fw={500} mb={2}>
                              DC Power Losses ({totalPowerLoss.toFixed(2)} kW
                              total)
                            </Text>
                            {Object.entries(subsystemAggregation).map(
                              ([subsystem, data]) => (
                                <Text
                                  key={subsystem}
                                  size="xs"
                                  style={{
                                    marginLeft: '8px',
                                    marginBottom: '2px',
                                  }}
                                >
                                  • {subsystem}:{' '}
                                  {data.totalPowerLoss.toFixed(2)} kW (
                                  {data.count} anomal
                                  {data.count === 1 ? 'y' : 'ies'})
                                </Text>
                              ),
                            )}
                          </>
                        ) : (
                          <Text size="xs" c="dimmed">
                            No anomalies detected
                          </Text>
                        )}
                      </>
                    )
                  })()}
            </div>
          )}

          <Attribution />
        </MapboxMap>

        {/* Legend and Filter Controls - Underneath StatsGrid */}
        <Box
          style={{
            position: 'absolute',
            top: 175,
            left: 0,
            zIndex: 1,
          }}
          p="md"
        >
          <Stack gap="md">
            {/* Anomaly Legend */}
            <Card withBorder radius="md" p="sm">
              <Stack gap="xs">
                <Text size="sm" fw={600}>
                  Anomalies
                </Text>
                <Group gap="xs" align="center">
                  <Box
                    style={{
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      backgroundColor: '#fa5252',
                      border: '2px solid #ffffff',
                    }}
                  />
                  <Text size="xs" lh={1}>
                    Remediation Recommended
                  </Text>
                </Group>
                <Group gap="xs" align="center">
                  <Box
                    style={{
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      backgroundColor: '#fd7e14',
                      border: '2px solid #ffffff',
                    }}
                  />
                  <Text size="xs" lh={1}>
                    Long Term Monitoring
                  </Text>
                </Group>
                <Group gap="xs" align="center">
                  <Box
                    style={{
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      backgroundColor: '#51cf66',
                      border: '2px solid #ffffff',
                    }}
                  />
                  <Text size="xs" lh={1}>
                    Other Categories
                  </Text>
                </Group>
              </Stack>
            </Card>

            {/* Filter Controls */}
            <Box
              onMouseEnter={cancelFilterMenuHideTimer}
              onMouseLeave={startFilterMenuHideTimer}
            >
              <Stack gap="xs">
                {/* Filter Toggle Button */}
                <Tooltip
                  label={showFilterMenu ? 'Hide Filters' : 'Show Filters'}
                  position="right"
                >
                  <ActionIcon
                    size={30}
                    onClick={() => setShowFilterMenu(!showFilterMenu)}
                  >
                    <IconFilter style={{ width: rem(18), height: rem(18) }} />
                  </ActionIcon>
                </Tooltip>

                {/* Collapsible Filter Menu */}
                {showFilterMenu && (
                  <Card withBorder radius="md" p="sm">
                    <Stack gap="xs">
                      {/* Remediation Category Filters */}
                      <Checkbox
                        label="Remediation Categories"
                        checked={showAllRemediationCategories}
                        onChange={(event) =>
                          setShowAllRemediationCategories(
                            event.currentTarget.checked,
                          )
                        }
                        size="sm"
                      />
                      {!showAllRemediationCategories && (
                        <MultiSelect
                          placeholder="Select categories"
                          data={uniqueRemediationCategories}
                          value={selectedRemediationCategories}
                          onChange={setSelectedRemediationCategories}
                          size="xs"
                          clearable
                          searchable
                          maxDropdownHeight={200}
                        />
                      )}

                      {/* Subsystem Filters */}
                      <Checkbox
                        label="Subsystems"
                        checked={showAllSubsystems}
                        onChange={(event) =>
                          setShowAllSubsystems(event.currentTarget.checked)
                        }
                        size="sm"
                      />
                      {!showAllSubsystems && (
                        <MultiSelect
                          placeholder="Select subsystems"
                          data={uniqueSubsystems}
                          value={selectedSubsystems}
                          onChange={setSelectedSubsystems}
                          size="xs"
                          clearable
                          searchable
                          maxDropdownHeight={200}
                        />
                      )}

                      {/* IR Signal Filters */}
                      <Checkbox
                        label="IR Signals"
                        checked={showAllIrSignals}
                        onChange={(event) =>
                          setShowAllIrSignals(event.currentTarget.checked)
                        }
                        size="sm"
                      />
                      {!showAllIrSignals && (
                        <MultiSelect
                          placeholder="Select IR signals"
                          data={uniqueIrSignals}
                          value={selectedIrSignals}
                          onChange={setSelectedIrSignals}
                          size="xs"
                          clearable
                          searchable
                          maxDropdownHeight={200}
                        />
                      )}

                      {/* RGB Signal Filters */}
                      <Checkbox
                        label="RGB Signals"
                        checked={showAllRgbSignals}
                        onChange={(event) =>
                          setShowAllRgbSignals(event.currentTarget.checked)
                        }
                        size="sm"
                      />
                      {!showAllRgbSignals && (
                        <MultiSelect
                          placeholder="Select RGB signals"
                          data={uniqueRgbSignals}
                          value={selectedRgbSignals}
                          onChange={setSelectedRgbSignals}
                          size="xs"
                          clearable
                          searchable
                          maxDropdownHeight={200}
                        />
                      )}
                    </Stack>
                  </Card>
                )}
              </Stack>
            </Box>
          </Stack>
        </Box>

        {/* Map Settings and Lock Controls */}
        <Box
          style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 1 }}
          p="md"
        >
          <Stack gap="sm">
            {/* Map Settings */}
            <MapSettings disableSatellite={mapStyleEmpty} />

            {/* Lock Button and Label Group */}
            <Menu shadow="md" width={200} position="top-start" withArrow>
              <Group gap={0}>
                <Tooltip
                  label={isViewLocked ? 'Unlock View' : 'Lock Current View'}
                  position="right"
                >
                  <Button
                    size="compact-md"
                    variant="default"
                    onClick={handleLockToggle}
                    leftSection={
                      isViewLocked ? (
                        <IconLock size={16} />
                      ) : (
                        <IconLockOpen size={16} />
                      )
                    }
                    style={{
                      borderTopRightRadius: 0,
                      borderBottomRightRadius: 0,
                    }}
                  >
                    {isViewLocked ? `${lockedViewName}` : `${currentViewName}`}
                  </Button>
                </Tooltip>
                <Menu.Target>
                  <Tooltip label="Select Layer to Lock" position="right">
                    <ActionIcon
                      variant="default"
                      size="1.875rem"
                      style={{
                        borderTopLeftRadius: 0,
                        borderBottomLeftRadius: 0,
                        borderLeft: 0,
                      }}
                    >
                      <IconChevronDown size="1rem" />
                    </ActionIcon>
                  </Tooltip>
                </Menu.Target>
              </Group>

              <Menu.Dropdown>
                <Menu.Label>Lock to Layer</Menu.Label>
                {Object.keys(layerLockConfig).map((layer) => (
                  <Menu.Item
                    key={layer}
                    onClick={() =>
                      handleLockToLayer(layer as keyof typeof layerLockConfig)
                    }
                  >
                    {layer}
                  </Menu.Item>
                ))}
              </Menu.Dropdown>
            </Menu>

            {/* Add Events Button */}
            <Tooltip
              label={
                isMapping
                  ? 'Mapping anomalies to DC Combiners'
                  : 'Group anomalies by DC Field and signal pair to create events'
              }
              multiline
              w={220}
              withArrow
            >
              <Button
                size="compact-md"
                variant="filled"
                onClick={handleOpenAddEvents}
                loading={isMapping}
              >
                Add Events...
              </Button>
            </Tooltip>
          </Stack>
        </Box>
      </Box>
      {/* Image Modal */}
      <Modal
        opened={imageModalOpen}
        onClose={() => setImageModalOpen(false)}
        title="Anomaly Image"
        size="xl"
        centered
      >
        {(imageModalData.irUrl || imageModalData.rgbUrl) && (
          <Tabs defaultValue={imageModalData.irUrl ? 'ir' : 'rgb'} mb="sm">
            <Tabs.List>
              {imageModalData.irUrl && <Tabs.Tab value="ir">IR</Tabs.Tab>}
              {imageModalData.rgbUrl && <Tabs.Tab value="rgb">RGB</Tabs.Tab>}
            </Tabs.List>
            {imageModalData.irUrl && (
              <Tabs.Panel value="ir">
                <Box mt="sm">
                  <img
                    src={imageModalData.irUrl}
                    alt="IR Anomaly"
                    style={{
                      width: '100%',
                      maxHeight: '50vh',
                      objectFit: 'contain',
                    }}
                  />
                </Box>
              </Tabs.Panel>
            )}
            {imageModalData.rgbUrl && (
              <Tabs.Panel value="rgb">
                <Box mt="sm">
                  <img
                    src={imageModalData.rgbUrl}
                    alt="RGB Anomaly"
                    style={{
                      width: '100%',
                      maxHeight: '50vh',
                      objectFit: 'contain',
                    }}
                  />
                </Box>
              </Tabs.Panel>
            )}
          </Tabs>
        )}
        {imageModalData.anomaly && (
          <Stack gap="sm">
            <Group justify="space-between" align="center">
              <Text fw={600}>Anomaly details</Text>
              {imageModalData.anomaly?.remediation_category && (
                <Badge variant="filled">
                  {imageModalData.anomaly.remediation_category}
                </Badge>
              )}
            </Group>
            <Divider />
            <Grid gutter="xs">
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <Stack gap={4}>
                  <Text size="sm">
                    <span style={{ fontWeight: 600 }}>Subsystem:</span>{' '}
                    {imageModalData.anomaly?.subsystem || '-'}
                  </Text>
                  <Text size="sm">
                    <span style={{ fontWeight: 600 }}>IR Signal:</span>{' '}
                    {imageModalData.anomaly?.ir_signal || '-'}
                  </Text>
                  <Text size="sm">
                    <span style={{ fontWeight: 600 }}>RGB Signal:</span>{' '}
                    {imageModalData.anomaly?.rgb_signal || '-'}
                  </Text>
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <Stack gap={4}>
                  <Text size="sm">
                    <span style={{ fontWeight: 600 }}>DC Power Loss:</span>{' '}
                    {imageModalData.anomaly?.power_loss_kw != null
                      ? `${imageModalData.anomaly.power_loss_kw.toFixed(2)} kW`
                      : '-'}
                  </Text>
                  {imageModalData.anomaly?.location_lat != null &&
                    imageModalData.anomaly?.location_lon != null && (
                      <Text size="sm">
                        <span style={{ fontWeight: 600 }}>Location:</span>{' '}
                        {imageModalData.anomaly?.location_lat?.toFixed(6)},{' '}
                        {imageModalData.anomaly?.location_lon?.toFixed(6)}
                      </Text>
                    )}
                  {imageModalData.anomaly?.stack_id && (
                    <Text size="sm">
                      <span style={{ fontWeight: 600 }}>Stack ID:</span>{' '}
                      {imageModalData.anomaly.stack_id}
                    </Text>
                  )}
                  {imageModalData.anomaly?.event_id && (
                    <Text size="sm" c="blue">
                      <span style={{ fontWeight: 600 }}>Event ID:</span>{' '}
                      {imageModalData.anomaly.event_id}
                    </Text>
                  )}
                  {imageModalData.anomaly?.event_id && (
                    <Text size="sm">
                      <Link
                        to={`/projects/${projectId}/events/event/?eventId=${imageModalData.anomaly.event_id}`}
                        style={{
                          color: 'var(--mantine-color-blue-6)',
                          textDecoration: 'none',
                          fontWeight: 600,
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.textDecoration = 'underline'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.textDecoration = 'none'
                        }}
                      >
                        View Event Details →
                      </Link>
                    </Text>
                  )}
                </Stack>
              </Grid.Col>
            </Grid>
          </Stack>
        )}
      </Modal>

      {/* Add Events Modal */}
      <Modal
        opened={addEventsOpen}
        onClose={() => setAddEventsOpen(false)}
        title="Create Events for Signal Pair Groups"
        size="70%"
        centered
      >
        <Stack gap="sm">
          {/* Summary */}
          <Card withBorder p="sm">
            <Grid gutter="xs" align="center">
              <Grid.Col span={{ base: 12, md: 3 }}>
                <Stack gap={4}>
                  <Text fw={700}>Total anomalies filtered</Text>
                  <Text size="lg" fw={700}>
                    {totalFiltered.toLocaleString()} /{' '}
                    {totalAnomalies.toLocaleString()}
                  </Text>
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 3 }}>
                <Stack gap={4}>
                  <Text fw={700}>Available for events</Text>
                  <Text size="lg" fw={700}>
                    {totalAvailableForEvents.toLocaleString()}
                  </Text>
                  {totalWithExistingEvents > 0 && (
                    <Group gap={4}>
                      <Text size="xs" c="dimmed">
                        {totalWithExistingEvents.toLocaleString()} already have
                        events
                      </Text>
                      <Tooltip
                        label="These anomalies are already associated with existing events and will not be included in new event creation"
                        multiline
                        w={220}
                        withArrow
                      >
                        <IconInfoCircle
                          size={14}
                          style={{ opacity: 0.5, cursor: 'help' }}
                        />
                      </Tooltip>
                    </Group>
                  )}
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 3 }}>
                <Stack gap={4}>
                  <Text fw={700}>
                    Signal pair groups with filtered anomalies
                  </Text>
                  <Text size="lg" fw={700}>
                    {combinerAggregation.size.toLocaleString()}
                  </Text>
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 3 }}>
                <Stack gap={4}>
                  <Text fw={700}>Total DC Capacity Loss</Text>
                  <Text size="lg" fw={700}>
                    {totalLossKw.toLocaleString()} kW DC
                  </Text>
                </Stack>
              </Grid.Col>
            </Grid>
          </Card>

          {/* Signal Pair Configuration (IR + RGB) */}
          <Card withBorder p="sm">
            <Stack gap="sm">
              <Group justify="space-between">
                <Text fw={600}>Signal Pair Configuration</Text>
                <Group gap="xs">
                  {rootCausesQuery.isLoading && (
                    <Text size="xs">Loading options…</Text>
                  )}
                  <Tooltip
                    label={
                      suggestRootCauses.isPending
                        ? `This will take around ${Math.round(1.5 * signalPairs.length + 6)} seconds`
                        : 'Use AI to automatically suggest root causes for each IR/RGB signal pair based on their characteristics'
                    }
                    multiline
                    w={220}
                    withArrow
                  >
                    <Button
                      variant="light"
                      size="compact-md"
                      leftSection={<IconRobot size={16} />}
                      onClick={async () => {
                        try {
                          const pairs = signalPairs.map((p) => ({
                            ir_signal: p.ir === '(none)' ? null : p.ir,
                            rgb_signal: p.rgb === '(none)' ? null : p.rgb,
                          }))
                          const candidates = allowedRootCauses.map(
                            (rc: any) => ({
                              root_cause_id: rc.root_cause_id,
                              name_short: rc.name_short,
                              name_long: rc.name_long,
                              device_type_id: rc.device_type_id,
                            }),
                          )
                          const res = await suggestRootCauses.mutateAsync({
                            pairs,
                            candidates,
                          })
                          const next: Record<
                            string,
                            {
                              root_cause_id: number | null
                              confidence?: number | null
                            }
                          > = {}
                          res.suggestions?.forEach((s) => {
                            const key = signalPairs[s.index]?.key
                            if (key)
                              next[key] = {
                                root_cause_id: s.root_cause_id,
                                confidence: s.confidence,
                              }
                          })
                          setPairSelections((prev) => ({ ...prev, ...next }))
                        } catch {
                          // optional helper: ignore errors silently
                        }
                      }}
                      loading={suggestRootCauses.isPending}
                      disabled={signalPairs.length === 0}
                    >
                      Suggest Root Causes
                    </Button>
                  </Tooltip>
                </Group>
              </Group>
              <Box mah={300} style={{ overflowY: 'auto' }}>
                <Stack gap={6}>
                  {signalPairs.length === 0 ? (
                    <Text size="sm" c="dimmed">
                      No IR/RGB signal pairs in current filter.
                    </Text>
                  ) : (
                    signalPairs.map(({ key, ir, rgb, count }) => (
                      <Group key={key} wrap="wrap" gap="xs">
                        <Badge variant="light">{count}</Badge>
                        <Text fw={500}>IR: {ir}</Text>
                        <Text fw={500}>RGB: {rgb}</Text>
                        <Tooltip
                          label={getConfidenceTooltip(
                            pairSelections[key]?.confidence,
                          )}
                          disabled={
                            pairSelections[key]?.confidence === null ||
                            pairSelections[key]?.confidence === undefined
                          }
                        >
                          <Select
                            placeholder="Root Cause"
                            data={rootCauseOptions}
                            value={
                              pairSelections[key]?.root_cause_id != null
                                ? String(pairSelections[key]?.root_cause_id)
                                : null
                            }
                            onChange={(v: string | null) =>
                              setPairSelections((prev) => ({
                                ...prev,
                                [key]: {
                                  root_cause_id: v ? Number(v) : null,
                                  confidence: prev[key]?.confidence, // Preserve confidence when manually changing
                                },
                              }))
                            }
                            searchable
                            clearable
                            w={320}
                            styles={{
                              input: getConfidenceStyle(
                                pairSelections[key]?.confidence,
                              ),
                            }}
                          />
                        </Tooltip>
                      </Group>
                    ))
                  )}
                </Stack>
              </Box>
              <Text size="xs" c="dimmed">
                Selections apply to events created from the currently filtered
                anomalies. Root causes include device types 9 (DC Combiner), 29
                (Tracker), and 30 (DC Field).
              </Text>
            </Stack>
          </Card>
          <Grid gutter="sm">
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <DateTimePicker
                label="Open date"
                placeholder="Pick date and time"
                value={openDate}
                onChange={setOpenDate}
                locale="en-US"
                valueFormat="MM/DD/YYYY HH:mm"
                required
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <DateTimePicker
                label="Close date (optional)"
                placeholder="Pick date and time"
                value={closeDate}
                onChange={setCloseDate}
                locale="en-US"
                valueFormat="MM/DD/YYYY HH:mm"
                clearable
              />
            </Grid.Col>
          </Grid>

          {/* Action Buttons moved above table */}
          <Group justify="flex-end" mt="sm">
            <Button variant="default" onClick={() => setAddEventsOpen(false)}>
              Cancel
            </Button>
            <Tooltip
              label="This may take up to a minute, depending on the number of anomalies processed"
              multiline
              w={220}
              withArrow
              events={{ hover: true, focus: true, touch: true }}
            >
              <Box style={{ display: 'inline-block' }}>
                <Button
                  onClick={handleConfirmAddEvents}
                  loading={bulkCreate.isPending}
                  disabled={!openDate || selected.size === 0}
                >
                  Create Events
                </Button>
              </Box>
            </Tooltip>
          </Group>

          {/* Table */}
          <Card withBorder p="sm">
            {combinerRows.length === 0 ? (
              <Text size="sm" c="dimmed">
                No signal pair groups matched the current filters.
              </Text>
            ) : (
              <MantineReactTable table={combinerTable} />
            )}
          </Card>
        </Stack>
      </Modal>
    </>
  )
}

export default DroneInspectionsMap
