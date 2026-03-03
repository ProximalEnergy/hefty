// Table shell component for KPI Instance Viewer
import { Table, useComputedColorScheme, useMantineTheme } from '@mantine/core'
import { IconChevronDown } from '@tabler/icons-react'
import {
  type Column,
  type RowData,
  type Table as TanStackTable,
  flexRender,
} from '@tanstack/react-table'
import { type CSSProperties, type ComponentType, Fragment } from 'react'

import type { RowMetaData } from './KPIInstanceViewer'

declare module '@tanstack/react-table' {
  interface ColumnMeta<TData extends RowData, TValue> {
    FilterComponent?: ComponentType<{ column: Column<TData, TValue> }>
    align?: 'left' | 'center' | 'right'
    projectType?: number
  }
}

type TableShellProps = {
  table: TanStackTable<RowMetaData>
}

const getAlignment = (
  align?: 'left' | 'center' | 'right',
): 'left' | 'center' | 'right' => {
  return align ?? 'left'
}

// Sort indicator component
type SortChevronProps = {
  sortState: false | 'asc' | 'desc'
  title: string
  ariaLabel: string
  onClick?: () => void
}

const SortChevron = ({
  sortState,
  title,
  ariaLabel,
  onClick,
}: SortChevronProps) => {
  const isSorted = sortState !== false
  const color = isSorted
    ? 'var(--mantine-color-blue-5)'
    : 'var(--mantine-color-gray-5)'
  const transform = sortState === 'asc' ? 'rotate(180deg)' : 'rotate(0deg)'

  return (
    <IconChevronDown
      size={18}
      strokeWidth={2.5}
      color={color}
      title={title}
      aria-label={ariaLabel}
      style={{
        cursor: onClick ? 'pointer' : 'default',
        opacity: isSorted ? 1 : 0.6,
        transform,
        transition: 'transform 120ms ease',
      }}
      onClick={onClick}
    />
  )
}

// Filter wrapper component
type FilterWrapperProps = {
  column: Column<RowMetaData, unknown>
}

const FilterWrapper = ({ column }: FilterWrapperProps) => {
  const CustomFilter = column.columnDef.meta?.FilterComponent as
    | ComponentType<{ column: Column<RowMetaData, unknown> }>
    | undefined

  if (!column.getCanFilter() || !CustomFilter) return null

  const align = getAlignment(column.columnDef.meta?.align)

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        justifyContent:
          align === 'left'
            ? 'flex-start'
            : align === 'center'
              ? 'center'
              : 'flex-end',
      }}
    >
      <CustomFilter column={column} />
    </div>
  )
}

// Sort toggle handler
const handleSortToggle = (column: Column<RowMetaData, unknown>) => {
  const currentSort = column.getIsSorted()
  if (currentSort === false) {
    column.toggleSorting(false) // false = ascending
  } else if (currentSort === 'asc') {
    column.toggleSorting(true) // true = descending
  } else {
    column.clearSorting()
  }
}

const getSortActionLabel = (sortState: false | 'asc' | 'desc'): string => {
  if (sortState === false) return 'Sort ascending'
  if (sortState === 'asc') return 'Sort descending'
  return 'Clear sorting'
}

const getProjectTypeLabel = (projectType?: number): string | null => {
  if (projectType === 1) return 'PV'
  if (projectType === 2) return 'BESS'
  if (projectType === 3) return 'PV+S'
  return null
}

