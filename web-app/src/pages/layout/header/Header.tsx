import { AppShell, Burger, Group } from '@mantine/core'
import { Link } from 'react-router-dom'

import { DataStatusContainer } from './DataStatus'
import Logo from './Logo'
import ProjectDropdown from './ProjectDropdown'
import SpotlightButton from './SpotlightButton'
import ThemeToggle from './ThemeToggle'
import UserAlerts from './UserAlerts'
import UserDropdown from './UserDropdown'

const Header = ({
  opened,
  toggle,
}: {
  opened: boolean
  toggle: React.MouseEventHandler
}) => {
  return (
    <AppShell.Header>
      <Group h="100%" px="md">
        <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
        <Link
          to="/"
          style={{
            height: '100%',
            display: 'flex',
            justifyItems: 'center',
            alignItems: 'center',
            textDecoration: 'none',
            gap: '15px',
            color: 'inherit',
          }}
        >
          <Logo />
        </Link>
        <div style={{ flex: 1 }}></div>
        <DataStatusContainer />
        <ProjectDropdown />
        <UserAlerts />
        <SpotlightButton />
        <ThemeToggle />
        <UserDropdown />
      </Group>
    </AppShell.Header>
  )
}

export default Header
