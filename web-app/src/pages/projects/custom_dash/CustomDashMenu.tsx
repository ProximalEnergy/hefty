import { useGetUserSelf } from '@/api/admin'
import { useGetCompanyUsers } from '@/api/operational'
import {
  useDeleteUserDashboard,
  useDuplicateUserDashboard,
  useGetDashboardSharedUsers,
  useGetSharedUserDashboards,
  useGetUserDashboards,
  useShareUserDashboard,
  useUnshareUserDashboard,
} from '@/api/v1/operational/project/custom_dash'
import { useGetProjects, useSelectProject } from '@/api/v1/operational/projects'
import { NoData, PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import {
  ActionIcon,
  Button,
  Checkbox,
  Divider,
  Group,
  Modal,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconCopy, IconPlus, IconShare, IconTrash } from '@tabler/icons-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

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
  const navigate = useNavigate()
  const [deleteOpened, { open: openDelete, close: closeDelete }] =
    useDisclosure(false)
  const [duplicateOpened, { open: openDuplicate, close: closeDuplicate }] =
    useDisclosure(false)
  const [shareOpened, { open: openShare, close: closeShare }] =
    useDisclosure(false)
  const [dashboardToDelete, setDashboardToDelete] = useState<{
    id: string
    name: string
  } | null>(null)
  const [dashboardToDuplicate, setDashboardToDuplicate] = useState<{
    id: string
    name: string
  } | null>(null)
  const [dashboardToShare, setDashboardToShare] = useState<{
    id: string
    name: string
  } | null>(null)
  const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>([])
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([])
  const [duplicateToAll, setDuplicateToAll] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [duplicatingId, setDuplicatingId] = useState<string | null>(null)
  const [sharingUserId, setSharingUserId] = useState<string | null>(null)

  const project = useSelectProject(projectId!)

  const userDashboards = useGetUserDashboards({
    pathParams: {
      projectId: projectId || '',
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })
  const sharedUserDashboards = useGetSharedUserDashboards({
    pathParams: {
      projectId: projectId || '',
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })
  const currentUser = useGetUserSelf({
    queryOptions: {
      enabled: shareOpened,
    },
  })
  const companyUsers = useGetCompanyUsers({
    queryOptions: {
      enabled: shareOpened,
    },
  })
  const dashboardSharedUsers = useGetDashboardSharedUsers({
    pathParams: {
      projectId: projectId || '',
      dashboardId: dashboardToShare?.id || '',
    },
    queryOptions: {
      enabled: shareOpened && !!dashboardToShare?.id && !!projectId,
    },
  })

  // Initialize selectedUserIds with already shared users when modal opens
  useEffect(() => {
    if (
      shareOpened &&
      dashboardSharedUsers.data?.shared_user_ids &&
      dashboardSharedUsers.data.shared_user_ids.length > 0
    ) {
      setSelectedUserIds(dashboardSharedUsers.data.shared_user_ids)
    } else if (shareOpened && !dashboardSharedUsers.isLoading) {
      // Reset if no shared users or data is loaded
      setSelectedUserIds([])
    }
  }, [
    shareOpened,
    dashboardSharedUsers.data?.shared_user_ids,
    dashboardSharedUsers.isLoading,
  ])
  const projects = useGetProjects({
    queryOptions: {
      enabled: duplicateOpened,
    },
  })

  const deleteUserDashboardMutation = useDeleteUserDashboard()
  const duplicateUserDashboardMutation = useDuplicateUserDashboard()
  const shareUserDashboardMutation = useShareUserDashboard()
  const unshareUserDashboardMutation = useUnshareUserDashboard()

  const handleDuplicateClick = (dashboardId: string, dashboardName: string) => {
    setDashboardToDuplicate({ id: dashboardId, name: dashboardName })
    // Reset selections when opening modal
    setSelectedProjectIds([])
    setDuplicateToAll(false)
    openDuplicate()
  }

  const handleDeleteClick = (dashboardId: string, dashboardName: string) => {
    setDashboardToDelete({ id: dashboardId, name: dashboardName })
    openDelete()
  }

  const handleShareClick = (dashboardId: string, dashboardName: string) => {
    setDashboardToShare({ id: dashboardId, name: dashboardName })
    openShare()
  }

  const handleConfirmDuplicate = async () => {
    if (!dashboardToDuplicate || !projectId) return

    // Determine which project IDs to duplicate to
    const projectIdsToDuplicate =
      duplicateToAll && projects.data
        ? projects.data.map((p) => p.project_id)
        : selectedProjectIds.length > 0
          ? selectedProjectIds
          : [projectId] // Default to current project if nothing selected

    if (projectIdsToDuplicate.length === 0) {
      return
    }

    try {
      setDuplicatingId(dashboardToDuplicate.id)
      const response = await duplicateUserDashboardMutation.mutateAsync({
        project_id: projectId, // Original project ID for fetching the dashboard
        dashboard_id: dashboardToDuplicate.id,
        target_project_ids: projectIdsToDuplicate,
      })
      closeDuplicate()
      setDashboardToDuplicate(null)
      setSelectedProjectIds([])
      setDuplicateToAll(false)
      // Navigate to the first duplicated dashboard (or current project if only one)
      const firstProjectId = projectIdsToDuplicate[0] || projectId
      const newDashboardId =
        response.data.dashboard_ids?.[0] || response.data.dashboard_id
      if (newDashboardId) {
        navigate(`/projects/${firstProjectId}/custom-dash/${newDashboardId}`)
      }
    } catch (error) {
      console.error('Failed to duplicate dashboard:', error)
    } finally {
      setDuplicatingId(null)
    }
  }

  // Handle "Duplicate to all" checkbox
  const handleDuplicateToAllChange = (checked: boolean) => {
    setDuplicateToAll(checked)
    if (checked && projects.data) {
      // Auto-select all projects
      setSelectedProjectIds(projects.data.map((p) => p.project_id))
    } else {
      // Clear selections
      setSelectedProjectIds([])
    }
  }

  // Handle individual project checkbox
  const handleProjectToggle = (projectId: string, checked: boolean) => {
    if (checked) {
      setSelectedProjectIds((prev) => [...prev, projectId])
    } else {
      setSelectedProjectIds((prev) => prev.filter((id) => id !== projectId))
      // If unchecking a project, uncheck "Duplicate to all"
      if (duplicateToAll) {
        setDuplicateToAll(false)
      }
    }
  }

  const handleConfirmDelete = async () => {
    if (!dashboardToDelete || !projectId) return

    try {
      setDeletingId(dashboardToDelete.id)
      await deleteUserDashboardMutation.mutateAsync({
        project_id: projectId,
        dashboard_id: dashboardToDelete.id,
      })
      closeDelete()
      setDashboardToDelete(null)
    } catch (error) {
      console.error('Failed to delete dashboard:', error)
    } finally {
      setDeletingId(null)
    }
  }

  const handleUserToggle = (userId: string, checked: boolean) => {
    if (checked) {
      setSelectedUserIds((prev) => [...prev, userId])
    } else {
      setSelectedUserIds((prev) => prev.filter((id) => id !== userId))
    }
  }

  const handleConfirmShare = async () => {
    if (!dashboardToShare || !projectId) return

    const alreadySharedUserIds =
      dashboardSharedUsers.data?.shared_user_ids || []
    const selectedUserIdsSet = new Set(selectedUserIds)

    // Determine which users to share (selected but not already shared)
    const usersToShare = selectedUserIds.filter(
      (userId) => !alreadySharedUserIds.includes(userId),
    )

    // Determine which users to unshare (already shared but not selected)
    const usersToUnshare = alreadySharedUserIds.filter(
      (userId) => !selectedUserIdsSet.has(userId),
    )

    if (usersToShare.length === 0 && usersToUnshare.length === 0) {
      // No changes, just close
      closeShare()
      setDashboardToShare(null)
      setSelectedUserIds([])
      return
    }

    try {
      // Share with new users
      for (const userId of usersToShare) {
        setSharingUserId(userId)
        try {
          await shareUserDashboardMutation.mutateAsync({
            project_id: projectId,
            dashboard_id: dashboardToShare.id,
            shared_user_id: userId,
          })
        } catch (error) {
          console.error(`Failed to share dashboard with user ${userId}:`, error)
          // Continue with other users even if one fails
        } finally {
          setSharingUserId(null)
        }
      }

      // Unshare with removed users
      for (const userId of usersToUnshare) {
        setSharingUserId(userId)
        try {
          await unshareUserDashboardMutation.mutateAsync({
            project_id: projectId,
            dashboard_id: dashboardToShare.id,
            shared_user_id: userId,
          })
        } catch (error) {
          console.error(
            `Failed to unshare dashboard with user ${userId}:`,
            error,
          )
          // Continue with other users even if one fails
        } finally {
          setSharingUserId(null)
        }
      }

      closeShare()
      setDashboardToShare(null)
      setSelectedUserIds([])
    } catch (error) {
      console.error('Failed to update dashboard sharing:', error)
    }
  }

  if (
    userDashboards.isLoading ||
    sharedUserDashboards.isLoading ||
    project.isLoading
  ) {
    return <PageLoader />
  }

  if (userDashboards.error) {
    return <PageError error={userDashboards.error} />
  }
  if (sharedUserDashboards.error) {
    return <PageError error={sharedUserDashboards.error} />
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
      ) : userDashboards.data.length === 0 &&
        (!sharedUserDashboards.data ||
          sharedUserDashboards.data.length === 0) ? (
        // If the project is not disabled and the user has no dashboards and no shared dashboards, show the no dashboards message
        <Text>
          You don&apos;t have any Custom Dashboards yet. Click the New Dashboard
          button above to get started!
        </Text>
      ) : (
        <Stack gap="md">
          {/* User's own dashboards */}
          {userDashboards.data.length > 0 &&
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
                        Boolean(deletingId) &&
                        deletingId !== dashboard.dashboard_id
                      }
                    >
                      <IconTrash {...ICON_PROPS} />
                    </ActionIcon>
                  </Tooltip>

                  {/* Share dashboard */}
                  <Tooltip label="Share">
                    <ActionIcon
                      {...ACTION_ICON_PROPS}
                      color="blue"
                      onClick={() =>
                        handleShareClick(
                          dashboard.dashboard_id,
                          dashboard.dashboard_name,
                        )
                      }
                      disabled={
                        (Boolean(deletingId) &&
                          deletingId !== dashboard.dashboard_id) ||
                        (Boolean(duplicatingId) &&
                          duplicatingId !== dashboard.dashboard_id)
                      }
                    >
                      <IconShare {...ICON_PROPS} />
                    </ActionIcon>
                  </Tooltip>

                  {/* Duplicate dashboard */}
                  <Tooltip label="Duplicate">
                    <ActionIcon
                      {...ACTION_ICON_PROPS}
                      color="gray"
                      onClick={() =>
                        handleDuplicateClick(
                          dashboard.dashboard_id,
                          dashboard.dashboard_name,
                        )
                      }
                      loading={duplicatingId === dashboard.dashboard_id}
                      disabled={
                        (Boolean(deletingId) &&
                          deletingId !== dashboard.dashboard_id) ||
                        (Boolean(duplicatingId) &&
                          duplicatingId !== dashboard.dashboard_id)
                      }
                    >
                      <IconCopy {...ICON_PROPS} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              ))}

          {/* Shared dashboards */}
          {sharedUserDashboards.data &&
            sharedUserDashboards.data.length > 0 && (
              <>
                {userDashboards.data.length > 0 && (
                  <Divider
                    label={
                      <Text size="sm" c="dimmed">
                        Shared with me
                      </Text>
                    }
                    labelPosition="left"
                    my="md"
                  />
                )}
                {[...sharedUserDashboards.data]
                  .sort((a, b) =>
                    a.dashboard_name.localeCompare(b.dashboard_name),
                  )
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

                      {/* Duplicate dashboard (shared dashboards can be duplicated) */}
                      <Tooltip label="Duplicate">
                        <ActionIcon
                          {...ACTION_ICON_PROPS}
                          color="gray"
                          onClick={() =>
                            handleDuplicateClick(
                              dashboard.dashboard_id,
                              dashboard.dashboard_name,
                            )
                          }
                          loading={duplicatingId === dashboard.dashboard_id}
                          disabled={
                            Boolean(duplicatingId) &&
                            duplicatingId !== dashboard.dashboard_id
                          }
                        >
                          <IconCopy {...ICON_PROPS} />
                        </ActionIcon>
                      </Tooltip>
                    </Group>
                  ))}
              </>
            )}
        </Stack>
      )}

      {/* Delete Dashboard Modal */}
      <Modal
        opened={deleteOpened}
        onClose={closeDelete}
        title="Delete Dashboard"
        centered
      >
        <Stack>
          <Text>
            Are you sure you want to delete the dashboard &quot;
            {dashboardToDelete?.name}&quot;? This action cannot be undone.
          </Text>
          <Group justify="flex-end">
            <Button variant="outline" onClick={closeDelete}>
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

      {/* Share Dashboard Modal */}
      <Modal
        opened={shareOpened}
        onClose={() => {
          closeShare()
          setSelectedUserIds([])
          setDashboardToShare(null)
        }}
        title="Share Dashboard"
        centered
      >
        <Stack>
          <Text>
            Share the dashboard &quot;{dashboardToShare?.name}&quot; with other
            users in your company.
          </Text>
          {companyUsers.isLoading ||
          currentUser.isLoading ||
          dashboardSharedUsers.isLoading ? (
            <Text c="dimmed">Loading users...</Text>
          ) : companyUsers.data && companyUsers.data.length > 0 ? (
            <Stack gap="xs" style={{ maxHeight: '400px', overflow: 'auto' }}>
              {companyUsers.data
                .filter((user) => user.user_id !== currentUser.data?.user_id)
                .sort((a, b) => a.name_long.localeCompare(b.name_long))
                .map((user) => {
                  const isSelected = selectedUserIds.includes(user.user_id)
                  return (
                    <Checkbox
                      key={user.user_id}
                      label={user.name_long}
                      checked={isSelected}
                      onChange={(event) =>
                        handleUserToggle(
                          user.user_id,
                          event.currentTarget.checked,
                        )
                      }
                      disabled={
                        Boolean(sharingUserId) && sharingUserId !== user.user_id
                      }
                    />
                  )
                })}
            </Stack>
          ) : (
            <Text c="dimmed">No users available</Text>
          )}

          <Group justify="flex-end" mt="md">
            <Button
              variant="outline"
              onClick={() => {
                closeShare()
                setSelectedUserIds([])
                setDashboardToShare(null)
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirmShare}
              loading={
                shareUserDashboardMutation.isPending ||
                unshareUserDashboardMutation.isPending
              }
              disabled={
                shareUserDashboardMutation.isPending ||
                unshareUserDashboardMutation.isPending
              }
            >
              Save
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Duplicate Dashboard Modal */}
      <Modal
        opened={duplicateOpened}
        onClose={() => {
          closeDuplicate()
          setSelectedProjectIds([])
          setDuplicateToAll(false)
        }}
        title="Duplicate Dashboard"
        centered
        size="lg"
      >
        <Stack>
          <Text>
            Select the projects where you want to duplicate the dashboard &quot;
            {dashboardToDuplicate?.name}&quot;. A copy will be created with the
            name &quot;Copy of {dashboardToDuplicate?.name}&quot;. You will be
            the owner of the new dashboard(s).
          </Text>

          {projects.isLoading ? (
            <Text c="dimmed">Loading projects...</Text>
          ) : projects.data && projects.data.length > 0 ? (
            <Stack gap="sm">
              <Checkbox
                label="Duplicate to all projects"
                checked={duplicateToAll}
                onChange={(event) =>
                  handleDuplicateToAllChange(event.currentTarget.checked)
                }
              />
              <Divider />
              <Stack gap="xs" style={{ maxHeight: '400px', overflow: 'auto' }}>
                {projects.data
                  .sort((a, b) => a.name_long.localeCompare(b.name_long))
                  .map((project) => (
                    <Checkbox
                      key={project.project_id}
                      label={project.name_long}
                      checked={
                        duplicateToAll ||
                        selectedProjectIds.includes(project.project_id)
                      }
                      onChange={(event) =>
                        handleProjectToggle(
                          project.project_id,
                          event.currentTarget.checked,
                        )
                      }
                      disabled={duplicateToAll}
                    />
                  ))}
              </Stack>
            </Stack>
          ) : (
            <Text c="dimmed">No projects available</Text>
          )}

          <Group justify="flex-end" mt="md">
            <Button
              variant="outline"
              onClick={() => {
                closeDuplicate()
                setSelectedProjectIds([])
                setDuplicateToAll(false)
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirmDuplicate}
              loading={duplicateUserDashboardMutation.isPending}
              disabled={
                !duplicateToAll &&
                selectedProjectIds.length === 0 &&
                !projects.isLoading
              }
            >
              Duplicate
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}

export default CustomDashMenu