const TableShell = ({ table }: TableShellProps) => {
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('light')
  const borderColor =
    computedColorScheme === 'dark' ? theme.colors.dark[4] : theme.colors.gray[3]
  const visibleLeafColumns = table.getVisibleLeafColumns()
  const stickyColumnIds = new Set(
    visibleLeafColumns.slice(0, 3).map((column) => column.id),
  )
  const stickyOffsets = visibleLeafColumns
    .slice(0, 3)
    .reduce<Record<string, number>>((acc, column) => {
      const previousTotal = acc.__total__ ?? 0
      acc[column.id] = previousTotal
      acc.__total__ = previousTotal + column.getSize()
      return acc
    }, {})
  const stickyCellStyle = (
    columnId: string,
    isHeader: boolean,
  ): CSSProperties => {
    if (!stickyColumnIds.has(columnId)) return {}
    return {
      position: 'sticky',
      left: stickyOffsets[columnId] ?? 0,
      zIndex: isHeader ? 4 : 1,
      backgroundColor:
        computedColorScheme === 'light'
          ? 'var(--mantine-color-default)'
          : 'var(--mantine-color-body)',
    }
  }

  return (
    <Table striped highlightOnHover withTableBorder stickyHeader>
      <Table.Thead>
        {table.getHeaderGroups().map((headerGroup) => (
          <Fragment key={headerGroup.id}>
            <Table.Tr style={{ borderBottom: 'none' }}>
              {headerGroup.headers.map((header) => {
                const align = getAlignment(header.column.columnDef.meta?.align)
                const explicitSize = header.column.columnDef.size
                const columnWidth =
                  explicitSize !== undefined ? header.getSize() : undefined
                const projectTypeLabel = getProjectTypeLabel(
                  header.column.columnDef.meta?.projectType,
                )
                return (
                  <Table.Th
                    key={header.id}
                    w={columnWidth}
                    style={{
                      width: columnWidth,
                      minWidth: columnWidth,
                      textAlign: align,
                      whiteSpace: 'nowrap',
                      backgroundColor:
                        computedColorScheme === 'light'
                          ? 'var(--mantine-color-default)'
                          : undefined,
                      ...stickyCellStyle(header.column.id, true),
                    }}
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                          justifyContent:
                            align === 'left'
                              ? 'flex-start'
                              : align === 'center'
                                ? 'center'
                                : 'flex-end',
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems:
                              align === 'left'
                                ? 'flex-start'
                                : align === 'center'
                                  ? 'center'
                                  : 'flex-end',
                            lineHeight: 1.2,
                          }}
                        >
                          <div>
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                          </div>
                          {projectTypeLabel && (
                            <div
                              style={{
                                fontSize: '0.75rem',
                                color: 'var(--mantine-color-dimmed)',
                                fontWeight: 500,
                              }}
                            >
                              {projectTypeLabel}
                            </div>
                          )}
                        </div>
                        {header.column.getCanSort() &&
                          (() => {
                            const sortState = header.column.getIsSorted()
                            const sortActionLabel =
                              getSortActionLabel(sortState)
                            return (
                              <SortChevron
                                sortState={sortState}
                                title={sortActionLabel}
                                ariaLabel={sortActionLabel}
                                onClick={() => handleSortToggle(header.column)}
                              />
                            )
                          })()}
                      </div>
                    )}
                  </Table.Th>
                )
              })}
            </Table.Tr>
            <Table.Tr
              style={{
                boxShadow: `0 2px 0 0 ${borderColor}`,
              }}
            >
              {headerGroup.headers.map((header) => {
                const explicitSize = header.column.columnDef.size
                const columnWidth =
                  explicitSize !== undefined ? header.getSize() : undefined
                return (
                  <Table.Th
                    key={`${header.id}-filter`}
                    w={columnWidth}
                    style={{
                      width: columnWidth,
                      minWidth: columnWidth,
                      paddingTop: 0,
                      paddingBottom: theme.spacing.xs,
                      backgroundColor:
                        computedColorScheme === 'light'
                          ? 'var(--mantine-color-default)'
                          : undefined,
                      ...stickyCellStyle(header.column.id, true),
                    }}
                  >
                    <FilterWrapper column={header.column} />
                  </Table.Th>
                )
              })}
            </Table.Tr>
          </Fragment>
        ))}
      </Table.Thead>
      <Table.Tbody>
        {table.getRowModel().rows.map((row) => (
          <Table.Tr key={row.id}>
            {row.getVisibleCells().map((cell) => {
              const align = getAlignment(cell.column.columnDef.meta?.align)
              const explicitSize = cell.column.columnDef.size
              const columnWidth =
                explicitSize !== undefined ? cell.column.getSize() : undefined
              return (
                <Table.Td
                  key={cell.id}
                  style={{
                    width: columnWidth,
                    minWidth: columnWidth,
                    textAlign: align,
                    overflow: 'hidden',
                    ...stickyCellStyle(cell.column.id, false),
                  }}
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </Table.Td>
              )
            })}
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  )
}

export default TableShell
