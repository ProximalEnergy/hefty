import { HexLoaderInline } from '@/HexLoaderInline'
import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetDevicesInViewport } from '@/api/v1/analytics/gis'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import { PageError } from '@/components/Error'
import { ColorBar, MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
import { useGetDevicesV2 } from '@/hooks/api'
import * as gisUtils from '@/utils/GIS'
import { QUERY_TIME } from '@/utils/queryTiming'
import {
  ActionIcon,
  Box,
  Button,
  Group,
  Menu,
  Paper,
  Stack,
  Text,
  Tooltip,
  useComputedColorScheme,
} from '@mantine/core'
import { IconChevronDown, IconLock, IconLockOpen } from '@tabler/icons-react'
import { keepPreviousData } from '@tanstack/react-query'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { Feature, FeatureCollection } from 'geojson'
import {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import MapboxMap, {
  Layer,
  MapMouseEvent,
  MapRef,
  Source,
} from 'react-map-gl/mapbox'
import { useNavigate, useParams } from 'react-router'

import { HoverInfo } from './utils'

dayjs.extend(utc)
dayjs.extend(timezone)

// Zoom levels
const ZOOM_LEVEL_DC_ENCLOSURE = 18
const ZOOM_LEVEL_DC_SKID = 19
const ZOOM_LEVEL_BANK = 20
const ZOOM_LEVEL_STRING = 20.1

// --- Layer Lock Configuration ---
// Defines the parameters for each view that can be locked
const layerLockConfig = {
  'PCS + DC Enclosure': {
    deviceTypeIds: [DeviceTypeEnum.BESS_PCS, DeviceTypeEnum.BESS_ENCLOSURE],
    zoom: ZOOM_LEVEL_DC_ENCLOSURE,
  },
  'PCS + DC Skid': {
    deviceTypeIds: [DeviceTypeEnum.BESS_PCS, DeviceTypeEnum.BESS_DC_SKID],
    zoom: ZOOM_LEVEL_DC_SKID,
  },
  'PCS + Bank': {
    deviceTypeIds: [DeviceTypeEnum.BESS_PCS, DeviceTypeEnum.BESS_BANK],
    zoom: ZOOM_LEVEL_BANK,
  },
  'PCS + String': {
    deviceTypeIds: [DeviceTypeEnum.BESS_STRING, DeviceTypeEnum.BESS_PCS],
    zoom: ZOOM_LEVEL_STRING,
  },
}

type LayerViewName = keyof typeof layerLockConfig

const layerRequirements: Record<
  LayerViewName,
  { deviceTypeId: number; sensorTypeId: number }
> = {
  'PCS + DC Enclosure': {
    deviceTypeId: DeviceTypeEnum.BESS_ENCLOSURE,
    sensorTypeId: SensorTypeEnum.BESS_ENCLOSURE_SOC_PERCENT,
  },
  'PCS + DC Skid': {
    deviceTypeId: DeviceTypeEnum.BESS_DC_SKID,
    sensorTypeId: SensorTypeEnum.BESS_DC_SKID_SOC_PERCENT,
  },
  'PCS + Bank': {
    deviceTypeId: DeviceTypeEnum.BESS_BANK,
    sensorTypeId: SensorTypeEnum.BESS_BANK_SOC_PERCENT,
  },
  'PCS + String': {
    deviceTypeId: DeviceTypeEnum.BESS_STRING,
    sensorTypeId: SensorTypeEnum.BESS_STRING_SOC_PERCENT,
  },
}

// Color for non-comm/missing values
const COLOR_NON_COMM = '#1C7ED6'
const OPACITY_NON_COMM = 0.5

const FIT_BOUNDS_PADDING = { top: 25, bottom: 25, left: 65, right: 65 }

function getViewNameForZoom({
  zoom,
  layerAvailability,
}: {
  zoom: number
  layerAvailability: Record<LayerViewName, boolean>
}): LayerViewName {
  const candidateViews: LayerViewName[] =
    zoom >= ZOOM_LEVEL_STRING
      ? ['PCS + String', 'PCS + Bank', 'PCS + DC Skid', 'PCS + DC Enclosure']
      : zoom >= ZOOM_LEVEL_BANK
        ? ['PCS + Bank', 'PCS + DC Skid', 'PCS + DC Enclosure', 'PCS + String']
        : zoom >= ZOOM_LEVEL_DC_SKID
          ? [
              'PCS + DC Skid',
              'PCS + DC Enclosure',
              'PCS + Bank',
              'PCS + String',
            ]
          : [
              'PCS + DC Enclosure',
              'PCS + DC Skid',
              'PCS + Bank',
              'PCS + String',
            ]

  return (
    candidateViews.find((viewName) => layerAvailability[viewName]) ??
    'PCS + DC Enclosure'
  )
}

function getHighestAvailableViewName({
  layerAvailability,
}: {
  layerAvailability: Record<LayerViewName, boolean>
}): LayerViewName {
  return (
    (
      [
        'PCS + DC Enclosure',
        'PCS + DC Skid',
        'PCS + Bank',
        'PCS + String',
      ] as LayerViewName[]
    ).find((viewName) => layerAvailability[viewName]) ?? 'PCS + DC Enclosure'
  )
}

function AdaptiveGisBESS() {
  const context = useContext(GISContext)
  const { projectId } = useParams()
  const navigate = useNavigate()
  const computedColorScheme = useComputedColorScheme('dark')
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })
  const [zoom, setZoom] = useState(ZOOM_LEVEL_DC_SKID - 1)
  const blankMapStyle = gisUtils.useBlankMapStyle()
  const mapRef = useRef<MapRef>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mouseDownPos = useRef<{ x: number; y: number } | null>(null)
  const initialFitDoneRef = useRef(false)
  const initialLayerSelectionDoneRef = useRef(false)
  // Global pulse (0..1) used for heartbeat glow
  const [pulse, setPulse] = useState(0)
  // Glow defaults (non-debug)
  const MIN_GLOW_INTENSITY = 0.0
  const MIN_GLOW_OPACITY = 0.3
  const PULSE_FLOOR = 0.0

  // --- Lock State ---
  const [isViewLocked, setIsViewLocked] = useState(false)
  const [lockedDeviceTypeIds, setLockedDeviceTypeIds] = useState<
    number[] | null
  >(null)
  const [lockedZoom, setLockedZoom] = useState<number | null>(null)
  const [lockedViewName, setLockedViewName] = useState<LayerViewName | null>(
    null,
  )

  const project = useSelectProject(projectId!)

  // Determine bounds from project polygon
  const projectBounds = useMemo(() => {
    if (
      project.data?.polygon &&
      project.data.polygon.coordinates &&
      project.data.polygon.type
    ) {
      const tempGeoJson: FeatureCollection = {
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            properties: {},
            geometry: project.data.polygon as GeoJSON.MultiPolygon,
          },
        ],
      }
      const [minLng, minLat, maxLng, maxLat] =
        gisUtils.findBoundingBox(tempGeoJson)
      if (
        minLng === -180 &&
        minLat === -90 &&
        maxLng === 180 &&
        maxLat === 90
      ) {
        return null
      }
      return { north: maxLat, east: maxLng, south: minLat, west: minLng }
    }
    return null
  }, [project.data])

  const layerAvailability = useMemo<Record<LayerViewName, boolean>>(() => {
    const usedDeviceTypeIds = new Set(
      project.data?.spec?.used_device_type_ids ?? [],
    )
    const usedSensorTypeIds = project.data?.spec?.used_sensor_type_ids ?? []
    return (Object.keys(layerRequirements) as LayerViewName[]).reduce(
      (availability, layerName) => {
        const requirement = layerRequirements[layerName]
        availability[layerName] =
          usedDeviceTypeIds.has(requirement.deviceTypeId) &&
          usedSensorTypeIds.includes(requirement.sensorTypeId)
        return availability
      },
      {} as Record<LayerViewName, boolean>,
    )
  }, [
    project.data?.spec?.used_device_type_ids,
    project.data?.spec?.used_sensor_type_ids,
  ])

  const currentViewName = useMemo<LayerViewName>(() => {
    return getViewNameForZoom({ zoom, layerAvailability })
  }, [zoom, layerAvailability])

  useEffect(() => {
    if (initialLayerSelectionDoneRef.current || !project.data) return

    const highestAvailableViewName = getHighestAvailableViewName({
      layerAvailability,
    })
    setZoom(layerLockConfig[highestAvailableViewName].zoom)
    initialLayerSelectionDoneRef.current = true
  }, [layerAvailability, project.data])

  // Pick device types based on the current zoom tier.
  const dynamicDeviceTypeIds = useMemo(() => {
    return layerLockConfig[currentViewName].deviceTypeIds
  }, [currentViewName])

  const effectiveIsViewLocked =
    isViewLocked &&
    lockedViewName !== null &&
    layerAvailability[lockedViewName] === true
  const deviceTypeIdsToFetch = effectiveIsViewLocked
    ? (lockedDeviceTypeIds ?? dynamicDeviceTypeIds)
    : dynamicDeviceTypeIds

  const viewportDevices = useGetDevicesInViewport({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_type_ids: deviceTypeIdsToFetch,
      power_device_type_id: DeviceTypeEnum.BESS_PCS,
    },
    queryOptions: {
      enabled: !!project.data,
      placeholderData: keepPreviousData,
    },
  })

  // --- Real-time latest values via protected endpoint (fast, single-shot) ---
  const REALTIME_SENSOR_IDS = [
    SensorTypeEnum.BESS_PCS_AC_POWER,
    SensorTypeEnum.BESS_PCS_AVAILABLE_CHARGE_POWER,
    SensorTypeEnum.BESS_PCS_AVAILABLE_DISCHARGE_POWER,
  ]
  const pcsRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_PCS,
    },
    queryParams: {
      sensor_type_ids: REALTIME_SENSOR_IDS,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchOnWindowFocus: false,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  // Fetch BESS String SOC (sensor_type_id 45)
  const stringSocRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_STRING,
    },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.BESS_STRING_SOC_PERCENT],
    },
    queryOptions: {
      enabled: !!projectId && layerAvailability['PCS + String'],
      refetchOnWindowFocus: false,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  // Fetch BESS DC Enclosure SOC only when this layer is available in the project
  const enclosureSocRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_ENCLOSURE,
    },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.BESS_ENCLOSURE_SOC_PERCENT],
    },
    queryOptions: {
      enabled: !!projectId && layerAvailability['PCS + DC Enclosure'],
      refetchOnWindowFocus: false,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  const dcSkidSocRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_DC_SKID,
    },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.BESS_DC_SKID_SOC_PERCENT],
    },
    queryOptions: {
      enabled: !!projectId && layerAvailability['PCS + DC Skid'],
      refetchOnWindowFocus: false,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  const bankSocRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_BANK,
    },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.BESS_BANK_SOC_PERCENT],
    },
    queryOptions: {
      enabled: !!projectId && layerAvailability['PCS + Bank'],
      refetchOnWindowFocus: false,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  // Fetch all string devices on page load to get parent_device_id relationships
  // This is needed for fallback calculation (average string SOC for enclosures)
  const stringDevicesForFallback = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [DeviceTypeEnum.BESS_STRING],
      fields: ['device_id', 'parent_device_id'],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchOnWindowFocus: false,
      staleTime: QUERY_TIME.NEVER, // String devices don't change frequently
    },
  })

  // Build string SOC lookup per device
  // SOC values are stored as decimals (0.01 = 1%), multiply by 100 for percentage
  const stringSocByDevice = useMemo(() => {
    const map: Record<number, number | null> = {}
    if (!stringSocRealtime.data) return map
    const { device_ids, traces } = stringSocRealtime.data
    const socTrace = traces.find(
      (t) => t.sensor_type_id === SensorTypeEnum.BESS_STRING_SOC_PERCENT,
    )
    if (socTrace) {
      socTrace.values.forEach((v, idx) => {
        const did = device_ids[idx]
        if (did !== undefined) {
          const socValue = v as number | null
          map[did] = socValue !== null ? socValue * 100 : null
        }
      })
    }
    return map
  }, [stringSocRealtime.data])

  // Build enclosure SOC lookup per device
  // If sensor_type_id 43 is in project spec, use direct enclosure SOC values
  // Otherwise, calculate average SOC of child strings for each enclosure
  const enclosureSocByDevice = useMemo(() => {
    const map: Record<number, number | null> = {}

    // Debug logging removed

    if (layerAvailability['PCS + DC Enclosure'] && enclosureSocRealtime.data) {
      // Use direct enclosure SOC values from realtime endpoint
      const { device_ids, traces } = enclosureSocRealtime.data
      const socTrace = traces.find(
        (t) => t.sensor_type_id === SensorTypeEnum.BESS_ENCLOSURE_SOC_PERCENT,
      )
      if (socTrace) {
        socTrace.values.forEach((v, idx) => {
          const did = device_ids[idx]
          if (did !== undefined) {
            const socValue = v as number | null
            // SOC values are stored as decimals (0.01 = 1%), multiply by 100 for percentage
            map[did] = socValue !== null ? socValue * 100 : null
          }
        })
      }
    } else if (
      viewportDevices.data &&
      stringSocByDevice &&
      stringDevicesForFallback.data
    ) {
      // Calculate average SOC of child strings for each enclosure
      const enclosureDevices = (viewportDevices.data || []).filter(
        (d) => d.device_type_id === DeviceTypeEnum.BESS_ENCLOSURE,
      )
      // Use fetched string devices for parent_device_id relationships
      const stringDevices = stringDevicesForFallback.data || []

      // Debug logging removed

      enclosureDevices.forEach((enclosure) => {
        // Find child strings for this enclosure
        const childStrings = stringDevices.filter(
          (str) => str.parent_device_id === enclosure.device_id,
        )
        // Removed debug variables

        // Debug logging removed

        if (childStrings.length > 0) {
          // Calculate average SOC of child strings
          const socValues = childStrings
            .map((str) => stringSocByDevice[str.device_id])
            .filter((soc) => soc !== null && soc !== undefined) as number[]

          if (socValues.length > 0) {
            const avgSoc =
              socValues.reduce((sum, val) => sum + val, 0) / socValues.length
            map[enclosure.device_id] = avgSoc
          } else {
            map[enclosure.device_id] = null
          }
        } else {
          map[enclosure.device_id] = null
        }
      })
    }

    return map
  }, [
    layerAvailability,
    enclosureSocRealtime.data,
    viewportDevices.data,
    stringSocByDevice,
    stringDevicesForFallback.data,
  ])

  const dcSkidSocByDevice = useMemo(() => {
    const map: Record<number, number | null> = {}
    if (!dcSkidSocRealtime.data) return map
    const { device_ids, traces } = dcSkidSocRealtime.data
    const socTrace = traces.find(
      (t) => t.sensor_type_id === SensorTypeEnum.BESS_DC_SKID_SOC_PERCENT,
    )
    if (socTrace) {
      socTrace.values.forEach((v, idx) => {
        const did = device_ids[idx]
        if (did !== undefined) {
          const socValue = v as number | null
          map[did] = socValue !== null ? socValue * 100 : null
        }
      })
    }
    return map
  }, [dcSkidSocRealtime.data])

  const bankSocByDevice = useMemo(() => {
    const map: Record<number, number | null> = {}
    if (!bankSocRealtime.data) return map
    const { device_ids, traces } = bankSocRealtime.data
    const socTrace = traces.find(
      (t) => t.sensor_type_id === SensorTypeEnum.BESS_BANK_SOC_PERCENT,
    )
    if (socTrace) {
      socTrace.values.forEach((v, idx) => {
        const did = device_ids[idx]
        if (did !== undefined) {
          const socValue = v as number | null
          map[did] = socValue !== null ? socValue * 100 : null
        }
      })
    }
    return map
  }, [bankSocRealtime.data])

  // Build realtime lookup per device for quick access when building features
  const pcsRealtimeByDevice = useMemo(() => {
    const map: Record<number, Record<number, number | null>> = {}
    if (!pcsRealtime.data) return map
    const { device_ids, traces } = pcsRealtime.data
    for (const did of device_ids) map[did] = {}
    for (const tr of traces) {
      tr.values.forEach((v, idx) => {
        const did = device_ids[idx]
        if (did === undefined) return
        map[did][tr.sensor_type_id] = (v as number) ?? null
      })
    }
    return map
  }, [pcsRealtime.data])

  // Track when map and container are available for resize observer setup
  const [mapReady, setMapReady] = useState(false)

  // Reset initial fit ref when projectId changes
  useEffect(() => {
    initialFitDoneRef.current = false
    initialLayerSelectionDoneRef.current = false
  }, [projectId])

  // Reset map ready state when projectId changes (using a ref to avoid cascading renders)
  const prevProjectIdRef = useRef(projectId)
  useEffect(() => {
    if (prevProjectIdRef.current !== projectId) {
      prevProjectIdRef.current = projectId
      // Use setTimeout to defer state update and avoid cascading renders
      setTimeout(() => {
        setMapReady(false)
      }, 0)
    }
  }, [projectId])

  // Animate a heartbeat pulse (0..1). Throttled to 15 FPS to reduce Mapbox repaints.
  useEffect(() => {
    let rafId = 0
    let start = performance.now()
    let lastUpdateTime = 0
    const basePeriodMs = 1200 // global base period
    const targetFrameInterval = 1000 / 15 // ~15 FPS (66.67ms)
    const tick = (now: number) => {
      const delta = now - lastUpdateTime
      // Only update state if enough time has passed
      if (delta >= targetFrameInterval) {
        const t = (now - start) / basePeriodMs
        const raw = (Math.sin(t * 2 * Math.PI) + 1) / 2 // 0..1
        const val = Math.max(PULSE_FLOOR, raw)
        setPulse(val)
        lastUpdateTime = now
      }
      rafId = requestAnimationFrame(tick)
    }
    rafId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafId)
  }, [])

  // Ensure the map resizes to fill its container on any layout changes
  useEffect(() => {
    const container = containerRef.current
    const map = mapRef.current

    // Only set up observers if both container and map are available
    if (!container || !map) {
      return
    }

    const resize = () => {
      // Mapbox sometimes needs two rafs to fully compute size
      requestAnimationFrame(() => {
        const currentMap = mapRef.current
        if (currentMap) {
          currentMap.resize()
        }
      })
    }

    const ro = new ResizeObserver(() => resize())
    ro.observe(container)

    // Also listen to window resize for safety
    window.addEventListener('resize', resize)

    return () => {
      ro.disconnect()
      window.removeEventListener('resize', resize)
    }
  }, [mapReady])

  /**
   * Normalize PCS AC power to per-unit based on device AC capacity.
   * - `acPowerMw` is in MW (from sensor 31).
   * - `capacityAcKw` is in kW.
   * Returns a value in [-1, 1] where:
   *   -1 = full charging, 0 = idle, 1 = full discharging.
   * Returns null if acPowerMw or capacityAcKw is missing or invalid.
   */
  const normalizePcsAcPower = (
    acPowerMw: number | null | undefined,
    capacityAcKw: number | null | undefined,
  ): number | null => {
    if (acPowerMw === null || acPowerMw === undefined) return null
    if (!capacityAcKw || capacityAcKw <= 0) return null

    const capacityMw = capacityAcKw / 1000
    if (capacityMw <= 0) return null

    const perUnit = acPowerMw / capacityMw
    if (!Number.isFinite(perUnit)) return null

    return Math.max(-1, Math.min(perUnit, 1))
  }

  // Build GeoJSON features
  const geojsonData: FeatureCollection | null = useMemo(() => {
    if (!viewportDevices.data) return null

    // Determine the zoom level to use for geometry and rendering logic
    const effectiveZoom = effectiveIsViewLocked ? (lockedZoom ?? zoom) : zoom

    const features: Feature[] = []
    const activeViewName = effectiveIsViewLocked
      ? (lockedViewName ?? currentViewName)
      : currentViewName

    viewportDevices.data.forEach((device) => {
      const latestActualPower =
        device.power_data?.actual?.power?.slice(-1)[0] ?? null

      // Estimate current per-unit ratio for glow intensity
      const pcsVals = pcsRealtimeByDevice[device.device_id] || {}
      const v31 = pcsVals[31]
      const perUnit = normalizePcsAcPower(v31, device.capacity_ac)
      const ratio = perUnit !== null ? Math.abs(perUnit) : 0

      const adjustedIntensity = Math.max(
        MIN_GLOW_INTENSITY,
        Math.max(0, Math.min(ratio, 1)),
      )
      const baseProps = {
        device_id: device.device_id,
        name: device.name_long,
        capacity_dc: device.capacity_dc,
        capacity_ac: device.capacity_ac,
        device_type_id: device.device_type_id,
        power_kw: latestActualPower,
        // Placeholder for SOC until backend exposes it via viewport endpoint
        soc_percent: null as number | null,
        effective_zoom: effectiveZoom,
        glow_intensity: adjustedIntensity,
      }

      if (activeViewName === 'PCS + String') {
        // Most detailed view: render BESS String and PCS polygons if available
        if (
          (device.device_type_id === DeviceTypeEnum.BESS_STRING ||
            device.device_type_id === DeviceTypeEnum.BESS_PCS) &&
          device.polygon &&
          Array.isArray(device.polygon.coordinates) &&
          device.polygon.coordinates.length > 0
        ) {
          const pcsVals = pcsRealtimeByDevice[device.device_id] || {}
          const stringSoc = stringSocByDevice[device.device_id] ?? null

          // Calculate normalized AC power for PCS (per-unit: -1 = full charge, 0 = idle, 1 = full discharge)
          const pcsAcPowerNormalized =
            device.device_type_id === DeviceTypeEnum.BESS_PCS
              ? normalizePcsAcPower(pcsVals[31], device.capacity_ac)
              : null

          features.push({
            type: 'Feature',
            properties: {
              ...baseProps,
              renderType: 'polygon',
              // attach realtime PCS values (strings will just carry nulls)
              pcs_val_31: pcsVals[31] ?? null,
              pcs_val_80: pcsVals[80] ?? null,
              pcs_val_81: pcsVals[81] ?? null,
              // attach normalized AC power for PCS color scale
              pcs_ac_power_normalized: pcsAcPowerNormalized,
              // attach string SOC value (PCS will just carry null)
              soc_percent: stringSoc,
            },
            geometry: device.polygon as GeoJSON.MultiPolygon,
          })
        }
      } else if (activeViewName === 'PCS + DC Skid') {
        if (
          (device.device_type_id === DeviceTypeEnum.BESS_DC_SKID ||
            device.device_type_id === DeviceTypeEnum.BESS_PCS) &&
          device.polygon &&
          Array.isArray(device.polygon.coordinates) &&
          device.polygon.coordinates.length > 0
        ) {
          const dcSkidSoc = dcSkidSocByDevice[device.device_id] ?? null
          const pcsAcPowerNormalized =
            device.device_type_id === DeviceTypeEnum.BESS_PCS
              ? normalizePcsAcPower(pcsVals[31], device.capacity_ac)
              : null

          features.push({
            type: 'Feature',
            properties: {
              ...baseProps,
              renderType: 'polygon',
              pcs_val_31: pcsVals[31] ?? null,
              pcs_val_80: pcsVals[80] ?? null,
              pcs_val_81: pcsVals[81] ?? null,
              pcs_ac_power_normalized: pcsAcPowerNormalized,
              soc_percent: dcSkidSoc,
            },
            geometry: device.polygon as GeoJSON.MultiPolygon,
          })
        }
      } else if (activeViewName === 'PCS + Bank') {
        if (
          (device.device_type_id === DeviceTypeEnum.BESS_BANK ||
            device.device_type_id === DeviceTypeEnum.BESS_PCS) &&
          device.polygon &&
          Array.isArray(device.polygon.coordinates) &&
          device.polygon.coordinates.length > 0
        ) {
          const bankSoc = bankSocByDevice[device.device_id] ?? null
          const pcsAcPowerNormalized =
            device.device_type_id === DeviceTypeEnum.BESS_PCS
              ? normalizePcsAcPower(pcsVals[31], device.capacity_ac)
              : null

          features.push({
            type: 'Feature',
            properties: {
              ...baseProps,
              renderType: 'polygon',
              pcs_val_31: pcsVals[31] ?? null,
              pcs_val_80: pcsVals[80] ?? null,
              pcs_val_81: pcsVals[81] ?? null,
              pcs_ac_power_normalized: pcsAcPowerNormalized,
              soc_percent: bankSoc,
            },
            geometry: device.polygon as GeoJSON.MultiPolygon,
          })
        }
      } else {
        // Least detailed view: render PCS and DC Enclosures polygons
        if (
          device.device_type_id === DeviceTypeEnum.BESS_PCS &&
          device.polygon &&
          Array.isArray(device.polygon.coordinates) &&
          device.polygon.coordinates.length > 0
        ) {
          // Calculate normalized AC power for PCS (per-unit: -1 = full charge, 0 = idle, 1 = full discharge)
          const pcsAcPowerNormalized = normalizePcsAcPower(
            pcsVals[31],
            device.capacity_ac,
          )

          features.push({
            type: 'Feature',
            properties: {
              ...baseProps,
              renderType: 'polygon',
              // attach realtime PCS values for styling/hover
              pcs_val_31: pcsVals[31] ?? null,
              pcs_val_80: pcsVals[80] ?? null,
              pcs_val_81: pcsVals[81] ?? null,
              // attach normalized AC power for PCS color scale
              pcs_ac_power_normalized: pcsAcPowerNormalized,
            },
            geometry: device.polygon as GeoJSON.MultiPolygon,
          })
        }
        if (
          device.device_type_id === DeviceTypeEnum.BESS_ENCLOSURE &&
          device.polygon &&
          Array.isArray(device.polygon.coordinates) &&
          device.polygon.coordinates.length > 0
        ) {
          const enclosureSoc = enclosureSocByDevice[device.device_id] ?? null
          features.push({
            type: 'Feature',
            properties: {
              ...baseProps,
              renderType: 'polygon',
              // attach enclosure SOC value
              soc_percent: enclosureSoc,
            },
            geometry: device.polygon as GeoJSON.MultiPolygon,
          })
        }
      }
    })

    return { type: 'FeatureCollection', features } as FeatureCollection
  }, [
    viewportDevices.data,
    zoom,
    effectiveIsViewLocked,
    lockedZoom,
    lockedViewName,
    currentViewName,
    pcsRealtimeByDevice,
    stringSocByDevice,
    enclosureSocByDevice,
    dcSkidSocByDevice,
    bankSocByDevice,
  ])

  // Calculate bounds from actual GeoJSON data for tighter fit
  const geojsonBounds = useMemo(() => {
    if (!geojsonData || geojsonData.features.length === 0) return null
    const [minLng, minLat, maxLng, maxLat] =
      gisUtils.findBoundingBox(geojsonData)
    if (minLng === -180 && minLat === -90 && maxLng === 180 && maxLat === 90) {
      return null
    }
    const bounds = { north: maxLat, east: maxLng, south: minLat, west: minLng }
    return bounds
  }, [geojsonData])

  // Fit bounds to GeoJSON data when it becomes available
  useEffect(() => {
    if (
      !initialFitDoneRef.current &&
      geojsonBounds &&
      mapRef.current &&
      geojsonData &&
      geojsonData.features.length > 0
    ) {
      const map = mapRef.current.getMap()
      const boundsToFit: [number, number, number, number] = [
        geojsonBounds.west,
        geojsonBounds.south,
        geojsonBounds.east,
        geojsonBounds.north,
      ]
      map.fitBounds(boundsToFit, {
        padding: { top: 2, bottom: 10, left: 10, right: 10 },
        duration: 0,
      })
      // Update zoom state to match the actual zoom level after fitBounds
      // Use setTimeout to ensure fitBounds completes
      setTimeout(() => {
        const actualZoom = map.getZoom()
        setZoom(actualZoom)
      }, 0)
      initialFitDoneRef.current = true
    }
  }, [geojsonBounds, geojsonData])

  const onHover = useCallback((event: MapMouseEvent) => {
    const {
      features,
      point: { x, y },
    } = event
    const hoveredFeature = features && features[0]
    if (hoveredFeature) setHoverInfo({ feature: hoveredFeature, x, y })
    else setHoverInfo({ feature: null, x: 0, y: 0 })
  }, [])

  const handleMapMouseUp = useCallback(
    (e: MapMouseEvent) => {
      if (mouseDownPos.current && mapRef.current) {
        const dx = e.point.x - mouseDownPos.current.x
        const dy = e.point.y - mouseDownPos.current.y
        const distance = Math.sqrt(dx * dx + dy * dy)
        if (distance < 5) {
          const features = mapRef.current.queryRenderedFeatures(e.point, {
            layers: ['data-polygons'],
          })
          if (features && features.length > 0) {
            const first = features[0]
            const deviceId = first.properties?.device_id
            const deviceTypeId = first.properties?.device_type_id
            if (deviceId && deviceTypeId !== DeviceTypeEnum.BESS_ENCLOSURE) {
              navigate(
                `/projects/${projectId}/device-details/vertical?device_id=${deviceId}`,
              )
            }
          }
        }
      }
      mouseDownPos.current = null
    },
    [navigate, projectId],
  )

  // --- Lock Toggle Handler ---
  const handleLockToggle = () => {
    if (effectiveIsViewLocked) {
      // If it's already locked, unlock it.
      setIsViewLocked(false)
      setLockedDeviceTypeIds(null)
      setLockedZoom(null)
      setLockedViewName(null)
    } else {
      // If it's not locked, lock to the current view based on zoom.
      const currentDeviceTypeIds = dynamicDeviceTypeIds
      const currentZoom = zoom

      setIsViewLocked(true)
      setLockedDeviceTypeIds(currentDeviceTypeIds)
      setLockedZoom(currentZoom)
      setLockedViewName(currentViewName)
    }
  }

  // --- Handler for Locking to a specific layer from the dropdown ---
  const handleLockToLayer = (layerName: LayerViewName) => {
    if (!layerAvailability[layerName]) return

    const config = layerLockConfig[layerName]

    setIsViewLocked(true)
    setLockedDeviceTypeIds(config.deviceTypeIds)
    setLockedZoom(config.zoom)
    setLockedViewName(layerName)
  }

  if (!context) {
    throw new Error('GISContext is not provided')
  }
  const { showLabels, showSatellite, colorsGoodBad, colorsHighLow } = context

  if (project.isLoading) return <PageLoader />
  if (viewportDevices.error) return <PageError error={viewportDevices.error} />
  if (project.error) return <PageError error={project.error} />

  // No dedicated layout flag for BESS; keep basemap unless explicitly empty
  const mapStyleEmpty = false

  return (
    project.data && (
      <div style={{ position: 'relative', height: '100%', width: '100%' }}>
        <div
          ref={containerRef}
          style={{ height: '100%', width: '100%', position: 'relative' }}
        >
          {viewportDevices.isFetching &&
            (zoom >= ZOOM_LEVEL_DC_SKID || effectiveIsViewLocked) && (
              <Box
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  backgroundColor: 'rgba(0, 0, 0, 0.5)',
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem',
                  zIndex: 10,
                }}
              >
                <HexLoaderInline />
                <span>Loading Devices...</span>
              </Box>
            )}

          {geojsonData && (
            <>
              <MapboxMap
                key={projectId}
                initialViewState={{
                  bounds: geojsonBounds
                    ? [
                        geojsonBounds.west,
                        geojsonBounds.south,
                        geojsonBounds.east,
                        geojsonBounds.north,
                      ]
                    : projectBounds
                      ? [
                          projectBounds.west,
                          projectBounds.south,
                          projectBounds.east,
                          projectBounds.north,
                        ]
                      : undefined,
                  fitBoundsOptions: {
                    padding: FIT_BOUNDS_PADDING,
                  },
                }}
                onLoad={() => {
                  // Mark map as ready for resize observer setup
                  setMapReady(true)

                  // Immediately fit bounds if geojsonBounds is available and fit hasn't been done
                  if (
                    !initialFitDoneRef.current &&
                    geojsonBounds &&
                    geojsonData &&
                    geojsonData.features.length > 0 &&
                    mapRef.current
                  ) {
                    const map = mapRef.current.getMap()
                    const boundsToFit: [number, number, number, number] = [
                      geojsonBounds.west,
                      geojsonBounds.south,
                      geojsonBounds.east,
                      geojsonBounds.north,
                    ]
                    map.fitBounds(boundsToFit, {
                      padding: FIT_BOUNDS_PADDING,
                      duration: 0,
                    })
                    // Update zoom state to match the actual zoom level after fitBounds
                    // Use setTimeout to ensure fitBounds completes
                    setTimeout(() => {
                      const actualZoom = map.getZoom()
                      setZoom(actualZoom)
                    }, 0)
                    initialFitDoneRef.current = true
                  }
                }}
                onMove={(evt) => setZoom(evt.viewState.zoom)}
                style={{
                  height: '100%',
                  width: '100%',
                  borderBottomLeftRadius: 'inherit',
                  borderBottomRightRadius: 'inherit',
                }}
                ref={mapRef}
                interactiveLayerIds={['data-polygons']}
                onMouseMove={onHover}
                onMouseDown={(e) => (mouseDownPos.current = e.point)}
                onMouseUp={handleMapMouseUp}
                mapStyle={
                  gisUtils.mapStyle({
                    empty: mapStyleEmpty,
                    satellite: showSatellite,
                    theme: computedColorScheme,
                  }) ?? blankMapStyle
                }
                mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
              >
                <Source id="data" type="geojson" data={geojsonData}>
                  <Layer
                    id="data-polygons"
                    type="fill"
                    filter={[
                      'any',
                      ['==', ['geometry-type'], 'Polygon'],
                      ['==', ['geometry-type'], 'MultiPolygon'],
                    ]}
                    paint={{
                      'fill-color': [
                        'case',
                        // BESS Non-PCS colored by SOC: red (low) → yellow (mid) → bright green (high)
                        [
                          '!=',
                          ['get', 'device_type_id'],
                          DeviceTypeEnum.BESS_PCS,
                        ],
                        [
                          'interpolate',
                          ['linear'],
                          ['coalesce', ['get', 'soc_percent'], -1],
                          0,
                          '#D50000', // red for low SOC
                          50,
                          '#FFEB3B', // yellow for mid SOC
                          100,
                          '#00C853', // bright green for high SOC
                        ],

                        // PCS colored by normalized AC power: dark red (full charge, negative) → gray (idle) → dark green (full discharge, positive)
                        [
                          '==',
                          ['get', 'device_type_id'],
                          DeviceTypeEnum.BESS_PCS,
                        ],
                        [
                          'interpolate',
                          ['linear'],
                          ['coalesce', ['get', 'pcs_ac_power_normalized'], 0],
                          -1,
                          '#b71c1c', // dark red for full charging (negative AC power)
                          0,
                          '#808080', // gray for idle
                          1,
                          '#2e7d32', // dark green for full discharging (positive AC power)
                        ],

                        // Default / non-comm
                        COLOR_NON_COMM,
                      ],
                      'fill-opacity': [
                        'case',
                        ['==', ['get', 'soc_percent'], null],
                        OPACITY_NON_COMM,
                        0.7,
                      ],
                    }}
                  />
                  {/* Glow overlay for PCS polygons */}
                  <Layer
                    id="pcs-glow"
                    type="fill"
                    filter={[
                      'all',
                      [
                        'any',
                        ['==', ['geometry-type'], 'Polygon'],
                        ['==', ['geometry-type'], 'MultiPolygon'],
                      ],
                      [
                        '==',
                        ['get', 'device_type_id'],
                        DeviceTypeEnum.BESS_PCS,
                      ],
                    ]}
                    paint={{
                      'fill-color': '#ffffff',
                      'fill-opacity': [
                        'case',
                        // Only show for CHARGING with magnitude >= 1% of rated power
                        [
                          'all',
                          [
                            '<',
                            ['coalesce', ['get', 'pcs_ac_power_normalized'], 0],
                            0,
                          ],
                          [
                            '>=',
                            [
                              'abs',
                              [
                                'coalesce',
                                ['get', 'pcs_ac_power_normalized'],
                                0,
                              ],
                            ],
                            0.01,
                          ],
                        ],
                        // Charging: Show subtle white inner glow overlay
                        [
                          'max',
                          0.15, // Low base opacity - subtle overlay, not full coverage
                          [
                            '*',
                            [
                              'max',
                              0.3, // Minimum glow_intensity fallback
                              [
                                'case',
                                ['==', ['get', 'glow_intensity'], null],
                                0.5, // Default if null
                                ['get', 'glow_intensity'],
                              ],
                            ],
                            pulse,
                            1.5, // Modest boost
                            [
                              'case',
                              [
                                '>=',
                                ['get', 'effective_zoom'],
                                ZOOM_LEVEL_STRING,
                              ],
                              0.6,
                              1,
                            ],
                          ],
                        ],
                        // Discharging/idle: No inner glow
                        0.0,
                      ],
                    }}
                  />
                  {/* Outline glow using a blurred line to bleed outside the polygon */}
                  <Layer
                    id="pcs-glow-outline"
                    type="line"
                    filter={[
                      'all',
                      [
                        'any',
                        ['==', ['geometry-type'], 'Polygon'],
                        ['==', ['geometry-type'], 'MultiPolygon'],
                      ],
                      [
                        '==',
                        ['get', 'device_type_id'],
                        DeviceTypeEnum.BESS_PCS,
                      ],
                    ]}
                    layout={{
                      'line-join': 'round',
                      'line-cap': 'round',
                    }}
                    paint={{
                      // Outline glow is green for discharging, no glow for charging/idle
                      'line-color': '#2e7d32', // dark green for discharging
                      'line-opacity': [
                        'case',
                        ['==', ['get', 'glow_intensity'], null],
                        0,
                        // Outline glow only for DISCHARGING with magnitude >= 1%
                        [
                          'case',
                          [
                            'all',
                            [
                              '>=',
                              [
                                'coalesce',
                                ['get', 'pcs_ac_power_normalized'],
                                0,
                              ],
                              0,
                            ],
                            [
                              '>=',
                              [
                                'abs',
                                [
                                  'coalesce',
                                  ['get', 'pcs_ac_power_normalized'],
                                  0,
                                ],
                              ],
                              0.01,
                            ],
                          ],
                          [
                            'max',
                            MIN_GLOW_OPACITY,
                            ['*', ['get', 'glow_intensity'], pulse],
                          ],
                          0.0,
                        ],
                      ],
                      'line-width': [
                        'case',
                        ['==', ['get', 'glow_intensity'], null],
                        0,
                        // Outline width only for DISCHARGING with magnitude >= 1%
                        [
                          'case',
                          [
                            'all',
                            [
                              '>=',
                              [
                                'coalesce',
                                ['get', 'pcs_ac_power_normalized'],
                                0,
                              ],
                              0,
                            ],
                            [
                              '>=',
                              [
                                'abs',
                                [
                                  'coalesce',
                                  ['get', 'pcs_ac_power_normalized'],
                                  0,
                                ],
                              ],
                              0.01,
                            ],
                          ],
                          ['+', 2, ['*', 4, ['get', 'glow_intensity']]],
                          0,
                        ],
                      ],
                      'line-blur': ['*', 4, pulse], // Wider blur for more spread
                    }}
                  />
                  {showLabels && (
                    <Layer
                      id="data-labels"
                      type="symbol"
                      filter={['==', ['geometry-type'], 'Polygon']}
                      layout={{
                        'text-field': ['get', 'name'],
                        'text-size': 10,
                        'text-anchor': 'center',
                      }}
                      paint={{
                        'text-color': '#ffffff',
                        'text-halo-color': '#000000',
                        'text-halo-width': 1,
                      }}
                    />
                  )}
                </Source>
                {hoverInfo.feature && <CustomHoverCard hoverInfo={hoverInfo} />}
              </MapboxMap>

              {/* PCS Color Scale Legend - Left Side */}
              <Box
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  zIndex: 1,
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                }}
                px="md"
                py={100}
              >
                <Box style={{ flex: 1, minHeight: 0 }}>
                  <ColorBar
                    gradient={gisUtils.colorBar({ colors: colorsHighLow })}
                    lowLabel={'0%'}
                    middleLabel={'PCS'}
                    highLabel={'100%+'}
                  />
                </Box>
              </Box>

              {/* SOC Color Scale Legend - Right Side */}
              <Box
                style={{
                  position: 'absolute',
                  top: 0,
                  right: 0,
                  zIndex: 1,
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                }}
                px="md"
                py={100}
              >
                <Box style={{ flex: 1, minHeight: 0 }}>
                  <ColorBar
                    gradient={gisUtils.colorBar({ colors: colorsGoodBad })}
                    lowLabel={'0%'}
                    middleLabel={'SOC'}
                    highLabel={'100%'}
                  />
                </Box>
              </Box>
            </>
          )}
        </div>

        <Stack
          style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 10 }}
          p="md"
          gap="sm"
        >
          <MapSettings disableSatellite={mapStyleEmpty} />

          {/* Lock Button and Label Group */}
          <Menu shadow="md" width={200} position="top-start" withArrow>
            <Group gap={0}>
              <Tooltip
                label={
                  effectiveIsViewLocked ? 'Unlock View' : 'Lock Current View'
                }
                position="right"
              >
                <Button
                  size="compact-md"
                  variant="default"
                  onClick={handleLockToggle}
                  leftSection={
                    effectiveIsViewLocked ? (
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
                  {effectiveIsViewLocked
                    ? `${lockedViewName}`
                    : `${currentViewName}`}
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
              {(Object.keys(layerLockConfig) as LayerViewName[])
                .filter((layer) => layerAvailability[layer])
                .map((layer) => (
                  <Menu.Item
                    key={layer}
                    onClick={() => handleLockToLayer(layer)}
                  >
                    {layer}
                  </Menu.Item>
                ))}
            </Menu.Dropdown>
          </Menu>
        </Stack>

        <Attribution />
      </div>
    )
  )
}

