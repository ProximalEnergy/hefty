import { MultiSelect } from '@mantine/core'
import { type Column } from '@tanstack/react-table'

import type { RowMetaData } from '../KPIInstanceViewer'

type ProjectTypeFilterProps = {
  column: Column<RowMetaData, unknown>
}

const options = [
  { value: '1', label: 'PV' },
  { value: '2', label: 'BESS' },
  { value: '3', label: 'PV+S' },
]

const ProjectTypeFilter = ({ column }: ProjectTypeFilterProps) => {
  const filterValue = column.getFilterValue() as number[] | undefined
  const selectValue = filterValue?.map((value) => value.toString()) ?? []

  return (
    <MultiSelect
      placeholder="Select..."
      data={options}
      value={selectValue}
      onChange={(values) => {
        column.setFilterValue(
          values.length > 0 ? values.map((value) => Number(value)) : undefined,
        )
      }}
      clearable
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

export default ProjectTypeFilter
