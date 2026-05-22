import {
  formatDataTableValue,
  getDataTableAlignment,
  getDataTableJustify,
  sortGroupedVisibleRows,
} from '@/components/DataTable/utils'
import {
  Box,
  Group,
  Table as MantineTable,
  Text,
  Tooltip,
  UnstyledButton,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import {
  IconArrowsSort,
  IconChevronDown,
  IconChevronRight,
  IconSortAscending,
  IconSortDescending,
} from '@tabler/icons-react'
import {
  type Cell,
  type Column,
  type Row,
  type Table as TanStackTable,
  flexRender,
} from '@tanstack/react-table'
import { useVirtualizer } from '@tanstack/react-virtual'
import { type KeyboardEvent, type ReactNode, useMemo, useRef } from 'react'

const ICON_SIZE = 14

interface DataTableProps<TData> {
  table: TanStackTable<TData>
  emptyState?: ReactNode
  getRowCanClick?: (row: Row<TData>) => boolean
  onRowClick?: (row: Row<TData>) => void
  renderExpandedRow?: (row: Row<TData>) => ReactNode
  estimateRowSize?: number
  maxHeight?: number | string
}

const getDataTableColors = (
  theme: ReturnType<typeof useMantineTheme>,
  isDark: boolean,
) => ({
  aggregateText: isDark ? theme.colors.gray[3] : theme.colors.gray[7],
  background: 'var(--mantine-color-body)',
  border: 'var(--mantine-color-default-border)',
  gridLine: isDark ? theme.colors.dark[5] : theme.colors.gray[1],
  groupedBackground: isDark ? theme.colors.dark[6] : theme.colors.gray[0],
  rowBackground: 'var(--mantine-color-body)',
  subtleBorder: isDark ? theme.colors.dark[4] : theme.colors.gray[1],
})

const getColumnTrack = <TData,>(
  column: Column<TData, unknown>,
  defaultColumnSize: number,
) => {
  const width = column.getSize()

  if (column.columnDef.size != null && width !== defaultColumnSize) {
    return `${width}px`
  }

  return `minmax(${width}px, 1fr)`
}

/**
 * Maps column sort state to `aria-sort`.
 *
 * @param sortState - `asc`, `desc`, or false when the column is not sorted.
 * @returns `ascending`, `descending`, or `none` for assistive technologies.
 */
const getAriaSort = (sortState: false | 'asc' | 'desc') => {
  if (sortState === 'asc') return 'ascending'
  if (sortState === 'desc') return 'descending'
  return 'none'
}

/**
 * Icon shown beside sortable column headers.
 *
 * @param sortState - `asc`, `desc`, or false when this column is not sorted.
 * @returns Tabler icons: ascending, descending, or a subdued selector glyph.
 */
const renderSortIcon = (sortState: false | 'asc' | 'desc') => {
  if (sortState === 'asc') return <IconSortAscending size={ICON_SIZE} />
  if (sortState === 'desc') return <IconSortDescending size={ICON_SIZE} />
  return <IconArrowsSort size={ICON_SIZE} opacity={0.45} />
}

export function DataTable<TData>({
  table,
  emptyState,
  getRowCanClick,
  onRowClick,
  renderExpandedRow,
  estimateRowSize = 42,
  maxHeight,
}: DataTableProps<TData>) {
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme('light')
  const colors = getDataTableColors(theme, colorScheme === 'dark')
  const parentRef = useRef<HTMLDivElement>(null)
  const visibleColumns = table.getVisibleLeafColumns()
  const hasClientPagination =
    !!table.options.getPaginationRowModel && !table.options.manualPagination
  const prePaginationRows = hasClientPagination
    ? table.getPrePaginationRowModel().rows
    : table.getRowModel().rows

  // === START TABLE STATE ===
  const tableState = table.getState() // access the entire internal state
  // Sorting
  const activeSort = tableState.sorting?.[0] // first ColumnSort, if any
  const activeSortId = activeSort?.id // first sorted column id, if any
  const activeSortDesc = activeSort?.desc // first sorted column direction, if any
  // Pagination
  const pagination = tableState.pagination
  // === END TABLE STATE ===

  const rows = useMemo(() => {
    const sortedRows = sortGroupedVisibleRows(
      prePaginationRows,
      activeSortId,
      activeSortDesc,
    )

    if (!hasClientPagination) {
      return sortedRows
    }

    const start = pagination.pageIndex * pagination.pageSize
    return sortedRows.slice(start, start + pagination.pageSize)
  }, [
    activeSortDesc,
    activeSortId,
    hasClientPagination,
    pagination.pageIndex,
    pagination.pageSize,
    prePaginationRows,
  ])

  const virtualizer = useVirtualizer({
    count: rows.length,
    estimateSize: () => estimateRowSize,
    getScrollElement: () => parentRef.current,
    overscan: 12,
  })

  const totalColumnWidth = visibleColumns.reduce(
    (total, column) => total + column.getSize(),
    0,
  )
  const defaultColumnSize = table.options.defaultColumn?.size ?? 150
  const gridTemplateColumns = visibleColumns
    .map((column) => getColumnTrack(column, defaultColumnSize))
    .join(' ')
  const virtualRows = virtualizer.getVirtualItems()

  const rowCanClick = (row: Row<TData>) => {
    return getRowCanClick?.(row) ?? Boolean(onRowClick)
  }

  const handleRowClick = (row: Row<TData>) => {
    if (row.getIsGrouped()) {
      row.toggleExpanded()
      return
    }

    if (rowCanClick(row)) {
      onRowClick?.(row)
    }
  }

  const handleRowKeyDown = (
    event: KeyboardEvent<HTMLTableRowElement>,
    row: Row<TData>,
  ) => {
    if (event.key !== 'Enter' && event.key !== ' ') return

    if (row.getIsGrouped() || onRowClick) {
      event.preventDefault()
      handleRowClick(row)
    }
  }

  return (
    <Box
      h={maxHeight == null ? '100%' : undefined}
      style={{
        border: `1px solid ${colors.border}`,
        borderRadius: theme.radius.sm,
        minHeight: 0,
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <Box
        ref={parentRef}
        h={maxHeight == null ? '100%' : undefined}
        style={{
          background: colors.background,
          maxHeight,
          overflow: 'auto',
          position: 'relative',
        }}
      >
        <MantineTable
          highlightOnHover
          role="grid"
          withRowBorders
          style={{
            display: 'grid',
            gridTemplateRows: 'auto auto',
            minWidth: totalColumnWidth,
            width: '100%',
          }}
        >
          <MantineTable.Thead
            style={{
              background: colors.background,
              borderBottom: `1px solid ${colors.border}`,
              display: 'grid',
              position: 'sticky',
              top: 0,
              zIndex: 2,
            }}
          >
            {table.getHeaderGroups().map((headerGroup) => (
              <MantineTable.Tr
                key={headerGroup.id}
                style={{
                  display: 'grid',
                  gridTemplateColumns,
                  minHeight: 42,
                }}
              >
                {headerGroup.headers.map((header) => {
                  const column = header.column
                  const canSort = column.getCanSort()
                  const align = getDataTableAlignment(
                    column.columnDef.meta?.align,
                  )
                  const content = header.isPlaceholder
                    ? null
                    : flexRender(column.columnDef.header, header.getContext())
                  const headerContent = (
                    <Group
                      gap={6}
                      justify={getDataTableJustify(align)}
                      wrap="nowrap"
                    >
                      <Text fw={600} size="sm" truncate>
                        {content}
                      </Text>
                      {canSort && renderSortIcon(column.getIsSorted())}
                    </Group>
                  )

                  return (
                    <MantineTable.Th
                      key={header.id}
                      aria-sort={
                        canSort ? getAriaSort(column.getIsSorted()) : undefined
                      }
                      scope="col"
                      style={{
                        alignItems: 'center',
                        display: 'flex',
                        justifyContent: getDataTableJustify(align),
                        minWidth: 0,
                        textAlign: align,
                      }}
                    >
                      {canSort ? (
                        <Tooltip
                          disabled={!column.columnDef.meta?.headerTooltip}
                          label={column.columnDef.meta?.headerTooltip}
                          withArrow
                        >
                          <UnstyledButton
                            onClick={column.getToggleSortingHandler()}
                            style={{
                              borderRadius: theme.radius.xs,
                              color: 'inherit',
                              outlineOffset: 2,
                              width: '100%',
                            }}
                          >
                            {headerContent}
                          </UnstyledButton>
                        </Tooltip>
                      ) : (
                        headerContent
                      )}
                    </MantineTable.Th>
                  )
                })}
              </MantineTable.Tr>
            ))}
          </MantineTable.Thead>

          <MantineTable.Tbody
            style={{
              display: 'grid',
              height:
                rows.length === 0
                  ? estimateRowSize
                  : virtualizer.getTotalSize(),
              position: 'relative',
            }}
          >
            {rows.length === 0 && (
              <MantineTable.Tr
                style={{
                  display: 'grid',
                  inset: 0,
                  position: 'absolute',
                }}
              >
                <MantineTable.Td
                  colSpan={visibleColumns.length}
                  style={{
                    alignItems: 'center',
                    display: 'flex',
                    justifyContent: 'center',
                    minWidth: totalColumnWidth,
                  }}
                >
                  {emptyState ?? (
                    <Text c="dimmed" size="sm">
                      No results
                    </Text>
                  )}
                </MantineTable.Td>
              </MantineTable.Tr>
            )}

            {virtualRows.map((virtualRow) => {
              const row = rows[virtualRow.index]
              if (!row) return null

              const expandedContent =
                row.getIsGrouped() || !row.getIsExpanded()
                  ? null
                  : renderExpandedRow?.(row)

              return (
                <DataTableRow
                  expandedContent={expandedContent}
                  key={row.id}
                  gridTemplateColumns={gridTemplateColumns}
                  measureElement={virtualizer.measureElement}
                  onClick={() => handleRowClick(row)}
                  onKeyDown={(event) => handleRowKeyDown(event, row)}
                  rowCanClick={rowCanClick(row)}
                  row={row}
                  rowHeight={estimateRowSize}
                  virtualRowIndex={virtualRow.index}
                  top={virtualRow.start}
                />
              )
            })}
          </MantineTable.Tbody>
        </MantineTable>
      </Box>
    </Box>
  )
}

function DataTableRow<TData>({
  expandedContent,
  gridTemplateColumns,
  measureElement,
  onClick,
  onKeyDown,
  row,
  rowCanClick,
  rowHeight,
  virtualRowIndex,
  top,
}: {
  expandedContent?: ReactNode
  gridTemplateColumns: string
  measureElement: (node: Element | null) => void
  onClick: () => void
  onKeyDown: (event: KeyboardEvent<HTMLTableRowElement>) => void
  row: Row<TData>
  rowCanClick: boolean
  rowHeight: number
  virtualRowIndex: number
  top: number
}) {
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme('light')
  const colors = getDataTableColors(theme, colorScheme === 'dark')
  const isGrouped = row.getIsGrouped()
  const expandIndicatorCellId =
    !isGrouped && row.getCanExpand()
      ? row.getVisibleCells().find((cell) => !cell.getIsPlaceholder())?.id
      : undefined

  return (
    <MantineTable.Tr
      aria-expanded={row.getCanExpand() ? row.getIsExpanded() : undefined}
      data-index={virtualRowIndex}
      onClick={onClick}
      onKeyDown={onKeyDown}
      ref={measureElement}
      tabIndex={isGrouped || rowCanClick ? 0 : undefined}
      style={{
        background: isGrouped ? colors.groupedBackground : colors.rowBackground,
        boxSizing: 'border-box',
        cursor: isGrouped || rowCanClick ? 'pointer' : 'default',
        display: 'grid',
        fontWeight: isGrouped ? 600 : undefined,
        gridTemplateColumns,
        minHeight: rowHeight,
        outlineOffset: -2,
        position: 'absolute',
        transform: `translateY(${top}px)`,
        width: '100%',
      }}
    >
      {row.getVisibleCells().map((cell) => {
        const align = getDataTableAlignment(cell.column.columnDef.meta?.align)
        const isGroupedCell = cell.getIsGrouped()
        const isAggregated = cell.getIsAggregated()
        const isPlaceholder = cell.getIsPlaceholder()
        const showExpandIndicator = cell.id === expandIndicatorCellId

        return (
          <MantineTable.Td
            key={cell.id}
            style={{
              alignItems: 'center',
              color:
                isAggregated && !isGroupedCell
                  ? colors.aggregateText
                  : undefined,
              display: 'flex',
              justifyContent: getDataTableJustify(align),
              minWidth: 0,
              textAlign: align,
            }}
          >
            <Text
              component="div"
              fw={isAggregated && !isGroupedCell ? 600 : undefined}
              size="sm"
              truncate
              w="100%"
            >
              {isPlaceholder
                ? renderExpandIndicator(row, showExpandIndicator)
                : renderCellContent({
                    isAggregated,
                    isGroupedCell,
                    showExpandIndicator,
                    row,
                    cell,
                  })}
            </Text>
          </MantineTable.Td>
        )
      })}
      {expandedContent && (
        <MantineTable.Td
          colSpan={row.getVisibleCells().length}
          onClick={(event) => event.stopPropagation()}
          style={{
            borderTop: `1px solid ${colors.subtleBorder}`,
            gridColumn: '1 / -1',
            minWidth: 0,
            padding: theme.spacing.md,
          }}
        >
          {expandedContent}
        </MantineTable.Td>
      )}
    </MantineTable.Tr>
  )
}

function renderCellContent<TData>({
  cell,
  isAggregated,
  isGroupedCell,
  showExpandIndicator,
  row,
}: {
  cell: Cell<TData, unknown>
  isAggregated: boolean
  isGroupedCell: boolean
  showExpandIndicator: boolean
  row: Row<TData>
}) {
  if (isGroupedCell) {
    return (
      <Group gap={6} pl={row.depth * 16} wrap="nowrap">
        {row.getIsExpanded() ? (
          <IconChevronDown size={ICON_SIZE} />
        ) : (
          <IconChevronRight size={ICON_SIZE} />
        )}
        <Text component="span" size="sm" truncate>
          {formatDataTableValue(cell.getValue())} ({row.subRows.length})
        </Text>
      </Group>
    )
  }

  if (isAggregated) {
    const columnDef = cell.column.columnDef
    const aggregatedCell = columnDef.aggregatedCell

    if (aggregatedCell) {
      return flexRender(aggregatedCell, cell.getContext())
    }

    return formatDataTableValue(cell.getValue(), columnDef.meta?.format)
  }

  const content = flexRender(cell.column.columnDef.cell, cell.getContext())

  if (showExpandIndicator) {
    return (
      <Group gap={6} wrap="nowrap">
        {renderExpandIndicator(row, true)}
        <Box
          component="span"
          flex={1}
          miw={0}
          style={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {content}
        </Box>
      </Group>
    )
  }

  return content
}

function renderExpandIndicator<TData>(
  row: Row<TData>,
  showExpandIndicator: boolean,
) {
  if (!showExpandIndicator) return null

  return row.getIsExpanded() ? (
    <IconChevronDown size={ICON_SIZE} />
  ) : (
    <IconChevronRight size={ICON_SIZE} />
  )
}
