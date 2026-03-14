import { useGetUserType, useUpdateSelfClerkDemoMode } from '@/api/admin'
import { NotificationSeverityEnum } from '@/api/enumerations'
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
import { useGetProjects } from '@/api/v1/operational/projects'
import { clearTips } from '@/components/Tips'
import RequiresUserType from '@/components/admin/RequiresUserType'
import { Teams as AdminTeams } from '@/components/admin/Teams'
import { GISContext } from '@/contexts/GISContext'
import { useUpdateReportSubscription } from '@/hooks/api'
import type { UserSubscription } from '@/hooks/types'
import { useUser } from '@clerk/react'
import {
  Accordion,
  ActionIcon,
  Button,
  Checkbox,
  ColorInput,
  Fieldset,
  Group,
  Loader,
  Paper,
  SegmentedControl,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
  rem,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { useLocalStorage } from '@mantine/hooks'
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconBolt,
  IconInfoCircle,
  IconMessage,
  IconNotification,
  IconReport,
  IconTrash,
  IconX,
} from '@tabler/icons-react'
import { useQueryClient } from '@tanstack/react-query'
import { useContext, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'

const TeamsGate = ({ children }: { children: React.ReactNode }) => (
  <RequiresUserType requiredUserType="admin" silent>
    {children}
  </RequiresUserType>
)

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
  // const { user } = useUser()
  return (
    <Stack p="md">
      <Title order={1}>Application Settings</Title>
      <TeamsGate>
        <AdminTeams />
      </TeamsGate>
      <Subscriptions />
      <PersonalPortfolio />
      <DemoMode />
      <Tips />
      <GISColors />
    </Stack>
  )
}

function Subscriptions() {
  const projects = useGetProjects({ personalPortfolio: false })
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
    <>
      <Title order={2}>Notifications</Title>

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
            disabled={!projects.data}
          >
            Event Chat Messages
          </Accordion.Control>
          <Accordion.Panel>
            <EventChatNotificationsPanel projects={projects.data || []} />
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
            disabled={!projects.data}
          >
            Weather
          </Accordion.Control>
          <Accordion.Panel>
            <WeatherPanel projects={projects.data || []} />
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
            disabled={!projects.data || !reportSubscriptions}
          >
            Reports
          </Accordion.Control>
          <Accordion.Panel>
            <Stack gap="xs">
              {reportSubscriptions &&
                projects.data
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
      </Accordion>
    </>
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

function PersonalPortfolio() {
  const queryClient = useQueryClient()
  const projects = useGetProjects({ personalPortfolio: false })

  const [excludedProjectIds, setExcludedProjectIds] = useLocalStorage<string[]>(
    {
      key: 'proximal-personal-portfolio-excluded-project-ids',
      defaultValue: [],
    },
  )

  return (
    <>
      <Title order={2}>Personal Portfolio</Title>
      <Text>
        Personal Portfolio lets you select a subset of projects you have access
        to and display them throughout the application. You can change your
        personal portfolio by clicking the checkboxes below.
      </Text>
      <Accordion multiple={true} variant="contained">
        <Accordion.Item value={'Notifications'}>
          <Accordion.Control
            icon={
              <IconBolt
                style={{
                  width: rem(20),
                  height: rem(20),
                }}
              />
            }
            disabled={!projects.data}
          >
            Personal Portfolio
          </Accordion.Control>
          <Accordion.Panel>
            <Stack gap="xs">
              {projects.data
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
    </>
  )
}

function Tips() {
  return (
    <>
      <Title order={2}>Tips</Title>
      <Text>
        Tips will help you understand how to use the application. By default,
        they will only be shown once. You can reset all tips and see them again
        by clicking the button below.
      </Text>
      <Button onClick={clearTips}>Reset Tips</Button>
    </>
  )
}

function GISColors() {
  return (
    <>
      <Title order={2}>GIS Colors</Title>
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
    </>
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

export default ApplicationSettings
