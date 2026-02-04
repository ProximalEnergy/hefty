// Sort indicator icon component that displays a chevron to indicate column sort state.
// Changes color when a column is sorted and handles click events to toggle sorting.
import { IconChevronDown } from '@tabler/icons-react'

type SortChevronProps = {
  isSorted: boolean
  onClick?: () => void
}

const SortChevron = ({ isSorted, onClick }: SortChevronProps) => {
  const color = isSorted
    ? 'var(--mantine-color-blue-5)'
    : 'var(--mantine-color-gray-5)'

  return (
    <IconChevronDown
      size={18}
      strokeWidth={2.5}
      color={color}
      style={{
        cursor: onClick ? 'pointer' : 'default',
      }}
      onClick={onClick}
    />
  )
}

export default SortChevron
