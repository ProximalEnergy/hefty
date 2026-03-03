// Text input filter component for filtering table columns
import { TextInput } from '@mantine/core'
import { type Column } from '@tanstack/react-table'

import type { RowMetaData } from '../KPIInstanceViewer'

type TextFilterProps = {
  column: Column<RowMetaData, unknown>
}

const TextFilter = ({ column }: TextFilterProps) => (
  <TextInput
    placeholder="Filter..."
    value={(column.getFilterValue() as string) ?? ''}
    onChange={(e) => column.setFilterValue(e.target.value)}
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

export default TextFilter
