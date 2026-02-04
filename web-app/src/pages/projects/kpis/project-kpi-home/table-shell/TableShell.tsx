import { Table, Text } from '@mantine/core'
import {
  type Column,
  type RowData,
  type Table as TanStackTable,
  flexRender,
} from '@tanstack/react-table'
import { type ComponentType } from 'react'

import type { EnrichedKPISummaryTableRow } from '../ProjectKPIHome'
import RenderTableHeader from './RenderTableHeader'

//
// This file is in charge of the mantine table styling of the tanstack
// table. It renders the sub-components provided to it while
// providing consistent table-level styling.
// Table shell components should be defined in this directory.
//

// ============================================================================
// Type Declarations
// ============================================================================

declare module '@tanstack/react-table' {
  interface ColumnMeta<TData extends RowData, TValue> {
    FilterComponent?: ComponentType<{ column: Column<TData, TValue> }>
    align?: 'left' | 'center' | 'right'
    deviceTypes?: Record<number, string>
  }
}

// ============================================================================
// Helper Components & Utilities
// ============================================================================

const getAlignment = (
  align?: 'left' | 'center' | 'right',
): 'left' | 'center' | 'right' => {
  return align ?? 'left'
}

// ============================================================================
// Table Rendering Functions
// ============================================================================

export const renderTableHeader = (
  table: TanStackTable<EnrichedKPISummaryTableRow>,
) => <RenderTableHeader table={table} />

export const renderSkeletonBody = (
  table: TanStackTable<EnrichedKPISummaryTableRow>,
) => {
  const visibleColumns = table.getVisibleLeafColumns()
  const skeletonRowCount = 5

  return (
    <Table.Tbody>
      {Array.from({ length: skeletonRowCount }).map((_, rowIndex) => (
        <Table.Tr key={`skeleton-${rowIndex}`}>
          {visibleColumns.map((column) => {
            const align = getAlignment(column.columnDef.meta?.align)
            const columnSize = column.getSize()
            // Calculate line length proportional to column size (approximately 8px per character)
            const lineLength = Math.max(1, Math.floor(columnSize / 20))
            const skeletonLine = '━'.repeat(lineLength)
            return (
              <Table.Td key={column.id} style={{ textAlign: align }}>
                <Text size="sm" c="dimmed" style={{ opacity: 0.5 }}>
                  {skeletonLine}
                </Text>
              </Table.Td>
            )
          })}
        </Table.Tr>
      ))}
    </Table.Tbody>
  )
}

export const renderTableBody = (
  table: TanStackTable<EnrichedKPISummaryTableRow>,
) => (
  <Table.Tbody>
    {table.getRowModel().rows.map((row) => (
      <Table.Tr key={row.id}>
        {row.getVisibleCells().map((cell) => {
          const align = getAlignment(cell.column.columnDef.meta?.align)
          return (
            <Table.Td
              key={cell.id}
              style={{
                textAlign: align,
                overflow: 'hidden',
              }}
            >
              {flexRender(cell.column.columnDef.cell, cell.getContext())}
            </Table.Td>
          )
        })}
      </Table.Tr>
    ))}
  </Table.Tbody>
)
