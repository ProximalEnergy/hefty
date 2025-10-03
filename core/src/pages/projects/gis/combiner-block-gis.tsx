import { useGetBlockDropdown } from '@/api/ui'
import { useGetProject } from '@/api/v1/operational/projects'
import BlockDropdown from '@/components/BlockDropdown'
import { PageError } from '@/components/Error'
import { ColorBar, MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
import { useGetGISCombinerBlock } from '@/hooks/api'
import { useProjectDropdownToggle } from '@/hooks/custom'
import * as gisUtils from '@/utils/GIS'
import {
  ActionIcon,
  Box,
  Group,
  HoverCard,
  Paper,
  Stack,
  Text,
  Title,
  Tooltip,
  useComputedColorScheme,
} from '@mantine/core'
import { IconArrowBackUp, IconInfoCircle } from '@tabler/icons-react'
import dayjs from 'dayjs'
import advancedFormat from 'dayjs/plugin/advancedFormat'
import timezone from 'dayjs/plugin/timezone'
import { useCallback, useContext, useState } from 'react'
import { Layer, Map, MapMouseEvent, Source } from 'react-map-gl'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { HoverInfo } from './utils'

dayjs.extend(advancedFormat)
dayjs.extend(timezone)

const CombinerBlockGIS = () => {
  const { projectId, blockId } = useParams()
  const computedColorScheme = useComputedColorScheme('dark')
  const context = useContext(GISContext)
  const blankMapStyle = gisUtils.useBlankMapStyle()
  const navigate = useNavigate()
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })

  useProjectDropdownToggle()

  const gisCombinerBlock = useGetGISCombinerBlock({
    pathParams: { projectId: projectId || '-1', blockId: blockId || '-1' },
    queryOptions: { enabled: !!projectId && !!blockId },
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

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, showSatellite, colorsHighLow } = context

  if (
    gisCombinerBlock.isLoading ||
    project.isLoading ||
    blockDropdown.isLoading
  )
    return <PageLoader />
  if (gisCombinerBlock.error)
    return <PageError error={gisCombinerBlock.error} />
  if (project.error) return <PageError error={project.error} />
  if (!gisCombinerBlock.data || !project.data) return null

  const block_name = gisCombinerBlock.data.features[0].properties?.block_name

  // Determine maximum current value
  let maxCurrent = gisCombinerBlock.data?.features[0].properties?.max_current
  if (maxCurrent === 0) {
    maxCurrent = 1
  }

  // Determine timestamp
  const timestamp = gisCombinerBlock.data?.features[0].properties?.timestamp

  // Check if the map style should be empty
  const mapStyleEmpty = project.data.has_pv_dc_combiner_layout === false

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
          key={blockId} // This is to force a re-render when the block changes
          initialViewState={{
            bounds: gisUtils.findBoundingBox(gisCombinerBlock.data),
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
          mapStyle={
            gisUtils.mapStyle({
              empty: mapStyleEmpty,
              satellite: showSatellite,
              theme: computedColorScheme,
            }) ?? blankMapStyle
          }
          mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
        >
          <Source type="geojson" data={gisCombinerBlock.data}>
            <Layer
              {...gisUtils.layerData({
                featureKey: 'combiner_current',
                colors: colorsHighLow,
                lowValue: 0,
                highValue: maxCurrent,
              })}
            />
            <Layer
              {...gisUtils.layerNonComm({ featureKey: 'combiner_current' })}
            />
            {showLabels && (
              <Layer {...gisUtils.layerLabel({ textField: 'combiner_name' })} />
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
                Combiner {hoverInfo.feature.properties?.combiner_name}
              </Text>
              <Text>PCS {hoverInfo.feature.properties?.pcs_name}</Text>
              <Text>
                {/* TODO: Add correct units to this text */}
                Current:{' '}
                {hoverInfo.feature.properties?.combiner_current !== undefined
                  ? hoverInfo.feature.properties?.combiner_current.toFixed(1)
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
            <Group gap={'xs'}>
              <Title order={3}>PV DC Combiner GIS - Block {block_name}</Title>
              <HoverCard shadow="md" width="20%">
                <HoverCard.Target>
                  <IconInfoCircle />
                </HoverCard.Target>
                <HoverCard.Dropdown>
                  <Text size="sm">
                    It can sometimes be challenging to determine which combiner
                    is connected to a specific PCS DC input. If you suspect a
                    mismatch, please reach out for assistance.
                  </Text>
                </HoverCard.Dropdown>
              </HoverCard>
            </Group>
            <Text>
              As of{' '}
              {dayjs(timestamp).tz(project.data.time_zone).format('HH:mm z')}
            </Text>
            <Group pt="xs" gap="xs">
              <BlockDropdown
                data={blockDropdown.data}
                value={blockId || null}
                onChange={handleBlockDropdownChange}
                size="xs"
              />
              <Link
                to={`/projects/${projectId}/gis/pv-dc-combiner`}
                // Without this there was weird additional space below the button
                style={{ display: 'flex', alignItems: 'center' }}
              >
                <Tooltip
                  label="Back to project view"
                  withArrow
                  position="bottom"
                >
                  <ActionIcon variant="light" size="input-xs">
                    <IconArrowBackUp style={{ width: '70%', height: '70%' }} />
                  </ActionIcon>
                </Tooltip>
              </Link>
            </Group>
          </Paper>
        </Box>
        <Box
          style={{ position: 'absolute', top: 0, left: 0, zIndex: 1 }}
          p="md"
        ></Box>
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
          {/* <Paper h="100%" p={5}>
            <Stack align="center" gap={3} h="100%">
              <Text size="xs">{maxCurrent.toFixed(0)}</Text>
              <Paper
                h={"100%"}
                w={30}
                style={{
                  background: `linear-gradient(to bottom, ${colorHigh}, ${colorLow})`,
                }}
              />
              <Text size="xs">0</Text>
            </Stack>
          </Paper> */}
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

export default CombinerBlockGIS
