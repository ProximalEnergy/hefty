import { useGetUnreadNotificationCount } from '@/api/v1/admin/notifications'
import { ActionIcon, Group, Indicator } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconBell } from '@tabler/icons-react'
import cx from 'clsx'

import NotificationsPanel from './NotificationsPanel'
import classes from './ThemeToggle.module.css'

const UserAlerts = () => {
  const { data: unreadCountData } = useGetUnreadNotificationCount({})
  const [
    notificationsOpened,
    { open: openNotifications, close: closeNotifications },
  ] = useDisclosure(false)
  const unreadCount = unreadCountData?.count || 0

  return (
    <>
      <Group justify="center">
        <Indicator
          disabled={unreadCount === 0}
          label={unreadCount > 0 ? unreadCount : undefined}
          size={16}
          color="red"
        >
          <ActionIcon
            variant="default"
            size="lg"
            aria-label="Open notifications"
            onClick={openNotifications}
          >
            <IconBell className={cx(classes.icon)} stroke={1.5} />
          </ActionIcon>
        </Indicator>
      </Group>
      <NotificationsPanel
        opened={notificationsOpened}
        onClose={closeNotifications}
      />
    </>
  )
}

export default UserAlerts
