import { DeviceTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
import { useGetDevice, useGetDevicesV2 } from '@/hooks/api'
import * as gisUtils from '@/utils/GIS'
import {
  Box,
  LoadingOverlay,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { IconDatabaseOff, IconFlag } from '@tabler/icons-react'
import { FeatureCollection, Geometry } from 'geojson'
import { useContext, useEffect, useMemo, useRef, useState } from 'react'
import MapboxMap, { Layer, MapRef, Marker, Source } from 'react-map-gl/mapbox'
import { useParams } from 'react-router'

import { MapSettings } from './GIS'

interface EventGISCardProps {
  deviceId: string | number
  additionalGeoJson?: FeatureCollection
  animateToDevice?: boolean
  zoom?: number
}

const useProjectId = () => useParams().projectId || '-1'
const EVENT_FOCUS_ZOOM = 17
const FOCUS_ANIMATION_DURATION_MS = 1800

type LngLat = [number, number]
type Bounds = [number, number, number, number]
type LocationDevice = {
  device_id: number
  name_long?: string | null
  point?: { coordinates: number[] } | null
  polygon?: unknown
}

const isLngLat = (value: number[] | undefined): value is LngLat =>
  Array.isArray(value) &&
  value.length >= 2 &&
  Number.isFinite(value[0]) &&
  Number.isFinite(value[1])

const collectLngLats = (coordinates: unknown): LngLat[] => {
  if (!Array.isArray(coordinates)) return []

  if (
    typeof coordinates[0] === 'number' &&
    typeof coordinates[1] === 'number'
  ) {
    return isLngLat(coordinates as number[]) ? [coordinates as LngLat] : []
  }

  return coordinates.flatMap((coord) => collectLngLats(coord))
}

const parseGeometry = (geometry: unknown): Geometry | null => {
  if (!geometry) return null

  let parsedGeometry = geometry
  if (typeof geometry === 'string') {
    try {
      parsedGeometry = JSON.parse(geometry)
    } catch {
      return null
    }
  }

  if (
    !parsedGeometry ||
    typeof parsedGeometry !== 'object' ||
    !('type' in parsedGeometry)
  ) {
    return null
  }

  return parsedGeometry as Geometry
}

const getGeometryBounds = (geometry: unknown) => {
  const parsedGeometry = parseGeometry(geometry)
  if (!parsedGeometry) return null

  const lngLats =
    parsedGeometry.type === 'Point'
      ? isLngLat(parsedGeometry.coordinates)
        ? [parsedGeometry.coordinates]
        : []
      : 'coordinates' in parsedGeometry
        ? collectLngLats(parsedGeometry.coordinates)
        : []

  if (lngLats.length === 0) return null

  const lngs = lngLats.map(([lng]) => lng)
  const lats = lngLats.map(([, lat]) => lat)

  return [
    Math.min(...lngs),
    Math.min(...lats),
    Math.max(...lngs),
    Math.max(...lats),
  ] satisfies Bounds
}

const getBoundsCenter = (bounds: Bounds): LngLat => [
  (bounds[0] + bounds[2]) / 2,
  (bounds[1] + bounds[3]) / 2,
]

const getFeatureCollectionBounds = (
  featureCollection: FeatureCollection,
): Bounds | null => {
  const bounds = featureCollection.features
    .map((feature) => getGeometryBounds(feature.geometry))
    .filter((bound): bound is Bounds => bound !== null)

  if (bounds.length === 0) return null

  return [
    Math.min(...bounds.map((bound) => bound[0])),
    Math.min(...bounds.map((bound) => bound[1])),
    Math.max(...bounds.map((bound) => bound[2])),
    Math.max(...bounds.map((bound) => bound[3])),
  ]
}

const getDeviceBounds = (device: LocationDevice | null | undefined) =>
  getGeometryBounds(device?.polygon)

const getDeviceCoordinates = (
  device: LocationDevice | null | undefined,
  bounds: Bounds | null,
): LngLat | null => {
  if (device?.point && isLngLat(device.point.coordinates)) {
    return device.point.coordinates
  }

  if (bounds) {
    return getBoundsCenter(bounds)
  }

  return null
}

const EventGISCard = ({
  deviceId,
  additionalGeoJson,
  animateToDevice = false,
  zoom,
}: EventGISCardProps) => {
  const projectId = useProjectId()
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('dark')
  const context = useContext(GISContext)
  const blankMapStyle = gisUtils.useBlankMapStyle()
  const mapRef = useRef<MapRef>(null)
  const lastFocusedDeviceIdRef = useRef<string | number | null>(null)
  const [isMapLoaded, setIsMapLoaded] = useState(false)

  const {
    data: deviceData,
    isLoading: isDeviceLoading,
    error: deviceError,
  } = useGetDevice({
    pathParams: { projectId, deviceId: deviceId.toString() },
  })

  const { isLoading: isProjectLoading, error: projectError } = useSelectProject(
    projectId!,
  )

  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [
        DeviceTypeEnum.PV_BLOCK,
        DeviceTypeEnum.BESS_ENCLOSURE,
        DeviceTypeEnum.BESS_PCS,
      ],
    },
  })

  const ancestorDeviceIds = useMemo(() => {
    const pathIds = deviceData?.device_id_path
      ?.split('.')
      .map((pathDeviceId) => Number(pathDeviceId))
      .filter((pathDeviceId) => Number.isFinite(pathDeviceId))

    if (pathIds?.length) {
      return pathIds
        .filter((pathDeviceId) => pathDeviceId !== deviceData?.device_id)
        .reverse()
    }

    return deviceData?.parent_device_id ? [deviceData.parent_device_id] : []
  }, [
    deviceData?.device_id,
    deviceData?.device_id_path,
    deviceData?.parent_device_id,
  ])

  const ancestorDevices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_ids: ancestorDeviceIds,
    },
    queryOptions: {
      enabled: ancestorDeviceIds.length > 0,
    },
  })

  const deviceBounds = useMemo(() => getDeviceBounds(deviceData), [deviceData])

  const locationDevice = useMemo<LocationDevice | null>(() => {
    const deviceCoordinates = getDeviceCoordinates(deviceData, deviceBounds)
    if (deviceCoordinates) return deviceData ?? null

    const ancestorsById = new Map(
      ancestorDevices.data?.map((ancestor) => [ancestor.device_id, ancestor]),
    )
    for (const ancestorDeviceId of ancestorDeviceIds) {
      const ancestor = ancestorsById.get(ancestorDeviceId)
      const ancestorBounds = getDeviceBounds(ancestor)
      const ancestorCoordinates = getDeviceCoordinates(ancestor, ancestorBounds)
      if (ancestorCoordinates) return ancestor ?? null
    }
    return null
  }, [ancestorDeviceIds, ancestorDevices.data, deviceBounds, deviceData])

  const locationBounds = useMemo(
    () => getDeviceBounds(locationDevice),
    [locationDevice],
  )
  const coordinates = useMemo(
    () => getDeviceCoordinates(locationDevice, locationBounds),
    [locationBounds, locationDevice],
  )

  const isLoading =
    isDeviceLoading ||
    devices.isLoading ||
    isProjectLoading ||
    ancestorDevices.isLoading
  const isError =
    deviceError || projectError || devices.isError || ancestorDevices.isError

  const showLabels = context?.showLabels ?? false
  const showSatellite = context?.showSatellite ?? false

  const getGoogleMapsDirectionsUrl = () => {
    if (!coordinates) return null

    const destination = `${coordinates[1]},${coordinates[0]}`
    return (
      'https://www.google.com/maps/dir/?api=1' +
      `&destination=${destination}&travelmode=driving`
    )
  }

  const handleLeftClick = (event: React.MouseEvent) => {
    event.preventDefault()
    event.stopPropagation()

    const directionsUrl = getGoogleMapsDirectionsUrl()
    if (directionsUrl) {
      window.open(directionsUrl, '_blank')
    }
  }

  const filteredData: FeatureCollection = {
    type: 'FeatureCollection',
    features:
      devices.data?.flatMap((device) => {
        const geometry = parseGeometry(device.polygon)
        if (!geometry) return []

        return [
          {
            type: 'Feature' as const,
            geometry,
            properties: {
              name: device.name_long,
            },
          },
        ]
      }) ?? [],
  }

  const locationPolygon = useMemo(
    () => parseGeometry(locationDevice?.polygon),
    [locationDevice?.polygon],
  )
  const locationName = locationDevice?.name_long
  const eventDeviceData: FeatureCollection | null = locationPolygon
    ? {
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature' as const,
            geometry: locationPolygon,
            properties: {
              name: locationName,
            },
          },
        ],
      }
    : null
  const projectBounds = getFeatureCollectionBounds(filteredData)
  const initialViewState = zoom
    ? coordinates
      ? { longitude: coordinates[0], latitude: coordinates[1], zoom }
      : undefined
    : projectBounds
      ? {
          bounds: projectBounds,
          fitBoundsOptions: { padding: 35 },
        }
      : coordinates
        ? {
            longitude: coordinates[0],
            latitude: coordinates[1],
            zoom: EVENT_FOCUS_ZOOM - 2,
          }
        : undefined

  useEffect(() => {
    if (
      !animateToDevice ||
      !isMapLoaded ||
      !coordinates ||
      lastFocusedDeviceIdRef.current === deviceId
    ) {
      return
    }

    lastFocusedDeviceIdRef.current = deviceId

    const timeoutId = window.setTimeout(() => {
      if (locationBounds) {
        mapRef.current?.fitBounds(locationBounds, {
          duration: FOCUS_ANIMATION_DURATION_MS,
          maxZoom: zoom ?? EVENT_FOCUS_ZOOM,
          padding: 80,
        })
        return
      }

      mapRef.current?.flyTo({
        center: coordinates,
        duration: FOCUS_ANIMATION_DURATION_MS,
        essential: true,
        zoom: zoom ?? EVENT_FOCUS_ZOOM,
      })
    }, 350)

    return () => window.clearTimeout(timeoutId)
  }, [
    animateToDevice,
    coordinates,
    deviceId,
    isMapLoaded,
    locationBounds,
    zoom,
  ])

  if (!context) {
    throw new Error('GISContext is not provided')
  }
  if (isLoading) {
    return <LoadingOverlay visible={true} />
  }
  if (isError) {
    return <IconDatabaseOff size={48} strokeWidth={1} />
  }

  return (
    <div
      style={{
        position: 'relative',
        height: '100%',
        width: '100%',
      }}
    >
      <MapboxMap
        ref={mapRef}
        initialViewState={initialViewState}
        onLoad={() => setIsMapLoaded(true)}
        style={{
          borderBottomLeftRadius: 'inherit',
          borderBottomRightRadius: 'inherit',
        }}
        mapStyle={
          gisUtils.mapStyle({
            satellite: showSatellite,
            theme: computedColorScheme,
          }) ?? blankMapStyle
        }
        mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
      >
        {additionalGeoJson && (
          <Source id="trackers" type="geojson" data={additionalGeoJson}>
            <Layer
              id="trackers-fill"
              type="fill"
              paint={{
                'fill-color': theme.colors.gray[9],
                'fill-opacity': 1,
              }}
            />
            <Layer
              id="trackers-line"
              type="line"
              paint={{
                'line-color': theme.colors.gray[9],
                'line-width': 1,
              }}
            />
            {showLabels && (
              <Layer
                {...gisUtils.layerLabel({
                  textField: 'name',
                  textRotate: -90, // Rotate labels 90 degrees like in tracker-block-gis
                })}
                id="trackers-labels"
              />
            )}
          </Source>
        )}
        <Source id="data" type="geojson" data={filteredData}>
          <Layer
            id="data"
            type="fill"
            paint={{
              'fill-color': theme.colors.gray[5], // Custom fill color
              'fill-opacity': 0.7,
            }}
          />
          {showLabels && (
            <Layer {...gisUtils.layerLabel({ textField: 'name' })} />
          )}
        </Source>
        {eventDeviceData && (
          <Source id="event-device" type="geojson" data={eventDeviceData}>
            <Layer
              id="event-device-fill"
              type="fill"
              paint={{
                'fill-color': theme.colors.red[6],
                'fill-opacity': 0.2,
              }}
            />
            <Layer
              id="event-device-outline"
              type="line"
              paint={{
                'line-color': theme.colors.red[7],
                'line-width': 3,
              }}
            />
          </Source>
        )}
        {coordinates && (
          <Marker
            key="event-location-flag"
            longitude={coordinates[0]}
            latitude={coordinates[1]}
            anchor="bottom"
          >
            <div onClick={handleLeftClick} style={{ cursor: 'pointer' }}>
              <IconFlag
                color={theme.colors.red[7]}
                fill={theme.colors.red[7]}
                style={{ pointerEvents: 'auto' }}
              />
            </div>
          </Marker>
        )}
      </MapboxMap>
      <Box
        style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 1 }}
        p="md"
      >
        <MapSettings />
      </Box>
      <Attribution />
    </div>
  )
}

export default EventGISCard
