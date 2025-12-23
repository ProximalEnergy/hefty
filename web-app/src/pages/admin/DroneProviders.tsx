import {
  DroneProvider,
  useCreateDroneProvider,
  useDeleteDroneProvider,
  useGetDroneProviders,
  useUpdateDroneProvider,
} from '@/api/v1/operational/drone_integrations'
import { PageLoader } from '@/components/Loading'
import {
  ActionIcon,
  Button,
  Group,
  Modal,
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

const DroneProviders: React.FC = () => {
  const { data: providers, isLoading } = useGetDroneProviders()
  const createDroneProvider = useCreateDroneProvider()
  const updateDroneProvider = useUpdateDroneProvider()
  const deleteDroneProvider = useDeleteDroneProvider()
  const [isModalOpen, { open, close }] = useDisclosure(false)
  const [isEditModalOpen, { open: openEdit, close: closeEdit }] =
    useDisclosure(false)
  const [isDeleteModalOpen, { open: openDelete, close: closeDelete }] =
    useDisclosure(false)
  const [selectedProvider, setSelectedProvider] =
    useState<DroneProvider | null>(null)

  const form = useForm({
    initialValues: {
      drone_provider_id: 0,
      name_short: '', // noqa: hardcoded-name-short
      name_long: '', // noqa: hardcoded-name-long
    },
  })

  const editForm = useForm({
    initialValues: {
      drone_provider_id: 0,
      name_short: '', // noqa: hardcoded-name-short
      name_long: '', // noqa: hardcoded-name-long
    },
  })

  const handleOpenModal = () => {
    const nextId =
      providers && providers.length > 0
        ? Math.max(...providers.map((p) => p.drone_provider_id)) + 1
        : 1
    form.setValues({
      drone_provider_id: nextId,
      name_short: '', // noqa: hardcoded-name-short
      name_long: '',
    })
    open()
  }

  const handleOpenEditModal = (provider: DroneProvider) => {
    setSelectedProvider(provider)
    editForm.setValues(provider)
    openEdit()
  }

  const handleOpenDeleteModal = (provider: DroneProvider) => {
    setSelectedProvider(provider)
    openDelete()
  }

  const handleSubmit = form.onSubmit(async (values) => {
    await createDroneProvider.mutateAsync(values)
    form.reset()
    close()
  })

  const handleEditSubmit = editForm.onSubmit(async (values) => {
    await updateDroneProvider.mutateAsync(values)
    closeEdit()
  })

  const handleDeleteSubmit = async () => {
    if (selectedProvider) {
      await deleteDroneProvider.mutateAsync(selectedProvider.drone_provider_id)
      closeDelete()
      closeEdit()
    }
  }

  if (isLoading) {
    return <PageLoader />
  }

  return (
    <Stack p="md">
      <Title order={1}>Drone Providers</Title>
      {providers && providers.length > 0 ? (
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Provider ID</Table.Th>
              <Table.Th>Short Name</Table.Th>
              <Table.Th>Long Name</Table.Th>
              <Table.Th>Edit</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {providers.map((provider) => (
              <Table.Tr key={provider.drone_provider_id}>
                <Table.Td>{provider.drone_provider_id}</Table.Td>
                <Table.Td>{provider.name_short}</Table.Td>
                <Table.Td>{provider.name_long}</Table.Td>
                <Table.Td>
                  <ActionIcon onClick={() => handleOpenEditModal(provider)}>
                    <IconPencil />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : (
        <Text>No drone providers found.</Text>
      )}
      <Button onClick={handleOpenModal}>Add Provider</Button>
      <Modal opened={isModalOpen} onClose={close} title="Add Drone Provider">
        <form onSubmit={handleSubmit}>
          <Stack>
            <TextInput
              label="Provider ID"
              {...form.getInputProps('drone_provider_id')}
              type="number"
              disabled
            />
            <TextInput
              label="Short Name"
              {...form.getInputProps('name_short')}
            />
            <TextInput label="Long Name" {...form.getInputProps('name_long')} />
            <Button type="submit" loading={createDroneProvider.isPending}>
              Add Provider
            </Button>
          </Stack>
        </form>
      </Modal>
      <Modal
        opened={isEditModalOpen}
        onClose={closeEdit}
        title="Edit Drone Provider"
      >
        <form onSubmit={handleEditSubmit}>
          <Stack>
            <TextInput
              label="Short Name"
              {...editForm.getInputProps('name_short')}
            />
            <TextInput
              label="Long Name"
              {...editForm.getInputProps('name_long')}
            />
            <Group justify="space-between">
              <Button
                color="red"
                onClick={() => handleOpenDeleteModal(selectedProvider!)}
              >
                <IconTrash />
              </Button>
              <Button type="submit" loading={updateDroneProvider.isPending}>
                Update Provider
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
            Are you sure you want to delete {selectedProvider?.name_long}? This
            action cannot be undone.
          </Text>
          <Group justify="flex-end">
            <Button variant="outline" onClick={closeDelete}>
              Cancel
            </Button>
            <Button
              color="red"
              onClick={handleDeleteSubmit}
              loading={deleteDroneProvider.isPending}
            >
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}

export default DroneProviders
