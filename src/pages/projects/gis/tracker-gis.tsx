import { useGetBlockDropdown } from '@/api/ui'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useGetProject } from '@/api/v1/operational/projects'
import BlockDropdown from '@/components/BlockDropdown'
import { PageError } from '@/components/Error'
import { ColorBar, MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
import { useGetGISTracker } from '@/hooks/api'
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
import { useCallback, useContext, useState } from 'react'
import { Layer, Map, MapMouseEvent, Source } from 'react-map-gl'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

import {
  HoverInfo,
  PositionSetpointHoverCard,
  PositionSetpointSegmentedControl,
  ZoomToBlockHoverCard,
} from './utils'

const TrackerPerformance = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.PV, ProjectTypeId.PV_BESS],
  })

  const { projectId } = useParams()
  const computedColorScheme = useComputedColorScheme('dark')
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })
  const [searchParams] = useSearchParams()
  const selectedView = searchParams.get('data') ?? 'position'
  const navigate = useNavigate()
  const context = useContext(GISContext)
  const blankMapStyle = gisUtils.useBlankMapStyle()

  const project = useGetProject({
    pathParams: { projectId: projectId || '-1' },
  })

  const blockDropdown = useGetBlockDropdown({
    pathParams: { projectId: projectId || '-1' },
  })

  const handleBlockDropdownChange = (value: string | null) => {
    if (value) {
      navigate(
        `/projects/${projectId}/gis/tracker/${value}?${searchParams.toString()}`,
      )
    }
  }

  const { start, end } = useValidateDateRange({})

  const { data, isLoading, error } = useGetGISTracker({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: start?.format('YYYY-MM-DD'),
      end: end?.format('YYYY-MM-DD'),
    },
    queryOptions: {
      enabled: !!project.data && !!start && !!end,
    },
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

  const onClick = (event: MapMouseEvent) => {
    const { features } = event

    const feature = features && features[0]

    if (feature?.properties?.device_id) {
      const currentSearchParams = new URLSearchParams(location.search)
      navigate(
        `/projects/${projectId}/gis/tracker/${
          feature?.properties.device_id
        }?${currentSearchParams.toString()}`,
      )
    }
  }

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, showSatellite, colorsGoodBad } = context

  if (isLoading || project.isLoading || blockDropdown.isLoading)
    return <PageLoader />

  if (error) return <PageError error={error} />
  if (project.error) return <PageError error={project.error} />

  if (!project.data) return <PageLoader />

  // Check if the map style should be empty
  const mapStyleEmpty = project.data.has_block_layout === false

  return (
    <div
      style={{
        position: 'relative',
        height: '100%',
        width: '100%',
        display: data ? 'block' : 'none',
      }}
    >
      {data && (
        <Map
          key={projectId}
          initialViewState={{
            bounds: gisUtils.findBoundingBox(data),
            fitBoundsOptions: {
              padding: {
                top: 77,
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
          <Source type="geojson" data={data}>
            <Layer
              {...gisUtils.layerData({
                featureKey:
                  selectedView === 'position'
                    ? 'position_deviation'
                    : 'setpoint_deviation',
                // Reverse the colors to match 0 at the top and 10 at the bottom
                colors: colorsGoodBad.slice().reverse(),
                lowValue: 0,
                highValue: 10,
              })}
            />
            <Layer
              {...gisUtils.layerNonComm({ featureKey: 'position_deviation' })}
            />
            {showLabels && (
              <Layer {...gisUtils.layerLabel({ textField: 'name' })} />
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
              <Text fw={700}>Block {hoverInfo.feature.properties?.name}</Text>
              {hoverInfo.feature.properties?.position_deviation !==
                undefined && (
                <Text>
                  Average position deviation from setpoint:{' '}
                  {hoverInfo.feature.properties.position_deviation.toFixed(1)}
                </Text>
              )}
              {hoverInfo.feature.properties?.setpoint_deviation !==
                undefined && (
                <Text>
                  Average setpoint deviation:{' '}
                  {hoverInfo.feature.properties.setpoint_deviation.toFixed(1)}
                </Text>
              )}
            </Paper>
          )}
        </Map>
      )}
      <Box
        style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 1 }}
        p="md"
      >
        <MapSettings disableSatellite={mapStyleEmpty} />
      </Box>
      <Box style={{ position: 'absolute', top: 0, left: 0, zIndex: 1 }} p="md">
        <Paper p="xs" withBorder>
          <Stack gap="xs">
            <Title order={3} lh={1}>
              Tracker GIS
            </Title>
            <Group gap={'xs'}>
              <PositionSetpointSegmentedControl />
              <PositionSetpointHoverCard />
            </Group>
            <Group gap={'xs'}>
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
          bottom: 0,
          right: 0,
          zIndex: 1,
          height: '100%',
        }}
        px="md"
        py={75}
      >
        <ColorBar
          gradient={gisUtils.colorBar({ colors: colorsGoodBad })}
          lowLabel="10 Degrees"
          highLabel="0 Degrees"
        />
      </Box>

      <Stack
        p="md"
        w={350}
        align="center"
        style={{
          position: 'absolute',
          top: 0,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 10,
        }}
      >
        <AdvancedDatePicker
          defaultRange="today"
          includeClearButton={false}
          includeTodayInDateRange={false}
        />
      </Stack>
      <Attribution />
    </div>
  )
}

export default TrackerPerformance
