// Table header component that renders column headers with sorting controls and filter rows.
// Manages the two-row header structure: one row for headers/sort indicators, one row for filters.
import { Table, useComputedColorScheme, useMantineTheme } from '@mantine/core'
import {
  type Column,
  type Table as TanStackTable,
  flexRender,
} from '@tanstack/react-table'
import { Fragment } from 'react'

import type { EnrichedKPISummaryTableRow } from '../ProjectKPIHome'
import FilterWrapper from './FilterWrapper'
import SortChevron from './SortChevron'

type RenderTableHeaderProps = {
  table: TanStackTable<EnrichedKPISummaryTableRow>
}

const getAlignment = (
  align?: 'left' | 'center' | 'right',
): 'left' | 'center' | 'right' => {
  return align ?? 'left'
}

const handleSortToggle = (
  column: Column<EnrichedKPISummaryTableRow, unknown>,
) => {
  const currentSort = column.getIsSorted()
  if (currentSort === false) {
    column.toggleSorting(false) // false = ascending
  } else {
    column.clearSorting()
  }
}

const RenderTableHeader = ({ table }: RenderTableHeaderProps) => {
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('light')
  const borderColor =
    computedColorScheme === 'dark' ? theme.colors.dark[4] : theme.colors.gray[3]

  return (
    <Table.Thead>
      {table.getHeaderGroups().map((headerGroup) => (
        <Fragment key={headerGroup.id}>
          <Table.Tr style={{ borderBottom: 'none' }}>
            {headerGroup.headers.map((header) => {
              const align = getAlignment(header.column.columnDef.meta?.align)
              const explicitSize = header.column.columnDef.size
              return (
                <Table.Th
                  key={header.id}
                  w={explicitSize !== undefined ? header.getSize() : undefined}
                  style={{
                    textAlign: align,
                    whiteSpace: 'nowrap',
                    backgroundColor: 'transparent',
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
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                      {header.column.getCanSort() && (
                        <SortChevron
                          isSorted={header.column.getIsSorted() !== false}
                          onClick={() => handleSortToggle(header.column)}
                        />
                      )}
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
              return (
                <Table.Th
                  key={`${header.id}-filter`}
                  style={{
                    paddingTop: 0,
                    paddingBottom: theme.spacing.xs,
                    backgroundColor: 'transparent',
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
  )
}

export default RenderTableHeader
