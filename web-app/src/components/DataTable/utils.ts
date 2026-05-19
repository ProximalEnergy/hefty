import type {
  DataTableAlign,
  DataTableFormat,
} from '@/components/DataTable/types'
import type { Row } from '@tanstack/react-table'

export const getDataTableAlignment = (align?: DataTableAlign): DataTableAlign =>
  align ?? 'left'

export const getDataTableJustify = (align?: DataTableAlign) => {
  if (align === 'right') return 'flex-end'
  if (align === 'center') return 'center'
  return 'flex-start'
}

export const formatDataTableValue = (
  value: unknown,
  format?: DataTableFormat,
) => {
  if (value == null || value === '') return ''

  if (format === 'currency' && typeof value === 'number') {
    return new Intl.NumberFormat('en-US', {
      currency: 'USD',
      maximumFractionDigits: 0,
      style: 'currency',
    }).format(value)
  }

  if (format === 'percent' && typeof value === 'number') {
    return `${value.toFixed(1)}%`
  }

  if (format === 'decimal' && typeof value === 'number') {
    return value.toFixed(2)
  }

  if (format === 'count' && typeof value === 'number') {
    return new Intl.NumberFormat('en-US').format(value)
  }

  if (format === 'duration' && typeof value === 'number') {
    return `${new Intl.NumberFormat('en-US').format(value)} min`
  }

  if (format === 'datetime') {
    const date = value instanceof Date ? value : new Date(String(value))
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
  }

  return String(value)
}

const compareTableValues = (left: unknown, right: unknown) => {
  if (left == null && right == null) return 0
  if (left == null) return 1
  if (right == null) return -1

  if (typeof left === 'number' && typeof right === 'number') {
    return left - right
  }

  return String(left).localeCompare(String(right), undefined, {
    numeric: true,
    sensitivity: 'base',
  })
}

const sortVisibleSiblingChunks = <TData>(
  rows: Row<TData>[],
  columnId: string,
  desc: boolean,
  depth: number,
): Row<TData>[] => {
  const chunks: Row<TData>[][] = []
  let currentChunk: Row<TData>[] = []

  rows.forEach((row) => {
    if (row.depth === depth) {
      if (currentChunk.length > 0) {
        chunks.push(currentChunk)
      }
      currentChunk = [row]
      return
    }

    if (currentChunk.length > 0) {
      currentChunk.push(row)
    }
  })

  if (currentChunk.length > 0) {
    chunks.push(currentChunk)
  }

  chunks.sort((left, right) => {
    const leftValue = left[0]?.getValue(columnId)
    const rightValue = right[0]?.getValue(columnId)

    if (leftValue == null && rightValue == null) return 0
    if (leftValue == null) return 1
    if (rightValue == null) return -1

    const result = compareTableValues(leftValue, rightValue)
    return desc ? -result : result
  })

  return chunks.flatMap((chunk) => {
    const [parent, ...children] = chunk

    if (!parent) return []
    if (children.length === 0) return [parent]

    return [
      parent,
      ...sortVisibleSiblingChunks(children, columnId, desc, depth + 1),
    ]
  })
}

export const sortGroupedVisibleRows = <TData>(
  rows: Row<TData>[],
  activeSortId: string | undefined,
  activeSortDesc: boolean | undefined,
) => {
  const hasGroupedRows = rows.some((row) => row.getIsGrouped())

  if (!activeSortId || !hasGroupedRows) {
    return rows
  }

  return sortVisibleSiblingChunks(
    rows,
    activeSortId,
    activeSortDesc ?? false,
    rows[0]?.depth ?? 0,
  )
}
