import type { OperationalKPIData } from '@/api/v1/operational/kpi_data'
import type { KPIType } from '@/api/v1/operational/kpi_types'
import CustomCard from '@/components/CustomCard'
import { ColorBar, MapSettings } from '@/components/GIS'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
import type { Device } from '@/hooks/types'
import * as gisUtils from '@/utils/GIS'
import { Box, Stack, Text, useComputedColorScheme } from '@mantine/core'
import type { FeatureCollection } from 'geojson'
import { useCallback, useContext, useState } from 'react'
import type { MapMouseEvent } from 'react-map-gl/mapbox'
import Map, { Layer, Source } from 'react-map-gl/mapbox'

import { MapHoverCard } from '../gis/MapHoverCard'
import type { HoverInfo } from '../gis/utils'

type PerformanceReportMapCardProps = {
  data: OperationalKPIData | undefined
  kpiType: KPIType
  cardTitle: string
  devices: Device[]
  isLoading: boolean
  isError: boolean
  onMapIdle?: (isIdle: boolean) => void
}

export function PerformanceReportMapCard({
  data,
  kpiType,
  cardTitle,
  devices,
  isLoading,
  isError,
  onMapIdle,
}: PerformanceReportMapCardProps) {
  const context = useContext(GISContext)
  const computedColorScheme = useComputedColorScheme('dark')
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })
  const blankMapStyle = gisUtils.useBlankMapStyle()

  const onHover = useCallback((event: MapMouseEvent) => {
    const {
      features,
      point: { x, y },
    } = event

    const hoveredFeature = features && features[0]

    if (hoveredFeature) {
      setHoverInfo({
        feature: hoveredFeature,
        x,
        y,
      })
    } else {
      setHoverInfo({
        feature: null,
        x: 0,
        y: 0,
      })
    }
  }, [])

  if (isLoading) {
    return (
      <CustomCard title={cardTitle} style={{ height: '50vh' }} fill={true}>
        <Text c="dimmed">Loading...</Text>
      </CustomCard>
    )
  }

  if (isError) {
    return (
      <CustomCard title={cardTitle} style={{ height: '50vh' }} fill={true}>
        <Text c="dimmed">Error loading data</Text>
      </CustomCard>
    )
  }

  if (!devices || devices.length === 0) {
    return (
      <CustomCard title={cardTitle} style={{ height: '50vh' }} fill={true}>
        <Text c="dimmed">No combiner devices found</Text>
      </CustomCard>
    )
  }

  if (!data) {
    return null
  }

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, showSatellite, colorsGoodBad } = context

  const deviceValues = data.data.device_data_obj?.device_values
  let aggregation: Record<string, number> = {}

  if (deviceValues && Object.keys(deviceValues).length > 0) {
    if (kpiType.aggregation_method === 'average') {
      aggregation = Object.fromEntries(
        Object.entries(deviceValues).map(([key, values]) => {
          const validValues = values.filter((value) => value != null)
          const average =
            validValues.reduce((sum, value) => sum + value, 0) /
              validValues.length || 0

          return [key, average]
        }),
      )
    } else if (kpiType.aggregation_method === 'sum') {
      aggregation = Object.fromEntries(
        Object.entries(deviceValues).map(([key, values]) => {
          return [
            key,
            values.reduce((acc, value) => (acc ?? 0) + (value ?? 0), 0) || 0,
          ]
        }),
      )
    }
  } else {
    aggregation = Object.fromEntries(
      devices.map((device) => [device.device_id.toString(), 0.5]),
    )
  }

  const gisData: FeatureCollection = {
    type: 'FeatureCollection',
    features:
      devices
        .map((device) => {
          return {
            type: 'Feature',
            properties: {
              name: device.name_long,
              value: aggregation[device.device_id] || 0,
            },
            geometry:
              typeof device.polygon === 'string'
                ? JSON.parse(device.polygon)
                : device.polygon,
          }
        })
        .filter((feature) => feature.geometry && feature.geometry.type) || [],
  } as FeatureCollection

  if (gisData.features.length === 0) {
    return (
      <CustomCard title={cardTitle} style={{ height: '50vh' }} fill={true}>
        <Stack align="center" justify="center" h="100%">
          <Text c="dimmed" size="lg" ta="center">
            No combiner devices with location data available
          </Text>
          <Text c="dimmed" size="sm" ta="center" mt="xs">
            {devices.length} combiner devices found, but none have geographic
            coordinates for mapping
          </Text>
        </Stack>
      </CustomCard>
    )
  }

  const mapStyleEmpty = false
  const values = Object.values(aggregation)
  const numberValues = values.flat().filter((value): value is number => {
    return value != null
  })

  let lowValue: number
  let highValue: number
  let lowLabel: string
  let highLabel: string

  switch (kpiType.unit) {
    case '%':
      lowValue = 0
      highValue = 1
      lowLabel = '0%'
      highLabel = '100%'
      break
    default:
      lowValue = Math.min(0, ...numberValues)
      highValue = Math.max(...numberValues)

      if (!isFinite(highValue)) {
        lowValue = 0
        highValue = 1
      }

      lowLabel = `${lowValue.toFixed(2)} ${kpiType.unit}`
      highLabel = `${highValue.toFixed(2)} ${kpiType.unit}`
  }

  const colors = colorsGoodBad

  return (
    <CustomCard
      title={cardTitle}
      style={{ height: '50vh' }}
      fill
      info="Map data is aggregated over the requested interval."
    >
      <div
        style={{
          position: 'relative',
          height: '100%',
          width: '100%',
        }}
      >
        <div style={{ height: '100%', width: '100%' }}>
          <Map
            key="map"
            preserveDrawingBuffer
            onIdle={() => onMapIdle?.(true)}
            initialViewState={{
              bounds: gisUtils.findBoundingBox(gisData),
              fitBoundsOptions: {
                padding: {
                  top: 25,
                  bottom: 25,
                  left: 65,
                  right: 65,
                },
              },
            }}
            style={{
              borderBottomLeftRadius: 'inherit',
              borderBottomRightRadius: 'inherit',
            }}
            mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
            interactiveLayerIds={['data']}
            onMouseMove={onHover}
            mapStyle={
              gisUtils.mapStyle({
                empty: mapStyleEmpty,
                satellite: showSatellite,
                theme: computedColorScheme,
              }) ?? blankMapStyle
            }
          >
            <Source id="data" type="geojson" data={gisData}>
              <Layer
                {...gisUtils.layerData({
                  featureKey: 'value',
                  colors,
                  lowValue,
                  highValue,
                })}
              />
              <Layer {...gisUtils.layerNonComm({ featureKey: 'value' })} />
              {showLabels && (
                <Layer {...gisUtils.layerLabel({ textField: 'name' })} />
              )}
            </Source>
            {hoverInfo.feature && (
              <MapHoverCard
                hoverInfo={hoverInfo}
                kpiType={kpiType}
                decimalPlaces={0}
              />
            )}
          </Map>
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
            <ColorBar
              gradient={gisUtils.colorBar({ colors })}
              lowLabel={lowLabel}
              highLabel={highLabel}
            />
          </Box>
        </div>
        <Box
          style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 10 }}
          px="md"
          py="md"
        >
          <MapSettings disableSatellite={mapStyleEmpty} />
        </Box>
        <Attribution />
      </div>
    </CustomCard>
  )
}
