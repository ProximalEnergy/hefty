import { SensorTypeEnum } from '@/api/enumerations'
import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import {
  SensorType,
  useCreateSensorTypeMutation,
  useGetSensorTypes,
} from '@/api/v1/operational/sensor_types'
import {
  useAssignPatternSensorTypeMutation,
  useGetTagPatternSamples,
  useGetTagsByPattern,
  useGetUniqueTagTypes,
  usePutUniqueTagPatterns,
} from '@/api/v1/protected/web-application/projects/project-tag-explorer'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { QUERY_TIME } from '@/utils/queryTiming'
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Group,
  LoadingOverlay,
  Select as MantineSelect,
  Modal,
  NumberInput,
  Pagination,
  Popover,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
  Tooltip,
  UnstyledButton,
} from '@mantine/core'
import { hasLength, useForm } from '@mantine/form'
import { useDisclosure } from '@mantine/hooks'
import {
  IconChevronDown,
  IconChevronUp,
  IconInfoCircle,
  IconPlus,
  IconRefresh,
} from '@tabler/icons-react'
import {
  type Column,
  type ColumnDef,
  type ColumnFiltersState,
  type FilterFn,
  type PaginationState,
  type RowData,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import React, { useMemo, useState } from 'react'
import { useParams } from 'react-router'

import { getUniqueUnits } from './sensorTypeUnits'

dayjs.extend(utc)
dayjs.extend(timezone)

type TagPatternRow = {
  tag_pattern: string
  device_type_name: string | null
  sensor_type_id: number | null
  sensor_type_name_short: string | null
  sensor_type_name_long: string | null
  scada_type: string | null
  unit_scada: string | null
  unit_offset: number | null
  unit_scale: number | null
  total_count: number
  examples: unknown[]
  sample_tag_id: number | null
  project_id: string
  project_name: string
  project_name_short: string
}

type AssignedSensorTypeRow = {
  sensor_type_id: number
  device_type_id: number
  name_short: string
  name_long: string
  name_metric: string | null
  unit: string | null
  assigned: boolean
  device_type_name: string | null
}

declare module '@tanstack/react-table' {
  interface ColumnMeta<TData extends RowData, TValue> {
    align?: 'left' | 'center' | 'right'
    filterVariant?: 'text' | 'boolean'
  }
}

const getAlignment = (
  align?: 'left' | 'center' | 'right',
): 'left' | 'center' | 'right' => {
  return align ?? 'left'
}

const stringifiedFilter: FilterFn<unknown> = (row, columnId, filterValue) => {
  const value = row.getValue(columnId)
  const filterText = String(filterValue ?? '')
    .trim()
    .toLowerCase()

  if (filterText.length === 0) {
    return true
  }

  return String(value ?? '')
    .toLowerCase()
    .includes(filterText)
}

const booleanSelectFilter: FilterFn<unknown> = (row, columnId, filterValue) => {
  if (filterValue !== 'true' && filterValue !== 'false') {
    return true
  }

  return String(Boolean(row.getValue(columnId))) === filterValue
}

const toggleSort = <TData extends object>(column: Column<TData, unknown>) => {
  const currentSort = column.getIsSorted()

  if (currentSort === false) {
    column.toggleSorting(false)
    return
  }

  if (currentSort === 'asc') {
    column.toggleSorting(true)
    return
  }

  column.clearSorting()
}

const renderPatternParts = (parts: string[]) => {
  const lastIndex = parts.length - 1

  return parts.map((part, index) => {
    const showIntToken = index < lastIndex

    return (
      <span key={index}>
        {part}
        {showIntToken && (
          <Text component="span" c="blue" fw={600}>
            [INT]
          </Text>
        )}
      </span>
    )
  })
}

const transformSampleValue = ({
  value,
  patternUnitScale,
  patternUnitOffset,
}: {
  value: number | string
  patternUnitScale: number | null
  patternUnitOffset: number | null
}) => {
  let transformedValue =
    typeof value === 'string' ? Number.parseFloat(value) : value

  if (patternUnitScale !== null) {
    transformedValue = transformedValue * patternUnitScale
  }

  if (patternUnitOffset !== null) {
    transformedValue = transformedValue + patternUnitOffset
  }

  return transformedValue
}

type TanStackMantineTableProps<TData extends object> = {
  columns: ColumnDef<TData>[]
  data: TData[]
  emptyText: string
  initialPagination: PaginationState
  initialSorting: SortingState
  isLoading?: boolean
  onRowClick?: (row: TData) => void
  searchPlaceholder?: string
}

function TanStackMantineTable<TData extends object>({
  columns,
  data,
  emptyText,
  initialPagination,
  initialSorting,
  isLoading = false,
  onRowClick,
  searchPlaceholder = 'Search all columns',
}: TanStackMantineTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>(initialSorting)
  const [globalFilter, setGlobalFilter] = useState('')
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [pagination, setPagination] =
    useState<PaginationState>(initialPagination)
  const defaultStringFilter = useMemo(
    () => stringifiedFilter as FilterFn<TData>,
    [],
  )

  const table = useReactTable<TData>({
    columns,
    data,
    state: {
      sorting,
      globalFilter,
      columnFilters,
      pagination,
    },
    defaultColumn: {
      size: 160,
      minSize: 80,
      filterFn: defaultStringFilter,
      enableColumnFilter: true,
      enableSorting: true,
      enableResizing: true,
    },
    columnResizeMode: 'onChange',
    globalFilterFn: defaultStringFilter,
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  const visibleColumns = table.getVisibleLeafColumns()
  const visibleRows = table.getRowModel().rows
  const pageCount = Math.max(table.getPageCount(), 1)
  const colspan = visibleColumns.length || 1
  const currentPage = pagination.pageIndex + 1
  const handlePageChange = (page: number) => {
    table.setPageIndex(page - 1)
  }

  React.useEffect(() => {
    if (pageCount === 0 && pagination.pageIndex !== 0) {
      table.setPageIndex(0)
      return
    }

    if (pagination.pageIndex >= pageCount && pageCount > 0) {
      table.setPageIndex(pageCount - 1)
    }
  }, [pageCount, pagination.pageIndex, table])

  return (
    <Stack gap="sm">
      <Group justify="space-between" align="flex-end">
        <TextInput
          label="Search"
          placeholder={searchPlaceholder}
          value={globalFilter}
          onChange={(event) => setGlobalFilter(event.currentTarget.value)}
          style={{ minWidth: 280 }}
        />
      </Group>

      <Box pos="relative">
        <LoadingOverlay visible={isLoading} zIndex={1} />
        <Table.ScrollContainer minWidth="100%">
          <Table
            striped
            highlightOnHover
            stickyHeader
            horizontalSpacing="sm"
            verticalSpacing="xs"
            fz="sm"
            style={{ width: Math.max(table.getTotalSize(), 960) }}
          >
            <Table.Thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <React.Fragment key={headerGroup.id}>
                  <Table.Tr>
                    {headerGroup.headers.map((header) => {
                      const align = getAlignment(
                        header.column.columnDef.meta?.align,
                      )

                      return (
                        <Table.Th
                          key={header.id}
                          style={{
                            position: 'relative',
                            width: header.getSize(),
                            minWidth: header.column.columnDef.minSize,
                            textAlign: align,
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {header.isPlaceholder ? null : (
                            <>
                              <UnstyledButton
                                onClick={() => toggleSort(header.column)}
                                style={{
                                  width: '100%',
                                  display: 'flex',
                                  justifyContent:
                                    align === 'left'
                                      ? 'flex-start'
                                      : align === 'center'
                                        ? 'center'
                                        : 'flex-end',
                                }}
                              >
                                <Group gap={4} wrap="nowrap">
                                  <Text fw={600} size="sm">
                                    {flexRender(
                                      header.column.columnDef.header,
                                      header.getContext(),
                                    )}
                                  </Text>
                                  {header.column.getIsSorted() === 'asc' && (
                                    <IconChevronUp size={14} />
                                  )}
                                  {header.column.getIsSorted() === 'desc' && (
                                    <IconChevronDown size={14} />
                                  )}
                                </Group>
                              </UnstyledButton>
                              {header.column.getCanResize() && (
                                <Box
                                  onDoubleClick={() =>
                                    header.column.resetSize()
                                  }
                                  onMouseDown={header.getResizeHandler()}
                                  onTouchStart={header.getResizeHandler()}
                                  style={{
                                    position: 'absolute',
                                    top: 0,
                                    right: 0,
                                    width: 8,
                                    height: '100%',
                                    cursor: 'col-resize',
                                    userSelect: 'none',
                                  }}
                                />
                              )}
                            </>
                          )}
                        </Table.Th>
                      )
                    })}
                  </Table.Tr>
                  <Table.Tr>
                    {headerGroup.headers.map((header) => {
                      const column = header.column
                      const filterVariant =
                        column.columnDef.meta?.filterVariant ?? 'text'
                      const filterValue = column.getFilterValue()
                      const align = getAlignment(column.columnDef.meta?.align)

                      return (
                        <Table.Th
                          key={`${header.id}-filter`}
                          style={{
                            width: header.getSize(),
                            minWidth: header.column.columnDef.minSize,
                            textAlign: align,
                          }}
                        >
                          {!column.getCanFilter() ? null : filterVariant ===
                            'boolean' ? (
                            <MantineSelect
                              size="xs"
                              clearable
                              placeholder="All"
                              value={
                                typeof filterValue === 'string'
                                  ? filterValue
                                  : null
                              }
                              data={[
                                { value: 'true', label: 'Yes' },
                                { value: 'false', label: 'No' },
                              ]}
                              onChange={(value) =>
                                column.setFilterValue(value ?? undefined)
                              }
                            />
                          ) : (
                            <TextInput
                              size="xs"
                              placeholder="Filter"
                              value={
                                typeof filterValue === 'string'
                                  ? filterValue
                                  : ''
                              }
                              onChange={(event) =>
                                column.setFilterValue(
                                  event.currentTarget.value || undefined,
                                )
                              }
                            />
                          )}
                        </Table.Th>
                      )
                    })}
                  </Table.Tr>
                </React.Fragment>
              ))}
            </Table.Thead>
            <Table.Tbody>
              {visibleRows.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={colspan}>
                    <Text size="sm" c="dimmed">
                      {emptyText}
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                visibleRows.map((row) => (
                  <Table.Tr
                    key={row.id}
                    onClick={() => onRowClick?.(row.original)}
                    style={{
                      cursor: onRowClick ? 'pointer' : undefined,
                    }}
                  >
                    {row.getVisibleCells().map((cell) => {
                      const align = getAlignment(
                        cell.column.columnDef.meta?.align,
                      )

                      return (
                        <Table.Td
                          key={cell.id}
                          style={{
                            width: cell.column.getSize(),
                            minWidth: cell.column.columnDef.minSize,
                            textAlign: align,
                            overflow: 'hidden',
                          }}
                        >
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext(),
                          )}
                        </Table.Td>
                      )
                    })}
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Box>

      <Group justify="space-between" align="center">
        <Group gap="xs" align="center">
          <Text size="sm">Rows per page</Text>
          <MantineSelect
            size="xs"
            w={90}
            value={String(pagination.pageSize)}
            data={['25', '50', '100'].map((value) => ({
              value,
              label: value,
            }))}
            onChange={(value) => {
              if (!value) return
              table.setPageSize(Number(value))
              table.setPageIndex(0)
            }}
          />
        </Group>
        <Pagination
          size="sm"
          total={pageCount}
          value={currentPage}
          onChange={handlePageChange}
        />
      </Group>
    </Stack>
  )
}

const ProjectTagExplorer = () => {
  const { projectId } = useParams<{ projectId: string }>()

  // Query parameters state
  // Removed legacy sensor type filter; use table filters instead
  const [executionTime, setExecutionTime] = useState<number | null>(null)
  const [isTableRefreshing, setIsTableRefreshing] = useState(false)
  const [tagPatternAlignRight, setTagPatternAlignRight] = useState(false)
  const [showOnlyUnassigned, setShowOnlyUnassigned] = useState(false)
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
  const [patternUnitScada, setPatternUnitScada] = useState<string | null>(null)
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
      name_short: '', // noqa: hardcoded-name-short
      name_long: '',
      name_metric: '',
      unit: '',
      description: '',
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

  const uniqueTagTypes = useGetUniqueTagTypes({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled: false, // Disable automatic fetching
    },
  })

  const sensorTypes = useGetSensorTypes({})
  const uniqueUnits = getUniqueUnits(sensorTypes.data)
  const deviceTypes = useGetDeviceTypes({})
  const project = useSelectProject(projectId!)

  // Predefined list of common SCADA units
  const predefinedUnits = [
    // Temperature
    'C',
    'F',
    'K',
    // Power
    'W',
    'kW',
    'MW',
    'GW',
    // Voltage
    'mV',
    'V',
    'kV',
    'MV',
    'p.u.',
    // Current
    'mA',
    'A',
    'kA',
    // Energy
    'Wh',
    'kWh',
    'MWh',
    'GWh',
    'J',
    'kJ',
    'MJ',
    // Reactive Power
    'VAR',
    'kVAR',
    'MVAR',
    // Apparent Power
    'VA',
    'kVA',
    'MVA',
    // Frequency
    'Hz',
    // No Unit
    '-',
    // Percentage
    '%',
    // Degrees for tracker position:
    'Degrees',
  ]

  const putUniqueTagPatterns = usePutUniqueTagPatterns()

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

  // Handle populate unique tag patterns
  const handlePopulatePatterns = async () => {
    if (!projectId) return

    try {
      await putUniqueTagPatterns.mutateAsync({
        projectId,
      })
      // After population, explicitly refetch and show a spinner on the table
      setIsTableRefreshing(true)
      await uniqueTagTypes.refetch()
      setIsTableRefreshing(false)
    } catch (error) {
      console.error('Error populating unique tag patterns:', error)
    }
  }

  // Trigger initial load
  React.useEffect(() => {
    if (!uniqueTagTypes.data && !uniqueTagTypes.isFetching) {
      handleRefresh()
    }
  }, []) // oxlint-disable-line react/exhaustive-deps

  // Auto-refresh when project changes (e.g., via project dropdown)
  React.useEffect(() => {
    // Clear any selection tied to previous project
    setSelectedTagPattern(null)
    // Refetch unique tag types for the new project
    handleRefresh()
    // oxlint-disable-next-line react/exhaustive-deps
  }, [projectId])

  // Removed legacy sensor type filter

  // Load existing pattern data when modal opens
  React.useEffect(() => {
    if (selectedTagPattern && uniqueTagTypes.data) {
      const patternData = uniqueTagTypes.data.find(
        (t) => t.tag_pattern === selectedTagPattern,
      )

      if (patternData) {
        setPatternSensorTypeId(patternData.sensor_type_id?.toString() || null)

        setPatternUnitScale(patternData.unit_scale ?? null)
        setPatternUnitOffset(patternData.unit_offset ?? null)
        setPatternUnitScada(patternData.unit_scada || null)

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
        setPatternUnitScada(null)
        setSelectedSensorTypeUnit(null)
      }
    } else {
      // Reset all values if no pattern selected
      setPatternSensorTypeId(null)

      setPatternUnitScale(null)
      setPatternUnitOffset(null)
      setPatternUnitScada(null)
      setSelectedSensorTypeUnit(null)
    }
  }, [selectedTagPattern, uniqueTagTypes.data, sensorTypes.data])

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
      enabled: !!selectedTagPattern,
    },
  })

  // Fetch all tags matching the selected pattern to compute [INT] ranges
  const tagsByPattern = useGetTagsByPattern({
    pathParams: {
      projectId: projectId || '-1',
      tagPattern: selectedTagPattern || '',
    },
    queryOptions: {
      enabled: !!selectedTagPattern,
      refetchOnWindowFocus: false,
      staleTime: QUERY_TIME.ZERO,
    },
  })

  const intRanges = useMemo(() => {
    if (!selectedTagPattern || !tagsByPattern.data)
      return [] as Array<{ index: number; min: number; max: number }>
    const parts = selectedTagPattern.split('[INT]')
    const countINT = parts.length - 1
    const mins = Array.from(
      { length: countINT },
      () => Number.POSITIVE_INFINITY,
    )
    const maxs = Array.from(
      { length: countINT },
      () => Number.NEGATIVE_INFINITY,
    )

    for (const t of tagsByPattern.data) {
      const name: string = t.name_scada
      if (!name) continue
      let cursor = 0
      let ok = true
      for (let i = 0; i < countINT; i++) {
        const fixed = parts[i]
        const pos = name.indexOf(fixed, cursor)
        if (pos === -1) {
          ok = false
          break
        }
        cursor = pos + fixed.length
        let j = cursor
        while (
          j < name.length &&
          name.charCodeAt(j) >= 48 &&
          name.charCodeAt(j) <= 57
        )
          j++
        if (j === cursor) {
          ok = false
          break
        }
        const num = parseInt(name.slice(cursor, j), 10)
        if (!Number.isNaN(num)) {
          if (num < mins[i]) mins[i] = num
          if (num > maxs[i]) maxs[i] = num
        }
        cursor = j
      }
      if (!ok) continue
    }
    return mins.map((mn, i) => ({ index: i, min: mn, max: maxs[i] }))
  }, [selectedTagPattern, tagsByPattern.data])

  // Group unique tag types by name_short to show "unique tag types"
  const groupedTagTypes = useMemo(() => {
    if (!uniqueTagTypes.data) return []

    return uniqueTagTypes.data.map((tagType) => {
      const st = sensorTypes.data?.find(
        (s: SensorType) => s.sensor_type_id === tagType.sensor_type_id,
      )
      return {
        tag_pattern: tagType.tag_pattern,
        device_type_name: tagType.device_type_name,
        sensor_type_id: tagType.sensor_type_id,
        sensor_type_name_short: st?.name_short || null,
        sensor_type_name_long: st?.name_long || null,
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
      }
    })
  }, [uniqueTagTypes.data, sensorTypes.data])

  // Filter groupedTagTypes to show only unassigned when checkbox is checked
  const filteredGroupedTagTypes = useMemo(() => {
    if (!showOnlyUnassigned) return groupedTagTypes
    return groupedTagTypes.filter(
      (row: (typeof groupedTagTypes)[number]) =>
        !row.sensor_type_id ||
        row.sensor_type_id === SensorTypeEnum.GHOST_UNKNOWN,
    )
  }, [groupedTagTypes, showOnlyUnassigned])
  const selectedPatternRow = useMemo(() => {
    if (!selectedTagPattern) return null
    return groupedTagTypes.find((row) => row.tag_pattern === selectedTagPattern)
  }, [groupedTagTypes, selectedTagPattern])
  const selectedTagPatternParts = useMemo(
    () => (selectedTagPattern ? selectedTagPattern.split('[INT]') : []),
    [selectedTagPattern],
  )
  const selectedTagPatternTitle = useMemo(() => {
    if (!selectedTagPattern) {
      return 'Tag Pattern Details'
    }

    return (
      <span>
        Tag Pattern Details: {renderPatternParts(selectedTagPatternParts)}
      </span>
    )
  }, [selectedTagPattern, selectedTagPatternParts])
  const intRangeNodes = useMemo(() => {
    if (!selectedTagPattern) return null

    const nodes: React.ReactNode[] = []

    for (let i = 0; i < selectedTagPatternParts.length; i++) {
      nodes.push(selectedTagPatternParts[i])

      if (i < intRanges.length) {
        const range = intRanges[i]
        const hasFiniteRange =
          Number.isFinite(range.min) && Number.isFinite(range.max)
        const rangeText = hasFiniteRange ? `${range.min}-${range.max}` : '—'

        nodes.push(
          <Text key={`range-${i}`} component="span" c="blue" fw={600}>
            [{rangeText}]
          </Text>,
        )
      }
    }

    return nodes
  }, [intRanges, selectedTagPattern, selectedTagPatternParts])
  const sampleTags = useMemo(
    () => tagPatternSamples.data?.sample_tags ?? [],
    [tagPatternSamples.data?.sample_tags],
  )
  const sampledTagCount = sampleTags.length
  const numericTagCount = useMemo(
    () => sampleTags.filter((tag) => tag.is_numeric).length,
    [sampleTags],
  )
  const nonNumericTagCount = useMemo(
    () => sampleTags.filter((tag) => !tag.is_numeric).length,
    [sampleTags],
  )
  const numericTagsWithSamples = useMemo(
    () =>
      sampleTags.filter(
        (tag) => tag.is_numeric && tag.sample_values.length > 0,
      ),
    [sampleTags],
  )
  const nonNumericTagsWithSamples = useMemo(
    () =>
      sampleTags.filter(
        (tag) => !tag.is_numeric && tag.sample_values.length > 0,
      ),
    [sampleTags],
  )
  const timezoneName = project.data?.time_zone ?? 'UTC'
  const selectedUnitLabel = selectedSensorTypeUnit
    ? `Values (${selectedSensorTypeUnit})`
    : 'Values'
  const selectedUnitTickFormat =
    selectedSensorTypeUnit && selectedSensorTypeUnit.toLowerCase().includes('%')
      ? ',.0%'
      : undefined
  const numericTimeseriesData = useMemo(
    () =>
      numericTagsWithSamples.map((tag) => ({
        x: tag.timestamps,
        y: tag.sample_values.map((value: string | number) =>
          transformSampleValue({
            value,
            patternUnitScale,
            patternUnitOffset,
          }),
        ),
        type: 'scatter' as const,
        mode: 'lines+markers' as const,
        name: tag.tag_name,
        hoverlabel: { namelength: -1 },
      })),
    [numericTagsWithSamples, patternUnitOffset, patternUnitScale],
  )
  const numericHistogramData = useMemo(
    () =>
      numericTagsWithSamples.map((tag) => ({
        x: tag.sample_values.map((value: string | number) =>
          transformSampleValue({
            value,
            patternUnitScale,
            patternUnitOffset,
          }),
        ),
        type: 'histogram' as const,
        name: tag.tag_name,
        nbinsx: 20,
        hoverlabel: { namelength: -1 },
      })),
    [numericTagsWithSamples, patternUnitOffset, patternUnitScale],
  )
  const nonNumericTagSummaries = useMemo(
    () =>
      nonNumericTagsWithSamples.map((tag) => {
        const uniqueValues = Array.from(new Set(tag.sample_values))
        const uniqueValueCount = uniqueValues.length
        const visibleUniqueValues = uniqueValues.slice(0, 20)
        const remainingUniqueValueCount = Math.max(uniqueValueCount - 20, 0)

        return {
          tagId: tag.tag_id,
          tagName: tag.tag_name,
          totalValueCount: tag.sample_values.length,
          uniqueValueCount,
          visibleUniqueValues,
          remainingUniqueValueCount,
        }
      }),
    [nonNumericTagsWithSamples],
  )

  const handleAssignPatternSensorType = async () => {
    if (!selectedTagPattern || !patternSensorTypeId || !projectId) return

    try {
      await assignPatternSensorType.mutateAsync({
        projectId,
        tagPattern: selectedTagPattern,
        sensorTypeId: parseInt(patternSensorTypeId),
        unitScale: patternUnitScale,
        unitOffset: patternUnitOffset,
        unitScada: patternUnitScada,
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
  const handleProjectTagDeviceTypeChange = (deviceTypeId: string | null) => {
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
      const sensorTypeData = {
        ...values,
        device_type_id: parseInt(values.device_type_id),
      }

      await createSensorType.mutateAsync({
        ...sensorTypeData,
        sensor_type_id: 0, // Let backend auto-generate the ID
      })
      closeCreateSensorType()
      // Refresh sensor types data
      sensorTypes.refetch()
    } catch (error) {
      console.error('Error creating sensor type:', error)
    }
  }

  const columns = useMemo<ColumnDef<TagPatternRow>[]>(
    () => [
      {
        header: 'Tag Pattern',
        accessorKey: 'tag_pattern',
        size: 300,
        meta: {
          align: tagPatternAlignRight ? 'right' : 'left',
        },
        cell: ({ getValue, row }) => {
          const pattern = getValue<string>()
          const parts = pattern.split('[INT]')

          return (
            <Tooltip
              label={
                row.original.examples && row.original.examples.length > 0
                  ? `Examples: ${row.original.examples.join(', ')}`
                  : 'No examples available'
              }
              disabled={
                !row.original.examples || row.original.examples.length === 0
              }
            >
              <Text fw={500}>{renderPatternParts(parts)}</Text>
            </Tooltip>
          )
        },
      },
      {
        header: 'Device Type',
        accessorKey: 'device_type_name',
        size: 220,
        meta: {
          align: 'left',
        },
        cell: ({ getValue }) => {
          const deviceTypeName = getValue<string | null>()
          return <Text>{deviceTypeName ?? '—'}</Text>
        },
      },
      {
        header: 'Sensor Type',
        accessorKey: 'sensor_type_name_short',
        size: 180,
        meta: {
          align: 'left',
        },
        cell: ({ getValue, row }) => {
          const nameShort = getValue<string | null>()
          const sensorTypeId = row.original.sensor_type_id as number | undefined
          if (!sensorTypeId || sensorTypeId === 0) {
            return (
              <Tooltip label="Click to assign sensor type">
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  onClick={() => {
                    setSelectedTagPattern(row.original.tag_pattern)
                    openDetails()
                  }}
                >
                  <IconPlus style={{ width: 16, height: 16 }} />
                </ActionIcon>
              </Tooltip>
            )
          }
          return (
            <Tooltip label={`ID: ${sensorTypeId}`}>
              <Text>{nameShort || '—'}</Text>
            </Tooltip>
          )
        },
      },
      {
        header: 'Unit SCADA',
        accessorKey: 'unit_scada',
        size: 150,
        meta: {
          align: 'left',
        },
      },
      {
        header: 'Unit Offset',
        accessorKey: 'unit_offset',
        size: 120,
        meta: {
          align: 'center',
        },
      },
      {
        header: 'Unit Scale',
        accessorKey: 'unit_scale',
        size: 120,
        meta: {
          align: 'center',
        },
      },
      {
        header: 'Total Count',
        accessorKey: 'total_count',
        size: 120,
        meta: {
          align: 'center',
        },
      },
    ],
    [openDetails, tagPatternAlignRight],
  )

  // Assigned Sensor Types table
  const assignedRows = useMemo(() => {
    return (
      sensorTypes.data?.map((st: SensorType) => ({
        sensor_type_id: st.sensor_type_id,
        device_type_id: st.device_type_id,
        name_short: st.name_short,
        name_long: st.name_long,
        name_metric: st.name_metric,
        unit: st.unit,
        assigned: groupedTagTypes.some(
          (row) => row.sensor_type_id === st.sensor_type_id,
        ),
        device_type_name:
          deviceTypes.data?.find(
            (dt) => dt.device_type_id === st.device_type_id,
          )?.name_long || null,
      })) || []
    )
  }, [sensorTypes.data, groupedTagTypes, deviceTypes.data])

  const assignedColumns = useMemo<ColumnDef<AssignedSensorTypeRow>[]>(
    () => [
      {
        header: 'Sensor Type',
        accessorKey: 'name_short',
        size: 220,
        cell: ({ getValue, row }) => {
          const nameShort = getValue<string>()
          const nameLong = row.original.name_long as string | undefined
          return (
            <Tooltip label={nameLong} disabled={!nameLong}>
              <Text fw={500}>{nameShort}</Text>
            </Tooltip>
          )
        },
      },
      {
        header: 'Device Type',
        accessorKey: 'device_type_name',
        size: 220,
        meta: { align: 'left' },
        cell: ({ getValue }) => {
          const dtName = getValue<string | null>()
          return <Text>{dtName ?? '—'}</Text>
        },
      },
      {
        header: 'Metric',
        accessorKey: 'name_metric',
        size: 200,
      },
      {
        header: 'Unit',
        accessorKey: 'unit',
        size: 120,
        meta: { align: 'center' },
      },
      {
        header: 'Assigned in Project?',
        accessorKey: 'assigned',
        size: 200,
        filterFn: booleanSelectFilter as FilterFn<AssignedSensorTypeRow>,
        meta: {
          align: 'center',
          filterVariant: 'boolean',
        },
        cell: ({ getValue }) => (
          <Checkbox checked={!!getValue<boolean>()} readOnly />
        ),
      },
    ],
    [],
  )

  if (
    uniqueTagTypes.isLoading ||
    sensorTypes.isLoading ||
    deviceTypes.isLoading ||
    project.isLoading
  ) {
    return <PageLoader />
  }

  if (project.isError) {
    return (
      <Stack p="md">
        <Title order={1}>Project Tag Explorer</Title>
        <Text c="red">
          Error loading project data:{' '}
          {project.error?.message || 'Unknown error'}
        </Text>
      </Stack>
    )
  }

  const noPrecomputedPatterns =
    uniqueTagTypes.data && Array.isArray(uniqueTagTypes.data)
      ? uniqueTagTypes.data.length === 0
      : false

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
                  Keep the Google Sheet called &quot;_operational&quot; and any
                  &quot;[project].tags&quot; manually updated in parallel with
                  this method for the time being. This way they will stay in
                  sync until we&apos;ve fully transitioned.
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

      <Tabs defaultValue="unique-tag-types">
        <Tabs.List>
          <Tabs.Tab value="unique-tag-types">Unique Tag Types</Tabs.Tab>
          <Tabs.Tab value="assigned-sensor-types">
            Assigned Sensor Types
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="unique-tag-types" pt="xs">
          <Card withBorder>
            <Stack gap="md">
              <Group justify="space-between" align="center">
                <Title order={3}>Unique Tag Types</Title>
                <Button
                  variant="filled"
                  leftSection={<IconPlus size={16} />}
                  onClick={handlePopulatePatterns}
                  loading={putUniqueTagPatterns.isPending}
                >
                  Populate Patterns
                </Button>
              </Group>
              <Text size="sm" c="dimmed">
                This table shows unique tag patterns for the current project.
                Tags are grouped by pattern with integers replaced by{' '}
                <b>[INT]</b>. You can assign sensor types to tag patterns to
                speed up project onboarding.
              </Text>

              {noPrecomputedPatterns && (
                <Card withBorder>
                  <Stack gap="xs">
                    <Text fw={600}>No precomputed patterns found</Text>
                    <Text size="sm" c="dimmed">
                      This project has no rows in the unique patterns table yet.
                      Click &quot;Populate Patterns&quot; to generate them. This
                      may take a minute.
                    </Text>
                  </Stack>
                </Card>
              )}

              {/* Query Controls */}
              <Group gap="lg" justify="space-between">
                <Group gap="xs">
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
                <Group gap="sm">
                  <Checkbox
                    label="Show only unassigned"
                    checked={showOnlyUnassigned}
                    onChange={(event) =>
                      setShowOnlyUnassigned(event.currentTarget.checked)
                    }
                  />
                  <Button
                    variant="light"
                    onClick={() =>
                      setTagPatternAlignRight(!tagPatternAlignRight)
                    }
                  >
                    Tag Pattern: {tagPatternAlignRight ? 'Right' : 'Left'}{' '}
                    Aligned
                  </Button>
                </Group>
              </Group>
              <TanStackMantineTable
                columns={columns}
                data={filteredGroupedTagTypes}
                emptyText="No unique tag patterns match the current filters."
                initialPagination={{
                  pageIndex: 0,
                  pageSize: 50,
                }}
                initialSorting={[{ id: 'total_count', desc: true }]}
                isLoading={uniqueTagTypes.isFetching || isTableRefreshing}
                onRowClick={(row) => {
                  setSelectedTagPattern(row.tag_pattern)
                  openDetails()
                }}
                searchPlaceholder="Search tag patterns, device types, units..."
              />
            </Stack>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="assigned-sensor-types" pt="xs">
          <Card withBorder>
            <Stack gap="md">
              <Title order={3}>Assigned Sensor Types</Title>
              <Text size="sm" c="dimmed">
                This tab summarizes sensor type availability vs. assignment in
                this project.
              </Text>
              <TanStackMantineTable
                columns={assignedColumns}
                data={assignedRows}
                emptyText="No sensor types match the current filters."
                initialPagination={{
                  pageIndex: 0,
                  pageSize: 50,
                }}
                initialSorting={[{ id: 'assigned', desc: true }]}
                isLoading={sensorTypes.isFetching}
                searchPlaceholder="Search sensor types, device types, units..."
              />
            </Stack>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Tag Pattern Details Modal */}
      <Modal
        opened={isDetailsModalOpen}
        onClose={closeDetails}
        title={selectedTagPatternTitle}
        size="100%"
      >
        <Stack gap="lg">
          {selectedTagPattern && (
            <>
              {/* Pattern with [INT] replaced by computed ranges */}
              <Card withBorder>
                <Stack gap="xs">
                  <Text size="sm" fw={500}>
                    Pattern Ranges
                  </Text>
                  {tagsByPattern.isLoading ? (
                    <>
                      <Text size="sm">Loading tags…</Text>
                      <Text
                        size="xs"
                        c="dimmed"
                        style={{ visibility: 'hidden' }}
                      >
                        Based on 0 tags matching this pattern
                      </Text>
                    </>
                  ) : tagsByPattern.error ? (
                    <>
                      <Text size="sm" c="red">
                        Error loading tags
                      </Text>
                      <Text
                        size="xs"
                        c="dimmed"
                        style={{ visibility: 'hidden' }}
                      >
                        Based on 0 tags matching this pattern
                      </Text>
                    </>
                  ) : intRanges.length > 0 ? (
                    <>
                      <Text size="sm" style={{ wordBreak: 'break-all' }}>
                        {intRangeNodes}
                      </Text>
                      <Text size="xs" c="dimmed">
                        Based on {tagsByPattern.data?.length || 0} tags matching
                        this pattern
                      </Text>
                    </>
                  ) : (
                    <Text size="sm" c="dimmed">
                      No ranges found
                    </Text>
                  )}
                </Stack>
              </Card>

              <Group align="flex-start">
                {/* Left: Tag Properties and Assignment */}
                <Card withBorder style={{ flex: 1 }}>
                  <Stack>
                    <Text size="lg">Tag Properties</Text>

                    <Group gap="xs" align="center">
                      <Text>Device Type</Text>
                      <Tooltip label="The representative device type for this pattern.">
                        <IconInfoCircle size={12} />
                      </Tooltip>
                    </Group>
                    <Text fw={500}>
                      {selectedPatternRow?.device_type_name ?? '—'}
                    </Text>

                    {/* SCADA Unit */}
                    <Group gap="xs" align="center">
                      <Text>SCADA Unit</Text>
                      <Tooltip label="The unit of the SCADA value.">
                        <IconInfoCircle size={12} />
                      </Tooltip>
                    </Group>
                    <Select
                      placeholder="Select SCADA unit (e.g., C, W, W/m2)"
                      searchable
                      clearable
                      value={patternUnitScada}
                      data={predefinedUnits.map((unit) => ({
                        value: unit,
                        label: unit,
                      }))}
                      onChange={(value) => setPatternUnitScada(value)}
                    />

                    {/* Sensor Type */}
                    <Group justify="space-between" align="center">
                      <Group gap="xs" align="center">
                        <Text size="lg">Sensor Type</Text>
                        <Tooltip label="The sensor type to assign to the tag pattern.">
                          <IconInfoCircle size={12} />
                        </Tooltip>
                      </Group>
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
                        sensorTypes.data?.map((sensorType: SensorType) => ({
                          value: sensorType.sensor_type_id.toString(),
                          label: `${sensorType.name_short} - ${sensorType.name_long}`,
                          unit: sensorType.unit,
                        })) || []
                      }
                      onChange={(value) => {
                        setPatternSensorTypeId(value)
                        if (value && sensorTypes.data) {
                          const sensorType = sensorTypes.data.find(
                            (st: SensorType) =>
                              st.sensor_type_id.toString() === value,
                          )
                          setSelectedSensorTypeUnit(sensorType?.unit || null)
                        } else {
                          setSelectedSensorTypeUnit(null)
                        }
                      }}
                    />

                    {selectedSensorTypeUnit && (
                      <Text size="sm">
                        Selected sensor type has an assumed unit of{' '}
                        <Text fw={600} component="span">
                          {selectedSensorTypeUnit}
                        </Text>
                        .
                      </Text>
                    )}

                    {/* Unit Scale */}
                    <Group gap="xs" align="center">
                      <Text size="lg">Unit Scale</Text>
                      <Tooltip label="The amount to multiply the SCADA value by.">
                        <IconInfoCircle size={12} />
                      </Tooltip>
                    </Group>
                    <Group grow>
                      <Group gap="xs" align="center">
                        <Text>
                          SCADA Value{' '}
                          {patternUnitScada ? `(${patternUnitScada})` : ''}{' '}
                          &times;
                        </Text>
                        <NumberInput
                          placeholder="1 (default)"
                          value={patternUnitScale ?? undefined}
                          onChange={(value) =>
                            setPatternUnitScale(
                              typeof value === 'number' ? value : null,
                            )
                          }
                          step={0.000001}
                          decimalScale={6}
                          size="xs"
                        />
                        <Text>→ {selectedSensorTypeUnit || 'Unit'}</Text>
                      </Group>
                    </Group>
                    <Group>
                      <Text>Quick Select Scales</Text>
                      <Button
                        size="compact-xs"
                        onClick={() => setPatternUnitScale(0.001)}
                      >
                        0.001
                      </Button>
                      <Button
                        size="compact-xs"
                        onClick={() => setPatternUnitScale(0.01)}
                      >
                        0.01
                      </Button>
                    </Group>

                    {/* Unit Offset */}
                    <Group gap="xs" align="center">
                      <Text size="lg">Unit Offset</Text>
                      <Tooltip label="The amount to add to the SCADA value. Offset will be applied after the scale if both are set.">
                        <IconInfoCircle size={12} />
                      </Tooltip>
                    </Group>
                    <NumberInput
                      placeholder="0 (default)"
                      value={patternUnitOffset ?? undefined}
                      onChange={(value) =>
                        setPatternUnitOffset(
                          typeof value === 'number' ? value : null,
                        )
                      }
                      step={0.01}
                      decimalScale={2}
                      size="xs"
                    />

                    {/* Submission */}
                    <Button
                      onClick={handleAssignPatternClick}
                      loading={assignPatternSensorType.isPending}
                      disabled={!patternSensorTypeId}
                      fullWidth
                    >
                      Assign to Pattern
                    </Button>
                    <Button variant="subtle" onClick={closeDetails} fullWidth>
                      Cancel
                    </Button>
                  </Stack>
                </Card>

                {/* Right: Sample Data */}
                <Card withBorder style={{ flex: 2 }}>
                  <Stack>
                    <Group justify="space-between" align="center">
                      <Title order={4}>Sample Data</Title>
                      <AdvancedDatePicker
                        defaultRange="past-3-days"
                        includeClearButton={false}
                        includeTodayInDateRange={true}
                      />
                    </Group>
                    {tagPatternSamples.data?.sample_tags && (
                      <Group gap="lg">
                        <Text size="sm">
                          <strong>Total Tags:</strong>{' '}
                          {selectedPatternRow?.total_count || 0}
                        </Text>
                        <Text size="sm">
                          <strong>Sampled Tags:</strong> {sampledTagCount}
                        </Text>
                        <Text size="sm">
                          <strong>Numeric Tags:</strong> {numericTagCount}
                        </Text>
                        <Text size="sm">
                          <strong>Non-Numeric Tags:</strong>{' '}
                          {nonNumericTagCount}
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
                        <>
                          {numericTagsWithSamples.length > 0 &&
                            project.isSuccess && (
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
                                  <div
                                    style={{
                                      width: '100%',
                                      height: '450px',
                                    }}
                                  >
                                    <PlotlyPlot
                                      data={numericTimeseriesData}
                                      xAxisTimeZone={timezoneName}
                                      layout={{
                                        yaxis: {
                                          title: {
                                            text: selectedUnitLabel,
                                          },
                                          tickformat: selectedUnitTickFormat,
                                        },
                                      }}
                                    />
                                  </div>
                                </Tabs.Panel>

                                <Tabs.Panel value="histogram" pt="xs">
                                  <div
                                    style={{
                                      width: '100%',
                                      height: '450px',
                                    }}
                                  >
                                    <PlotlyPlot
                                      data={numericHistogramData}
                                      layout={{
                                        showlegend: false,
                                        xaxis: {
                                          title: {
                                            text: selectedUnitLabel,
                                          },
                                          tickformat: selectedUnitTickFormat,
                                        },
                                        yaxis: {
                                          title: { text: 'Frequency' },
                                        },
                                      }}
                                    />
                                  </div>
                                </Tabs.Panel>
                              </Tabs>
                            )}

                          {numericTagsWithSamples.length > 0 &&
                            !project.isSuccess && (
                              <Card withBorder variant="light">
                                <Text c="dimmed">
                                  Charts unavailable: Project data not loaded
                                </Text>
                              </Card>
                            )}

                          {nonNumericTagSummaries.length > 0 && (
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
                                  {nonNumericTagSummaries.map((tag) => (
                                    <div
                                      key={tag.tagId}
                                      style={{ marginBottom: '12px' }}
                                    >
                                      <Text size="sm" fw={500} c="blue">
                                        {tag.tagName}:
                                      </Text>
                                      <Text
                                        size="xs"
                                        c="dimmed"
                                        style={{
                                          marginLeft: '16px',
                                          marginBottom: '4px',
                                        }}
                                      >
                                        {tag.totalValueCount} total values,{' '}
                                        {tag.uniqueValueCount} unique
                                      </Text>
                                      <Group
                                        gap="xs"
                                        wrap="wrap"
                                        style={{ marginLeft: '16px' }}
                                      >
                                        {tag.visibleUniqueValues.map(
                                          (value, valueIndex) => (
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
                                        {tag.remainingUniqueValueCount > 0 && (
                                          <Text size="xs" c="dimmed">
                                            +{tag.remainingUniqueValueCount}{' '}
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

                          {numericTagsWithSamples.length === 0 &&
                            nonNumericTagsWithSamples.length === 0 && (
                              <Card withBorder variant="light">
                                <Stack gap="sm">
                                  <Text fw={500}>No Sample Data Available</Text>
                                  <Text size="sm" c="dimmed">
                                    No timeseries data was found for the
                                    selected tags in the specified date range.
                                  </Text>
                                </Stack>
                              </Card>
                            )}
                        </>
                      </Stack>
                    ) : (
                      <Text c="dimmed">
                        No sample data available for this pattern. This could be
                        because:
                        <br />• No tags match this pattern in the database
                        <br />• The tags exist but have no timeseries data in
                        the selected date range
                      </Text>
                    )}
                  </Stack>
                </Card>
              </Group>
            </>
          )}
        </Stack>
      </Modal>

      {/* Confirmation Modal for Pattern Assignment */}
      <Modal
        opened={isConfirmOpen}
        onClose={closeConfirm}
        title="Confirm Pattern Assignment"
        size="lg"
      >
        <Stack gap="md">
          <Text>
            Are you sure you want to assign the sensor type &quot;
            {
              sensorTypes.data?.find(
                (st) => st.sensor_type_id.toString() === patternSensorTypeId,
              )?.name_short
            }
            &quot; to all tags matching the pattern &quot;{selectedTagPattern}
            &quot;?
          </Text>
          {patternUnitScale !== null && (
            <Text size="sm" c="dimmed">
              This will also set the unit scale multiplier to {patternUnitScale}
              .
            </Text>
          )}
          {patternUnitOffset !== null && (
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
                onChange={handleProjectTagDeviceTypeChange}
                searchable
                clearable
                required
              />
            </Tooltip>
            <Tooltip
              label="Device comes first, then a full name for the sensor type. Each word starts with a capital letter. Example: PV Inverter AC Power, Tracker Position"
              position="top"
              multiline
            >
              <TextInput
                label="Long Name"
                placeholder="e.g., PV Inverter AC Power"
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
                placeholder="e.g., pv_inverter_ac_power"
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
                    {uniqueUnits.length > 0
                      ? uniqueUnits.join(', ')
                      : 'No existing units found'}
                  </Text>
                  <Text size="xs" c="dimmed" style={{ fontStyle: 'italic' }}>
                    Try to stick to existing units when possible, but you can
                    type a new one if necessary.
                  </Text>
                </Stack>
              </Popover.Dropdown>
            </Popover>
            <TextInput
              label="Description"
              placeholder="Optional description of the sensor type"
              {...createSensorTypeForm.getInputProps('description')}
            />
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
