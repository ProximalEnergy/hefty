import { searchActions } from '@/components/Spotlight.search.store'
import classes from '@/pages/layout/header/ThemeToggle.module.css'
import { ActionIcon, Tooltip } from '@mantine/core'
import { useOs } from '@mantine/hooks'
import { IconSearch } from '@tabler/icons-react'
import cx from 'clsx'

const SpotlightButton = () => {
  // Detect if the user is on macOS
  const isMac = useOs() == 'macos'

  const shortcutText = isMac ? '⌘+K' : 'Ctrl+K'

  return (
    <Tooltip label={`Search (${shortcutText})`} position="bottom" withArrow>
      <ActionIcon
        variant="default"
        size="lg"
        onClick={searchActions.open}
        aria-label={`Open search (${shortcutText})`}
      >
        <IconSearch className={cx(classes.icon)} stroke={1.5} />
      </ActionIcon>
    </Tooltip>
  )
}

export default SpotlightButton
