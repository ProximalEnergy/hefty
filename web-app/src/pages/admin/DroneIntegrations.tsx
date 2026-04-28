import {
  DroneIntegration,
  ProviderSite,
  useCreateDroneIntegration,
  useDeleteDroneIntegration,
  useGetDroneIntegrations,
  useGetDroneProviders,
  useQueryProviderSites,
  useUpdateDroneIntegration,
} from '@/api/v1/operational/drone_integrations'
import { useGetProjects } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import {
  ActionIcon,
  Button,
  Card,
  Checkbox,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { useDisclosure } from '@mantine/hooks'
import { IconCopy, IconPencil, IconTrash } from '@tabler/icons-react'
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
      api_key: '',
      provider_project_id: '',
    },
  })

  const queryProviderSites = useQueryProviderSites()
  const [providerSites, setProviderSites] = useState<ProviderSite[]>([])
  const [selectedSite, setSelectedSite] = useState<string | null>(null)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [awsSecretsConfirmed, setAwsSecretsConfirmed] = useState<boolean>(false)

  const editForm = useForm({
    initialValues: {
      drone_integration_id: 0,
      project_id: '',
      drone_provider_id: '',
      provider_project_id: '',
    },
  })

  const handleDroneIntegrationsOpenModal = () => {
    const nextId =
      integrations && integrations.length > 0
        ? Math.max(...integrations.map((i) => i.drone_integration_id)) + 1
        : 1
    form.setValues({
      drone_integration_id: nextId,
      project_id: '',
      drone_provider_id: '',
      api_key: '',
      provider_project_id: '',
    })
    setProviderSites([])
    setSelectedSite(null)
    setFetchError(null)
    setAwsSecretsConfirmed(false)
    open()
  }

  const handleFetchSites = async () => {
    const apiKey = form.values.api_key
    const providerId = form.values.drone_provider_id

    if (!apiKey || !providerId || providerId === '') {
      setFetchError('Please select a provider and enter an API key')
      return
    }

    const providerIdNum = Number(providerId)
    if (isNaN(providerIdNum) || providerIdNum < 0) {
      setFetchError('Invalid provider selected')
      return
    }

    setFetchError(null)
    setProviderSites([])
    setSelectedSite(null)

    try {
      const sites = await queryProviderSites.mutateAsync({
        api_key: apiKey,
        provider_id: providerIdNum,
      })
      setProviderSites(sites)
    } catch (error) {
      console.error('Failed to fetch sites:', error)
      const errorMessage =
        (error as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ||
        (error as Error)?.message ||
        'Failed to fetch sites. Please check your API key and provider selection.'
      setFetchError(errorMessage)
    }
  }

  const handleSiteSelect = (siteId: string) => {
    setSelectedSite(siteId)
    form.setFieldValue('provider_project_id', siteId)
  }

  const handleCopyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch (err) {
      console.error('Failed to copy text:', err)
    }
  }

  const handleDroneIntegrationsOpenEditModal = (
    integration: DroneIntegration,
  ) => {
    setSelectedIntegration(integration)
    editForm.setValues({
      ...integration,
      drone_provider_id: String(integration.drone_provider_id),
    })
    openEdit()
  }

  const handleDroneIntegrationsOpenDeleteModal = (
    integration: DroneIntegration,
  ) => {
    setSelectedIntegration(integration)
    openDelete()
  }

  const handleSubmit = form.onSubmit(async (values) => {
    await createDroneIntegration.mutateAsync({
      project_id: values.project_id,
      drone_provider_id: Number(values.drone_provider_id),
      provider_project_id: values.provider_project_id,
    })
    form.reset()
    setProviderSites([])
    setSelectedSite(null)
    close()
  })

  const handleEditSubmit = editForm.onSubmit(async (values) => {
    await updateDroneIntegration.mutateAsync({
      ...values,
      drone_provider_id: Number(values.drone_provider_id),
    })
    closeEdit()
  })

  const handleDroneIntegrationsDeleteSubmit = async () => {
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

  const nextIntegrationId =
    integrations && integrations.length > 0
      ? Math.max(...integrations.map((i) => i.drone_integration_id)) + 1
      : 1

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
                  <ActionIcon
                    onClick={() =>
                      handleDroneIntegrationsOpenEditModal(integration)
                    }
                  >
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
      <Button onClick={handleDroneIntegrationsOpenModal}>
        Add Integration
      </Button>
      <Modal
        opened={isModalOpen}
        onClose={close}
        title="Add Drone Integration"
        size="lg"
      >
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
              label="API Key"
              type="password"
              placeholder="Enter API key"
              {...form.getInputProps('api_key')}
            />
            <Button
              type="button"
              onClick={handleFetchSites}
              disabled={
                !form.values.api_key?.trim() ||
                !form.values.drone_provider_id ||
                queryProviderSites.isPending
              }
              loading={queryProviderSites.isPending}
            >
              Fetch Sites
            </Button>
            {fetchError && (
              <Text size="sm" c="red">
                {fetchError}
              </Text>
            )}
            {providerSites.length > 0 && (
              <Select
                label="Select Site"
                placeholder="Select a site"
                data={providerSites.map((site) => ({
                  value: site.provider_site_id,
                  label: site.name || site.provider_site_id,
                }))}
                value={selectedSite}
                onChange={(value) => {
                  if (value) {
                    handleSiteSelect(value)
                  }
                }}
              />
            )}
            <TextInput
              label="Provider Project ID"
              {...form.getInputProps('provider_project_id')}
            />
            {selectedSite &&
              form.values.project_id &&
              form.values.drone_provider_id && (
                <Card withBorder p="md" radius="md" mt="md">
                  <Stack gap="xs">
                    <Text size="sm" fw={500}>
                      Store the provider API key in{' '}
                      <Text
                        component="a"
                        href="https://us-east-2.console.aws.amazon.com/secretsmanager/newsecret?region=us-east-2"
                        target="_blank"
                        rel="noopener noreferrer"
                        c="blue"
                        style={{ textDecoration: 'underline' }}
                      >
                        AWS Secrets Manager
                      </Text>
                      . Follow these steps:
                    </Text>
                    <Stack gap="xs" pl="md">
                      <Text size="sm" fw={500}>
                        Step 1:
                      </Text>
                      <Stack gap="xs" pl="md">
                        <Text size="sm" c="dimmed">
                          1. Secret type: select &quot;Other type of
                          secret&quot;
                        </Text>
                        <Text size="sm" c="dimmed">
                          2. Key/value pairs:
                        </Text>
                        <Group gap="xs" pl="md">
                          <Text size="sm" c="dimmed">
                            Key:{' '}
                            <code>
                              {providerMap
                                .get(Number(form.values.drone_provider_id))
                                ?.toLowerCase()
                                .replace(/\s+/g, '_') || '[droneprovider]'}
                              _api_key
                            </code>
                          </Text>
                          <Tooltip label="Copy key">
                            <ActionIcon
                              size="sm"
                              variant="subtle"
                              onClick={() =>
                                handleCopyToClipboard(
                                  `${
                                    providerMap
                                      .get(
                                        Number(form.values.drone_provider_id),
                                      )
                                      ?.toLowerCase()
                                      .replace(/\s+/g, '_') || '[droneprovider]'
                                  }_api_key`,
                                )
                              }
                            >
                              <IconCopy size={16} />
                            </ActionIcon>
                          </Tooltip>
                        </Group>
                        <Group gap="xs" pl="md">
                          <Text size="sm" c="dimmed">
                            Value: {form.values.api_key || 'the API key'}
                          </Text>
                          {form.values.api_key && (
                            <Tooltip label="Copy value">
                              <ActionIcon
                                size="sm"
                                variant="subtle"
                                onClick={() =>
                                  handleCopyToClipboard(form.values.api_key)
                                }
                              >
                                <IconCopy size={16} />
                              </ActionIcon>
                            </Tooltip>
                          )}
                        </Group>
                        <Text size="sm" c="dimmed">
                          3. Encryption key: &quot;aws/secretsmanager&quot;
                          (default)
                        </Text>
                      </Stack>
                      <Text size="sm" fw={500} mt="xs">
                        Step 2:
                      </Text>
                      <Stack gap="xs" pl="md">
                        <Text size="sm" c="dimmed">
                          1. Secret name:
                        </Text>
                        <Text
                          size="sm"
                          style={{
                            fontFamily: 'monospace',
                            backgroundColor: 'var(--mantine-color-gray-1)',
                            padding: '8px',
                            borderRadius: '4px',
                          }}
                          pl="md"
                        >
                          drone_integrations/drone_integration_id/
                          {nextIntegrationId}
                        </Text>
                        <Text size="sm" c="dimmed">
                          2. Description:{' '}
                          <code>
                            [customername] -{' '}
                            {projects?.find(
                              (p) => p.project_id === form.values.project_id,
                            )?.name_long || '[projectname]'}{' '}
                            -{' '}
                            {providerMap.get(
                              Number(form.values.drone_provider_id),
                            ) || '[droneprovider]'}
                          </code>
                        </Text>
                      </Stack>
                      <Text size="sm" fw={500} mt="xs">
                        Step 3:
                      </Text>
                      <Text size="sm" c="dimmed" pl="md">
                        No rotation (i.e., disabled)
                      </Text>
                    </Stack>
                  </Stack>
                </Card>
              )}
            {selectedSite &&
              form.values.project_id &&
              form.values.drone_provider_id && (
                <Checkbox
                  label="I have stored the API key in AWS Secrets Manager following the steps above"
                  checked={awsSecretsConfirmed}
                  onChange={(event) =>
                    setAwsSecretsConfirmed(event.currentTarget.checked)
                  }
                  mt="md"
                />
              )}
            <Button
              type="submit"
              loading={createDroneIntegration.isPending}
              disabled={
                !selectedSite ||
                !form.values.project_id ||
                !form.values.drone_provider_id ||
                !awsSecretsConfirmed
              }
            >
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
                onClick={() =>
                  handleDroneIntegrationsOpenDeleteModal(selectedIntegration!)
                }
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
              onClick={handleDroneIntegrationsDeleteSubmit}
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
