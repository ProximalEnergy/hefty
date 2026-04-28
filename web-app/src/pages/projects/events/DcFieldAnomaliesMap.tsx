import { DeviceTypeEnum } from '@/api/enumerations'
import {
  DroneAnomaly,
  useGetEventAnomalies,
} from '@/api/v1/operational/project/events'
import Attribution from '@/components/gis/Attribution'
import { useGetDevicesV2 } from '@/hooks/api'
import { Event } from '@/hooks/types'
import * as gisUtils from '@/utils/GIS'
import {
  Badge,
  Box,
  Card,
  Grid,
  Group,
  Loader,
  Modal,
  Stack,
  Tabs,
  Text,
  useComputedColorScheme,
} from '@mantine/core'
import { IconFlag } from '@tabler/icons-react'
import { Feature } from 'geojson'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import MapboxMap, {
  Layer,
  MapMouseEvent,
  MapRef,
  Marker,
  Source,
} from 'react-map-gl/mapbox'

interface DcFieldAnomaliesMapProps {
  event: Event | null
  projectId: string
}

interface HoverInfo {
  feature: Feature | null
  x: number
  y: number
}

interface MapBounds {
  west: number
  south: number
  east: number
  north: number
}

type LngLat = [number, number]

const EVENT_FOCUS_ZOOM = 17
const FOCUS_ANIMATION_DURATION_MS = 1800

const getBoundsCenter = (bounds: MapBounds): [number, number] => [
  (bounds.west + bounds.east) / 2,
  (bounds.south + bounds.north) / 2,
]

const getPointCoordinates = (
  point: { coordinates: number[] } | null | undefined,
): [number, number] | null => {
  if (
    Array.isArray(point?.coordinates) &&
    Number.isFinite(point.coordinates[0]) &&
    Number.isFinite(point.coordinates[1])
  ) {
    return [point.coordinates[0], point.coordinates[1]]
  }

  return null
}

const collectLngLats = (coordinates: unknown): LngLat[] => {
  if (!Array.isArray(coordinates)) return []

  if (
    typeof coordinates[0] === 'number' &&
    typeof coordinates[1] === 'number' &&
    Number.isFinite(coordinates[0]) &&
    Number.isFinite(coordinates[1])
  ) {
    return [[coordinates[0], coordinates[1]]]
  }

  return coordinates.flatMap((coord) => collectLngLats(coord))
}

const getPolygonBounds = (polygon: unknown): MapBounds | null => {
  if (!polygon) return null

  let polygonData: unknown = polygon
  if (typeof polygon === 'string') {
    try {
      polygonData = JSON.parse(polygon)
    } catch (error) {
      console.warn('Failed to parse polygon JSON for bounds:', error, polygon)
      return null
    }
  }

  const coordinatesSource =
    typeof polygonData === 'object' &&
    polygonData !== null &&
    'coordinates' in polygonData
      ? polygonData.coordinates
      : null

  const coordinates = collectLngLats(coordinatesSource)
  if (coordinates.length === 0) {
    console.warn(
      'Invalid polygon coordinates structure for bounds:',
      coordinatesSource,
    )
    return null
  }

  const lngs = coordinates.map(([lng]) => lng)
  const lats = coordinates.map(([, lat]) => lat)

  return {
    west: Math.min(...lngs),
    south: Math.min(...lats),
    east: Math.max(...lngs),
    north: Math.max(...lats),
  }
}

