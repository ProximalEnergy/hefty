import { useGetUserType } from '@/api/admin'
import { ClaimUpdateTypeEnum } from '@/api/enumerations'
import {
  useAddClaimDevice,
  useAddClaimUpdate,
  useDeleteClaim,
  useDeleteClaimAttachment,
  useGetClaimById,
  useGetClaimConfigs,
  useRemoveClaimDevice,
  useUpdateClaim,
  useUpdateClaimDevice,
  useUploadClaimAttachment,
} from '@/api/v1/operational/claims'
import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import DeviceEventSelect from '@/components/warranty-claims/DeviceEventSelect'
import {
  STATUS_COLORS,
  STATUS_OPTIONS,
  UPDATE_ICONS,
  UPDATE_TYPE_OPTIONS,
} from '@/components/warranty-claims/constants'
import { formatDateTime } from '@/components/warranty-claims/formatDate'
import { useGetDevicesV2 } from '@/hooks/api'
import { downloadRemoteFileBestEffort } from '@/utils/triggerDownload'
import {
  ActionIcon,
  Anchor,
  Badge,
  Box,
  Button,
  Grid,
  Group,
  List,
  Menu,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Timeline,
  Title,
} from '@mantine/core'
import { Dropzone } from '@mantine/dropzone'
import { useDisclosure } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconCheck,
  IconClock,
  IconDotsVertical,
  IconDownload,
  IconEdit,
  IconFile,
  IconFileText,
  IconPlus,
  IconTrash,
  IconUpload,
  IconX,
} from '@tabler/icons-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

const BYTES_PER_KB = 1024
const CLAIM_ATTACHMENT_MAX_SIZE_BYTES = 40 * 1024 * 1024

