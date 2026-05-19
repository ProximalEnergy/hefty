// Text input filter component for searching and filtering KPI metrics by name.
// Provides a simple text field that filters table rows as the user types.
import type { EnrichedKPISummaryTableRow } from '@/pages/projects/kpis/project-kpi-home/ProjectKPIHome'
import { TextInput } from '@mantine/core'
import { type Column } from '@tanstack/react-table'

type TextFilterProps = {
  column: Column<EnrichedKPISummaryTableRow, unknown>
}

const TextFilter = ({ column }: TextFilterProps) => (
  <TextInput
    placeholder=" Filter metrics..."
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
