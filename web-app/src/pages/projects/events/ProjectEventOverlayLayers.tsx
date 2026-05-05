import { EventSummary } from '@/hooks/types'
import { useMantineTheme } from '@mantine/core'
import { Feature, FeatureCollection, Point } from 'geojson'
import type { ExpressionSpecification, GeoJSONSource } from 'mapbox-gl'
import { Fragment, useEffect, useMemo, useState } from 'react'
import { Layer, Source, useMap } from 'react-map-gl/mapbox'

export const EVENT_SOURCE_ID = 'project-events'
export const EVENT_CLUSTER_LAYER_ID = 'project-events-clusters'
const EVENT_CLUSTER_COUNT_LAYER_ID = 'project-events-cluster-count'
export const EVENT_POINT_LAYER_ID = 'project-events-points'
const EVENT_TABLE_HOVER_SOURCE_ID = 'project-events-table-hover'
const EVENT_TABLE_HOVER_LAYER_ID = 'project-events-table-hover-ring'

const DAILY_LOSS_PURPLE_THRESHOLD = 100

/** One icon per $10/day bucket (0–100+), plus a gray closed-event icon. */
const EVENT_TRIANGLE_IMAGE_KEY = 'proj-ev-tri-w1'

const EVENT_TRIANGLE_CLOSED_IMAGE_ID = `${EVENT_TRIANGLE_IMAGE_KEY}-closed`

const eventTriangleBucketImageId = (bucketIndex: number) =>
  `${EVENT_TRIANGLE_IMAGE_KEY}-b${bucketIndex}`

const EVENT_TRIANGLE_BUCKET_COUNT = 11

const TRIANGLE_PATH = 'M32 8 L56 52 H8 Z'

const buildEventTriangleSvg = (fill: string) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" ` +
  `viewBox="0 0 64 64">` +
  `<path d="${TRIANGLE_PATH}" fill="none" stroke="#ffffff" ` +
  `stroke-width="8" stroke-linejoin="round"/>` +
  `<path d="${TRIANGLE_PATH}" fill="${fill}" stroke="${fill}" ` +
  `stroke-width="4" stroke-linejoin="round"/>` +
  `<rect x="29.5" y="23" width="5" height="16" rx="2.5" fill="#ffffff"/>` +
  `<circle cx="32" cy="45" r="3" fill="#ffffff"/>` +
  `</svg>`

/** Closed events: same shell with a checkmark instead of an alert glyph. */
const buildClosedEventTriangleSvg = (fill: string) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" ` +
  `viewBox="0 0 64 64">` +
  `<path d="${TRIANGLE_PATH}" fill="none" stroke="#ffffff" ` +
  `stroke-width="8" stroke-linejoin="round"/>` +
  `<path d="${TRIANGLE_PATH}" fill="${fill}" stroke="${fill}" ` +
  `stroke-width="4" stroke-linejoin="round"/>` +
  `<path d="M 23 34 L 30 42 L 46 24" fill="none" stroke="#ffffff" ` +
  `stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>` +
  `</svg>`

/** Same triangle shell as single-event markers, without the inner glyph. */
const buildClusterTriangleSvg = (fill: string) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" ` +
  `viewBox="0 0 64 64">` +
  `<path d="${TRIANGLE_PATH}" fill="none" stroke="#ffffff" ` +
  `stroke-width="8" stroke-linejoin="round"/>` +
  `<path d="${TRIANGLE_PATH}" fill="${fill}" stroke="${fill}" ` +
  `stroke-width="4" stroke-linejoin="round"/>` +
  `</svg>`

const eventTriangleDataUrl = (fill: string) =>
  `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
    buildEventTriangleSvg(fill),
  )}`

const clusterTriangleDataUrl = (fill: string) =>
  `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
    buildClusterTriangleSvg(fill),
  )}`

const closedEventTriangleDataUrl = (fill: string) =>
  `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
    buildClosedEventTriangleSvg(fill),
  )}`

