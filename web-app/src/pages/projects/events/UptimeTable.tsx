import { SensorTypeEnum } from '@/api/enumerations'
import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import UptimeGIS from '@/components/UptimeGIS'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import { useGetTags, useGetUptimeTable } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import { Tag } from '@/hooks/projectTags'
import {
  Button,
  Group,
  Pagination,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  Title,
  UnstyledButton,
} from '@mantine/core'
import {
  IconArrowRight,
  IconChevronDown,
  IconChevronUp,
} from '@tabler/icons-react'
import {
  type ColumnDef,
  type PaginationState,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useEffect, useMemo, useRef, useState } from 'react'
import { LngLatBoundsLike, MapRef } from 'react-map-gl/mapbox'
import { useParams } from 'react-router'

function ViewDataButton({
  deviceId,
  deviceTypeId,
  startQuery,
  endQuery,
  tags,
}: {
  deviceId: number
  deviceTypeId: number
  startQuery: string
  endQuery: string
  tags: Tag[]
}) {
  const { projectId } = useParams<{ projectId: string }>()
  const filteredTags = tags
    .filter((tag) => tag.device_id === deviceId)
    .filter((tag) => tag.sensor_type_id != SensorTypeEnum.GHOST_UNKNOWN)
  const tagString = filteredTags.map((tag) => tag.tag_id).join('%2C')

  const onClick = () => {
    if (filteredTags.length > 0) {
      const link = `/projects/${projectId}/data-browsing?start=${
        startQuery.split('T')[0]
      }&end=${
        endQuery.split('T')[0]
      }&selectedDeviceType=${deviceTypeId}&selectedTagIds=${tagString}`
      window.open(link, '_blank')
    }
  }

  return (
    <Stack>
      <Button rightSection={<IconArrowRight />} onClick={onClick}>
        View Data
      </Button>
    </Stack>
  )
}

type UptimeDisplayRow = {
  deviceTypeName: string
  deviceName: string
  uptimeHours: number
  uptimePercentage: number
  downtimeHours: number
  downtimePercentage: number
  events: number
  deviceId: number
  deviceTypeId: number
}