const DcFieldAnomaliesMap = ({
  event,
  projectId,
}: DcFieldAnomaliesMapProps) => {
  const computedColorScheme = useComputedColorScheme('dark')
  const mapRef = useRef<MapRef>(null)
  const hasFocusedEventRef = useRef(false)
  const [isMapLoaded, setIsMapLoaded] = useState(false)
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })

  // Image modal state
  const [imageModalOpen, setImageModalOpen] = useState(false)
  const [imageModalData, setImageModalData] = useState<{
    irUrl: string | null
    rgbUrl: string | null
    anomaly: DroneAnomaly | null
  }>({ irUrl: null, rgbUrl: null, anomaly: null })

  const blankMapStyle = gisUtils.useBlankMapStyle()

  // Get all DC Combiner devices in the project for display purposes
  const { data: devices, isLoading: devicesLoading } = useGetDevicesV2({
    pathParams: { projectId },
    filters: {
      device_type_ids: [DeviceTypeEnum.PV_DC_COMBINER, DeviceTypeEnum.DC_FIELD],
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  // Find the DC Field device and its parent combiner for map centering
  const dcFieldInfo = useMemo(() => {
    if (!devices || !event?.device_id) return null

    // Find the DC Field device
    const dcField = devices.find(
      (d) =>
        d.device_id === event.device_id &&
        d.device_type_id === DeviceTypeEnum.DC_FIELD,
    )
    if (!dcField?.parent_device_id) return null

    // Find its parent DC Combiner
    const parentCombiner = devices.find(
      (d) =>
        d.device_id === dcField.parent_device_id &&
        d.device_type_id === DeviceTypeEnum.PV_DC_COMBINER,
    )

    return { dcField, parentCombiner }
  }, [devices, event])

  // Get all DC Combiners with polygons for map visualization
  const allCombiners = useMemo(() => {
    if (!devices) return []
    return devices.filter(
      (d) => d.device_type_id === DeviceTypeEnum.PV_DC_COMBINER && d.polygon,
    )
  }, [devices])

  // Get anomalies directly by event_id (much simpler than geographic filtering!)
  const { data: relevantAnomalies, isLoading: anomaliesLoading } =
    useGetEventAnomalies({
      pathParams: {
        projectId,
        eventId: event?.event_id ?? -1,
      },
      queryOptions: {
        enabled: !!projectId && !!event?.event_id,
      },
    })

  // Calculate total DC combiner capacity for percentage calculation
  const totalDcCombinerCapacity = useMemo(() => {
    if (!dcFieldInfo?.parentCombiner?.capacity_dc) return 0
    return dcFieldInfo.parentCombiner.capacity_dc
  }, [dcFieldInfo?.parentCombiner?.capacity_dc])

  // Convert anomalies to GeoJSON
  const anomalyGeoJSON = useMemo(() => {
    if (!relevantAnomalies?.length) {
      return null
    }

    const features = relevantAnomalies
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
        },
      }))

    return {
      type: 'FeatureCollection' as const,
      features,
    }
  }, [relevantAnomalies])

  // Create combiner polygon GeoJSON for all combiners
  const combinerGeoJSON = useMemo(() => {
    if (allCombiners.length === 0) return null

    const features = allCombiners
      .map((device) => {
        let polygonData = device.polygon
        if (typeof device.polygon === 'string') {
          try {
            polygonData = JSON.parse(device.polygon)
          } catch (error) {
            console.warn(
              'Failed to parse polygon JSON for GeoJSON:',
              error,
              device.polygon,
            )
            return null
          }
        }

        // Skip if geometry is null
        if (!polygonData) {
          return null
        }

        return {
          type: 'Feature' as const,
          geometry: polygonData as GeoJSON.MultiPolygon,
          properties: {
            device_id: device.device_id,
            device_type_id: device.device_type_id,
            name: device.name_long,
            isParent:
              dcFieldInfo?.parentCombiner?.device_id === device.device_id,
          },
        }
      })
      .filter(
        (feature): feature is NonNullable<typeof feature> => feature !== null,
      )

    return {
      type: 'FeatureCollection' as const,
      features,
    }
  }, [allCombiners, dcFieldInfo?.parentCombiner])

  const dcField = dcFieldInfo?.dcField
  const parentCombiner = dcFieldInfo?.parentCombiner

  const ancestorDeviceIds = useMemo(() => {
    const pathIds = dcField?.device_id_path
      ?.split('.')
      .map((pathDeviceId) => Number(pathDeviceId))
      .filter((pathDeviceId) => Number.isFinite(pathDeviceId))

    if (pathIds?.length) {
      return pathIds
        .filter((pathDeviceId) => pathDeviceId !== dcField?.device_id)
        .reverse()
    }

    return dcField?.parent_device_id ? [dcField.parent_device_id] : []
  }, [dcField])

  const ancestorDevices = useGetDevicesV2({
    pathParams: { projectId },
    filters: {
      device_ids: ancestorDeviceIds,
    },
    queryOptions: {
      enabled: ancestorDeviceIds.length > 0,
    },
  })

  const projectMapBounds = useMemo(() => {
    const bounds = allCombiners
      .map((device) => getPolygonBounds(device.polygon))
      .filter((bound): bound is MapBounds => bound !== null)

    if (bounds.length === 0) return null

    return {
      west: Math.min(...bounds.map((bound) => bound.west)),
      south: Math.min(...bounds.map((bound) => bound.south)),
      east: Math.max(...bounds.map((bound) => bound.east)),
      north: Math.max(...bounds.map((bound) => bound.north)),
    }
  }, [allCombiners])

  // Calculate bounds for the map focused on the parent combiner
  const mapBounds = useMemo(() => {
    return getPolygonBounds(parentCombiner?.polygon)
  }, [parentCombiner?.polygon])

  const eventLocation = useMemo<[number, number] | null>(() => {
    const dcFieldPoint = getPointCoordinates(dcField?.point)
    if (dcFieldPoint) return dcFieldPoint

    const dcFieldBounds = getPolygonBounds(dcField?.polygon)
    if (dcFieldBounds) return getBoundsCenter(dcFieldBounds)

    const ancestorsById = new Map(
      ancestorDevices.data?.map((ancestor) => [ancestor.device_id, ancestor]),
    )
    for (const ancestorDeviceId of ancestorDeviceIds) {
      const ancestor = ancestorsById.get(ancestorDeviceId)
      const ancestorPoint = getPointCoordinates(ancestor?.point)
      if (ancestorPoint) return ancestorPoint

      const ancestorBounds = getPolygonBounds(ancestor?.polygon)
      if (ancestorBounds) return getBoundsCenter(ancestorBounds)
    }

    return null
  }, [ancestorDeviceIds, ancestorDevices.data, dcField])

  const [viewState, setViewState] = useState({
    longitude: 0,
    latitude: 0,
    zoom: 15,
    pitch: 0,
    bearing: 0,
  })

  // Start at the full project, then animate into the event's device location.
  useEffect(() => {
    if (!isMapLoaded || hasFocusedEventRef.current || !eventLocation) {
      return
    }

    hasFocusedEventRef.current = true

    if (projectMapBounds) {
      mapRef.current?.fitBounds(
        [
          projectMapBounds.west,
          projectMapBounds.south,
          projectMapBounds.east,
          projectMapBounds.north,
        ],
        { duration: 0, padding: 35 },
      )
    }

    const timeoutId = window.setTimeout(() => {
      if (mapBounds) {
        mapRef.current?.fitBounds(
          [mapBounds.west, mapBounds.south, mapBounds.east, mapBounds.north],
          {
            duration: FOCUS_ANIMATION_DURATION_MS,
            maxZoom: EVENT_FOCUS_ZOOM,
            padding: 80,
          },
        )
        return
      }

      mapRef.current?.flyTo({
        center: eventLocation,
        duration: FOCUS_ANIMATION_DURATION_MS,
        essential: true,
        zoom: EVENT_FOCUS_ZOOM,
      })
    }, 350)

    return () => window.clearTimeout(timeoutId)
  }, [eventLocation, isMapLoaded, mapBounds, projectMapBounds])

  const onHover = useCallback((event: MapMouseEvent) => {
    const {
      features,
      point: { x, y },
    } = event

    const hoveredFeature = features?.[0]
    setHoverInfo({ feature: hoveredFeature || null, x, y })
  }, [])

  const onAnomalyClick = useCallback(
    (anomalyUuid: string) => {
      if (!relevantAnomalies) return

      const anomaly = relevantAnomalies.find(
        (a) => a.anomaly_uuid === anomalyUuid,
      )
      if (!anomaly) return

      const irUrl = anomaly.ir_image_url || null
      const rgbUrl = anomaly.rgb_image_url || null
      if (!irUrl && !rgbUrl) return

      setImageModalData({ irUrl, rgbUrl, anomaly })
      setImageModalOpen(true)
    },
    [relevantAnomalies],
  )

  // Show loader while devices or event are still loading
  if (!dcFieldInfo && devicesLoading) {
    return (
      <Card
        withBorder
        p="md"
        h="100%"
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <Loader size="lg" />
      </Card>
    )
  }

  if (!dcFieldInfo?.parentCombiner) {
    return (
      <Card withBorder p="md" h="100%">
        <Text c="dimmed">
          No parent DC Combiner found for this DC Field event.
        </Text>
      </Card>
    )
  }

  if (!relevantAnomalies && !anomaliesLoading) {
    return (
      <Card withBorder p="md" h="100%">
        <Text c="dimmed">No drone anomaly data available for this event.</Text>
      </Card>
    )
  }

  return (
    <>
      <Card
        withBorder
        p={0}
        h="100%"
        style={{ position: 'relative', overflow: 'hidden' }}
      >
        {/* Map fills the entire card */}
        <Box
          style={{ width: '100%', height: '100%', position: 'relative' }}
          onMouseLeave={() => setHoverInfo({ feature: null, x: 0, y: 0 })}
        >
          {/* High-level Stats - positioned over the map */}
          <Box
            style={{
              position: 'absolute',
              top: 16,
              left: 16,
              right: 16,
              zIndex: 5,
            }}
          >
            <Card
              withBorder
              p="sm"
              style={{
                backgroundColor:
                  computedColorScheme === 'dark'
                    ? 'rgba(37, 38, 43, 0.95)'
                    : 'rgba(255, 255, 255, 0.95)',
              }}
            >
              <Grid gutter="xs" align="center">
                <Grid.Col
                  span={{ base: 12, md: 4 }}
                  style={{ textAlign: 'center' }}
                >
                  <Stack gap={4} align="center">
                    <Text fw={700}>Anomalies Detected</Text>
                    <Text size="lg" fw={700}>
                      {(relevantAnomalies?.length || 0).toLocaleString()}
                    </Text>
                    <Text size="xs" c="dimmed" ta="center">
                      Within {dcFieldInfo?.parentCombiner?.name_long}
                    </Text>
                  </Stack>
                </Grid.Col>
                <Grid.Col
                  span={{ base: 12, md: 4 }}
                  style={{ textAlign: 'center' }}
                >
                  <Stack gap={4} align="center">
                    <Text fw={700}>Total DC Power Loss</Text>
                    <Text size="lg" fw={700}>
                      {(
                        relevantAnomalies?.reduce(
                          (sum, a) => sum + (a.power_loss_kw || 0),
                          0,
                        ) || 0
                      ).toFixed(2)}{' '}
                      kW DC
                    </Text>
                    {totalDcCombinerCapacity > 0 && relevantAnomalies && (
                      <Text size="xs" c="dimmed" ta="center">
                        {(
                          (relevantAnomalies.reduce(
                            (sum, a) => sum + (a.power_loss_kw || 0),
                            0,
                          ) /
                            totalDcCombinerCapacity) *
                          100
                        ).toFixed(1)}
                        % of DC Combiner Capacity
                      </Text>
                    )}
                  </Stack>
                </Grid.Col>
                <Grid.Col
                  span={{ base: 12, md: 4 }}
                  style={{ textAlign: 'center' }}
                >
                  <Stack gap={4} align="center">
                    <Text fw={700}>Event Start Date</Text>
                    <Text size="lg" fw={700}>
                      {event?.time_start
                        ? new Date(event.time_start).toLocaleDateString()
                        : 'N/A'}
                    </Text>
                    <Text size="xs" c="dimmed" ta="center">
                      When event was detected
                    </Text>
                  </Stack>
                </Grid.Col>
              </Grid>
            </Card>
          </Box>
          {anomaliesLoading && (
            <Box
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                zIndex: 10,
                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                padding: '16px',
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
              }}
            >
              <Group gap="sm">
                <Loader size="sm" />
                <Text size="sm">Loading anomalies...</Text>
              </Group>
            </Box>
          )}
          <MapboxMap
            {...viewState}
            ref={mapRef}
            onLoad={() => setIsMapLoaded(true)}
            onMove={(evt) => setViewState(evt.viewState)}
            onClick={(evt) => {
              const feature = (evt as MapMouseEvent & { features?: Feature[] })
                .features?.[0]
              const anomalyUuid = feature?.properties?.anomaly_uuid
              if (anomalyUuid) {
                onAnomalyClick(anomalyUuid)
              }
            }}
            style={{ width: '100%', height: '100%' }}
            mapStyle={
              gisUtils.mapStyle({
                empty: false,
                satellite: false,
                theme: computedColorScheme,
              }) ?? blankMapStyle
            }
            mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
            interactiveLayerIds={['anomaly-points', 'combiner-polygon']}
            onMouseMove={onHover}
            onMouseLeave={() => setHoverInfo({ feature: null, x: 0, y: 0 })}
          >
            {/* Combiner Polygon */}
            {combinerGeoJSON && (
              <Source id="combiner-data" type="geojson" data={combinerGeoJSON}>
                <Layer
                  id="combiner-polygon"
                  type="fill"
                  paint={{
                    'fill-color': [
                      'case',
                      ['get', 'isParent'],
                      '#ff7f0e', // Orange for parent combiner
                      '#cccccc', // Grey for other combiners
                    ],
                    'fill-opacity': [
                      'case',
                      ['get', 'isParent'],
                      0.4, // More opaque for parent
                      0.1, // Very faded for others
                    ],
                  }}
                />
                <Layer
                  id="combiner-outline"
                  type="line"
                  paint={{
                    'line-color': [
                      'case',
                      ['get', 'isParent'],
                      '#ff7f0e', // Orange for parent combiner
                      '#999999', // Grey for other combiners
                    ],
                    'line-width': [
                      'case',
                      ['get', 'isParent'],
                      3, // Thicker line for parent
                      1, // Thinner line for others
                    ],
                    'line-opacity': [
                      'case',
                      ['get', 'isParent'],
                      0.8, // Full opacity for parent
                      0.3, // Faded for others
                    ],
                  }}
                />
              </Source>
            )}

            {/* Anomaly Points */}
            {anomalyGeoJSON && (
              <Source id="anomaly-data" type="geojson" data={anomalyGeoJSON}>
                <Layer
                  id="anomaly-points"
                  type="circle"
                  layout={{
                    'circle-sort-key': ['get', 'power_loss_kw'],
                  }}
                  paint={{
                    'circle-radius': [
                      'interpolate',
                      ['linear'],
                      ['get', 'power_loss_kw'],
                      0,
                      6,
                      1,
                      8,
                      5,
                      12,
                    ],
                    'circle-color': [
                      'case',
                      [
                        '==',
                        ['get', 'remediation_category'],
                        'Remediation Recommended',
                      ],
                      '#fa5252',
                      [
                        '==',
                        ['get', 'remediation_category'],
                        'Long Term Monitoring',
                      ],
                      '#fd7e14',
                      '#51cf66',
                    ],
                    'circle-stroke-width': 2,
                    'circle-stroke-color': '#ffffff',
                    'circle-opacity': 0.9,
                    'circle-stroke-opacity': 1.0,
                  }}
                />
              </Source>
            )}

            {eventLocation && (
              <Marker
                key="event-location-flag"
                longitude={eventLocation[0]}
                latitude={eventLocation[1]}
                anchor="bottom"
              >
                <IconFlag color="#e03131" fill="#e03131" />
              </Marker>
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
                {hoverInfo.feature.properties?.anomaly_uuid ? (
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
                      RGB: {hoverInfo.feature.properties.rgb_signal}
                    </Text>
                    <Text size="xs">
                      DC Power Loss:{' '}
                      {hoverInfo.feature.properties.power_loss_kw?.toFixed(2)}{' '}
                      kW
                    </Text>
                    <Text size="xs">
                      Category:{' '}
                      {hoverInfo.feature.properties.remediation_category}
                    </Text>
                  </>
                ) : (
                  <>
                    <Text size="sm" fw={600}>
                      {hoverInfo.feature.properties?.name}
                    </Text>
                    <Text size="xs">
                      DC Combiner
                      {hoverInfo.feature.properties?.isParent && (
                        <Badge size="xs" color="orange" ml="xs">
                          Parent
                        </Badge>
                      )}
                    </Text>
                  </>
                )}
              </div>
            )}

            <Attribution />
          </MapboxMap>
        </Box>
      </Card>

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
            </Stack>
          </Stack>
        )}
      </Modal>
    </>
  )
}

export default DcFieldAnomaliesMap
