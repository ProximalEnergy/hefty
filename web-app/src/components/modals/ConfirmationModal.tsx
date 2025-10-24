import { Button, Group, Modal, Text } from '@mantine/core'

interface ConfirmationModalProps {
  opened: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string
  confirmLoading?: boolean
}

const ConfirmationModal = ({
  opened,
  onClose,
  onConfirm,
  title,
  message,
  confirmLoading = false,
}: ConfirmationModalProps) => {
  return (
    <Modal opened={opened} onClose={onClose} title={title}>
      <Text component="div">{message}</Text>
      <Group mt="md">
        <Button variant="default" onClick={onClose} disabled={confirmLoading}>
          Cancel
        </Button>
        <Button color="red" onClick={onConfirm} loading={confirmLoading}>
          Confirm
        </Button>
      </Group>
    </Modal>
  )
}

export default ConfirmationModal
