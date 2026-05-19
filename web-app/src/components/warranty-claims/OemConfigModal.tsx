import { ClaimSubmissionChannelEnum } from '@/api/enumerations'
import {
  type ClaimConfig,
  useCreateClaimConfig,
  useUpdateClaimConfig,
} from '@/api/v1/operational/claims'
import OemConfigForm, {
  type OemConfigFormValues,
  getDefaultContactEmailError,
} from '@/components/warranty-claims/OemConfigForm'
import { channelUsesPortalUrl } from '@/components/warranty-claims/constants'
import { Button, Group, Modal, Stack, Text } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useEffect, useState } from 'react'

type CreateProps = {
  mode: 'create'
  projectId: string
  opened: boolean
  onClose: () => void
  onSaved?: (claimConfigId: number) => void
  /** Edit-mode only; ignored in create. */
  existing?: never
}

type EditProps = {
  mode: 'edit'
  projectId: string
  opened: boolean
  onClose: () => void
  onSaved?: (claimConfigId: number) => void
  existing: ClaimConfig
}

type Props = CreateProps | EditProps

const EMPTY: OemConfigFormValues = {
  counterpartyId: null,
  channel: ClaimSubmissionChannelEnum.EMAIL,
  contact: '',
  portal: '',
}

function fromConfig(cfg: ClaimConfig): OemConfigFormValues {
  return {
    counterpartyId: cfg.counterparty_company_id,
    channel: cfg.default_submission_channel,
    contact: cfg.default_contact ?? '',
    portal: cfg.portal_url ?? '',
  }
}

export default function OemConfigModal(props: Props) {
  const { mode, projectId, opened, onClose, onSaved } = props
  const existing = mode === 'edit' ? props.existing : null
  const [values, setValues] = useState<OemConfigFormValues>(EMPTY)
  const create = useCreateClaimConfig()
  const update = useUpdateClaimConfig()
  const pending = create.isPending || update.isPending
  const contactError = getDefaultContactEmailError(values.contact)

  useEffect(() => {
    if (!opened) return
    setValues(existing ? fromConfig(existing) : EMPTY)
  }, [opened, existing])

  const handleSave = async () => {
    if (mode === 'create' && !values.counterpartyId) return
    if (contactError) return
    const contact = values.contact.trim()
    const portal = channelUsesPortalUrl(values.channel)
      ? values.portal || undefined
      : undefined
    try {
      if (mode === 'create') {
        const res = await create.mutateAsync({
          projectId,
          data: {
            counterparty_company_id: values.counterpartyId!,
            default_submission_channel: values.channel,
            default_contact: contact || undefined,
            portal_url: portal,
          },
        })
        notifications.show({
          title: 'OEM added',
          message: 'Claim config created',
          color: 'green',
        })
        onSaved?.(res.data.claim_config_id)
      } else {
        await update.mutateAsync({
          projectId,
          claimConfigId: props.existing.claim_config_id,
          data: {
            default_submission_channel: values.channel,
            default_contact: contact || null,
            portal_url: channelUsesPortalUrl(values.channel)
              ? values.portal || null
              : null,
          },
        })
        notifications.show({
          title: 'Updated',
          message: 'OEM configuration saved',
          color: 'green',
        })
        onSaved?.(props.existing.claim_config_id)
      }
      onClose()
    } catch {
      notifications.show({
        title: 'Error',
        message:
          mode === 'create'
            ? 'Failed to create OEM config'
            : 'Failed to update OEM config',
        color: 'red',
      })
    }
  }

  const fixedName =
    mode === 'edit'
      ? props.existing.counterparty_name ||
        `Config #${props.existing.claim_config_id}`
      : undefined

  return (
    <Modal
      opened={opened}
      onClose={() => {
        if (pending) return
        onClose()
      }}
      title={
        mode === 'create' ? 'Add OEM Configuration' : 'Edit OEM Configuration'
      }
      size="md"
    >
      <Stack gap="sm">
        {mode === 'create' && (
          <Text size="xs" c="dimmed">
            Configure a counterparty (OEM) so you can file warranty claims
            against it for this project.
          </Text>
        )}
        <OemConfigForm
          values={values}
          onChange={setValues}
          fixedCounterpartyName={fixedName}
          autoFocus={mode === 'create'}
        />
        <Group justify="flex-end" mt="xs">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            loading={pending}
            disabled={
              Boolean(contactError) ||
              (mode === 'create' && !values.counterpartyId)
            }
          >
            {mode === 'create' ? 'Add OEM' : 'Save Changes'}
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
