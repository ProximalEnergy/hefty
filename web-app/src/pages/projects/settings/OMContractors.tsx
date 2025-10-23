import { HexLoader } from '@/HexLoader'
import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import {
  OMContractorScope,
  useCreateOMContractorScope,
  useDeleteOMContractorScope,
  useGetOMContractorScopes,
  useUpdateOMContractorScope,
} from '@/api/v1/operational/project/om_contractors'
import { useGetProject } from '@/api/v1/operational/projects'
import CompanyLookup from '@/components/CompanyLookup'
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { isEmail, useForm } from '@mantine/form'
import { useDisclosure } from '@mantine/hooks'
import { IconEdit, IconPlus, IconTrash } from '@tabler/icons-react'
import { useMemo, useState } from 'react'

export default function OMContractors({ projectId }: { projectId: string }) {
  const project = useGetProject({
    pathParams: { projectId },
    queryParams: { deep: true },
    queryOptions: { enabled: !!projectId },
  })

  const deviceTypes = useGetDeviceTypes({
    // Backend supports filtering by project_id to only return device types in use
    queryOptions: { enabled: !!projectId },
  })

  const omScopes = useGetOMContractorScopes({
    pathParams: { projectId },
    queryOptions: { enabled: !!projectId },
  })

  // Company selection now handled by CompanyLookup

  const isLoading =
    project.isLoading || deviceTypes.isLoading || omScopes.isLoading

  const usedDeviceTypeIds: number[] = Array.isArray(
    project.data?.spec?.used_device_type_ids,
  )
    ? (project.data.spec.used_device_type_ids as number[])
    : []

  const filteredDeviceTypes = (deviceTypes.data || []).filter(
    (dt) =>
      usedDeviceTypeIds.includes(dt.device_type_id) && dt.device_type_id !== 0,
  )

  // Desired ordering (PV + Storage combined order covers PV-only and BESS-only subsets)
  const DEVICE_TYPE_ORDER = [
    1, 5, 7, 16, 15, 2, 3, 9, 28, 29, 35, 17, 12, 25, 13, 32, 33, 11, 27, 34,
  ]

  const orderedDeviceTypes = useMemo(() => {
    const indexOf = (id: number) => {
      const idx = DEVICE_TYPE_ORDER.indexOf(id)
      return idx === -1 ? Number.MAX_SAFE_INTEGER : idx
    }
    return [...filteredDeviceTypes].sort(
      (a, b) => indexOf(a.device_type_id) - indexOf(b.device_type_id),
    )
  }, [filteredDeviceTypes])

  // Add Scope Modal state
  const [opened, { open, close }] = useDisclosure(false)
  const [submitError, setSubmitError] = useState<string>('')
  const [editingScope, setEditingScope] = useState<OMContractorScope | null>(
    null,
  )
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)
  const [confirmOpened, confirmHandlers] = useDisclosure(false)

  // Custom phone validator to prevent invalid entries like +123
  const validatePhone = (value: string) => {
    if (!value) return null // Allow empty phone numbers

    // Disallow any letters
    if (/[A-Za-z]/.test(value)) {
      return 'Phone number cannot contain letters'
    }

    // Remove all non-digit characters except the leading +
    const sanitized = value.replace(/[^\d+]/g, '')

    // Must start with + and have at least 7 digits total (country code + number)
    // E.164 format: +[country code][number] with total length 7-15 digits
    const e164Regex = /^\+[1-9]\d{6,14}$/

    if (!e164Regex.test(sanitized)) {
      return 'Enter a valid phone number with country code (e.g., +15551234567)'
    }

    return null
  }

  const form = useForm({
    mode: 'controlled',
    validateInputOnBlur: true,
    initialValues: {
      selectedCompanyId: null as string | null,
      selectedDeviceTypeIds: [] as number[],
      addressee: '',
      email: '',
      phone: '',
    },
    validate: {
      phone: validatePhone,
      email: (value) =>
        value
          ? isEmail('Enter a valid email, e.g., name@example.com')(value)
          : null,
    },
  })
  const createScope = useCreateOMContractorScope({ projectId })
  const updateScope = useUpdateOMContractorScope({ projectId })
  const deleteScope = useDeleteOMContractorScope({ projectId })

  // Company options moved into CompanyLookup

  const deviceTypeChecks = useMemo(
    () =>
      orderedDeviceTypes.map((dt) => (
        <Checkbox
          key={dt.device_type_id}
          label={dt.name_long}
          checked={form.values.selectedDeviceTypeIds.includes(
            dt.device_type_id,
          )}
          onChange={(e) => {
            const checked = e.currentTarget.checked
            const currentIds = form.values.selectedDeviceTypeIds
            const newIds = checked
              ? [...currentIds, dt.device_type_id]
              : currentIds.filter((id) => id !== dt.device_type_id)
            form.setFieldValue('selectedDeviceTypeIds', newIds)
          }}
        />
      )),
    [orderedDeviceTypes, form.values.selectedDeviceTypeIds],
  )

  const handleSubmit = form.onSubmit(async (values) => {
    if (!values.selectedCompanyId || values.selectedDeviceTypeIds.length === 0)
      return

    setSubmitError('')
    try {
      if (editingScope) {
        await updateScope.mutateAsync({
          om_contractor_scope_id: editingScope.om_contractor_scope_id,
          device_type_ids: values.selectedDeviceTypeIds,
          contractor_addressee: values.addressee || undefined,
          contractor_email: values.email || undefined,
          contractor_phone: values.phone || undefined,
        })
      } else {
        await createScope.mutateAsync({
          company_id: values.selectedCompanyId,
          device_type_ids: values.selectedDeviceTypeIds,
          contractor_addressee: values.addressee || undefined,
          contractor_email: values.email || undefined,
          contractor_phone: values.phone || undefined,
        })
      }
    } catch (err: any) {
      // Best-effort message from axios error
      const apiMsg =
        err?.response?.data?.detail || err?.message || 'Submit failed'
      setSubmitError(String(apiMsg))
      return
    }
    form.reset()
    setEditingScope(null)
    close()
  })

  const handleEdit = (scope: OMContractorScope) => {
    setEditingScope(scope)
    form.setValues({
      selectedCompanyId: scope.company_id,
      selectedDeviceTypeIds: scope.scope_json?.device_type_ids || [],
      addressee: scope.contractor_addressee || '',
      email: scope.contractor_email || '',
      phone: scope.contractor_phone || '',
    })
    open()
  }

  const handleClose = () => {
    setEditingScope(null)
    form.reset()
    setSubmitError('')
    close()
  }

  const contractorRows = (omScopes.data || []).map((scope) => {
    const deviceTypeNames = (scope.scope_json?.device_type_ids || [])
      .map((id: number) => {
        const dt = filteredDeviceTypes.find((d) => d.device_type_id === id)
        return dt?.name_long || `Device Type ${id}`
      })
      .join(', ')

    return (
      <Table.Tr key={scope.om_contractor_scope_id}>
        <Table.Td>
          <Text size="sm" fw={500}>
            {scope.company_name_long ||
              scope.company_name_short ||
              scope.company_id}
          </Text>
        </Table.Td>
        <Table.Td>
          <Text size="sm">{scope.contractor_addressee || 'Not set'}</Text>
        </Table.Td>
        <Table.Td>
          <Text size="sm">{scope.contractor_email || 'Not set'}</Text>
        </Table.Td>
        <Table.Td>
          <Text size="sm">{scope.contractor_phone || 'Not set'}</Text>
        </Table.Td>
        <Table.Td>
          <Text size="sm" c="dimmed">
            {deviceTypeNames || 'No device types'}
          </Text>
        </Table.Td>
        <Table.Td>
          <Group gap={8}>
            <ActionIcon
              variant="light"
              size="sm"
              onClick={() => handleEdit(scope)}
            >
              <IconEdit size={16} />
            </ActionIcon>
            <ActionIcon
              color="red"
              variant="light"
              size="sm"
              onClick={() => {
                setConfirmDeleteId(scope.om_contractor_scope_id)
                confirmHandlers.open()
              }}
            >
              <IconTrash size={16} />
            </ActionIcon>
          </Group>
        </Table.Td>
      </Table.Tr>
    )
  })

  const rows = orderedDeviceTypes.map((dt) => {
    const coveringScopes = (omScopes.data || []).filter((s) =>
      Array.isArray(s.scope_json?.device_type_ids)
        ? s.scope_json.device_type_ids.includes(dt.device_type_id)
        : false,
    )

    return (
      <Table.Tr key={dt.device_type_id}>
        <Table.Td>
          <Text size="sm" fw={500}>
            {dt.name_long}
          </Text>
        </Table.Td>
        <Table.Td>
          {coveringScopes.length > 0 ? (
            <Group gap={8} wrap="wrap">
              {coveringScopes.map((s) => (
                <Badge key={s.om_contractor_scope_id} variant="light">
                  {s.company_name_short || s.company_name_long || 'Contractor'}
                </Badge>
              ))}
            </Group>
          ) : (
            <Badge color="gray" variant="light">
              None
            </Badge>
          )}
        </Table.Td>
      </Table.Tr>
    )
  })

  return (
    <Stack h="100%" p="md">
      {/* Contractor List Table */}
      <Card withBorder p="md">
        <Stack gap="md">
          <Group justify="space-between" align="center">
            <Group align="center" gap="xs">
              <Title order={3} mb={0}>
                O&M Contractors
              </Title>
              <ActionIcon variant="light" size="sm" onClick={open}>
                <IconPlus size={16} />
              </ActionIcon>
            </Group>
          </Group>

          {isLoading && <HexLoader />}

          {!isLoading && (omScopes.data || []).length === 0 && (
            <Alert title="No contractors" color="gray" variant="light">
              No O&M contractors have been assigned to this project yet. Click
              the + button to add a new contractor and scope.
            </Alert>
          )}

          {!isLoading && (omScopes.data || []).length > 0 && (
            <Table striped highlightOnHover withTableBorder withColumnBorders>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Company</Table.Th>
                  <Table.Th>Contact</Table.Th>
                  <Table.Th>Email</Table.Th>
                  <Table.Th>Phone</Table.Th>
                  <Table.Th>Device Types</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {contractorRows}
                <Table.Tr>
                  <Table.Td colSpan={6}>
                    <Button
                      size="xs"
                      variant="light"
                      leftSection={<IconPlus size={14} />}
                      onClick={open}
                    >
                      Add New
                    </Button>
                  </Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>
          )}
        </Stack>
      </Card>

      {/* Device Type Coverage Table */}
      <Card withBorder p="md">
        <Stack gap="md">
          <Title order={4} mb={0}>
            Device Type Coverage
          </Title>

          {isLoading && <HexLoader />}

          {!isLoading && filteredDeviceTypes.length === 0 && (
            <Alert title="No device types" color="gray" variant="light">
              No device types found for this project.
            </Alert>
          )}

          {!isLoading && filteredDeviceTypes.length > 0 && (
            <Table striped highlightOnHover withTableBorder withColumnBorders>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Device Type</Table.Th>
                  <Table.Th>Covered By O&M Contractor(s)</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>{rows}</Table.Tbody>
            </Table>
          )}
        </Stack>
      </Card>

      <Modal
        opened={opened}
        onClose={handleClose}
        title={
          <Title order={4}>
            {editingScope ? 'Edit Contractor Scope' : 'Add Contractor Scope'}
          </Title>
        }
        size="lg"
      >
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Select a company and the device types they cover for O&M services.
            </Text>
            {submitError && (
              <Alert color="red" variant="light" title="Could not save">
                {submitError}
              </Alert>
            )}
            {editingScope ? (
              <TextInput
                label="Company"
                value={
                  editingScope.company_name_long ||
                  editingScope.company_name_short ||
                  editingScope.company_id
                }
                disabled
              />
            ) : (
              <CompanyLookup
                selectedCompanyId={form.values.selectedCompanyId}
                onSelect={(id) => form.setFieldValue('selectedCompanyId', id)}
                autoFocus
              />
            )}

            {/* Delete button removed from edit modal as requested */}

            <Stack gap="xs">
              <Title order={6}>Device Types</Title>
              <Stack gap={6}>{deviceTypeChecks}</Stack>
            </Stack>

            <Stack gap="xs">
              <Title order={6}>Contact Details</Title>
              <TextInput
                label="Addressee"
                placeholder="Name of contractor contact"
                {...form.getInputProps('addressee')}
              />
              <TextInput
                label="Email"
                type="email"
                placeholder="name@example.com"
                {...form.getInputProps('email')}
              />
              <TextInput
                label="Phone"
                placeholder="+1 555 123 4567"
                {...form.getInputProps('phone')}
                onChange={(e) => {
                  const value = e.currentTarget.value
                  // Do not coerce or reformat while typing; just set value
                  form.setFieldValue('phone', value)
                }}
                onBlur={(e) => {
                  let v = e.currentTarget.value.trim()
                  if (!v) {
                    form.setFieldValue('phone', '')
                    return
                  }
                  // Remove all characters except digits and plus
                  v = v.replace(/[^\d+]/g, '')
                  // Ensure single leading + and none elsewhere
                  v = v.replace(/(?!^)\+/g, '')
                  if (v[0] !== '+') {
                    v = `+${v.replace(/\D/g, '')}`
                  }
                  form.setFieldValue('phone', v)
                  form.validateField('phone')
                }}
              />
            </Stack>

            <Group justify="flex-end" mt="sm">
              <Button variant="default" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                loading={createScope.isPending || updateScope.isPending}
                disabled={
                  !form.values.selectedCompanyId ||
                  form.values.selectedDeviceTypeIds.length === 0
                }
              >
                {editingScope ? 'Update' : 'Save'}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
      <Modal
        opened={confirmOpened}
        onClose={() => {
          setConfirmDeleteId(null)
          confirmHandlers.close()
        }}
        title={<Title order={5}>Confirm deletion</Title>}
        centered
      >
        <Stack gap="md">
          <Text>Are you sure you want to delete this contractor scope?</Text>
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => {
                setConfirmDeleteId(null)
                confirmHandlers.close()
              }}
            >
              Cancel
            </Button>
            <Button
              color="red"
              loading={deleteScope.isPending}
              onClick={async () => {
                if (confirmDeleteId == null) return
                try {
                  await deleteScope.mutateAsync({
                    om_contractor_scope_id: confirmDeleteId,
                  })
                  setConfirmDeleteId(null)
                  confirmHandlers.close()
                  if (
                    editingScope &&
                    editingScope.om_contractor_scope_id === confirmDeleteId
                  ) {
                    handleClose()
                  }
                } catch (err: any) {
                  const apiMsg =
                    err?.response?.data?.detail ||
                    err?.message ||
                    'Delete failed'
                  setSubmitError(String(apiMsg))
                }
              }}
            >
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}
