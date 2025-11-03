import { HexLoaderInline } from '@/HexLoaderInline'
import { useGetDevicesInViewport } from '@/api/v1/analytics/gis'
import { useSelectProject } from '@/api/v1/operational/projects'
import { PageError } from '@/components/Error'
import { ColorBar, MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
import * as gisUtils from '@/utils/GIS'
import { Box, Paper, Stack, Text, useComputedColorScheme } from '@mantine/core'
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

// Device type IDs for BESS domain
// 13: BESS PCS, 11: BESS DC Enclosure, 27: BESS String
const DT_BESS_PCS = 13
const DT_BESS_DC_ENCLOSURE = 11
const DT_BESS_STRING = 27

// Zoom levels
const ZOOM_LEVEL_2 = 14.6
const ZOOM_LEVEL_1 = 13

// Color for non-comm/missing values
const COLOR_NON_COMM = '#1C7ED6'
const OPACITY_NON_COMM = 0.5

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
  const [zoom, setZoom] = useState(ZOOM_LEVEL_1)
  const blankMapStyle = gisUtils.useBlankMapStyle()
  const mapRef = useRef<MapRef>(null)
  const mouseDownPos = useRef<{ x: number; y: number } | null>(null)

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

  // Pick device types to fetch based on zoom:
  // - Level 1: PCS + BESS DC Enclosures
  // - Level 2: BESS Strings
  const deviceTypeIdsToFetch = useMemo(() => {
    return zoom >= ZOOM_LEVEL_2
      ? [DT_BESS_STRING]
      : [DT_BESS_PCS, DT_BESS_DC_ENCLOSURE]
  }, [zoom])

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
      enabled: !!project.data && !!viewportBounds && zoom >= ZOOM_LEVEL_1,
      placeholderData: keepPreviousData,
    },
  })

  // Build GeoJSON features
  const geojsonData: FeatureCollection | null = useMemo(() => {
    if (!viewportDevices.data) return null

    const features: Feature[] = []
    const isStringsView = zoom >= ZOOM_LEVEL_2

    viewportDevices.data.forEach((device) => {
      const latestActualPower =
        device.power_data?.actual?.power?.slice(-1)[0] ?? null

      const baseProps = {
        device_id: device.device_id,
        name: device.name_long,
        capacity_dc: device.capacity_dc,
        capacity_ac: device.capacity_ac,
        device_type_id: device.device_type_id,
        power_kw: latestActualPower,
        // Placeholder for SOC until backend exposes it via viewport endpoint
        soc_percent: null as number | null,
        effective_zoom: zoom,
      }

      if (isStringsView) {
        // Zoom level 2: render BESS String polygons if available
        if (
          device.device_type_id === DT_BESS_STRING &&
          device.polygon &&
          Array.isArray(device.polygon.coordinates) &&
          device.polygon.coordinates.length > 0
        ) {
          features.push({
            type: 'Feature',
            properties: { ...baseProps, renderType: 'polygon' },
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
          features.push({
            type: 'Feature',
            properties: { ...baseProps, renderType: 'polygon' },
            geometry: device.polygon as GeoJSON.MultiPolygon,
          })
        }
        if (
          device.device_type_id === DT_BESS_DC_ENCLOSURE &&
          device.polygon &&
          Array.isArray(device.polygon.coordinates) &&
          device.polygon.coordinates.length > 0
        ) {
          features.push({
            type: 'Feature',
            properties: { ...baseProps, renderType: 'polygon' },
            geometry: device.polygon as GeoJSON.MultiPolygon,
          })
        }
      }
    })

    return { type: 'FeatureCollection', features } as FeatureCollection
  }, [viewportDevices.data, zoom])

  const onHover = useCallback((event: MapMouseEvent) => {
    const {
      features,
      point: { x, y },
    } = event
    const hoveredFeature = features && features[0]
    if (hoveredFeature) setHoverInfo({ feature: hoveredFeature, x, y })
    else setHoverInfo({ feature: null, x: 0, y: 0 })
  }, [])

  if (!context) {
    throw new Error('GISContext is not provided')
  }
  const { showLabels, showSatellite, colorsGoodBad, colorsHighLow } = context

  if (project.isLoading) return <PageLoader />
  if (viewportDevices.error) return <PageError error={viewportDevices.error} />
  if (project.error) return <PageError error={project.error} />

  // No dedicated layout flag for BESS; keep basemap unless explicitly empty
  const mapStyleEmpty = false

  // Legend labels
  const powerLowLabel = '0%'
  const powerHighLabel = '100%+'
  const socLowLabel = '0%'
  const socHighLabel = '100%'

  return (
    project.data && (
      <div style={{ position: 'relative', height: '100%', width: '100%' }}>
        <div style={{ height: '100%', width: '100%', position: 'relative' }}>
          {viewportDevices.isFetching && zoom >= ZOOM_LEVEL_1 && (
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
                    padding: { top: 25, bottom: 25, left: 65, right: 65 },
                  },
                }}
                onMove={(evt) => setZoom(evt.viewState.zoom)}
                style={{
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
                        // Zoom level 2: BESS String colored by SOC (placeholder until SOC available)
                        [
                          'all',
                          ['>=', ['get', 'effective_zoom'], ZOOM_LEVEL_2],
                          ['==', ['get', 'device_type_id'], DT_BESS_STRING],
                        ],
                        [
                          'interpolate',
                          ['linear'],
                          ['coalesce', ['get', 'soc_percent'], -1],
                          0,
                          colorsHighLow[0]?.value ?? '#e03131',
                          50,
                          colorsHighLow[1]?.value ?? '#fab005',
                          100,
                          colorsHighLow[2]?.value ?? '#40c057',
                        ],

                        // Zoom level 1: BESS DC Enclosures by SOC (placeholder)
                        [
                          'all',
                          ['>=', ['get', 'effective_zoom'], ZOOM_LEVEL_1],
                          ['<', ['get', 'effective_zoom'], ZOOM_LEVEL_2],
                          [
                            '==',
                            ['get', 'device_type_id'],
                            DT_BESS_DC_ENCLOSURE,
                          ],
                        ],
                        [
                          'interpolate',
                          ['linear'],
                          ['coalesce', ['get', 'soc_percent'], -1],
                          0,
                          colorsHighLow[0]?.value ?? '#e03131',
                          50,
                          colorsHighLow[1]?.value ?? '#fab005',
                          100,
                          colorsHighLow[2]?.value ?? '#40c057',
                        ],

                        // Zoom level 1: PCS by actual/capacity (good-bad scale)
                        [
                          'all',
                          ['>=', ['get', 'effective_zoom'], ZOOM_LEVEL_1],
                          ['<', ['get', 'effective_zoom'], ZOOM_LEVEL_2],
                          ['==', ['get', 'device_type_id'], DT_BESS_PCS],
                        ],
                        [
                          'interpolate',
                          ['linear'],
                          [
                            'coalesce',
                            [
                              '*',
                              [
                                'case',
                                ['==', ['get', 'power_kw'], null],
                                0,
                                ['get', 'power_kw'],
                              ],
                              [
                                'case',
                                ['==', ['get', 'capacity_ac'], null],
                                0,
                                ['/', 100, ['get', 'capacity_ac']],
                              ],
                            ],
                            0,
                          ],
                          0,
                          colorsGoodBad[0]?.value ?? '#e03131',
                          50,
                          colorsGoodBad[1]?.value ?? '#fab005',
                          100,
                          colorsGoodBad[2]?.value ?? '#40c057',
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
                {zoom >= ZOOM_LEVEL_2 ? (
                  <ColorBar
                    gradient={gisUtils.colorBar({ colors: colorsHighLow })}
                    lowLabel={socLowLabel}
                    highLabel={socHighLabel}
                  />
                ) : (
                  <Stack gap={8}>
                    <ColorBar
                      gradient={gisUtils.colorBar({ colors: colorsGoodBad })}
                      lowLabel={powerLowLabel}
                      highLabel={powerHighLabel}
                    />
                    <ColorBar
                      gradient={gisUtils.colorBar({ colors: colorsHighLow })}
                      lowLabel={socLowLabel}
                      highLabel={socHighLabel}
                    />
                  </Stack>
                )}
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
        <Text size="sm">
          Power:{' '}
          {props?.power_kw !== undefined && props?.power_kw !== null
            ? props.power_kw.toFixed(1) + ' kW'
            : 'No Data'}
        </Text>
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
            ? props.capacity_ac.toFixed(1) + ' kW'
            : 'No Data'}
        </Text>
      )}
    </Paper>
  )
}

export default AdaptiveGisBESS
