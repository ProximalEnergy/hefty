import { GISContext } from '@/contexts/GISContext'
import { useGetDevicesV2 } from '@/hooks/api'
import { UptimeData } from '@/hooks/types'
import { HoverInfo } from '@/pages/projects/gis/utils'
import * as gisUtils from '@/utils/GIS'
import { findBoundingBox } from '@/utils/GIS'
import { Box, Paper, Text, useComputedColorScheme } from '@mantine/core'
import { FeatureCollection } from 'geojson'
import { useCallback, useContext, useEffect, useState } from 'react'
import Map, {
  Layer,
  LngLatBoundsLike,
  MapMouseEvent,
  MapRef,
  Source,
} from 'react-map-gl'
import { useParams } from 'react-router-dom'

import { ColorBar, MapSettings } from './GIS'
import { PageLoader } from './Loading'

interface UptimeGISProps {
  deviceTypeId: number
  uptimeData: UptimeData[]
  mapRef?: React.Ref<MapRef>
  deviceTypeName: string
  onBoundsChange?: (bounds: any) => void
}

const UptimeGIS = ({
  deviceTypeId,
  uptimeData,
  mapRef,
  deviceTypeName,
  onBoundsChange,
}: UptimeGISProps) => {
  const projectId = useParams().projectId || '-1'
  const computedColorScheme = useComputedColorScheme('dark')
  const context = useContext(GISContext)
  const blankMapStyle = gisUtils.useBlankMapStyle()
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })
  const { data: devices, isLoading: isDevicesLoading } = useGetDevicesV2({
    pathParams: { projectId },
    filters: {
      device_type_ids: [deviceTypeId],
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })
  const filteredDevices = devices

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, showSatellite, colorsGoodBad } = context

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
  let bounds: LngLatBoundsLike | undefined = undefined
  let filteredData: FeatureCollection

  useEffect(() => {
    if (filteredData?.features.length > 0) {
      const bounds = findBoundingBox(filteredData)
      if (bounds) {
        onBoundsChange?.(bounds)
      }
    }
  }, [onBoundsChange])

  if (isDevicesLoading) {
    return <PageLoader />
  }

  filteredData = {
    type: 'FeatureCollection',
    features: filteredDevices?.map((device) => {
      const uptimeEntry = uptimeData.find(
        (data) => data.device_id === device.device_id,
      )

      const downtimePercentage = uptimeEntry
        ? uptimeEntry.downtime_percentage
        : 0

      return {
        type: 'Feature',
        geometry: device.polygon,
        properties: {
          name: device.name_long,
          downtime_percentage: 1 - downtimePercentage,
        },
      }
    }),
  } as FeatureCollection

  if (filteredData?.features.length > 0) {
    bounds = findBoundingBox(filteredData)
  }

  return (
    <div
      style={{
        position: 'relative',
        height: '100%',
        width: '100%',
      }}
    >
      <Map
        initialViewState={{
          bounds: bounds || undefined,
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
        mapStyle={
          gisUtils.mapStyle({
            satellite: showSatellite,
            theme: computedColorScheme,
          }) ?? blankMapStyle
        }
        mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
        ref={mapRef}
        interactiveLayerIds={['data']}
        onMouseMove={onHover}
      >
        <Source id="data" type="geojson" data={filteredData}>
          <Layer
            {...gisUtils.layerData({
              featureKey: 'downtime_percentage',
              colors: colorsGoodBad,
              lowValue: 0,
              highValue: 1,
            })}
          />
          {showLabels && (
            <Layer {...gisUtils.layerLabel({ textField: 'name' })} />
          )}
        </Source>
        {hoverInfo.feature && (
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
              {deviceTypeName} {hoverInfo.feature.properties?.name}
            </Text>
            <Text>
              Uptime:{' '}
              {hoverInfo.feature.properties?.downtime_percentage !== undefined
                ? (
                    hoverInfo.feature.properties?.downtime_percentage * 100
                  ).toFixed(1) + '%'
                : 'No Data'}
            </Text>
          </Paper>
        )}
      </Map>
      <Box
        style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 1 }}
        px="md"
        py="xl"
      >
        <MapSettings />
      </Box>
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
          gradient={gisUtils.colorBar({ colors: colorsGoodBad })}
          lowLabel="0%"
          highLabel="100%"
        />
      </Box>
    </div>
  )
}

export default UptimeGIS
