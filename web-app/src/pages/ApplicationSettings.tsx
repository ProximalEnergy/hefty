import { useGetUserType, useUpdateSelfClerkDemoMode } from '@/api/admin'
import {
  NotificationSeverityEnum,
  NotificationTypeEnum,
} from '@/api/enumerations'
import {
  type NotificationPreference,
  useGetNotificationPreferences,
  useUpdateNotificationPreference,
} from '@/api/v1/admin/notification_preferences'
import {
  type NotificationType,
  useGetNotificationTypes,
} from '@/api/v1/admin/notification_types'
import { useGetSubscriptions } from '@/api/v1/admin/subscriptions'
import { Project, useGetProjects } from '@/api/v1/operational/projects'
import {
  type UserProjectLabel,
  type UserProjectLabelCreate,
  useCreateUserProjectLabel,
  useDeleteUserProjectLabel,
  useGetUserProjectLabels,
  useUpdateUserProjectLabel,
} from '@/api/v1/operational/user_project_labels'
import { PageLoader } from '@/components/Loading'
import { clearTips } from '@/components/Tips'
import { Teams as AdminTeams } from '@/components/admin/Teams'
import { GISContext } from '@/contexts/GISContext'
import { useUpdateReportSubscription } from '@/hooks/api'
import type { UserSubscription } from '@/hooks/types'
import { useUser } from '@clerk/react'
import {
  Accordion,
  ActionIcon,
  ActionIconGroup,
  Button,
  Checkbox,
  ColorInput,
  ColorSwatch,
  Fieldset,
  Group,
  Loader,
  Modal,
  MultiSelect,
  Paper,
  SegmentedControl,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
  Tooltip,
  rem,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { useDisclosure, useLocalStorage } from '@mantine/hooks'
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconBolt,
  IconBulb,
  IconEdit,
  IconInfoCircle,
  IconLabelImportant,
  IconMessage,
  IconNotification,
  IconPalette,
  IconPlus,
  IconReport,
  IconTrash,
  IconUsersGroup,
  IconX,
} from '@tabler/icons-react'
import { useQueryClient } from '@tanstack/react-query'
import { useContext, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'

const DemoMode = () => {
  const { user } = useUser()
  const userType = useGetUserType({})
  const navigate = useNavigate()
  const [demoMode, setDemoMode] = useState<boolean>(
    typeof user?.publicMetadata.demo === 'boolean'
      ? (user?.publicMetadata.demo as boolean)
      : false,
  )
  const { mutate: updateSelfClerkDemoMode, isPending: isUpdatingDemoMode } =
    useUpdateSelfClerkDemoMode()

  const handleDemoModeChange = (value: boolean) => {
    setDemoMode(value)
    updateSelfClerkDemoMode(
      { demo_mode: value },
      {
        onSuccess: () => {
          // Hard refresh by navigating to portfolio with full page reload
          navigate('/portfolio')
        },
      },
    )
  }

  const ret = () => {
    return (
      <Group w="100%" justify="center">
        <Paper withBorder p="md" w="25%">
          <Stack align="center">
            <Group>
              <Text fw="bold">Demo Mode:</Text>
              <SegmentedControl
                data={[
                  { label: 'Off', value: 'false' },
                  { label: 'On', value: 'true' },
                ]}
                value={demoMode ? 'true' : 'false'}
                disabled={isUpdatingDemoMode}
                onChange={(value) =>
                  handleDemoModeChange(value === 'true' ? true : false)
                }
              />
            </Group>
            <Text>
              Demo Mode allows you to view the application with project names
              hidden. On changing your demo mode, you will be redirected to the
              Portfolio homepage. Please refresh your browser after changing
              your demo mode.
            </Text>
          </Stack>
        </Paper>
      </Group>
    )
  }

  const isSuperadmin = userType.data?.name_short === 'superadmin'
  const isSpecificUser = [
    'user_2dj6d9XfGyIPqx8ZKw6ZWvwCjzJ',
    'user_2xmRqek6OcT48vnVplc1cn64Kvf',
  ].includes(user?.id ?? '')

  if (isSuperadmin || isSpecificUser) {
    return ret()
  }

  return null
}

const ApplicationSettings = () => {
  const userType = useGetUserType({})
  const projects = useGetProjects({ personalPortfolio: false })
  if (userType.isLoading || projects.isLoading) {
    return <PageLoader />
  }
  const isAdmin =
    userType.data?.name_short === 'admin' ||
    userType.data?.name_short === 'superadmin'

  return (
    <Stack p="md">
      <Title order={1}>Application Settings</Title>
      <Tabs
        defaultValue={isAdmin ? 'teams' : 'notifications'}
        variant="outline"
      >
        <Tabs.List>
          {isAdmin && (
            <Tabs.Tab value="teams" leftSection={<IconUsersGroup size={16} />}>
              Teams
            </Tabs.Tab>
          )}
          <Tabs.Tab
            value="notifications"
            leftSection={<IconNotification size={16} />}
          >
            Notifications
          </Tabs.Tab>
          <Tabs.Tab
            value="personal-portfolio"
            leftSection={<IconBolt size={16} />}
          >
            Personal Portfolio
          </Tabs.Tab>
          <Tabs.Tab value="tips" leftSection={<IconBulb size={16} />}>
            Tips
          </Tabs.Tab>
          <Tabs.Tab value="gis-colors" leftSection={<IconPalette size={16} />}>
            GIS Colors
          </Tabs.Tab>
          <Tabs.Tab
            value="project-labels"
            leftSection={<IconLabelImportant size={16} />}
          >
            Project Labels
          </Tabs.Tab>
        </Tabs.List>

        {isAdmin && (
          <Tabs.Panel value="teams" pt="md">
            <AdminTeams />
          </Tabs.Panel>
        )}

        <Tabs.Panel value="notifications" pt="md">
          <Subscriptions projects={projects.data || []} />
        </Tabs.Panel>

        <Tabs.Panel value="personal-portfolio" pt="md">
          <PersonalPortfolioTab projects={projects.data || []} />
        </Tabs.Panel>

        <Tabs.Panel value="tips" pt="md">
          <Tips />
        </Tabs.Panel>

        <Tabs.Panel value="gis-colors" pt="md">
          <GISColors />
        </Tabs.Panel>

        <Tabs.Panel value="project-labels" pt="md">
          <ProjectLabels projects={projects.data || []} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}

function Subscriptions({ projects }: { projects: Project[] }) {
  const subscriptions = useGetSubscriptions({})
  const reportMutation = useUpdateReportSubscription()

  const handleReportSubscriptionChange = (
    value: boolean,
    project_id: string,
  ) => {
    reportMutation.mutate({ project_id, subscribe: value })
  }

  // Get array of project IDs for which the user is subscribed to reports
  const reportSubscriptions = subscriptions.data
    ?.filter((sub: UserSubscription) => sub.reports)
    .map((sub: UserSubscription) => sub.operational_project_id)

  return (
    <Stack gap="md">
      <Text>
        Configure your notification preferences for reports, weather risk
        notifications, and event chat messages.
      </Text>
      <Accordion multiple={true} variant="contained">
        <Accordion.Item value={'Event Chat Messages'}>
          <Accordion.Control
            icon={
              <IconMessage
                style={{
                  width: rem(20),
                  height: rem(20),
                }}
              />
            }
            disabled={!projects}
          >
            Event Chat Messages
          </Accordion.Control>
          <Accordion.Panel>
            <EventChatNotificationsPanel projects={projects || []} />
          </Accordion.Panel>
        </Accordion.Item>
        <Accordion.Item value={'Weather'}>
          <Accordion.Control
            icon={
              <IconNotification
                style={{
                  width: rem(20),
                  height: rem(20),
                }}
              />
            }
            disabled={!projects}
          >
            Weather
          </Accordion.Control>
          <Accordion.Panel>
            <WeatherPanel projects={projects || []} />
          </Accordion.Panel>
        </Accordion.Item>
        <Accordion.Item value={'Reports'}>
          <Accordion.Control
            icon={
              <IconReport
                style={{
                  width: rem(20),
                  height: rem(20),
                }}
              />
            }
            disabled={!projects || !reportSubscriptions}
          >
            Reports
          </Accordion.Control>
          <Accordion.Panel>
            <Stack gap="xs">
              {reportSubscriptions &&
                projects
                  ?.sort((a, b) => a.name_long.localeCompare(b.name_long))
                  .map((project) => (
                    <Checkbox
                      key={project.project_id}
                      value={project.project_id}
                      label={project.name_long}
                      checked={reportSubscriptions.includes(project.project_id)}
                      onChange={(value) =>
                        handleReportSubscriptionChange(
                          value.currentTarget.checked,
                          project.project_id,
                        )
                      }
                    />
                  ))}
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>
        <Accordion.Item value={'Capacity Reduction'}>
          <Accordion.Control
            icon={
              <IconAlertTriangle
                style={{
                  width: rem(20),
                  height: rem(20),
                }}
              />
            }
            disabled={!projects}
          >
            Capacity Reduction
          </Accordion.Control>
          <Accordion.Panel>
            <CapacityReductionNotificationsPanel projects={projects || []} />
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Stack>
  )
}

function WeatherPanel({
  projects,
}: {
  projects: Array<{ project_id: string; name_long: string }>
}) {
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()
  const notificationTypes = useGetNotificationTypes({})
  const preferences = useGetNotificationPreferences({})
  const updateMutation = useUpdateNotificationPreference()

  // Find weather notification types
  const weatherTypes = useMemo(() => {
    if (!notificationTypes.data) return []
    const types = notificationTypes.data.filter((type) => {
      const nameLower = type.name_long.toLowerCase()
      return (
        nameLower.includes('hail') ||
        nameLower.includes('wind') ||
        nameLower.includes('fire') ||
        nameLower.includes('tornado')
      )
    })

    // Order: Hail, Wind, Fire, Tornado
    const order = ['hail', 'wind', 'fire', 'tornado']
    return types.sort((a, b) => {
      const aIndex = order.findIndex((o) =>
        a.name_long.toLowerCase().includes(o),
      )
      const bIndex = order.findIndex((o) =>
        b.name_long.toLowerCase().includes(o),
      )
      if (aIndex === -1) return 1
      if (bIndex === -1) return -1
      return aIndex - bIndex
    })
  }, [notificationTypes.data])

  // Create a map of preferences for quick lookup
  const preferencesMap = useMemo(() => {
    const map = new Map<string, NotificationPreference>()
    preferences.data?.forEach((pref) => {
      const key = `${pref.project_id}-${pref.notification_type_id}`
      map.set(key, pref)
    })
    return map
  }, [preferences.data])

  const getPreference = (
    projectId: string,
    notificationTypeId: number,
  ): NotificationPreference | null => {
    const key = `${projectId}-${notificationTypeId}`
    return preferencesMap.get(key) || null
  }

  const sortedProjects = [...projects].sort((a, b) =>
    a.name_long.localeCompare(b.name_long),
  )

  if (notificationTypes.isLoading || preferences.isLoading) {
    return <Loader />
  }

  // Get display names for weather types
  const getWeatherTypeName = (type: NotificationType): string => {
    const nameLower = type.name_long.toLowerCase()
    if (nameLower.includes('hail')) return 'Hail'
    if (nameLower.includes('wind')) return 'Wind'
    if (nameLower.includes('fire')) return 'Fire'
    if (nameLower.includes('tornado')) return 'Tornadoes'
    return type.name_long
  }

  // Get tooltip text for weather types
  const getWeatherTypeTooltip = (type: NotificationType): string => {
    const nameLower = type.name_long.toLowerCase()
    let weatherType = ''
    if (nameLower.includes('hail')) weatherType = 'Hail'
    else if (nameLower.includes('wind')) weatherType = 'Wind'
    else if (nameLower.includes('fire')) weatherType = 'Fire'
    else if (nameLower.includes('tornado')) weatherType = 'Tornado'
    else {
      // Remove all caps and convert to title case
      const words = type.name_long.toLowerCase().split(' ')
      weatherType = words
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
    }

    return `${weatherType} forecasts from the National Weather Service (NWS)`
  }

  // Generate severity control data with colored icons
  const getSeverityControlData = () => {
    const isDark = colorScheme === 'dark'
    const iconSize = 14

    return [
      {
        label: (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <IconX
              size={iconSize}
              color={isDark ? theme.colors.gray[5] : theme.colors.gray[7]}
            />
            <span>OFF</span>
          </span>
        ),
        value: 'OFF',
      },
      {
        label: (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <IconInfoCircle
              size={iconSize}
              color={isDark ? theme.colors.blue[4] : theme.colors.blue[6]}
            />
            <span>INFO</span>
          </span>
        ),
        value: NotificationSeverityEnum.INFO.toUpperCase(),
      },
      {
        label: (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <IconAlertTriangle
              size={iconSize}
              color={isDark ? theme.colors.yellow[4] : theme.colors.yellow[6]}
            />
            <span>WARN</span>
          </span>
        ),
        value: NotificationSeverityEnum.WARNING.toUpperCase(),
      },
      {
        label: (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <IconAlertCircle
              size={iconSize}
              color={isDark ? theme.colors.red[4] : theme.colors.red[6]}
            />
            <span>CRIT</span>
          </span>
        ),
        value: NotificationSeverityEnum.CRITICAL.toUpperCase(),
      },
    ]
  }

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Configure notifications for weather-related events. Severity levels:
        INFO (&lt; 15%), WARNING (&lt; 30%), CRITICAL (&gt; 30%).
      </Text>
      <Table.ScrollContainer minWidth={800}>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Project Name</Table.Th>
              {weatherTypes.map((type) => (
                <Table.Th key={type.notification_type_id}>
                  <Group gap={4}>
                    {getWeatherTypeName(type)}
                    <Tooltip label={getWeatherTypeTooltip(type)}>
                      <ActionIcon size="xs" variant="transparent" color="gray">
                        <IconInfoCircle size={14} />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                </Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {sortedProjects.map((project) => (
              <Table.Tr key={project.project_id}>
                <Table.Td>{project.name_long}</Table.Td>
                {weatherTypes.map((type) => {
                  const preference = getPreference(
                    project.project_id,
                    type.notification_type_id,
                  )
                  const inAppEnabled =
                    preference?.in_app_enabled ?? type.in_app_enabled_default
                  const emailEnabled =
                    preference?.email_enabled ?? type.email_enabled_default
                  const inAppSeverity =
                    preference?.in_app_min_severity ??
                    type.in_app_severity_default ??
                    'info'
                  const emailSeverity =
                    preference?.email_min_severity ??
                    type.email_severity_default ??
                    'info'

                  return (
                    <Table.Td key={type.notification_type_id}>
                      <Stack gap="xs">
                        <Group gap="xs" align="center">
                          <Text size="xs" w={50}>
                            in-app:
                          </Text>
                          <SegmentedControl
                            size="xs"
                            value={
                              inAppEnabled ? inAppSeverity.toUpperCase() : 'OFF'
                            }
                            onChange={(value) => {
                              if (value === 'OFF') {
                                updateMutation.mutate({
                                  project_id: project.project_id,
                                  notification_type_id:
                                    type.notification_type_id,
                                  in_app_enabled: false,
                                })
                              } else {
                                updateMutation.mutate({
                                  project_id: project.project_id,
                                  notification_type_id:
                                    type.notification_type_id,
                                  in_app_enabled: true,
                                  in_app_min_severity: value?.toLowerCase() as
                                    | 'info'
                                    | 'warning'
                                    | 'critical',
                                })
                              }
                            }}
                            data={getSeverityControlData()}
                          />
                        </Group>
                        <Group gap="xs" align="center">
                          <Text size="xs" w={50}>
                            email:
                          </Text>
                          <SegmentedControl
                            size="xs"
                            value={
                              emailEnabled ? emailSeverity.toUpperCase() : 'OFF'
                            }
                            onChange={(value) => {
                              if (value === 'OFF') {
                                updateMutation.mutate({
                                  project_id: project.project_id,
                                  notification_type_id:
                                    type.notification_type_id,
                                  email_enabled: false,
                                })
                              } else {
                                updateMutation.mutate({
                                  project_id: project.project_id,
                                  notification_type_id:
                                    type.notification_type_id,
                                  email_enabled: true,
                                  email_min_severity: value?.toLowerCase() as
                                    | 'info'
                                    | 'warning'
                                    | 'critical',
                                })
                              }
                            }}
                            data={getSeverityControlData()}
                          />
                        </Group>
                      </Stack>
                    </Table.Td>
                  )
                })}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Stack>
  )
}

function EventChatNotificationsPanel({
  projects,
}: {
  projects: Array<{ project_id: string; name_long: string }>
}) {
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()
  const notificationTypes = useGetNotificationTypes({})
  const preferences = useGetNotificationPreferences({})
  const updateMutation = useUpdateNotificationPreference()

  const eventChatType = useMemo(
    () =>
      notificationTypes.data?.find((t) => t.name_long === 'event_chat_message'),
    [notificationTypes.data],
  )

  const preferencesMap = useMemo(() => {
    const map = new Map<string, NotificationPreference>()
    preferences.data?.forEach((pref) => {
      map.set(`${pref.project_id}-${pref.notification_type_id}`, pref)
    })
    return map
  }, [preferences.data])

  const getPreference = (
    projectId: string,
    notificationTypeId: number,
  ): NotificationPreference | null => {
    const key = `${projectId}-${notificationTypeId}`
    return preferencesMap.get(key) || null
  }

  const sortedProjects = useMemo(
    () => [...projects].sort((a, b) => a.name_long.localeCompare(b.name_long)),
    [projects],
  )

  const getEventChatControlData = () => {
    const isDark = colorScheme === 'dark'
    const iconSize = 14

    return [
      {
        label: (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <IconX
              size={iconSize}
              color={isDark ? theme.colors.gray[5] : theme.colors.gray[7]}
            />
            <span>OFF</span>
          </span>
        ),
        value: 'OFF',
      },
      {
        label: (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <IconInfoCircle
              size={iconSize}
              color={isDark ? theme.colors.blue[4] : theme.colors.blue[6]}
            />
            <span>ON</span>
          </span>
        ),
        value: 'ON',
      },
    ]
  }

  if (notificationTypes.isLoading || preferences.isLoading) {
    return <Loader />
  }

  if (!eventChatType) {
    return (
      <Text size="sm" c="dimmed">
        Event chat notification type is not configured.
      </Text>
    )
  }

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Control event chat notifications per project. First message in a thread:
        all company users with project access (filtered by your preferences
        below). Follow-up messages: all users who have posted in that thread
        (preferences do not apply - you will always receive notifications for
        conversations you&apos;ve participated in). Users who have muted the
        chat are never notified.
      </Text>
      <Table.ScrollContainer minWidth={600}>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Project Name</Table.Th>
              <Table.Th>
                <Group gap={4}>
                  Event Chat Messages
                  <Tooltip label="Notifications for messages posted in event chat threads">
                    <ActionIcon size="xs" variant="transparent" color="gray">
                      <IconInfoCircle size={14} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {sortedProjects.map((project) => {
              const preference = getPreference(
                project.project_id,
                eventChatType.notification_type_id,
              )
              const inAppEnabled =
                preference?.in_app_enabled ??
                eventChatType.in_app_enabled_default
              const emailEnabled =
                preference?.email_enabled ?? eventChatType.email_enabled_default

              return (
                <Table.Tr key={project.project_id}>
                  <Table.Td>{project.name_long}</Table.Td>
                  <Table.Td>
                    <Stack gap="xs">
                      <Group gap="xs" align="center">
                        <Text size="xs" w={50}>
                          in-app:
                        </Text>
                        <SegmentedControl
                          size="xs"
                          value={inAppEnabled ? 'ON' : 'OFF'}
                          onChange={(value) => {
                            if (value === 'OFF') {
                              updateMutation.mutate({
                                project_id: project.project_id,
                                notification_type_id:
                                  eventChatType.notification_type_id,
                                in_app_enabled: false,
                              })
                            } else {
                              updateMutation.mutate({
                                project_id: project.project_id,
                                notification_type_id:
                                  eventChatType.notification_type_id,
                                in_app_enabled: true,
                                in_app_min_severity: 'info',
                              })
                            }
                          }}
                          data={getEventChatControlData()}
                        />
                      </Group>
                      <Group gap="xs" align="center">
                        <Text size="xs" w={50}>
                          email:
                        </Text>
                        <SegmentedControl
                          size="xs"
                          value={emailEnabled ? 'ON' : 'OFF'}
                          onChange={(value) => {
                            if (value === 'OFF') {
                              updateMutation.mutate({
                                project_id: project.project_id,
                                notification_type_id:
                                  eventChatType.notification_type_id,
                                email_enabled: false,
                              })
                            } else {
                              updateMutation.mutate({
                                project_id: project.project_id,
                                notification_type_id:
                                  eventChatType.notification_type_id,
                                email_enabled: true,
                                email_min_severity: 'info',
                              })
                            }
                          }}
                          data={getEventChatControlData()}
                        />
                      </Group>
                    </Stack>
                  </Table.Td>
                </Table.Tr>
              )
            })}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Stack>
  )
}

function CapacityReductionNotificationsPanel({
  projects,
}: {
  projects: Array<{ project_id: string; name_long: string }>
}) {
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()
  const notificationTypes = useGetNotificationTypes({})
  const preferences = useGetNotificationPreferences({})
  const updateMutation = useUpdateNotificationPreference()

  const capacityNotificationType = useMemo(() => {
    const types = notificationTypes.data
    if (!types) return undefined
    return types.find(
      (t) =>
        t.notification_type_id ===
        NotificationTypeEnum.PROJECT_CAPACITY_REDUCTION,
    )
  }, [notificationTypes.data])

  const preferencesMap = useMemo(() => {
    const map = new Map<string, NotificationPreference>()
    preferences.data?.forEach((pref) => {
      map.set(`${pref.project_id}-${pref.notification_type_id}`, pref)
    })
    return map
  }, [preferences.data])

  const getPreference = (
    projectId: string,
    notificationTypeId: number,
  ): NotificationPreference | null => {
    const key = `${projectId}-${notificationTypeId}`
    return preferencesMap.get(key) || null
  }

  const sortedProjects = useMemo(
    () => [...projects].sort((a, b) => a.name_long.localeCompare(b.name_long)),
    [projects],
  )

  const getSeverityControlData = () => {
    const isDark = colorScheme === 'dark'
    const iconSize = 14

    return [
      {
        label: (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <IconX
              size={iconSize}
              color={isDark ? theme.colors.gray[5] : theme.colors.gray[7]}
            />
            <span>OFF</span>
          </span>
        ),
        value: 'OFF',
      },
      {
        label: (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <IconInfoCircle
              size={iconSize}
              color={isDark ? theme.colors.blue[4] : theme.colors.blue[6]}
            />
            <span>INFO</span>
          </span>
        ),
        value: NotificationSeverityEnum.INFO.toUpperCase(),
      },
      {
        label: (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <IconAlertTriangle
              size={iconSize}
              color={isDark ? theme.colors.yellow[4] : theme.colors.yellow[6]}
            />
            <span>WARNING</span>
          </span>
        ),
        value: NotificationSeverityEnum.WARNING.toUpperCase(),
      },
      {
        label: (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <IconAlertCircle
              size={iconSize}
              color={isDark ? theme.colors.red[4] : theme.colors.red[6]}
            />
            <span>CRITICAL</span>
          </span>
        ),
        value: NotificationSeverityEnum.CRITICAL.toUpperCase(),
      },
    ]
  }

  if (notificationTypes.isLoading || preferences.isLoading) {
    return <Loader />
  }

  if (!capacityNotificationType) {
    return (
      <Text size="sm" c="dimmed">
        Capacity reduction notification type is not configured.
      </Text>
    )
  }

  return (
    <Stack gap="md">
      <Stack gap={0}>
        <Text size="sm" c="dimmed">
          Control capacity reduction notifications per project. Capacity
          reduction calculations are derived from project Events.
        </Text>
        <Text size="sm" c="dimmed">
          INFO alerts are sent when the project is below 98% capacity.
        </Text>
        <Text size="sm" c="dimmed">
          WARNING alerts are sent when the project is below 95% capacity.
        </Text>
        <Text size="sm" c="dimmed">
          CRITICAL alerts are sent when the project is below 90% capacity.
        </Text>
      </Stack>
      <Table.ScrollContainer minWidth={800}>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Project Name</Table.Th>
              <Table.Th>
                <Group gap={4}>
                  Capacity Reduction
                  <Tooltip label="Notifications for capacity reduction alerts">
                    <ActionIcon size="xs" variant="transparent" color="gray">
                      <IconInfoCircle size={14} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {sortedProjects.map((project) => {
              const preference = getPreference(
                project.project_id,
                capacityNotificationType.notification_type_id,
              )
              const inAppEnabled =
                preference?.in_app_enabled ??
                capacityNotificationType.in_app_enabled_default
              const emailEnabled =
                preference?.email_enabled ??
                capacityNotificationType.email_enabled_default
              const inAppSeverity =
                preference?.in_app_min_severity ??
                capacityNotificationType.in_app_severity_default ??
                'info'
              const emailSeverity =
                preference?.email_min_severity ??
                capacityNotificationType.email_severity_default ??
                'info'

              return (
                <Table.Tr key={project.project_id}>
                  <Table.Td>{project.name_long}</Table.Td>
                  <Table.Td>
                    <Stack gap="xs">
                      <Group gap="xs" align="center">
                        <Text size="xs" w={50}>
                          in-app:
                        </Text>
                        <SegmentedControl
                          size="xs"
                          value={
                            inAppEnabled ? inAppSeverity.toUpperCase() : 'OFF'
                          }
                          onChange={(value) => {
                            if (value === 'OFF') {
                              updateMutation.mutate({
                                project_id: project.project_id,
                                notification_type_id:
                                  capacityNotificationType.notification_type_id,
                                in_app_enabled: false,
                              })
                            } else {
                              updateMutation.mutate({
                                project_id: project.project_id,
                                notification_type_id:
                                  capacityNotificationType.notification_type_id,
                                in_app_enabled: true,
                                in_app_min_severity: value?.toLowerCase() as
                                  | 'info'
                                  | 'warning'
                                  | 'critical',
                              })
                            }
                          }}
                          data={getSeverityControlData()}
                        />
                      </Group>
                      <Group gap="xs" align="center">
                        <Text size="xs" w={50}>
                          email:
                        </Text>
                        <SegmentedControl
                          size="xs"
                          value={
                            emailEnabled ? emailSeverity.toUpperCase() : 'OFF'
                          }
                          onChange={(value) => {
                            if (value === 'OFF') {
                              updateMutation.mutate({
                                project_id: project.project_id,
                                notification_type_id:
                                  capacityNotificationType.notification_type_id,
                                email_enabled: false,
                              })
                            } else {
                              updateMutation.mutate({
                                project_id: project.project_id,
                                notification_type_id:
                                  capacityNotificationType.notification_type_id,
                                email_enabled: true,
                                email_min_severity: value?.toLowerCase() as
                                  | 'info'
                                  | 'warning'
                                  | 'critical',
                              })
                            }
                          }}
                          data={getSeverityControlData()}
                        />
                      </Group>
                    </Stack>
                  </Table.Td>
                </Table.Tr>
              )
            })}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Stack>
  )
}

function PersonalPortfolioTab({ projects }: { projects: Project[] }) {
  return (
    <Stack gap="lg">
      <PersonalPortfolio projects={projects || []} />
      <DemoMode />
    </Stack>
  )
}

function PersonalPortfolio({ projects }: { projects: Project[] }) {
  const queryClient = useQueryClient()

  const [excludedProjectIds, setExcludedProjectIds] = useLocalStorage<string[]>(
    {
      key: 'proximal-personal-portfolio-excluded-project-ids',
      defaultValue: [],
    },
  )

  return (
    <Stack gap="md">
      <Text>
        Personal Portfolio lets you select a subset of projects you have access
        to and display them throughout the application. You can change your
        personal portfolio by clicking the checkboxes below.
      </Text>
      <Accordion multiple={true} variant="contained">
        <Accordion.Item value={'Projects'}>
          <Accordion.Control
            icon={
              <IconBolt
                style={{
                  width: rem(20),
                  height: rem(20),
                }}
              />
            }
            disabled={!projects}
          >
            Select Projects
          </Accordion.Control>
          <Accordion.Panel>
            <Stack gap="xs">
              {projects
                ?.sort((a, b) => a.name_long.localeCompare(b.name_long))
                .map((project) => (
                  <Checkbox
                    key={project.project_id}
                    value={project.project_id}
                    label={project.name_long}
                    td={
                      excludedProjectIds.includes(project.project_id)
                        ? 'line-through'
                        : undefined
                    }
                    checked={!excludedProjectIds.includes(project.project_id)}
                    onChange={(value) => {
                      setExcludedProjectIds(
                        value.currentTarget.checked
                          ? excludedProjectIds.filter(
                              (id) => id !== project.project_id,
                            )
                          : [...excludedProjectIds, project.project_id],
                      )
                      queryClient.removeQueries({
                        queryKey: ['getProjectsPersonal'],
                      })
                    }}
                  />
                ))}
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Stack>
  )
}

function Tips() {
  return (
    <Stack gap="md">
      <Text>
        Tips will help you understand how to use the application. By default,
        they will only be shown once. You can reset all tips and see them again
        by clicking the button below.
      </Text>
      <Button onClick={clearTips} w="fit-content">
        Reset Tips
      </Button>
    </Stack>
  )
}

function GISColors() {
  return (
    <Stack gap="md">
      <Text>
        Customize the color scales used in GIS visualizations. The two scales
        used are <span style={{ fontStyle: 'italic' }}>High to Low</span> and{' '}
        <span style={{ fontStyle: 'italic' }}>Good to Bad</span>. High to Low
        will be shown when there is no{' '}
        <span style={{ fontStyle: 'italic' }}>ideal</span> value. Good to Bad
        will be shown when there is an ideal value. You can change colors by
        clicking on the color inputs.
      </Text>
      <ColorScalePicker localStorageKey="proximal-gis-colors-high-low" />
      <ColorScalePicker localStorageKey="proximal-gis-colors-good-bad" />
    </Stack>
  )
}

function ColorScalePicker({
  localStorageKey,
}: {
  localStorageKey:
    | 'proximal-gis-colors-high-low'
    | 'proximal-gis-colors-good-bad'
}) {
  const theme = useMantineTheme()
  const context = useContext(GISContext)

  if (!context) {
    throw new Error('GISContext is not defined')
  }

  const defaultColors = {
    'proximal-gis-colors-high-low': [
      { id: 1, value: theme.colors.dark[1] },
      { id: 2, value: theme.colors.green[7] },
    ],
    'proximal-gis-colors-good-bad': [
      { id: 1, value: theme.colors.red[7] },
      { id: 2, value: theme.colors.yellow[7] },
      { id: 3, value: theme.colors.green[7] },
    ],
  }

  let colors, setColors
  if (localStorageKey === 'proximal-gis-colors-high-low') {
    colors = context.colorsHighLow
    setColors = context.setColorsHighLow
  } else {
    colors = context.colorsGoodBad
    setColors = context.setColorsGoodBad
  }

  const legends = {
    'proximal-gis-colors-high-low': 'High to Low',
    'proximal-gis-colors-good-bad': 'Good to Bad',
  }

  const labels = {
    'proximal-gis-colors-high-low': ['Low', 'High'],
    'proximal-gis-colors-good-bad': ['Bad', 'Good'],
  }

  const addColor = () => {
    if (colors.length < 5) {
      const newColors = [...colors, { id: colors.length + 1, value: '#000000' }]
      setColors(newColors)
    }
  }

  const updateColor = (id: number, value: string) => {
    const updatedColors = colors.map((color) =>
      color.id === id ? { ...color, value } : color,
    )
    setColors(updatedColors)
  }

  const deleteColor = (id: number) => {
    if (colors.length > 2) {
      const updatedColors = colors
        .filter((color) => color.id !== id)
        .map((color, index) => ({
          ...color,
          id: index + 1,
        }))
      setColors(updatedColors)
    }
  }

  const restoreToDefault = () => {
    setColors(defaultColors[localStorageKey])
  }

  const gradientStyle = {
    background: `linear-gradient(to right, ${colors
      .map((color) => color.value)
      .join(', ')})`,
  }

  const labelStyle = {
    color: 'white',
    fontWeight: 'bold',
    fontFamily: 'monospace',
  }

  return (
    <Fieldset legend={legends[localStorageKey]}>
      <Stack gap="xs">
        <Paper style={gradientStyle}>
          <Group justify="space-between" px="sm" py={5}>
            <Text style={{ ...labelStyle }}>{labels[localStorageKey][0]}</Text>
            <Text style={{ ...labelStyle }}>{labels[localStorageKey][1]}</Text>
          </Group>
        </Paper>

        {colors.map((color) => (
          <Group key={color.id}>
            <ColorInput
              value={color.value}
              onChange={(value) => updateColor(color.id, value)}
              withPicker
              style={{ flex: 1 }}
            />
            <ActionIcon
              onClick={() => deleteColor(color.id)}
              disabled={colors.length <= 2}
              variant="default"
              size="lg"
            >
              <IconTrash size={16} />
            </ActionIcon>
          </Group>
        ))}

        <Group>
          <Button
            flex={1}
            size="compact-sm"
            variant="default"
            onClick={addColor}
            disabled={colors.length >= 5}
          >
            Add Color
          </Button>
          <Button
            flex={1}
            size="compact-sm"
            variant="default"
            onClick={restoreToDefault}
          >
            Restore to Defaults
          </Button>
        </Group>
      </Stack>
    </Fieldset>
  )
}

function ProjectLabels({ projects }: { projects: Project[] }) {
  const [createOpened, createModal] = useDisclosure(false)
  const [editOpened, editModal] = useDisclosure(false)
  const [deleteOpened, deleteModal] = useDisclosure(false)
  const [activeLabel, setActiveLabel] = useState<UserProjectLabel | null>(null)
  const userProjectLabels = useGetUserProjectLabels()
  const createUserProjectLabel = useCreateUserProjectLabel()
  const updateUserProjectLabel = useUpdateUserProjectLabel()
  const deleteUserProjectLabel = useDeleteUserProjectLabel()

  const projectNameById = useMemo(
    () =>
      new Map(
        projects.map(
          (project) => [project.project_id, project.name_long] as const,
        ),
      ),
    [projects],
  )

  const handleCreateProjectLabel = async (
    labelData: UserProjectLabelCreate,
  ) => {
    await createUserProjectLabel.mutateAsync(labelData)
  }

  const handleOpenCreateModal = () => {
    createUserProjectLabel.reset()
    createModal.open()
  }

  const handleCloseCreateModal = () => {
    createModal.close()
  }

  const handleOpenEditModal = (label: UserProjectLabel) => {
    updateUserProjectLabel.reset()
    setActiveLabel(label)
    editModal.open()
  }

  const handleCloseEditModal = () => {
    setActiveLabel(null)
    editModal.close()
  }

  const handleUpdateProjectLabel = async (labelData: UserProjectLabel) => {
    if (!activeLabel) return
    await updateUserProjectLabel.mutateAsync({
      userProjectLabelId: activeLabel.user_project_label_id,
      labelData,
    })
  }

  const handleOpenDeleteModal = (label: UserProjectLabel) => {
    deleteUserProjectLabel.reset()
    setActiveLabel(label)
    deleteModal.open()
  }

  const handleCloseDeleteModal = () => {
    setActiveLabel(null)
    deleteModal.close()
  }

  const handleDeleteProjectLabel = async () => {
    if (!activeLabel) return
    await deleteUserProjectLabel.mutateAsync({
      userProjectLabelId: activeLabel.user_project_label_id,
    })
  }

  return (
    <Stack w="100%" gap="md">
      <Text>Create and manage project labels.</Text>
      <Paper withBorder p="md">
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Color</Table.Th>
              <Table.Th>Projects</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {userProjectLabels.isLoading ||
              (userProjectLabels.isRefetching && (
                <Table.Tr>
                  <Table.Td colSpan={4}>
                    <Group justify="center">
                      <Loader size="sm" />
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            {!userProjectLabels.isLoading &&
              !userProjectLabels.isRefetching &&
              userProjectLabels.data?.map((label) => {
                const projectNames = label.project_ids
                  .map((projectId) => projectNameById.get(projectId))
                  .filter((projectName): projectName is string => !!projectName)
                  .sort((a, b) => a.localeCompare(b))

                return (
                  <Table.Tr key={label.user_project_label_id}>
                    <Table.Td>{label.name}</Table.Td>
                    <Table.Td>
                      <ColorSwatch color={label.color} size={16} />
                    </Table.Td>
                    <Table.Td>
                      {projectNames.length
                        ? projectNames.join(', ')
                        : 'No projects assigned'}
                    </Table.Td>
                    <Table.Td>
                      <ActionIconGroup>
                        <ActionIcon
                          variant="transparent"
                          color="blue"
                          onClick={() => handleOpenEditModal(label)}
                        >
                          <IconEdit size={16} />
                        </ActionIcon>
                        <ActionIcon
                          variant="transparent"
                          color="red"
                          onClick={() => handleOpenDeleteModal(label)}
                        >
                          <IconTrash size={16} />
                        </ActionIcon>
                      </ActionIconGroup>
                    </Table.Td>
                  </Table.Tr>
                )
              })}
            {!userProjectLabels.isLoading &&
              !userProjectLabels.isRefetching &&
              !userProjectLabels.data?.length && (
                <Table.Tr>
                  <Table.Td colSpan={4}>
                    <Text c="dimmed">No project labels found.</Text>
                  </Table.Td>
                </Table.Tr>
              )}
          </Table.Tbody>
        </Table>
      </Paper>
      <Button
        leftSection={<IconPlus size={16} />}
        w="fit-content"
        onClick={handleOpenCreateModal}
      >
        Create New Project Label
      </Button>
      <CreateProjectLabelModal
        opened={createOpened}
        close={handleCloseCreateModal}
        projects={projects}
        isPending={createUserProjectLabel.isPending}
        errorMessage={createUserProjectLabel.error?.message}
        onCreate={handleCreateProjectLabel}
      />
      <EditProjectLabelModal
        opened={editOpened}
        close={handleCloseEditModal}
        projects={projects}
        initialLabel={activeLabel}
        isPending={updateUserProjectLabel.isPending}
        errorMessage={updateUserProjectLabel.error?.message}
        onSave={handleUpdateProjectLabel}
      />
      <DeleteProjectLabelModal
        opened={deleteOpened}
        close={handleCloseDeleteModal}
        labelName={activeLabel?.name}
        isPending={deleteUserProjectLabel.isPending}
        errorMessage={deleteUserProjectLabel.error?.message}
        onDelete={handleDeleteProjectLabel}
      />
    </Stack>
  )
}

function CreateProjectLabelModal({
  opened,
  close,
  projects,
  isPending,
  errorMessage,
  onCreate,
}: {
  opened: boolean
  close: () => void
  projects: Project[]
  isPending: boolean
  errorMessage?: string
  onCreate: (labelData: UserProjectLabelCreate) => Promise<void>
}) {
  const [name, setName] = useState('')
  const [color, setColor] = useState<string>('#adb5bd')
  const [projectIds, setProjectIds] = useState<string[]>([])

  const sortedProjects = useMemo(
    () => [...projects].sort((a, b) => a.name_long.localeCompare(b.name_long)),
    [projects],
  )

  const isColorValid = /^#[0-9a-fA-F]{6}$/.test(color)
  const isCreateDisabled = !name.trim() || !isColorValid || !projectIds.length

  const handleClose = () => {
    setName('')
    setColor('#adb5bd')
    setProjectIds([])
    close()
  }

  const handleCreate = async () => {
    try {
      await onCreate({
        name: name.trim(),
        color,
        project_ids: projectIds,
      })
      handleClose()
    } catch {
      // Keep modal open so user can adjust and retry.
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Create New Project Label"
    >
      <Stack gap="md">
        <TextInput
          label="Name"
          placeholder="Enter label name"
          value={name}
          onChange={(e) => setName(e.currentTarget.value)}
        />
        <ColorInput
          label="Color"
          placeholder="Select color"
          withEyeDropper={false}
          value={color}
          onChange={setColor}
        />
        <MultiSelect
          label="Projects"
          placeholder="Select projects"
          data={sortedProjects.map((project) => ({
            value: project.project_id,
            label: project.name_long,
          }))}
          value={projectIds}
          onChange={setProjectIds}
          searchable
        />
        <Button
          onClick={handleCreate}
          loading={isPending}
          disabled={isCreateDisabled || isPending}
        >
          Create
        </Button>
        {!!errorMessage && (
          <Text size="sm" c="red">
            {errorMessage}
          </Text>
        )}
      </Stack>
    </Modal>
  )
}

function EditProjectLabelModal({
  opened,
  close,
  projects,
  initialLabel,
  isPending,
  errorMessage,
  onSave,
}: {
  opened: boolean
  close: () => void
  projects: Project[]
  initialLabel: UserProjectLabel | null
  isPending: boolean
  errorMessage?: string
  onSave: (labelData: UserProjectLabel) => Promise<void>
}) {
  const [name, setName] = useState('')
  const [color, setColor] = useState<string>('#adb5bd')
  const [projectIds, setProjectIds] = useState<string[]>([])

  useEffect(() => {
    if (!opened || !initialLabel) {
      return
    }
    setName(initialLabel.name)
    setColor(initialLabel.color)
    setProjectIds(initialLabel.project_ids)
  }, [opened, initialLabel])

  const sortedProjects = useMemo(
    () => [...projects].sort((a, b) => a.name_long.localeCompare(b.name_long)),
    [projects],
  )

  const isColorValid = /^#[0-9a-fA-F]{6}$/.test(color)
  const isSaveDisabled = !name.trim() || !isColorValid || !projectIds.length

  const handleSave = async () => {
    try {
      await onSave({
        name: name.trim(),
        color,
        project_ids: projectIds,
        user_project_label_id: initialLabel?.user_project_label_id ?? 0,
        user_id: initialLabel?.user_id ?? '',
      })
      close()
    } catch {
      // Keep modal open so user can adjust and retry.
    }
  }

  return (
    <Modal opened={opened} onClose={close} title="Edit Project Label">
      <Stack gap="md">
        <TextInput
          label="Name"
          placeholder="Enter label name"
          value={name}
          onChange={(e) => setName(e.currentTarget.value)}
        />
        <ColorInput
          label="Color"
          placeholder="Select color"
          withEyeDropper={false}
          value={color}
          onChange={setColor}
        />
        <MultiSelect
          label="Projects"
          placeholder="Select projects"
          data={sortedProjects.map((project) => ({
            value: project.project_id,
            label: project.name_long,
          }))}
          value={projectIds}
          onChange={setProjectIds}
          searchable
        />
        <Button
          onClick={handleSave}
          loading={isPending}
          disabled={isSaveDisabled || isPending}
        >
          Save Changes
        </Button>
        {!!errorMessage && (
          <Text size="sm" c="red">
            {errorMessage}
          </Text>
        )}
      </Stack>
    </Modal>
  )
}

function DeleteProjectLabelModal({
  opened,
  close,
  labelName,
  isPending,
  errorMessage,
  onDelete,
}: {
  opened: boolean
  close: () => void
  labelName?: string
  isPending: boolean
  errorMessage?: string
  onDelete: () => Promise<void>
}) {
  const handleDelete = async () => {
    try {
      await onDelete()
      close()
    } catch {
      // Keep modal open so user can retry.
    }
  }

  return (
    <Modal opened={opened} onClose={close} title="Delete Project Label">
      <Stack gap="md">
        <Text>
          Are you sure you want to delete{' '}
          <Text span fw={700}>
            {labelName}
          </Text>
          ?
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={close} disabled={isPending}>
            Cancel
          </Button>
          <Button color="red" onClick={handleDelete} loading={isPending}>
            Delete
          </Button>
        </Group>
        {!!errorMessage && (
          <Text size="sm" c="red">
            {errorMessage}
          </Text>
        )}
      </Stack>
    </Modal>
  )
}

export default ApplicationSettings
