import { HexLoaderInline } from '@/HexLoaderInline'
import { useGetDevicesInViewport } from '@/api/v1/analytics/gis'
import { useSelectProject } from '@/api/v1/operational/projects'
import { PageError } from '@/components/Error'
import { ColorBar, MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
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
import { useCallback, useContext, useMemo, useRef, useState } from 'react'
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

// Import the non-comm color and opacity
const COLOR_NON_COMM = '#1C7ED6' // From utils/GIS.ts
const OPACITY_NON_COMM = 0.5 // Restore default non-comm opacity

// --- Zoom Level Definitions ---
const VERY_HIGH_ZOOM = 16
const HIGH_ZOOM = 14.6
const LOW_ZOOM = 13
// Medium zoom is implicitly between LOW_ZOOM and HIGH_ZOOM

// --- Helper Functions for Device Type Calculation ---
const calculateDeviceTypeIds = (zoom: number): number[] => {
  if (zoom >= VERY_HIGH_ZOOM) {
    return [4, 29, 9, 2] // Added PCS(2) and Combiner(9) back for potential point rendering if polygon fails
  } else if (zoom >= HIGH_ZOOM) {
    return [2, 4, 9] // PCS, Met, Combiner
  } else if (zoom >= LOW_ZOOM) {
    return [2, 4, 9] // Also include Met/Combiner points at medium zoom for consistency
  } else {
    return [2] // Low Zoom: PCS only (polygons)
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
// Defines the parameters for each view that can be locked
const layerLockConfig = {
  PCS: {
    powerTypeId: 2,
    // Use the function to stay consistent with dynamic calculations
    deviceTypeIds: calculateDeviceTypeIds(LOW_ZOOM),
    zoom: LOW_ZOOM,
  },
  'DC Combiner': {
    powerTypeId: 9,
    deviceTypeIds: calculateDeviceTypeIds(HIGH_ZOOM),
    zoom: HIGH_ZOOM,
  },
  Tracker: {
    powerTypeId: 29,
    deviceTypeIds: calculateDeviceTypeIds(VERY_HIGH_ZOOM),
    zoom: VERY_HIGH_ZOOM,
  },
} as const // Use 'as const' for stricter typing of keys

export function AdaptiveGisMap() {
  // GIS context for settings
  const context = useContext(GISContext)

  // URL params
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const computedColorScheme = useComputedColorScheme('dark')
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })
  // --- Add Zoom State ---
  const [zoom, setZoom] = useState(LOW_ZOOM) // Initial zoom, adjust as needed
  const blankMapStyle = gisUtils.useBlankMapStyle()
  const mapRef = useRef<MapRef>(null)
  const mouseDownPos = useRef<{ x: number; y: number } | null>(null)

  // --- Lock State ---
  const [isViewLocked, setIsViewLocked] = useState(false)
  const [lockedDeviceTypeIds, setLockedDeviceTypeIds] = useState<
    number[] | null
  >(null)
  const [lockedPowerDeviceTypeId, setLockedPowerDeviceTypeId] = useState<
    number | null
  >(null)
  const [lockedZoom, setLockedZoom] = useState<number | null>(null) // State for locked zoom level
  const [lockedViewName, setLockedViewName] = useState<string | null>(null) // State for locked view name

  // Fetch project data
  const project = useSelectProject(projectId!)

  // Calculate project bounds from project polygon if available
  const projectBounds = useMemo(() => {
    // Use findBoundingBox which expects a FeatureCollection
    if (
      project.data?.polygon &&
      project.data.polygon.coordinates && // Ensure coordinates exist
      project.data.polygon.type // Ensure type exists (basic validation)
    ) {
      // Create a temporary FeatureCollection for findBoundingBox
      const tempGeoJson: FeatureCollection = {
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            properties: {}, // Minimal properties
            // Explicitly cast the polygon to the correct GeoJSON type
            geometry: project.data.polygon as GeoJSON.MultiPolygon,
          },
        ],
      }

      // Call findBoundingBox with the temporary GeoJSON
      const [minLng, minLat, maxLng, maxLat] =
        gisUtils.findBoundingBox(tempGeoJson)

      // Convert the array output [west, south, east, north] to the required object format
      // Check for default world bounds returned by findBoundingBox on error/no coords
      if (
        minLng === -180 &&
        minLat === -90 &&
        maxLng === 180 &&
        maxLat === 90
      ) {
        console.warn(
          'findBoundingBox returned default world bounds for project polygon. Check polygon data.',
          project.data.polygon,
        )
        return null // Indicate bounds could not be determined
      }

      return {
        north: maxLat,
        east: maxLng,
        south: minLat,
        west: minLng,
      }
    }
    return null // Return null if no valid polygon is available
  }, [project.data])

  // Define bounds for viewport - use project bounds if available, otherwise fallback to test bounds
  const viewportBounds = useMemo(() => {
    if (projectBounds) {
      return projectBounds
    }
    // Fallback to test bounds
    return {
      north: 40.0,
      east: -95.0,
      south: 35.0,
      west: -99.0,
    }
  }, [projectBounds])

  // --- Determine Device Types to Fetch ---
  const dynamicDeviceTypeIds = useMemo(
    () => calculateDeviceTypeIds(zoom),
    [zoom],
  )
  const dynamicPowerDeviceTypeId = useMemo(
    () => calculatePowerDeviceTypeId(zoom),
    [zoom],
  )

  const deviceTypeIdsToFetch = isViewLocked
    ? (lockedDeviceTypeIds ?? dynamicDeviceTypeIds)
    : dynamicDeviceTypeIds
  const powerDeviceTypeIdToFetch = isViewLocked
    ? (lockedPowerDeviceTypeId ?? dynamicPowerDeviceTypeId)
    : dynamicPowerDeviceTypeId

  const viewportDevices = useGetDevicesInViewport({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      ...viewportBounds, // Use the calculated bounds or fallback
      device_type_ids: deviceTypeIdsToFetch, // Use potentially locked IDs
      power_device_type_id: powerDeviceTypeIdToFetch, // Use potentially locked ID
    },
    queryOptions: {
      enabled:
        !!project.data &&
        !!(viewportBounds ?? projectBounds) &&
        (zoom >= LOW_ZOOM || isViewLocked),
      placeholderData: keepPreviousData,
      refetchInterval: 60 * 1000, // Refetch every 60 seconds
      staleTime: 30 * 1000, // Consider data stale after 30 seconds
    },
  })

  // --- Generate GeoJSON data from viewportDevices ---
  const geojsonData: FeatureCollection | null = useMemo(() => {
    if (!viewportDevices.data) return null

    // Determine the zoom level to use for geometry and rendering logic
    const effectiveZoom = isViewLocked ? (lockedZoom ?? zoom) : zoom

    const features: Feature[] = [] // Initialize empty features array

    viewportDevices.data.forEach((device) => {
      // Common properties extraction
      const latestActualPower =
        device.power_data?.actual?.power?.slice(-1)[0] ?? null
      const latestExpectedPower =
        device.power_data?.expected_soiled?.power?.slice(-1)[0] ?? null

      // --- Calculate Actual vs Expected Ratio (or Actual vs Capacity if Expected is missing) ---
      let actual_vs_expected: number | null = null
      let ratio_label = 'Actual/Expected' // Default label

      if (latestActualPower !== null) {
        if (latestExpectedPower !== null && latestExpectedPower > 0) {
          // Case 1: Valid Expected Power exists
          actual_vs_expected = (latestActualPower / latestExpectedPower) * 100
          // Keep ratio_label as "Actual/Expected"
        } else {
          // Case 2: Expected Power is missing or zero, fallback to capacity
          let usedCapacity = false
          if (
            device.device_type_id === 2 &&
            device.capacity_ac &&
            device.capacity_ac > 0
          ) {
            // PCS: Use AC Capacity
            actual_vs_expected = (latestActualPower / device.capacity_ac) * 100
            usedCapacity = true
          } else if (
            device.device_type_id === 9 &&
            device.capacity_dc &&
            device.capacity_dc > 0
          ) {
            // Combiner: Use DC Capacity
            actual_vs_expected = (latestActualPower / device.capacity_dc) * 100
            usedCapacity = true
          }

          // If we used capacity, update the label
          if (usedCapacity) {
            ratio_label = 'Actual/Capacity'
          }
          // If neither condition is met (e.g., tracker, or missing capacity), actual_vs_expected remains null
          // and label remains "Actual/Expected"
        }

        // Clamp the calculated value (if not null)
        if (actual_vs_expected !== null) {
          actual_vs_expected = Math.max(0, Math.min(actual_vs_expected, 110))
        }
      }
      // If latestActualPower is null, actual_vs_expected remains null

      // Special case: If both actual and expected are exactly 0, treat as 100%
      if (
        actual_vs_expected === null &&
        latestActualPower === 0 &&
        latestExpectedPower === 0
      ) {
        actual_vs_expected = 100
        // Keep label as "Actual/Expected" in this specific 0/0 case
      }

      const baseProperties = {
        device_id: device.device_id,
        name: device.name_long,
        capacity_dc: device.capacity_dc,
        capacity_ac: device.capacity_ac,
        power: latestActualPower,
        power_expected: latestExpectedPower,
        device_type_id: device.device_type_id,
        actual_vs_expected: actual_vs_expected,
        ratio_label: ratio_label,
        tracker_angle: device.tracker_data?.tracker_angle ?? null,
        effective_zoom: effectiveZoom,
        met_station_values:
          typeof device.met_station_values === 'string'
            ? JSON.parse(device.met_station_values)
            : device.met_station_values,
      }

      // --- Zoom-based Logic with Geometry Validation ---
      if (effectiveZoom >= VERY_HIGH_ZOOM) {
        // VERY HIGH ZOOM: Tracker (polygon), Combiner (polygon), PCS (point), Met (point)
        if (
          device.device_type_id === 29 && // Tracker Row
          device.polygon
        ) {
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
              return
            }
          }

          if (
            Array.isArray(polygonGeometry.coordinates) &&
            polygonGeometry.coordinates.length > 0
          ) {
            features.push({
              type: 'Feature',
              properties: { ...baseProperties, renderType: 'polygon' },
              geometry: polygonGeometry as GeoJSON.MultiPolygon,
            })
          }
        }
        if (
          device.device_type_id === 9 && // Combiner
          device.polygon
        ) {
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
              return
            }
          }

          if (
            Array.isArray(polygonGeometry.coordinates) &&
            polygonGeometry.coordinates.length > 0
          ) {
            features.push({
              type: 'Feature',
              properties: { ...baseProperties, renderType: 'polygon' }, // Will be colored gray
              geometry: polygonGeometry as GeoJSON.MultiPolygon,
            })
          }
        }
        if (
          device.device_type_id === 2 && // PCS
          device.point &&
          Array.isArray(device.point.coordinates)
        ) {
          features.push({
            type: 'Feature',
            properties: { ...baseProperties, renderType: 'point' },
            geometry: device.point as GeoJSON.Point,
          })
        }
        if (
          device.device_type_id === 4 && // Met
          device.point &&
          Array.isArray(device.point.coordinates)
        ) {
          features.push({
            type: 'Feature',
            properties: { ...baseProperties, renderType: 'point' },
            geometry: device.point as GeoJSON.Point,
          })
        }
      } else if (effectiveZoom >= HIGH_ZOOM) {
        // HIGH ZOOM: Combiner (polygon), PCS (point), Met (point)
        if (
          device.device_type_id === 9 && // Combiner
          device.polygon &&
          Array.isArray(device.polygon.coordinates) &&
          device.polygon.coordinates.length > 0
        ) {
          features.push({
            type: 'Feature',
            properties: { ...baseProperties, renderType: 'polygon' },
            geometry: device.polygon as GeoJSON.MultiPolygon,
          })
        }
        // PCS and Met points (same as VERY_HIGH_ZOOM, repeated for clarity)
        if (
          device.device_type_id === 2 &&
          device.point &&
          Array.isArray(device.point.coordinates)
        ) {
          features.push({
            type: 'Feature',
            properties: { ...baseProperties, renderType: 'point' },
            geometry: device.point as GeoJSON.Point,
          })
        }
        if (
          device.device_type_id === 4 &&
          device.point &&
          Array.isArray(device.point.coordinates)
        ) {
          features.push({
            type: 'Feature',
            properties: { ...baseProperties, renderType: 'point' },
            geometry: device.point as GeoJSON.Point,
          })
        }
      } else if (effectiveZoom >= LOW_ZOOM) {
        // MEDIUM ZOOM: PCS (point & polygon)
        if (device.device_type_id === 2) {
          // Check polygon validity
          if (
            device.polygon &&
            Array.isArray(device.polygon.coordinates) &&
            device.polygon.coordinates.length > 0
          ) {
            features.push({
              type: 'Feature',
              properties: { ...baseProperties, renderType: 'polygon' },
              geometry: device.polygon as GeoJSON.MultiPolygon,
            })
          }
          // Check point validity
          if (device.point && Array.isArray(device.point.coordinates)) {
            features.push({
              type: 'Feature',
              properties: { ...baseProperties, renderType: 'point' },
              geometry: device.point as GeoJSON.Point,
            })
          }
        }
        // Add Met Station points at medium zoom
        if (
          device.device_type_id === 4 &&
          device.point &&
          Array.isArray(device.point.coordinates)
        ) {
          features.push({
            type: 'Feature',
            properties: { ...baseProperties, renderType: 'point' },
            geometry: device.point as GeoJSON.Point,
          })
        }
      } else {
        // LOW ZOOM: PCS (polygon)
        // Check polygon validity
        if (
          device.device_type_id === 2 &&
          device.polygon &&
          Array.isArray(device.polygon.coordinates) &&
          device.polygon.coordinates.length > 0
        ) {
          features.push({
            type: 'Feature',
            properties: { ...baseProperties, renderType: 'polygon' },
            geometry: device.polygon as GeoJSON.MultiPolygon,
          })
        }
        // Add Met Station points at low zoom
        if (
          device.device_type_id === 4 &&
          device.point &&
          Array.isArray(device.point.coordinates)
        ) {
          features.push({
            type: 'Feature',
            properties: { ...baseProperties, renderType: 'point' },
            geometry: device.point as GeoJSON.Point,
          })
        }
      }
    }) // End forEach

    return {
      type: 'FeatureCollection',
      features: features,
    } as FeatureCollection
  }, [viewportDevices.data, zoom, isViewLocked, lockedZoom]) // Update dependencies
  // --- End GeoJSON Generation ---

  const onHover = useCallback((event: MapMouseEvent) => {
    const {
      features,
      point: { x, y },
    } = event

    const hoveredFeature =
      features?.find((f) => {
        const props = (f.properties || {}) as any
        const isCombiner = props?.device_type_id === 9
        const atVeryHighZoom = (props?.effective_zoom ?? 0) >= VERY_HIGH_ZOOM
        // Ignore combiner hovers only at highest (tracker) zoom level
        if (isCombiner && atVeryHighZoom) return false
        return true
      }) ?? null

    if (hoveredFeature) {
      setHoverInfo({ feature: hoveredFeature, x, y })
    } else {
      setHoverInfo({ feature: null, x: 0, y: 0 })
    }
  }, [])

  // Calculate the current view name based on zoom, even if not locked
  const currentPowerTypeId = useMemo(
    () => calculatePowerDeviceTypeId(zoom),
    [zoom],
  )
  const currentViewName = viewNameMapping[currentPowerTypeId] || 'Overview' // Calculation can stay here or move too

  // --- Lock Toggle Handler ---
  const handleLockToggle = () => {
    if (isViewLocked) {
      // If it's already locked, unlock it.
      setIsViewLocked(false)
      setLockedDeviceTypeIds(null)
      setLockedPowerDeviceTypeId(null)
      setLockedZoom(null)
      setLockedViewName(null)
    } else {
      // If it's not locked, lock to the current view based on zoom.
      const currentPowerTypeId = calculatePowerDeviceTypeId(zoom)
      const currentDeviceTypeIds = calculateDeviceTypeIds(zoom)
      const currentZoom = zoom

      setIsViewLocked(true)
      setLockedDeviceTypeIds(currentDeviceTypeIds)
      setLockedPowerDeviceTypeId(currentPowerTypeId)
      setLockedZoom(currentZoom)
      setLockedViewName(viewNameMapping[currentPowerTypeId] || null)
    }
  }

  // --- Handler for Locking to a specific layer from the dropdown ---
  const handleLockToLayer = (layerName: keyof typeof layerLockConfig) => {
    const config = layerLockConfig[layerName]

    setIsViewLocked(true)
    setLockedPowerDeviceTypeId(config.powerTypeId)
    setLockedDeviceTypeIds(config.deviceTypeIds)
    setLockedZoom(config.zoom)
    setLockedViewName(layerName)
  }

  // --- Check Context ---
  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, showSatellite, colorsGoodBad } = context

  // --- Early returns for loading/error states ---
  // Only show PageLoader while initial project data is loading
  if (project.isLoading) return <PageLoader />
  // Show PageError if either query fails
  if (viewportDevices.error) return <PageError error={viewportDevices.error} />
  if (project.error) return <PageError error={project.error} />

  // --- Remaining component logic ---
  const mapStyleEmpty = project.data ? !project.data.has_pv_pcs_layout : true

  // Set unit and labels for Power (Actual vs Expected)
  const lowLabel = '0%'
  const highLabel = '100%+'

  // Define tracker angle color palette and labels for the legend
  const trackerAngleColors = [
    { id: 0, value: '#b5d6e0' }, // Sunrise (-60)
    { id: 1, value: '#ffef7a' }, // Mid-morning (-30)
    { id: 2, value: '#f7c16a' }, // Noon (0)
    { id: 3, value: '#ff6b3e' }, // Mid-afternoon (30)
    { id: 4, value: '#27214e' }, // Sunset (60)
  ]
  const trackerLowLabel = '-60°'
  const trackerHighLabel = '+60°'

  return (
    // Ensure project data is loaded before rendering map elements that depend on it
    project.data && (
      <div
        style={{
          position: 'relative',
          height: '100%',
          width: '100%',
        }}
      >
        <div style={{ height: '100%', width: '100%', position: 'relative' }}>
          {/* Loading Message Overlay */}
          {viewportDevices.isFetching && (zoom >= LOW_ZOOM || isViewLocked) && (
            <Box
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                backgroundColor: 'rgba(0, 0, 0, 0.5)', // Semi-transparent black background
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                padding: '0.5rem',
                zIndex: 10, // Ensure it's above map layers but potentially below other UI
              }}
            >
              <HexLoaderInline />
              <span>Loading Device Data...</span>
            </Box>
          )}

          {geojsonData && (
            <>
              <MapboxMap
                key={projectId}
                initialViewState={{
                  bounds: projectBounds
                    ? [
                        projectBounds.west,
                        projectBounds.south,
                        projectBounds.east,
                        projectBounds.north,
                      ]
                    : undefined,
                  fitBoundsOptions: {
                    padding: {
                      top: 25,
                      bottom: 25,
                      left: 65,
                      right: 65,
                    },
                  },
                }}
                onMove={(evt) => {
                  setZoom(evt.viewState.zoom)
                }}
                style={{
                  borderBottomLeftRadius: 'inherit',
                  borderBottomRightRadius: 'inherit',
                }}
                ref={mapRef}
                interactiveLayerIds={['data-polygons', 'data-points']}
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
                        {
                          layers: ['data-polygons', 'data-points'],
                        },
                      )
                      if (features && features.length > 0) {
                        const deviceId = features[0].properties?.device_id
                        if (deviceId) {
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
                  {/* Polygon Layer - Manual Props */}
                  <Layer
                    id="data-polygons"
                    type="fill" // Explicit type
                    filter={[
                      'any',
                      ['==', ['geometry-type'], 'Polygon'],
                      ['==', ['geometry-type'], 'MultiPolygon'],
                    ]}
                    paint={{
                      // Dynamic fill color based on zoom and device type
                      'fill-color': [
                        'case',

                        // --- PRIORITY 1: VERY HIGH ZOOM Logic ---
                        ['>=', ['get', 'effective_zoom'], VERY_HIGH_ZOOM],
                        [
                          'case',
                          // Sub-Case 1.1: Tracker Row (29)
                          ['==', ['get', 'device_type_id'], 29],
                          [
                            'case',
                            // Sub-Case 1.1.1: Tracker angle is NULL -> Black
                            ['==', ['get', 'tracker_angle'], null],
                            '#000000',
                            // Sub-Case 1.1.2: Tracker angle is NOT NULL -> Interpolate by angle
                            [
                              'interpolate',
                              ['linear'],
                              ['get', 'tracker_angle'],
                              -60,
                              '#b5d6e0', // Sunrise
                              -30,
                              '#ffef7a', // Mid-morning
                              0,
                              '#f7c16a', // Noon
                              30,
                              '#ff6b3e', // Mid-afternoon
                              60,
                              '#27214e', // Sunset
                            ],
                          ],
                          // Sub-Case 1.2: Combiner (9) -> Gray
                          ['==', ['get', 'device_type_id'], 9],
                          '#cccccc',
                          // Sub-Case 1.3: Default for other polygons at VERY_HIGH_ZOOM -> Gray
                          '#cccccc',
                        ],

                        // --- PRIORITY 2: General Non-Comm/Null Data (Blue) ---
                        // Applies if not handled by VERY_HIGH_ZOOM logic above
                        ['==', ['get', 'actual_vs_expected'], null],
                        COLOR_NON_COMM, // Blue for non-communication/missing power data

                        // --- PRIORITY 3: HIGH ZOOM (Combiners by Ratio) ---
                        // Implicitly zoom < VERY_HIGH_ZOOM because of ordering
                        [
                          'all',
                          ['>=', ['get', 'effective_zoom'], HIGH_ZOOM],
                          ['==', ['get', 'device_type_id'], 9],
                        ],
                        [
                          'interpolate',
                          ['linear'],
                          ['get', 'actual_vs_expected'],
                          0,
                          colorsGoodBad[0]?.value ?? '#e03131',
                          50,
                          colorsGoodBad[1]?.value ?? '#fab005',
                          100,
                          colorsGoodBad[2]?.value ?? '#40c057',
                          110,
                          colorsGoodBad[2]?.value ?? '#40c057',
                        ],

                        // --- PRIORITY 4: MEDIUM ZOOM (PCS by Ratio) ---
                        // Implicitly zoom < HIGH_ZOOM
                        [
                          'all',
                          ['>=', ['get', 'effective_zoom'], LOW_ZOOM],
                          ['==', ['get', 'device_type_id'], 2],
                        ],
                        [
                          'interpolate',
                          ['linear'],
                          ['get', 'actual_vs_expected'],
                          0,
                          colorsGoodBad[0]?.value ?? '#e03131',
                          50,
                          colorsGoodBad[1]?.value ?? '#fab005',
                          100,
                          colorsGoodBad[2]?.value ?? '#40c057',
                          110,
                          colorsGoodBad[2]?.value ?? '#40c057',
                        ],

                        // --- PRIORITY 5: LOW ZOOM (PCS by Ratio) ---
                        // Implicitly zoom < LOW_ZOOM
                        ['all', ['==', ['get', 'device_type_id'], 2]],
                        [
                          'interpolate',
                          ['linear'],
                          ['get', 'actual_vs_expected'],
                          0,
                          colorsGoodBad[0]?.value ?? '#e03131',
                          50,
                          colorsGoodBad[1]?.value ?? '#fab005',
                          100,
                          colorsGoodBad[2]?.value ?? '#40c057',
                          110,
                          colorsGoodBad[2]?.value ?? '#40c057',
                        ],

                        // --- Default Fallback ---
                        '#cccccc',
                      ],
                      'fill-opacity': [
                        'case',

                        // New: make combiners more transparent only at the highest (tracker) zoom level
                        [
                          'all',
                          ['>=', ['get', 'effective_zoom'], VERY_HIGH_ZOOM],
                          ['==', ['get', 'device_type_id'], 9],
                        ],
                        0.35,

                        // Keep non-comm blue opacity as before
                        [
                          'all',
                          ['==', ['get', 'actual_vs_expected'], null],
                          // Exclude trackers at high zoom with null angle
                          [
                            '!=',
                            [
                              'all',
                              ['>=', ['get', 'effective_zoom'], VERY_HIGH_ZOOM],
                              ['==', ['get', 'device_type_id'], 29],
                              ['==', ['get', 'tracker_angle'], null],
                            ],
                            true,
                          ],
                        ],
                        OPACITY_NON_COMM,

                        // Default opacity for other colored polygons
                        0.7,
                      ],
                    }}
                  />
                  {/* Point Layer (Keep as is) */}
                  <Layer
                    id="data-points"
                    type="circle"
                    filter={['==', ['geometry-type'], 'Point']}
                    paint={{
                      'circle-radius': 5,
                      'circle-color': [
                        'case',
                        ['==', ['get', 'device_type_id'], 2], // PCS
                        '#1f77b4',
                        ['==', ['get', 'device_type_id'], 4], // Met Station
                        '#2ca02c',
                        ['==', ['get', 'device_type_id'], 9], // Combiner
                        '#ff7f0e',
                        ['==', ['get', 'device_type_id'], 29], // Tracker Row
                        '#9467bd', // Purple for Trackers
                        '#cccccc', // Default
                      ],
                      'circle-stroke-width': 1,
                      'circle-stroke-color': '#ffffff',
                    }}
                  />
                  {/* Label Layer - Manual Props */}
                  {showLabels && (
                    <Layer
                      id="data-labels"
                      type="symbol" // Explicit type
                      // Assume labels apply to points for now, adjust filter if needed
                      filter={['==', ['geometry-type'], 'Point']}
                      layout={{
                        'text-field': ['get', 'name'], // Get name from properties
                        'text-size': 10,
                        'text-anchor': 'top',
                        'text-offset': [0, 0.8],
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
                {isViewLocked ? (
                  // Show locked legend based on locked device type
                  lockedPowerDeviceTypeId === 29 ? (
                    <ColorBar
                      gradient={gisUtils.colorBar({
                        colors: trackerAngleColors,
                      })}
                      lowLabel={trackerLowLabel}
                      highLabel={trackerHighLabel}
                    />
                  ) : (
                    <ColorBar
                      gradient={gisUtils.colorBar({ colors: colorsGoodBad })}
                      lowLabel={lowLabel}
                      highLabel={highLabel}
                    />
                  )
                ) : // Show dynamic legend based on current zoom
                zoom >= VERY_HIGH_ZOOM ? (
                  <ColorBar
                    gradient={gisUtils.colorBar({ colors: trackerAngleColors })}
                    lowLabel={trackerLowLabel}
                    highLabel={trackerHighLabel}
                  />
                ) : (
                  <ColorBar
                    gradient={gisUtils.colorBar({ colors: colorsGoodBad })}
                    lowLabel={lowLabel}
                    highLabel={highLabel}
                  />
                )}
              </Box>
            </>
          )}
        </div>

        {/* --- Combined Bottom Left Controls --- */}
        <Stack
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            zIndex: 10,
          }}
          p="md"
          gap="sm"
        >
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

  // Add type definition for the props
  type DeviceProps = {
    device_type_id: number
    device_id: number
    name: string
    power?: number
    power_expected?: number
    actual_vs_expected?: number
    ratio_label?: string
    capacity_dc?: number
    tracker_angle?: number
    met_station_values: any
  }

  // Adjust property access with type
  const props = {
    ...hoverInfo.feature.properties,
    met_station_values:
      typeof hoverInfo.feature.properties.met_station_values === 'string'
        ? JSON.parse(hoverInfo.feature.properties.met_station_values)
        : hoverInfo.feature.properties.met_station_values,
  } as DeviceProps

  // Determine device type string
  let deviceTypeString = 'Device'
  if (props?.device_type_id === 2) {
    deviceTypeString = 'PCS'
  } else if (props?.device_type_id === 9) {
    deviceTypeString = 'Combiner' // Or DC Combiner?
  } else if (props?.device_type_id === 4) {
    deviceTypeString = 'Met Station'
  } else if (props?.device_type_id === 29) {
    deviceTypeString = 'Tracker Row'
  }

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
        {/* Use determined device type and name */}
        {deviceTypeString}: {props?.name ?? 'N/A'}
      </Text>
      {/* Show tracker angle if it's a tracker row */}
      {props?.device_type_id === 29 && (
        <Text size="sm">
          Tracker Angle:{' '}
          {props?.tracker_angle !== undefined && props?.tracker_angle !== null
            ? props.tracker_angle.toFixed(1) + '°'
            : 'No Data'}
        </Text>
      )}
      {/* Only show power details for non-tracker devices and non-met-station devices */}
      {props?.device_type_id !== 29 && props?.device_type_id !== 4 && (
        <>
          <Text size="sm">
            Power:{' '}
            {props?.power !== undefined && props?.power !== null
              ? props.power.toFixed(1) + ' kW'
              : 'No Data'}
          </Text>
          <Text size="sm">
            Expected Power:{' '}
            {props?.power_expected !== undefined &&
            props?.power_expected !== null
              ? props.power_expected.toFixed(1) + ' kW'
              : 'No Data'}
          </Text>
          {/* Use the dynamic label from properties */}
          <Text size="sm">
            {props?.ratio_label ?? 'Actual/Expected'}:{' '}
            {props?.actual_vs_expected !== undefined &&
            props?.actual_vs_expected !== null
              ? props.actual_vs_expected.toFixed(1) + ' %'
              : 'No Data'}
          </Text>
          <Text size="sm">
            DC Capacity:{' '}
            {props?.capacity_dc !== undefined && props?.capacity_dc !== null
              ? props.capacity_dc.toFixed(1) + ' kW'
              : 'No Data'}
          </Text>
        </>
      )}
      {/* Display Met Station specific data */}
      {props?.device_type_id === 4 && (
        <>
          <Text size="sm">
            POA:{' '}
            {(() => {
              const values = props.met_station_values
              return values?.poa !== undefined && values?.poa !== null
                ? values.poa.toFixed(1) + ' W/m²'
                : 'No Data'
            })()}
          </Text>
          <Text size="sm">
            GHI:{' '}
            {(() => {
              const values = props.met_station_values
              return values?.ghi !== undefined && values?.ghi !== null
                ? values.ghi.toFixed(1) + ' W/m²'
                : 'No Data'
            })()}
          </Text>
          <Text size="sm">
            Ambient Temp:{' '}
            {(() => {
              const values = props.met_station_values
              return values?.ambient_temp !== undefined &&
                values?.ambient_temp !== null
                ? values.ambient_temp.toFixed(1) + ' °C'
                : 'No Data'
            })()}
          </Text>
          <Text size="sm">
            Wind Speed:{' '}
            {(() => {
              const values = props.met_station_values
              return values?.wind_speed !== undefined &&
                values?.wind_speed !== null
                ? values.wind_speed.toFixed(1) + ' m/s'
                : 'No Data'
            })()}
          </Text>
        </>
      )}
    </Paper>
  )
}
