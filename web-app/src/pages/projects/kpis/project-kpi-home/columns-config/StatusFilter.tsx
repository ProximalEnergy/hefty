// Filter component for status columns that allows users to filter by KPI status (normal, warning, critical).
// Displays colored dots for each status type and a clear button when filters are active.
import type { EnrichedKPISummaryTableRow } from '@/pages/projects/kpis/project-kpi-home/ProjectKPIHome'
import { Tooltip } from '@mantine/core'
import { IconX } from '@tabler/icons-react'
import { type Column } from '@tanstack/react-table'

type StatusFilterProps = {
  column: Column<EnrichedKPISummaryTableRow, unknown>
}

const StatusFilter = ({ column }: StatusFilterProps) => {
  // Decode: Convert [show0, show1, show2] to [redButtonOn, orangeButtonOn]
  const filterValue = column.getFilterValue() as
    | [boolean, boolean, boolean]
    | undefined
  const [show0, show1, show2] = filterValue ?? [true, true, true]
  const showAll = show0 && show1 && show2
  const redButtonOn = show2 && !showAll
  const orangeButtonOn = show1 && !showAll

  // Encode: Convert [redButtonOn, orangeButtonOn] back to [show0, show1, show2]
  const encodeFilter = (
    redOn: boolean,
    orangeOn: boolean,
  ): [boolean, boolean, boolean] => {
    const show0 = !(redOn || orangeOn)
    const show1 = show0 || orangeOn
    const show2 = show0 || redOn
    return [show0, show1, show2]
  }

  // Color constants - same color for all cases, use opacity for on/off
  const RED_COLOR = 'var(--mantine-color-red-6)'
  const RED_BORDER = 'var(--mantine-color-red-8)'
  const ORANGE_COLOR = 'var(--mantine-color-orange-4)'
  const ORANGE_BORDER = 'var(--mantine-color-orange-6)'
  const GRAY_COLOR = 'var(--mantine-color-gray-5)'

  // Opacity values
  const OPACITY_ON = 1
  const OPACITY_OFF = 0.4

  // Toggle functions
  const toggleRed = () => {
    column.setFilterValue(encodeFilter(!redButtonOn, orangeButtonOn))
  }

  const toggleOrange = () => {
    column.setFilterValue(encodeFilter(redButtonOn, !orangeButtonOn))
  }

  const clearFilter = () => {
    column.setFilterValue(encodeFilter(false, false))
  }

  // Dot component helper
  const createDot = (
    isOn: boolean,
    color: string,
    borderColor: string,
    onClick: () => void,
    tooltip: string,
  ) => (
    <Tooltip label={tooltip}>
      <div
        onClick={onClick}
        style={{
          width: 12,
          height: 12,
          borderRadius: '50%',
          backgroundColor: color,
          opacity: isOn ? OPACITY_ON : OPACITY_OFF,
          cursor: 'pointer',
          border: isOn ? `2px solid ${borderColor}` : '2px solid transparent',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.opacity = OPACITY_ON.toString()
          e.currentTarget.style.border = `2px solid ${borderColor}`
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.opacity = (
            isOn ? OPACITY_ON : OPACITY_OFF
          ).toString()
          e.currentTarget.style.border = isOn
            ? `2px solid ${borderColor}`
            : '2px solid transparent'
        }}
      />
    </Tooltip>
  )

  const hasActiveFilter = redButtonOn || orangeButtonOn

  return (
    <>
      {createDot(redButtonOn, RED_COLOR, RED_BORDER, toggleRed, 'Critical')}
      {createDot(
        orangeButtonOn,
        ORANGE_COLOR,
        ORANGE_BORDER,
        toggleOrange,
        'Warning',
      )}
      {hasActiveFilter ? (
        <Tooltip label="Clear filter">
          <div
            onClick={clearFilter}
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
              if (icon) icon.style.opacity = OPACITY_OFF.toString()
            }}
          >
            <IconX
              size={14}
              strokeWidth={2.5}
              style={{ color: GRAY_COLOR, opacity: OPACITY_OFF }}
            />
          </div>
        </Tooltip>
      ) : (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <IconX
            size={14}
            strokeWidth={2.5}
            style={{ color: GRAY_COLOR, opacity: OPACITY_OFF }}
          />
        </div>
      )}
    </>
  )
}

export default StatusFilter
