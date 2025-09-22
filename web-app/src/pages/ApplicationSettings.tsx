import { useGetProjects } from '@/api/v1/operational/projects'
import { clearTips } from '@/components/Tips'
import RequiresUserType from '@/components/admin/RequiresUserType'
import { Teams as AdminTeams } from '@/components/admin/Teams'
import { GISContext } from '@/contexts/GISContext'
import {
  useGetSubscriptions,
  useUpdateNotificationSubscription,
  useUpdateReportSubscription,
} from '@/hooks/api'
import {
  Accordion,
  ActionIcon,
  Button,
  Checkbox,
  ColorInput,
  Fieldset,
  Group,
  Paper,
  Stack,
  Text,
  Title,
  rem,
  useMantineTheme,
} from '@mantine/core'
import { useLocalStorage } from '@mantine/hooks'
import {
  IconBolt,
  IconNotification,
  IconReport,
  IconTrash,
} from '@tabler/icons-react'
import { useQueryClient } from '@tanstack/react-query'
import { useContext } from 'react'

export const ApplicationSettings = () => {
  // const { user } = useUser()
  // Use shared gate to check visibility to reduce duplicate logic
  const TeamsGate = ({ children }: { children: React.ReactNode }) => (
    <RequiresUserType requiredUserType="admin" silent>
      {children}
    </RequiresUserType>
  )
  return (
    <Stack p="md">
      <Title order={1}>Application Settings</Title>
      <TeamsGate>
        <AdminTeams />
      </TeamsGate>
      <Subscriptions />
      <PersonalPortfolio />
      <Tips />
      <GISColors />
    </Stack>
  )
}

function Subscriptions() {
  const projects = useGetProjects({ personalPortfolio: false })
  const subscriptions = useGetSubscriptions({})
  const notificationMutation = useUpdateNotificationSubscription()
  const reportMutation = useUpdateReportSubscription()

  const handleNotificationSubscriptionChange = (
    value: boolean,
    project_id: string,
  ) => {
    notificationMutation.mutate({ project_id, subscribe: value })
  }

  const handleReportSubscriptionChange = (
    value: boolean,
    project_id: string,
  ) => {
    reportMutation.mutate({ project_id, subscribe: value })
  }

  // Get array of project IDs for which the user is subscribed to notifications
  const notificationSubscriptions = subscriptions.data
    ?.filter((sub) => sub.notifications)
    .map((sub) => sub.operational_project_id)

  // Get array of project IDs for which the user is subscribed to reports
  const reportSubscriptions = subscriptions.data
    ?.filter((sub) => sub.reports)
    .map((sub) => sub.operational_project_id)

  return (
    <>
      <Title order={2}>Subscriptions</Title>
      <Text>
        Subscriptions allow you to receive emails for notifications and reports.
        You can change your subscription settings by clicking the checkboxes
        below.
      </Text>
      <Accordion multiple={true} variant="separated">
        <Accordion.Item value={'Notifications'}>
          <Accordion.Control
            icon={
              <IconNotification
                style={{
                  width: rem(20),
                  height: rem(20),
                }}
              />
            }
            disabled={!projects.data || !notificationSubscriptions}
          >
            Notifications
          </Accordion.Control>
          <Accordion.Panel>
            <Stack gap="xs">
              {notificationSubscriptions &&
                projects.data
                  ?.sort((a, b) => a.name_long.localeCompare(b.name_long))
                  .map((project) => (
                    <Checkbox
                      key={project.project_id}
                      value={project.project_id}
                      label={project.name_long}
                      checked={notificationSubscriptions.includes(
                        project.project_id,
                      )}
                      onChange={(value) =>
                        handleNotificationSubscriptionChange(
                          value.currentTarget.checked,
                          project.project_id,
                        )
                      }
                    />
                  ))}
            </Stack>
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
            disabled={!projects.data || !notificationSubscriptions}
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
      <Accordion multiple={true} variant="separated">
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
