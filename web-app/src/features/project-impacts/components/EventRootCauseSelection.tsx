import {
  Button,
  ComboboxItem,
  Group,
  Modal,
  OptionsFilter,
  Select,
  Stack,
  Switch,
  Text,
} from '@mantine/core'
import type { RootCause } from '@/features/project-impacts/types/project-impacts-types'

const optionsFilter: OptionsFilter = ({ options, search }) => {
  const filtered = (options as ComboboxItem[]).filter((option) =>
    option.label.toLowerCase().includes(search.toLowerCase().trim()),
  )
  return filtered.sort((a, b) => a.label.localeCompare(b.label))
}

type EventRootCauseSelectionProps = {
  eventRootCauseId: number | null | undefined
  onRootCauseChange: (cause: number | null) => void
  rootCauseDeviceTypes: number[]
  rootCauses: RootCause[]
  selectedRootCause: number | null
  setSelectedRootCause: (cause: number | null) => void
  setShowAllCauses: (show: boolean) => void
  showAllCauses: boolean
}

export function EventRootCauseSelection({
  eventRootCauseId,
  onRootCauseChange,
  rootCauseDeviceTypes,
  rootCauses,
  selectedRootCause,
  setSelectedRootCause,
  setShowAllCauses,
  showAllCauses,
}: EventRootCauseSelectionProps) {
  const shownRootCauses = showAllCauses
    ? rootCauses
    : rootCauses.filter((rootCause) =>
        rootCauseDeviceTypes.includes(rootCause.device_type_id),
      )

  return (
    <>
      <Group>
        <Text>Root Cause:</Text>
        <Select
          w="60%"
          data={shownRootCauses.map((rootCause) => ({
            value: rootCause.root_cause_id.toString(),
            label: rootCause.name_full || rootCause.name_long,
          }))}
          value={selectedRootCause?.toString()}
          onChange={(value) => {
            const parsedValue = value ? parseInt(value) : null
            setSelectedRootCause(parsedValue)
            if (value !== eventRootCauseId?.toString()) {
              onRootCauseChange(parsedValue)
            }
          }}
          clearable
          searchable
          nothingFoundMessage="Nothing found..."
          filter={optionsFilter}
        />
      </Group>
      <Switch
        label="Show All Root Causes"
        checked={showAllCauses}
        onChange={(event) => setShowAllCauses(event.currentTarget.checked)}
      />
    </>
  )
}

type ConfirmRootCauseModalProps = {
  onCancel: () => void
  onConfirm: () => void
  opened: boolean
  rootCauses: RootCause[]
  selectedRootCause: number | null
}

export function ConfirmRootCauseModal({
  onCancel,
  onConfirm,
  opened,
  rootCauses,
  selectedRootCause,
}: ConfirmRootCauseModalProps) {
  const selectedRootCauseName =
    rootCauses.find((rootCause) => {
      return rootCause.root_cause_id === selectedRootCause
    })?.name_long ?? 'Unknown'

  return (
    <Modal
      opened={opened}
      onClose={onCancel}
      title={`Confirm Root Cause: ${selectedRootCauseName}`}
      transitionProps={{ transition: 'rotate-left' }}
    >
      <Stack>
        <Text>Are you sure you want to change the root cause?</Text>
        <Group grow>
          <Button onClick={onCancel}>Cancel</Button>
          <Button onClick={onConfirm}>Confirm</Button>
        </Group>
      </Stack>
    </Modal>
  )
}
