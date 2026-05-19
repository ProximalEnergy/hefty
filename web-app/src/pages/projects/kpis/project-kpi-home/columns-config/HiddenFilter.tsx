// Filter component for the favorites column that allows users to toggle between showing all KPIs
// or only favorited KPIs. Displays a heart icon that changes opacity based on filter state.
import type { EnrichedKPISummaryTableRow } from '@/pages/projects/kpis/project-kpi-home/ProjectKPIHome'
import { Tooltip } from '@mantine/core'
import { IconEyeOff } from '@tabler/icons-react'
import { type Column } from '@tanstack/react-table'

type HiddenFilterProps = {
  column: Column<EnrichedKPISummaryTableRow, unknown>
}

const HiddenFilter = ({ column }: HiddenFilterProps) => {
  // Decode: Convert filter to hiddenOn
  const filterValue = column.getFilterValue() as boolean | undefined
  const hiddenOn = filterValue === false ? false : true

  const encodeFilter = (hiddenOn: boolean): boolean | undefined => {
    return hiddenOn ? undefined : false
  }

  // Opacity values
  const OPACITY_ON = 1
  const OPACITY_OFF = 0.4

  // Toggle function
  const toggleHidden = () => {
    column.setFilterValue(encodeFilter(!hiddenOn))
  }

  return (
    <Tooltip label="Show hidden">
      <div
        onClick={toggleHidden}
        style={{
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        onMouseEnter={(e) => {
          const icon = e.currentTarget.querySelector('svg')
          if (icon) icon.style.opacity = OPACITY_ON.toString()
        }}
        onMouseLeave={(e) => {
          const icon = e.currentTarget.querySelector('svg')
          if (icon)
            icon.style.opacity = (
              hiddenOn ? OPACITY_ON : OPACITY_OFF
            ).toString()
        }}
      >
        <IconEyeOff
          size={14}
          style={{
            opacity: hiddenOn ? OPACITY_ON : OPACITY_OFF,
          }}
        />
      </div>
    </Tooltip>
  )
}

export default HiddenFilter
