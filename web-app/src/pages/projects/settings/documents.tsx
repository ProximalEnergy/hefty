import { useGetUserPermissions, useGetUserSelf } from '@/api/admin'
import {
  useDeleteProjectDocument,
  useGetProjectDocuments,
  useUploadProjectDocument,
} from '@/api/v1/operational/documents'
import CustomCard from '@/components/CustomCard'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import {
  ActionIcon,
  Button,
  Group,
  LoadingOverlay,
  Modal,
  ScrollArea,
  Stack,
  Table,
  Text,
  Tooltip,
} from '@mantine/core'
import {
  Dropzone,
  FileRejection,
  FileWithPath,
  PDF_MIME_TYPE,
} from '@mantine/dropzone'
import { notifications } from '@mantine/notifications'
import { IconInfoCircle, IconTrash } from '@tabler/icons-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

function AdminContactInfo() {
  const label =
    'For document upload permission, please contact an administrator.'

  return (
    <Tooltip label={label} withArrow>
      <IconInfoCircle
        style={{
          marginLeft: '4px',
          color: 'var(--mantine-color-gray-6)',
        }}
      />
    </Tooltip>
  )
}

interface FileUploadProps {
  projectId: string
  disabled: boolean
}

function FileUpload({
  projectId,
  uploadMutation,
  disabled,
}: FileUploadProps & {
  uploadMutation: ReturnType<typeof useUploadProjectDocument>
  disabled: boolean
}) {
  const MAX_MB = 40

  const [opened, setOpened] = useState(false)
  const [file, setFile] = useState<FileWithPath | null>(null)

  const handleDrop = (files: FileWithPath[]) => {
    setFile(files[0])
  }

  const handleReject = (fileRejections: FileRejection[]) => {
    fileRejections.forEach(({ file, errors }) => {
      if (errors[0]?.code === 'file-too-large') {
        notifications.show({
          title: 'File too large',
          message: `${file.name} exceeds the ${MAX_MB}MB limit`,
          color: 'red',
        })
      } else {
        notifications.show({
          title: 'Invalid file',
          message: `${file.name} is not a valid file type`,
          color: 'red',
        })
      }
    })
  }

  const handleUpload = () => {
    if (file) {
      uploadMutation.mutate({ projectId, file })
      setOpened(false)
      setFile(null)
    }
  }

  return (
    <>
      {!disabled && (
        <Button onClick={() => setOpened(true)}>Upload Document</Button>
      )}
      {disabled && (
        <Group>
          <Button disabled>Upload Document</Button>
          <AdminContactInfo />
        </Group>
      )}
      <Modal
        opened={opened}
        onClose={() => {
          setOpened(false)
          setFile(null)
        }}
        title="Upload Document"
      >
        <Stack>
          {file ? (
            <Text>File selected: {file.name}</Text>
          ) : (
            <Dropzone
              onDrop={handleDrop}
              onReject={handleReject}
              maxSize={MAX_MB * 1024 ** 2}
              accept={PDF_MIME_TYPE}
              multiple={false}
            >
              <Stack style={{ pointerEvents: 'none' }}>
                <Text size="xl" inline>
                  Drag file here or click to select file
                </Text>
                <Text size="sm" c="dimmed" inline mt={7}>
                  File should not exceed {MAX_MB}mb
                </Text>
              </Stack>
            </Dropzone>
          )}
          <Group w="100%">
            <Button
              flex={1}
              onClick={() => {
                setOpened(false)
                setFile(null)
              }}
              variant="outline"
            >
              Cancel
            </Button>
            <Button
              flex={1}
              onClick={handleUpload}
              loading={uploadMutation.isPending}
              disabled={!file}
            >
              Upload
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  )
}

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
  }, [uploadMutation.error])

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
          All uploaded documents will be added to the Aria knowledge base. They
          will only be accessible to other users within your company. Text-based
          documents such as contracts, manuals, and data sheets are recommended
          for the best results.
        </Text>
        <FileUpload
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
