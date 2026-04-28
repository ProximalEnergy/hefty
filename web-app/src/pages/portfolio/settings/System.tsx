import {
  useGetProjectSystemFileStatus,
  useImportProjectSystem,
} from '@/api/v1/commissioning/system'
import { useGetProjects, useUpdateProject } from '@/api/v1/operational/projects'
import { PageTitle } from '@/components/PageTitle'
import {
  Anchor,
  Button,
  Container,
  Group,
  Paper,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import {
  IconArrowUpToArc,
  IconCheck,
  IconDeviceFloppy,
  IconX,
} from '@tabler/icons-react'
import axios from 'axios'
import { type ChangeEvent, useMemo, useState } from 'react'

const System = () => {
  const projectsQuery = useGetProjects({
    queryParams: { deep: true },
    personalPortfolio: false,
  })
  const updateProject = useUpdateProject()
  const importProjectSystem = useImportProjectSystem()

  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
    null,
  )
  const [googleSheetDrafts, setGoogleSheetDrafts] = useState<
    Record<string, string>
  >({})
  const systemFileStatus = useGetProjectSystemFileStatus({
    pathParams: { projectId: selectedProjectId ?? '' },
    queryOptions: { enabled: !!selectedProjectId },
  })

  const projectOptions = useMemo(() => {
    if (!projectsQuery.data) {
      return []
    }

    return projectsQuery.data
      .slice()
      .sort((a, b) => a.name_long.localeCompare(b.name_long))
      .map((project) => ({
        value: project.project_id,
        label: project.name_long,
      }))
  }, [projectsQuery.data])

  const selectedProject = useMemo(() => {
    if (!selectedProjectId || !projectsQuery.data) {
      return null
    }

    return projectsQuery.data.find(
      (item) => item.project_id === selectedProjectId,
    )
  }, [selectedProjectId, projectsQuery.data])

  const googleSheetId = selectedProjectId
    ? (googleSheetDrafts[selectedProjectId] ?? selectedProject?.gsheet_id ?? '')
    : ''
  const normalizedGoogleSheetId = googleSheetId.trim()
  const googleSheetUrl =
    normalizedGoogleSheetId.length > 0
      ? `https://docs.google.com/spreadsheets/d/${normalizedGoogleSheetId}`
      : null

  const isSaveDisabled =
    !selectedProjectId ||
    updateProject.isPending ||
    projectsQuery.isLoading ||
    googleSheetId === (selectedProject?.gsheet_id ?? '')
  const isImportDisabled =
    !selectedProjectId ||
    updateProject.isPending ||
    importProjectSystem.isPending ||
    projectsQuery.isLoading

  const handlePortfolioSystemSave = () => {
    if (!selectedProjectId) {
      return
    }

    updateProject.mutate(
      {
        projectId: selectedProjectId,
        projectData: {
          gsheet_id:
            normalizedGoogleSheetId.length > 0 ? normalizedGoogleSheetId : null,
        },
      },
      {
        onSuccess: () => {
          setGoogleSheetDrafts((prev) => ({
            ...prev,
            [selectedProjectId]: normalizedGoogleSheetId,
          }))
          notifications.show({
            title: 'Saved',
            message: 'Google Sheet ID was updated for this project.',
            color: 'green',
            icon: <IconCheck size={16} />,
          })
        },
        onError: (error) => {
          notifications.show({
            title: 'Save failed',
            message: error.message || 'Unable to update Google Sheet ID.',
            color: 'red',
            icon: <IconX size={16} />,
          })
        },
      },
    )
  }

  const handleImportSystem = async () => {
    if (!selectedProjectId) {
      return
    }

    const savedGoogleSheetId = (selectedProject?.gsheet_id ?? '').trim()

    if (normalizedGoogleSheetId !== savedGoogleSheetId) {
      try {
        await updateProject.mutateAsync({
          projectId: selectedProjectId,
          projectData: {
            gsheet_id:
              normalizedGoogleSheetId.length > 0
                ? normalizedGoogleSheetId
                : null,
          },
        })
        setGoogleSheetDrafts((prev) => ({
          ...prev,
          [selectedProjectId]: normalizedGoogleSheetId,
        }))
      } catch (error) {
        notifications.show({
          title: 'Import failed',
          message:
            error instanceof Error
              ? error.message
              : 'Unable to save Google Sheet ID before importing.',
          color: 'red',
          icon: <IconX size={16} />,
        })
        return
      }
    }

    importProjectSystem.mutate(
      { projectId: selectedProjectId },
      {
        onSuccess: () => {
          void systemFileStatus.refetch()
          notifications.show({
            title: 'System import started',
            message: 'Requested system S3 file update for this project.',
            color: 'green',
            icon: <IconCheck size={16} />,
          })
        },
        onError: (error: unknown) => {
          let errorMessage = 'Unable to update the system S3 file.'

          if (axios.isAxiosError(error)) {
            const detail = error.response?.data?.detail
            if (typeof detail === 'string' && detail.trim().length > 0) {
              errorMessage = detail
            } else if (Array.isArray(detail)) {
              errorMessage = detail
                .map((item) => {
                  if (typeof item === 'string') return item
                  if (item && typeof item === 'object') {
                    return item.msg || item.message
                  }
                  return null
                })
                .filter(Boolean)
                .join('; ')
            } else if (typeof error.message === 'string') {
              errorMessage = error.message
            }
          } else if (error instanceof Error) {
            errorMessage = error.message
          }

          notifications.show({
            title: 'Import failed',
            message: errorMessage,
            color: 'red',
            icon: <IconX size={16} />,
          })
        },
      },
    )
  }

  const handleGoogleSheetIdChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (!selectedProjectId) {
      return
    }

    const nextValue = event.currentTarget.value
    setGoogleSheetDrafts((prev) => ({
      ...prev,
      [selectedProjectId]: nextValue,
    }))
  }

  return (
    <Container size="lg" p="md" style={{ width: '100%' }}>
      <Paper withBorder p="md" radius="md">
        <Stack>
          <PageTitle
            info={
              <Stack>
                <Text>
                  This page allows you to manage project-level Google Sheet IDs
                  used by commissioning system import.
                </Text>
              </Stack>
            }
          >
            System
          </PageTitle>

          <Text c="dimmed" size="sm" mb="md">
            Select a project, review its current Google Sheet ID, and update it
            if needed.
          </Text>

          <Select
            label="Project"
            placeholder="Select project"
            searchable
            clearable
            data={projectOptions}
            value={selectedProjectId}
            onChange={setSelectedProjectId}
            disabled={projectsQuery.isLoading}
            nothingFoundMessage="No projects found"
          />

          <TextInput
            label="Google Sheet ID"
            placeholder="Enter Google Sheet ID"
            value={googleSheetId}
            onChange={handleGoogleSheetIdChange}
            disabled={!selectedProjectId}
          />
          {googleSheetUrl && (
            <Text size="xs">
              Google Sheet:{' '}
              <Anchor href={googleSheetUrl} target="_blank" rel="noreferrer">
                Open sheet
              </Anchor>
            </Text>
          )}

          {selectedProjectId && (
            <Stack gap={4}>
              <Text c="dimmed" size="xs">
                Target S3 key: {systemFileStatus.data?.file_key ?? 'Unknown'}
              </Text>
              {systemFileStatus.isLoading && (
                <Text c="dimmed" size="xs">
                  Checking whether target S3 file already exists...
                </Text>
              )}
              {systemFileStatus.isError && (
                <Text c="red" size="xs">
                  Unable to check if target S3 file exists.
                </Text>
              )}
              {!systemFileStatus.isLoading &&
                !systemFileStatus.isError &&
                systemFileStatus.data && (
                  <Text
                    c={systemFileStatus.data.exists ? 'orange' : 'teal'}
                    size="xs"
                  >
                    {systemFileStatus.data.exists
                      ? 'Target S3 file already exists.'
                      : 'Target S3 file does not exist yet.'}
                  </Text>
                )}
            </Stack>
          )}

          <Group style={{ justifyContent: 'flex-end' }} mt="md">
            <Button
              variant="light"
              leftSection={<IconArrowUpToArc size={16} />}
              onClick={handleImportSystem}
              loading={importProjectSystem.isPending}
              disabled={isImportDisabled}
            >
              Update System S3 File
            </Button>
            <Button
              leftSection={<IconDeviceFloppy size={16} />}
              onClick={handlePortfolioSystemSave}
              loading={updateProject.isPending}
              disabled={isSaveDisabled}
            >
              Save Google Sheet ID
            </Button>
          </Group>
        </Stack>
      </Paper>
    </Container>
  )
}

export default System
