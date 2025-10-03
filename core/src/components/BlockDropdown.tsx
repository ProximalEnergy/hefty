import { useGetBlockDropdown } from '@/api/ui'
import { Button, ButtonProps, Select, SelectProps } from '@mantine/core'
import {
  IconChevronLeft,
  IconChevronRight,
  IconChevronsLeft,
  IconChevronsRight,
} from '@tabler/icons-react'

// NOTE: For some reason I was not able to get the types to behave when I used the SelectProps for onChange. The Mantine type for onChange wanted a ComboboxItem in addition to the value. See https://mantine.dev/core/select/#onchange-handler for more details.
interface BlockDropdownProps {
  data: ReturnType<typeof useGetBlockDropdown>['data']
  value: SelectProps['value']
  onChange: (value: string | null) => void
  includeNextPrevious?: boolean
  includeFirstLast?: boolean
  size?: ButtonProps['size']
  buttonVariant?: ButtonProps['variant']
  buttonPx?: ButtonProps['px']
}

/**
 * A dropdown for selecting a block. Note that data is passed in as a prop so that parent components can handle fetching, loading, and other logic.
 *
 * @param data - The data returned from the useGetBlockDropdown hook.
 * @param value - The value of the dropdown.
 * @param onChange - The callback function when the value changes.
 * @param includeNextPrevious - Whether to include the next and previous block button.
 * @param includeFirstLast - Whether to include the first and last block buttons.
 * @param size - The size of the elements.
 * @param buttonVariant - The variant of the buttons.
 * @param buttonPx - The horizontal padding of the buttons.
 */
const BlockDropdown = ({
  data,
  value,
  onChange,
  includeNextPrevious = true,
  includeFirstLast = true,
  size = 'sm',
  buttonVariant = 'default',
  buttonPx = 0,
}: BlockDropdownProps) => {
  const currentIndex =
    data?.findIndex((item) => item.device_id.toString() === value) ?? -1

  const handleNavigate = (direction: 'first' | 'last' | 'prev' | 'next') => {
    if (!data?.length) return

    let newIndex
    switch (direction) {
      case 'first':
        newIndex = 0
        break
      case 'last':
        newIndex = data.length - 1
        break
      case 'prev':
        newIndex = currentIndex <= 0 ? data.length - 1 : currentIndex - 1
        break
      case 'next':
        newIndex = currentIndex >= data.length - 1 ? 0 : currentIndex + 1
        break
    }

    const newBlockId = data?.[newIndex]?.device_id.toString()
    onChange?.(newBlockId)
  }

  const isFirstBlock = currentIndex === 0
  const isLastBlock = currentIndex === (data?.length ?? 0) - 1

  return (
    <Button.Group>
      {includeFirstLast && (
        <Button
          size={size}
          variant={buttonVariant}
          px={buttonPx}
          onClick={() => handleNavigate('first')}
          disabled={!data?.length || isFirstBlock}
        >
          <IconChevronsLeft />
        </Button>
      )}
      {includeNextPrevious && (
        <Button
          size={size}
          variant={buttonVariant}
          px={buttonPx}
          onClick={() => handleNavigate('prev')}
          disabled={!data?.length || isFirstBlock}
        >
          <IconChevronLeft />
        </Button>
      )}

      <Select
        placeholder="Select a block"
        value={value}
        onChange={onChange}
        data={
          data?.map((item) => ({
            value: item.device_id.toString(),
            label: item.name_full,
          })) || []
        }
        comboboxProps={{ zIndex: 1000 }}
        searchable
        radius={includeNextPrevious || includeFirstLast ? 0 : undefined}
        size={size}
      />

      {includeNextPrevious && (
        <Button
          size={size}
          variant={buttonVariant}
          px={buttonPx}
          onClick={() => handleNavigate('next')}
          disabled={!data?.length || isLastBlock}
        >
          <IconChevronRight />
        </Button>
      )}
      {includeFirstLast && (
        <Button
          size={size}
          variant={buttonVariant}
          px={buttonPx}
          onClick={() => handleNavigate('last')}
          disabled={!data?.length || isLastBlock}
        >
          <IconChevronsRight />
        </Button>
      )}
    </Button.Group>
  )
}

export default BlockDropdown
