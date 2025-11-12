import {
  useDeleteUserDashboard,
  useGetUserDashboards,
} from '@/api/v1/operational/project/custom_dash'
import { useSelectProject } from '@/api/v1/operational/projects'
import { NoData, PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import {
  ActionIcon,
  Button,
  Divider,
  Group,
  Modal,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconCopy, IconPlus, IconShare, IconTrash } from '@tabler/icons-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'

const ACTION_ICON_PROPS = {
  size: 'lg',
  variant: 'light',
}

const ICON_PROPS = {
  width: '70%',
  height: '70%',
  stroke: 1.5,
}

const CustomDashMenu = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const [opened, { open, close }] = useDisclosure(false)
  const [dashboardToDelete, setDashboardToDelete] = useState<{
    id: string
    name: string
  } | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const project = useSelectProject(projectId!)

  const userDashboards = useGetUserDashboards({
    pathParams: {
      projectId: projectId || '',
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  const deleteUserDashboardMutation = useDeleteUserDashboard()

  const handleDeleteClick = (dashboardId: string, dashboardName: string) => {
    setDashboardToDelete({ id: dashboardId, name: dashboardName })
    open()
  }

  const handleConfirmDelete = async () => {
    if (!dashboardToDelete || !projectId) return

    try {
      setDeletingId(dashboardToDelete.id)
      await deleteUserDashboardMutation.mutateAsync({
        project_id: projectId,
        dashboard_id: dashboardToDelete.id,
      })
      close()
      setDashboardToDelete(null)
    } catch (error) {
      console.error('Failed to delete dashboard:', error)
    } finally {
      setDeletingId(null)
    }
  }

  if (userDashboards.isLoading || project.isLoading) {
    return <PageLoader />
  }

  if (userDashboards.error) {
    return <PageError error={userDashboards.error} />
  }
  if (project.error) {
    return <PageError error={project.error} />
  }

  if (!userDashboards.data || !project.data) {
    return <NoData />
  }

  const disabledProjects = ['sun_streams_3', 'lancaster', 'snipesville_2']
  const isDisabled =
    project.data && disabledProjects.includes(project.data.name_short)

  return (
    <Stack p="md" h="100%">
      <Group justify="space-between">
        <PageTitle>Custom Dashboards</PageTitle>

        {/* If the project is not disabled, show the new dashboard button */}
        {!isDisabled && (
          <Link to={`/projects/${projectId}/custom-dash/new`}>
            <Button
              style={{ cursor: isDisabled ? 'not-allowed' : 'pointer' }}
              leftSection={<IconPlus size={14} />}
            >
              New Dashboard
            </Button>
          </Link>
        )}
      </Group>

      {isDisabled ? (
        // If the project is disabled, show the disabled message
        <Text>
          Custom dashboards are not enabled for this project. Please request
          custom dashboards using the feedback button in the bottom left hand
          corner of the screen.
        </Text>
      ) : userDashboards.data.length === 0 ? (
        // If the project is not disabled and the user has no dashboards, show the no dashboards message
        <Text>
          You don&apos;t have any Custom Dashboards yet. Click the New Dashboard
          button above to get started!
        </Text>
      ) : (
        // If the project is not disabled and the user has dashboards, show the dashboards
        [...userDashboards.data]
          .sort((a, b) => a.dashboard_name.localeCompare(b.dashboard_name))
          .map((dashboard) => (
            <Group
              key={dashboard.dashboard_id}
              justify="space-between"
              align="center"
            >
              <Link
                to={`/projects/${projectId}/custom-dash/${dashboard.dashboard_id}`}
                style={{ color: 'inherit' }}
              >
                <Text size="lg">{dashboard.dashboard_name}</Text>
              </Link>
              <Divider variant="dashed" flex={1} />

              {/* Delete dashboard */}
              <Tooltip label="Delete">
                <ActionIcon
                  {...ACTION_ICON_PROPS}
                  color="red"
                  onClick={() =>
                    handleDeleteClick(
                      dashboard.dashboard_id,
                      dashboard.dashboard_name,
                    )
                  }
                  loading={deletingId === dashboard.dashboard_id}
                  disabled={
                    Boolean(deletingId) && deletingId !== dashboard.dashboard_id
                  }
                >
                  <IconTrash {...ICON_PROPS} />
                </ActionIcon>
              </Tooltip>

              {/* Share dashboard */}
              <Tooltip label="Share coming soon!">
                <ActionIcon {...ACTION_ICON_PROPS} color="blue" disabled>
                  <IconShare {...ICON_PROPS} />
                </ActionIcon>
              </Tooltip>

              {/* Duplicate dashboard */}
              <Tooltip label="Duplicate coming soon!">
                <ActionIcon {...ACTION_ICON_PROPS} color="gray" disabled>
                  <IconCopy {...ICON_PROPS} />
                </ActionIcon>
              </Tooltip>
            </Group>
          ))
      )}

      {/* Delete Dashboard Modal */}
      <Modal opened={opened} onClose={close} title="Delete Dashboard" centered>
        <Stack>
          <Text>
            Are you sure you want to delete the dashboard &quot;
            {dashboardToDelete?.name}&quot;? This action cannot be undone.
          </Text>
          <Group justify="flex-end">
            <Button variant="outline" onClick={close}>
              Cancel
            </Button>
            <Button
              color="red"
              onClick={handleConfirmDelete}
              loading={deleteUserDashboardMutation.isPending}
            >
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}

export default CustomDashMenu
