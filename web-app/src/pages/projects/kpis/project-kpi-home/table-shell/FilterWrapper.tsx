// Wrapper component that renders filter components in table header cells.
// Handles alignment and positioning of filter components based on column configuration.
import type { EnrichedKPISummaryTableRow } from '@/pages/projects/kpis/project-kpi-home/ProjectKPIHome'
import { type Column } from '@tanstack/react-table'

type FilterWrapperProps = {
  column: Column<EnrichedKPISummaryTableRow, unknown>
}

const getAlignment = (
  align?: 'left' | 'center' | 'right',
): 'left' | 'center' | 'right' => {
  return align ?? 'left'
}

const FilterWrapper = ({ column }: FilterWrapperProps) => {
  const CustomFilter = column.columnDef.meta?.FilterComponent

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

export default FilterWrapper
