import { ClaimSubmissionChannelEnum } from '@/api/enumerations'
import CompanyLookup from '@/components/CompanyLookup'
import { Group, Select, Stack, Text, TextInput } from '@mantine/core'
import { IconBuildingFactory2 } from '@tabler/icons-react'

import { CHANNEL_OPTIONS, channelUsesPortalUrl } from './constants'

export interface OemConfigFormValues {
  /** Required when `mode === 'create'`; null otherwise. */
  counterpartyId: string | null
  channel: string
  contact: string
  portal: string
}

interface Props {
  values: OemConfigFormValues
  onChange: (next: OemConfigFormValues) => void
  /** Show readonly counterparty (edit) instead of `<CompanyLookup />`. */
  fixedCounterpartyName?: string
  autoFocus?: boolean
}

export function getDefaultContactEmailError(contact: string): string | null {
  const value = contact.trim()
  if (!value) return null

  const addresses = value.split(/[\s,;]+/).filter(Boolean)
  if (addresses.length > 1) {
    return 'Enter one email address only. Add extras as Cc when submitting.'
  }

  return null
}

/**
 * Form fields for an OEM (claim_config): counterparty, submission channel,
 * default contact, and (for portal/hybrid channels) portal URL.
 */
export default function OemConfigForm({
  values,
  onChange,
  fixedCounterpartyName,
  autoFocus,
}: Props) {
  const set = (patch: Partial<OemConfigFormValues>) =>
    onChange({ ...values, ...patch })
  const contactError = getDefaultContactEmailError(values.contact)

  return (
    <Stack gap="sm">
      {fixedCounterpartyName ? (
        <Stack gap={2}>
          <Text size="sm" fw={500}>
            OEM / Counterparty
          </Text>
          <Group gap="xs">
            <IconBuildingFactory2 size={16} stroke={1.5} />
            <Text size="sm">{fixedCounterpartyName}</Text>
          </Group>
        </Stack>
      ) : (
        <CompanyLookup
          label="OEM / Counterparty"
          placeholder="Search for the OEM company..."
          selectedCompanyId={values.counterpartyId}
          onSelect={(id) => set({ counterpartyId: id })}
          autoFocus={autoFocus}
        />
      )}
      <Select
        label="Submission Channel"
        description="How claims are typically sent to this OEM"
        data={CHANNEL_OPTIONS}
        value={values.channel}
        onChange={(v) => {
          const next = v ?? ClaimSubmissionChannelEnum.EMAIL
          const portal = channelUsesPortalUrl(next) ? values.portal : ''
          set({ channel: next, portal })
        }}
        allowDeselect={false}
      />
      <TextInput
        label="Default Contact Email"
        description="The OEM contact who will receive claim submissions"
        error={contactError}
        value={values.contact}
        onChange={(e) => set({ contact: e.currentTarget.value })}
      />
      {channelUsesPortalUrl(values.channel) && (
        <TextInput
          label="Portal URL (optional)"
          description="Link to the OEM's warranty claim portal, if applicable"
          value={values.portal}
          onChange={(e) => set({ portal: e.currentTarget.value })}
        />
      )}
    </Stack>
  )
}
