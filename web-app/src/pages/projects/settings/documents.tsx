import { useGetUserPermissions } from '@/api/admin'
import { useGetCompanies } from '@/api/v1/admin/companies'
import { useGetUserSelf } from '@/api/v1/admin/users'
import {
  useDeleteProjectDocument,
  useGetProjectDocuments,
  useUploadProjectDocument,
} from '@/api/v1/operational/documents'
import CustomCard from '@/components/CustomCard'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { ProjectDocumentUploadButton } from '@/components/ProjectDocumentUploadButton'
import {
  ActionIcon,
  Group,
  LoadingOverlay,
  ScrollArea,
  Stack,
  Table,
  Text,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconTrash } from '@tabler/icons-react'
import { useEffect } from 'react'
import { Link } from 'react-router'

const checkPermissions = (
  permissions: ReturnType<typeof useGetUserPermissions>['data'],
  permissionNameShort: string,
) => {
  return permissions?.some((p) => p.name_short === permissionNameShort) ?? false
}

interface DocumentsProps {
  projectId: string
}

const Documents = ({ projectId }: DocumentsProps) => {
  const permissions = useGetUserPermissions({
    pathParams: { projectId },
  })
  const self = useGetUserSelf({})
  const companies = useGetCompanies({
    queryParams: {
      company_ids: self.data?.company_id ? [self.data.company_id] : undefined,
    },
    queryOptions: {
      enabled: !!self.data?.company_id,
    },
  })

  const documents = useGetProjectDocuments({
    pathParams: { projectId },
  })

  const uploadMutation = useUploadProjectDocument()
  const deleteDocumentMutation = useDeleteProjectDocument()

  useEffect(() => {
    if (uploadMutation.error) {
      notifications.show({
        id: 'upload-error',
        title: 'Upload Error',
        message: uploadMutation.error.response?.data.detail,
        color: 'red',
      })
      uploadMutation.reset()
    }
  }, [uploadMutation, uploadMutation.error])

  const handleDeleteDocument = (documentId: string) => {
    deleteDocumentMutation.mutate({ projectId, documentId })
  }

  if (documents.isLoading || permissions.isLoading || self.isLoading) {
    return <PageLoader />
  }
  if (documents.error) return <PageError error={documents.error} />

  const canDeleteDocuments = checkPermissions(
    permissions.data,
    'delete:documents',
  )

  const canCreateDocuments =
    checkPermissions(permissions.data, 'create:documents') ||
    (self.data?.user_type_id ?? 3) <= 2
  const isAdminUser = (self.data?.user_type_id ?? 3) <= 2

  const companyName = companies.data?.[0]?.name_long ?? 'your company'

  const rows = documents.data?.map((doc) => (
    <Table.Tr key={doc.document_id}>
      <Table.Td>
        <Link
          to={doc.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: 'inherit' }}
        >
          {doc.name}
        </Link>
      </Table.Td>
      <Table.Td style={{ textAlign: 'right' }}>
        {canDeleteDocuments && (
          <ActionIcon
            variant="subtle"
            color="red"
            onClick={() => handleDeleteDocument(doc.document_id)}
            aria-label="Delete document"
          >
            <IconTrash size={16} />
          </ActionIcon>
        )}
      </Table.Td>
    </Table.Tr>
  ))

  return (
    <Stack h="100%" pt="md">
      <Group justify="space-between" align="flex-start">
        <Text style={{ flex: 1 }}>
          This document will be viewable by all users in {companyName}. Uploaded
          documents are also added to the Aria knowledge base.{' '}
          {isAdminUser && (
            <>
              Manage users in <Link to="/admin/users">User Management</Link>.
            </>
          )}
        </Text>
        <ProjectDocumentUploadButton
          projectId={projectId}
          uploadMutation={uploadMutation}
          disabled={!canCreateDocuments}
        />
      </Group>

      <div style={{ position: 'relative', flex: 1 }}>
        <LoadingOverlay
          visible={
            deleteDocumentMutation.isPending ||
            uploadMutation.isPending ||
            documents.isLoading ||
            documents.isFetching ||
            documents.isRefetching
          }
        />
        {documents.data?.length === 0 ? (
          <Text>No documents uploaded for this project.</Text>
        ) : (
          <CustomCard title="Documents" fill>
            <ScrollArea h="100%">
              <Table striped highlightOnHover withRowBorders={false}>
                <Table.Tbody>{rows}</Table.Tbody>
              </Table>
            </ScrollArea>
          </CustomCard>
        )}
      </div>
    </Stack>
  )
}

export default Documents
