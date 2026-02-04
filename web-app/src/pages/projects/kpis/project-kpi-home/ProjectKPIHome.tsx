import { useGetUserType } from '@/api/admin'
import {
  useGetUserFavoriteKPITypes,
  useUpdateUserKPITypeFavoriteMutation,
} from '@/api/v1/admin/user_kpi_types'
import {
  KPISummaryTableRow,
  useGetProjectKPISummaryTable,
} from '@/api/v1/protected/web-application/projects/project-kpi-summary-table'
import { PageTitle } from '@/components/PageTitle'
import {
  Button,
  Checkbox,
  Group,
  Menu,
  Paper,
  Stack,
  Table,
  Text,
  useComputedColorScheme,
} from '@mantine/core'
import { useLocalStorage } from '@mantine/hooks'
import { IconColumns, IconFileText, IconPlus } from '@tabler/icons-react'
import {
  type ColumnFiltersState,
  type SortingState,
  type Table as TanStackTable,
  type VisibilityState,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'

import RequestKPIModal from '../RequestKPIModal'
import {
  filterByStatus,
  useCreateColumns,
} from './columns-config/ColumnsConfig'
import {
  renderSkeletonBody,
  renderTableBody,
  renderTableHeader,
} from './table-shell/TableShell'

//
// This file is in charge of the main page component for the Project KPI Home page.
// It pulls the column configuration from the columns-config/ColumnsConfig.tsx file and the
// table styling from the table-shell/TableShell.tsx file.
// The primary responsibilities of this file are state management, data fetching,
// and packaging together the final default export function.
//

// ============================================================================
// Types & Constants
// ============================================================================

export type EnrichedKPISummaryTableRow = KPISummaryTableRow

const columnLabelMap: Record<string, string> = {
  hidden: 'Hidden',
  yesterday: 'Yesterday',
  week: 'Week',
  month: 'Month',
  ytd: 'YTD',
  year: 'Year',
}

// ============================================================================
// UI Components
// ============================================================================

type ColumnVisibilityMenuProps = {
  table: TanStackTable<EnrichedKPISummaryTableRow>
}

const ColumnVisibilityMenu = ({ table }: ColumnVisibilityMenuProps) => {
  const hideableColumns = table
    .getAllLeafColumns()
    .filter((column) => column.getCanHide())

  return (
    <Menu shadow="md" width={200} closeOnItemClick={false}>
      <Menu.Target>
        <Button variant="light" leftSection={<IconColumns size={16} />}>
          Columns
        </Button>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Label>Toggle Columns</Menu.Label>
        {hideableColumns.map((column) => {
          const label = columnLabelMap[column.id] || column.id
          return (
            <Menu.Item key={column.id}>
              <Checkbox
                label={label}
                checked={column.getIsVisible()}
                onChange={column.getToggleVisibilityHandler()}
              />
            </Menu.Item>
          )
        })}
      </Menu.Dropdown>
    </Menu>
  )
}

type PageHeaderProps = {
  table: TanStackTable<EnrichedKPISummaryTableRow>
}

const PageHeader = ({ table }: PageHeaderProps) => (
  <Group justify="space-between" align="center">
    <PageTitle
      info={
        <Text>
          View and analyze project KPIs across different time periods (Week,
          Month, YTD, Year). Use the Columns menu to toggle time period columns.
          Click column headers to sort. Heart KPIs to mark them as favorites for
          quick access. The table displays performance metrics with trend
          indicators and status filters.
        </Text>
      }
    >
      Project KPIs
    </PageTitle>
    <ColumnVisibilityMenu table={table} />
  </Group>
)

// ============================================================================
// Main Component
// ============================================================================

export default function ProjectKPIHome() {
  const computedColorScheme = useComputedColorScheme('light')

  // URL params
  const [searchParams, setSearchParams] = useSearchParams()
  const { projectId } = useParams()

  //
  // Column visibility state managed with local storage
  //

  const [columnVisibility, setColumnVisibility] =
    useLocalStorage<VisibilityState>({
      key: 'project-kpi-columns-visibility',
      defaultValue: {
        hidden: true,
        yesterday: false,
        week: true,
        month: false,
        ytd: true,
        year: false,
      },
    })

  //
  // Sorting states managed with local storage
  //

  const [sortingColumnId, setSortingColumnId] = useLocalStorage<string | null>({
    key: 'project-kpi-sorting-column',
    defaultValue: 'favorites',
  })

  // Convert from simple columnId string to TanStack Table's SortingState
  const sorting = useMemo<SortingState>(() => {
    if (!sortingColumnId) return []
    return [{ id: sortingColumnId, desc: false }]
  }, [sortingColumnId])

  // Convert from TanStack Table's SortingState back to simple columnId string
  const handleSortingChange = (
    updater: SortingState | ((old: SortingState) => SortingState),
  ) => {
    const newSorting =
      typeof updater === 'function' ? updater(sorting) : updater
    const columnId = newSorting.length > 0 ? newSorting[0].id : null
    setSortingColumnId(columnId)
  }

  //
  // Filter states
  //

  // all filters derived from state except for device_type_id
  const [otherFilters, setOtherFilters] = useState<ColumnFiltersState>([
    { id: 'hidden', value: false }, // default filter value
  ])

  // Derive columnFilters from URL + state
  const columnFilters = useMemo<ColumnFiltersState>(() => {
    const filters: ColumnFiltersState = []

    // Add device_type_id from URL
    const deviceTypeParam = searchParams.get('device_type')
    if (deviceTypeParam) {
      const deviceTypeId = Number(deviceTypeParam)
      if (!isNaN(deviceTypeId)) {
        filters.push({
          id: 'device_type_id',
          value: deviceTypeId,
        })
      }
    }

    // Add all other filters from state
    filters.push(...otherFilters)

    return filters
  }, [searchParams, otherFilters])

  // Handle column filter changes: route device_type_id to URL, others to state
  const handleColumnFiltersChange = (
    updater:
      | ColumnFiltersState
      | ((old: ColumnFiltersState) => ColumnFiltersState),
  ) => {
    const newFilters =
      typeof updater === 'function' ? updater(columnFilters) : updater

    // Separate device_type_id filter from others
    const deviceTypeFilter = newFilters.find((f) => f.id === 'device_type_id')
    const remainingFilters = newFilters.filter((f) => f.id !== 'device_type_id')

    // Update URL for device_type_id
    const newSearchParams = new URLSearchParams(searchParams)
    const deviceTypeValue = deviceTypeFilter?.value
    if (deviceTypeValue && typeof deviceTypeValue === 'number') {
      newSearchParams.set('device_type', deviceTypeValue.toString())
    } else {
      newSearchParams.delete('device_type')
    }
    setSearchParams(newSearchParams, { replace: true })

    // Update state for other filters
    setOtherFilters(remainingFilters)
  }

  // Derive modal state from URL parameter
  const requestModalOpen = searchParams.get('openRequestModal') === 'true'

  //
  // Data fetching
  //

  const kpiSummaryTable = useGetProjectKPISummaryTable(
    useMemo(
      () => ({
        pathParams: { project_id: projectId || '-1' },
        queryOptions: {
          enabled: !!projectId,
        },
      }),
      [projectId],
    ),
  )

  const { data: favorites, isLoading: favoritesLoading } =
    useGetUserFavoriteKPITypes({})
  const updateFavorite = useUpdateUserKPITypeFavoriteMutation()
  const { data: userType } = useGetUserType({})
  const isSuperAdmin = userType?.name_short === 'superadmin'

  const favoriteSet = useMemo(() => {
    return new Set(favorites?.map((f) => f.kpi_type_id) || [])
  }, [favorites])

  // Enrich rows with favorite status
  const enrichedRows = useMemo<EnrichedKPISummaryTableRow[]>(() => {
    const rows = kpiSummaryTable.data?.rows || []
    return rows.map((row) => ({
      ...row,
      is_favorite: favoriteSet.has(row.kpi_type_id),
    }))
  }, [kpiSummaryTable.data?.rows, favoriteSet])

  // Compute unique device types for filter dropdown
  const deviceTypes = useMemo(() => {
    const deviceTypeMap: Record<number, string> = {}
    enrichedRows.forEach((row) => {
      const id = row.device_type_id
      const name = row.device_type_name_long
      if (id !== undefined && id !== null && name) {
        deviceTypeMap[id] = name
      }
    })
    return deviceTypeMap
  }, [enrichedRows])

  const toggleFavorite = (kpiTypeId: number, isFavorited: boolean) => {
    updateFavorite.mutate({
      kpiTypeId,
      isFavorited,
    })
  }

  // Table configuration
  const columns = useCreateColumns(deviceTypes, isSuperAdmin)

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable<EnrichedKPISummaryTableRow>({
    data: enrichedRows,
    columns,
    enableSorting: true,
    state: {
      columnVisibility,
      columnFilters,
      sorting,
    },
    meta: {
      projectId,
      dates: {
        start: {
          week: kpiSummaryTable.data?.start?.week || null,
          month: kpiSummaryTable.data?.start?.month || null,
          ytd: kpiSummaryTable.data?.start?.ytd || null,
          year: kpiSummaryTable.data?.start?.year || null,
        },
        yesterday: kpiSummaryTable.data?.yesterday || null,
      },
      trend_dates: kpiSummaryTable.data?.trend_dates || null,
      favorites: favoriteSet,
      toggleFavorite,
      favoritesLoading,
    },
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    filterFns: {
      filterByStatus,
    },
    onColumnVisibilityChange: setColumnVisibility,
    onColumnFiltersChange: handleColumnFiltersChange,
    onSortingChange: handleSortingChange,
  })

  return (
    <Stack
      gap="md"
      p="lg"
      style={{ height: '100%', minHeight: 'calc(100vh - 100px)' }}
      justify="space-between"
    >
      <Stack gap="md">
        <PageHeader table={table} />
        <Paper
          withBorder
          shadow="none"
          radius="md"
          style={{
            overflow: 'hidden',
            backgroundColor:
              computedColorScheme === 'light'
                ? 'var(--mantine-color-default)'
                : undefined,
          }}
        >
          <Table.ScrollContainer
            minWidth="100%"
            maxHeight="calc(100vh - 180px)"
          >
            <Table
              style={{
                width: '100%',
                tableLayout: 'fixed',
              }}
              highlightOnHover
              striped
              stickyHeader
            >
              {renderTableHeader(table)}
              {kpiSummaryTable.isLoading || favoritesLoading
                ? renderSkeletonBody(table)
                : renderTableBody(table)}
            </Table>
          </Table.ScrollContainer>
        </Paper>
      </Stack>
      <Group justify="flex-start">
        <Button
          variant="subtle"
          size="sm"
          leftSection={
            <Group gap={4}>
              <IconPlus size={14} />
              <IconFileText size={14} />
            </Group>
          }
          onClick={() => {
            const newParams = new URLSearchParams(searchParams)
            newParams.set('openRequestModal', 'true')
            setSearchParams(newParams, { replace: true })
          }}
        >
          Request New Contractual KPI
        </Button>
      </Group>
      <RequestKPIModal
        opened={requestModalOpen}
        onClose={() => {
          const newParams = new URLSearchParams(searchParams)
          newParams.delete('openRequestModal')
          setSearchParams(newParams, { replace: true })
        }}
      />
    </Stack>
  )
}
