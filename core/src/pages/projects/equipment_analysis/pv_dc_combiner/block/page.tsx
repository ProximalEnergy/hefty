import { useGetBlockDropdown } from '@/api/ui'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { useGetProject } from '@/api/v1/operational/projects'
import BlockDropdown from '@/components/BlockDropdown'
import CustomCard from '@/components/CustomCard'
import { MapSettings } from '@/components/GIS'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import Attribution from '@/components/gis/Attribution'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { traceColors } from '@/components/plots/PlotlyPlotUtils'
import { GISContext } from '@/contexts/GISContext'
import {
  useAnalyzeCombinerSwaps,
  useGetDevicesV2,
  useGetGISCombinerBlock,
  useGetTags,
  useValidateCombinerData,
} from '@/hooks/api'
import { useProjectDropdownToggle } from '@/hooks/custom'
import * as gisUtils from '@/utils/GIS'
import { OPACITY_DEFAULT } from '@/utils/GIS'
import { DndContext, DragEndEvent, closestCenter } from '@dnd-kit/core'
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  Box,
  Button,
  Group,
  Indicator,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import {
  IconAnalyze,
  IconArrowBackUp,
  IconArrowsExchange,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useContext, useEffect, useState } from 'react'
import { Layer, Map, Source } from 'react-map-gl'
import { Link, useParams, useSearchParams } from 'react-router-dom'

dayjs.extend(utc)
dayjs.extend(timezone)

type combinerData = {
  combiner_device_id: number
  combiner_dc_capacity: number
  combiner_name_long: string
  tag_name_scada: string
  original_tag_name_scada: string
  tag_id: number
}

const MAX_DAYS = 7

