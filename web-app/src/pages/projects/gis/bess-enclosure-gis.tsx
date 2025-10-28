import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useGetProject } from '@/api/v1/operational/projects'
import { PageError } from '@/components/Error'
import { MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
import { useGetGISBessEnclosure } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import * as gisUtils from '@/utils/GIS'
import {
  Box,
  Paper,
  Stack,
  Text,
  Title,
  useComputedColorScheme,
} from '@mantine/core'
import { useCallback, useContext, useState } from 'react'
import {
  Layer,
  MapMouseEvent,
  Map as ReactMap,
  Source,
} from 'react-map-gl/mapbox'
import { useParams } from 'react-router-dom'

import { HoverInfo } from './utils'

const Page = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.BESS, ProjectTypeId.PV_BESS],
  })

  return <BESSEnclosureGIS showTitleCard={true} />
}

export const BESSEnclosureGIS = ({
  showTitleCard = true,
}: {
  showTitleCard?: boolean
}) => {
  const { projectId } = useParams()
  const computedColorScheme = useComputedColorScheme('dark')
  const context = useContext(GISContext)
  const blankMapStyle = gisUtils.useBlankMapStyle()

  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })

  const data = useGetGISBessEnclosure({
    pathParams: { projectId: projectId || '-1' },
  })

  const project = useGetProject({
    pathParams: { projectId: projectId || '-1' },
  })

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

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, showSatellite } = context

  if (data.isLoading || project.isLoading) return <PageLoader />
  if (data.error) return <PageError error={data.error} />
  if (project.error) return <PageError error={project.error} />
  if (!data.data || !project.data) return null

  // Check if the map style should be empty
  const mapStyleEmpty = false

  return (
    <Stack h="100%" gap={0}>
      <div
        style={{
          position: 'relative',
          height: '100%',
          width: '100%',
        }}
      >
        <ReactMap
          key={projectId}
          initialViewState={{
            bounds: gisUtils.findBoundingBox(data.data),
            fitBoundsOptions: {
              padding: {
                top: 30,
                bottom: 30,
                left: 65,
                right: 65,
              },
            },
          }}
          style={{
            borderBottomLeftRadius: 'inherit',
            borderBottomRightRadius: 'inherit',
          }}
          interactiveLayerIds={['data']}
          onMouseMove={onHover}
          mapStyle={
            gisUtils.mapStyle({
              empty: mapStyleEmpty,
              satellite: showSatellite,
              theme: computedColorScheme,
            }) ?? blankMapStyle
          }
          mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
        >
          <Source type="geojson" data={data.data}>
            <Layer id="data" type="fill" paint={{ 'fill-color': 'grey' }} />
            {showLabels && (
              <Layer {...gisUtils.layerLabel({ textField: 'name_long' })} />
            )}
          </Source>
          {hoverInfo.feature && (
            <Paper
              p="xs"
              style={{
                left: hoverInfo.x,
                top: hoverInfo.y,
                position: 'absolute',
                zIndex: 9,
                pointerEvents: 'none',
              }}
            >
              <Text fw={700}>
                BESS Enclosure {hoverInfo.feature.properties?.name_long}
              </Text>
            </Paper>
          )}
        </ReactMap>
        <Box
          style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 1 }}
          p="md"
        >
          <MapSettings disableSatellite={mapStyleEmpty} />
        </Box>
        {showTitleCard && (
          <Box
            style={{ position: 'absolute', top: 0, left: 0, zIndex: 1 }}
            p="md"
          >
            <Paper p="xs" withBorder>
              <Title order={3}>BESS Enclosure GIS</Title>
            </Paper>
          </Box>
        )}
        <Attribution />
      </div>
    </Stack>
  )
}

export default Page
