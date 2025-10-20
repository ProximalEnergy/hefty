import {
  Box,
  Collapse,
  Group,
  Text,
  ThemeIcon,
  Tooltip,
  UnstyledButton,
  rem,
} from '@mantine/core'
import { IconChevronRight } from '@tabler/icons-react'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

import classes from './NavbarLinksGroup.module.css'

interface DropdownLinkProps {
  label: string
  to: string
  underDevelopment: boolean
}

interface LinksGroupProps {
  icon: React.ElementType
  label: string
  initiallyOpened?: boolean
  to?: string
  links?: DropdownLinkProps[]
  underDevelopment?: boolean
  dropdownBehavior?: 'full' | 'arrow-only'
  collapsed: boolean
  onExpandNavbar?: () => void
}

export function LinksGroup({
  icon: Icon,
  label,
  initiallyOpened,
  to,
  links,
  dropdownBehavior = 'full',
  collapsed,
  onExpandNavbar,
}: LinksGroupProps) {
  const hasLinks = Array.isArray(links)
  const location = useLocation()

  const isActive = (path: string) => {
    if (location.pathname.startsWith(path)) {
      const nextChar = location.pathname[path.length]
      // Only return true if this is the most specific match
      // i.e., if there are no more path segments after this one
      return nextChar === undefined
    }
    return false
  }

  // Check if any dropdown items are active
  const hasActiveDropdownItem =
    hasLinks &&
    links?.some((link) => {
      if (typeof link.to === 'string') {
        return isActive(link.to)
      }
      return false
    })

  // Initialize opened state based on initiallyOpened prop or if any dropdown items are active
  const [opened, setOpened] = useState(initiallyOpened || hasActiveDropdownItem)

  const handleMainClick = () => {
    if (collapsed && hasLinks && onExpandNavbar) {
      // If sidebar is collapsed and this item has nested links, expand the sidebar
      onExpandNavbar()
      setOpened(true)
    } else if (dropdownBehavior === 'full') {
      setOpened((o) => !o)
    }
  }

  const handleArrowClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setOpened((o) => !o)
  }

  const items = (hasLinks ? links : []).map((link) => (
    <Link
      to={link.to}
      style={{ textDecoration: 'none' }}
      key={link.label}
      data-active={isActive(link.to)}
    >
      <Text className={classes.link}>{link.label}</Text>
    </Link>
  ))

  const activeState = to ? isActive(to) : false

  const unstyledButton = (
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
          <Box onClick={handleArrowClick}>
            <IconChevronRight
              className={classes.chevron}
              stroke={1.5}
              style={{
                width: rem(16),
                height: rem(16),
                transform: opened ? 'rotate(-90deg)' : 'none',
              }}
            />
          </Box>
        )}
      </Group>
    </UnstyledButton>
  )

  const button = to ? (
    <Link to={to} style={{ textDecoration: 'none' }} data-active={activeState}>
      {unstyledButton}
    </Link>
  ) : (
    unstyledButton
  )

  if (collapsed) {
    const tooltipLabel = hasLinks ? `${label} (click to expand)` : label
    return (
      <Tooltip label={tooltipLabel} position="right" withArrow>
        {button}
      </Tooltip>
    )
  }

  return (
    <>
      {button}
      {hasLinks ? <Collapse in={opened}>{items}</Collapse> : null}
    </>
  )
}
