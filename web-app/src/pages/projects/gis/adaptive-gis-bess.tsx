import { HexLoaderInline } from '@/HexLoaderInline'
import { SensorTypeEnum } from '@/api/enumerations'
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

// Device type IDs for BESS domain
// 13: BESS PCS, 11: BESS DC Enclosure, 27: BESS String
const DT_BESS_PCS = 13
const DT_BESS_DC_ENCLOSURE = 11
const DT_BESS_STRING = 27

// Zoom levels
const ZOOM_LEVEL_1 = 20.1 // PCS and DC Enclosure (default a bit closer)
const ZOOM_LEVEL_2 = 19 // BESS String

// --- Layer Lock Configuration ---
// Defines the parameters for each view that can be locked
const layerLockConfig = {
  'PCS + DC Enclosure': {
    deviceTypeIds: [DT_BESS_PCS, DT_BESS_DC_ENCLOSURE] as number[],
    zoom: ZOOM_LEVEL_1,
  },
  'PCS + String': {
    deviceTypeIds: [DT_BESS_STRING, DT_BESS_PCS] as number[],
    zoom: ZOOM_LEVEL_2,
  },
}

// Color for non-comm/missing values
const COLOR_NON_COMM = '#1C7ED6'
const OPACITY_NON_COMM = 0.5

