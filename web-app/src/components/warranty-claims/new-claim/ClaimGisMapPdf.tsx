import { type Device } from '@/hooks/types'
import { mapStyle } from '@/utils/GIS'
import type { Feature, FeatureCollection, Geometry, Position } from 'geojson'
import html2canvas from 'html2canvas-pro'
import jsPDF from 'jspdf'
import {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react'
import MapboxMap, { Layer, type MapRef, Source } from 'react-map-gl/mapbox'

import { type DeviceEntry } from './devices'

const LEGACY_WARRANTY_CLAIM_GIS_MAP_FILENAME = 'warranty-claim-gis-map.pdf'
const WARRANTY_CLAIM_GIS_MAP_FILENAME_PATTERN =
  /^warranty-claim-(?:\d+|pending)-\d{4}-\d{2}-\d{2}-gis-map\.pdf$/

export function isWarrantyClaimGisMapFilename(filename: string): boolean {
  return (
    filename === LEGACY_WARRANTY_CLAIM_GIS_MAP_FILENAME ||
    WARRANTY_CLAIM_GIS_MAP_FILENAME_PATTERN.test(filename)
  )
}

function buildWarrantyClaimGisMapFilename(claimId: number | null): string {
  const claimPart = claimId == null ? 'pending' : String(claimId)
  const datePart = new Date().toISOString().slice(0, 10)
  return `warranty-claim-${claimPart}-${datePart}-gis-map.pdf`
}

export interface ClaimGisMapPdfHandle {
  createPdfFile: (claimIdOverride?: number | null) => Promise<File | null>
}

type ClaimGisMapPdfProps = {
  enabled: boolean
  projectName: string
  claimId: number | null
  oemName: string
  summary: string
  selectedDevices: DeviceEntry[]
  selectedDeviceDetails: Device[]
  selectedDeviceAncestorDetails: Device[]
  selectedEvents: ClaimMapEvent[]
  siteDevices: Device[]
  projectPolygon: unknown
}

type ClaimMapEvent = {
  event_id: number
  device_id: number
  location_point?: unknown
}

type DeviceFeatureProperties = {
  deviceId: number
  selected: boolean
  label: string
}

type ClaimMapMarker = {
  deviceId: number
  number: number
  devicePosition: { x: number; y: number }
  markerPosition: { x: number; y: number }
}

type ScreenRect = {
  minX: number
  minY: number
  maxX: number
  maxY: number
}

const PDF_WIDTH = 1100
const PDF_HEIGHT = 850
const MAP_HEIGHT = 560
const CLAIM_MAP_MARKER_SIZE = 24
const CLAIM_MAP_MARKER_MARGIN = 6
const MAP_IDLE_TIMEOUT_MS = 4000
const PDF_JPEG_QUALITY = 0.82

function parseGeometry(geometry: unknown): Geometry | null {
  if (!geometry) return null
  const parsed =
    typeof geometry === 'string' ? parseJsonGeometry(geometry) : geometry
  if (!parsed || typeof parsed !== 'object') return null

  const candidate = parsed as Geometry
  if (
    candidate.type === 'Point' ||
    candidate.type === 'Polygon' ||
    candidate.type === 'MultiPolygon'
  ) {
    return candidate
  }

  return null
}

function parseJsonGeometry(value: string): unknown {
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

function geometryHasCoordinates(geometry: Geometry | null): boolean {
  if (!geometry || geometry.type === 'GeometryCollection') return false
  return geometry.coordinates.length > 0
}

function getDeviceGeometry(device: Device | undefined): Geometry | null {
  const polygon = parseGeometry(device?.polygon)
  if (geometryHasCoordinates(polygon)) return polygon

  const point = parseGeometry(device?.point)
  if (geometryHasCoordinates(point)) return point

  return null
}

function getDeviceGeometryWithAncestors(
  device: Device | undefined,
  devicesById: Map<number, Device>,
): Geometry | null {
  const deviceGeometry = getDeviceGeometry(device)
  if (deviceGeometry || !device?.parent_device_id) return deviceGeometry

  const visitedDeviceIds = new Set([device.device_id])
  let parentDevice = devicesById.get(device.parent_device_id)
  while (parentDevice && !visitedDeviceIds.has(parentDevice.device_id)) {
    const parentGeometry = getDeviceGeometry(parentDevice)
    if (parentGeometry) return parentGeometry

    visitedDeviceIds.add(parentDevice.device_id)
    parentDevice = parentDevice.parent_device_id
      ? devicesById.get(parentDevice.parent_device_id)
      : undefined
  }

  return null
}

function walkPositions(
  geometry: Geometry,
  visitPosition: (position: Position) => void,
) {
  if (geometry.type === 'Point') {
    visitPosition(geometry.coordinates)
    return
  }

  if (geometry.type === 'Polygon') {
    geometry.coordinates.forEach((ring) => ring.forEach(visitPosition))
    return
  }

  if (geometry.type === 'MultiPolygon') {
    geometry.coordinates.forEach((polygon) =>
      polygon.forEach((ring) => ring.forEach(visitPosition)),
    )
  }
}

function geometryAnchor(geometry: Geometry): [number, number] | null {
  if (geometry.type === 'Point') {
    const [lng, lat] = geometry.coordinates
    return [lng, lat]
  }

  let lngSum = 0
  let latSum = 0
  let count = 0
  walkPositions(geometry, ([lng, lat]) => {
    lngSum += lng
    latSum += lat
    count += 1
  })

  if (count === 0) return null
  return [lngSum / count, latSum / count]
}

function geometryBounds(
  geometries: Geometry[],
  {
    minPadding = 0.00005,
    paddingRatio = 0.03,
  }: { minPadding?: number; paddingRatio?: number } = {},
): [number, number, number, number] | undefined {
  let minLng = Infinity
  let minLat = Infinity
  let maxLng = -Infinity
  let maxLat = -Infinity

  geometries.forEach((geometry) => {
    walkPositions(geometry, ([lng, lat]) => {
      minLng = Math.min(minLng, lng)
      minLat = Math.min(minLat, lat)
      maxLng = Math.max(maxLng, lng)
      maxLat = Math.max(maxLat, lat)
    })
  })

  if (!Number.isFinite(minLng)) return undefined

  const lngPad = Math.max((maxLng - minLng) * paddingRatio, minPadding)
  const latPad = Math.max((maxLat - minLat) * paddingRatio, minPadding)
  return [minLng - lngPad, minLat - latPad, maxLng + lngPad, maxLat + latPad]
}

function screenRectForCenter(
  center: { x: number; y: number },
  size: number,
): ScreenRect {
  const halfSize = size / 2
  return {
    minX: center.x - halfSize,
    minY: center.y - halfSize,
    maxX: center.x + halfSize,
    maxY: center.y + halfSize,
  }
}

function expandScreenRect(rect: ScreenRect, padding: number): ScreenRect {
  return {
    minX: rect.minX - padding,
    minY: rect.minY - padding,
    maxX: rect.maxX + padding,
    maxY: rect.maxY + padding,
  }
}

function screenRectsOverlap(a: ScreenRect, b: ScreenRect): boolean {
  return (
    a.minX < b.maxX && a.maxX > b.minX && a.minY < b.maxY && a.maxY > b.minY
  )
}

function geometryScreenBounds(
  geometry: Geometry,
  project: (position: [number, number]) => { x: number; y: number },
): ScreenRect | null {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity

  walkPositions(geometry, ([lng, lat]) => {
    const point = project([lng, lat])
    minX = Math.min(minX, point.x)
    minY = Math.min(minY, point.y)
    maxX = Math.max(maxX, point.x)
    maxY = Math.max(maxY, point.y)
  })

  if (!Number.isFinite(minX)) return null
  return { minX, minY, maxX, maxY }
}

function buildMarkerCandidatePositions(anchor: { x: number; y: number }) {
  const radii = [22, 34, 46, 58, 76, 96]
  const angles = [
    -Math.PI / 2,
    -Math.PI / 4,
    0,
    Math.PI / 4,
    Math.PI / 2,
    (Math.PI * 3) / 4,
    Math.PI,
    (-Math.PI * 3) / 4,
  ]
  const positions = [{ x: anchor.x, y: anchor.y }]

  radii.forEach((radius) => {
    angles.forEach((angle) => {
      positions.push({
        x: anchor.x + Math.cos(angle) * radius,
        y: anchor.y + Math.sin(angle) * radius,
      })
    })
  })

  return positions
}

function keepMarkerInMap(
  marker: { x: number; y: number },
  mapSize: { width: number; height: number },
) {
  const halfSize = CLAIM_MAP_MARKER_SIZE / 2
  return {
    x: Math.min(Math.max(marker.x, halfSize), mapSize.width - halfSize),
    y: Math.min(Math.max(marker.y, halfSize), mapSize.height - halfSize),
  }
}

function chooseClaimMapMarkerPosition({
  anchor,
  mapSize,
  occupiedRects,
  polygonRects,
}: {
  anchor: { x: number; y: number }
  mapSize: { width: number; height: number }
  occupiedRects: ScreenRect[]
  polygonRects: ScreenRect[]
}) {
  const candidates = buildMarkerCandidatePositions(anchor).map((candidate) =>
    keepMarkerInMap(candidate, mapSize),
  )

  return (
    candidates.find((candidate) => {
      const rect = expandScreenRect(
        screenRectForCenter(candidate, CLAIM_MAP_MARKER_SIZE),
        CLAIM_MAP_MARKER_MARGIN,
      )
      return ![...occupiedRects, ...polygonRects].some((obstacle) =>
        screenRectsOverlap(rect, obstacle),
      )
    }) ??
    candidates.find((candidate) => {
      const rect = expandScreenRect(
        screenRectForCenter(candidate, CLAIM_MAP_MARKER_SIZE),
        CLAIM_MAP_MARKER_MARGIN,
      )
      return !occupiedRects.some((obstacle) =>
        screenRectsOverlap(rect, obstacle),
      )
    }) ??
    candidates[0]
  )
}

function createDeviceFeature(
  device: Device,
  selected: boolean,
): Feature<Geometry, DeviceFeatureProperties> | null {
  const geometry = getDeviceGeometry(device)
  if (!geometry) return null

  return {
    type: 'Feature',
    properties: {
      deviceId: device.device_id,
      selected,
      label:
        device.name_long || device.name_short || `Device ${device.device_id}`,
    },
    geometry,
  }
}

function createSelectedDeviceFeature({
  selectedDevice,
  device,
  event,
  devicesById,
}: {
  selectedDevice: DeviceEntry
  device: Device | undefined
  event: ClaimMapEvent | undefined
  devicesById: Map<number, Device>
}): Feature<Geometry, DeviceFeatureProperties> | null {
  const geometry =
    getDeviceGeometryWithAncestors(device, devicesById) ??
    parseGeometry(event?.location_point)
  if (!geometry) return null

  return {
    type: 'Feature',
    properties: {
      deviceId: selectedDevice.device_id,
      selected: true,
      label: selectedDevice.device_name,
    },
    geometry,
  }
}

function buildDetailLines(device: DeviceEntry): string[] {
  return [
    device.oem_serial_number ? `Serial: ${device.oem_serial_number}` : null,
    device.oem_part_number ? `Part: ${device.oem_part_number}` : null,
    device.event_id != null ? `Event: ${device.event_id}` : null,
  ].filter((line): line is string => line != null)
}

const ClaimGisMapPdf = forwardRef<ClaimGisMapPdfHandle, ClaimGisMapPdfProps>(
  function ClaimGisMapPdf(
    {
      enabled,
      projectName,
      claimId,
      oemName,
      summary,
      selectedDevices,
      selectedDeviceDetails,
      selectedDeviceAncestorDetails,
      selectedEvents,
      siteDevices,
      projectPolygon,
    },
    ref,
  ) {
    const captureRef = useRef<HTMLDivElement>(null)
    const mapRef = useRef<MapRef>(null)
    const idleResolversRef = useRef<(() => void)[]>([])
    const [mapIdle, setMapIdle] = useState(false)
    const [claimMapMarkers, setClaimMapMarkers] = useState<ClaimMapMarker[]>([])

    const selectedDetailsById = useMemo(
      () => new Map(selectedDeviceDetails.map((d) => [d.device_id, d])),
      [selectedDeviceDetails],
    )

    const siteDetailsById = useMemo(
      () => new Map(siteDevices.map((d) => [d.device_id, d])),
      [siteDevices],
    )

    const devicesById = useMemo(
      () =>
        new Map(
          [
            ...siteDevices,
            ...selectedDeviceAncestorDetails,
            ...selectedDeviceDetails,
          ].map((d) => [d.device_id, d]),
        ),
      [selectedDeviceAncestorDetails, selectedDeviceDetails, siteDevices],
    )

    const selectedEventsById = useMemo(
      () => new Map(selectedEvents.map((event) => [event.event_id, event])),
      [selectedEvents],
    )

    const selectedEventsByDeviceId = useMemo(
      () => new Map(selectedEvents.map((event) => [event.device_id, event])),
      [selectedEvents],
    )

    const selectedGeometryByDeviceId = useMemo(
      () =>
        new Map(
          selectedDevices.map((selectedDevice) => {
            const detail =
              selectedDetailsById.get(selectedDevice.device_id) ??
              siteDetailsById.get(selectedDevice.device_id)
            const event =
              (selectedDevice.event_id != null
                ? selectedEventsById.get(selectedDevice.event_id)
                : undefined) ??
              selectedEventsByDeviceId.get(selectedDevice.device_id)
            return [
              selectedDevice.device_id,
              getDeviceGeometryWithAncestors(detail, devicesById) ??
                parseGeometry(event?.location_point),
            ]
          }),
        ),
      [
        devicesById,
        selectedDetailsById,
        selectedDevices,
        selectedEventsByDeviceId,
        selectedEventsById,
        siteDetailsById,
      ],
    )

    const selectedIds = useMemo(
      () => new Set(selectedDevices.map((device) => device.device_id)),
      [selectedDevices],
    )

    const siteFeatures = useMemo<
      FeatureCollection<Geometry, DeviceFeatureProperties>
    >(
      () => ({
        type: 'FeatureCollection',
        features: siteDevices
          .filter((device) => !selectedIds.has(device.device_id))
          .map((device) => createDeviceFeature(device, false))
          .filter(
            (feature): feature is Feature<Geometry, DeviceFeatureProperties> =>
              feature != null,
          ),
      }),
      [selectedIds, siteDevices],
    )

    const selectedFeatures = useMemo<
      FeatureCollection<Geometry, DeviceFeatureProperties>
    >(
      () => ({
        type: 'FeatureCollection',
        features: selectedDevices
          .map((selectedDevice) => {
            const detail =
              selectedDetailsById.get(selectedDevice.device_id) ??
              siteDetailsById.get(selectedDevice.device_id)
            const event =
              (selectedDevice.event_id != null
                ? selectedEventsById.get(selectedDevice.event_id)
                : undefined) ??
              selectedEventsByDeviceId.get(selectedDevice.device_id)
            return createSelectedDeviceFeature({
              selectedDevice,
              device: detail,
              event,
              devicesById,
            })
          })
          .filter(
            (feature): feature is Feature<Geometry, DeviceFeatureProperties> =>
              feature != null,
          ),
      }),
      [
        devicesById,
        selectedDetailsById,
        selectedDevices,
        selectedEventsByDeviceId,
        selectedEventsById,
        siteDetailsById,
      ],
    )

    const parsedProjectPolygon = useMemo(
      () => parseGeometry(projectPolygon),
      [projectPolygon],
    )

    const projectFeature = useMemo<FeatureCollection<Geometry>>(
      () => ({
        type: 'FeatureCollection',
        features: parsedProjectPolygon
          ? [
              {
                type: 'Feature',
                properties: {},
                geometry: parsedProjectPolygon,
              },
            ]
          : [],
      }),
      [parsedProjectPolygon],
    )

    const mappableSelectedDeviceIds = useMemo(
      () =>
        new Set(
          selectedFeatures.features
            .map((feature) => feature.properties?.deviceId)
            .filter((deviceId): deviceId is number => deviceId != null),
        ),
      [selectedFeatures],
    )

    const missingGeometryDevices = useMemo(
      () =>
        selectedDevices.filter(
          (device) => !mappableSelectedDeviceIds.has(device.device_id),
        ),
      [mappableSelectedDeviceIds, selectedDevices],
    )

    const bounds = useMemo(() => {
      const projectGeometries = projectFeature.features.map(
        (feature) => feature.geometry,
      )
      if (projectGeometries.length > 0) {
        return geometryBounds(projectGeometries)
      }

      const siteGeometries = siteFeatures.features.map(
        (feature) => feature.geometry,
      )
      if (siteGeometries.length > 0) {
        return geometryBounds(siteGeometries)
      }

      return geometryBounds(
        selectedFeatures.features.map((feature) => feature.geometry),
        { minPadding: 0.0008, paddingRatio: 0.1 },
      )
    }, [projectFeature, selectedFeatures, siteFeatures])

    const updateClaimMapMarkers = useCallback(() => {
      const map = mapRef.current
      if (!map) return

      const mapElement = map.getMap().getContainer()
      const mapSize = {
        width: mapElement.clientWidth,
        height: mapElement.clientHeight,
      }
      const project = (position: [number, number]) => {
        const projected = map.project(position)
        return { x: projected.x, y: projected.y }
      }
      const selectedPolygonRects = selectedFeatures.features
        .filter((feature) => feature.geometry.type !== 'Point')
        .map((feature) => geometryScreenBounds(feature.geometry, project))
        .filter((rect): rect is ScreenRect => rect != null)
      const occupiedRects: ScreenRect[] = []
      const markers: ClaimMapMarker[] = []

      selectedDevices.forEach((selectedDevice, index) => {
        const geometry = selectedGeometryByDeviceId.get(
          selectedDevice.device_id,
        )
        const anchorPosition = geometry ? geometryAnchor(geometry) : null
        if (!anchorPosition) return

        const devicePosition = project(anchorPosition)
        const markerPosition = chooseClaimMapMarkerPosition({
          anchor: devicePosition,
          mapSize,
          occupiedRects,
          polygonRects: selectedPolygonRects,
        })
        markers.push({
          deviceId: selectedDevice.device_id,
          number: index + 1,
          devicePosition,
          markerPosition,
        })
        occupiedRects.push(
          expandScreenRect(
            screenRectForCenter(markerPosition, CLAIM_MAP_MARKER_SIZE),
            CLAIM_MAP_MARKER_MARGIN,
          ),
        )
      })

      setClaimMapMarkers(markers)
    }, [selectedDevices, selectedFeatures, selectedGeometryByDeviceId])

    const handleMapIdle = useCallback(() => {
      setMapIdle(true)
      updateClaimMapMarkers()
      idleResolversRef.current.splice(0).forEach((resolve) => resolve())
    }, [updateClaimMapMarkers])

    const waitForMapIdle = useCallback(async () => {
      if (mapIdle || selectedFeatures.features.length === 0) return

      await new Promise<void>((resolve) => {
        const timeoutId = window.setTimeout(resolve, MAP_IDLE_TIMEOUT_MS)
        idleResolversRef.current.push(() => {
          window.clearTimeout(timeoutId)
          resolve()
        })
      })
    }, [mapIdle, selectedFeatures.features.length])

    const createPdfFile = useCallback(
      async (claimIdOverride = claimId) => {
        if (!enabled || !captureRef.current || selectedDevices.length === 0) {
          return null
        }

        await waitForMapIdle()
        updateClaimMapMarkers()
        await new Promise((resolve) => window.requestAnimationFrame(resolve))

        const canvas = await html2canvas(captureRef.current, {
          scale: 2,
          useCORS: true,
        })
        const imgData = canvas.toDataURL('image/jpeg', PDF_JPEG_QUALITY)
        const pdf = new jsPDF({
          orientation: 'landscape',
          unit: 'px',
          format: [canvas.width, canvas.height],
        })
        pdf.addImage(imgData, 'JPEG', 0, 0, canvas.width, canvas.height)
        const arrayBuffer = pdf.output('arraybuffer')
        return new File(
          [arrayBuffer],
          buildWarrantyClaimGisMapFilename(claimIdOverride),
          { type: 'application/pdf' },
        )
      },
      [
        claimId,
        enabled,
        selectedDevices.length,
        updateClaimMapMarkers,
        waitForMapIdle,
      ],
    )

    useImperativeHandle(ref, () => ({ createPdfFile }), [createPdfFile])

    if (!enabled) return null

    return (
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          left: -12000,
          top: 0,
          width: PDF_WIDTH,
          height: PDF_HEIGHT,
          pointerEvents: 'none',
          zIndex: -1,
        }}
      >
        <div
          ref={captureRef}
          style={{
            width: PDF_WIDTH,
            height: PDF_HEIGHT,
            background: '#ffffff',
            color: '#1f2937',
            fontFamily: 'Inter, Arial, sans-serif',
            padding: 28,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 28, fontWeight: 700 }}>
                Warranty Claim GIS Map
              </div>
              <div style={{ color: '#4b5563', fontSize: 16, marginTop: 4 }}>
                {projectName}
              </div>
            </div>
            <div style={{ fontSize: 13, textAlign: 'right' }}>
              <div>OEM: {oemName}</div>
              <div>Claim: {claimId ?? 'pending'}</div>
              <div>Generated: {new Date().toLocaleString()}</div>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 280px',
              gap: 18,
              marginTop: 18,
            }}
          >
            <div>
              <div
                style={{
                  position: 'relative',
                  width: '100%',
                  height: MAP_HEIGHT,
                  border: '1px solid #d1d5db',
                  borderRadius: 12,
                  overflow: 'hidden',
                }}
              >
                <MapboxMap
                  ref={mapRef}
                  preserveDrawingBuffer
                  interactive={false}
                  onIdle={handleMapIdle}
                  initialViewState={{
                    bounds,
                    fitBoundsOptions: {
                      padding: {
                        top: 48,
                        bottom: 48,
                        left: 48,
                        right: 48,
                      },
                    },
                    longitude: bounds ? undefined : -98,
                    latitude: bounds ? undefined : 39,
                    zoom: bounds ? undefined : 3,
                  }}
                  mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
                  mapStyle={mapStyle({ theme: 'light' })}
                  style={{ width: '100%', height: '100%' }}
                >
                  <Source
                    id="claim-site-devices"
                    type="geojson"
                    data={siteFeatures}
                  >
                    <Layer
                      id="claim-site-polygons"
                      type="fill"
                      filter={[
                        'any',
                        ['==', ['geometry-type'], 'Polygon'],
                        ['==', ['geometry-type'], 'MultiPolygon'],
                      ]}
                      paint={{
                        'fill-color': '#9ca3af',
                        'fill-opacity': 0.24,
                      }}
                    />
                    <Layer
                      id="claim-site-lines"
                      type="line"
                      filter={[
                        'any',
                        ['==', ['geometry-type'], 'Polygon'],
                        ['==', ['geometry-type'], 'MultiPolygon'],
                      ]}
                      paint={{
                        'line-color': '#6b7280',
                        'line-width': 0.75,
                      }}
                    />
                    <Layer
                      id="claim-site-points"
                      type="circle"
                      filter={['==', ['geometry-type'], 'Point']}
                      paint={{
                        'circle-radius': 3,
                        'circle-color': '#9ca3af',
                        'circle-stroke-color': '#ffffff',
                        'circle-stroke-width': 1,
                      }}
                    />
                  </Source>
                  <Source
                    id="claim-selected-devices"
                    type="geojson"
                    data={selectedFeatures}
                  >
                    <Layer
                      id="claim-selected-polygons"
                      type="fill"
                      filter={[
                        'any',
                        ['==', ['geometry-type'], 'Polygon'],
                        ['==', ['geometry-type'], 'MultiPolygon'],
                      ]}
                      paint={{
                        'fill-color': '#ef4444',
                        'fill-opacity': 0.55,
                      }}
                    />
                    <Layer
                      id="claim-selected-lines"
                      type="line"
                      filter={[
                        'any',
                        ['==', ['geometry-type'], 'Polygon'],
                        ['==', ['geometry-type'], 'MultiPolygon'],
                      ]}
                      paint={{
                        'line-color': '#991b1b',
                        'line-width': 2,
                      }}
                    />
                    <Layer
                      id="claim-selected-points"
                      type="circle"
                      filter={['==', ['geometry-type'], 'Point']}
                      paint={{
                        'circle-radius': 7,
                        'circle-color': '#ef4444',
                        'circle-stroke-color': '#ffffff',
                        'circle-stroke-width': 2,
                      }}
                    />
                  </Source>
                </MapboxMap>

                <svg
                  width="100%"
                  height="100%"
                  style={{ position: 'absolute', inset: 0 }}
                >
                  {claimMapMarkers.map((marker) => (
                    <line
                      key={`line-${marker.deviceId}`}
                      x1={marker.devicePosition.x}
                      y1={marker.devicePosition.y}
                      x2={marker.markerPosition.x}
                      y2={marker.markerPosition.y}
                      stroke="#991b1b"
                      strokeWidth={1.5}
                    />
                  ))}
                </svg>

                {claimMapMarkers.map((marker) => (
                  <div
                    key={`marker-${marker.deviceId}`}
                    style={{
                      alignItems: 'center',
                      background: '#dc2626',
                      border: '2px solid #ffffff',
                      borderRadius: 999,
                      boxShadow: '0 2px 6px rgba(0, 0, 0, 0.28)',
                      color: '#ffffff',
                      display: 'flex',
                      fontSize: 12,
                      fontWeight: 700,
                      height: 24,
                      justifyContent: 'center',
                      left: marker.markerPosition.x,
                      minWidth: 24,
                      position: 'absolute',
                      top: marker.markerPosition.y,
                      transform: 'translate(-50%, -50%)',
                    }}
                  >
                    {marker.number}
                  </div>
                ))}

                {!mapIdle && (
                  <div
                    style={{
                      alignItems: 'center',
                      background: 'rgba(255, 255, 255, 0.85)',
                      display: 'flex',
                      inset: 0,
                      justifyContent: 'center',
                      position: 'absolute',
                    }}
                  >
                    Loading GIS map...
                  </div>
                )}
              </div>
              <div style={{ color: '#6b7280', fontSize: 11, marginTop: 6 }}>
                Map data © Mapbox © OpenStreetMap. Red markers identify devices
                included in this warranty claim.
              </div>
            </div>

            <div style={{ fontSize: 13 }}>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>
                Claim Context
              </div>
              <div style={{ color: '#374151', marginBottom: 14 }}>
                {summary || 'No summary provided.'}
              </div>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>
                Selected Devices
              </div>
              <ol style={{ margin: 0, paddingLeft: 20 }}>
                {selectedDevices.map((device) => (
                  <li key={device.device_id} style={{ marginBottom: 8 }}>
                    <div style={{ fontWeight: 600 }}>{device.device_name}</div>
                    {buildDetailLines(device).map((line) => (
                      <div key={line} style={{ color: '#4b5563' }}>
                        {line}
                      </div>
                    ))}
                  </li>
                ))}
              </ol>
              {missingGeometryDevices.length > 0 && (
                <div
                  style={{
                    background: '#fff7ed',
                    border: '1px solid #fed7aa',
                    borderRadius: 8,
                    marginTop: 14,
                    padding: 10,
                  }}
                >
                  <div style={{ fontWeight: 700 }}>Not shown on map</div>
                  {missingGeometryDevices.map((device) => (
                    <div key={device.device_id} style={{ marginTop: 4 }}>
                      {device.device_name}: no GIS geometry available
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  },
)

export default ClaimGisMapPdf
