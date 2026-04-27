import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetSensorTypes } from '@/api/v1/operational/sensor_types'
import {
  DataAvailability,
  useGetDataAvailabilityV2,
} from '@/api/v1/protected/web-application/projects/real_time'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { useGetDevicesV2 } from '@/hooks/api'
import * as types from '@/hooks/types'
import {
  Badge,
  Box,
  Button,
  Group,
  Loader,
  LoadingOverlay,
  NumberInput,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  UnstyledButton,
  useMantineColorScheme,
  useMantineTheme,
} from '@mantine/core'
import {
  IconChevronDown,
  IconChevronRight,
  IconChevronUp,
} from '@tabler/icons-react'
import {
  type ColumnDef,
  type ColumnFiltersState,
  type ExpandedState,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getExpandedRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useVirtualizer } from '@tanstack/react-virtual'
import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { useParams } from 'react-router'

interface DeviceData {
  device_id: number
  device_name: string | null
  total_tags: number
  active_tags: number
  stale_tags: number
  no_data_tags: number
}

const numericEquals: ColumnDef<DeviceData>['filterFn'] = (
  row,
  columnId,
  filterValue,
) => {
  if (filterValue == null || filterValue === '') return true
  return Number(row.getValue(columnId)) === Number(filterValue)
}

