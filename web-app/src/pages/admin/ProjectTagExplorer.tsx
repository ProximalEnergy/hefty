import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import {
  useAssignPatternSensorTypeMutation,
  useGetTagPatternSamples,
  useGetUniqueTagTypes,
} from '@/api/v1/operational/project/tags'
import {
  useCreateSensorTypeMutation,
  useGetSensorTypes,
} from '@/api/v1/operational/sensor_types'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import { SensorType } from '@/hooks/types'
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  NumberInput,
  Popover,
  Select,
  Stack,
  Tabs,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core'
import { hasLength, useForm } from '@mantine/form'
import { useDisclosure } from '@mantine/hooks'
import { IconEye, IconPlus, IconRefresh } from '@tabler/icons-react'
import {
  type MRT_Cell,
  MRT_ColumnDef,
  MantineReactTable,
  useMantineReactTable,
} from 'mantine-react-table'
import React, { useMemo, useState } from 'react'
import Plot from 'react-plotly.js'
import { useParams } from 'react-router-dom'

const ProjectTagExplorer = () => {
  const { projectId } = useParams()

  // Query parameters state
  const [limit, setLimit] = useState(500)
  const [sensorTypeFilter, setSensorTypeFilter] = useState<
    'assigned' | 'all' | 'unassigned'
  >('all')
  const [executionTime, setExecutionTime] = useState<number | null>(null)
  const [showColumnHandles, setShowColumnHandles] = useState(false)
  const [tagPatternAlignRight, setTagPatternAlignRight] = useState(true)
  const [isDetailsModalOpen, { open: openDetails, close: closeDetails }] =
    useDisclosure(false)
  const [isConfirmOpen, { open: openConfirm, close: closeConfirm }] =
    useDisclosure(false)
  const [selectedTagPattern, setSelectedTagPattern] = useState<string | null>(
    null,
  )

  // Get date range from URL search parameters (managed by AdvancedDatePicker)
  const { start, end } = useValidateDateRange({})

  const [patternSensorTypeId, setPatternSensorTypeId] = useState<string | null>(
    null,
  )
  const [patternUnitScale, setPatternUnitScale] = useState<number | null>(null)

  const [patternUnitOffset, setPatternUnitOffset] = useState<number | null>(
    null,
  )
  const [selectedSensorTypeUnit, setSelectedSensorTypeUnit] = useState<
    string | null
  >(null)

  // Create sensor type modal state
  const [
    isCreateSensorTypeModalOpen,
    { open: openCreateSensorType, close: closeCreateSensorType },
  ] = useDisclosure(false)
  const createSensorType = useCreateSensorTypeMutation()

  // Form for creating sensor type
  const createSensorTypeForm = useForm({
    initialValues: {
      device_type_id: '',
      name_short: '',
      name_long: '',
      name_metric: '',
      unit: '',
    },
    validate: {
      name_short: (value) => {
        if (!value || value.length === 0) {
          return 'Short name is required'
        }
        // Check for duplicates
        const isDuplicate = sensorTypes.data?.some(
          (sensorType) => sensorType.name_short === value,
        )
        if (isDuplicate) {
          return 'A sensor type with this short name already exists'
        }
        return null
      },
      name_long: hasLength({ min: 1 }, 'Long name is required'),
      name_metric: hasLength({ min: 1 }, 'Metric name is required'),
    },
  })

  // Get unique units from existing sensor types
  const getUniqueUnits = () => {
    if (!sensorTypes.data) return []
    const units = sensorTypes.data
      .map((sensorType) => sensorType.unit)
      .filter((unit) => unit !== null && unit !== '')
    return [...new Set(units)]
  }

  const uniqueTagTypes = useGetUniqueTagTypes({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      limit,
      include_null_sensor_types: sensorTypeFilter === 'all',
      only_null_sensor_types: sensorTypeFilter === 'unassigned',
    },
    queryOptions: {
      enabled: false, // Disable automatic fetching
    },
  })

  // No automatic execution time tracking - only manual refresh measurements

  // Custom refetch function that measures execution time
  const handleRefresh = async () => {
    const startTime = performance.now()
    setExecutionTime(null)

    try {
      if (uniqueTagTypes.data) {
        // If we have data, use refetch
        await uniqueTagTypes.refetch()
      } else {
        // If no data, trigger initial fetch
        await uniqueTagTypes.refetch()
      }
      const endTime = performance.now()
      setExecutionTime(Math.round(endTime - startTime))
    } catch (error) {
      console.error('Error refreshing data:', error)
    }
  }

  // Trigger initial load
  React.useEffect(() => {
    if (!uniqueTagTypes.data && !uniqueTagTypes.isFetching) {
      handleRefresh()
    }
  }, []) // Only run once on mount

  // Auto-refresh when sensor type filter changes
  React.useEffect(() => {
    // Simulate refresh button click to avoid white screen/spinner
    const startTime = performance.now()
    setExecutionTime(null)

    try {
      if (uniqueTagTypes.data) {
        // If we have data, use refetch
        uniqueTagTypes.refetch()
      } else {
        // If no data, trigger initial fetch
        uniqueTagTypes.refetch()
      }
      const endTime = performance.now()
      setExecutionTime(Math.round(endTime - startTime))
    } catch (error) {
      console.error('Error refreshing data:', error)
    }
  }, [sensorTypeFilter]) // Trigger when sensorTypeFilter changes

  // Load existing pattern data when modal opens
  React.useEffect(() => {
    if (selectedTagPattern && uniqueTagTypes.data) {
      const patternData = uniqueTagTypes.data.find(
        (t: any) => t.tag_pattern === selectedTagPattern,
      )

      if (patternData) {
        setPatternSensorTypeId(patternData.sensor_type_id?.toString() || null)

        setPatternUnitScale(patternData.unit_scale || null)
        setPatternUnitOffset(patternData.unit_offset || null)

        // Reset the unit first, then set it from the sensor type if available
        setSelectedSensorTypeUnit(null)

        if (patternData.sensor_type_id && sensorTypes.data) {
          const sensorType = sensorTypes.data.find(
            (st: SensorType) =>
              st.sensor_type_id === patternData.sensor_type_id,
          )
          setSelectedSensorTypeUnit(sensorType?.unit || null)
        }
      } else {
        // Reset all values if no pattern data found
        setPatternSensorTypeId(null)

        setPatternUnitScale(null)
        setPatternUnitOffset(null)
        setSelectedSensorTypeUnit(null)
      }
    } else {
      // Reset all values if no pattern selected
      setPatternSensorTypeId(null)

      setPatternUnitScale(null)
      setPatternUnitOffset(null)
      setSelectedSensorTypeUnit(null)
    }
  }, [selectedTagPattern, uniqueTagTypes.data])
  // Temporarily disabled due to performance issues with large datasets
  // const sensorTypeAssignments = useGetSensorTypeAssignments({
  //   pathParams: { projectId: projectId || '-1' },
  // })
  const sensorTypes = useGetSensorTypes({})
  const deviceTypes = useGetDeviceTypes({})

  const assignPatternSensorType = useAssignPatternSensorTypeMutation()

  // Get sample data for the selected pattern
  const tagPatternSamples = useGetTagPatternSamples({
    pathParams: {
      projectId: projectId || '-1',
      tagPattern: selectedTagPattern || '',
    },
    queryParams: {
      start: start?.toISOString(),
      end: end?.toISOString(),
    },
    queryOptions: {
      enabled: !!selectedTagPattern, // Only require selectedTagPattern, let backend handle default dates
      refetchOnWindowFocus: false,
      staleTime: 0, // Always refetch when parameters change
    },
  })

  // Group unique tag types by name_short to show "unique tag types"
  const groupedTagTypes = useMemo(() => {
    if (!uniqueTagTypes.data) return []

    // The data is already grouped by pattern from the backend
    return uniqueTagTypes.data.map((tagType: any) => ({
      tag_pattern: tagType.tag_pattern,
      sensor_type_id: tagType.sensor_type_id,
      scada_type: tagType.scada_type,
      unit_scada: tagType.unit_scada,
      unit_offset: tagType.unit_offset,
      unit_scale: tagType.unit_scale,
      total_count: tagType.count,
      examples: tagType.examples,
      sample_tag_id: tagType.sample_tag_id,
      project_id: tagType.project_id,
      project_name: tagType.project_name,
      project_name_short: tagType.project_name_short,
    }))
  }, [uniqueTagTypes.data])

  const handleAssignPatternSensorType = async () => {
    if (!selectedTagPattern || !patternSensorTypeId || !projectId) return

    try {
      await assignPatternSensorType.mutateAsync({
        projectId,
        tagPattern: selectedTagPattern,
        sensorTypeId: parseInt(patternSensorTypeId),
        unitScale: patternUnitScale,
        unitOffset: patternUnitOffset,
      })
      closeConfirm()
      closeDetails()
      // Refresh the data to show updated assignments
      uniqueTagTypes.refetch()
    } catch (error) {
      console.error('Error assigning sensor type to pattern:', error)
    }
  }

  const handleAssignPatternClick = () => {
    if (!selectedTagPattern || !patternSensorTypeId) {
      // Show some error message or validation
      return
    }
    openConfirm()
  }

  const handleCreateSensorType = () => {
    createSensorTypeForm.reset()
    openCreateSensorType()
  }

  // Handle device type selection to pre-populate long name
  const handleDeviceTypeChange = (deviceTypeId: string | null) => {
    if (deviceTypeId && deviceTypes.data) {
      const selectedDeviceType = deviceTypes.data.find(
        (dt) => dt.device_type_id.toString() === deviceTypeId,
      )
      if (selectedDeviceType) {
        createSensorTypeForm.setFieldValue('device_type_id', deviceTypeId)
        // Pre-populate the long name with the device type name
        createSensorTypeForm.setFieldValue(
          'name_long',
          selectedDeviceType.name_long,
        )
      }
    } else {
      createSensorTypeForm.setFieldValue('device_type_id', '')
      createSensorTypeForm.setFieldValue('name_long', '')
    }
  }

  const handleCreateSensorTypeSubmit = async (
    values: typeof createSensorTypeForm.values,
  ) => {
    try {
      // Remove device_type_id from values before submitting
      const { device_type_id, ...sensorTypeData } = values

      await createSensorType.mutateAsync({
        sensor_type_id: 0, // Will be auto-assigned by backend
        ...sensorTypeData,
      })
      closeCreateSensorType()
      // Refresh sensor types data
      sensorTypes.refetch()
    } catch (error) {
      console.error('Error creating sensor type:', error)
    }
  }

  const columns = useMemo<MRT_ColumnDef<any>[]>(
    () => [
      {
        header: 'Tag Pattern',
        accessorKey: 'tag_pattern',
        size: 300,
        mantineTableHeadCellProps: {
          align: 'left',
        },
        mantineTableBodyCellProps: {
          align: tagPatternAlignRight ? 'right' : 'left',
        },
        Cell: ({ cell }: { cell: MRT_Cell<any> }) => {
          const pattern = cell.getValue<string>()
          const parts = pattern.split('[INT]')

          return (
            <Tooltip
              label={
                cell.row.original.examples &&
                cell.row.original.examples.length > 0
                  ? `Examples: ${cell.row.original.examples.join(', ')}`
                  : 'No examples available'
              }
              disabled={
                !cell.row.original.examples ||
                cell.row.original.examples.length === 0
              }
            >
              <Text fw={500}>
                {parts.map((part, index) => (
                  <span key={index}>
                    {part}
                    {index < parts.length - 1 && (
                      <Text component="span" c="blue" fw={600}>
                        [INT]
                      </Text>
                    )}
                  </span>
                ))}
              </Text>
            </Tooltip>
          )
        },
      },
      {
        header: 'Sensor Type ID',
        accessorKey: 'sensor_type_id',
        size: 120,
        mantineTableHeadCellProps: {
          align: 'left',
        },
        mantineTableBodyCellProps: {
          align: 'center',
        },
        Cell: ({ cell }: { cell: MRT_Cell<any> }) => {
          const sensorTypeId = cell.getValue<number>()
          if (sensorTypeId === 0) {
            return (
              <Tooltip label="Click to assign sensor type">
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  onClick={() => {
                    setSelectedTagPattern(cell.row.original.tag_pattern)
                    openDetails()
                  }}
                >
                  <IconPlus style={{ width: 16, height: 16 }} />
                </ActionIcon>
              </Tooltip>
            )
          }
          return sensorTypeId
        },
      },
      {
        header: 'SCADA Type',
        accessorKey: 'scada_type',
        size: 150,
        mantineTableHeadCellProps: {
          align: 'left',
        },
      },
      {
        header: 'Unit SCADA',
        accessorKey: 'unit_scada',
        size: 150,
        mantineTableHeadCellProps: {
          align: 'left',
        },
      },
      {
        header: 'Unit Offset',
        accessorKey: 'unit_offset',
        size: 120,
        mantineTableHeadCellProps: {
          align: 'left',
        },
        mantineTableBodyCellProps: {
          align: 'center',
        },
      },
      {
        header: 'Unit Scale',
        accessorKey: 'unit_scale',
        size: 120,
        mantineTableHeadCellProps: {
          align: 'left',
        },
        mantineTableBodyCellProps: {
          align: 'center',
        },
      },
      {
        header: 'Total Count',
        accessorKey: 'total_count',
        size: 120,
        mantineTableHeadCellProps: {
          align: 'left',
        },
        mantineTableBodyCellProps: {
          align: 'center',
        },
      },
      {
        header: 'Example Tag ID',
        accessorKey: 'sample_tag_id',
        size: 120,
        mantineTableHeadCellProps: {
          align: 'left',
        },
        mantineTableBodyCellProps: {
          align: 'center',
        },
        Cell: ({ cell }: { cell: MRT_Cell<any> }) => {
          const sampleTagId = cell.getValue<number>()
          return sampleTagId || '-'
        },
      },
      // Project column removed
      {
        header: 'Actions',
        accessorKey: 'actions',
        size: 120,
        mantineTableHeadCellProps: {
          align: 'left',
        },
        mantineTableBodyCellProps: {
          align: 'center',
        },
        Cell: ({ cell }: { cell: MRT_Cell<any> }) => (
          <Group gap="xs" justify="center">
            <Tooltip label="View details">
              <ActionIcon
                variant="subtle"
                color="blue"
                onClick={() => {
                  setSelectedTagPattern(cell.row.original.tag_pattern)
                  openDetails()
                }}
              >
                <IconEye style={{ width: 16, height: 16 }} />
              </ActionIcon>
            </Tooltip>
          </Group>
        ),
        enableSorting: false,
        enableColumnFilter: false,
        enableGlobalFilter: false,
      },
    ],
    [open, tagPatternAlignRight],
  )

  const table = useMantineReactTable({
    columns,
    data: groupedTagTypes,
    enableGrouping: true,
    enableColumnDragging: showColumnHandles,
    enableColumnResizing: true,
    enableColumnOrdering: showColumnHandles,
    enableRowSelection: false,
    enableMultiSort: showColumnHandles,
    enableSorting: showColumnHandles,
    enableGlobalFilter: true,
    enableColumnFilters: true,
    enableDensityToggle: true,
    enableFullScreenToggle: true,
    enableHiding: true,
    layoutMode: 'grid',
    mantineTableBodyRowProps: ({ row }) => ({
      onClick: () => {
        setSelectedTagPattern(row.original.tag_pattern)
        openDetails()
      },
      style: { cursor: 'pointer' },
    }),
    initialState: {
      density: 'xs',
      columnVisibility: {
        tag_pattern: true,
        sensor_type_id: true,
        scada_type: false,
        unit_scada: false,
        unit_offset: true,
        unit_scale: true,
        total_count: true,
        sample_tag_id: true,
        actions: true,
      },
      sorting: [{ id: 'total_count', desc: true }],
      globalFilter: '',
      showGlobalFilter: true,
      pagination: {
        pageSize: 50,
        pageIndex: 0,
      },
    },
    mantineTableProps: {
      striped: true,
      highlightOnHover: true,
      style: { width: '100%' },
    },
  })

  if (
    uniqueTagTypes.isLoading ||
    sensorTypes.isLoading ||
    deviceTypes.isLoading
  ) {
    return <PageLoader />
  }

  return (
    <Stack p="md">
      <Group justify="space-between">
        <Group gap="md" align="center">
          <Title order={1}>Project Tag Explorer</Title>
          <Tooltip
            label={
              <Stack gap="xs" style={{ maxWidth: 400 }}>
                <Text size="sm" fw={500}>
                  ⚠️ Google Sheets Sync Warning
                </Text>
                <Text size="xs" c="dimmed">
                  The Google Sheet does not automatically sync with this file.
                  Changes made here will not update the Google Sheet.
                </Text>
                <Text size="xs" fw={500} c="blue">
                  Best Practice:
                </Text>
                <Text size="xs" c="dimmed">
                  Keep the Google Sheet called "_operational" and any
                  "[project].tags" manually updated in parallel with this method
                  for the time being. This way they will stay in sync until
                  we've fully transitioned.
                </Text>
              </Stack>
            }
            position="bottom"
            withArrow
            multiline
          >
            <Badge
              color="red"
              size="lg"
              variant="filled"
              style={{ cursor: 'help' }}
            >
              USE WITH CAUTION
            </Badge>
          </Tooltip>
        </Group>
        <Text size="sm" c="dimmed">
          View and manage tag types for this project.
        </Text>
      </Group>

      <Card withBorder>
        <Stack gap="md">
          <Title order={3}>Unique Tag Types</Title>
          <Text size="sm" c="dimmed">
            This table shows unique tag patterns for the current project. Tags
            are grouped by pattern with integers replaced by <b>[INT]</b>. You
            can assign sensor types to tag patterns to speed up project
            onboarding. Limited to 500 most common tag patterns for performance.
          </Text>

          {/* Query Controls */}
          <Group gap="lg" justify="space-between">
            <Group gap="lg">
              <NumberInput
                label="Result Limit"
                description="Maximum number of tag patterns to return (higher values may be slower)"
                value={limit}
                onChange={(value) =>
                  setLimit(typeof value === 'number' ? value : 500)
                }
                min={50}
                max={100000}
                step={50}
                style={{ minWidth: 200 }}
              />
              <Select
                label="Sensor Type Filter"
                description="Choose which tags to display"
                value={sensorTypeFilter}
                onChange={(value) =>
                  setSensorTypeFilter(
                    value as 'assigned' | 'all' | 'unassigned',
                  )
                }
                data={[
                  { value: 'assigned', label: 'Assigned Only' },
                  { value: 'all', label: 'All Tags' },
                  { value: 'unassigned', label: 'Unassigned Only' },
                ]}
                style={{ minWidth: 200 }}
              />
              <Group gap="xs" style={{ marginTop: 43 }}>
                <Button
                  variant="light"
                  leftSection={<IconRefresh size={16} />}
                  onClick={handleRefresh}
                  loading={uniqueTagTypes.isRefetching}
                >
                  Refresh
                </Button>
                {executionTime !== null && (
                  <Text size="sm" c="dimmed">
                    Execution time: {executionTime}ms
                  </Text>
                )}
              </Group>
            </Group>
            <Group gap="sm">
              <Button
                variant="light"
                onClick={() => setShowColumnHandles(!showColumnHandles)}
                style={{ marginTop: 43 }}
              >
                {showColumnHandles ? 'Hide' : 'Show'} Column Handles
              </Button>
              <Button
                variant="light"
                onClick={() => setTagPatternAlignRight(!tagPatternAlignRight)}
                style={{ marginTop: 43 }}
              >
                Tag Pattern: {tagPatternAlignRight ? 'Right' : 'Left'} Aligned
              </Button>
            </Group>
          </Group>
          <MantineReactTable table={table} />
        </Stack>
      </Card>

      {/* Temporarily disabled due to performance issues with large datasets */}
      {/* <Card withBorder>
        <Stack gap="md">
          <Title order={3}>Sensor Type Assignments</Title>
          <Text size="sm" c="dimmed">
            View which sensor types are currently assigned across projects.
          </Text>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Sensor Type</Table.Th>
                <Table.Th>Metric Name</Table.Th>
                <Table.Th>Unit</Table.Th>
                <Table.Th>Total Projects</Table.Th>
                <Table.Th>Projects</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {sensorTypeAssignments.data?.map(
                (assignment: SensorTypeAssignment) => (
                  <Table.Tr key={assignment.sensor_type_id}>
                    <Table.Td>
                      <Text fw={500}>{assignment.sensor_type_name_short}</Text>
                      <Text size="xs" c="dimmed">
                        {assignment.sensor_type_name_long}
                      </Text>
                    </Table.Td>
                    <Table.Td>{assignment.sensor_type_name_metric}</Table.Td>
                    <Table.Td>{assignment.sensor_type_unit || '-'}</Table.Td>
                    <Table.Td>{assignment.total_projects}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        {assignment.project_assignments.map((project) => (
                          <Badge
                            key={project.project_id}
                            size="sm"
                            variant="light"
                          >
                            {project.project_name_short} ({project.tag_count})
                          </Badge>
                        ))}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ),
              )}
            </Table.Tbody>
          </Table>
        </Stack>
      </Card> */}

      {/* Tag Pattern Details Modal */}
      <Modal
        opened={isDetailsModalOpen}
        onClose={closeDetails}
        title={
          selectedTagPattern ? (
            <span>
              Tag Pattern Details:{' '}
              {selectedTagPattern?.split('[INT]').map((part, index) => (
                <span key={index}>
                  {part}
                  {index < selectedTagPattern.split('[INT]').length - 1 && (
                    <Text component="span" c="blue" fw={600}>
                      [INT]
                    </Text>
                  )}
                </span>
              ))}
            </span>
          ) : (
            'Tag Pattern Details'
          )
        }
        size="xl"
      >
        <Stack gap="lg">
          {selectedTagPattern && (
            <>
              <Card withBorder>
                <Stack gap="md">
                  <Group justify="space-between" align="center">
                    <Title order={4}>Sample Data</Title>
                    <AdvancedDatePicker
                      defaultRange="past-3-days"
                      size="sm"
                      width={400}
                    />
                  </Group>
                  {tagPatternSamples.data?.sample_tags && (
                    <Group gap="lg">
                      <Text size="sm">
                        <strong>Total Tags:</strong>{' '}
                        {uniqueTagTypes.data?.find(
                          (t) => t.tag_pattern === selectedTagPattern,
                        )?.count || 0}
                      </Text>
                      <Text size="sm">
                        <strong>Sampled Tags:</strong>{' '}
                        {tagPatternSamples.data.sample_tags.length}
                      </Text>
                      <Text size="sm">
                        <strong>Numeric Tags:</strong>{' '}
                        {
                          tagPatternSamples.data.sample_tags.filter(
                            (tag: any) => tag.is_numeric,
                          ).length
                        }
                      </Text>
                      <Text size="sm">
                        <strong>Non-Numeric Tags:</strong>{' '}
                        {
                          tagPatternSamples.data.sample_tags.filter(
                            (tag: any) => !tag.is_numeric,
                          ).length
                        }
                      </Text>
                    </Group>
                  )}
                  {tagPatternSamples.isLoading ? (
                    <Text>Loading sample data...</Text>
                  ) : tagPatternSamples.error ? (
                    <Text c="red">
                      Error loading sample data:{' '}
                      {tagPatternSamples.error.message}
                    </Text>
                  ) : tagPatternSamples.data?.sample_tags &&
                    tagPatternSamples.data.sample_tags.length > 0 ? (
                    <Stack gap="md">
                      {/* Check if any tags have numeric data */}
                      {(() => {
                        const numericTags =
                          tagPatternSamples.data.sample_tags.filter(
                            (tag: any) =>
                              tag.is_numeric && tag.sample_values.length > 0,
                          )
                        const nonNumericTags =
                          tagPatternSamples.data.sample_tags.filter(
                            (tag: any) =>
                              !tag.is_numeric && tag.sample_values.length > 0,
                          )

                        return (
                          <>
                            {/* Numeric data - show as tabs with histogram and timeseries */}
                            {numericTags.length > 0 && (
                              <Tabs defaultValue="timeseries">
                                <Tabs.List>
                                  <Tabs.Tab value="timeseries">
                                    Timeseries
                                  </Tabs.Tab>
                                  <Tabs.Tab value="histogram">
                                    Histogram
                                  </Tabs.Tab>
                                </Tabs.List>

                                <Tabs.Panel value="timeseries" pt="xs">
                                  <Plot
                                    data={numericTags.map((tag: any) => ({
                                      x: tag.timestamps,
                                      y: tag.sample_values.map(
                                        (value: number) =>
                                          patternUnitScale
                                            ? value * patternUnitScale
                                            : value,
                                      ),
                                      type: 'scatter',
                                      mode: 'lines+markers',
                                      name: tag.tag_name,
                                      opacity: 0.7,
                                    }))}
                                    layout={{
                                      width: 600,
                                      height: 300,
                                      showlegend: false,
                                      margin: {
                                        l: 50,
                                        r: 20,
                                        t: 20,
                                        b: 50,
                                      },
                                      xaxis: {
                                        title: 'Time',
                                        type: 'date',
                                      },
                                      yaxis: {
                                        title: selectedSensorTypeUnit
                                          ? `Values (${selectedSensorTypeUnit})`
                                          : 'Values',
                                      },
                                    }}
                                    config={{ displayModeBar: false }}
                                  />
                                </Tabs.Panel>

                                <Tabs.Panel value="histogram" pt="xs">
                                  <Plot
                                    data={numericTags.map((tag: any) => ({
                                      x: tag.sample_values.map(
                                        (value: number) =>
                                          patternUnitScale
                                            ? value * patternUnitScale
                                            : value,
                                      ),
                                      type: 'histogram',
                                      name: tag.tag_name,
                                      opacity: 0.7,
                                      nbinsx: 20,
                                    }))}
                                    layout={{
                                      width: 600,
                                      height: 300,
                                      showlegend: false,
                                      margin: {
                                        l: 50,
                                        r: 20,
                                        t: 20,
                                        b: 50,
                                      },
                                      xaxis: {
                                        title: selectedSensorTypeUnit
                                          ? `Values (${selectedSensorTypeUnit})`
                                          : 'Values',
                                      },
                                      yaxis: { title: 'Frequency' },
                                    }}
                                    config={{ displayModeBar: false }}
                                  />
                                </Tabs.Panel>
                              </Tabs>
                            )}

                            {/* Non-numeric data - show as expanded list with unique values */}
                            {nonNumericTags.length > 0 && (
                              <Card withBorder variant="light">
                                <Stack gap="sm">
                                  <Text fw={500}>Non-Numeric Values</Text>
                                  <div
                                    style={{
                                      maxHeight: '300px',
                                      overflowY: 'auto',
                                      border: '1px solid #e0e0e0',
                                      borderRadius: '4px',
                                      padding: '8px',
                                    }}
                                  >
                                    {nonNumericTags.map((tag: any) => (
                                      <div
                                        key={tag.tag_id}
                                        style={{ marginBottom: '12px' }}
                                      >
                                        <Text size="sm" fw={500} c="blue">
                                          {tag.tag_name}:
                                        </Text>
                                        <Text
                                          size="xs"
                                          c="dimmed"
                                          style={{
                                            marginLeft: '16px',
                                            marginBottom: '4px',
                                          }}
                                        >
                                          {tag.sample_values.length} total
                                          values,{' '}
                                          {new Set(tag.sample_values).size}{' '}
                                          unique
                                        </Text>
                                        <Group
                                          gap="xs"
                                          wrap="wrap"
                                          style={{ marginLeft: '16px' }}
                                        >
                                          {/* Show unique values instead of all values */}
                                          {Array.from(
                                            new Set(tag.sample_values),
                                          )
                                            .slice(0, 20)
                                            .map(
                                              (
                                                value: any,
                                                valueIndex: number,
                                              ) => (
                                                <Badge
                                                  key={valueIndex}
                                                  size="xs"
                                                  variant="light"
                                                  color="gray"
                                                >
                                                  {String(value)}
                                                </Badge>
                                              ),
                                            )}
                                          {new Set(tag.sample_values).size >
                                            20 && (
                                            <Text size="xs" c="dimmed">
                                              +
                                              {new Set(tag.sample_values).size -
                                                20}{' '}
                                              more unique values...
                                            </Text>
                                          )}
                                        </Group>
                                      </div>
                                    ))}
                                  </div>
                                </Stack>
                              </Card>
                            )}

                            {/* Show message when no numeric data available */}
                            {numericTags.length === 0 &&
                              nonNumericTags.length === 0 && (
                                <Card withBorder variant="light">
                                  <Stack gap="sm">
                                    <Text fw={500}>
                                      No Sample Data Available
                                    </Text>
                                    <Text size="sm" c="dimmed">
                                      No timeseries data was found for the
                                      selected tags in the specified date range.
                                    </Text>
                                  </Stack>
                                </Card>
                              )}

                            {/* Assignment section */}
                            <Card withBorder variant="light">
                              <Stack gap="sm">
                                <Text fw={500}>Assignment</Text>
                                <Stack gap="md">
                                  <Group justify="space-between" align="center">
                                    <Text fw={500}>Sensor Type</Text>
                                    <Button
                                      variant="subtle"
                                      size="xs"
                                      leftSection={<IconPlus size={12} />}
                                      onClick={handleCreateSensorType}
                                    >
                                      Add New...
                                    </Button>
                                  </Group>
                                  <Select
                                    placeholder="Select a sensor type"
                                    searchable
                                    clearable
                                    value={patternSensorTypeId}
                                    data={
                                      sensorTypes.data?.map(
                                        (sensorType: SensorType) => ({
                                          value:
                                            sensorType.sensor_type_id.toString(),
                                          label: `${sensorType.name_short} - ${sensorType.name_long}`,
                                          unit: sensorType.unit,
                                        }),
                                      ) || []
                                    }
                                    onChange={(value) => {
                                      setPatternSensorTypeId(value)

                                      // Set the unit from the selected sensor type
                                      if (value && sensorTypes.data) {
                                        const sensorType =
                                          sensorTypes.data.find(
                                            (st: SensorType) =>
                                              st.sensor_type_id.toString() ===
                                              value,
                                          )
                                        setSelectedSensorTypeUnit(
                                          sensorType?.unit || null,
                                        )
                                      } else {
                                        setSelectedSensorTypeUnit(null)
                                      }
                                    }}
                                  />

                                  {selectedSensorTypeUnit && (
                                    <Text size="sm" c="blue" fw={500}>
                                      Unit: {selectedSensorTypeUnit}
                                    </Text>
                                  )}

                                  <Group gap="md" grow>
                                    <div>
                                      <Tooltip
                                        label="e.g., 0.000001 to convert MW to W"
                                        position="top"
                                      >
                                        <Text
                                          size="sm"
                                          fw={500}
                                          style={{ marginBottom: '8px' }}
                                        >
                                          Unit Scale Multiplier
                                        </Text>
                                      </Tooltip>
                                      <Group gap="xs" align="center">
                                        <Text size="sm">SCADA value ×</Text>
                                        <NumberInput
                                          placeholder="1"
                                          value={patternUnitScale || undefined}
                                          onChange={(value) =>
                                            setPatternUnitScale(
                                              typeof value === 'number'
                                                ? value
                                                : null,
                                            )
                                          }
                                          min={0}
                                          step={0.000001}
                                          decimalScale={6}
                                          style={{ width: '120px' }}
                                          size="xs"
                                        />
                                        <Text size="sm">
                                          → {selectedSensorTypeUnit || 'Unit'}
                                        </Text>
                                      </Group>
                                    </div>

                                    <div>
                                      <Tooltip
                                        label="Usually null/empty (not often used)"
                                        position="top"
                                      >
                                        <Text
                                          size="sm"
                                          fw={500}
                                          style={{ marginBottom: '8px' }}
                                        >
                                          Unit Offset
                                        </Text>
                                      </Tooltip>
                                      <NumberInput
                                        placeholder="0 (default)"
                                        value={patternUnitOffset || undefined}
                                        onChange={(value) =>
                                          setPatternUnitOffset(
                                            typeof value === 'number'
                                              ? value
                                              : null,
                                          )
                                        }
                                        step={0.01}
                                        decimalScale={2}
                                        size="xs"
                                      />
                                    </div>
                                  </Group>

                                  <Button
                                    variant="light"
                                    color="blue"
                                    onClick={handleAssignPatternClick}
                                    loading={assignPatternSensorType.isPending}
                                    disabled={!patternSensorTypeId}
                                    fullWidth
                                  >
                                    Assign to Pattern
                                  </Button>
                                  <Button
                                    variant="subtle"
                                    onClick={closeDetails}
                                    fullWidth
                                  >
                                    Cancel
                                  </Button>
                                </Stack>
                              </Stack>
                            </Card>
                          </>
                        )
                      })()}
                    </Stack>
                  ) : (
                    <Text c="dimmed">
                      No sample data available for this pattern. This could be
                      because:
                      <br />• No tags match this pattern in the database
                      <br />• The tags exist but have no timeseries data in the
                      selected date range
                    </Text>
                  )}
                </Stack>
              </Card>
            </>
          )}
        </Stack>
      </Modal>

      {/* Confirmation Modal for Pattern Assignment */}
      <Modal
        opened={isConfirmOpen}
        onClose={closeConfirm}
        title="Confirm Pattern Assignment"
        size="sm"
      >
        <Stack gap="md">
          <Text>
            Are you sure you want to assign the sensor type "
            {
              sensorTypes.data?.find(
                (st) => st.sensor_type_id.toString() === patternSensorTypeId,
              )?.name_short
            }
            " to all tags matching the pattern "{selectedTagPattern}"?
          </Text>
          {patternUnitScale && (
            <Text size="sm" c="dimmed">
              This will also set the unit scale multiplier to {patternUnitScale}
              .
            </Text>
          )}
          {patternUnitOffset && (
            <Text size="sm" c="dimmed">
              This will also set the unit offset to {patternUnitOffset}.
            </Text>
          )}
          <Text size="sm" c="red">
            This action will update all tags that match this pattern in the
            database.
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button variant="subtle" onClick={closeConfirm}>
              Cancel
            </Button>
            <Button
              color="blue"
              onClick={handleAssignPatternSensorType}
              loading={assignPatternSensorType.isPending}
            >
              Yes, Assign to Pattern
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Create Sensor Type Modal */}
      <Modal
        opened={isCreateSensorTypeModalOpen}
        onClose={closeCreateSensorType}
        title="Add Sensor Type"
        size="md"
      >
        <form
          onSubmit={createSensorTypeForm.onSubmit(handleCreateSensorTypeSubmit)}
        >
          <Stack gap="md">
            <Tooltip
              label="Select a device type to automatically pre-populate the long name"
              position="top"
              multiline
            >
              <Select
                label="Device Type"
                placeholder="Select a device type..."
                data={
                  deviceTypes.data?.map((dt) => ({
                    value: dt.device_type_id.toString(),
                    label: `${dt.name_long} (${dt.name_short})`,
                  })) || []
                }
                value={createSensorTypeForm.values.device_type_id}
                onChange={handleDeviceTypeChange}
                searchable
                clearable
                required
              />
            </Tooltip>
            <Tooltip
              label="Device comes first, then a full name for the sensor type. Each word starts with a capital letter. Example: PV PCS AC Power, Tracker Position"
              position="top"
              multiline
            >
              <TextInput
                label="Long Name"
                placeholder="e.g., PV PCS AC Power"
                required
                {...createSensorTypeForm.getInputProps('name_long')}
                onChange={(event) => {
                  const longName = event.currentTarget.value
                  const shortName = longName
                    .toLowerCase()
                    .replace(/\s+/g, '_')
                    .replace(/[^a-z0-9_]/g, '')
                  createSensorTypeForm.setFieldValue('name_short', shortName)
                  // Trigger validation on short name after setting the value
                  setTimeout(
                    () => createSensorTypeForm.validateField('name_short'),
                    0,
                  )
                  createSensorTypeForm
                    .getInputProps('name_long')
                    .onChange(event)
                }}
              />
            </Tooltip>
            <Tooltip
              label="Automatically generated from the Long Name. All lowercase with underscores instead of spaces. You can edit this field if needed."
              position="top"
              multiline
            >
              <TextInput
                label="Short Name"
                placeholder="e.g., pv_pcs_ac_power"
                required
                {...createSensorTypeForm.getInputProps('name_short')}
                onChange={(event) => {
                  // Trigger validation immediately
                  createSensorTypeForm.validateField('name_short')
                  createSensorTypeForm
                    .getInputProps('name_short')
                    .onChange(event)
                }}
              />
            </Tooltip>
            <Tooltip
              label="Same as Long Name but remove the device name that is prepended. Example: If Long Name is 'Inverter AC Power', Metric Name should be 'AC Power'"
              position="top"
              multiline
            >
              <TextInput
                label="Metric Name"
                placeholder="e.g., AC Power"
                required
                {...createSensorTypeForm.getInputProps('name_metric')}
              />
            </Tooltip>
            <Popover position="top" withArrow shadow="md">
              <Popover.Target>
                <TextInput
                  label="Unit"
                  placeholder="W/m2"
                  {...createSensorTypeForm.getInputProps('unit')}
                />
              </Popover.Target>
              <Popover.Dropdown>
                <Stack gap="xs">
                  <Text size="sm" fw={500}>
                    Unit of measurement (optional)
                  </Text>
                  <Text size="xs" c="dimmed">
                    Examples: kW, %, °C, V
                  </Text>
                  <Text size="xs" fw={500}>
                    Existing units:
                  </Text>
                  <Text size="xs">
                    {getUniqueUnits().length > 0
                      ? getUniqueUnits().join(', ')
                      : 'No existing units found'}
                  </Text>
                  <Text size="xs" c="dimmed" style={{ fontStyle: 'italic' }}>
                    Try to stick to existing units when possible, but you can
                    type a new one if necessary.
                  </Text>
                </Stack>
              </Popover.Dropdown>
            </Popover>
            <Group justify="flex-end" gap="sm">
              <Button
                variant="subtle"
                onClick={closeCreateSensorType}
                disabled={createSensorType.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" loading={createSensorType.isPending}>
                Create
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Stack>
  )
}

export default ProjectTagExplorer