const eventClusterTriangleBucketImageId = (bucketIndex: number) =>
  `${EVENT_TRIANGLE_IMAGE_KEY}-cb${bucketIndex}`

const loadImageElement = (src: string): Promise<HTMLImageElement> =>
  new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })

const lossBucketIconStepExpr = (
  property: 'dailyLossFinancial' | 'lossDailyFinancial',
  bucketImageId: (bucketIndex: number) => string = eventTriangleBucketImageId,
): ExpressionSpecification => {
  const expr: unknown[] = [
    'step',
    ['max', 0, ['coalesce', ['get', property], 0]],
    bucketImageId(0),
  ]
  for (let i = 1; i < EVENT_TRIANGLE_BUCKET_COUNT; i += 1) {
    expr.push(i * 10, bucketImageId(i))
  }
  return expr as ExpressionSpecification
}

const clamp = (value: number, min: number, max: number) =>
  Math.min(Math.max(value, min), max)

const hexToRgb = (hexColor: string) => {
  const normalized = hexColor.replace('#', '')
  const value =
    normalized.length === 3
      ? normalized
          .split('')
          .map((char) => `${char}${char}`)
          .join('')
      : normalized

  return {
    r: Number.parseInt(value.slice(0, 2), 16),
    g: Number.parseInt(value.slice(2, 4), 16),
    b: Number.parseInt(value.slice(4, 6), 16),
  }
}

const rgbToHex = ({ r, g, b }: { r: number; g: number; b: number }) =>
  `#${[r, g, b]
    .map((channel) => Math.round(channel).toString(16).padStart(2, '0'))
    .join('')}`

export const getDailyLossColor = ({
  dailyLossFinancial,
  minColor,
  maxColor,
}: {
  dailyLossFinancial: number | null | undefined
  minColor: string
  maxColor: string
}) => {
  const loss = clamp(dailyLossFinancial ?? 0, 0, DAILY_LOSS_PURPLE_THRESHOLD)
  const ratio = loss / DAILY_LOSS_PURPLE_THRESHOLD
  const start = hexToRgb(minColor)
  const end = hexToRgb(maxColor)

  return rgbToHex({
    r: start.r + (end.r - start.r) * ratio,
    g: start.g + (end.g - start.g) * ratio,
    b: start.b + (end.b - start.b) * ratio,
  })
}

type EventFeatureProperties = {
  eventId: number
  deviceId: number
  deviceName: string
  deviceTypeName: string
  failureMode: string
  rootCause: string | null
  timeStart: string
  timeEnd: string | null
  lossDailyFinancial: number | null
  lossTotalFinancial: number | null
  lossDailyEnergy: number | null
  lossTotalEnergy: number | null
  isClosed: boolean
}

type EventClusterFeatureProperties = {
  cluster: boolean
  cluster_id: number
  point_count: number
  point_count_abbreviated: string
  openEventCount: number
  closedEventCount: number
  dailyLossFinancial: number
  totalLossFinancial: number
  dailyLossEnergy: number
  totalLossEnergy: number
}

export const isProjectEventPointProperties = (
  properties: unknown,
): properties is EventFeatureProperties => {
  if (!properties || typeof properties !== 'object') {
    return false
  }

  const candidate = properties as Record<string, unknown>

  return (
    typeof candidate.eventId === 'number' &&
    typeof candidate.deviceName === 'string' &&
    typeof candidate.deviceTypeName === 'string' &&
    typeof candidate.failureMode === 'string' &&
    typeof candidate.timeStart === 'string' &&
    typeof candidate.isClosed === 'boolean'
  )
}

export const isProjectEventClusterProperties = (
  properties: unknown,
): properties is EventClusterFeatureProperties => {
  if (!properties || typeof properties !== 'object') {
    return false
  }

  const candidate = properties as Record<string, unknown>

  return (
    candidate.cluster === true &&
    typeof candidate.point_count === 'number' &&
    typeof candidate.openEventCount === 'number' &&
    typeof candidate.closedEventCount === 'number'
  )
}

