import { ClaimUpdateTypeEnum } from '@/api/enumerations'
import { useGetCompanies } from '@/api/v1/admin/companies'
import { useGetUserSelf } from '@/api/v1/admin/users'
import {
  type CandidateEvent,
  type HistoricalClaimExtractResponse,
  requestHistoricalClaimExtract,
} from '@/api/v1/ai/historical_claim_extract'
import {
  useAddClaimDevice,
  useAddClaimUpdate,
  useCreateClaim,
  useGetClaimConfigs,
  useUpdateClaim,
  useUploadClaimAttachment,
} from '@/api/v1/operational/claims'
import { useGetDeviceModels } from '@/api/v1/operational/device_models'
import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import {
  STATUS_OPTIONS,
  UPDATE_TYPE_OPTIONS,
} from '@/components/warranty-claims/constants'
import { formatEventOption } from '@/components/warranty-claims/formatEvent'
import { useGetDevicesV2 } from '@/hooks/api'
import { useAuth } from '@clerk/react'
import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Group,
  Loader,
  Modal,
  Select,
  Stack,
  Stepper,
  Table,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core'
import { DatePickerInput, DateTimePicker } from '@mantine/dates'
import { Dropzone } from '@mantine/dropzone'
import { notifications } from '@mantine/notifications'
import {
  IconFile,
  IconPlus,
  IconSparkles,
  IconTrash,
  IconUpload,
  IconX,
} from '@tabler/icons-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'

const BYTES_PER_KB = 1024
const CLAIM_FILE_MAX_SIZE_BYTES = 40 * 1024 * 1024

interface Props {
  projectId: string
  opened: boolean
  onClose: () => void
}

interface DeviceRow {
  device_type_id: number | null
  device_id: number | null
  device_name_hint: string
  oem_serial_number: string
  oem_part_number: string
  notes: string
  event_id: number | null
  event_candidates: CandidateEvent[]
}

interface UpdateRow {
  update_type: string
  message: string
  occurred_at: Date | null
  from_status: string | null
  to_status: string | null
}

