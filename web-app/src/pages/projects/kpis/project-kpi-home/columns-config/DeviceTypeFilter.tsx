// Device type filter component for filtering KPI metrics by device type.
// Provides a select dropdown that filters table rows by device type.
import { Select } from '@mantine/core'
import { type Column } from '@tanstack/react-table'

import type { EnrichedKPISummaryTableRow } from '../ProjectKPIHome'

type DeviceTypeFilterProps = {
  column: Column<EnrichedKPISummaryTableRow, unknown>
}

const DeviceTypeFilter = ({ column }: DeviceTypeFilterProps) => {
  // Get device types from column meta
  const deviceTypes =
    (
      column.columnDef.meta as {
        deviceTypes?: Record<number, string>
      }
    )?.deviceTypes || {}

  const filterValue = column.getFilterValue() as number | undefined
  const selectValue = filterValue?.toString() ?? null

  // Convert to options array: use ID as value, name as label, sort by name
  const options = Object.entries(deviceTypes)
    .map(([id, name]) => ({
      value: id,
      label: name,
    }))
    .sort((a, b) => a.label.localeCompare(b.label))

  return (
    <Select
      placeholder="Filter device"
      data={options}
      value={selectValue}
      onChange={(value) => {
        column.setFilterValue(value ? Number(value) : undefined)
      }}
      clearable
      searchable
      size="sm"
      variant="unstyled"
      styles={{
        input: {
          backgroundColor: 'transparent',
          paddingLeft: 5,
          paddingRight: 5,
          fontWeight: 'normal',
          border: 'none',
          borderBottom: '1px solid var(--mantine-color-gray-4)',
          borderRadius: 0,
        },
      }}
    />
  )
}

export default DeviceTypeFilter
