import { useGetUserType } from '@/api/admin'
import { useClerk, useUser } from '@clerk/clerk-react'
import { Avatar, Menu, UnstyledButton, rem } from '@mantine/core'
import {
  IconChevronRight,
  IconCode,
  IconDeviceDesktopCog,
  IconGauge,
  IconHelicopter,
  IconHistory,
  IconLogout2,
  IconUserCog,
  IconUsers,
} from '@tabler/icons-react'
import { Link, useParams } from 'react-router'

const UserDropdown = () => {
  const { signOut } = useClerk()
  const userType = useGetUserType({})
  const { projectId } = useParams<{ projectId: string }>()
  const { user } = useUser()

  const initials =
    user?.firstName && user?.lastName
      ? `${user.firstName[0]}${user.lastName[0]}`
      : user?.firstName?.[0] || ''

  return (
    <Menu position="bottom-end">
      <Menu.Target>
        <UnstyledButton>
          <Avatar
            src={user?.hasImage ? user?.imageUrl : undefined}
            alt={user?.fullName || 'User avatar'}
            radius="xl"
          >
            {initials}
          </Avatar>
        </UnstyledButton>
      </Menu.Target>

      <Menu.Dropdown style={{ zIndex: 800 }}>
        <Menu.Item
          component={Link}
          to="/account-settings"
          leftSection={
            <IconUserCog style={{ width: rem(14), height: rem(14) }} />
          }
        >
          Account Settings
        </Menu.Item>
        <Menu.Item
          component={Link}
          to="/application-settings"
          leftSection={
            <IconDeviceDesktopCog style={{ width: rem(14), height: rem(14) }} />
          }
        >
          Application Settings
        </Menu.Item>
        {userType.data?.name_short === 'superadmin' && (
          <>
            <Menu.Item
              component={Link}
              to="/api"
              leftSection={
                <IconCode style={{ width: rem(14), height: rem(14) }} />
              }
            >
              API
            </Menu.Item>
          </>
        )}
        {userType.data?.name_short !== 'user' && (
          <>
            <Menu.Divider />
            <Menu.Item
              component={Link}
              to={`/admin/users`}
              leftSection={
                <IconUsers style={{ width: rem(14), height: rem(14) }} />
              }
            >
              Users
            </Menu.Item>
            {userType.data?.name_short === 'superadmin' && (
              <>
                <Menu.Item
                  component={Link}
                  to="/admin/sensor-types"
                  leftSection={
                    <IconGauge style={{ width: rem(14), height: rem(14) }} />
                  }
                >
                  Sensor Types
                </Menu.Item>
                <Menu.Item
                  component={Link}
                  to="/admin/kpi-backfill"
                  leftSection={
                    <IconHistory style={{ width: rem(14), height: rem(14) }} />
                  }
                >
                  KPI Backfill
                </Menu.Item>
                <Menu trigger="hover" position="right-start" withArrow>
                  <Menu.Target>
                    <Menu.Item
                      leftSection={
                        <IconHelicopter
                          style={{ width: rem(14), height: rem(14) }}
                        />
                      }
                      rightSection={
                        <IconChevronRight
                          style={{ width: rem(16), height: rem(16) }}
                        />
                      }
                    >
                      Drones
                    </Menu.Item>
                  </Menu.Target>
                  <Menu.Dropdown>
                    <Menu.Item component={Link} to="/admin/drone-integrations">
                      Drone Integrations
                    </Menu.Item>
                    <Menu.Item component={Link} to="/admin/drone-providers">
                      Drone Providers
                    </Menu.Item>
                    <Menu.Item component={Link} to="/admin/drone-permissions">
                      Drone Permissions
                    </Menu.Item>
                  </Menu.Dropdown>
                </Menu>
              </>
            )}
            {projectId && (
              <Menu.Item
                component={Link}
                to={`/projects/${projectId}/admin`}
                leftSection={
                  <IconUsers style={{ width: rem(14), height: rem(14) }} />
                }
              >
                Admin
              </Menu.Item>
            )}
          </>
        )}
        <Menu.Divider />
        <Menu.Item
          onClick={() => signOut()}
          leftSection={
            <IconLogout2 style={{ width: rem(14), height: rem(14) }} />
          }
        >
          Logout
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  )
}

export default UserDropdown
