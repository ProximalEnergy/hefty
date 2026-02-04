import { KPISummaryTableRow } from '@/api/v1/protected/web-application/projects/project-kpi-summary-table'
import { Group, Text } from '@mantine/core'
import { IconEyeOff } from '@tabler/icons-react'
import {
  type FilterFn,
  type Row,
  type Table,
  createColumnHelper,
} from '@tanstack/react-table'
import { type ReactNode, useMemo } from 'react'
import { Link } from 'react-router'

import type { EnrichedKPISummaryTableRow } from '../ProjectKPIHome'
import DeviceTypeFilter from './DeviceTypeFilter'
import FavoriteFilter from './FavoriteFilter'
import FavoriteHeart from './FavoriteHeart'
import HiddenFilter from './HiddenFilter'
import { KPISparkline } from './KPISparkline'
import MetricCellWithIcon from './MetricCellWithIcon'
import MetricInfoHoverCard from './MetricInfoHoverCard'
import SimpleInfoHoverCard from './SimpleInfoHoverCard'
import StatusFilter from './StatusFilter'
import TextFilter from './TextFilter'

//
// This file is in charge of creating the tanstack column configuration for the Project KPI Home page.
// Any rendered sub-components should be defined in this directory. Universal table properties should be
// defined in the table-shell/TableShell.tsx file.
//

// ============================================================================
// Types
// ============================================================================

type KpiTableMeta = {
  projectId: string | undefined
  dates: {
    start: {
      week: string | null
      month: string | null
      ytd: string | null
      year: string | null
    }
    yesterday: string | null
  }
  trend_dates: string[] | null // Common 365-day array from metadata
  favorites: Set<number>
  toggleFavorite: (kpiTypeId: number, isFavorited: boolean) => void
  favoritesLoading: boolean
}

type KpiStatus =
  | 0 // Normal
  | 1 // Warning
  | 2 // Critical

// ============================================================================
// Constants
// ============================================================================

const columnHelper = createColumnHelper<EnrichedKPISummaryTableRow>()

// ============================================================================
// Data Processing Helpers
// ============================================================================
const filterTrendDataByStartDate = (
  trendDates: string[],
  trendData: (number | null)[],
  startDate: string,
): { dates: string[]; data: (number | null)[] } => {
  const startDateObj = new Date(startDate)
  const startIndex = trendDates.findIndex(
    (date) => new Date(date) >= startDateObj,
  )

  if (startIndex === -1) {
    return { dates: [], data: [] }
  }

  // Since arrays are aligned and complete, simple slice works
  return {
    dates: trendDates.slice(startIndex),
    data: trendData.slice(startIndex),
  }
}

const calculateKpiStatus = (
  row: Row<EnrichedKPISummaryTableRow>,
  columnId: string,
): KpiStatus => {
  const value = row.getValue(columnId) as number | null
  const original = row.original
  if (value === null) {
    return 0
  }
  if (original.critical_low !== null && value <= original.critical_low) {
    return 2
  }
  if (original.warning_low !== null && value <= original.warning_low) {
    return 1
  }
  if (original.critical_high !== null && value >= original.critical_high) {
    return 2
  }
  if (original.warning_high !== null && value >= original.warning_high) {
    return 1
  }
  return 0
}

const statusSort = (
  rowA: Row<EnrichedKPISummaryTableRow>,
  rowB: Row<EnrichedKPISummaryTableRow>,
  columnId: string,
) => {
  const statusA = calculateKpiStatus(rowA, columnId)
  const statusB = calculateKpiStatus(rowB, columnId)
  return statusB - statusA
}

// ============================================================================
// Value Formatting & Status Calculation
// ============================================================================

const formatKpiValueString = (value: number, unit: string | null): string => {
  const fractionDigits = value > 100 ? 0 : 1
  if (unit === '%') {
    return value.toLocaleString('en-US', {
      style: 'percent',
      maximumFractionDigits: fractionDigits,
      minimumFractionDigits: fractionDigits,
    })
  } else {
    const formatted = value.toLocaleString('en-US', {
      style: 'decimal',
      maximumFractionDigits: fractionDigits,
      minimumFractionDigits: fractionDigits,
    })
    return unit ? `${formatted} ${unit}` : formatted
  }
}

const getStatusColor = (status: KpiStatus): 'red' | 'orange' | undefined => {
  return status === 2 ? 'red' : status === 1 ? 'orange' : undefined
}

const getFormattedValueAndColor = (
  row: Row<EnrichedKPISummaryTableRow>,
  columnId: string,
): { formattedValue: string; color: 'red' | 'orange' | undefined } | null => {
  const value = row.getValue(columnId) as number | null
  if (value === null) {
    return null
  }

  const original = row.original
  const formattedValue = formatKpiValueString(value, original.unit)
  const status = calculateKpiStatus(row, columnId)
  const color = getStatusColor(status)

  return { formattedValue, color }
}

const createValueText = (
  formattedValue: string,
  color: 'red' | 'orange' | undefined,
) => (
  <Text size="sm" c={color}>
    {formattedValue}
  </Text>
)

