import { useUploadProjectDocument } from '@/api/v1/operational/documents'
import { Button, Group, Modal, Stack, Text, Tooltip } from '@mantine/core'
import {
  Dropzone,
  FileRejection,
  FileWithPath,
  PDF_MIME_TYPE,
} from '@mantine/dropzone'
import { notifications } from '@mantine/notifications'
import { IconInfoCircle } from '@tabler/icons-react'
import { useState } from 'react'

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

interface ProjectDocumentUploadButtonProps {
  projectId: string
  uploadMutation: ReturnType<typeof useUploadProjectDocument>
  disabled: boolean
  /** Defaults to "Upload Document" */
  buttonLabel?: string
}

const MAX_MB = 40
const MAX_UPLOAD_SIZE_BYTES = MAX_MB * 1024 ** 2

/**
 * Modal + button to upload a PDF to project documents (same flow as Settings →
 * Documents).
 */
export function ProjectDocumentUploadButton({
  projectId,
  uploadMutation,
  disabled,
  buttonLabel = 'Upload Document',
}: ProjectDocumentUploadButtonProps) {
  const [opened, setOpened] = useState(false)
  const [file, setFile] = useState<FileWithPath | null>(null)

  const handleDrop = (files: FileWithPath[]) => {
    setFile(files[0])
  }

  const handleReject = (fileRejections: FileRejection[]) => {
    fileRejections.forEach(({ file: rejFile, errors }) => {
      if (errors[0]?.code === 'file-too-large') {
        notifications.show({
          title: 'File too large',
          message: `${rejFile.name} exceeds the ${MAX_MB}MB limit`,
          color: 'red',
        })
      } else {
        notifications.show({
          title: 'Invalid file',
          message: `${rejFile.name} is not a valid file type`,
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
        <Button onClick={() => setOpened(true)}>{buttonLabel}</Button>
      )}
      {disabled && (
        <Group>
          <Button disabled>{buttonLabel}</Button>
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
              maxSize={MAX_UPLOAD_SIZE_BYTES}
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
