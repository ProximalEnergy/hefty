import { useSelectProject } from '@/api/v1/operational/projects'
import {
  useGetPTPData,
  useGetPTPEndpoints,
  useGetPTPEndpointsAvailability,
} from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import { useGetQSEAccess } from '@/api/v1/protected/web-application/projects/financial/qse_access'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectDropdownToggle } from '@/hooks/custom'
import {
  Badge,
  Button,
  Card,
  Group,
  LoadingOverlay,
  ScrollArea,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  useMantineTheme,
} from '@mantine/core'
import { DatePickerInput } from '@mantine/dates'
import {
  IconChartBar,
  IconChevronDown,
  IconChevronUp,
  IconCurrencyDollar,
  IconDatabase,
  IconFileText,
  IconGauge,
  IconTrendingUp,
} from '@tabler/icons-react'
import {
  ColumnDef,
  PaginationState,
  SortingState,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { Data, Layout } from 'plotly.js/dist/plotly-custom.min.js'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router'

dayjs.extend(utc)
dayjs.extend(timezone)

const CATEGORY_ICONS = {
  performance: IconGauge,
  settlement: IconCurrencyDollar,
  market: IconTrendingUp,
  analysis: IconChartBar,
  submissions: IconFileText,
}

const CATEGORY_COLORS = {
  performance: 'blue',
  settlement: 'green',
  market: 'orange',
  analysis: 'purple',
  submissions: 'cyan',
}

interface EndpointCardProps {
  endpoint: string
  category: string
  hasData?: boolean
  onViewData: (endpoint: string, category: string) => void
}

const EndpointCard = ({
  endpoint,
  category,
  hasData,
  onViewData,
}: EndpointCardProps) => {
  const theme = useMantineTheme()
  const Icon = CATEGORY_ICONS[category as keyof typeof CATEGORY_ICONS]
  const color = CATEGORY_COLORS[category as keyof typeof CATEGORY_COLORS]

  return (
    <Card
      withBorder
      p="md"
      style={{
        cursor: 'pointer',
        transition: 'transform 0.2s, box-shadow 0.2s',
        opacity: hasData === false ? 0.6 : 1,
      }}
      onMouseEnter={(e) => {
        if (hasData !== false) {
          e.currentTarget.style.transform = 'translateY(-2px)'
          e.currentTarget.style.boxShadow = theme.shadows.md
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)'
        e.currentTarget.style.boxShadow = 'none'
      }}
      onClick={() => hasData !== false && onViewData(endpoint, category)}
    >
      <Group justify="space-between" mb="xs">
        <Group gap="xs">
          <Icon size={20} color={theme.colors[color]?.[6]} />
          <Text fw={500} size="sm">
            {endpoint}
          </Text>
        </Group>
        <Group gap="xs">
          {hasData === false && (
            <Badge color="gray" variant="dot" size="sm">
              No Data
            </Badge>
          )}
          <Badge color={color} variant="light" size="sm">
            {category}
          </Badge>
        </Group>
      </Group>
      <Text size="xs" c="dimmed" lineClamp={2}>
        {hasData === false
          ? 'No data available for this endpoint'
          : 'Click to view data'}
      </Text>
    </Card>
  )
}

interface DataViewerProps {
  endpoint: string
  category: string
  projectId: string
  start: Date | null
  end: Date | null
  onClose: () => void
}

const DataViewer = ({
  endpoint,
  category,
  projectId,
  start,
  end,
  onClose,
}: DataViewerProps) => {
  const { data, isLoading, error } = useGetPTPData({
    pathParams: { projectId },
    queryParams: {
      endpoint,
      category,
      start: start ? dayjs(start).toISOString() : undefined,
      end: end ? dayjs(end).toISOString() : undefined,
    },
    queryOptions: {
      enabled: !!endpoint && !!category,
    },
  })
  const [sorting, setSorting] = useState<SortingState>([])
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 50,
  })

  type TableRow = Record<string, string | number | null>

  const tableData = useMemo(() => {
    if (!data?.data || data.data.length === 0) return []

    const element = data.data[0]
    const rows: TableRow[] = []

    // Get all unique intervals
    const intervals = new Set<string>()
    element.dataPoints.forEach((dp) => {
      dp.values.forEach((v) => {
        intervals.add(v.intervalStartUtc)
      })
    })

    // Create rows for each interval
    Array.from(intervals).forEach((interval) => {
      const row: Record<string, string | number | null> = {
        interval: dayjs(interval).format('YYYY-MM-DD HH:mm:ss'),
      }

      element.dataPoints.forEach((dp) => {
        const valueObj = dp.values.find((v) => v.intervalStartUtc === interval)
        row[dp.keyName] = (valueObj?.data[0]?.value ?? null) as number | null
      })

      rows.push(row)
    })

    return rows.sort((a, b) =>
      dayjs(a.interval).isAfter(dayjs(b.interval)) ? 1 : -1,
    )
  }, [data])

  const columns: ColumnDef<TableRow>[] = useMemo(() => {
    if (!data?.data || data.data.length === 0) return []

    const baseColumns: ColumnDef<TableRow>[] = [
      {
        accessorKey: 'interval',
        header: 'Interval',
        size: 180,
        enableSorting: true,
      },
    ]

    const element = data.data[0]
    element.dataPoints.forEach((dp) => {
      baseColumns.push({
        accessorKey: dp.keyName,
        header: dp.keyName,
        size: 150,
        enableSorting: true,
      })
    })

    return baseColumns
  }, [data])

  const plotData: Data[] = useMemo(() => {
    if (!data?.data || data.data.length === 0) return []

    const element = data.data[0]
    const traces: Data[] = []

    element.dataPoints.forEach((dp) => {
      const x: string[] = []
      const y: (number | null)[] = []

      dp.values.forEach((v) => {
        x.push(v.intervalStartUtc)
        y.push(v.data[0]?.value ?? null)
      })

      traces.push({
        x,
        y,
        type: 'scatter',
        mode: 'lines+markers',
        name: dp.keyName,
        line: { width: 2 },
      } as Data)
    })

    return traces
  }, [data])

  const plotLayout: Partial<Layout> = useMemo(
    () => ({
      title: { text: endpoint },
      xaxis: { title: { text: 'Time' } },
      yaxis: { title: { text: 'Value' } },
      hovermode: 'x unified',
      height: 500,
    }),
    [endpoint],
  )

  const table = useReactTable({
    columns,
    data: tableData,
    enableSorting: true,
    state: {
      sorting,
      pagination,
    },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  if (error) {
    return (
      <Card withBorder p="md">
        <Text c="red">Error loading data: {String(error)}</Text>
        <Button mt="md" onClick={onClose}>
          Close
        </Button>
      </Card>
    )
  }

  return (
    <Card withBorder p="md">
      <Group justify="space-between" mb="md">
        <Text fw={600} size="lg">
          {endpoint}
        </Text>
        <Button variant="subtle" onClick={onClose}>
          Close
        </Button>
      </Group>

      <LoadingOverlay visible={isLoading} />

      {data?.data && data.data.length > 0 ? (
        <Stack gap="md">
          <Tabs defaultValue="table">
            <Tabs.List>
              <Tabs.Tab value="table" leftSection={<IconDatabase size={16} />}>
                Table
              </Tabs.Tab>
              <Tabs.Tab value="chart" leftSection={<IconChartBar size={16} />}>
                Chart
              </Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="table" pt="md">
              <ScrollArea h={600}>
                <Table.ScrollContainer minWidth={700}>
                  <Table stickyHeader striped highlightOnHover withTableBorder>
                    <Table.Thead>
                      {table.getHeaderGroups().map((headerGroup) => (
                        <Table.Tr key={headerGroup.id}>
                          {headerGroup.headers.map((header) => {
                            const sorted = header.column.getIsSorted()
                            return (
                              <Table.Th
                                key={header.id}
                                w={header.column.getSize()}
                                style={{
                                  cursor: header.column.getCanSort()
                                    ? 'pointer'
                                    : undefined,
                                  userSelect: 'none',
                                  whiteSpace: 'nowrap',
                                }}
                                onClick={() => {
                                  if (!header.column.getCanSort()) return
                                  if (sorted === false) {
                                    header.column.toggleSorting(false)
                                    return
                                  }
                                  if (sorted === 'asc') {
                                    header.column.toggleSorting(true)
                                    return
                                  }
                                  header.column.toggleSorting(false)
                                }}
                              >
                                <Group gap={6} wrap="nowrap">
                                  {header.isPlaceholder
                                    ? null
                                    : flexRender(
                                        header.column.columnDef.header,
                                        header.getContext(),
                                      )}
                                  {sorted === 'asc' && (
                                    <IconChevronUp size={14} />
                                  )}
                                  {sorted === 'desc' && (
                                    <IconChevronDown size={14} />
                                  )}
                                </Group>
                              </Table.Th>
                            )
                          })}
                        </Table.Tr>
                      ))}
                    </Table.Thead>
                    <Table.Tbody>
                      {table.getRowModel().rows.map((row) => (
                        <Table.Tr key={row.id}>
                          {row.getVisibleCells().map((cell) => (
                            <Table.Td key={cell.id}>
                              {flexRender(
                                cell.column.columnDef.cell,
                                cell.getContext(),
                              )}
                            </Table.Td>
                          ))}
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Table.ScrollContainer>
              </ScrollArea>
              <Group justify="space-between" mt="sm">
                <Text size="sm" c="dimmed">
                  Page {table.getState().pagination.pageIndex + 1} of{' '}
                  {Math.max(table.getPageCount(), 1)}
                </Text>
                <Group gap="xs">
                  <Button
                    size="xs"
                    variant="default"
                    onClick={() => table.previousPage()}
                    disabled={!table.getCanPreviousPage()}
                  >
                    Previous
                  </Button>
                  <Button
                    size="xs"
                    variant="default"
                    onClick={() => table.nextPage()}
                    disabled={!table.getCanNextPage()}
                  >
                    Next
                  </Button>
                </Group>
              </Group>
            </Tabs.Panel>

            <Tabs.Panel value="chart" pt="md">
              <PlotlyPlot
                data={plotData}
                layout={plotLayout}
                isLoading={isLoading}
                error={error}
              />
            </Tabs.Panel>
          </Tabs>
        </Stack>
      ) : (
        <Text c="dimmed" ta="center" py="xl">
          {isLoading ? 'Loading data...' : 'No data available'}
        </Text>
      )}
    </Card>
  )
}

const PTPDataPage = () => {
  const { projectId } = useParams()
  const project = useSelectProject(projectId || '-1')
  useProjectDropdownToggle()

  const qseAccess = useGetQSEAccess({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: { enabled: !!projectId },
  })
  const hasQSEAccess = qseAccess.data?.has_access === true

  const [activeTab, setActiveTab] = useState<string>('performance')
  const [selectedEndpoint, setSelectedEndpoint] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [availabilityCache, setAvailabilityCache] = useState<
    Record<string, Record<string, boolean>>
  >({})
  const [dateRange, setDateRange] = useState<[Date | null, Date | null]>(() => {
    const now = dayjs()
    const yesterday = now.subtract(1, 'day')
    return [yesterday.toDate(), now.toDate()]
  })

  const { data: endpointsData, isLoading: endpointsLoading } =
    useGetPTPEndpoints({
      pathParams: { projectId: projectId || '-1' },
      queryOptions: {
        enabled: !!projectId && !!project.data && hasQSEAccess,
      },
    })

  // Check availability for the active tab when it's first accessed
  const { data: availabilityData, isLoading: availabilityLoading } =
    useGetPTPEndpointsAvailability({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        category: activeTab,
      },
      queryOptions: {
        enabled:
          !!projectId &&
          !!project.data &&
          hasQSEAccess &&
          !!endpointsData &&
          !availabilityCache[activeTab],
      },
    })

  // Cache availability data when it's received
  // This is a valid use case: caching async query results to avoid re-fetching
  useEffect(() => {
    if (availabilityData && activeTab && !availabilityCache[activeTab]) {
      setAvailabilityCache((prev) => ({
        ...prev,
        [activeTab]: availabilityData,
      }))
    }
    // We check availabilityCache[activeTab] in the condition, not as a dependency
    // oxlint-disable-next-line react/exhaustive-deps
  }, [availabilityData, activeTab])

  const handleViewData = useCallback((endpoint: string, category: string) => {
    setSelectedEndpoint(endpoint)
    setSelectedCategory(category)
  }, [])

  const handleCloseViewer = useCallback(() => {
    setSelectedEndpoint(null)
    setSelectedCategory(null)
  }, [])

  const categoryTabs = useMemo(() => {
    if (!endpointsData?.categories) return []

    return Object.keys(endpointsData.categories).map((category) => ({
      value: category,
      label: category.charAt(0).toUpperCase() + category.slice(1),
      count:
        endpointsData.categories[
          category as keyof typeof endpointsData.categories
        ].length,
    }))
  }, [endpointsData])

  if (project.isLoading) {
    return <PageLoader />
  }
  if (qseAccess.isLoading) {
    return <PageLoader />
  }
  if (!hasQSEAccess) {
    return (
      <PageError text="Your company's QSE integration is not set up for this project" />
    )
  }

  if (selectedEndpoint && selectedCategory) {
    return (
      <Stack p="md" w="100%" h="100%">
        <PageTitle>PTP Data - {selectedEndpoint} (Superadmin only)</PageTitle>
        <Group>
          <DatePickerInput
            type="range"
            label="Date Range"
            placeholder="Pick dates range"
            value={dateRange}
            onChange={(value) =>
              setDateRange([
                value[0] ? new Date(value[0]) : null,
                value[1] ? new Date(value[1]) : null,
              ])
            }
            w={300}
          />
          <Button variant="subtle" onClick={handleCloseViewer}>
            Back to Endpoints
          </Button>
        </Group>
        <DataViewer
          endpoint={selectedEndpoint}
          category={selectedCategory}
          projectId={projectId || '-1'}
          start={dateRange[0]}
          end={dateRange[1]}
          onClose={handleCloseViewer}
        />
      </Stack>
    )
  }

  return (
    <Stack p="md" w="100%" h="100%">
      <PageTitle>PTP Data (Superadmin only)</PageTitle>
      <Text size="sm" c="dimmed" mb="md">
        PowerTools Platform (PTP) API data for this project. Select an endpoint
        to view data.
      </Text>

      <LoadingOverlay
        visible={
          endpointsLoading ||
          (availabilityLoading && !availabilityCache[activeTab])
        }
      />

      {endpointsData && (
        <Tabs
          value={activeTab}
          onChange={(v) => setActiveTab(v || 'performance')}
        >
          <Tabs.List>
            {categoryTabs.map((tab) => (
              <Tabs.Tab key={tab.value} value={tab.value}>
                {tab.label} ({tab.count})
              </Tabs.Tab>
            ))}
          </Tabs.List>

          {categoryTabs.map((tab) => (
            <Tabs.Panel key={tab.value} value={tab.value} pt="md">
              <SimpleGrid cols={{ base: 1, sm: 2, md: 3, lg: 4 }} spacing="md">
                {endpointsData.categories[
                  tab.value as keyof typeof endpointsData.categories
                ].map((endpoint) => (
                  <EndpointCard
                    key={endpoint}
                    endpoint={endpoint}
                    category={tab.value}
                    hasData={availabilityCache[tab.value]?.[endpoint]}
                    onViewData={handleViewData}
                  />
                ))}
              </SimpleGrid>
            </Tabs.Panel>
          ))}
        </Tabs>
      )}
    </Stack>
  )
}

export default PTPDataPage