// ============================================================================
// Filter Functions
// ============================================================================

// filterValue should now be a 3 element array of booleans (e.g. [true, false, true])
// filterValue[0] is for normal status
// filterValue[1] is for warning status
// filterValue[2] is for critical status

export const filterByStatus: FilterFn<EnrichedKPISummaryTableRow> = (
  row,
  columnId,
  filterValue,
) => {
  const status = calculateKpiStatus(row, columnId)
  return filterValue[status]
}

// filterValue format: [showFavorites, showNonFavorites]
const filterByFavorites: FilterFn<EnrichedKPISummaryTableRow> = (
  row,
  _columnId,
  filterValue,
) => {
  const [showFavorites, showNonFavorites] = filterValue as [boolean, boolean]
  return row.original.is_favorite ? showFavorites : showNonFavorites
}

const buildKpiLinkPath = (
  projectId: string | undefined,
  kpiTypeId: number,
  startDate: string | null,
  endDate: string | null,
): string | null => {
  if (!projectId || !startDate || !endDate) {
    return null
  }
  return `/projects/${projectId}/kpis/type/${kpiTypeId}?start=${startDate}&end=${endDate}`
}

// ============================================================================
// Cell Renderers
// ============================================================================

const metricCell = ({
  row,
  projectId,
}: {
  row: KPISummaryTableRow
  projectId: string | undefined
}) => {
  const linkPath = row.is_contract_kpi
    ? `/projects/${projectId}/kpis/contractual/${row.name_short.replace(/_/g, '-')}`
    : `/projects/${projectId}/kpis/type/${row.kpi_type_id}`

  return (
    <MetricCellWithIcon showIcon={row.is_contract_kpi}>
      <Group gap={4} style={{ width: '100%' }}>
        <Link
          to={linkPath}
          style={{
            color: 'inherit',
            textDecoration: 'none',
            display: 'block',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flex: 1,
          }}
        >
          <Text
            size="sm"
            style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {row.name_metric}
          </Text>
        </Link>
        {row.description && (
          <MetricInfoHoverCard
            description={row.description}
            unit={row.unit}
            critical_low={row.critical_low}
            warning_low={row.warning_low}
            warning_high={row.warning_high}
            critical_high={row.critical_high}
          />
        )}
      </Group>
    </MetricCellWithIcon>
  )
}

const renderValueCell = ({
  row,
  columnId,
  table,
}: {
  row: Row<EnrichedKPISummaryTableRow>
  columnId: string
  table?: Table<EnrichedKPISummaryTableRow>
}): ReactNode => {
  const formattedAndColor = getFormattedValueAndColor(row, columnId)
  if (!formattedAndColor) {
    return ''
  }

  const { formattedValue, color } = formattedAndColor
  const valueText = createValueText(formattedValue, color)

  // Add link for yesterday column if meta is available
  if (table && columnId === 'yesterday') {
    const meta = table.options.meta as KpiTableMeta | undefined
    const endDate = meta?.dates?.yesterday ?? null
    const linkPath = buildKpiLinkPath(
      meta?.projectId,
      row.original.kpi_type_id,
      endDate, // Use yesterday as both start and end for single day view
      endDate,
    )

    if (linkPath) {
      return (
        <Link
          to={linkPath}
          style={{
            color: 'inherit',
            textDecoration: 'none',
          }}
        >
          {valueText}
        </Link>
      )
    }
  }

  return valueText
}

const renderValueAndSparklineCell = ({
  row,
  columnId,
  table,
}: {
  row: Row<EnrichedKPISummaryTableRow>
  columnId: string
  table: Table<EnrichedKPISummaryTableRow>
}): ReactNode => {
  const original = row.original
  const meta = table.options.meta as KpiTableMeta | undefined

  const formattedAndColor = getFormattedValueAndColor(row, columnId)
  if (!formattedAndColor) {
    return ''
  }

  const { formattedValue, color } = formattedAndColor

  // Determine start date based on columnId
  const startDate = meta?.dates?.start
    ? (meta.dates.start[columnId as keyof typeof meta.dates.start] ?? null)
    : null

  // Get end date (yesterday)
  const endDate = meta?.dates?.yesterday ?? null

  // Build link path if projectId, startDate, and endDate are available
  const linkPath = buildKpiLinkPath(
    meta?.projectId,
    original.kpi_type_id,
    startDate,
    endDate,
  )

  // Use common trend_dates from metadata (all KPIs share the same dates)
  const commonTrendDates = meta?.trend_dates || []

  // Filter trend data if startDate exists
  const filteredData =
    startDate && commonTrendDates.length > 0
      ? filterTrendDataByStartDate(
          commonTrendDates,
          original.trend_data,
          startDate,
        )
      : { dates: commonTrendDates, data: original.trend_data }

  // Build thresholds object
  const thresholds = {
    critical_low: original.critical_low,
    warning_low: original.warning_low,
    warning_high: original.warning_high,
    critical_high: original.critical_high,
  }

  // Create the value Text component
  const valueText = createValueText(formattedValue, color)

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        justifyContent: 'flex-end',
      }}
    >
      {linkPath ? (
        <Link
          to={linkPath}
          style={{
            color: 'inherit',
            textDecoration: 'none',
          }}
        >
          {valueText}
        </Link>
      ) : (
        valueText
      )}
      {filteredData.dates.length > 0 && (
        <KPISparkline
          trendDates={filteredData.dates}
          trendData={filteredData.data}
          unit={original.unit}
          startDate={startDate}
          endDate={endDate}
          thresholds={thresholds}
        />
      )}
    </div>
  )
}

