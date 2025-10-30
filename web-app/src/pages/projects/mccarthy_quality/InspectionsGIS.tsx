import { PageLoader } from '@/components/Loading'
import { useGetDevicesV2, useGetInspections } from '@/hooks/api'
import { Device } from '@/hooks/types'
import * as gisUtils from '@/utils/GIS'
import { List, Paper, ScrollArea, Stack, useMantineTheme } from '@mantine/core'
import { FeatureCollection } from 'geojson'
import { GeoJSONFeature, GeoJSONSource, MapMouseEvent } from 'mapbox-gl'
import { useCallback, useState } from 'react'
import { Layer, Map, MapInstance, Popup, Source } from 'react-map-gl/mapbox'
import { useParams } from 'react-router'

import './CustomStyles.css'

export default function InspectionsGIS() {
  const theme = useMantineTheme()
  const { projectId } = useParams<{ projectId: string }>()
  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [6],
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })
  const inspections = useGetInspections({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  const [selectedFeature, setSelectedFeature] =
    useState<mapboxgl.GeoJSONFeature | null>(null)
  const [clusterFeatures, setClusterFeatures] = useState<
    mapboxgl.GeoJSONFeature[]
  >([])

  const handleMapClick = useCallback((event: MapMouseEvent) => {
    const map = event.target as MapInstance
    const features = map.queryRenderedFeatures(event.point, {
      layers: ['clusters', 'unclustered-point'],
    }) as GeoJSONFeature[]

    if (features.length > 0) {
      const feature = features[0]
      if (feature.properties && 'cluster_id' in feature.properties) {
        const source = map.getSource('data') as GeoJSONSource
        source.getClusterLeaves(
          feature.properties.cluster_id as number,
          Infinity,
          0,
          (err, clusterFeatures) => {
            if (err) {
              return console.error(err)
            }
            setSelectedFeature(feature)
            setClusterFeatures(clusterFeatures as GeoJSONFeature[])
          },
        )
      } else {
        setSelectedFeature(feature)
        setClusterFeatures([])
      }
    } else {
      setSelectedFeature(null)
      setClusterFeatures([])
    }
  }, [])

  if (!devices.data || !inspections.data) {
    return <PageLoader />
  }

  const deviceMap = devices.data.reduce<{ [key: number]: Device }>(
    (acc, device) => {
      acc[device.device_id] = device
      return acc
    },
    {},
  )

  const dataInspections = {
    type: 'FeatureCollection',
    features: inspections.data.map((inspection) => {
      const device = deviceMap[inspection.device_id]
      return {
        type: 'Feature',
        properties: {
          device: device,
          inspection,
        },
        geometry: device.point!,
      }
    }),
  } as FeatureCollection

  const dataBlocks = {
    type: 'FeatureCollection',
    features: devices.data.map((device) => ({
      type: 'Feature',
      properties: { device },
      geometry:
        typeof device.polygon === 'string'
          ? JSON.parse(device.polygon)
          : device.polygon!,
    })),
  } as FeatureCollection

  return (
    <Stack h="100%" gap={0}>
      <div style={{ position: 'relative', height: '100%', width: '100%' }}>
        <Map
          initialViewState={{
            bounds: gisUtils.findBoundingBox(dataBlocks),
            fitBoundsOptions: { padding: 25 },
          }}
          style={{
            borderBottomLeftRadius: 'inherit',
            borderBottomRightRadius: 'inherit',
          }}
          mapStyle={gisUtils.mapStyle({
            empty: false,
            satellite: true,
            theme: 'light',
          })}
          mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
          onClick={handleMapClick}
        >
          <Source id="data2" type="geojson" data={dataBlocks}>
            <Layer
              {...{
                id: 'block',
                type: 'fill',
                paint: {
                  'fill-color': theme.colors.dark[1],
                  'fill-opacity': 0.75,
                },
              }}
            />
          </Source>
          <Source
            id="data"
            type="geojson"
            data={dataInspections}
            cluster={true}
            clusterRadius={50}
          >
            <Layer
              {...{
                id: 'clusters',
                type: 'circle',
                source: 'data',
                filter: ['has', 'point_count'],
                paint: {
                  'circle-color': [
                    'step',
                    ['get', 'point_count'],
                    theme.colors.red[5],
                    10,
                    theme.colors.red[7],
                    100,
                    theme.colors.red[9],
                  ],
                  'circle-radius': [
                    'step',
                    ['get', 'point_count'],
                    20,
                    100,
                    30,
                    750,
                    40,
                  ],
                },
              }}
            />
            <Layer
              {...{
                id: 'cluster-count',
                type: 'symbol',
                source: 'data',
                filter: ['has', 'point_count'],
                layout: {
                  'text-field': '{point_count_abbreviated}',
                  'text-size': 12,
                },
              }}
            />
            <Layer
              {...{
                id: 'unclustered-point',
                type: 'circle',
                source: 'data',
                filter: ['!', ['has', 'point_count']],
                paint: {
                  'circle-color': '#11b4da',
                  'circle-radius': 4,
                  'circle-stroke-width': 1,
                  'circle-stroke-color': '#fff',
                },
              }}
            />
          </Source>
          {selectedFeature && (
            <Popup
              // @ts-expect-error Ignore
              longitude={selectedFeature.geometry.coordinates[0]}
              // @ts-expect-error Ignore
              latitude={selectedFeature.geometry.coordinates[1]}
              closeButton={false}
              closeOnClick={false}
              onClose={() => {
                setSelectedFeature(null)
                setClusterFeatures([])
              }}
              style={{
                background: 'transparent',
                border: 'none',
                boxShadow: 'none',
              }}
              closeOnMove={true}
            >
              <Paper p="md" w={500}>
                <ScrollArea.Autosize mah={250} maw={500}>
                  <List>
                    {clusterFeatures.slice(0, 25).map((feature, index) => (
                      <List.Item key={index}>
                        {feature.properties?.inspection.inspection}
                      </List.Item>
                    ))}
                  </List>
                </ScrollArea.Autosize>
              </Paper>
            </Popup>
          )}
        </Map>
      </div>
    </Stack>
  )
}
