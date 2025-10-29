import { ChatCard, IStep } from '@/components/ChatCard'
import { ProjectSpotlight, SpotlightSearch } from '@/components/Spotlight'
import useVersionChecker from '@/hooks/versionChecker'
import {
  ActionIcon,
  Affix,
  AppShell,
  Button,
  Modal,
  Popover,
  Text,
  useMantineTheme,
} from '@mantine/core'
import { useDisclosure, useMediaQuery } from '@mantine/hooks'
import {
  IconChevronLeft,
  IconChevronRight,
  IconMessageChatbot,
} from '@tabler/icons-react'
import React, { useEffect, useState } from 'react'
import { Outlet, useLocation, useParams } from 'react-router'

import Header from './header/Header'
import { NavbarNested } from './navbar/NavbarNested'

const Demo = ({
  messages,
  setMessages,
  firstQuestionAsked,
  setFirstQuestionAsked,
}: {
  messages: IStep[]
  setMessages: React.Dispatch<React.SetStateAction<IStep[]>>
  firstQuestionAsked: boolean
  setFirstQuestionAsked: React.Dispatch<React.SetStateAction<boolean>>
}) => {
  const theme = useMantineTheme()

  return (
    // Note: Mantine LoadingOverlay has a zIndex of 400 by default
    <Affix position={{ bottom: 10, right: 20 }} zIndex={500}>
      <Popover
        trapFocus
        position="top-end"
        arrowPosition="center"
        withArrow
        shadow="md"
      >
        <Popover.Target>
          <ActionIcon
            color={theme.primaryColor}
            radius="xl"
            size={40}
            style={{
              boxShadow: '0px 0px 4px 0px black',
            }}
          >
            <IconMessageChatbot stroke={1.5} size={20} />
          </ActionIcon>
        </Popover.Target>
        <Popover.Dropdown
          style={{
            padding: 0,
          }}
        >
          <ChatCard
            messages={messages}
            setMessages={setMessages}
            firstQuestionAsked={firstQuestionAsked}
            setFirstQuestionAsked={setFirstQuestionAsked}
          />
        </Popover.Dropdown>
      </Popover>
    </Affix>
  )
}

export function Layout() {
  const isOutdated = useVersionChecker()
  const [opened, { toggle: toggleMobile }] = useDisclosure()
  const [navbarCollapsed, { toggle: toggleNavbar, close: expandNavbar }] =
    useDisclosure(false)
  const [messages, setMessages] = useState<IStep[]>([])
  const [firstQuestionAsked, setFirstQuestionAsked] = useState(false)
  const location = useLocation()
  const { projectId } = useParams()
  const isDesktop = useMediaQuery('(min-width: 768px)') // sm breakpoint

  // Clear chat when projectId changes
  useEffect(() => {
    setMessages([])
    setFirstQuestionAsked(false)
  }, [projectId, setMessages])

  // Function to expand navbar when needed
  const handleExpandNavbar = () => {
    if (navbarCollapsed) {
      expandNavbar()
    }
  }

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{
        width: { base: navbarCollapsed ? 80 : 250 },
        breakpoint: 'sm',
        collapsed: { mobile: !opened },
      }}
      padding={0}
    >
      <Header opened={opened} toggle={toggleMobile} />
      <NavbarNested
        collapsed={navbarCollapsed}
        onExpandNavbar={handleExpandNavbar}
      />
      {isDesktop && (
        <Affix
          position={{
            top: 'calc(50% - 20px)',
            left: navbarCollapsed ? '80px' : '250px',
          }}
          style={{
            transition: 'left 0.2s',
            transform: 'translateX(-50%)',
          }}
        >
          <ActionIcon
            onClick={toggleNavbar}
            size="lg"
            variant="default"
            title={navbarCollapsed ? 'Expand navbar' : 'Collapse navbar'}
            radius="xl"
          >
            {navbarCollapsed ? (
              <IconChevronRight size={20} />
            ) : (
              <IconChevronLeft size={20} />
            )}
          </ActionIcon>
        </Affix>
      )}
      <AppShell.Main h="100dvh">
        <div style={{ height: '100%', width: '100%', overflowY: 'auto' }}>
          <Outlet />
        </div>
        {location.pathname.includes('/projects/') && (
          <Demo
            messages={messages}
            setMessages={setMessages}
            firstQuestionAsked={firstQuestionAsked}
            setFirstQuestionAsked={setFirstQuestionAsked}
          />
        )}
        <SpotlightSearch />
        <ProjectSpotlight />
        {isOutdated && (
          <Modal
            opened={isOutdated}
            onClose={() => window.location.reload()}
            centered
            withCloseButton={false}
          >
            <Text style={{ textAlign: 'justify' }}>
              A new version of this application is available. Please refresh to
              update.
            </Text>
            <Button fullWidth mt="md" onClick={() => window.location.reload()}>
              Refresh
            </Button>
          </Modal>
        )}
      </AppShell.Main>
    </AppShell>
  )
}
