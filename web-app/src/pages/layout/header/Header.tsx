import Logo from '@/pages/layout/header/Logo'
import ProjectDropdown from '@/pages/layout/header/ProjectDropdown'
import { ProjectStatusIcons } from '@/pages/layout/header/ProjectStatusIcons'
import SpotlightButton from '@/pages/layout/header/SpotlightButton'
import ThemeToggle from '@/pages/layout/header/ThemeToggle'
import UserAlerts from '@/pages/layout/header/UserAlerts'
import UserDropdown from '@/pages/layout/header/UserDropdown'
import { AppShell, Burger, Group } from '@mantine/core'
import { Link } from 'react-router'

const AppLayoutHeader = ({
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
        <ProjectStatusIcons />
        <ProjectDropdown />
        <UserAlerts />
        <SpotlightButton />
        <ThemeToggle />
        <UserDropdown />
      </Group>
    </AppShell.Header>
  )
}

export default AppLayoutHeader