const Page = () => {
  const context = useContext(GISContext)
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('dark')
  const blankMapStyle = gisUtils.useBlankMapStyle()
  const { projectId } = useParams()
  const [indexArray, setIndexArray] = useState<number[]>([])
  const [searchParams, setSearchParams] = useSearchParams()
  const blockDeviceId = searchParams.get('deviceId')

  useProjectDropdownToggle()

  const handleBlockDropdownChange = (value: string | null) => {
    if (value) {
      searchParams.set('deviceId', value)
      setSearchParams(searchParams)
    }
  }

  // Fetch project data
  const project = useGetProject({
    pathParams: { projectId: projectId || '-1' },
  })

  // Fetch block dropdown data
  const blockDropdown = useGetBlockDropdown({
    pathParams: { projectId: projectId || '-1' },
  })

  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  let startRequest, endRequest
  if (project.data) {
    startRequest = start && start.tz(project.data.time_zone, true).toISOString()
    endRequest = end && end.tz(project.data.time_zone, true).toISOString()
  }

  const devices = useGetDevicesV2({
    pathParams: {
      projectId: projectId || '-1',
    },
    filters: {
      device_type_ids: [2, 6, 9],
      device_id_descendent_of: blockDeviceId ? Number(blockDeviceId) : null,
    },
  })

  const combinerTags = useGetTags({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      sensor_type_ids: [27],
      deep: true,
    },
  })

  const pcsDeviceIds = devices.data
    ?.filter((d) => d.device_type_id === 2)
    .map((d) => d.device_id)

  const combinerDeviceIds = devices.data
    ?.filter((d) => d.device_type_id === 9)
    .map((d) => d.device_id)

  const combinerData = useGetTimeSeries({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      device_ids: combinerDeviceIds,
      sensor_type_name_shorts: ['pv_dc_combiner_current'],
      start: startRequest ?? undefined,
      end: endRequest ?? undefined,
    },
    queryOptions: {
      enabled:
        combinerDeviceIds &&
        combinerDeviceIds.length > 0 &&
        !!project.data &&
        !!start &&
        !!end,
    },
  })

  const analyzeCombinerSwaps = useAnalyzeCombinerSwaps()

  // Add new state for validation
  const [dataValidation, setDataValidation] = useState<{
    isValid: boolean
    message?: string
  }>({ isValid: true })
  // Add before the useEffects
  const validation = useValidateCombinerData({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      deviceIds: combinerDeviceIds,
      start: startRequest ?? undefined,
      end: endRequest ?? undefined,
    },
    queryOptions: {
      enabled:
        !blockDropdown.isLoading &&
        !devices.isLoading &&
        !combinerTags.isLoading &&
        !!combinerDeviceIds &&
        combinerDeviceIds.length > 0 &&
        !!startRequest &&
        !!endRequest,
    },
  })

  // Log validation data whenever it changes
  useEffect(() => {
    if (validation.error) {
      console.error('Validation error:', validation.error)
    }
  }, [validation.data, validation.error])

  // Add validation check when combiner data changes
  useEffect(() => {
    if (!combinerData.data || combinerData.data.length === 0) {
      setDataValidation({ isValid: false, message: 'No data available' })
      return
    }

    // Get the first combiner's data to check time range
    const firstCombiner = combinerData.data[0]
    if (!firstCombiner.x || firstCombiner.x.length === 0) {
      setDataValidation({
        isValid: false,
        message: 'No time series data available',
      })
      return
    }
  }, [combinerData.data])

  // Separate effect for validation API call
  useEffect(() => {
    if (validation.data) {
      setDataValidation(validation.data)
    }
  }, [validation.data])

  // Update the validation effect
  useEffect(() => {
    if (validation.isLoading) {
      setDataValidation({ isValid: false, message: 'Validating data...' })
    } else if (validation.error) {
      setDataValidation({ isValid: false, message: 'Error validating data' })
    } else if (validation.data) {
      setDataValidation(validation.data)
    }
  }, [validation.isLoading, validation.data, validation.error])

  // Add new state for analysis results
  const [analysisResult, setAnalysisResult] = useState<{
    hasSwaps: boolean
    swapCount: number
    isComplete: boolean
  } | null>(null)

  // Update the analyzeSwaps function
  const analyzeSwaps = async () => {
    if (!start || !projectId || !blockDeviceId) return

    const blockNames = devices.data
      ?.filter((d) => d.device_id === Number(blockDeviceId))
      .map((d) => d.name_short)

    if (!blockNames || blockNames.length === 0) return

    try {
      // Reset the index array to restore original positions
      setIndexArray([])
      setAnalysisResult(null)

      const result = await analyzeCombinerSwaps.mutateAsync({
        projectId,
        analysisDate: start.format('YYYY-MM-DD'),
        blockNames: blockNames.filter((name): name is string => name !== null),
      })

      const blockName = blockNames[0]
      const swaps = blockName ? result[blockName]?.swaps || [] : []

      setAnalysisResult({
        hasSwaps: swaps.length > 0,
        swapCount: swaps.length,
        isComplete: true,
      })

      if (swaps.length > 0) {
        // Existing swap handling logic...
        const newIndexArray =
          indexArray.length > 0
            ? [...indexArray]
            : Array.from({ length: data.length }, (_, i) => i)

        swaps.forEach(([tag1, tag2]: [number, number]) => {
          const index1 = data.findIndex((d) => Number(d.tag_id) === tag1)
          const index2 = data.findIndex((d) => Number(d.tag_id) === tag2)

          if (index1 !== -1 && index2 !== -1) {
            const temp = newIndexArray[index1]
            newIndexArray[index1] = newIndexArray[index2]
            newIndexArray[index2] = temp
          }
        })

        setIndexArray(newIndexArray)
      }
    } catch {
      setAnalysisResult(null)
    }
  }

  // Add effect to reset indexArray when blockDeviceId changes
  useEffect(() => {
    setIndexArray([])
    setAnalysisResult(null)
  }, [blockDeviceId])

  const gisData = useGetGISCombinerBlock({
    pathParams: {
      projectId: projectId || '-1',
      blockId: blockDeviceId || '-1',
    },
    queryOptions: {
      enabled: !!projectId && !!blockDeviceId,
    },
  })

  // Add state to track hovered combiner name
  const [hoveredCombinerName, setHoveredCombinerName] = useState<string | null>(
    null,
  )

  // Add state to track hovered SCADA tag name
  const [hoveredTagName, setHoveredTagName] = useState<string | null>(null)

  if (blockDropdown.isLoading || devices.isLoading || combinerTags.isLoading) {
    return <PageLoader />
  }

  if (!devices.data || !combinerTags.data) {
    return <div>No data</div>
  }

  let data = combinerTags.data
    ?.filter((d) => pcsDeviceIds?.includes(d.device.parent_device_id ?? -1))
    .map((d) => ({
      combiner_device_id: d.device.device_id,
      combiner_dc_capacity: d.device.capacity_dc ?? 0,
      combiner_name_long: d.device.name_long ?? '',
      tag_name_scada: d.name_scada,
      original_tag_name_scada: d.name_scada,
      tag_id: d.tag_id,
    }))
    .sort((a, b) => a.combiner_name_long.localeCompare(b.combiner_name_long))

  if (indexArray.length > 0) {
    // Create arrays for all fields that need to be reordered
    const reorderedData = indexArray.map((i) => ({
      tag_name_scada: data[i].tag_name_scada,
      tag_id: data[i].tag_id,
    }))

    // Update data with reordered values
    data = data.map((d, i) => ({
      ...d,
      tag_name_scada: reorderedData[i].tag_name_scada,
      tag_id: reorderedData[i].tag_id,
    }))
  }

  const tagNameToCapacityDC: {
    [key: string]: number
  } = data.reduce(
    (acc, d) => ({
      ...acc,
      [d.tag_name_scada]: d.combiner_dc_capacity,
    }),
    {},
  )

  // Get unique array of data.combiner_dc_capacity
  const capacityDCs = Array.from(
    new Set(data.map((d) => d.combiner_dc_capacity).sort((a, b) => a - b)),
  )

  const colors = traceColors(theme)

  // Create an object mapping capacityDCs to colors
  const capacityDCsToColors: {
    [key: number]: string
  } = capacityDCs.reduce(
    (acc, d, i) => ({
      ...acc,
      [d]: colors[i],
    }),
    {},
  )

  // Create a mapping from combiner_device_id to dc_capacity
  const nameLongToCapacityDC = data.reduce(
    (acc, d) => ({
      ...acc,
      [d.combiner_name_long]: d.combiner_dc_capacity,
    }),
    {},
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (!over || active.id === over.id) return

    const oldIndex = data.findIndex(
      (item) => item.combiner_device_id === active.id,
    )
    const newIndex = data.findIndex(
      (item) => item.combiner_device_id === over.id,
    )

    let newIndexArray
    if (indexArray.length === 0) {
      newIndexArray = Array.from({ length: data.length }, (_, i) => i)
    } else {
      newIndexArray = [...indexArray]
    }

    // Swap the two indices directly
    const temp = newIndexArray[oldIndex]
    newIndexArray[oldIndex] = newIndexArray[newIndex]
    newIndexArray[newIndex] = temp

    setIndexArray(newIndexArray)
  }

  const handleCopy = () => {
    const tagNames = data
      .map((d) => {
        const row = [
          `C${d.combiner_name_long}`,
          d.combiner_dc_capacity,
          d.tag_name_scada,
        ]
        return row.join('\t')
      })
      .join('\n')

    navigator.clipboard.writeText(tagNames)
  }

  if (!context) {
    throw new Error('GISContext is not provided')
  }

  const { showLabels, showSatellite } = context

  const CombinerTableRow = ({
    combiner,
    capacityDCsToColors,
  }: {
    combiner: combinerData
    capacityDCsToColors: { [key: number]: string }
  }) => {
    return (
      <Table.Tr
        style={{ height: '27px', cursor: 'pointer' }}
        onMouseEnter={() => setHoveredCombinerName(combiner.combiner_name_long)}
        onMouseLeave={() => setHoveredCombinerName(null)}
      >
        <Table.Td style={{ padding: '2px 16px' }}>
          <Group gap="xs" wrap="nowrap">
            {combiner.combiner_name_long}
          </Group>
        </Table.Td>
        <Table.Td style={{ padding: '2px 16px' }}>
          <Group gap="xs" wrap="nowrap">
            <Indicator
              color={capacityDCsToColors[combiner.combiner_dc_capacity]}
              offset={0}
            />
            {combiner.combiner_dc_capacity}
          </Group>
        </Table.Td>
      </Table.Tr>
    )
  }

  return (
    <Stack p="md">
      <Title order={1}>Combiner Current Day</Title>
      <Group>
        <BlockDropdown
          data={blockDropdown.data}
          value={blockDeviceId}
          onChange={handleBlockDropdownChange}
        />
        <AdvancedDatePicker
          includeClearButton={false}
          defaultRange="today"
          includeTodayInDateRange
          limits={{
            day: 7,
            week: 1,
            month: 0,
            quarter: 0,
            year: 0,
          }}
          disableQuickActions={true}
          maxDays={MAX_DAYS}
        />
        <Link
          to={`/projects/${projectId}/equipment-analysis?tab=pv-dc-combiner`}
        >
          <Button variant="light" rightSection={<IconArrowBackUp size={14} />}>
            Back to Project
          </Button>
        </Link>
      </Group>
      <Group align="stretch" grow>
        <CustomCard
          title="Combiners"
          fill
          headerChildren={
            <Group>
              <Button
                variant="default"
                size="compact-xs"
                onClick={handleCopy}
                style={{ alignSelf: 'flex-end', WebkitAlignSelf: 'auto' }}
              >
                Copy to Clipboard
              </Button>
              <Tooltip
                label={
                  validation.isLoading
                    ? 'Validating data...'
                    : !dataValidation.isValid
                      ? dataValidation.message
                      : analyzeCombinerSwaps.isPending
                        ? 'Analyzing...'
                        : analysisResult?.isComplete
                          ? analysisResult.hasSwaps
                            ? `${analysisResult.swapCount} mismatches detected`
                            : 'No mismatches detected'
                          : 'Analyze GIS:SCADA Mappings'
                }
                position="bottom"
              >
                <Button
                  leftSection={<IconAnalyze size={14} />}
                  size="compact-xs"
                  onClick={analyzeSwaps}
                  loading={analyzeCombinerSwaps.isPending}
                  disabled={
                    !start ||
                    !end ||
                    !dataValidation.isValid ||
                    validation.isLoading
                  }
                  color={
                    analysisResult?.isComplete
                      ? analysisResult.hasSwaps
                        ? 'yellow'
                        : 'green'
                      : 'blue'
                  }
                >
                  Detect Mismatches
                </Button>
              </Tooltip>
            </Group>
          }
          style={{ width: '70%', display: 'flex', height: '100%' }}
        >
          {data !== undefined && data.length > 0 ? (
            <Group align="flex-start" gap={0} style={{ height: '100%' }}>
              <Box style={{ width: '40%', height: '100%' }}>
                <Table
                  striped
                  highlightOnHover
                  verticalSpacing={2}
                  style={{ height: '100%', whiteSpace: 'nowrap' }}
                >
                  <Table.Thead>
                    <Table.Tr style={{ height: '27px' }}>
                      <Table.Th style={{ whiteSpace: 'nowrap' }}>
                        GIS Name
                      </Table.Th>
                      <Table.Th style={{ whiteSpace: 'nowrap' }}>
                        Power (kW)
                      </Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {data.map((d) => (
                      <CombinerTableRow
                        key={`reference-${d.combiner_device_id}`}
                        combiner={d}
                        capacityDCsToColors={capacityDCsToColors}
                      />
                    ))}
                  </Table.Tbody>
                </Table>
              </Box>
              <Box style={{ width: '60%', height: '100%' }}>
                <DndContext
                  collisionDetection={closestCenter}
                  onDragEnd={handleDragEnd}
                >
                  <Table
                    striped
                    highlightOnHover
                    verticalSpacing={1}
                    style={{ height: '100%' }}
                  >
                    <Table.Thead>
                      <Table.Tr style={{ height: '27px' }}>
                        <Table.Th style={{ whiteSpace: 'nowrap' }}>
                          SCADA Tag Name
                        </Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      <SortableContext
                        items={data.map((d) => d.combiner_device_id)}
                        strategy={verticalListSortingStrategy}
                      >
                        {data.map((d) => (
                          <SortableRow
                            key={d.combiner_device_id}
                            combiner={d}
                            setHoveredTagName={setHoveredTagName}
                          />
                        ))}
                      </SortableContext>
                    </Table.Tbody>
                  </Table>
                </DndContext>
              </Box>
            </Group>
          ) : (
            <Group justify="center">Select a block to see combiners</Group>
          )}
        </CustomCard>
        <CustomCard title="Combiner Layout" fill>
          {gisData.data && (
            <Map
              key={blockDeviceId}
              initialViewState={{
                bounds: gisUtils.findBoundingBox(gisData.data),
                fitBoundsOptions: {
                  padding: {
                    top: 25,
                    bottom: 25,
                    left: 65,
                    right: 65,
                  },
                },
              }}
              mapStyle={
                gisUtils.mapStyle({
                  empty: false,
                  satellite: showSatellite,
                  theme: computedColorScheme,
                }) ?? blankMapStyle
              }
              mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
            >
              <Source type="geojson" data={gisData.data}>
                <Layer
                  id="combiner-layer"
                  type="fill"
                  paint={{
                    'fill-color': [
                      'match',
                      ['get', 'combiner_name'],
                      ...Object.entries(nameLongToCapacityDC).flatMap(
                        ([nameLong, capacity]) => [
                          nameLong as string,
                          capacityDCsToColors[capacity as number] || '#000000',
                        ],
                      ),
                      '#000000',
                    ],
                    'fill-opacity': OPACITY_DEFAULT,
                  }}
                />
                {showLabels && (
                  <Layer
                    {...gisUtils.layerLabel({ textField: 'combiner_name' })}
                  />
                )}
                <Layer
                  id="combiner-outline-layer"
                  type="line"
                  paint={{
                    'line-color': [
                      'case',
                      ['==', ['get', 'combiner_name'], hoveredCombinerName],
                      '#FF0000', // Highlight color
                      'transparent',
                    ],
                    'line-width': [
                      'case',
                      ['==', ['get', 'combiner_name'], hoveredCombinerName],
                      3, // Thick border width
                      0,
                    ],
                  }}
                />
              </Source>
              <Box
                style={{ position: 'absolute', bottom: 0, left: 0, zIndex: 1 }}
                p="md"
              >
                <MapSettings disableSatellite={false} />
              </Box>
              <Attribution />
            </Map>
          )}
        </CustomCard>
      </Group>
      <CustomCard title="Combiner Current" style={{ height: '50vh' }}>
        <PlotlyPlot
          data={combinerData.data
            ?.filter((d) => d.sensor_type_name === 'pv_dc_combiner_current')
            .map((d) => {
              // Find the matching combiner data based on tag_name_scada
              const matchingCombiner = data.find(
                (c) => c.tag_name_scada === d.tag_name_scada,
              )
              return {
                x: d.x,
                y: d.y,
                name: `${
                  matchingCombiner?.combiner_name_long || d.device_name_long
                } - ${d.tag_name_scada}`,
                hoverlabel: {
                  namelength: -1,
                },
                line: {
                  color:
                    capacityDCsToColors[tagNameToCapacityDC[d.tag_name_scada]],
                  width: hoveredTagName === d.tag_name_scada ? 4 : 2, // Highlight line width
                },
              }
            })}
          layout={{
            yaxis: {
              title: 'Current (A)',
            },
          }}
          isLoading={combinerData.isLoading}
          error={combinerData.error}
        />
      </CustomCard>
      <CustomCard
        title="Combiner Current per Capacity"
        style={{ height: '50vh' }}
      >
        <PlotlyPlot
          data={combinerData.data
            ?.filter((d) => d.sensor_type_name === 'pv_dc_combiner_current')
            .map((d) => {
              // Find the matching combiner data based on tag_name_scada
              const matchingCombiner = data.find(
                (c) => c.tag_name_scada === d.tag_name_scada,
              )
              return {
                x: d.x,
                y: d.y.map((y) => y / tagNameToCapacityDC[d.tag_name_scada]),
                name: `${
                  matchingCombiner?.combiner_name_long || d.device_name_long
                } - ${d.tag_name_scada}`,
                hoverlabel: {
                  namelength: -1,
                },
                line: {
                  color:
                    capacityDCsToColors[tagNameToCapacityDC[d.tag_name_scada]],
                },
              }
            })}
          layout={{
            yaxis: {
              title: 'Specific Current (A/kWdc)',
            },
          }}
          isLoading={combinerData.isLoading}
          error={combinerData.error}
        />
      </CustomCard>
    </Stack>
  )
}

