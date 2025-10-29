import {
  useGetAllPermissions,
  useGetCompanyPermissions,
  useGetCompanyUsersPermissions,
  useUpdateUserPermissionMutation,
} from '@/api/admin'
import CustomCard from '@/components/CustomCard'
import {
  Checkbox,
  LoadingOverlay,
  ScrollArea,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from '@mantine/core'
import { useParams } from 'react-router'

const Page = () => {
  const { projectId } = useParams()
  const updatePermission = useUpdateUserPermissionMutation()

  const allPermissions = useGetAllPermissions({})
  const companyPermissions = useGetCompanyPermissions({
    pathParams: { projectId: projectId || '-1' },
  })

  const userPermissions = useGetCompanyUsersPermissions({
    pathParams: { projectId: projectId || '-1' },
  })

  const isLoading =
    allPermissions.isLoading ||
    companyPermissions.isLoading ||
    userPermissions.isLoading

  const handlePermissionChange = (
    userId: string,
    permissionId: number,
    checked: boolean,
  ) => {
    if (!projectId) return

    updatePermission.mutate({
      userId,
      projectId,
      permissionId,
      grant: checked,
    })
  }

  // Create a map of company permission IDs for quick lookup
  const companyPermissionIds = new Set(
    companyPermissions.data?.map((p) => p.permission_id) || [],
  )

  return (
    <Stack p="md" h="100%">
      <Title order={1}>Admin</Title>
      <CustomCard title="User Permissions" fill style={{ minHeight: 200 }}>
        <LoadingOverlay visible={isLoading} />
        <ScrollArea h="100%">
          {allPermissions.data && (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>User</Table.Th>
                  {allPermissions.data?.map((permission) => (
                    <Table.Th key={permission.permission_id}>
                      <Tooltip label={permission.name_long}>
                        <span>{permission.name_short}</span>
                      </Tooltip>
                    </Table.Th>
                  ))}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {userPermissions.data && userPermissions.data.length > 0 ? (
                  userPermissions.data
                    ?.sort((a, b) => a.name_long.localeCompare(b.name_long))
                    .map((user) => (
                      <Table.Tr key={user.user_id}>
                        <Table.Td>{user.name_long}</Table.Td>
                        {allPermissions.data?.map((permission) => (
                          <Table.Td key={permission.permission_id}>
                            <Checkbox
                              checked={user.permission_ids.includes(
                                permission.permission_id,
                              )}
                              disabled={
                                !companyPermissionIds.has(
                                  permission.permission_id,
                                )
                              }
                              onChange={(event) =>
                                handlePermissionChange(
                                  user.user_id.toString(),
                                  permission.permission_id,
                                  event.currentTarget.checked,
                                )
                              }
                            />
                          </Table.Td>
                        ))}
                      </Table.Tr>
                    ))
                ) : (
                  <Table.Tr>
                    <Table.Td colSpan={allPermissions.data.length + 1}>
                      <Text ta="center" c="dimmed" py="md">
                        No users have been assigned to this project yet.
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          )}
        </ScrollArea>
      </CustomCard>
    </Stack>
  )
}

export default Page
