import {
  useGetSharedUserDashboards,
  useGetUserDashboards,
} from '@/api/v1/operational/project/custom_dash'
import { Box, Group, Menu, Text, ThemeIcon, Tooltip, rem } from '@mantine/core'
import { IconChevronRight, IconHome, IconSettings } from '@tabler/icons-react'
import { useState } from 'react'
import { Link, useLocation, useParams } from 'react-router'

import classes from './NavbarLinksGroup.module.css'

export function HomeLinkWithDashboards({ collapsed }: { collapsed: boolean }) {
  const { projectId } = useParams<{ projectId: string }>()
  const location = useLocation()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isMouseOnDropdown, setIsMouseOnDropdown] = useState(false)

  const userDashboards = useGetUserDashboards({
    pathParams: {
      projectId: projectId || '',
    },
    queryOptions: {
      enabled: !!projectId, // Fetch dashboards when projectId is available
    },
  })
  const sharedUserDashboards = useGetSharedUserDashboards({
    pathParams: {
      projectId: projectId || '',
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })
  const allDashboards = [
    ...(userDashboards.data || []),
    ...(sharedUserDashboards.data || []),
  ]

  const isActive = (path: string) => {
    if (location.pathname.startsWith(path)) {
      const nextChar = location.pathname[path.length]
      return nextChar === undefined
    }
    return false
  }

  const activeState = projectId ? isActive(`/projects/${projectId}`) : false

  if (!projectId) {
    // If no projectId, render a simple home link without dashboard functionality
    const homePath = '/portfolio'
    const activeState = isActive('/portfolio')

    const button = (
      <Link
        to={homePath}
        style={{ textDecoration: 'none' }}
        data-active={activeState}
      >
        <Box className={classes.control}>
          <Group
            justify={collapsed ? 'center' : 'space-between'}
            gap={0}
            pl={collapsed ? 0 : 'md'}
            pr={collapsed ? 0 : 'md'}
          >
            <Box
              style={{ display: 'flex', alignItems: 'center' }}
              p={collapsed ? 5 : 5}
            >
              <ThemeIcon variant="light" size={30}>
                <IconHome style={{ width: rem(18), height: rem(18) }} />
              </ThemeIcon>
              {!collapsed && <Box ml="md">Home</Box>}
            </Box>
          </Group>
        </Box>
      </Link>
    )

    if (collapsed) {
      return (
        <Tooltip label="Home" position="right" withArrow>
          {button}
        </Tooltip>
      )
    }

    return button
  }

  const homePath = `/projects/${projectId}`
  const customDashboardsPath = `/projects/${projectId}/custom-dash`

  const shouldHighlightDefault = isMenuOpen && !isMouseOnDropdown

  const menuItems =
    userDashboards.isLoading || sharedUserDashboards.isLoading
      ? [
          <Menu.Item key="loading" disabled>
            <Text c="dimmed" size="sm">
              Loading...
            </Text>
          </Menu.Item>,
        ]
      : [
          <Menu.Item
            key="home-default"
            component={Link}
            to={homePath}
            data-active={activeState}
            data-highlight-default={shouldHighlightDefault}
          >
            Home (default)
          </Menu.Item>,
          ...(allDashboards && allDashboards.length > 0
            ? allDashboards
                .sort((a, b) =>
                  a.dashboard_name.localeCompare(b.dashboard_name),
                )
                .map((dashboard) => (
                  <Menu.Item
                    key={dashboard.dashboard_id}
                    component={Link}
                    to={`/projects/${projectId}/custom-dash/${dashboard.dashboard_id}`}
                    data-active={isActive(
                      `/projects/${projectId}/custom-dash/${dashboard.dashboard_id}`,
                    )}
                  >
                    {dashboard.dashboard_name}
                  </Menu.Item>
                ))
            : []),
          <Menu.Item
            key="custom-dashboards"
            component={Link}
            to={customDashboardsPath}
            leftSection={<IconSettings size={14} />}
            data-active={isActive(customDashboardsPath)}
          >
            Manage Dashboards
          </Menu.Item>,
        ]

  const buttonContent = (
    <Box className={classes.control}>
      <Group
        justify={collapsed ? 'center' : 'space-between'}
        gap={0}
        pl={collapsed ? 0 : 'md'}
        pr={collapsed ? 0 : 'md'}
      >
        <Box
          style={{ display: 'flex', alignItems: 'center' }}
          p={collapsed ? 5 : 5}
        >
          <ThemeIcon variant="light" size={30}>
            <IconHome style={{ width: rem(18), height: rem(18) }} />
          </ThemeIcon>
          {!collapsed && <Box ml="md">Home</Box>}
        </Box>
        {!collapsed && (
          <IconChevronRight
            className={classes.chevron}
            stroke={1.5}
            style={{
              width: rem(16),
              height: rem(16),
            }}
          />
        )}
      </Group>
    </Box>
  )

  const homeLink = (
    <Link
      to={homePath}
      style={{ textDecoration: 'none' }}
      data-active={activeState}
    >
      {buttonContent}
    </Link>
  )

  if (collapsed) {
    return (
      <Tooltip label="Home" position="right" withArrow>
        <Menu
          trigger="click-hover"
          position="right-start"
          openDelay={0}
          closeDelay={0}
          transitionProps={{ duration: 0 }}
          offset={0}
          zIndex={10000}
          opened={isMenuOpen}
          onChange={(opened) => {
            setIsMenuOpen(opened)
            if (!opened) {
              setIsMouseOnDropdown(false)
            }
          }}
        >
          <Menu.Target>{homeLink}</Menu.Target>
          <Menu.Dropdown
            onMouseEnter={() => setIsMouseOnDropdown(true)}
            onMouseLeave={() => setIsMouseOnDropdown(false)}
          >
            {menuItems}
          </Menu.Dropdown>
        </Menu>
      </Tooltip>
    )
  }

  return (
    <Menu
      trigger="hover"
      position="right-start"
      openDelay={0}
      closeDelay={0}
      transitionProps={{ duration: 0 }}
      offset={0}
      zIndex={10000}
      opened={isMenuOpen}
      onChange={(opened) => {
        setIsMenuOpen(opened)
        if (!opened) {
          setIsMouseOnDropdown(false)
        }
      }}
    >
      <Menu.Target>{homeLink}</Menu.Target>
      <Menu.Dropdown
        onMouseEnter={() => setIsMouseOnDropdown(true)}
        onMouseLeave={() => setIsMouseOnDropdown(false)}
      >
        {menuItems}
      </Menu.Dropdown>
    </Menu>
  )
}