// ============================================================================
// UI Components (Headers & Filters)
// ============================================================================

const columnHeader = (header: string, description?: string) => {
  const headerText = (
    <Text size="sm" fw={600}>
      {header}
    </Text>
  )

  return (
    <Group gap={4}>
      {headerText}
      {description && <SimpleInfoHoverCard description={description} />}
    </Group>
  )
}

const createValueColumn = (
  accessor: 'week' | 'month' | 'ytd' | 'year',
  label: string,
  description: string,
) =>
  columnHelper.accessor(accessor, {
    header: () => columnHeader(label, description),
    cell: ({ row, table }) =>
      renderValueAndSparklineCell({ row, columnId: accessor, table }),
    sortingFn: statusSort,
    filterFn: filterByStatus,
    size: undefined,
    meta: {
      FilterComponent: StatusFilter,
      align: 'right',
    },
  })

// ============================================================================
// Column Definitions
// ============================================================================

export const useCreateColumns = (
  deviceTypes: Record<number, string> = {},
  isSuperAdmin: boolean = false,
) => {
  return useMemo(
    () => [
      columnHelper.accessor(
        (row) => {
          // Return 0 if favorited, 1 if not - this makes ascending sort put favorites first
          // Accessor reads directly from row data which updates when data array reference changes
          return row.is_favorite ? 0 : 1
        },
        {
          id: 'favorites',
          header: () => null,
          cell: ({ row, table }) => {
            const meta = table.options.meta as KpiTableMeta | undefined
            const toggleFavorite = meta?.toggleFavorite || (() => {})
            // Read directly from row data instead of looking up in meta
            const isFavorite = row.original.is_favorite
            return (
              <FavoriteHeart
                kpiTypeId={row.original.kpi_type_id}
                isFavorite={isFavorite}
                onToggle={toggleFavorite}
              />
            )
          },
          enableHiding: false,
          enableSorting: true,
          filterFn: filterByFavorites,
          size: 50,
          meta: {
            FilterComponent: FavoriteFilter,
            align: 'center',
          },
        },
      ),
      ...(isSuperAdmin
        ? [
            columnHelper.accessor('is_hidden', {
              id: 'hidden',
              header: () => null,
              cell: ({ row }) =>
                row.original.is_hidden ? <IconEyeOff size={16} /> : null,
              enableHiding: true,
              enableSorting: true,
              filterFn: 'equals',
              size: 50,
              meta: {
                FilterComponent: HiddenFilter,
                align: 'center',
              },
            }),
          ]
        : []),
      columnHelper.accessor('device_type_id', {
        header: () => columnHeader('Device Type'),
        cell: ({ row }) => (
          <Text size="sm">{row.original.device_type_name_long}</Text>
        ),
        enableHiding: false,
        filterFn: 'equals',
        size: 170,
        meta: {
          FilterComponent: DeviceTypeFilter,
          deviceTypes,
          align: 'right',
        },
      }),
      columnHelper.accessor('name_metric', {
        header: () => columnHeader('Metric'),
        cell: ({ row, table }) => {
          const meta = table.options.meta as KpiTableMeta | undefined
          return metricCell({ row: row.original, projectId: meta?.projectId })
        },
        enableHiding: false,
        filterFn: 'includesString',
        size: 300,
        meta: {
          FilterComponent: TextFilter,
          align: 'left',
        },
      }),
      columnHelper.accessor('yesterday', {
        header: () =>
          columnHeader('Yesterday', 'The KPI value calculated for yesterday.'),
        cell: ({ row, table }) =>
          renderValueCell({ row, columnId: 'yesterday', table }),
        enableHiding: true,
        sortingFn: statusSort,
        filterFn: filterByStatus,
        size: undefined,
        meta: {
          FilterComponent: StatusFilter,
          align: 'right',
        },
      }),
      createValueColumn('week', 'Week', 'Aggregated KPI from the last 7 days.'),
      createValueColumn(
        'month',
        'Month',
        'Aggregated KPI from the last 30 days.',
      ),
      createValueColumn(
        'ytd',
        'YTD',
        'Aggregated KPI from January 1st of the current year to today.',
      ),
      createValueColumn(
        'year',
        'Year',
        'Aggregated KPI from the last 365 days.',
      ),
    ],
    [deviceTypes, isSuperAdmin],
  )
}
