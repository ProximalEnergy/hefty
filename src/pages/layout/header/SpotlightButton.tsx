import { ActionIcon, Tooltip } from '@mantine/core'
import { useOs } from '@mantine/hooks'
import { spotlight } from '@mantine/spotlight'
import { IconSearch } from '@tabler/icons-react'

const SpotlightButton = () => {
  // Detect if the user is on macOS
  const isMac = useOs() == 'macos'

  const shortcutText = isMac ? '⌘+K' : 'Ctrl+K'

  return (
    <Tooltip label={`Search (${shortcutText})`} position="bottom" withArrow>
      <ActionIcon
        variant="default"
        size="lg"
        onClick={spotlight.open}
        aria-label={`Open search (${shortcutText})`}
      >
        <IconSearch size={18} stroke={1.5} />
      </ActionIcon>
    </Tooltip>
  )
}

export default SpotlightButton
