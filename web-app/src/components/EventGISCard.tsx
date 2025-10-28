import { DeviceType } from '@/api/enumerations'
import { useGetProject } from '@/api/v1/operational/projects'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
import { useGetDevice, useGetDevicesV2 } from '@/hooks/api'
import * as gisUtils from '@/utils/GIS'
import { findBoundingBox } from '@/utils/GIS'
import {
  Box,
  LoadingOverlay,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { IconDatabaseOff, IconFlag } from '@tabler/icons-react'
import { FeatureCollection } from 'geojson'
import { useContext } from 'react'
import Map, { Layer, Marker, Source } from 'react-map-gl/mapbox'
import { useParams } from 'react-router-dom'

import { MapSettings } from './GIS'

interface EventGISCardProps {
  deviceId: string | number
  additionalGeoJson?: FeatureCollection
  zoom?: number
}

const useProjectId = () => useParams().projectId || '-1'

const EventGISCard = ({
  deviceId,
  additionalGeoJson,
  zoom,
}: EventGISCardProps) => {
  const projectId = useProjectId()
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('dark')
  const context = useContext(GISContext)
  const blankMapStyle = gisUtils.useBlankMapStyle()

  const {
    data: deviceData,
    isLoading: isDeviceLoading,
    error: deviceError,
  } = useGetDevice({
    pathParams: { projectId, deviceId: deviceId.toString() },
  })

  const {
    data: projectData,
    isLoading: isProjectLoading,
    error: projectError,
  } = useGetProject({
    pathParams: { projectId },
  })

  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [DeviceType.BLOCK],
    },
  })

  const { data: parentDeviceData } = useGetDevice({
    pathParams: {
      projectId,
      deviceId: deviceData?.parent_device_id?.toString() || '-1',
    },
    queryOptions: {
      enabled: !!deviceData?.parent_device_id,
    },
  })

  let coordinates: [number, number] = [0, 0]

  if (deviceData?.device_type_id === 29) {
    coordinates = [
      deviceData?.polygon?.coordinates[0][0][0][0] || 0,
      deviceData?.polygon?.coordinates[0][0][0][1] || 0,
    ]
  } else if (!projectData?.has_pv_pcs_layout) {
    coordinates = [
      parentDeviceData?.point?.coordinates[0] || 0,
      parentDeviceData?.point?.coordinates[1] || 0,
    ]
  } else {
    coordinates = [
      deviceData?.point?.coordinates[0] || 0,
      deviceData?.point?.coordinates[1] || 0,
    ]
  }

  const isLoading = isDeviceLoading || devices.isLoading || isProjectLoading
  const isError = deviceError || projectError || devices.isError

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, showSatellite } = context

  const getGoogleMapsDirectionsUrl = () => {
    return `https://www.google.com/maps/dir/?api=1&destination=${coordinates[1]},${coordinates[0]}&travelmode=driving`
  }

  const handleLeftClick = (event: React.MouseEvent) => {
    event.preventDefault()
    event.stopPropagation()
    window.open(getGoogleMapsDirectionsUrl(), '_blank')
  }

  if (isLoading) {
    return <LoadingOverlay visible={true} />
  }
  if (isError) {
    return <IconDatabaseOff size={48} strokeWidth={1} />
  }

  const filteredData = {
    type: 'FeatureCollection',
    features: devices.data?.map((device) => {
      return {
        type: 'Feature',
        geometry: device.polygon,
        properties: {
          name: device.name_long,
        },
      }
    }),
  } as FeatureCollection

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
          ...(zoom
            ? { longitude: coordinates[0], latitude: coordinates[1], zoom }
            : {
                bounds: findBoundingBox(filteredData),
                fitBoundsOptions: { padding: 35 },
              }),
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
        <Marker
          key="Key!"
          longitude={coordinates[0]}
          latitude={coordinates[1]}
          anchor="bottom"
        >
          <div onClick={handleLeftClick} style={{ cursor: 'pointer' }}>
            <IconFlag
              color={'#ff0000'}
              fill={'#ff0000'}
              style={{ pointerEvents: 'auto' }}
            />
          </div>
        </Marker>
      </Map>
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
