import {
  useDeleteUserDashboard,
  useGetUserDashboards,
} from '@/api/v1/operational/project/custom_dash'
import { useSelectProject } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import {
  ActionIcon,
  Button,
  Group,
  Modal,
  Stack,
  Text,
  Title,
  Tooltip,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconCopy, IconPlus, IconShare, IconTrash } from '@tabler/icons-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'

const CustomDashMenu = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
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

  const disabledProjects = ['sun_streams_3', 'lancaster', 'snipesville_2']
  const isDisabled =
    project.data && disabledProjects.includes(project.data.name_short)

  return (
    <Stack p="md" h="100%">
      <Title>Custom Dashboards</Title>
      {userDashboards.data?.map((dashboard) => (
        <Group
          key={dashboard.dashboard_id}
          justify="space-between"
          align="center"
        >
          <Button onClick={() => navigate(dashboard.dashboard_id)} flex={1}>
            {dashboard.dashboard_name}
          </Button>

          <Group>
            <Tooltip label="Delete">
              <ActionIcon
                variant="light"
                color="red"
                onClick={() =>
                  handleDeleteClick(
                    dashboard.dashboard_id,
                    dashboard.dashboard_name,
                  )
                }
                loading={deletingId === dashboard.dashboard_id} // only this one spins
                disabled={
                  Boolean(deletingId) && deletingId !== dashboard.dashboard_id
                } // optional: lock others
              >
                <IconTrash size={16} />
              </ActionIcon>
            </Tooltip>

            <Tooltip label="Share coming soon!">
              <ActionIcon variant="light" color="blue" disabled>
                <IconShare size={16} />
              </ActionIcon>
            </Tooltip>

            <Tooltip label="Duplicate coming soon!">
              <ActionIcon variant="light" color="gray" disabled>
                <IconCopy size={16} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>
      ))}
      <Tooltip
        label="Custom dashboards are not enabled for this project. Please request custom dashboards using the feedback button in the bottom left hand corner of the screen."
        disabled={!isDisabled}
        multiline
        w={220}
        withArrow
      >
        <Button
          onClick={() => navigate('new')}
          disabled={isDisabled}
          style={{ cursor: isDisabled ? 'not-allowed' : 'pointer' }}
        >
          <IconPlus /> New Dashboard
        </Button>
      </Tooltip>

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