function CustomHoverCard({ hoverInfo }: { hoverInfo: HoverInfo }) {
  if (
    hoverInfo.feature?.properties === null ||
    hoverInfo.feature?.properties === undefined
  ) {
    return null
  }

  type Props = {
    device_type_id: number
    name: string
    power_kw?: number | null
    capacity_ac?: number | null
    soc_percent?: number | null
    pcs_val_31?: number | null
    pcs_val_80?: number | null
    pcs_val_81?: number | null
    pcs_ac_power_normalized?: number | null
  }

  const props = hoverInfo.feature.properties as Props

  const isPCS = props.device_type_id === DeviceTypeEnum.BESS_PCS
  const isEnclosure = props.device_type_id === DeviceTypeEnum.BESS_ENCLOSURE
  const isDcSkid = props.device_type_id === DeviceTypeEnum.BESS_DC_SKID
  const isBank = props.device_type_id === DeviceTypeEnum.BESS_BANK
  const isString = props.device_type_id === DeviceTypeEnum.BESS_STRING

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
      <Text fw={700}>
        {(isPCS && 'BESS PCS') ||
          (isEnclosure && 'BESS DC Enclosure') ||
          (isDcSkid && 'BESS DC Skid') ||
          (isBank && 'BESS Bank') ||
          (isString && 'BESS String') ||
          'Device'}
        : {props?.name ?? 'N/A'}
      </Text>
      {isPCS && (
        <>
          <Text size="sm">
            AC Power:{' '}
            {props?.pcs_val_31 !== undefined && props?.pcs_val_31 !== null
              ? props.pcs_val_31.toFixed(3) + ' MW'
              : 'No Data'}
          </Text>
          <Text size="sm">
            Avail Charge:{' '}
            {props?.pcs_val_80 !== undefined && props?.pcs_val_80 !== null
              ? (props.pcs_val_80 / 1000).toFixed(3) + ' MW'
              : 'No Data'}
          </Text>
          <Text size="sm">
            Avail Discharge:{' '}
            {props?.pcs_val_81 !== undefined && props?.pcs_val_81 !== null
              ? (props.pcs_val_81 / 1000).toFixed(3) + ' MW'
              : 'No Data'}
          </Text>
        </>
      )}
      {(isEnclosure || isDcSkid || isBank || isString) && (
        <Text size="sm">
          SOC:{' '}
          {props?.soc_percent !== undefined && props?.soc_percent !== null
            ? props.soc_percent.toFixed(1) + ' %'
            : 'No Data'}
        </Text>
      )}
      {isPCS && (
        <Text size="sm">
          AC Capacity:{' '}
          {props?.capacity_ac !== undefined && props?.capacity_ac !== null
            ? (props.capacity_ac / 1000).toFixed(3) + ' MW'
            : 'No Data'}
        </Text>
      )}
    </Paper>
  )
}

export default AdaptiveGisBESS
