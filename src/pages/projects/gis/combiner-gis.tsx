import { useGetBlockDropdown } from '@/api/ui'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useGetProject } from '@/api/v1/operational/projects'
import BlockDropdown from '@/components/BlockDropdown'
import { PageError } from '@/components/Error'
import { ColorBar, MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
import { useGetGISCombiner } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import * as gisUtils from '@/utils/GIS'
import {
  Box,
  Group,
  Paper,
  Stack,
  Text,
  Title,
  useComputedColorScheme,
} from '@mantine/core'
import dayjs from 'dayjs'
import advancedFormat from 'dayjs/plugin/advancedFormat'
import timezone from 'dayjs/plugin/timezone'
import { useCallback, useContext, useState } from 'react'
import { Layer, Map, MapMouseEvent, Source } from 'react-map-gl'
import { useNavigate, useParams } from 'react-router-dom'

import { HoverInfo, ZoomToBlockHoverCard } from './utils'

dayjs.extend(advancedFormat)
dayjs.extend(timezone)

const CombinerPerformance = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.PV, ProjectTypeId.PV_BESS],
  })

  const navigate = useNavigate()
  const context = useContext(GISContext)
  const { projectId } = useParams()
  const computedColorScheme = useComputedColorScheme('dark')
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })

  const blankMapStyle = gisUtils.useBlankMapStyle()

  const gisCombiner = useGetGISCombiner({
    pathParams: { projectId: projectId || '-1' },
  })

  const project = useGetProject({
    pathParams: { projectId: projectId || '-1' },
  })

  const blockDropdown = useGetBlockDropdown({
    pathParams: { projectId: projectId || '-1' },
  })

  const handleBlockDropdownChange = (value: string | null) => {
    if (value) {
      navigate(`/projects/${projectId}/gis/pv-dc-combiner/${value}`)
    }
  }

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

  const onClick = (event: MapMouseEvent) => {
    const { features } = event

    const feature = features && features[0]

    if (feature?.properties?.block_device_id) {
      navigate(
        `/projects/${projectId}/gis/pv-dc-combiner/${feature?.properties.block_device_id}`,
      )
    }
  }

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, showSatellite, colorsHighLow } = context

  if (project.isLoading || blockDropdown.isLoading || gisCombiner.isLoading)
    return <PageLoader />
  if (gisCombiner.error) return <PageError error={gisCombiner.error} />
  if (project.isError) return <PageError error={project.error} />
  if (!gisCombiner.data || !project.data) return null

  // Determine maximum current value
  let maxCurrent = gisCombiner.data?.features[0].properties?.max_current
  if (maxCurrent === 0) {
    maxCurrent = 1
  }

  // Determine timestamp
  const timestamp = gisCombiner.data?.features[0].properties?.timestamp

  // Check if the map style should be empty
  const mapStyleEmpty = !project.data.has_block_layout

  return (
    <Stack h="100%" gap={0}>
      <div
        style={{
          position: 'relative',
          height: '100%',
          width: '100%',
        }}
      >
        <Map
          key={projectId}
          initialViewState={{
            bounds: gisUtils.findBoundingBox(gisCombiner.data),
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
          interactiveLayerIds={['data']}
          onMouseMove={onHover}
          onClick={onClick}
          mapStyle={
            gisUtils.mapStyle({
              empty: mapStyleEmpty,
              satellite: showSatellite,
              theme: computedColorScheme,
            }) ?? blankMapStyle
          }
          mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
        >
          <Source type="geojson" data={gisCombiner.data}>
            <Layer
              {...gisUtils.layerData({
                featureKey: 'block_current',
                colors: colorsHighLow,
                lowValue: 0,
                highValue: maxCurrent,
              })}
            />
            <Layer
              {...gisUtils.layerNonComm({ featureKey: 'block_current' })}
            />
            {showLabels && (
              <Layer {...gisUtils.layerLabel({ textField: 'block_name' })} />
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
                {'Block '}
                {hoverInfo.feature.properties?.block_name}
              </Text>
              <Text>
                {/* TODO: Add correct units to this text */}
                Average Current:{' '}
                {hoverInfo.feature.properties?.block_current !== undefined
                  ? hoverInfo.feature.properties?.block_current.toFixed(1)
                  : 'No Data'}
              </Text>
            </Paper>
          )}
        </Map>
        <Box
          style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 1 }}
          p="md"
        >
          <MapSettings disableSatellite={mapStyleEmpty} />
        </Box>
        <Box
          style={{ position: 'absolute', top: 0, left: 0, zIndex: 1 }}
          p="md"
        >
          <Paper p="xs" withBorder>
            <Stack gap="xs">
              <Title order={3} lh={1}>
                PV DC Combiner GIS
              </Title>
              <Text lh={1}>
                As of{' '}
                {dayjs(timestamp).tz(project.data.time_zone).format('HH:mm z')}
              </Text>
              <Group gap="xs">
                <BlockDropdown
                  data={blockDropdown.data}
                  value={null}
                  onChange={handleBlockDropdownChange}
                  includeNextPrevious={false}
                  includeFirstLast={false}
                  size="xs"
                />
                <ZoomToBlockHoverCard />
              </Group>
            </Stack>
          </Paper>
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
            gradient={gisUtils.colorBar({ colors: colorsHighLow })}
            lowLabel="0 Amps"
            highLabel={`${maxCurrent.toFixed(0)} Amps`}
          />
        </Box>
        <Attribution />
      </div>
    </Stack>
  )
}

export default CombinerPerformance
