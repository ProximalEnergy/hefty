import {
  ColorSwatch,
  ComboboxItem,
  ComboboxLikeRenderOptionInput,
  Group,
  Text,
} from '@mantine/core'
import { IconUsers } from '@tabler/icons-react'

// Custom renderer for category options
export const renderCategoryOption = (
  input: ComboboxLikeRenderOptionInput<ComboboxItem>,
) => {
  const option = input.option as ComboboxItem & { color_code?: string }
  if (!option.color_code) {
    return null
  }
  return (
    <Group gap="xs" wrap="nowrap">
      <ColorSwatch
        color={option.color_code || '#868e96'}
        size={10}
        radius="xl"
      />
      <Text
        size="sm"
        style={{ flexGrow: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}
      >
        {option.label}
      </Text>
    </Group>
  )
}

export const renderAssigneeOption = (
  input: ComboboxLikeRenderOptionInput<ComboboxItem>,
) => {
  const isTeam = input.option.value.startsWith('team:')
  return (
    <Group gap="xs" wrap="nowrap">
      {isTeam && <IconUsers size={14} />}
      <Text
        size="sm"
        style={{ flexGrow: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}
      >
        {input.option.label}
      </Text>
    </Group>
  )
}