const DataAvailabilityPage = () => {
  const theme = useMantineTheme()
  const { colorScheme } = useMantineColorScheme()
  const { projectId } = useParams<{ projectId: string }>()
  const [selectedDeviceType, setSelectedDeviceType] = useState<string | null>(
    null,
  )
  const [isAllDataLoaded, setIsAllDataLoaded] = useState(false)
  const [prefetchIndex, setPrefetchIndex] = useState(0)
  const [devicesOffset, setDevicesOffset] = useState(0)
  const [allDevices, setAllDevices] = useState<types.Device[]>([])
  const [hasMoreDevices, setHasMoreDevices] = useState(true)
  const [devicesByType, setDevicesByType] = useState<
    Record<string, types.Device[]>
  >({})
  const [hasMoreDevicesByType, setHasMoreDevicesByType] = useState<
    Record<string, boolean>
  >({})
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [expanded, setExpanded] = useState<ExpandedState>({})
  const tableContainerRef = useRef<HTMLDivElement>(null)

  // Reset state when component mounts (handles same-project navigation)
  useEffect(() => {
    queueMicrotask(() => setSelectedDeviceType(null))
    queueMicrotask(() => setIsAllDataLoaded(false))
    queueMicrotask(() => setPrefetchIndex(0))
    queueMicrotask(() => setDevicesOffset(0))
    queueMicrotask(() => setAllDevices([]))
    queueMicrotask(() => setHasMoreDevices(true))
    queueMicrotask(() => setDevicesByType({}))
    queueMicrotask(() => setHasMoreDevicesByType({}))
  }, [])

  const project = useSelectProject(projectId!)

  const usedDeviceTypeIds = (
    project.data?.spec.used_device_type_ids ?? []
  ).filter((id: number) => id !== 0)

  const devicesQuery = useGetDevicesV2({
    pathParams: { projectId: projectId ?? '' },
    filters: {
      device_type_ids: selectedDeviceType ? [Number(selectedDeviceType)] : [],
      limit: 1000,
      offset: devicesOffset,
      fields: ['device_id', 'name_long'],
    },
    queryOptions: {
      enabled: !!selectedDeviceType,
    },
  })

  // Update devices when new data comes in
  useEffect(() => {
    if (devicesQuery.data && devicesQuery.isSuccess && selectedDeviceType) {
      const devices = devicesQuery.data as types.Device[]

      queueMicrotask(() =>
        setDevicesByType((prev) => {
          const currentDevices = prev[selectedDeviceType] || []
          if (devicesOffset === 0) {
            // First load - replace all devices for this type
            return { ...prev, [selectedDeviceType]: devices }
          } else {
            // Load more - append to existing devices for this type
            return {
              ...prev,
              [selectedDeviceType]: [...currentDevices, ...devices],
            }
          }
        }),
      )

      // Check if we have more devices to load for this type
      queueMicrotask(() =>
        setHasMoreDevicesByType((prev) => ({
          ...prev,
          [selectedDeviceType]: devices.length === 1000,
        })),
      )
    }
  }, [
    devicesQuery.data,
    devicesQuery.isSuccess,
    devicesOffset,
    selectedDeviceType,
  ])

  // Update current devices when device type changes
  useEffect(() => {
    if (selectedDeviceType) {
      // Load devices from cache for this device type
      const cachedDevices = devicesByType[selectedDeviceType] || []
      queueMicrotask(() => setAllDevices(cachedDevices))
      queueMicrotask(() =>
        setHasMoreDevices(hasMoreDevicesByType[selectedDeviceType] ?? true),
      )

      // Reset offset for new loads
      queueMicrotask(() => setDevicesOffset(0))
    }
  }, [selectedDeviceType, devicesByType, hasMoreDevicesByType])

  // Reset expanded rows only when the selected device type changes
  useEffect(() => {
    setExpanded({})
  }, [selectedDeviceType])

  const panelDevices = allDevices

  const loadMoreDevices = () => {
    if (!devicesQuery.isLoading && hasMoreDevices && selectedDeviceType) {
      setDevicesOffset((prev) => prev + 1000)
    }
  }

  const sensorTypes = useGetSensorTypes({})

  const prefetchDeviceTypeId = usedDeviceTypeIds[prefetchIndex] ?? null

  const dataAvailabilityInitialQuery = useGetDataAvailabilityV2({
    pathParams: { projectId: projectId ?? '' },
    queryParams: {
      device_type_ids: prefetchDeviceTypeId ? [prefetchDeviceTypeId] : [],
    },
    queryOptions: { enabled: !!prefetchDeviceTypeId && !isAllDataLoaded },
  })
  const dataAvailabilityInitial = useMemo(
    () =>
      dataAvailabilityInitialQuery.data
        ? (dataAvailabilityInitialQuery.data.toArray() as DataAvailability[])
        : [],
    [dataAvailabilityInitialQuery.data],
  )
  // When the initial query finishes, decide whether to accept this device type or move on
  useEffect(() => {
    if (!usedDeviceTypeIds.length) return
    if (!dataAvailabilityInitialQuery.isSuccess) return
    // Don't process if we already found a device type with data
    if (selectedDeviceType) return

    const rows = dataAvailabilityInitial ?? []
    const noData = rows.length === 0

    if (noData) {
      // try next device type
      const next = prefetchIndex + 1
      if (next < (usedDeviceTypeIds.length ?? 0)) {
        queueMicrotask(() => setPrefetchIndex(next))
      } else {
        // none had data; surface an empty page state by ending loading, but without a selected type
        queueMicrotask(() => setIsAllDataLoaded(true))
        queueMicrotask(() => setSelectedDeviceType(null))
      }
    } else {
      // lock in the first device type that actually has data
      if (prefetchDeviceTypeId != null) {
        queueMicrotask(() =>
          setSelectedDeviceType(prefetchDeviceTypeId.toString()),
        )
      }
    }
  }, [
    dataAvailabilityInitialQuery.isSuccess,
    dataAvailabilityInitial,
    usedDeviceTypeIds,
    prefetchDeviceTypeId,
    prefetchIndex,
    isAllDataLoaded,
    selectedDeviceType,
  ])
  const dataAvailabilityDataQuery = useGetDataAvailabilityV2({
    pathParams: { projectId: projectId ?? '' },
    queryParams: { device_type_ids: usedDeviceTypeIds },
    queryOptions: { enabled: false },
  })

  const dataAvailabilityData = useMemo(
    () =>
      dataAvailabilityDataQuery.data
        ? (dataAvailabilityDataQuery.data.toArray() as DataAvailability[])
        : null,
    [dataAvailabilityDataQuery.data],
  )

  useEffect(() => {
    if (selectedDeviceType && usedDeviceTypeIds.length && !isAllDataLoaded) {
      dataAvailabilityDataQuery.refetch()
    }
  }, [
    selectedDeviceType,
    usedDeviceTypeIds,
    dataAvailabilityDataQuery,
    isAllDataLoaded,
  ])

  const dataAvailability = useMemo(() => {
    return isAllDataLoaded
      ? dataAvailabilityData?.filter(
          (d) => Number(d.device_type_id)?.toString() === selectedDeviceType,
        )
      : (dataAvailabilityInitial ?? [])
  }, [
    isAllDataLoaded,
    dataAvailabilityData,
    selectedDeviceType,
    dataAvailabilityInitial,
  ])

  const uniqueDeviceTypeIds = [
    ...new Set(
      dataAvailabilityData
        ?.map((d) => Number(d.device_type_id))
        .filter(Boolean),
    ),
  ]
    .sort((a, b) => Number(a) - Number(b))
    .map((id) => Number(id))

  const deviceTypesInitial = useGetDeviceTypes({
    queryParams: {
      device_type_ids: prefetchDeviceTypeId
        ? [Number(prefetchDeviceTypeId)]
        : [],
    },
    queryOptions: {
      enabled: !!usedDeviceTypeIds.length && !!prefetchDeviceTypeId,
    },
  })
  const deviceTypesAll = useGetDeviceTypes({
    queryParams: { device_type_ids: uniqueDeviceTypeIds },
    queryOptions: { enabled: !!uniqueDeviceTypeIds.length },
  })
  const deviceTypes =
    deviceTypesAll.isSuccess && deviceTypesAll.data?.length > 0
      ? deviceTypesAll
      : deviceTypesInitial

  useEffect(() => {
    // Only set isAllDataLoaded to true if:
    // 1. We have all the data loaded AND
    // 2. We have a selected device type (found one with data)
    if (
      dataAvailabilityDataQuery.isSuccess &&
      dataAvailabilityData &&
      deviceTypesAll.isSuccess &&
      selectedDeviceType
    ) {
      queueMicrotask(() => setIsAllDataLoaded(true))
    }
  }, [
    dataAvailabilityDataQuery,
    dataAvailabilityData,
    deviceTypesAll,
    selectedDeviceType,
  ])

  deviceTypes.data?.map((d) =>
    dataAvailabilityData?.filter(
      (da) => Number(da.device_type_id) === d.device_type_id,
    ),
  )

  // Compute stale count per device type
  const staleCountByDeviceType: Record<number, number> =
    deviceTypes.data?.reduce(
      (acc, d) => {
        const count =
          dataAvailabilityData?.filter(
            (da) =>
              Number(da.device_type_id) === d.device_type_id &&
              da.stale === true,
          ).length || 0
        acc[d.device_type_id] = count
        return acc
      },
      {} as Record<number, number>,
    ) || {}

  const uniqueSensorTypes = useMemo(() => {
    return [
      ...new Set(
        dataAvailability
          ?.map(
            (d) =>
              sensorTypes.data?.find(
                (s) => s.sensor_type_id === Number(d.sensor_type_id),
              )?.name_long,
          )
          .filter(Boolean),
      ),
    ]
  }, [dataAvailability, sensorTypes.data])

  // Transform data for MRT
  const mrtData = useMemo(() => {
    if (!panelDevices.length || !dataAvailability) return []

    const total_possible_tags = uniqueSensorTypes.length

    return panelDevices.map((device) => {
      const deviceTags =
        dataAvailability.filter(
          (d) => Number(d.device_id) === device.device_id,
        ) || []

      const total_tags = deviceTags.length
      const stale_tags = deviceTags.filter((d) => d.stale).length
      const active_tags = total_tags - stale_tags
      const no_data_tags = total_possible_tags - total_tags

      return {
        device_id: device.device_id,
        device_name: device.name_long,
        total_tags,
        active_tags,
        stale_tags,
        no_data_tags,
      }
    })
  }, [panelDevices, dataAvailability, uniqueSensorTypes])

  const columns = useMemo<ColumnDef<DeviceData>[]>(
    () => [
      {
        accessorKey: 'device_name',
        header: 'Device',
        filterFn: 'includesString',
      },
      {
        accessorKey: 'total_tags',
        header: 'Total Tags',
        filterFn: numericEquals,
      },
      {
        accessorKey: 'active_tags',
        header: 'Active Tags',
        filterFn: numericEquals,
      },
      {
        accessorKey: 'stale_tags',
        header: 'Stale Tags',
        filterFn: numericEquals,
      },
      {
        accessorKey: 'no_data_tags',
        header: 'No Data Tags',
        filterFn: numericEquals,
      },
    ],
    [],
  )

  const table = useReactTable<DeviceData>({
    data: mrtData,
    columns,
    state: { sorting, columnFilters, expanded },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onExpandedChange: setExpanded,
    getRowCanExpand: () => true,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
  })

  // Build flat slot list: each data row + optional expansion row
  const rows = table.getRowModel().rows
  type Slot =
    | { type: 'data'; row: (typeof rows)[0] }
    | { type: 'expansion'; row: (typeof rows)[0] }
  const slots = useMemo<Slot[]>(() => {
    const result: Slot[] = []
    for (const row of rows) {
      result.push({ type: 'data', row })
      if (row.getIsExpanded()) result.push({ type: 'expansion', row })
    }
    return result
  }, [rows])

  const getScrollElement = useCallback(() => tableContainerRef.current, [])
  const estimateSize = useCallback(
    (index: number) => (slots[index]?.type === 'expansion' ? 200 : 48),
    [slots],
  )

  const getItemKey = useCallback(
    (index: number) => {
      const slot = slots[index]
      if (!slot) return index
      return slot.type === 'expansion'
        ? `${slot.row.id}-expansion`
        : slot.row.id
    },
    [slots],
  )

  const rowVirtualizer = useVirtualizer({
    count: slots.length,
    getScrollElement,
    estimateSize,
    getItemKey,
    overscan: 10,
  })

  // Stable measureElement ref (AllTags.tsx pattern)
  const measureElementRef = useRef(rowVirtualizer.measureElement)
  measureElementRef.current = rowVirtualizer.measureElement
  const measureElement = useCallback((node: Element | null) => {
    if (node) measureElementRef.current(node)
  }, [])

  const virtualItems = rowVirtualizer.getVirtualItems()
  const totalSize = rowVirtualizer.getTotalSize()
  const colSpan = table.getVisibleLeafColumns().length + 1
  const topSpacerHeight = virtualItems[0]?.start ?? 0
  const lastVirtualItem = virtualItems[virtualItems.length - 1]
  const bottomSpacerHeight = lastVirtualItem
    ? totalSize - lastVirtualItem.end
    : 0

  const shouldShowLoader =
    project.isLoading ||
    deviceTypesInitial.isPending ||
    // devicesQuery.isLoading ||
    sensorTypes.isLoading ||
    dataAvailabilityInitialQuery.isLoading ||
    (!isAllDataLoaded && !selectedDeviceType) || // NEW: don't render page while cycling empties
    dataAvailabilityInitialQuery.isLoading
  if (shouldShowLoader) {
    return <PageLoader />
  }

  return (
    <Stack h="100%" p="md" style={{ minHeight: 0 }}>
      <Group>
        <PageTitle
          info={
            <>
              Identify when every sensor last reported. Each tab represents a
              different device type with the number of stale sensors for that
              device type. The table shows the last reported time for each
              sensor on each device.
              <br />
              <br />
              <Text span c="green">
                Green
              </Text>
              : Fresh data - sensor is reporting as expected.
              <br />
              <Text span c="orange">
                Orange
              </Text>
              : Stale data - sensor hasn&apos;t reported recently and may need
              attention.
              <br />
              <Text span c="gray">
                Gray
              </Text>
              : No data available from this sensor.
              <br />
              <br />
              <Text fw={600}>How Stale Values Are Calculated:</Text>
              <br />
              A sensor reading is marked as &apos;stale&apos; when it&apos;s
              older than expected. The system calculates this by:
              <br />
              1. Taking the typical age for similar sensors (median age) and
              doubling it
              <br />
              2. Making sure this threshold is at least 1 hour (3600 seconds)
              <br />
              3. If a reading is older than this calculated threshold, it&apos;s
              marked as stale
              <br />
              <br />
              <Text fs="italic">
                Example: If similar sensors typically report every 30 minutes, a
                reading becomes stale after 1 hour (30 min × 2). But if sensors
                typically report every 10 minutes, readings become stale after 1
                hour (not 20 minutes) because of the 1-hour minimum.
              </Text>
            </>
          }
        >
          Data Availability
        </PageTitle>
        {!isAllDataLoaded && <Loader size="sm" />}
      </Group>
      <Tabs
        h="100%"
        style={{
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
        }}
        value={
          selectedDeviceType ?? deviceTypes.data?.[0]?.device_type_id.toString()
        }
        onChange={setSelectedDeviceType}
      >
        <Tabs.List>
          {deviceTypes.data?.map((deviceType) => (
            <Tabs.Tab
              value={deviceType.device_type_id.toString()}
              key={deviceType.device_type_id}
              disabled={!isAllDataLoaded}
              px="xs"
            >
              <Group gap={5}>
                {deviceType.name_long}
                <Badge
                  size="sm"
                  color={
                    staleCountByDeviceType[deviceType.device_type_id] > 0
                      ? 'orange'
                      : 'green'
                  }
                >
                  {staleCountByDeviceType[deviceType.device_type_id] ?? 0}
                </Badge>
              </Group>
            </Tabs.Tab>
          ))}
        </Tabs.List>
        {/* Only render the panel for the selected device type */}
        {deviceTypes.data
          ?.filter(
            (deviceType) =>
              deviceType.device_type_id.toString() === selectedDeviceType,
          )
          .map((deviceType) => (
            <Tabs.Panel
              value={deviceType.device_type_id.toString()}
              key={deviceType.device_type_id}
              style={{
                flex: 1,
                minHeight: 0,
                overflow: 'hidden', // keep: the panel itself doesn't scroll
                display: 'flex',
                flexDirection: 'column',
              }}
              pt="md"
            >
              {/* Outer wrapper — fills Tabs.Panel, flex column */}
              <div
                style={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  minHeight: 0,
                  position: 'relative',
                }}
              >
                <LoadingOverlay visible={devicesQuery.isLoading} />

                {/* Scrollable container */}
                <div
                  ref={tableContainerRef}
                  style={{
                    flex: 1,
                    height: '100%',
                    overflow: 'auto',
                    minHeight: 0,
                  }}
                >
                  <Table
                    withColumnBorders
                    withTableBorder
                    stickyHeader
                    stickyHeaderOffset={-1}
                    style={{ minWidth: 'max-content' }}
                  >
                    <Table.Thead>
                      {table.getHeaderGroups().map((headerGroup) => (
                        <Fragment key={headerGroup.id}>
                          {/* Row 1: Column labels + sort controls */}
                          <Table.Tr>
                            <Table.Th style={{ width: 40 }} />
                            {headerGroup.headers.map((header) => (
                              <Table.Th key={header.id}>
                                <UnstyledButton
                                  onClick={header.column.getToggleSortingHandler()}
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
                              </Table.Th>
                            ))}
                          </Table.Tr>

                          {/* Row 2: Filter inputs (always visible) */}
                          <Table.Tr>
                            <Table.Th />
                            {headerGroup.headers.map((header) => (
                              <Table.Th key={`${header.id}-filter`}>
                                {header.column.id === 'device_name' ? (
                                  <TextInput
                                    size="xs"
                                    placeholder="Filter..."
                                    value={
                                      (header.column.getFilterValue() as string) ??
                                      ''
                                    }
                                    onChange={(e) =>
                                      header.column.setFilterValue(
                                        e.currentTarget.value,
                                      )
                                    }
                                  />
                                ) : (
                                  <NumberInput
                                    size="xs"
                                    placeholder="Filter..."
                                    value={
                                      (header.column.getFilterValue() as
                                        | number
                                        | '') ?? ''
                                    }
                                    onChange={(value) =>
                                      header.column.setFilterValue(
                                        value === '' ? undefined : value,
                                      )
                                    }
                                  />
                                )}
                              </Table.Th>
                            ))}
                          </Table.Tr>
                        </Fragment>
                      ))}
                    </Table.Thead>

                    <Table.Tbody>
                      {/* Top spacer */}
                      {topSpacerHeight > 0 && (
                        <Table.Tr>
                          <Table.Td
                            colSpan={colSpan}
                            style={{
                              height: topSpacerHeight,
                              padding: 0,
                              border: 'none',
                            }}
                          />
                        </Table.Tr>
                      )}

                      {virtualItems.map((virtualItem) => {
                        const slot = slots[virtualItem.index]
                        if (!slot) return null

                        if (slot.type === 'data') {
                          const { row } = slot
                          const bgColor =
                            row.original.stale_tags > 0
                              ? colorScheme === 'dark'
                                ? `${theme.colors.orange[7]}30`
                                : theme.colors.orange[1]
                              : colorScheme === 'dark'
                                ? `${theme.colors.green[7]}30`
                                : theme.colors.green[1]
                          return (
                            <Table.Tr
                              key={row.id}
                              data-index={virtualItem.index}
                              ref={measureElement}
                              style={{ backgroundColor: bgColor }}
                            >
                              <Table.Td
                                style={{ width: 40, cursor: 'pointer' }}
                                onClick={row.getToggleExpandedHandler()}
                              >
                                {row.getIsExpanded() ? (
                                  <IconChevronDown size={14} />
                                ) : (
                                  <IconChevronRight size={14} />
                                )}
                              </Table.Td>
                              {row.getVisibleCells().map((cell) => (
                                <Table.Td key={cell.id}>
                                  {flexRender(
                                    cell.column.columnDef.cell,
                                    cell.getContext(),
                                  )}
                                </Table.Td>
                              ))}
                            </Table.Tr>
                          )
                        }

                        if (slot.type === 'expansion') {
                          const { row } = slot
                          const deviceId = row.original.device_id
                          const deviceTags = dataAvailability?.filter(
                            (d) => Number(d.device_id) === deviceId,
                          )
                          return (
                            <Table.Tr
                              key={`${row.id}-expansion`}
                              data-index={virtualItem.index}
                              ref={measureElement}
                            >
                              <Table.Td
                                colSpan={colSpan}
                                style={{ padding: 0 }}
                              >
                                <Box p="md">
                                  <Table>
                                    <Table.Thead>
                                      <Table.Tr>
                                        <Table.Th>Sensor Name</Table.Th>
                                        <Table.Th>Last Reported Time</Table.Th>
                                        <Table.Th>Status</Table.Th>
                                      </Table.Tr>
                                    </Table.Thead>
                                    <Table.Tbody>
                                      {deviceTags?.map((tag) => {
                                        const sensorType =
                                          sensorTypes.data?.find(
                                            (s) =>
                                              s.sensor_type_id ===
                                              Number(tag.sensor_type_id),
                                          )
                                        return (
                                          <Table.Tr key={tag.tag_id}>
                                            <Table.Td>
                                              {sensorType?.name_long ||
                                                'Unknown'}
                                            </Table.Td>
                                            <Table.Td>
                                              {new Date(
                                                tag.time,
                                              ).toLocaleString()}
                                            </Table.Td>
                                            <Table.Td>
                                              <Badge
                                                color={
                                                  tag.stale ? 'orange' : 'green'
                                                }
                                              >
                                                {tag.stale ? 'Stale' : 'Fresh'}
                                              </Badge>
                                            </Table.Td>
                                          </Table.Tr>
                                        )
                                      })}
                                    </Table.Tbody>
                                  </Table>
                                </Box>
                              </Table.Td>
                            </Table.Tr>
                          )
                        }

                        return null
                      })}

                      {/* Bottom spacer */}
                      {bottomSpacerHeight > 0 && (
                        <Table.Tr>
                          <Table.Td
                            colSpan={colSpan}
                            style={{
                              height: bottomSpacerHeight,
                              padding: 0,
                              border: 'none',
                            }}
                          />
                        </Table.Tr>
                      )}
                    </Table.Tbody>
                  </Table>
                </div>

                {/* Load More button */}
                {hasMoreDevices &&
                  panelDevices.length > 0 &&
                  panelDevices.length % 1000 === 0 && (
                    <Group justify="center" mt="md">
                      <Button
                        onClick={loadMoreDevices}
                        loading={devicesQuery.isLoading}
                        disabled={devicesQuery.isLoading}
                        variant="light"
                      >
                        {devicesQuery.isLoading
                          ? `Loading devices...`
                          : `Load More Devices (${panelDevices.length} loaded)`}
                      </Button>
                    </Group>
                  )}
              </div>
            </Tabs.Panel>
          ))}
      </Tabs>
    </Stack>
  )
}

export default DataAvailabilityPage
