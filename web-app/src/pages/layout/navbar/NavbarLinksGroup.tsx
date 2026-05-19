import classes from '@/pages/layout/navbar/NavbarLinksGroup.module.css'
import { isPathActive } from '@/pages/layout/navbar/isPathActive'
import {
  Box,
  Group,
  Menu,
  ThemeIcon,
  Tooltip,
  UnstyledButton,
  rem,
} from '@mantine/core'
import { IconChevronRight } from '@tabler/icons-react'
import { Link, useLocation } from 'react-router'

interface DropdownLinkProps {
  label: string
  to: string
  underDevelopment: boolean
  tooltip?: string
}

interface LinksGroupProps {
  icon: React.ElementType
  label: string
  to?: string
  links?: DropdownLinkProps[]
  underDevelopment?: boolean
  collapsed: boolean
  onExpandNavbar?: () => void
}

export function LinksGroup({
  icon: Icon,
  label,
  to,
  links,
  collapsed,
  onExpandNavbar,
}: LinksGroupProps) {
  const hasLinks = Array.isArray(links)
  const location = useLocation()

  const handleMainClick = () => {
    if (collapsed && hasLinks && onExpandNavbar) {
      // If sidebar is collapsed and this item has nested links, expand the sidebar
      onExpandNavbar()
    }
  }

  const menuItems = hasLinks
    ? links?.map((link) => (
        <Tooltip
          key={link.label}
          label={link.tooltip || ''}
          disabled={!link.tooltip}
          withArrow
          position="right"
        >
          <Menu.Item
            component={Link}
            to={link.to}
            data-active={isPathActive(location.pathname, link.to)}
          >
            {link.label}
          </Menu.Item>
        </Tooltip>
      ))
    : []

  const activeState = to ? isPathActive(location.pathname, to) : false

  const buttonContent = (
    <UnstyledButton onClick={handleMainClick} className={classes.control}>
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
            <Icon style={{ width: rem(18), height: rem(18) }} />
          </ThemeIcon>
          {!collapsed && <Box ml="md">{label}</Box>}
        </Box>
        {hasLinks && !collapsed && (
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
    </UnstyledButton>
  )

  const menuTarget = to ? (
    <Link
      to={to}
      style={{ textDecoration: 'none', color: 'inherit' }}
      data-active={activeState}
    >
      {buttonContent}
    </Link>
  ) : (
    buttonContent
  )

  if (collapsed) {
    const tooltipLabel = hasLinks ? `${label} (click to expand)` : label
    if (hasLinks) {
      return (
        <Tooltip label={tooltipLabel} position="right" withArrow>
          <Menu
            trigger="click-hover"
            position="right-start"
            openDelay={0}
            closeDelay={100}
            offset={0}
            zIndex={10000}
          >
            <Menu.Target>{buttonContent}</Menu.Target>
            <Menu.Dropdown>{menuItems}</Menu.Dropdown>
          </Menu>
        </Tooltip>
      )
    }
    return (
      <Tooltip label={tooltipLabel} position="right" withArrow>
        {menuTarget}
      </Tooltip>
    )
  }

  if (hasLinks) {
    return (
      <Menu
        trigger="hover"
        position="right-start"
        openDelay={0}
        closeDelay={100}
        offset={0}
        zIndex={10000}
      >
        <Menu.Target>{menuTarget}</Menu.Target>
        <Menu.Dropdown>{menuItems}</Menu.Dropdown>
      </Menu>
    )
  }

  return <>{menuTarget}</>
}