const SortableRow = ({
  combiner,
  setHoveredTagName,
}: {
  combiner: combinerData
  setHoveredTagName: (tagName: string | null) => void
}) => {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: combiner.combiner_device_id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    cursor: 'grab',
    backgroundColor:
      combiner.tag_name_scada !== combiner.original_tag_name_scada
        ? 'rgba(255, 220, 100, 0.2)'
        : undefined,
    height: '27px',
  }

  const formatTagName = (tag: string) => {
    if (tag.length > 26) {
      return `${tag.slice(0, 3)}[...]${tag.slice(-23)}`
    }
    return tag
  }

  return (
    <Table.Tr
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onMouseEnter={() => setHoveredTagName(combiner.tag_name_scada)}
      onMouseLeave={() => setHoveredTagName(null)}
    >
      <Table.Td style={{ padding: '2px 16px' }}>
        <Group gap="xs" wrap="nowrap">
          <Tooltip label={combiner.tag_name_scada}>
            <Text size="sm" style={{ whiteSpace: 'nowrap' }}>
              {formatTagName(combiner.tag_name_scada)}
            </Text>
          </Tooltip>
          {combiner.tag_name_scada !== combiner.original_tag_name_scada && (
            <IconArrowsExchange size={16} color="orange" />
          )}
        </Group>
      </Table.Td>
    </Table.Tr>
  )
}

export default Page