const EVENT_CLUSTER_PROPERTIES = {
  openEventCount: ['+', ['case', ['get', 'isClosed'], 0, 1]],
  closedEventCount: ['+', ['case', ['get', 'isClosed'], 1, 0]],
  dailyLossFinancial: ['+', ['coalesce', ['get', 'lossDailyFinancial'], 0]],
  totalLossFinancial: ['+', ['coalesce', ['get', 'lossTotalFinancial'], 0]],
  dailyLossEnergy: ['+', ['coalesce', ['get', 'lossDailyEnergy'], 0]],
  totalLossEnergy: ['+', ['coalesce', ['get', 'lossTotalEnergy'], 0]],
} as const

export const hasMappableEventLocation = (event: EventSummary): boolean =>
  Array.isArray(event.location_point?.coordinates) &&
  event.location_point.coordinates.length >= 2

const getProjectEventFeatureCollection = (
  events: EventSummary[],
): FeatureCollection<Point, EventFeatureProperties> => ({
  type: 'FeatureCollection',
  features: events.filter(hasMappableEventLocation).map(
    (event): Feature<Point, EventFeatureProperties> => ({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [
          Number(event.location_point!.coordinates[0]),
          Number(event.location_point!.coordinates[1]),
        ],
      },
      properties: {
        eventId: event.event_id,
        deviceId: event.device_id,
        deviceName: event.device_name_full,
        deviceTypeName: event.device_type_name,
        failureMode: event.failure_mode,
        rootCause: event.root_cause,
        timeStart: event.time_start,
        timeEnd: event.time_end,
        lossDailyFinancial: event.loss_daily_financial,
        lossTotalFinancial: event.loss_total_financial,
        lossDailyEnergy: event.loss_daily_energy,
        lossTotalEnergy: event.loss_total_energy,
        isClosed: event.time_end !== null,
      },
    }),
  ),
})

export const isProjectEventLayerId = (layerId: string | undefined): boolean =>
  layerId === EVENT_CLUSTER_LAYER_ID || layerId === EVENT_POINT_LAYER_ID

interface ProjectEventOverlayLayersProps {
  events: EventSummary[]
  /**
   * When set (e.g. Events page), table-hover resolves coordinates from this list
   * so markers still highlight if the row is filtered off the map (e.g. DC Field).
   */
  mapHoverEventLookup?: EventSummary[]
  /** Events page: pulse ring at this event's coordinates while the table row is hovered. */
  tableHoveredEventId?: number | null
}