function parseIsoToDate(value: string | null): Date | null {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

export default function HistoricalClaimModal({
  projectId,
  opened,
  onClose,
}: Props) {
  const navigate = useNavigate()
  const { getToken } = useAuth()

  const [step, setStep] = useState(0)
  const [files, setFiles] = useState<File[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [extraction, setExtraction] =
    useState<HistoricalClaimExtractResponse | null>(null)

  const [claimConfigId, setClaimConfigId] = useState<number | null>(null)
  const [summary, setSummary] = useState('')
  const [externalRef, setExternalRef] = useState('')
  const [status, setStatus] = useState('closed')
  const [claimDate, setClaimDate] = useState<Date | null>(null)
  const [devices, setDevices] = useState<DeviceRow[]>([])
  const [updates, setUpdates] = useState<UpdateRow[]>([])

  const project = useSelectProject(projectId)
  const userSelf = useGetUserSelf({ queryOptions: { enabled: opened } })
  const { data: companiesForUser } = useGetCompanies({
    queryParams: {
      company_ids: userSelf.data?.company_id
        ? [userSelf.data.company_id]
        : undefined,
    },
    queryOptions: {
      enabled: opened && !!userSelf.data?.company_id,
    },
  })
  const { data: configs } = useGetClaimConfigs({
    pathParams: { projectId },
    queryOptions: { enabled: opened },
  })
  const { data: projectDevices } = useGetDevicesV2({
    pathParams: { projectId },
    filters: {},
    queryOptions: { enabled: opened },
  })
  const { data: deviceTypes } = useGetDeviceTypes({
    queryOptions: { enabled: opened },
  })

  const projectDeviceModelIds = useMemo(
    () =>
      Array.from(
        new Set(
          (projectDevices ?? [])
            .map((d) => d.device_model_id)
            .filter((id): id is number => id != null),
        ),
      ),
    [projectDevices],
  )
  const { data: projectDeviceModels } = useGetDeviceModels({
    queryParams: { device_model_ids: projectDeviceModelIds },
    queryOptions: {
      enabled: opened && projectDeviceModelIds.length > 0,
    },
  })
  const createClaim = useCreateClaim()
  const updateClaim = useUpdateClaim()
  const addDevice = useAddClaimDevice()
  const addUpdate = useAddClaimUpdate()
  const uploadAttachment = useUploadClaimAttachment()

  const configOptions = useMemo(
    () =>
      (configs ?? []).map((c) => ({
        value: String(c.claim_config_id),
        label: c.counterparty_name || `Config #${c.claim_config_id}`,
      })),
    [configs],
  )

  const usedDeviceTypeIds = useMemo(() => {
    const ids = new Set<number>()
    for (const d of projectDevices ?? []) {
      if (d.name_long) ids.add(d.device_type_id)
    }
    return ids
  }, [projectDevices])

  const deviceTypeOptions = useMemo(
    () =>
      (deviceTypes ?? [])
        .filter((dt) => usedDeviceTypeIds.has(dt.device_type_id))
        .map((dt) => ({
          value: String(dt.device_type_id),
          label: dt.name_long,
        })),
    [deviceTypes, usedDeviceTypeIds],
  )

  const getDeviceOptionsForType = (typeId: number | null) => {
    if (typeId == null) return []
    return (projectDevices ?? [])
      .filter((d) => d.device_type_id === typeId && !!d.name_long)
      .map((d) => ({
        value: String(d.device_id),
        label: d.name_long as string,
      }))
  }

  const getDeviceTypeIdForDevice = (deviceId: number | null) => {
    if (deviceId == null) return null
    const dev = (projectDevices ?? []).find((d) => d.device_id === deviceId)
    return dev ? dev.device_type_id : null
  }

  const resetState = () => {
    setStep(0)
    setFiles([])
    setAnalyzing(false)
    setSubmitting(false)
    setExtraction(null)
    setClaimConfigId(null)
    setSummary('')
    setExternalRef('')
    setStatus('closed')
    setClaimDate(null)
    setDevices([])
    setUpdates([])
  }

  useEffect(() => {
    if (!opened) resetState()
  }, [opened])

  const selectedConfig = useMemo(
    () =>
      (configs ?? []).find((c) => c.claim_config_id === claimConfigId) ?? null,
    [configs, claimConfigId],
  )

  /**
   * Devices passed to the LLM, narrowed by the selected OEM. We find the
   * device_models whose company_id matches the OEM's counterparty_company_id,
   * then include every project device whose device_type_id is in that set.
   * If no device_models match, we fall back to the full list so the LLM
   * still has something to work with.
   */
  const devicesForLlm = useMemo(() => {
    const all = projectDevices ?? []
    if (!selectedConfig?.counterparty_company_id) return all
    const oemCompanyId = selectedConfig.counterparty_company_id
    const oemDeviceTypeIds = new Set<number>()
    for (const m of projectDeviceModels ?? []) {
      if (m.company_id === oemCompanyId) {
        oemDeviceTypeIds.add(m.device_type_id)
      }
    }
    if (oemDeviceTypeIds.size === 0) return all
    const matches = all.filter(
      (d) => d.device_type_id != null && oemDeviceTypeIds.has(d.device_type_id),
    )
    return matches.length > 0 ? matches : all
  }, [projectDevices, projectDeviceModels, selectedConfig])

  const handleAnalyze = async () => {
    if (files.length === 0 || !claimConfigId || !selectedConfig) return
    setAnalyzing(true)
    try {
      const token = await getToken({ template: 'default' })
      if (!token) {
        throw new Error('No auth token available')
      }
      const company =
        companiesForUser && companiesForUser.length > 0
          ? companiesForUser[0].name_long ||
            companiesForUser[0].name_short ||
            ''
          : ''
      const deviceTypeNameById = new Map(
        (deviceTypes ?? []).map((dt) => [dt.device_type_id, dt.name_long]),
      )
      const llmDeviceTypeIds = new Set(
        devicesForLlm.map((d) => d.device_type_id),
      )
      const context = {
        project_id: projectId,
        project_name: project.data?.name_long || project.data?.name_short || '',
        company_name: company,
        claim_configs: [
          {
            claim_config_id: selectedConfig.claim_config_id,
            counterparty_name: selectedConfig.counterparty_name,
          },
        ],
        devices: devicesForLlm.map((d) => ({
          device_id: d.device_id,
          device_name: d.name_long || d.name_short || null,
          device_type_id: d.device_type_id,
          device_type_name: deviceTypeNameById.get(d.device_type_id) ?? null,
        })),
        device_types: (deviceTypes ?? [])
          .filter((dt) => llmDeviceTypeIds.has(dt.device_type_id))
          .map((dt) => ({
            device_type_id: dt.device_type_id,
            device_type_name: dt.name_long,
          })),
      }
      const result = await requestHistoricalClaimExtract(token, {
        projectId,
        context,
        files,
      })
      setExtraction(result)
      setClaimConfigId(result.claim_config_id ?? claimConfigId)
      setSummary(result.summary || '')
      setExternalRef(result.external_reference || '')
      setStatus(result.status || 'closed')
      setClaimDate(
        result.claim_date ? new Date(`${result.claim_date}T00:00:00`) : null,
      )
      const candidatesByRow = result.device_event_candidates ?? {}
      setDevices(
        result.devices.map((d, idx) => {
          const cands = candidatesByRow[idx] ?? []
          const suggested =
            d.event_id != null && cands.some((c) => c.event_id === d.event_id)
              ? d.event_id
              : null
          return {
            device_type_id:
              d.device_type_id ?? getDeviceTypeIdForDevice(d.device_id),
            device_id: d.device_id,
            device_name_hint: d.device_name_hint,
            oem_serial_number: d.oem_serial_number,
            oem_part_number: d.oem_part_number,
            notes: d.notes,
            event_id: suggested,
            event_candidates: cands,
          }
        }),
      )
      setUpdates(
        result.updates.map((u) => ({
          update_type: u.update_type,
          message: u.message,
          occurred_at: parseIsoToDate(u.occurred_at),
          from_status: u.from_status,
          to_status: u.to_status,
        })),
      )
      setStep(1)
    } catch (e) {
      notifications.show({
        title: 'Analysis failed',
        message:
          e instanceof Error ? e.message : 'Could not extract claim fields',
        color: 'red',
      })
    } finally {
      setAnalyzing(false)
    }
  }

  const handleCreateClaim = async () => {
    if (!claimConfigId) {
      notifications.show({
        title: 'OEM required',
        message: 'Please select an OEM / claim config before creating.',
        color: 'red',
      })
      return
    }
    setSubmitting(true)
    try {
      const created = await createClaim.mutateAsync({
        projectId,
        data: {
          claim_config_id: claimConfigId,
          summary: summary || undefined,
          external_reference: externalRef || undefined,
        },
      })
      const claimId = created.data.claim_id

      if (status && status !== 'draft') {
        await updateClaim.mutateAsync({
          projectId,
          claimId,
          data: { status },
        })
      } else if (summary || externalRef) {
        await updateClaim.mutateAsync({
          projectId,
          claimId,
          data: {
            summary: summary || null,
            external_reference: externalRef || null,
          },
        })
      }

      for (const d of devices) {
        if (!d.device_id) continue
        await addDevice.mutateAsync({
          projectId,
          claimId,
          data: {
            device_id: d.device_id,
            oem_serial_number: d.oem_serial_number || undefined,
            oem_part_number: d.oem_part_number || undefined,
            notes: d.notes || undefined,
            event_id: d.event_id ?? undefined,
          },
        })
      }

      for (const u of updates) {
        await addUpdate.mutateAsync({
          projectId,
          claimId,
          data: {
            update_type: u.update_type,
            message: u.message || undefined,
            from_status: u.from_status || undefined,
            to_status: u.to_status || undefined,
            created_at: u.occurred_at ? u.occurred_at.toISOString() : undefined,
          },
        })
      }

      for (const file of files) {
        await uploadAttachment.mutateAsync({ projectId, claimId, file })
      }

      notifications.show({
        title: 'Historical claim created',
        message: `Claim #${claimId} saved with ${files.length} attachment(s).`,
        color: 'green',
      })
      onClose()
      navigate(`/projects/${projectId}/maintenance/warranty-claims/${claimId}`)
    } catch (e) {
      notifications.show({
        title: 'Failed to create claim',
        message:
          e instanceof Error ? e.message : 'An unexpected error occurred',
        color: 'red',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={() => {
        if (submitting || analyzing) return
        onClose()
      }}
      title="Add Historical Claim"
      size={900}
    >
      <Stepper active={step} onStepClick={setStep} size="xs">
        <Stepper.Step label="Upload">
          <Stack gap="md" mt="md">
            <Text size="sm" c="dimmed">
              Select the OEM this claim is against, then upload the warranty
              claim form and any supporting documents (printed email
              conversations, OEM replies, etc.). An AI model will read them and
              suggest how to fill in the claim fields.
            </Text>

            <Select
              label="OEM / Counterparty"
              placeholder="Select claim config"
              data={configOptions}
              value={claimConfigId != null ? String(claimConfigId) : null}
              onChange={(v) => setClaimConfigId(v ? Number(v) : null)}
              required
              searchable
              description={
                selectedConfig
                  ? `AI will only consider devices of the device types that "${selectedConfig.counterparty_name ?? ''}" produces in this project.`
                  : 'Used to narrow which devices the AI considers when matching the claim form.'
              }
            />

            <Dropzone
              onDrop={(dropped) => setFiles((prev) => [...prev, ...dropped])}
              accept={['application/pdf']}
              maxSize={CLAIM_FILE_MAX_SIZE_BYTES}
              multiple
            >
              <Group
                justify="center"
                gap="xl"
                mih={120}
                style={{ pointerEvents: 'none' }}
              >
                <Dropzone.Accept>
                  <IconUpload size={40} />
                </Dropzone.Accept>
                <Dropzone.Reject>
                  <IconX size={40} />
                </Dropzone.Reject>
                <Dropzone.Idle>
                  <IconFile size={40} />
                </Dropzone.Idle>
                <Box>
                  <Text size="sm" fw={500}>
                    Drop PDFs here or click to select
                  </Text>
                  <Text size="xs" c="dimmed">
                    Claim form + supporting PDFs. Up to 40 MB each.
                  </Text>
                </Box>
              </Group>
            </Dropzone>

            {files.length > 0 && (
              <Stack gap={4}>
                {files.map((f, i) => {
                  const fileSizeKb = (f.size / BYTES_PER_KB).toFixed(0)

                  return (
                    <Group key={`${f.name}-${i}`} justify="space-between">
                      <Group gap="xs">
                        <IconFile size={14} />
                        <Text size="sm">{f.name}</Text>
                        <Text size="xs" c="dimmed">
                          {fileSizeKb} KB
                        </Text>
                      </Group>
                      <ActionIcon
                        variant="subtle"
                        color="red"
                        size="sm"
                        onClick={() =>
                          setFiles((prev) => prev.filter((_, j) => j !== i))
                        }
                      >
                        <IconTrash size={14} />
                      </ActionIcon>
                    </Group>
                  )
                })}
              </Stack>
            )}

            <Group justify="flex-end">
              <Button
                leftSection={<IconSparkles size={16} />}
                onClick={handleAnalyze}
                loading={analyzing}
                disabled={files.length === 0 || !claimConfigId}
              >
                Analyze with AI
              </Button>
            </Group>
          </Stack>
        </Stepper.Step>

        <Stepper.Step label="Review">
          <Stack gap="md" mt="md">
            {extraction && (
              <Alert
                color="blue"
                variant="light"
                icon={<IconSparkles size={16} />}
              >
                Fields below were suggested by the AI. Please review and edit
                before saving.
              </Alert>
            )}

            <Select
              label="OEM / Counterparty"
              placeholder="Select claim config"
              data={configOptions}
              value={claimConfigId != null ? String(claimConfigId) : null}
              onChange={(v) => setClaimConfigId(v ? Number(v) : null)}
              required
              searchable
              description={
                extraction?.oem_name_suggested
                  ? `AI detected OEM: ${extraction.oem_name_suggested}.`
                  : 'Pre-selected from the Upload step.'
              }
            />

            <Textarea
              label="Summary"
              value={summary}
              onChange={(e) => setSummary(e.currentTarget.value)}
              autosize
              minRows={2}
              maxRows={6}
            />

            <Group grow>
              <TextInput
                label="External reference"
                placeholder="e.g. WC-2026-001"
                value={externalRef}
                onChange={(e) => setExternalRef(e.currentTarget.value)}
              />
              <Select
                label="Status"
                data={STATUS_OPTIONS}
                value={status}
                onChange={(v) => setStatus(v || 'closed')}
                allowDeselect={false}
              />
              <DatePickerInput
                label="Claim date"
                description="Used to filter related events"
                placeholder="Pick a date"
                value={claimDate}
                onChange={(v) => setClaimDate(v ? new Date(v) : null)}
                clearable
              />
            </Group>

            <Stack gap="xs">
              <Group justify="space-between">
                <Text size="sm" fw={500}>
                  Impacted devices
                </Text>
                <Button
                  variant="subtle"
                  size="xs"
                  leftSection={<IconPlus size={14} />}
                  onClick={() =>
                    setDevices((prev) => [
                      ...prev,
                      {
                        device_type_id: null,
                        device_id: null,
                        device_name_hint: '',
                        oem_serial_number: '',
                        oem_part_number: '',
                        notes: '',
                        event_id: null,
                        event_candidates: [],
                      },
                    ])
                  }
                >
                  Add device
                </Button>
              </Group>
              {devices.length === 0 ? (
                <Text size="xs" c="dimmed">
                  No devices suggested.
                </Text>
              ) : (
                <Table
                  withTableBorder
                  withColumnBorders
                  style={{ width: '100%', tableLayout: 'fixed' }}
                >
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th style={{ width: '16%' }}>Device Type</Table.Th>
                      <Table.Th style={{ width: '13%' }}>Device</Table.Th>
                      <Table.Th style={{ width: '16%' }}>
                        Related event
                      </Table.Th>
                      <Table.Th style={{ width: '13%' }}>Serial</Table.Th>
                      <Table.Th style={{ width: '13%' }}>Part</Table.Th>
                      <Table.Th style={{ width: '24%' }}>Notes</Table.Th>
                      <Table.Th style={{ width: 44 }} />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {devices.map((d, i) => (
                      <Table.Tr key={i}>
                        <Table.Td>
                          <Select
                            placeholder="Select type"
                            data={deviceTypeOptions}
                            value={
                              d.device_type_id != null
                                ? String(d.device_type_id)
                                : null
                            }
                            onChange={(v) =>
                              setDevices((prev) =>
                                prev.map((r, j) =>
                                  j === i
                                    ? {
                                        ...r,
                                        device_type_id: v ? Number(v) : null,
                                        device_id: null,
                                      }
                                    : r,
                                ),
                              )
                            }
                            searchable
                            size="xs"
                            nothingFoundMessage="No device types"
                          />
                        </Table.Td>
                        <Table.Td>
                          <Select
                            placeholder={
                              d.device_type_id == null
                                ? 'Pick a type first'
                                : d.device_name_hint
                                  ? `AI hint: ${d.device_name_hint}`
                                  : 'Select device'
                            }
                            data={getDeviceOptionsForType(d.device_type_id)}
                            value={
                              d.device_id != null ? String(d.device_id) : null
                            }
                            onChange={(v) =>
                              setDevices((prev) =>
                                prev.map((r, j) =>
                                  j === i
                                    ? { ...r, device_id: v ? Number(v) : null }
                                    : r,
                                ),
                              )
                            }
                            searchable
                            size="xs"
                            disabled={d.device_type_id == null}
                            nothingFoundMessage="No matching devices"
                          />
                        </Table.Td>
                        <Table.Td>
                          <Select
                            placeholder={
                              d.device_id == null
                                ? 'Pick a device first'
                                : d.event_candidates.length === 0
                                  ? 'No events found'
                                  : 'Select event'
                            }
                            data={d.event_candidates.map((c) => ({
                              value: String(c.event_id),
                              label: formatEventOption(c),
                            }))}
                            value={
                              d.event_id != null ? String(d.event_id) : null
                            }
                            onChange={(v) =>
                              setDevices((prev) =>
                                prev.map((r, j) =>
                                  j === i
                                    ? { ...r, event_id: v ? Number(v) : null }
                                    : r,
                                ),
                              )
                            }
                            clearable
                            searchable
                            size="xs"
                            disabled={
                              d.device_id == null ||
                              d.event_candidates.length === 0
                            }
                            nothingFoundMessage="No matching events"
                          />
                        </Table.Td>
                        <Table.Td>
                          <TextInput
                            value={d.oem_serial_number}
                            onChange={(e) => {
                              const value = e.currentTarget.value
                              setDevices((prev) =>
                                prev.map((r, j) =>
                                  j === i
                                    ? {
                                        ...r,
                                        oem_serial_number: value,
                                      }
                                    : r,
                                ),
                              )
                            }}
                            size="xs"
                          />
                        </Table.Td>
                        <Table.Td>
                          <TextInput
                            value={d.oem_part_number}
                            onChange={(e) => {
                              const value = e.currentTarget.value
                              setDevices((prev) =>
                                prev.map((r, j) =>
                                  j === i
                                    ? {
                                        ...r,
                                        oem_part_number: value,
                                      }
                                    : r,
                                ),
                              )
                            }}
                            size="xs"
                          />
                        </Table.Td>
                        <Table.Td>
                          <TextInput
                            value={d.notes}
                            onChange={(e) => {
                              const value = e.currentTarget.value
                              setDevices((prev) =>
                                prev.map((r, j) =>
                                  j === i ? { ...r, notes: value } : r,
                                ),
                              )
                            }}
                            size="xs"
                          />
                        </Table.Td>
                        <Table.Td>
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            size="sm"
                            onClick={() =>
                              setDevices((prev) =>
                                prev.filter((_, j) => j !== i),
                              )
                            }
                          >
                            <IconTrash size={14} />
                          </ActionIcon>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Stack>

            <Stack gap="xs">
              <Group justify="space-between">
                <Text size="sm" fw={500}>
                  Timeline
                </Text>
                <Button
                  variant="subtle"
                  size="xs"
                  leftSection={<IconPlus size={14} />}
                  onClick={() =>
                    setUpdates((prev) => [
                      ...prev,
                      {
                        update_type: ClaimUpdateTypeEnum.NOTE,
                        message: '',
                        occurred_at: null,
                        from_status: null,
                        to_status: null,
                      },
                    ])
                  }
                >
                  Add entry
                </Button>
              </Group>
              {updates.length === 0 ? (
                <Text size="xs" c="dimmed">
                  No timeline entries.
                </Text>
              ) : (
                <Stack gap="xs">
                  {updates.map((u, i) => (
                    <Group
                      key={i}
                      align="flex-start"
                      gap="xs"
                      wrap="nowrap"
                      p="xs"
                      style={{
                        border: '1px solid var(--mantine-color-gray-3)',
                        borderRadius: 6,
                      }}
                    >
                      <Stack gap="xs" style={{ flex: 1 }}>
                        <Group grow>
                          <Select
                            label="Type"
                            data={UPDATE_TYPE_OPTIONS}
                            value={u.update_type}
                            onChange={(v) =>
                              setUpdates((prev) =>
                                prev.map((r, j) =>
                                  j === i
                                    ? {
                                        ...r,
                                        update_type:
                                          v || ClaimUpdateTypeEnum.NOTE,
                                      }
                                    : r,
                                ),
                              )
                            }
                            size="xs"
                            allowDeselect={false}
                          />
                          <DateTimePicker
                            label="When"
                            value={u.occurred_at}
                            onChange={(v) =>
                              setUpdates((prev) =>
                                prev.map((r, j) =>
                                  j === i
                                    ? {
                                        ...r,
                                        occurred_at: v ? new Date(v) : null,
                                      }
                                    : r,
                                ),
                              )
                            }
                            size="xs"
                            valueFormat="DD MMM YYYY hh:mm A"
                            clearable
                          />
                        </Group>
                        <Textarea
                          label="Message"
                          value={u.message}
                          onChange={(e) =>
                            setUpdates((prev) =>
                              prev.map((r, j) =>
                                j === i
                                  ? { ...r, message: e.currentTarget.value }
                                  : r,
                              ),
                            )
                          }
                          autosize
                          minRows={1}
                          maxRows={4}
                          size="xs"
                        />
                        {u.update_type === ClaimUpdateTypeEnum.STATUS_CHANGE ? (
                          <Group grow>
                            <Select
                              label="From status"
                              data={STATUS_OPTIONS}
                              value={u.from_status}
                              onChange={(v) =>
                                setUpdates((prev) =>
                                  prev.map((r, j) =>
                                    j === i ? { ...r, from_status: v } : r,
                                  ),
                                )
                              }
                              size="xs"
                              clearable
                            />
                            <Select
                              label="To status"
                              data={STATUS_OPTIONS}
                              value={u.to_status}
                              onChange={(v) =>
                                setUpdates((prev) =>
                                  prev.map((r, j) =>
                                    j === i ? { ...r, to_status: v } : r,
                                  ),
                                )
                              }
                              size="xs"
                              clearable
                            />
                          </Group>
                        ) : null}
                      </Stack>
                      <ActionIcon
                        variant="subtle"
                        color="red"
                        size="sm"
                        onClick={() =>
                          setUpdates((prev) => prev.filter((_, j) => j !== i))
                        }
                      >
                        <IconTrash size={14} />
                      </ActionIcon>
                    </Group>
                  ))}
                </Stack>
              )}
            </Stack>

            <Group justify="space-between">
              <Button variant="default" onClick={() => setStep(0)}>
                Back
              </Button>
              <Button onClick={() => setStep(2)} disabled={!claimConfigId}>
                Continue
              </Button>
            </Group>
          </Stack>
        </Stepper.Step>

        <Stepper.Step label="Confirm">
          <Stack gap="md" mt="md">
            <Text size="sm">
              Ready to create a historical claim with the details below.
            </Text>
            <Table withTableBorder>
              <Table.Tbody>
                <Table.Tr>
                  <Table.Td fw={500} w={180}>
                    OEM
                  </Table.Td>
                  <Table.Td>
                    {configOptions.find(
                      (o) => Number(o.value) === claimConfigId,
                    )?.label || '—'}
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>Status</Table.Td>
                  <Table.Td>
                    <Badge variant="light">{status}</Badge>
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>External reference</Table.Td>
                  <Table.Td>{externalRef || '—'}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>Summary</Table.Td>
                  <Table.Td>{summary || '—'}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>Devices</Table.Td>
                  <Table.Td>
                    {devices.filter((d) => d.device_id).length}
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>Timeline entries</Table.Td>
                  <Table.Td>{updates.length}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>Attachments</Table.Td>
                  <Table.Td>{files.length}</Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>
            <Group justify="space-between">
              <Button
                variant="default"
                onClick={() => setStep(1)}
                disabled={submitting}
              >
                Back
              </Button>
              <Button onClick={handleCreateClaim} loading={submitting}>
                Create Historical Claim
              </Button>
            </Group>
          </Stack>
        </Stepper.Step>
      </Stepper>

      {analyzing && (
        <Group justify="center" mt="md">
          <Loader size="sm" />
          <Text size="sm" c="dimmed">
            Analyzing {files.length} file(s) with AI…
          </Text>
        </Group>
      )}
    </Modal>
  )
}
