import {
  useCreateUser,
  useDeleteUser,
  useGetCompanies,
  useGetUsers,
  useUpdateUserProjects,
} from '@/api/admin'
import { UserTypeEnumEnum } from '@/api/enumerations'
import { useGetProjects } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import { useUser } from '@clerk/clerk-react'
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
  TextInput,
  Title,
} from '@mantine/core'
import { hasLength, isEmail, useForm } from '@mantine/form'
import { useDisclosure } from '@mantine/hooks'
import { IconUserMinus } from '@tabler/icons-react'
import { AxiosError } from 'axios'
import { useState } from 'react'

const UserManagement = () => {
  const [isModalOpen, { open, close }] = useDisclosure(false)
  const [deleteModalOpen, { open: openDeleteModal, close: closeDeleteModal }] =
    useDisclosure(false)
  const [userToDelete, setUserToDelete] = useState<{
    user_id: string
    name_long: string
  } | null>(null)
  const [modifiedUsers, setModifiedUsers] = useState<Record<string, string[]>>(
    {},
  )
  const [createUserError, setCreateUserError] = useState<string | null>(null)
  const createUser = useCreateUser()
  const deleteUser = useDeleteUser()
  const updateUserProjects = useUpdateUserProjects()
  const { user: clerkUser } = useUser()
  const currentUser = useGetUsers({
    queryParams: { user_ids: [clerkUser?.id || ''] },
    queryOptions: { enabled: !!clerkUser?.id },
  })
  const user = currentUser.data?.[0]
  const users = useGetUsers({
    queryParams: {
      company_ids:
        currentUser.data?.[0].user_type_id === UserTypeEnumEnum.SUPERADMIN
          ? undefined
          : [user?.company_id || ''],
    },
    queryOptions: { enabled: !!user?.company_id },
  })
  const uniqueCompanyIds = [
    ...new Set(users.data?.map((user) => user.company_id) || []),
  ]

  const companies = useGetCompanies({
    queryParams: { company_ids: uniqueCompanyIds },
  })

  // Create a map of company IDs to company names for easier lookup
  const companyMap =
    companies.data?.reduce(
      (acc, company) => {
        acc[company.company_id] = company.name_long
        return acc
      },
      {} as Record<string, string>,
    ) || {}

  // Collect all unique project IDs from all users
  const uniqueProjectIds = Array.from(
    new Set(users.data?.flatMap((user) => user.operational_project_ids) || []),
  ).sort()
  const projects = useGetProjects({
    queryParams: { projectIds: uniqueProjectIds.join(',') },
    queryOptions: {
      enabled: !!uniqueProjectIds.length && uniqueProjectIds.length > 0,
    },
  })

  // Add new state for company filter
  const [selectedCompanyFilter, setSelectedCompanyFilter] = useState<
    string | null
  >(null)

  // Modify the sorting and filtering of users
  const sortedUsers = users.data
    ?.slice()
    .filter(
      (user) =>
        !selectedCompanyFilter || user.company_id === selectedCompanyFilter,
    )
    .sort((a, b) => {
      // First compare by company name
      const companyComparison = (companyMap[a.company_id] || '').localeCompare(
        companyMap[b.company_id] || '',
      )
      if (companyComparison !== 0) return companyComparison
      // If companies are the same, compare by user name
      return a.name_long.localeCompare(b.name_long)
    })

  const isLoading =
    currentUser.isLoading ||
    users.isLoading ||
    projects.isLoading ||
    companies.isLoading

  const form = useForm({
    initialValues: {
      first_name: '',
      last_name: '',
      email: '',
      company_id: user?.company_id || '',
    },
    validate: {
      first_name: hasLength(
        { min: 2 },
        'First name must be at least 2 characters',
      ),
      last_name: hasLength(
        { min: 2 },
        'Last name must be at least 2 characters',
      ),
      email: isEmail('Invalid email address'),
      company_id: hasLength({ min: 1 }, 'Company is required'),
    },
  })

  const handleSubmit = form.onSubmit(async (values) => {
    try {
      const selectedCompany = companies.data?.find(
        (company) => company.company_id === values.company_id,
      )
      await createUser.mutateAsync({
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        company_id: values.company_id,
        company_name_short: selectedCompany?.name_short || '',
      })
      form.reset()
      close()
    } catch (error: unknown) {
      if (error instanceof AxiosError) {
        setCreateUserError(error.response?.data.detail)
      }
      // You might want to add error handling here, perhaps with notifications
    }
  })
  const handleDeleteUser = (user_id: string) => {
    deleteUser.mutateAsync({ user_id }).then(() => {
      closeDeleteModal()
      setUserToDelete(null)
    })
  }

  const openDeleteConfirmation = (user: {
    user_id: string
    name_long: string
  }) => {
    setUserToDelete(user)
    openDeleteModal()
  }

  // Check if any changes have been made
  const hasChanges = Object.keys(modifiedUsers).some((userId) => {
    const originalProjects =
      users.data?.find((u) => u.user_id === userId)?.operational_project_ids ||
      []
    const modifiedProjects = modifiedUsers[userId]

    // Check if arrays have different lengths
    if (originalProjects.length !== modifiedProjects.length) return true

    // Check if all projects match
    return (
      !originalProjects.every((id) => modifiedProjects.includes(id)) ||
      !modifiedProjects.every((id) => originalProjects.includes(id))
    )
  })

  // Handle checkbox changes
  const handleProjectChange = (
    userId: string,
    projectId: string,
    checked: boolean,
  ) => {
    setModifiedUsers((prev) => {
      const originalProjects =
        users.data?.find((u) => u.user_id === userId)
          ?.operational_project_ids || []
      const userProjects = prev[userId] || originalProjects

      const updatedProjects = checked
        ? [...userProjects, projectId].filter(Boolean)
        : userProjects.filter((id) => id !== projectId && id !== null)

      // Create new state object
      const newState = { ...prev }

      // Check if the updated projects match the original projects
      const isUnchanged =
        updatedProjects.length === originalProjects.length &&
        updatedProjects.every((id) => originalProjects.includes(id)) &&
        originalProjects.every((id) => updatedProjects.includes(id))

      if (isUnchanged) {
        // Remove this user from modifiedUsers if their projects match original state
        delete newState[userId]
      } else {
        // Update the projects for this user, ensuring no null values
        newState[userId] = updatedProjects
      }

      return newState
    })
  }
  // Handle project updates submission
  const handleProjectUpdates = async () => {
    const userIds = Object.keys(modifiedUsers)
    const projectIds = userIds.map((userId) => modifiedUsers[userId])
    await updateUserProjects.mutateAsync({
      user_ids: userIds,
      operational_project_ids: projectIds,
    })

    // Clear modifications after successful update
    setModifiedUsers({})
  }

  // Get the current projects for a user, taking into account any modifications
  const getCurrentProjects = (userId: string, originalProjects: string[]) => {
    return modifiedUsers[userId] ?? originalProjects
  }

  if (isLoading) return <PageLoader />

  return (
    <Stack p="md">
      <Title order={1}>User Management</Title>

      {/* Only show company filter if there are multiple companies */}
      {(companies.data?.length || 0) > 1 && (
        <Select
          label="Filter by Company"
          placeholder="All Companies"
          clearable
          data={
            companies.data
              ?.map((company) => ({
                value: company.company_id,
                label: company.name_long,
              }))
              .sort((a, b) => a.label.localeCompare(b.label)) || []
          }
          value={selectedCompanyFilter}
          onChange={setSelectedCompanyFilter}
        />
      )}

      <Table stickyHeader stickyHeaderOffset={0} striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Company</Table.Th>
            {projects.data?.map((project) => (
              <Table.Th key={project.project_id}>{project.name_long}</Table.Th>
            ))}
            <Table.Th>Remove User</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sortedUsers?.map((tableUser) => (
            <Table.Tr key={tableUser.user_id}>
              <Table.Td>{tableUser.name_long}</Table.Td>
              <Table.Td>{companyMap[tableUser.company_id]}</Table.Td>
              {projects.data?.map((project) => (
                <Table.Td key={project.project_id}>
                  <Checkbox
                    checked={getCurrentProjects(
                      tableUser.user_id,
                      tableUser.operational_project_ids,
                    ).includes(project.project_id)}
                    onChange={(event) =>
                      handleProjectChange(
                        tableUser.user_id,
                        project.project_id,
                        event.currentTarget.checked,
                      )
                    }
                  />
                </Table.Td>
              ))}
              <Table.Td>
                <ActionIcon
                  color="red"
                  disabled={user && tableUser.user_type_id <= user.user_type_id}
                  onClick={() => openDeleteConfirmation(tableUser)}
                >
                  <IconUserMinus />
                </ActionIcon>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      <Button onClick={open}>Create User</Button>

      {/* Add Update Projects button */}
      <Button
        onClick={handleProjectUpdates}
        disabled={!hasChanges}
        loading={updateUserProjects.isPending}
      >
        Update Projects
      </Button>

      {/* Delete Confirmation Modal */}
      <Modal
        opened={deleteModalOpen}
        onClose={closeDeleteModal}
        title="Confirm Removal"
      >
        <Stack>
          <Text>Remove user: {userToDelete?.name_long}?</Text>
          <Group justify="flex-end">
            <Button variant="outline" onClick={closeDeleteModal}>
              Cancel
            </Button>
            <Button
              color="red"
              onClick={() =>
                userToDelete && handleDeleteUser(userToDelete.user_id)
              }
              loading={deleteUser.isPending}
            >
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal title="Create User" opened={isModalOpen} onClose={close}>
        <form onSubmit={handleSubmit}>
          <Stack>
            <TextInput
              required
              label="First Name"
              placeholder="First Name"
              {...form.getInputProps('first_name')}
            />
            <TextInput
              required
              label="Last Name"
              placeholder="Last Name"
              {...form.getInputProps('last_name')}
            />
            <TextInput
              required
              label="Email"
              placeholder="Email"
              {...form.getInputProps('email')}
            />
            <Select
              required
              label="Company"
              placeholder="Select Company"
              data={companies.data?.map((company) => ({
                value: company.company_id,
                label: company.name_long,
              }))}
              {...form.getInputProps('company_id')}
            />
            <Button type="submit" loading={createUser.isPending}>
              Create User
            </Button>
            {createUser.isError && <Text c="red">{createUserError}</Text>}
          </Stack>
        </form>
      </Modal>
    </Stack>
  )
}

export default UserManagement