const ProjectEventOverlayLayers = ({
  events,
  mapHoverEventLookup,
  tableHoveredEventId = null,
}: ProjectEventOverlayLayersProps) => {
  const theme = useMantineTheme()
  const maps = useMap()
  const mapRef = maps.current
  const [mapRefRetry, setMapRefRetry] = useState(0)
  const [iconsReady, setIconsReady] = useState(false)

  const eventGeoJson = useMemo(
    () => getProjectEventFeatureCollection(events),
    [events],
  )

  const hoverLookupList = mapHoverEventLookup ?? events

  const tableHoverGeoJson = useMemo((): FeatureCollection<Point> => {
    if (tableHoveredEventId == null) {
      return { type: 'FeatureCollection', features: [] }
    }
    const ev = hoverLookupList.find((e) => e.event_id === tableHoveredEventId)
    if (!ev || !hasMappableEventLocation(ev)) {
      return { type: 'FeatureCollection', features: [] }
    }
    const coords = ev.location_point!.coordinates
    return {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'Point',
            coordinates: [Number(coords[0]), Number(coords[1])],
          },
        },
      ],
    }
  }, [hoverLookupList, tableHoveredEventId])

  const clusterIconImageExpr = useMemo(
    () =>
      lossBucketIconStepExpr(
        'dailyLossFinancial',
        eventClusterTriangleBucketImageId,
      ),
    [],
  )
  const pointIconImageExpr = useMemo(
    () =>
      [
        'case',
        ['get', 'isClosed'],
        EVENT_TRIANGLE_CLOSED_IMAGE_ID,
        lossBucketIconStepExpr('lossDailyFinancial'),
      ] as ExpressionSpecification,
    [],
  )

  useEffect(() => {
    if (mapRef) {
      return
    }

    let cancelled = false
    let frame = 0

    const retryWhenMapRefIsReady = () => {
      if (cancelled) {
        return
      }
      if (maps.current) {
        setMapRefRetry((current) => current + 1)
        return
      }
      frame = requestAnimationFrame(retryWhenMapRefIsReady)
    }

    frame = requestAnimationFrame(retryWhenMapRefIsReady)
    return () => {
      cancelled = true
      cancelAnimationFrame(frame)
    }
  }, [mapRef, maps])

  useEffect(() => {
    const map = mapRef?.getMap()
    if (!map) {
      return
    }

    let cancelled = false

    const installIcons = async () => {
      if (!map.isStyleLoaded() || cancelled) {
        return
      }

      const red = theme.colors.red[6]
      const violet = theme.colors.violet[6]
      const gray = theme.colors.gray[6]

      const addSvgIcon = async (
        id: string,
        fill: string,
        dataUrl: (f: string) => string,
      ) => {
        if (map.hasImage(id) || cancelled) {
          return
        }
        const img = await loadImageElement(dataUrl(fill))
        if (cancelled || map.hasImage(id)) {
          return
        }
        map.addImage(id, img, { pixelRatio: 2 })
      }

      try {
        await Promise.all([
          ...Array.from({ length: EVENT_TRIANGLE_BUCKET_COUNT }, (_, i) => {
            const midpoint =
              i === EVENT_TRIANGLE_BUCKET_COUNT - 1 ? 100 : i * 10 + 5
            const fill = getDailyLossColor({
              dailyLossFinancial: midpoint,
              minColor: red,
              maxColor: violet,
            })
            return Promise.all([
              addSvgIcon(
                eventTriangleBucketImageId(i),
                fill,
                eventTriangleDataUrl,
              ),
              addSvgIcon(
                eventClusterTriangleBucketImageId(i),
                fill,
                clusterTriangleDataUrl,
              ),
            ])
          }),
          addSvgIcon(
            EVENT_TRIANGLE_CLOSED_IMAGE_ID,
            gray,
            closedEventTriangleDataUrl,
          ),
        ])
      } catch {
        return
      }

      if (
        cancelled ||
        !map.hasImage(eventTriangleBucketImageId(0)) ||
        !map.hasImage(eventClusterTriangleBucketImageId(0)) ||
        !map.hasImage(EVENT_TRIANGLE_CLOSED_IMAGE_ID)
      ) {
        return
      }
      setIconsReady(true)
    }

    let styledataDebounce: ReturnType<typeof setTimeout> | undefined
    const scheduleInstallFromStyleData = () => {
      clearTimeout(styledataDebounce)
      styledataDebounce = setTimeout(() => void installIcons(), 150)
    }

    void installIcons()
    map.on('style.load', installIcons)
    map.on('styledata', scheduleInstallFromStyleData)
    return () => {
      cancelled = true
      clearTimeout(styledataDebounce)
      map.off('style.load', installIcons)
      map.off('styledata', scheduleInstallFromStyleData)
    }
  }, [
    mapRef,
    mapRefRetry,
    theme.colors.red,
    theme.colors.violet,
    theme.colors.gray,
  ])

  useEffect(() => {
    const map = mapRef?.getMap()
    if (!map || !iconsReady || eventGeoJson.features.length === 0) {
      return
    }
    let cancelled = false
    const schedule = () => {
      if (cancelled) {
        return
      }
      if (!map.isStyleLoaded()) {
        map.once('idle', schedule)
        return
      }
      const src = map.getSource(EVENT_SOURCE_ID)
      if (src && src.type === 'geojson') {
        ;(src as GeoJSONSource).setData(eventGeoJson)
        return
      }
      map.once('idle', schedule)
    }
    const raf = requestAnimationFrame(schedule)
    return () => {
      cancelled = true
      cancelAnimationFrame(raf)
    }
  }, [mapRef, eventGeoJson, iconsReady])

  useEffect(() => {
    const map = mapRef?.getMap()
    if (!map || tableHoverGeoJson.features.length === 0) {
      return
    }
    let frame = 0
    let cancelled = false
    const start = performance.now()
    const step = (now: number) => {
      if (cancelled) {
        return
      }
      if (!map.isStyleLoaded()) {
        frame = requestAnimationFrame(step)
        return
      }
      if (!map.getLayer(EVENT_TABLE_HOVER_LAYER_ID)) {
        frame = requestAnimationFrame(step)
        return
      }
      const t = (now - start) / 1000
      const pulse = (Math.sin(t * Math.PI * 2 * 1.15) + 1) / 2
      map.setPaintProperty(
        EVENT_TABLE_HOVER_LAYER_ID,
        'circle-radius',
        10 + pulse * 16,
      )
      map.setPaintProperty(
        EVENT_TABLE_HOVER_LAYER_ID,
        'circle-opacity',
        0.16 + pulse * 0.24,
      )
      map.setPaintProperty(
        EVENT_TABLE_HOVER_LAYER_ID,
        'circle-stroke-width',
        1.5 + pulse * 1.5,
      )
      frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => {
      cancelled = true
      cancelAnimationFrame(frame)
    }
  }, [mapRef, tableHoverGeoJson])

  const showMainMarkers = iconsReady && eventGeoJson.features.length > 0
  const showTableHoverRing = tableHoverGeoJson.features.length > 0

  if (!showMainMarkers && !showTableHoverRing) {
    return null
  }

  const accent = theme.colors.red[6]

  return (
    <Fragment>
      {showTableHoverRing ? (
        <Source
          id={EVENT_TABLE_HOVER_SOURCE_ID}
          type="geojson"
          data={tableHoverGeoJson}
        >
          <Layer
            id={EVENT_TABLE_HOVER_LAYER_ID}
            type="circle"
            paint={{
              'circle-radius': 18,
              'circle-color': accent,
              'circle-opacity': 0.28,
              'circle-blur': 0.35,
              'circle-stroke-width': 2,
              'circle-stroke-color': '#ffffff',
              'circle-stroke-opacity': 0.85,
            }}
          />
        </Source>
      ) : null}
      {showMainMarkers ? (
        <Source
          id={EVENT_SOURCE_ID}
          type="geojson"
          data={eventGeoJson}
          cluster
          clusterMaxZoom={11}
          clusterRadius={48}
          clusterProperties={EVENT_CLUSTER_PROPERTIES}
        >
          <Layer
            id={EVENT_CLUSTER_LAYER_ID}
            type="symbol"
            filter={['has', 'point_count']}
            layout={{
              'icon-image': clusterIconImageExpr,
              'icon-size': [
                'step',
                ['get', 'point_count'],
                0.66,
                10,
                0.86,
                50,
                1.12,
              ],
              'icon-allow-overlap': true,
              'icon-ignore-placement': true,
            }}
          />
          <Layer
            id={EVENT_CLUSTER_COUNT_LAYER_ID}
            type="symbol"
            filter={['has', 'point_count']}
            layout={{
              'text-field': ['get', 'point_count_abbreviated'],
              'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
              'text-size': 14,
              'text-allow-overlap': true,
              'text-ignore-placement': true,
            }}
            paint={{
              'text-color': '#ffffff',
              'text-halo-color': 'rgba(0, 0, 0, 0.55)',
              'text-halo-width': 1.25,
            }}
          />
          <Layer
            id={EVENT_POINT_LAYER_ID}
            type="symbol"
            filter={['!', ['has', 'point_count']]}
            layout={{
              'icon-image': pointIconImageExpr,
              'icon-size': [
                'interpolate',
                ['linear'],
                ['zoom'],
                10,
                0.55,
                14,
                0.76,
              ],
              'icon-allow-overlap': true,
              'icon-ignore-placement': true,
            }}
          />
        </Source>
      ) : null}
    </Fragment>
  )
}

export default ProjectEventOverlayLayers
