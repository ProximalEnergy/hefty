import type { RowData } from '@tanstack/react-table'
import type { ReactNode } from 'react'

export type DataTableAlign = 'left' | 'right' | 'center'

export type DataTableFormat =
  | 'currency'
  | 'duration'
  | 'count'
  | 'severity'
  | 'datetime'
  | 'percent'
  | 'decimal'

declare module '@tanstack/react-table' {
  interface ColumnMeta<TData extends RowData, TValue> {
    /** Format hint used by both leaf and aggregated cells. */
    format?: DataTableFormat
    /** Cell text alignment. */
    align?: DataTableAlign
    /** Optional tooltip content for the header. */
    headerTooltip?: ReactNode
  }
}
