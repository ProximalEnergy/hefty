import { DeviceTypeEnum, ProjectTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { PageError } from '@/components/Error'
import { ColorBar, MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import { useTipsPCSGIS } from '@/components/Tips'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import Attribution from '@/components/gis/Attribution'
import { GISContext } from '@/contexts/GISContext'
import { useGetDevicesV2, useGetGISPCS } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import * as gisUtils from '@/utils/GIS'
import {
  Box,
  Button,
  Group,
  HoverCard,
  List,
  LoadingOverlay,
  Paper,
  SegmentedControl,
  Stack,
  Switch,
  Text,
  Title,
  useComputedColorScheme,
} from '@mantine/core'
import { IconDownload, IconInfoCircle } from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { FeatureCollection } from 'geojson'
import { useCallback, useContext, useState } from 'react'
import { Layer, Map, MapMouseEvent, Source } from 'react-map-gl/mapbox'
import { useNavigate, useParams, useSearchParams } from 'react-router'
import { z } from 'zod'

import { HoverInfo } from './utils'

dayjs.extend(utc)
dayjs.extend(timezone)

const NORMALIZED_OPTIONS = ['none', 'dc', 'expected']

const QueryParamsSchema = z.object({
  normalized: z
    .string()
    .transform((val) => {
      if (NORMALIZED_OPTIONS.includes(val)) {
        return val
      }
      return 'none'
    })
    .optional()
    .default('expected'),
  block: z
    .preprocess((val) => {
      if (val === 'false') {
        return false
      }
      return true
    }, z.boolean())
    .optional()
    .default(true),
})

const normalizedOptions = {
  power: {
    none: 'power',
    dc: 'power_normalized',
    expected: 'power_normalized_expected',
  },
  energy: {
    none: 'energy',
    dc: 'energy_normalized',
    expected: 'test',
  },
}

function getDataType(start: string | null, end: string | null) {
  if (start === null || end === null) {
    return 'power'
  }
  return 'energy'
}

export default function PCSGIS() {
  useTipsPCSGIS()

  useProjectFilter({
    projectTypes: [ProjectTypeEnum.PV, ProjectTypeEnum.PVS],
  })

  return <PCSGISMap />
}

export function PCSGISMap({
  showTitleCard = true,
}: {
  showTitleCard?: boolean
}) {
  // GIS context for settings
  const context = useContext(GISContext)

  // URL params
  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams] = useSearchParams()
  const searchParamsObj = Object.fromEntries([...searchParams])

  const navigate = useNavigate()
  const computedColorScheme = useComputedColorScheme('dark')
  const [hoverInfo, setHoverInfo] = useState<HoverInfo>({
    feature: null,
    x: 0,
    y: 0,
  })
  const blankMapStyle = gisUtils.useBlankMapStyle()

  // Fetch project data
  const project = useSelectProject(projectId!)

  // Parse query params
  let start = searchParams.get('start')
  let end = searchParams.get('end')
  const block = QueryParamsSchema.pick({ block: true }).parse(
    searchParamsObj,
  ).block
  const normalized = QueryParamsSchema.pick({ normalized: true }).parse(
    searchParamsObj,
  ).normalized

  // Determine if data is power or energy based on start and end dates
  const dataType = getDataType(start, end)

  // If project data (time_zone) is available and dataType is energy, parse start and end dates
  if (project.data && dataType === 'energy') {
    start = dayjs(start).tz(project.data.time_zone, true).toISOString()
    end = dayjs(end)
      .add(1, 'day')
      .tz(project.data.time_zone, true)
      .toISOString()
  }

  // Fetch GIS PCS data
  // At this point, start and end are undefined (live data) or ISO strings (historical data)
  const gis = useGetGISPCS({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: start ?? undefined,
      end: end ?? undefined,
    },
    queryOptions: {
      enabled: project.data !== undefined,
      staleTime: dataType === 'energy' ? Infinity : 30 * 1000,
      refetchInterval: dataType === 'energy' ? undefined : 60 * 1000, // Refetch every 60 seconds for live data
    },
  })

  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [DeviceTypeEnum.PV_PCS, DeviceTypeEnum.BLOCK],
    },
  })

  const onHover = useCallback(
    (event: MapMouseEvent) => {
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
    },
    [setHoverInfo],
  )

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, showSatellite, colorsGoodBad, colorsHighLow } = context

  if (gis.isLoading || project.isLoading || devices.isLoading)
    return <PageLoader />
  if (gis.error) return <PageError error={gis.error} />

  const filteredDevices = devices.data?.filter((device) =>
    block
      ? device.device_type_id === DeviceTypeEnum.BLOCK
      : device.device_type_id === DeviceTypeEnum.PV_PCS,
  )

  // Determine of there are more devices of device_type_id 2 than 6
  const multiplePCSsPerBlock = devices.data
    ? devices.data?.filter(
        (device) => device.device_type_id === DeviceTypeEnum.PV_PCS,
      ).length >
      devices.data?.filter(
        (device) => device.device_type_id === DeviceTypeEnum.BLOCK,
      ).length
    : undefined

  // Generate GeoJSON data from filteredDevices and gis.data
  const data =
    gis.data !== undefined &&
    filteredDevices !== undefined &&
    ({
      type: 'FeatureCollection',
      features: filteredDevices?.map((device) => {
        return {
          type: 'Feature',
          properties: {
            name: device.name_long,
            power: gis.data.data[device.device_id].power,
            power_expected: gis.data.data[device.device_id].power_exp,
            energy: gis.data.data[device.device_id].energy,
            capacity_dc: device.capacity_dc,
            capacity_ac: device.capacity_ac,
            energy_normalized:
              gis.data.data[device.device_id].energy !== null
                ? (gis.data.data[device.device_id].energy ?? 0) /
                  ((device.capacity_dc ?? 1) / 1000)
                : null,
            power_normalized:
              gis.data.data[device.device_id].power !== null
                ? (gis.data.data[device.device_id].power ?? 0) /
                  (device.capacity_dc ?? 1)
                : null,
            power_normalized_expected:
              gis.data.data[device.device_id].power_norm_exp,
            red_outline: gis.data.data[device.device_id].red_outline,
          },
          geometry:
            typeof device.polygon === 'string'
              ? JSON.parse(device.polygon)
              : device.polygon,
        }
      }),
    } as FeatureCollection)

  // Check if the map style should be empty
  const mapStyleEmpty = project.data
    ? !(block ? project.data.has_block_layout : project.data.has_pv_pcs_layout)
    : true

  let unit
  if (dataType === 'power') {
    switch (normalized) {
      case 'none':
        unit = 'kW'
        break
      case 'dc':
        unit = 'kW/kWDC'
        break
      case 'expected':
        unit = '%'
        break
    }
  } else {
    switch (normalized) {
      case 'none':
        unit = 'MWh'
        break
      case 'dc':
        unit = 'MWh/MWDC'
        break
    }
  }

  const lowLabel = unit === '%' ? '0%' : `0 ${unit}`

  const featureKey = (normalizedOptions[dataType] as { [key: string]: string })[
    normalized
  ]

  let highValue = 1
  if (data) {
    if (dataType === 'energy') {
      highValue = data.features.reduce(
        (acc, feature) => Math.max(acc, feature.properties?.[featureKey] ?? 0),
        0,
      )
    } else {
      if (normalized === 'none') {
        highValue = data.features[0].properties?.capacity_ac
      } else {
        highValue = 1
      }
    }
    highValue = Math.ceil(highValue)
  }
  if (highValue === 0) highValue = 1

  const highLabel = unit === '%' ? '100%' : `${highValue} ${unit}`

  return (
    gis.data &&
    project.data &&
    devices.data && (
      <div
        style={{
          position: 'relative',
          height: '100%',
          width: '100%',
        }}
      >
        <div style={{ height: '100%', width: '100%' }}>
          <LoadingOverlay visible={gis.isLoading || gis.isPending} zIndex={5} />
          {data && (
            <>
              <Map
                key={projectId + String(block)}
                initialViewState={{
                  bounds: gisUtils.findBoundingBox(data),
                  fitBoundsOptions: {
                    padding: {
                      top: showTitleCard ? 134 : 25,
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
                <Source id="data" type="geojson" data={data}>
                  <Layer
                    {...gisUtils.layerData({
                      featureKey,
                      colors:
                        normalized === 'expected'
                          ? colorsGoodBad
                          : colorsHighLow,
                      lowValue: 0,
                      highValue,
                    })}
                  />
                  <Layer {...gisUtils.layerNonComm({ featureKey })} />
                  {showLabels && (
                    <Layer {...gisUtils.layerLabel({ textField: 'name' })} />
                  )}
                </Source>
                {hoverInfo.feature && (
                  <CustomHoverCard
                    hoverInfo={hoverInfo}
                    block={block}
                    dataType={dataType}
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
                  gradient={
                    normalized === 'expected'
                      ? gisUtils.colorBar({ colors: colorsGoodBad })
                      : gisUtils.colorBar({ colors: colorsHighLow })
                  }
                  lowLabel={lowLabel}
                  highLabel={highLabel}
                />
              </Box>
            </>
          )}
        </div>
        <Box
          style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 10 }}
          p="md"
        >
          <MapSettings disableSatellite={mapStyleEmpty} />
        </Box>
        <Attribution />
        {showTitleCard && (
          <>
            <TitleCard
              as_of={gis.data.as_of}
              time_zone={project.data.time_zone}
              dataType={dataType}
              multiplePCSsPerBlock={multiplePCSsPerBlock ?? false}
            />
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
                includeIncrementButtons={false}
                disableInput={normalized === 'expected'}
              />
              {dataType === 'energy' && (
                <Button
                  size="compact-sm"
                  rightSection={<IconDownload size={14} />}
                  onClick={() =>
                    navigate(
                      `/projects/${projectId}/kpis/pv-pcs-energy-production?start=${start}&end=${end}`,
                      { replace: false },
                    )
                  }
                >
                  Download
                </Button>
              )}
            </Stack>
          </>
        )}
      </div>
    )
  )
}

function TitleCard({
  as_of,
  time_zone,
  dataType,
  multiplePCSsPerBlock,
}: {
  as_of: string | null
  time_zone: string
  dataType: string
  multiplePCSsPerBlock: boolean
}) {
  return (
    <Group
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        zIndex: 10,
      }}
      p="md"
      align="top"
    >
      <Paper p="xs" withBorder>
        <Stack gap="xs">
          <Title order={3} lh={1}>
            PV PCS GIS
          </Title>
          {as_of && (
            <Text lh={1}>
              As of {dayjs(as_of).tz(time_zone).format('HH:mm z')}
            </Text>
          )}
          <Group gap="xs">
            <NormSegmentedControl dataType={dataType} />
            <HoverCard shadow="md" width="20%">
              <HoverCard.Target>
                <IconInfoCircle />
              </HoverCard.Target>
              <HoverCard.Dropdown>
                <List size="sm" pr="md">
                  <List.Item>
                    Expected - Power output divided by expected power, not
                    available for energy
                  </List.Item>
                  <List.Item>
                    DC - Power output/energy production divided by DC capacity
                  </List.Item>
                  <List.Item>None - Power output/energy production</List.Item>
                </List>
              </HoverCard.Dropdown>
            </HoverCard>
          </Group>
          {multiplePCSsPerBlock && <BlockAggregated />}
        </Stack>
      </Paper>
    </Group>
  )
}

function NormSegmentedControl({ dataType }: { dataType: string }) {
  const [searchParams, setSearchParams] = useSearchParams()

  const normalized = QueryParamsSchema.pick({ normalized: true }).parse(
    Object.fromEntries([...searchParams]),
  ).normalized

  const handleOnChange = (value: string) => {
    const newParams = new URLSearchParams(searchParams)
    newParams.set('normalized', value)
    setSearchParams(newParams)
  }

  const segmentedControlData = [
    { label: 'None', value: 'none' },
    { label: 'DC', value: 'dc' },
    { label: 'Expected', value: 'expected', disabled: dataType === 'energy' },
  ]

  return (
    <SegmentedControl
      size="xs"
      value={normalized}
      onChange={handleOnChange}
      data={segmentedControlData}
    />
  )
}

function BlockAggregated() {
  const [searchParams, setSearchParams] = useSearchParams()

  const block = QueryParamsSchema.pick({ block: true }).parse(
    Object.fromEntries([...searchParams]),
  ).block

  const handleOnChange = () => {
    const newParams = new URLSearchParams(searchParams)
    newParams.set('block', String(!block))
    setSearchParams(newParams)
  }

  return (
    <Switch
      label="Block Aggregated"
      size="xs"
      checked={block}
      onChange={handleOnChange}
    />
  )
}

function CustomHoverCard({
  hoverInfo,
  block,
  dataType,
}: {
  hoverInfo: HoverInfo
  block: boolean
  dataType: string
}) {
  if (hoverInfo.feature === null) {
    return null
  }

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
        {block ? 'Block' : 'PCS'} {hoverInfo.feature.properties?.name}
      </Text>
      {dataType === 'power' && (
        <Text>
          Power:{' '}
          {hoverInfo.feature.properties?.power !== undefined
            ? hoverInfo.feature.properties?.power.toFixed(1) + ' kW'
            : 'No Data'}
        </Text>
      )}
      {dataType === 'power' && (
        <Text>
          Expected Power:{' '}
          {hoverInfo.feature.properties?.power_expected !== undefined
            ? hoverInfo.feature.properties?.power_expected.toFixed(1) + ' kW'
            : 'No Data'}
        </Text>
      )}
      {dataType === 'energy' && (
        <Text>
          Energy:{' '}
          {hoverInfo.feature.properties?.energy !== undefined
            ? hoverInfo.feature.properties?.energy.toFixed(1) + ' MWh'
            : 'No Data'}
        </Text>
      )}
      <Text>
        DC Capacity:{' '}
        {hoverInfo.feature.properties?.capacity_dc !== undefined
          ? hoverInfo.feature.properties?.capacity_dc.toFixed(1) + ' kW'
          : 'No Data'}
      </Text>
      {dataType === 'power' && (
        <Text>
          Normalized Power:{' '}
          {hoverInfo.feature.properties?.power_normalized !== undefined
            ? hoverInfo.feature.properties?.power_normalized.toFixed(3) +
              ' kW/kWDC'
            : 'No Data'}
        </Text>
      )}
    </Paper>
  )
}