const FIT_BOUNDS_PADDING = { top: 25, bottom: 25, left: 65, right: 65 }

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
  // Initialize to a slightly more zoomed-out value than ZOOM_LEVEL_2 so
  // the default view corresponds to PCS + DC Enclosure
  const [zoom, setZoom] = useState(ZOOM_LEVEL_2 - 1)
  const blankMapStyle = gisUtils.useBlankMapStyle()
  const mapRef = useRef<MapRef>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mouseDownPos = useRef<{ x: number; y: number } | null>(null)
  const initialFitDoneRef = useRef(false)
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
  const [lockedViewName, setLockedViewName] = useState<string | null>(null)

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

  const viewportBounds = useMemo(() => {
    if (projectBounds) return projectBounds
    return { north: 40.0, east: -95.0, south: 35.0, west: -99.0 }
  }, [projectBounds])

  // Pick device types based on a single threshold to avoid flip-flopping at high zoom:
  // - zoom >= ZOOM_LEVEL_2 (19): BESS Strings + PCS
  // - zoom < ZOOM_LEVEL_2: PCS + BESS DC Enclosures
  const dynamicDeviceTypeIds = useMemo(() => {
    return zoom >= ZOOM_LEVEL_2
      ? [DT_BESS_STRING, DT_BESS_PCS]
      : [DT_BESS_PCS, DT_BESS_DC_ENCLOSURE]
  }, [zoom])

  const deviceTypeIdsToFetch = isViewLocked
    ? (lockedDeviceTypeIds ?? dynamicDeviceTypeIds)
    : dynamicDeviceTypeIds

  // For power data enrichment from backend, request the power device type
  const powerDeviceTypeIdToFetch = useMemo(() => DT_BESS_PCS, [])

  const viewportDevices = useGetDevicesInViewport({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      ...viewportBounds,
      device_type_ids: deviceTypeIdsToFetch,
      power_device_type_id: powerDeviceTypeIdToFetch,
    },
    queryOptions: {
      enabled: !!project.data && !!viewportBounds,
      placeholderData: keepPreviousData,
    },
  })

  // --- Real-time latest values via protected endpoint (fast, single-shot) ---
  const REALTIME_SENSOR_IDS = [31, 80, 81] // ac_power, available_charge, available_discharge
  const pcsRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DT_BESS_PCS,
    },
    queryParams: {
      sensor_type_ids: REALTIME_SENSOR_IDS,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchOnWindowFocus: false,
      refetchInterval: 30_000,
      staleTime: 15_000,
    },
  })

  // Fetch BESS String SOC (sensor_type_id 45)
  const stringSocRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DT_BESS_STRING,
    },
    queryParams: {
      sensor_type_ids: [45], // String SOC
    },
    queryOptions: {
      enabled: !!projectId,
      refetchOnWindowFocus: false,
      refetchInterval: 30_000,
      staleTime: 15_000,
    },
  })

  // Check if sensor_type_id 43 is available in project spec (enclosure SOC)
  const hasEnclosureSOC = useMemo(() => {
    const usedSensorTypeIds = project.data?.spec?.used_sensor_type_ids ?? []
    return usedSensorTypeIds.includes(43)
  }, [project.data?.spec?.used_sensor_type_ids])

  // Fetch BESS DC Enclosure SOC (sensor_type_id 43) - only if available in project
  const enclosureSocRealtime = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DT_BESS_DC_ENCLOSURE,
    },
    queryParams: {
      sensor_type_ids: [43], // Enclosure SOC
    },
    queryOptions: {
      enabled: !!projectId && hasEnclosureSOC,
      refetchOnWindowFocus: false,
      refetchInterval: 30_000,
      staleTime: 15_000,
    },
  })

  // Fetch all string devices on page load to get parent_device_id relationships
  // This is needed for fallback calculation (average string SOC for enclosures)
  const stringDevicesForFallback = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [DT_BESS_STRING],
      fields: ['device_id', 'parent_device_id'],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchOnWindowFocus: false,
      staleTime: Infinity, // String devices don't change frequently
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

    if (hasEnclosureSOC && enclosureSocRealtime.data) {
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
        (d) => d.device_type_id === DT_BESS_DC_ENCLOSURE,
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
    hasEnclosureSOC,
    enclosureSocRealtime.data,
    viewportDevices.data,
    stringSocByDevice,
    stringDevicesForFallback.data,
  ])

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

  // Build GeoJSON features
  const geojsonData: FeatureCollection | null = useMemo(() => {
    if (!viewportDevices.data) return null

    // Determine the zoom level to use for geometry and rendering logic
    const effectiveZoom = isViewLocked ? (lockedZoom ?? zoom) : zoom

    const features: Feature[] = []
    // Determine view based on locked device types if locked, otherwise use zoom threshold
    const isStringsView = isViewLocked
      ? (lockedDeviceTypeIds?.includes(DT_BESS_STRING) ?? false)
      : effectiveZoom >= ZOOM_LEVEL_2

    viewportDevices.data.forEach((device) => {
      const latestActualPower =
        device.power_data?.actual?.power?.slice(-1)[0] ?? null

      // Estimate current per-unit ratio for glow intensity
      const pcsVals = pcsRealtimeByDevice[device.device_id] || {}
      let ratio = 0
      const v31 = pcsVals[31]
      if (v31 !== null && v31 !== undefined) {
        // If 31 looks per-unit (|v|<=2), use abs(v). Else divide by capacity_ac.
        const absv = Math.abs(v31)
        if (absv <= 2) ratio = absv
        else if (device.capacity_ac && device.capacity_ac > 0)
          ratio = Math.min(absv / device.capacity_ac, 1)
      }

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

      if (isStringsView) {
        // Zoom level 2: render BESS String and PCS polygons if available
        if (
          (device.device_type_id === DT_BESS_STRING ||
            device.device_type_id === DT_BESS_PCS) &&
          device.polygon &&
          Array.isArray(device.polygon.coordinates) &&
          device.polygon.coordinates.length > 0
        ) {
          const pcsVals = pcsRealtimeByDevice[device.device_id] || {}
          const stringSoc = stringSocByDevice[device.device_id] ?? null

          // Calculate normalized AC power for PCS (per-unit: -1 = full charge, 0 = idle, 1 = full discharge)
          let pcsAcPowerNormalized: number | null = null
          if (device.device_type_id === DT_BESS_PCS) {
            const acPower = pcsVals[31] ?? null
            if (acPower !== null) {
              const absv = Math.abs(acPower)
              if (absv <= 2) {
                pcsAcPowerNormalized = acPower
              } else if (device.capacity_ac && device.capacity_ac > 0) {
                pcsAcPowerNormalized = acPower / device.capacity_ac
              }
            }
          }

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
      } else {
        // Zoom level 1: render PCS and DC Enclosures polygons
        if (
          device.device_type_id === DT_BESS_PCS &&
          device.polygon &&
          Array.isArray(device.polygon.coordinates) &&
          device.polygon.coordinates.length > 0
        ) {
          // Calculate normalized AC power for PCS (per-unit: -1 = full charge, 0 = idle, 1 = full discharge)
          let pcsAcPowerNormalized: number | null = null
          const acPower = pcsVals[31] ?? null
          if (acPower !== null) {
            const absv = Math.abs(acPower)
            if (absv <= 2) {
              pcsAcPowerNormalized = acPower
            } else if (device.capacity_ac && device.capacity_ac > 0) {
              pcsAcPowerNormalized = acPower / device.capacity_ac
            }
          }

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
          device.device_type_id === DT_BESS_DC_ENCLOSURE &&
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
    isViewLocked,
    lockedZoom,
    lockedDeviceTypeIds,
    pcsRealtimeByDevice,
    stringSocByDevice,
    enclosureSocByDevice,
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

  // Calculate the current view name based on zoom, even if not locked
  const currentViewName = useMemo(() => {
    // Single threshold for consistent progression: DC → String
    return zoom >= ZOOM_LEVEL_2 ? 'PCS + String' : 'PCS + DC Enclosure'
  }, [zoom])

  // --- Lock Toggle Handler ---
  const handleLockToggle = () => {
    if (isViewLocked) {
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
  const handleLockToLayer = (layerName: keyof typeof layerLockConfig) => {
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
            (zoom >= ZOOM_LEVEL_2 || isViewLocked) && (
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
                onMouseUp={(e) => {
                  if (mouseDownPos.current && mapRef.current) {
                    const dx = e.point.x - mouseDownPos.current.x
                    const dy = e.point.y - mouseDownPos.current.y
                    const distance = Math.sqrt(dx * dx + dy * dy)
                    if (distance < 5) {
                      const features = mapRef.current.queryRenderedFeatures(
                        e.point,
                        { layers: ['data-polygons'] },
                      )
                      if (features && features.length > 0) {
                        const first = features[0]
                        const deviceId = first.properties?.device_id
                        const deviceTypeId = first.properties?.device_type_id
                        // Temporarily disable navigation for DC Enclosures
                        if (deviceId && deviceTypeId !== DT_BESS_DC_ENCLOSURE) {
                          navigate(
                            `/projects/${projectId}/device-details/vertical?device_id=${deviceId}`,
                          )
                        }
                      }
                    }
                  }
                  mouseDownPos.current = null
                }}
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
                        // BESS String colored by SOC: red (low) → yellow (mid) → bright green (high)
                        ['==', ['get', 'device_type_id'], DT_BESS_STRING],
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

                        // BESS DC Enclosures by SOC: red (low) → yellow (mid) → bright green (high)
                        ['==', ['get', 'device_type_id'], DT_BESS_DC_ENCLOSURE],
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
                        ['==', ['get', 'device_type_id'], DT_BESS_PCS],
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
                      ['==', ['get', 'device_type_id'], DT_BESS_PCS],
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
                              ['>=', ['get', 'effective_zoom'], ZOOM_LEVEL_2],
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
                      ['==', ['get', 'device_type_id'], DT_BESS_PCS],
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

  const isPCS = props.device_type_id === DT_BESS_PCS
  const isEnclosure = props.device_type_id === DT_BESS_DC_ENCLOSURE
  const isString = props.device_type_id === DT_BESS_STRING

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
      {(isEnclosure || isString) && (
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
