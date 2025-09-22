import {
  DroneIntegration,
  useCreateDroneIntegration,
  useDeleteDroneIntegration,
  useGetDroneIntegrations,
  useGetDroneProviders,
  useUpdateDroneIntegration,
} from '@/api/v1/operational/drone_integrations'
import { useGetProjects } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import {
  ActionIcon,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { useDisclosure } from '@mantine/hooks'
import { IconPencil, IconTrash } from '@tabler/icons-react'
import React, { useState } from 'react'

const DroneIntegrations: React.FC = () => {
  const { data: integrations, isLoading: integrationsLoading } =
    useGetDroneIntegrations()
  const { data: projects, isLoading: projectsLoading } = useGetProjects({
    personalPortfolio: false,
  })
  const { data: providers, isLoading: providersLoading } =
    useGetDroneProviders()
  const createDroneIntegration = useCreateDroneIntegration()
  const updateDroneIntegration = useUpdateDroneIntegration()
  const deleteDroneIntegration = useDeleteDroneIntegration()
  const [isModalOpen, { open, close }] = useDisclosure(false)
  const [isEditModalOpen, { open: openEdit, close: closeEdit }] =
    useDisclosure(false)
  const [isDeleteModalOpen, { open: openDelete, close: closeDelete }] =
    useDisclosure(false)
  const [selectedIntegration, setSelectedIntegration] =
    useState<DroneIntegration | null>(null)

  const projectMap = React.useMemo(() => {
    if (!projects) return new Map<string, string>()
    return new Map(projects.map((p) => [p.project_id, p.name_long]))
  }, [projects])

  const providerMap = React.useMemo(() => {
    if (!providers) return new Map<number, string>()
    return new Map(providers.map((p) => [p.drone_provider_id, p.name_long]))
  }, [providers])

  const form = useForm({
    initialValues: {
      drone_integration_id: 0,
      project_id: '',
      drone_provider_id: '',
      provider_project_id: '',
    },
  })

  const editForm = useForm({
    initialValues: {
      drone_integration_id: 0,
      project_id: '',
      drone_provider_id: '',
      provider_project_id: '',
    },
  })

  const handleOpenModal = () => {
    const nextId =
      integrations && integrations.length > 0
        ? Math.max(...integrations.map((i) => i.drone_integration_id)) + 1
        : 1
    form.setValues({
      drone_integration_id: nextId,
      project_id: '',
      drone_provider_id: '',
      provider_project_id: '',
    })
    open()
  }

  const handleOpenEditModal = (integration: DroneIntegration) => {
    setSelectedIntegration(integration)
    editForm.setValues({
      ...integration,
      drone_provider_id: String(integration.drone_provider_id),
    })
    openEdit()
  }

  const handleOpenDeleteModal = (integration: DroneIntegration) => {
    setSelectedIntegration(integration)
    openDelete()
  }

  const handleSubmit = form.onSubmit(async (values) => {
    await createDroneIntegration.mutateAsync({
      ...values,
      drone_provider_id: Number(values.drone_provider_id),
    })
    form.reset()
    close()
  })

  const handleEditSubmit = editForm.onSubmit(async (values) => {
    await updateDroneIntegration.mutateAsync({
      ...values,
      drone_provider_id: Number(values.drone_provider_id),
    })
    closeEdit()
  })

  const handleDeleteSubmit = async () => {
    if (selectedIntegration) {
      await deleteDroneIntegration.mutateAsync(
        selectedIntegration.drone_integration_id,
      )
      closeDelete()
      closeEdit()
    }
  }

  if (integrationsLoading || projectsLoading || providersLoading) {
    return <PageLoader />
  }

  return (
    <Stack p="md">
      <Title order={1}>Drone Integrations</Title>
      {integrations && integrations.length > 0 ? (
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Integration ID</Table.Th>
              <Table.Th>Project</Table.Th>
              <Table.Th>Provider</Table.Th>
              <Table.Th>Provider Project ID</Table.Th>
              <Table.Th>Edit</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {integrations.map((integration) => (
              <Table.Tr key={integration.drone_integration_id}>
                <Table.Td>{integration.drone_integration_id}</Table.Td>
                <Table.Td>
                  {projectMap.get(integration.project_id)} (
                  {integration.project_id})
                </Table.Td>
                <Table.Td>
                  {providerMap.get(integration.drone_provider_id)} (
                  {integration.drone_provider_id})
                </Table.Td>
                <Table.Td>{integration.provider_project_id}</Table.Td>
                <Table.Td>
                  <ActionIcon onClick={() => handleOpenEditModal(integration)}>
                    <IconPencil />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : (
        <Text>No drone integrations found.</Text>
      )}
      <Button onClick={handleOpenModal}>Add Integration</Button>
      <Modal opened={isModalOpen} onClose={close} title="Add Drone Integration">
        <form onSubmit={handleSubmit}>
          <Stack>
            <TextInput
              label="Integration ID"
              {...form.getInputProps('drone_integration_id')}
              type="number"
              disabled
            />
            <Select
              label="Project"
              placeholder="Select a project"
              data={
                projects?.map((project) => ({
                  value: project.project_id,
                  label: `${project.name_long} - ${project.project_id}`,
                })) || []
              }
              {...form.getInputProps('project_id')}
            />
            <Select
              label="Provider"
              placeholder="Select a provider"
              data={
                providers?.map((provider) => ({
                  value: String(provider.drone_provider_id),
                  label: provider.name_long,
                })) || []
              }
              {...form.getInputProps('drone_provider_id')}
            />
            <TextInput
              label="Provider Project ID"
              {...form.getInputProps('provider_project_id')}
            />
            <Button type="submit" loading={createDroneIntegration.isPending}>
              Add Integration
            </Button>
          </Stack>
        </form>
      </Modal>
      <Modal
        opened={isEditModalOpen}
        onClose={closeEdit}
        title="Edit Drone Integration"
      >
        <form onSubmit={handleEditSubmit}>
          <Stack>
            <Select
              label="Project"
              placeholder="Select a project"
              data={
                projects?.map((project) => ({
                  value: project.project_id,
                  label: `${project.name_long} - ${project.project_id}`,
                })) || []
              }
              {...editForm.getInputProps('project_id')}
            />
            <Select
              label="Provider"
              placeholder="Select a provider"
              data={
                providers?.map((provider) => ({
                  value: String(provider.drone_provider_id),
                  label: provider.name_long,
                })) || []
              }
              {...editForm.getInputProps('drone_provider_id')}
            />
            <TextInput
              label="Provider Project ID"
              {...editForm.getInputProps('provider_project_id')}
            />
            <Group justify="space-between">
              <Button
                color="red"
                onClick={() => handleOpenDeleteModal(selectedIntegration!)}
              >
                <IconTrash />
              </Button>
              <Button type="submit" loading={updateDroneIntegration.isPending}>
                Update Integration
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
      <Modal
        opened={isDeleteModalOpen}
        onClose={closeDelete}
        title="Confirm Delete"
      >
        <Stack>
          <Text>
            Are you sure you want to delete this integration? This action cannot
            be undone.
          </Text>
          <Group justify="flex-end">
            <Button variant="outline" onClick={closeDelete}>
              Cancel
            </Button>
            <Button
              color="red"
              onClick={handleDeleteSubmit}
              loading={deleteDroneIntegration.isPending}
            >
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}

export default DroneIntegrations