export default function ClaimDetail() {
  const { projectId, claimId } = useParams<{
    projectId: string
    claimId: string
  }>()
  const navigate = useNavigate()
  const [updateOpened, { open: openUpdate, close: closeUpdate }] =
    useDisclosure(false)
  const [
    deviceModalOpened,
    { open: openDeviceModal, close: closeDeviceModal },
  ] = useDisclosure(false)
  const [
    deleteConfirmOpened,
    { open: openDeleteConfirm, close: closeDeleteConfirm },
  ] = useDisclosure(false)
  const [updateType, setUpdateType] = useState<string>(ClaimUpdateTypeEnum.NOTE)
  const [updateMessage, setUpdateMessage] = useState('')
  const [newStatus, setNewStatus] = useState<string | null>(null)
  const [updateFiles, setUpdateFiles] = useState<File[]>([])

  const [editingSummary, setEditingSummary] = useState(false)
  const [summaryDraft, setSummaryDraft] = useState('')

  const [editingClaimDeviceId, setEditingClaimDeviceId] = useState<
    number | null
  >(null)
  const [formDeviceTypeId, setFormDeviceTypeId] = useState<string | null>(null)
  const [formDeviceId, setFormDeviceId] = useState<string | null>(null)
  const [formSerial, setFormSerial] = useState('')
  const [formPart, setFormPart] = useState('')
  const [formNotes, setFormNotes] = useState('')

  const {
    data: claim,
    isLoading,
    isError,
  } = useGetClaimById({
    pathParams: { projectId: projectId!, claimId: claimId! },
    queryOptions: { enabled: !!projectId && !!claimId },
  })

  const { data: projectDevices } = useGetDevicesV2({
    pathParams: { projectId: projectId! },
    filters: {},
    queryOptions: { enabled: !!projectId && deviceModalOpened },
  })

  const { data: deviceTypes } = useGetDeviceTypes({
    queryOptions: { enabled: deviceModalOpened },
  })

  const { data: userType } = useGetUserType({})
  const isAdmin =
    userType?.name_short === 'admin' || userType?.name_short === 'superadmin'

  const { data: claimConfigs } = useGetClaimConfigs({
    pathParams: { projectId: projectId! },
    queryOptions: { enabled: !!projectId },
  })

  const addUpdate = useAddClaimUpdate()
  const updateClaim = useUpdateClaim()
  const addDevice = useAddClaimDevice()
  const updateClaimDeviceMut = useUpdateClaimDevice()
  const removeDevice = useRemoveClaimDevice()
  const deleteAttachment = useDeleteClaimAttachment()
  const uploadAttachment = useUploadClaimAttachment()
  const deleteClaim = useDeleteClaim()

  const attachmentsByUpdate = useMemo(() => {
    type Attachment = NonNullable<typeof claim>['attachments'][number]
    const map = new Map<number, Attachment[]>()
    for (const a of claim?.attachments ?? []) {
      if (a.claim_update_id == null) continue
      const list = map.get(a.claim_update_id) ?? []
      list.push(a)
      map.set(a.claim_update_id, list)
    }
    return map
  }, [claim])

  const editingClaimDevice = useMemo(
    () =>
      (claim?.devices ?? []).find(
        (d) => d.claim_device_id === editingClaimDeviceId,
      ) ?? null,
    [claim, editingClaimDeviceId],
  )

  const attachedDeviceIds = useMemo(() => {
    const ids = new Set((claim?.devices ?? []).map((d) => d.device_id))
    if (editingClaimDevice) ids.delete(editingClaimDevice.device_id)
    return ids
  }, [claim, editingClaimDevice])

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

  const deviceOptions = useMemo(() => {
    if (!formDeviceTypeId) return []
    const typeId = Number(formDeviceTypeId)
    return (projectDevices ?? [])
      .filter(
        (d) =>
          d.device_type_id === typeId &&
          !!d.name_long &&
          !attachedDeviceIds.has(d.device_id),
      )
      .map((d) => ({
        value: String(d.device_id),
        label: d.name_long as string,
      }))
  }, [projectDevices, attachedDeviceIds, formDeviceTypeId])

  useEffect(() => {
    if (!editingSummary && claim) {
      setSummaryDraft(claim.summary ?? '')
    }
  }, [claim, editingSummary])

  if (isLoading) return <PageLoader />
  if (isError || !claim) return <PageError />

  const claimTimelineActiveIndex = claim.updates.length - 1

  const canDeleteClaim =
    isAdmin &&
    (claimConfigs ?? []).some(
      (cfg) => cfg.claim_config_id === claim.claim_config_id,
    )

  const handleDeleteClaim = async () => {
    try {
      await deleteClaim.mutateAsync({
        projectId: projectId!,
        claimId: claim.claim_id,
      })
      notifications.show({
        title: 'Claim deleted',
        message: `Claim #${claim.claim_id} and its attachments removed`,
        color: 'green',
      })
      closeDeleteConfirm()
      navigate(`/projects/${projectId}/maintenance/warranty-claims`)
    } catch {
      notifications.show({
        title: 'Error',
        message: 'Failed to delete claim',
        color: 'red',
      })
    }
  }

  const handleSaveSummary = async () => {
    const next = summaryDraft.trim()
    if (next === (claim.summary ?? '')) {
      setEditingSummary(false)
      return
    }
    try {
      await updateClaim.mutateAsync({
        projectId: projectId!,
        claimId: claim.claim_id,
        data: { summary: next || null },
      })
      notifications.show({
        title: 'Summary updated',
        message: 'Claim summary saved',
        color: 'green',
      })
      setEditingSummary(false)
    } catch {
      notifications.show({
        title: 'Error',
        message: 'Failed to update summary',
        color: 'red',
      })
    }
  }

  const resetDeviceForm = () => {
    setEditingClaimDeviceId(null)
    setFormDeviceTypeId(null)
    setFormDeviceId(null)
    setFormSerial('')
    setFormPart('')
    setFormNotes('')
  }

  const handleOpenAddDevice = () => {
    resetDeviceForm()
    openDeviceModal()
  }

  const handleOpenEditDevice = (cd: (typeof claim.devices)[number]) => {
    const dev = (projectDevices ?? []).find((d) => d.device_id === cd.device_id)
    setEditingClaimDeviceId(cd.claim_device_id)
    setFormDeviceTypeId(dev ? String(dev.device_type_id) : null)
    setFormDeviceId(String(cd.device_id))
    setFormSerial(cd.oem_serial_number ?? '')
    setFormPart(cd.oem_part_number ?? '')
    setFormNotes(cd.notes ?? '')
    openDeviceModal()
  }

  const handleCloseDeviceModal = () => {
    closeDeviceModal()
    resetDeviceForm()
  }

  const handleChangeDeviceEvent = async (
    claimDeviceId: number,
    eventId: number | null,
  ) => {
    if (!claim) return
    try {
      await updateClaimDeviceMut.mutateAsync({
        projectId: projectId!,
        claimId: claim.claim_id,
        claimDeviceId,
        data: { event_id: eventId },
      })
    } catch {
      notifications.show({
        title: 'Error',
        message: 'Failed to update related event',
        color: 'red',
      })
    }
  }

  const handleSaveDevice = async () => {
    if (!formDeviceId) return
    try {
      if (editingClaimDeviceId) {
        await updateClaimDeviceMut.mutateAsync({
          projectId: projectId!,
          claimId: claim.claim_id,
          claimDeviceId: editingClaimDeviceId,
          data: {
            device_id: Number(formDeviceId),
            oem_serial_number: formSerial || null,
            oem_part_number: formPart || null,
            notes: formNotes || null,
          },
        })
      } else {
        await addDevice.mutateAsync({
          projectId: projectId!,
          claimId: claim.claim_id,
          data: {
            device_id: Number(formDeviceId),
            oem_serial_number: formSerial || undefined,
            oem_part_number: formPart || undefined,
            notes: formNotes || undefined,
          },
        })
      }
      notifications.show({
        title: editingClaimDeviceId ? 'Device updated' : 'Device added',
        message: editingClaimDeviceId
          ? 'Device changes saved'
          : 'Device attached to claim',
        color: 'green',
      })
      handleCloseDeviceModal()
    } catch {
      notifications.show({
        title: 'Error',
        message: editingClaimDeviceId
          ? 'Failed to update device'
          : 'Failed to add device',
        color: 'red',
      })
    }
  }

  const handleDeviceTypeChange = (value: string | null) => {
    setFormDeviceTypeId(value)
    setFormDeviceId(null)
  }

  const handleAddUpdate = async () => {
    try {
      const statusChanged = !!newStatus && newStatus !== claim.status
      const effectiveType = statusChanged
        ? ClaimUpdateTypeEnum.STATUS_CHANGE
        : updateType

      const data: {
        update_type: string
        from_status?: string
        to_status?: string
        message?: string
      } = {
        update_type: effectiveType,
        message: updateMessage || undefined,
      }

      if (statusChanged) {
        data.from_status = claim.status
        data.to_status = newStatus!
      }

      const res = await addUpdate.mutateAsync({
        projectId: projectId!,
        claimId: claim.claim_id,
        data,
      })
      const newClaimUpdateId: number | undefined = res?.data?.claim_update_id

      if (statusChanged) {
        await updateClaim.mutateAsync({
          projectId: projectId!,
          claimId: claim.claim_id,
          data: { status: newStatus },
        })
      }

      if (updateFiles.length > 0 && newClaimUpdateId) {
        await Promise.all(
          updateFiles.map((file) =>
            uploadAttachment.mutateAsync({
              projectId: projectId!,
              claimId: claim.claim_id,
              file,
              claimUpdateId: newClaimUpdateId,
            }),
          ),
        )
      }

      notifications.show({
        title: 'Update added',
        message: statusChanged
          ? `Claim status changed to ${newStatus!.replace('_', ' ')}`
          : 'Claim update recorded',
        color: 'green',
      })
      setUpdateMessage('')
      setNewStatus(null)
      setUpdateType(ClaimUpdateTypeEnum.NOTE)
      setUpdateFiles([])
      closeUpdate()
    } catch {
      notifications.show({
        title: 'Error',
        message: 'Failed to add update',
        color: 'red',
      })
    }
  }

  return (
    <Stack p="md" gap="lg">
      {/* Header */}
      <Group justify="space-between">
        <Group>
          <Button
            variant="subtle"
            size="xs"
            leftSection={<IconArrowLeft size={14} />}
            onClick={() =>
              navigate(`/projects/${projectId}/maintenance/warranty-claims`)
            }
          >
            Back
          </Button>
          <Title order={3}>
            Claim #{claim.claim_id}
            {claim.external_reference && ` — ${claim.external_reference}`}
          </Title>
          <Badge
            color={STATUS_COLORS[claim.status] ?? 'gray'}
            variant="light"
            size="lg"
          >
            {claim.status.replace('_', ' ')}
          </Badge>
        </Group>
        <Group gap="xs">
          <Button size="sm" onClick={openUpdate}>
            Add Update
          </Button>
          {canDeleteClaim && (
            <Menu position="bottom-end" withinPortal shadow="md">
              <Menu.Target>
                <Button
                  size="sm"
                  variant="default"
                  leftSection={<IconDotsVertical size={14} />}
                >
                  More Options
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item
                  color="red"
                  leftSection={<IconTrash size={14} />}
                  onClick={openDeleteConfirm}
                >
                  Delete Claim
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          )}
        </Group>
      </Group>

      <Grid gap="lg">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Stack gap="lg">
            {/* Summary info */}
            <Table withTableBorder>
              <Table.Tbody>
                <Table.Tr>
                  <Table.Td fw={500} w={160}>
                    OEM
                  </Table.Td>
                  <Table.Td>{claim.counterparty_name ?? '—'}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>Summary</Table.Td>
                  <Table.Td>
                    {editingSummary ? (
                      <Stack gap="xs">
                        <Textarea
                          value={summaryDraft}
                          onChange={(e) =>
                            setSummaryDraft(e.currentTarget.value)
                          }
                          autosize
                          minRows={2}
                          maxRows={8}
                          autoFocus
                        />
                        <Group gap="xs" justify="flex-end">
                          <Button
                            size="xs"
                            variant="default"
                            leftSection={<IconX size={14} />}
                            onClick={() => {
                              setSummaryDraft(claim.summary ?? '')
                              setEditingSummary(false)
                            }}
                          >
                            Cancel
                          </Button>
                          <Button
                            size="xs"
                            leftSection={<IconCheck size={14} />}
                            loading={updateClaim.isPending}
                            onClick={handleSaveSummary}
                          >
                            Save
                          </Button>
                        </Group>
                      </Stack>
                    ) : (
                      <Group gap="xs" justify="space-between" wrap="nowrap">
                        <Text size="sm">{claim.summary ?? '—'}</Text>
                        <ActionIcon
                          variant="subtle"
                          size="sm"
                          onClick={() => {
                            setSummaryDraft(claim.summary ?? '')
                            setEditingSummary(true)
                          }}
                        >
                          <IconEdit size={14} />
                        </ActionIcon>
                      </Group>
                    )}
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>Created</Table.Td>
                  <Table.Td>{formatDateTime(claim.created_at)}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>Last Updated</Table.Td>
                  <Table.Td>{formatDateTime(claim.updated_at)}</Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>

            {/* Devices */}
            <Stack gap="xs">
              <Group justify="space-between">
                <Title order={5}>Devices ({claim.devices.length})</Title>
                <Button
                  size="xs"
                  variant="default"
                  leftSection={<IconPlus size={14} />}
                  onClick={handleOpenAddDevice}
                >
                  Add Device
                </Button>
              </Group>
              {claim.devices.length > 0 ? (
                <Table withTableBorder striped>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Device</Table.Th>
                      <Table.Th w={260}>Related event</Table.Th>
                      <Table.Th>Serial #</Table.Th>
                      <Table.Th>Part #</Table.Th>
                      <Table.Th>Notes</Table.Th>
                      <Table.Th w={80} />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {claim.devices.map((d) => (
                      <Table.Tr key={d.claim_device_id}>
                        <Table.Td>
                          {d.device_name ?? `Device ${d.device_id}`}
                        </Table.Td>
                        <Table.Td>
                          <DeviceEventSelect
                            projectId={projectId!}
                            deviceId={d.device_id}
                            value={d.event_id ?? null}
                            onChange={(eventId) =>
                              handleChangeDeviceEvent(
                                d.claim_device_id,
                                eventId,
                              )
                            }
                          />
                        </Table.Td>
                        <Table.Td>{d.oem_serial_number ?? '—'}</Table.Td>
                        <Table.Td>{d.oem_part_number ?? '—'}</Table.Td>
                        <Table.Td>{d.notes ?? '—'}</Table.Td>
                        <Table.Td>
                          <Group gap={4} wrap="nowrap">
                            <ActionIcon
                              variant="subtle"
                              size="sm"
                              onClick={() => handleOpenEditDevice(d)}
                            >
                              <IconEdit size={14} />
                            </ActionIcon>
                            {claim.status === 'draft' && (
                              <ActionIcon
                                color="red"
                                variant="subtle"
                                size="sm"
                                onClick={() =>
                                  removeDevice.mutate({
                                    projectId: projectId!,
                                    claimId: claim.claim_id,
                                    claimDeviceId: d.claim_device_id,
                                  })
                                }
                              >
                                <IconTrash size={14} />
                              </ActionIcon>
                            )}
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              ) : (
                <Text size="sm" c="dimmed">
                  No devices attached to this claim.
                </Text>
              )}
            </Stack>

            {/* Attachments */}
            <Stack gap="xs">
              <Title order={5}>Attachments ({claim.attachments.length})</Title>
              {claim.attachments.length > 0 ? (
                <Stack gap="xs">
                  {claim.attachments.map((a) => (
                    <Group key={a.s3_key} gap="sm" wrap="nowrap">
                      <IconFileText size={16} />
                      {a.url ? (
                        <>
                          <Anchor href={a.url} target="_blank" size="sm">
                            {a.filename}
                          </Anchor>
                          <ActionIcon
                            variant="subtle"
                            size="sm"
                            aria-label={`Download ${a.filename}`}
                            onClick={() =>
                              void downloadRemoteFileBestEffort(
                                a.url!,
                                a.filename,
                              )
                            }
                          >
                            <IconDownload size={14} />
                          </ActionIcon>
                        </>
                      ) : (
                        <Text size="sm">{a.filename}</Text>
                      )}
                      <Text size="xs" c="dimmed">
                        {a.content_type}
                      </Text>
                      {claim.status === 'draft' && (
                        <ActionIcon
                          color="red"
                          variant="subtle"
                          size="sm"
                          aria-label={`Delete ${a.filename}`}
                          onClick={() =>
                            deleteAttachment.mutate({
                              projectId: projectId!,
                              claimId: claim.claim_id,
                              filename: a.filename,
                            })
                          }
                        >
                          <IconTrash size={14} />
                        </ActionIcon>
                      )}
                    </Group>
                  ))}
                </Stack>
              ) : (
                <Text size="sm" c="dimmed">
                  No attachments.
                </Text>
              )}
            </Stack>
          </Stack>
        </Grid.Col>

        {/* Timeline */}
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Stack gap="xs">
            <Title order={5}>Timeline</Title>
            {claim.updates.length > 0 ? (
              <Timeline
                active={claimTimelineActiveIndex}
                bulletSize={24}
                lineWidth={2}
              >
                {claim.updates.map((u) => (
                  <Timeline.Item
                    key={u.claim_update_id}
                    bullet={
                      UPDATE_ICONS[u.update_type] ?? <IconClock size={14} />
                    }
                    title={
                      <Group gap="xs">
                        <Text size="sm" fw={500}>
                          {u.update_type.replace('_', ' ')}
                        </Text>
                        {u.to_status && (
                          <Badge
                            size="xs"
                            color={STATUS_COLORS[u.to_status] ?? 'gray'}
                            variant="light"
                          >
                            → {u.to_status.replace('_', ' ')}
                          </Badge>
                        )}
                      </Group>
                    }
                  >
                    {u.message && <Text size="sm">{u.message}</Text>}
                    {(attachmentsByUpdate.get(u.claim_update_id) ?? []).map(
                      (a) => (
                        <Group key={a.s3_key} gap={4} wrap="nowrap">
                          <IconFileText size={12} />
                          {a.url ? (
                            <>
                              <Anchor href={a.url} target="_blank" size="xs">
                                {a.filename}
                              </Anchor>
                              <ActionIcon
                                variant="subtle"
                                size="xs"
                                aria-label={`Download ${a.filename}`}
                                onClick={() =>
                                  void downloadRemoteFileBestEffort(
                                    a.url!,
                                    a.filename,
                                  )
                                }
                              >
                                <IconDownload size={12} />
                              </ActionIcon>
                            </>
                          ) : (
                            <Text size="xs">{a.filename}</Text>
                          )}
                        </Group>
                      ),
                    )}
                    <Text size="xs" c="dimmed">
                      {u.user_name ?? u.user_id} ·{' '}
                      {formatDateTime(u.created_at)}
                    </Text>
                  </Timeline.Item>
                ))}
              </Timeline>
            ) : (
              <Text size="sm" c="dimmed">
                No updates yet.
              </Text>
            )}
          </Stack>
        </Grid.Col>
      </Grid>

      {/* Add / Edit Device Modal */}
      <Modal
        opened={deviceModalOpened}
        onClose={handleCloseDeviceModal}
        title={editingClaimDeviceId ? 'Edit Device' : 'Add Device to Claim'}
      >
        <Stack gap="md">
          <Select
            label="Device Type"
            placeholder="Select device type…"
            data={deviceTypeOptions}
            value={formDeviceTypeId}
            onChange={handleDeviceTypeChange}
            searchable
            required
            nothingFoundMessage="No device types"
          />
          <Select
            label="Device"
            placeholder={
              formDeviceTypeId ? 'Search devices…' : 'Pick a device type first'
            }
            data={deviceOptions}
            value={formDeviceId}
            onChange={setFormDeviceId}
            searchable
            required
            disabled={!formDeviceTypeId}
            nothingFoundMessage="No matching devices"
          />
          <TextInput
            label="OEM Serial #"
            value={formSerial}
            onChange={(e) => setFormSerial(e.currentTarget.value)}
          />
          <TextInput
            label="OEM Part #"
            value={formPart}
            onChange={(e) => setFormPart(e.currentTarget.value)}
          />
          <Textarea
            label="Notes"
            value={formNotes}
            onChange={(e) => setFormNotes(e.currentTarget.value)}
            autosize
            minRows={2}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={handleCloseDeviceModal}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveDevice}
              loading={addDevice.isPending || updateClaimDeviceMut.isPending}
              disabled={!formDeviceId}
            >
              {editingClaimDeviceId ? 'Save Changes' : 'Add Device'}
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Delete Claim Confirmation */}
      <Modal
        opened={deleteConfirmOpened}
        onClose={closeDeleteConfirm}
        title={
          <Group gap="xs">
            <IconAlertTriangle size={18} color="var(--mantine-color-red-6)" />
            <Text fw={600}>Delete Claim</Text>
          </Group>
        }
      >
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to delete{' '}
            <Text span fw={600}>
              Claim #{claim.claim_id}
              {claim.external_reference && ` — ${claim.external_reference}`}
            </Text>
            ?
          </Text>
          <Text size="sm" c="red">
            This action is permanent and cannot be undone:
          </Text>
          <List size="sm" spacing={4}>
            <List.Item>
              The entire claim, including all timeline updates and device
              assignments, will be removed.
            </List.Item>
            <List.Item>
              All attachments will be permanently deleted from storage.
            </List.Item>
          </List>
          <Group justify="flex-end">
            <Button variant="default" onClick={closeDeleteConfirm}>
              Cancel
            </Button>
            <Button
              color="red"
              leftSection={<IconTrash size={14} />}
              loading={deleteClaim.isPending}
              onClick={handleDeleteClaim}
            >
              Delete Permanently
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Add Update Modal */}
      <Modal opened={updateOpened} onClose={closeUpdate} title="Add Update">
        <Stack gap="md">
          <Select
            label="Update Type"
            data={UPDATE_TYPE_OPTIONS}
            value={updateType}
            onChange={(v) => setUpdateType(v ?? ClaimUpdateTypeEnum.NOTE)}
          />

          <Select
            label="Change Status (optional)"
            description={`Current: ${claim.status.replace('_', ' ')}`}
            placeholder="Leave unchanged"
            data={STATUS_OPTIONS.filter((o) => o.value !== claim.status)}
            value={newStatus}
            onChange={setNewStatus}
            clearable
          />

          <Textarea
            label="Message (optional)"
            placeholder="Add notes or details..."
            value={updateMessage}
            onChange={(e) => setUpdateMessage(e.currentTarget.value)}
            minRows={3}
          />

          <Box>
            <Text size="sm" fw={500} mb={4}>
              Attachments (optional)
            </Text>
            <Dropzone
              onDrop={(dropped) =>
                setUpdateFiles((prev) => [...prev, ...dropped])
              }
              maxSize={CLAIM_ATTACHMENT_MAX_SIZE_BYTES}
              multiple
            >
              <Group
                justify="center"
                gap="md"
                mih={70}
                style={{ pointerEvents: 'none' }}
              >
                <Dropzone.Accept>
                  <IconUpload size={28} />
                </Dropzone.Accept>
                <Dropzone.Reject>
                  <IconX size={28} />
                </Dropzone.Reject>
                <Dropzone.Idle>
                  <IconFile size={28} />
                </Dropzone.Idle>
                <Box>
                  <Text size="sm">Drop files here or click to select</Text>
                  <Text size="xs" c="dimmed">
                    Up to 40 MB each
                  </Text>
                </Box>
              </Group>
            </Dropzone>
            {updateFiles.length > 0 && (
              <Stack gap={4} mt="xs">
                {updateFiles.map((f, i) => {
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
                          setUpdateFiles((prev) =>
                            prev.filter((_, j) => j !== i),
                          )
                        }
                      >
                        <IconTrash size={14} />
                      </ActionIcon>
                    </Group>
                  )
                })}
              </Stack>
            )}
          </Box>

          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => {
                setUpdateFiles([])
                closeUpdate()
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleAddUpdate}
              loading={
                addUpdate.isPending ||
                updateClaim.isPending ||
                uploadAttachment.isPending
              }
            >
              Save Update
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}
