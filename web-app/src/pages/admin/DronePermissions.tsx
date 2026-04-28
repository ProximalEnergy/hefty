import { useGetCompanies } from '@/api/v1/admin/companies'
import {
  DronePermission,
  useCreateDronePermission,
  useDeleteDronePermission,
  useGetDroneIntegrations,
  useGetDronePermissions,
  useGetDroneProviders,
  useUpdateDronePermission,
} from '@/api/v1/operational/drone_integrations'
import { useGetProjects } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import {
  ActionIcon,
  Button,
  Checkbox,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { useDisclosure } from '@mantine/hooks'
import { IconPencil, IconTrash } from '@tabler/icons-react'
import React, { useState } from 'react'

const DronePermissions: React.FC = () => {
  const { data: permissions, isLoading: permissionsLoading } =
    useGetDronePermissions()
  const { data: integrations, isLoading: integrationsLoading } =
    useGetDroneIntegrations()
  const { data: companies, isLoading: companiesLoading } = useGetCompanies()
  const { data: providers, isLoading: providersLoading } =
    useGetDroneProviders()
  const { data: projects, isLoading: projectsLoading } = useGetProjects({
    personalPortfolio: false,
  })

  const createDronePermission = useCreateDronePermission()
  const updateDronePermission = useUpdateDronePermission()
  const deleteDronePermission = useDeleteDronePermission()
  const [isModalOpen, { open, close }] = useDisclosure(false)
  const [isEditModalOpen, { open: openEdit, close: closeEdit }] =
    useDisclosure(false)
  const [isDeleteModalOpen, { open: openDelete, close: closeDelete }] =
    useDisclosure(false)
  const [selectedPermission, setSelectedPermission] =
    useState<DronePermission | null>(null)

  const projectMap = React.useMemo(() => {
    if (!projects) return new Map<string, string>()
    return new Map(projects.map((p) => [p.project_id, p.name_long]))
  }, [projects])

  const providerMap = React.useMemo(() => {
    if (!providers) return new Map<number, string>()
    return new Map(providers.map((p) => [p.drone_provider_id, p.name_long]))
  }, [providers])

  const companyMap = React.useMemo(() => {
    if (!companies) return new Map<string, string>()
    return new Map(companies.map((c) => [c.company_id, c.name_long]))
  }, [companies])

  const integrationMap = React.useMemo(() => {
    if (!integrations) return new Map()
    return new Map(integrations.map((i) => [i.drone_integration_id, i]))
  }, [integrations])

  const form = useForm({
    initialValues: {
      drone_integration_id: 0,
      company_id: '',
      can_view: false,
    },
  })

  const editForm = useForm({
    initialValues: {
      drone_integration_id: 0,
      company_id: '',
      can_view: false,
    },
  })

  const handleDronePermissionsOpenEditModal = (permission: DronePermission) => {
    setSelectedPermission(permission)
    editForm.setValues(permission)
    openEdit()
  }

  const handleDronePermissionsOpenDeleteModal = (
    permission: DronePermission,
  ) => {
    setSelectedPermission(permission)
    openDelete()
  }

  const handleSubmit = form.onSubmit(async (values) => {
    await createDronePermission.mutateAsync({
      ...values,
      drone_integration_id: Number(values.drone_integration_id),
    })
    form.reset()
    close()
  })

  const handleEditSubmit = editForm.onSubmit(async (values) => {
    await updateDronePermission.mutateAsync(values)
    closeEdit()
  })

  const handleDronePermissionsDeleteSubmit = async () => {
    if (selectedPermission) {
      await deleteDronePermission.mutateAsync(selectedPermission)
      closeDelete()
      closeEdit()
    }
  }

  if (
    permissionsLoading ||
    integrationsLoading ||
    companiesLoading ||
    providersLoading ||
    projectsLoading
  ) {
    return <PageLoader />
  }

  return (
    <Stack p="md">
      <Title order={1}>Drone Permissions</Title>
      {permissions && permissions.length > 0 ? (
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Integration</Table.Th>
              <Table.Th>Company</Table.Th>
              <Table.Th>Can View</Table.Th>
              <Table.Th>Edit</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {permissions.map((permission) => {
              const integration = integrationMap.get(
                permission.drone_integration_id,
              )
              const projectName = integration
                ? projectMap.get(integration.project_id)
                : 'N/A'
              const providerName = integration
                ? providerMap.get(integration.drone_provider_id)
                : 'N/A'
              const companyName = companyMap.get(permission.company_id)

              return (
                <Table.Tr
                  key={`${permission.drone_integration_id}-${permission.company_id}`}
                >
                  <Table.Td>
                    {projectName} - {providerName} (
                    {permission.drone_integration_id})
                  </Table.Td>
                  <Table.Td>
                    {companyName} ({permission.company_id})
                  </Table.Td>
                  <Table.Td>{permission.can_view.toString()}</Table.Td>
                  <Table.Td>
                    <ActionIcon
                      onClick={() =>
                        handleDronePermissionsOpenEditModal(permission)
                      }
                    >
                      <IconPencil />
                    </ActionIcon>
                  </Table.Td>
                </Table.Tr>
              )
            })}
          </Table.Tbody>
        </Table>
      ) : (
        <Text>No drone permissions found.</Text>
      )}
      <Button onClick={open}>Add Permission</Button>
      <Modal opened={isModalOpen} onClose={close} title="Add Drone Permission">
        <form onSubmit={handleSubmit}>
          <Stack>
            <Select
              label="Integration"
              placeholder="Select an integration"
              data={
                integrations?.map((integration) => {
                  const projectName = projectMap.get(integration.project_id)
                  const providerName = providerMap.get(
                    integration.drone_provider_id,
                  )
                  return {
                    value: String(integration.drone_integration_id),
                    label: `${projectName} - ${providerName} (${integration.drone_integration_id})`,
                  }
                }) || []
              }
              {...form.getInputProps('drone_integration_id')}
            />
            <Select
              label="Company"
              placeholder="Select a company"
              data={
                companies?.map((company) => ({
                  value: company.company_id,
                  label: company.name_long,
                })) || []
              }
              {...form.getInputProps('company_id')}
            />
            <Checkbox
              label="Can View"
              {...form.getInputProps('can_view', { type: 'checkbox' })}
            />
            <Button type="submit" loading={createDronePermission.isPending}>
              Add Permission
            </Button>
          </Stack>
        </form>
      </Modal>
      <Modal
        opened={isEditModalOpen}
        onClose={closeEdit}
        title="Edit Drone Permission"
      >
        <form onSubmit={handleEditSubmit}>
          <Stack>
            <Checkbox
              label="Can View"
              {...editForm.getInputProps('can_view', { type: 'checkbox' })}
            />
            <Group justify="space-between">
              <Button
                color="red"
                onClick={() =>
                  handleDronePermissionsOpenDeleteModal(selectedPermission!)
                }
              >
                <IconTrash />
              </Button>
              <Button type="submit" loading={updateDronePermission.isPending}>
                Update Permission
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
            Are you sure you want to delete this permission? This action cannot
            be undone.
          </Text>
          <Group justify="flex-end">
            <Button variant="outline" onClick={closeDelete}>
              Cancel
            </Button>
            <Button
              color="red"
              onClick={handleDronePermissionsDeleteSubmit}
              loading={deleteDronePermission.isPending}
            >
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}

export default DronePermissions
