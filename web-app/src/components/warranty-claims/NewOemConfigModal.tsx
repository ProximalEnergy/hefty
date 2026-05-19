import OemConfigModal from '@/components/warranty-claims/OemConfigModal'

interface Props {
  projectId: string
  opened: boolean
  onClose: () => void
  onCreated?: (claimConfigId: number) => void
}

/**
 * Backwards-compatible wrapper: existing `<NewOemConfigModal />` callers keep
 * working but the implementation now lives in `OemConfigModal` so create/edit
 * stay in sync.
 */
export default function NewOemConfigModal({
  projectId,
  opened,
  onClose,
  onCreated,
}: Props) {
  return (
    <OemConfigModal
      mode="create"
      projectId={projectId}
      opened={opened}
      onClose={onClose}
      onSaved={onCreated}
    />
  )
}