const UptimeTable = () => {
  useProjectFilter({
    hasEventIntegration: true,
  })

  const { projectId } = useParams<{ projectId: string }>()
  const pcsRef = useRef<MapRef>(null)
  const blockRef = useRef<MapRef>(null)
  const pcsModuleRef = useRef<MapRef>(null)
  const combinerRef = useRef<MapRef>(null)

  const [selectedGIS, setSelectedGIS] = useState<string | null>(null)
  const [selectedTab, setSelectedTab] = useState<string | null>(null)
  const [pcsBounds, setPcsBounds] = useState<LngLatBoundsLike | null>(null)
  const [blockBounds, setBlockBounds] = useState<LngLatBoundsLike | null>(null)
  const [combinerBounds, setCombinerBounds] = useState<LngLatBoundsLike | null>(
    null,
  )

  const { data: project } = useSelectProject(projectId!)

  let startQuery: string | undefined = undefined
  let endQuery: string | undefined = undefined
  const { start, end } = useValidateDateRange({})

  if (project) {
    if (start) {
      startQuery = start.tz(project.time_zone, true).toISOString()
    }
    if (end) {
      endQuery = end.tz(project.time_zone, true).toISOString()
    }
  }

  const { data: deviceTypes, isLoading: isDeviceTypesLoading } =
    useGetDeviceTypes({
      queryOptions: {
        enabled: !!projectId,
      },
    })

  const { data: uptimeData, isLoading: isUptimeDataLoading } =
    useGetUptimeTable({
      pathParams: { projectId: projectId || '' },
      queryParams: {
        start: startQuery || '',
        end: endQuery || '',
        project_id: projectId || '',
      },
      queryOptions: {
        enabled: !!projectId && !!startQuery && !!endQuery,
      },
    })
  const uniqueDeviceIds = Array.from(
    new Set(uptimeData?.map((data) => data.device_id)),
  )

  const { data: tags, isLoading: isTagsLoading } = useGetTags({
    pathParams: { projectId: projectId || '' },
    queryParams: { device_ids: uniqueDeviceIds, in_tsdb: true },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  useEffect(() => {
    pcsRef.current?.resize()
    blockRef.current?.resize()
    pcsModuleRef.current?.resize()
    combinerRef.current?.resize()
    if (pcsBounds) {
      pcsRef.current?.fitBounds(pcsBounds, { duration: 0 })
    }
    if (blockBounds) {
      blockRef.current?.fitBounds(blockBounds, { duration: 0 })
    }
    if (combinerBounds) {
      combinerRef.current?.fitBounds(combinerBounds, { duration: 0 })
    }
  }, [
    selectedGIS,
    selectedTab,
    uptimeData,
    blockBounds,
    combinerBounds,
    pcsBounds,
  ])

  const maxUptime = useMemo(() => {
    if (!uptimeData?.length) {
      return 0
    }

    const possibleUptime = uptimeData[0]?.possible_uptime
    if (!Number.isFinite(possibleUptime)) {
      return 0
    }

    return Math.max(possibleUptime, 0)
  }, [uptimeData])

  const deviceTypeNamesById = useMemo(() => {
    const namesById = new Map<number, string>()
    ;(deviceTypes || []).forEach((deviceType) => {
      namesById.set(deviceType.device_type_id, deviceType.name_long)
    })
    return namesById
  }, [deviceTypes])

  const displayRows = useMemo<UptimeDisplayRow[]>(() => {
    return (uptimeData || []).map((row) => {
      return {
        deviceTypeName:
          deviceTypeNamesById.get(row.device_type_id) || 'Unknown Device Type',
        deviceName: row.device_name_full,
        uptimeHours: Math.max(maxUptime - row.downtime_hours, 0),
        uptimePercentage: (1 - row.downtime_percentage) * 100,
        downtimeHours: row.downtime_hours,
        downtimePercentage: row.downtime_percentage * 100,
        events: row.events,
        deviceId: row.device_id,
        deviceTypeId: row.device_type_id,
      }
    })
  }, [deviceTypeNamesById, maxUptime, uptimeData])

  const [sorting, setSorting] = useState<SortingState>([])
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 25,
  })

  const columns = useMemo<ColumnDef<UptimeDisplayRow>[]>(() => {
    return [
      {
        accessorKey: 'deviceTypeName',
        header: 'Device Type',
      },
      {
        accessorKey: 'deviceName',
        header: 'Device Name',
      },
      {
        accessorKey: 'uptimeHours',
        header: 'Uptime Hours',
        cell: ({ getValue }) => Number(getValue()).toFixed(1),
      },
      {
        accessorKey: 'uptimePercentage',
        header: 'Uptime Percentage',
        cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`,
      },
      {
        accessorKey: 'downtimeHours',
        header: 'Downtime Hours',
        cell: ({ getValue }) => Number(getValue()).toFixed(1),
      },
      {
        accessorKey: 'downtimePercentage',
        header: 'Downtime Percentage',
        cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`,
      },
      {
        accessorKey: 'events',
        header: 'Events',
      },
      {
        id: 'dataBrowsing',
        header: 'Data Browsing',
        cell: ({ row }) => {
          return (
            <ViewDataButton
              deviceId={row.original.deviceId}
              deviceTypeId={row.original.deviceTypeId}
              startQuery={startQuery || ''}
              endQuery={endQuery || ''}
              tags={tags || []}
            />
          )
        },
      },
    ]
  }, [endQuery, startQuery, tags])

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable<UptimeDisplayRow>({
    data: displayRows,
    columns,
    state: { sorting, pagination },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  const rowModel = table.getPaginationRowModel()
  const firstHeaderGroup = table.getHeaderGroups()[0]
  const visibleHeaderCells = firstHeaderGroup?.headers || []
  const visibleRows = rowModel.rows
  const colspan = visibleHeaderCells.length || 1
  const pageCount = Math.max(table.getPageCount(), 1)

  if (isUptimeDataLoading || isDeviceTypesLoading || isTagsLoading) {
    return <PageLoader />
  }

  return (
    <Stack h="100%" w="100%" p="md">
      <Title order={1}>Uptime Table</Title>
      <Group justify="space-between">
        <AdvancedDatePicker defaultRange="today" includeClearButton={false} />
        <Text>Maximum Uptime: {maxUptime.toFixed(1)} hours</Text>
      </Group>
      <Tabs
        defaultValue="table"
        flex={1}
        display="flex"
        onChange={(value) => setSelectedTab(value)}
        style={{ flexDirection: 'column' }}
      >
        <Tabs.List>
          <Tabs.Tab value="table">Table</Tabs.Tab>
          <Tabs.Tab value="gis">GIS</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="table" pb="md">
          <Table.ScrollContainer minWidth="100%" flex={1}>
            <Table
              striped
              highlightOnHover
              stickyHeader
              horizontalSpacing="sm"
              verticalSpacing="sm"
              fz="sm"
            >
              <Table.Thead>
                <Table.Tr>
                  {visibleHeaderCells.map((header) => (
                    <Table.Th key={header.id}>
                      {header.isPlaceholder ? null : (
                        <UnstyledButton
                          onClick={header.column.getToggleSortingHandler()}
                          disabled={!header.column.getCanSort()}
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
                      )}
                    </Table.Th>
                  ))}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {visibleRows.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={colspan}>
                      <Text size="sm" c="dimmed">
                        No uptime data available for the selected range.
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  visibleRows.map((row) => {
                    const cells = row.getVisibleCells()

                    return (
                      <Table.Tr key={row.id}>
                        {cells.map((cell) => (
                          <Table.Td key={cell.id}>
                            {cell.getIsPlaceholder()
                              ? null
                              : flexRender(
                                  cell.column.columnDef.cell,
                                  cell.getContext(),
                                )}
                          </Table.Td>
                        ))}
                      </Table.Tr>
                    )
                  })
                )}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          <Group justify="center" mt="sm" pb="sm" gap="xl">
            <Group gap="xs" align="center">
              <Text size="sm">Rows per page</Text>
              <Select
                size="xs"
                w={80}
                value={String(pagination.pageSize)}
                data={['25', '50', '100']}
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
              value={pagination.pageIndex + 1}
              onChange={(page) => table.setPageIndex(page - 1)}
            />
          </Group>
        </Tabs.Panel>
        <Tabs.Panel value="gis" h="100%">
          <Tabs
            defaultValue={selectedGIS || 'pcs'}
            flex={1}
            h="100%"
            display="flex"
            onChange={(value) => setSelectedGIS(value)}
            style={{ flexDirection: 'column' }}
          >
            <Tabs.List>
              <Tabs.Tab value="block">Block</Tabs.Tab>
              <Tabs.Tab value="pcs">PCS</Tabs.Tab>
              <Tabs.Tab value="combiner">Combiner</Tabs.Tab>
            </Tabs.List>
            <Tabs.Panel value="block" h="100%">
              <UptimeGIS
                deviceTypeId={6}
                uptimeData={uptimeData || []}
                mapRef={blockRef}
                deviceTypeName="Block"
                onBoundsChange={(bounds) => setBlockBounds(bounds)}
              />
            </Tabs.Panel>
            <Tabs.Panel value="pcs" h="100%">
              <UptimeGIS
                deviceTypeId={2}
                uptimeData={uptimeData || []}
                mapRef={pcsRef}
                deviceTypeName="PCS"
                onBoundsChange={(bounds) => setPcsBounds(bounds)}
              />
            </Tabs.Panel>
            <Tabs.Panel value="combiner" h="100%">
              <UptimeGIS
                deviceTypeId={9}
                uptimeData={uptimeData || []}
                mapRef={combinerRef}
                deviceTypeName="Combiner"
                onBoundsChange={(bounds) => setCombinerBounds(bounds)}
              />
            </Tabs.Panel>
          </Tabs>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}

export default UptimeTable
