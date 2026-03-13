import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import {
  SensorType,
  useCreateSensorTypeMutation,
  useGetSensorTypes,
  useUpdateSensorTypeMutation,
} from '@/api/v1/operational/sensor_types'
import { PageLoader } from '@/components/Loading'
import {
  ActionIcon,
  Button,
  Group,
  Modal,
  Popover,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core'
import { hasLength, useForm } from '@mantine/form'
import { useDisclosure } from '@mantine/hooks'
import { IconEdit, IconPlus } from '@tabler/icons-react'
import { useState } from 'react'

const columns = [
  { key: 'sensor_type_id', header: 'ID', align: 'center' as const },
  { key: 'name_short', header: 'Short Name' },
  { key: 'name_long', header: 'Long Name' },
  { key: 'name_metric', header: 'Metric Name' },
  { key: 'unit', header: 'Unit', align: 'center' as const },
  { key: 'device_type_id', header: 'Device Type' },
  { key: 'description', header: 'Description' },
  {
    key: 'actions',
    header: 'Actions',
    align: 'center' as const,
    filterable: false,
    sortable: false,
  },
]

const SensorTypes = () => {
  const [isModalOpen, { open, close }] = useDisclosure(false)
  const [isConfirmOpen, { open: openConfirm, close: closeConfirm }] =
    useDisclosure(false)
  const [editingSensorType, setEditingSensorType] = useState<SensorType | null>(
    null,
  )
  const [columnFilters, setColumnFilters] = useState<Record<string, string>>({})
  const [sortConfig, setSortConfig] = useState<{
    key: string
    direction: 'asc' | 'desc'
  } | null>({ key: 'sensor_type_id', direction: 'asc' })

  const sensorTypes = useGetSensorTypes({})
  const deviceTypes = useGetDeviceTypes({})
  const createSensorType = useCreateSensorTypeMutation()
  const updateSensorType = useUpdateSensorTypeMutation()

  // Get unique units from existing sensor types
  const getUniqueUnits = () => {
    if (!sensorTypes.data) return []
    const units = sensorTypes.data
      .map((sensorType) => sensorType.unit)
      .filter((unit) => unit !== null && unit !== '')
    return [...new Set(units)]
  }

  const form = useForm({
    initialValues: {
      device_type_id: '',
      name_short: '', // noqa: hardcoded-name-short
      name_long: '',
      name_metric: '',
      unit: '',
      description: '',
    },
    validate: {
      name_short: (value) => {
        if (!value || value.length === 0) {
          return 'Short name is required'
        }
        const isDuplicate = sensorTypes.data?.some(
          (sensorType) =>
            sensorType.name_short === value &&
            sensorType.sensor_type_id !== editingSensorType?.sensor_type_id,
        )
        if (isDuplicate) {
          return 'A sensor type with this short name already exists'
        }
        return null
      },
      name_long: hasLength({ min: 1 }, 'Long name is required'),
      name_metric: hasLength({ min: 1 }, 'Metric name is required'),
    },
  })

  const handleEdit = (sensorType: SensorType) => {
    setEditingSensorType(sensorType)
    form.setValues({
      device_type_id: sensorType.device_type_id.toString(),
      name_short: sensorType.name_short,
      name_long: sensorType.name_long,
      name_metric: sensorType.name_metric,
      unit: sensorType.unit || '',
      description: sensorType.description || '',
    })
    open()
  }

  const handleAdd = () => {
    setEditingSensorType(null)
    form.reset()
    open()
  }

  const handleDeviceTypeChange = (deviceTypeId: string | null) => {
    if (deviceTypeId && deviceTypes.data) {
      const selectedDeviceType = deviceTypes.data.find(
        (dt) => dt.device_type_id.toString() === deviceTypeId,
      )
      if (selectedDeviceType) {
        form.setFieldValue('device_type_id', deviceTypeId)
        form.setFieldValue('name_long', selectedDeviceType.name_long)
      }
    } else {
      form.setFieldValue('device_type_id', '')
      form.setFieldValue('name_long', '')
    }
  }

  const handleSubmit = async (values: typeof form.values) => {
    try {
      const sensorTypeData = {
        ...values,
        device_type_id: parseInt(values.device_type_id),
      }

      if (editingSensorType) {
        await updateSensorType.mutateAsync({
          sensorTypeId: editingSensorType.sensor_type_id,
          sensorType: {
            ...editingSensorType,
            ...sensorTypeData,
          },
        })
      } else {
        await createSensorType.mutateAsync({
          ...sensorTypeData,
          sensor_type_id: 0,
        })
      }
      close()
      closeConfirm()
    } catch (error) {
      console.error('Error saving sensor type:', error)
    }
  }

  const handleUpdateClick = () => {
    openConfirm()
  }

  const getCellText = (sensorType: SensorType, key: string): string => {
    switch (key) {
      case 'unit':
      case 'description':
        return (sensorType[key as keyof SensorType] as string) || '-'
      case 'device_type_id': {
        const dt = deviceTypes.data?.find(
          (d) => d.device_type_id === sensorType.device_type_id,
        )
        return dt ? dt.name_short : '-' // noqa: hardcoded-name-short
      }
      case 'actions':
        return ''
      default:
        return String(sensorType[key as keyof SensorType] ?? '')
    }
  }

  const renderCell = (sensorType: SensorType, key: string): React.ReactNode => {
    switch (key) {
      case 'unit':
      case 'description':
        return (
          <Text size="sm">
            {(sensorType[key as keyof SensorType] as string) || '-'}
          </Text>
        )
      case 'device_type_id': {
        const dt = deviceTypes.data?.find(
          (d) => d.device_type_id === sensorType.device_type_id,
        )
        return <Text size="sm">{dt ? dt.name_short : '-'}</Text> // noqa: hardcoded-name-short
      }
      case 'actions':
        return (
          <ActionIcon
            variant="subtle"
            color="blue"
            onClick={() => handleEdit(sensorType)}
          >
            <IconEdit style={{ width: 16, height: 16 }} />
          </ActionIcon>
        )
      default:
        return String(sensorType[key as keyof SensorType] ?? '')
    }
  }

  const handleSort = (key: string) => {
    setSortConfig((current) => {
      if (!current || current.key !== key) {
        return { key, direction: 'asc' }
      }
      if (current.direction === 'asc') {
        return { key, direction: 'desc' }
      }
      return null
    })
  }

  const filtered = (sensorTypes.data ?? []).filter((row) =>
    columns.every((col) => {
      const filter = columnFilters[col.key]
      if (!filter) return true
      if (col.filterable === false) return true
      const cellText = getCellText(row, col.key)
      return cellText.toLowerCase().includes(filter.toLowerCase())
    }),
  )

  const sortedData = sortConfig
    ? [...filtered].sort((a, b) => {
        const aVal = getCellText(a, sortConfig.key)
        const bVal = getCellText(b, sortConfig.key)
        const aNum = Number(aVal)
        const bNum = Number(bVal)
        const bothNumeric =
          aVal !== '' && bVal !== '' && !isNaN(aNum) && !isNaN(bNum)
        const cmp = bothNumeric
          ? aNum - bNum
          : aVal.localeCompare(bVal, undefined, { numeric: true })
        return sortConfig.direction === 'asc' ? cmp : -cmp
      })
    : filtered

  if (sensorTypes.isLoading || deviceTypes.isLoading) {
    return <PageLoader />
  }

  return (
    <Stack p="md">
      <Group justify="space-between">
        <Title order={1}>Sensor Types</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={handleAdd}>
          Add Sensor Type
        </Button>
      </Group>

      <Table.ScrollContainer minWidth={1000}>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              {columns.map((col) => {
                const isSortable = col.sortable !== false
                return (
                  <Table.Th
                    key={col.key}
                    style={{
                      textAlign: col.align,
                      cursor: isSortable ? 'pointer' : undefined,
                    }}
                    onClick={isSortable ? () => handleSort(col.key) : undefined}
                  >
                    {col.header}
                    {sortConfig?.key === col.key && (
                      <span>
                        {sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}
                      </span>
                    )}
                  </Table.Th>
                )
              })}
            </Table.Tr>
            <Table.Tr>
              {columns.map((col) => (
                <Table.Th key={`${col.key}-filter`}>
                  {col.filterable !== false ? (
                    <TextInput
                      size="xs"
                      placeholder="Filter..."
                      value={columnFilters[col.key] ?? ''}
                      onChange={(e) => {
                        const value = e.currentTarget?.value ?? ''
                        setColumnFilters((prev) => ({
                          ...prev,
                          [col.key]: value,
                        }))
                      }}
                    />
                  ) : null}
                </Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {sortedData.map((sensorType) => (
              <Table.Tr key={sensorType.sensor_type_id}>
                {columns.map((col) => (
                  <Table.Td key={col.key} style={{ textAlign: col.align }}>
                    {renderCell(sensorType, col.key)}
                  </Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>

      <Modal
        opened={isModalOpen}
        onClose={close}
        title={editingSensorType ? 'Edit Sensor Type' : 'Add Sensor Type'}
        size="md"
      >
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack gap="md">
            {editingSensorType && (
              <Text
                size="sm"
                c="red"
                p="sm"
                style={{
                  borderRadius: '4px',
                  border: '1px solid var(--mantine-color-red-3)',
                }}
              >
                <strong>⚠️ WARNING:</strong> Be extremely careful when editing
                sensor types, especially the short name. Changes to the short
                name can affect existing data/scripts and may cause issues in
                the system.
              </Text>
            )}
            {!editingSensorType && (
              <Tooltip
                label="Select a device type to automatically pre-populate the long name"
                position="top"
                multiline
              >
                <Select
                  label="Device Type"
                  placeholder="Select a device type..."
                  data={
                    deviceTypes.data?.map((dt) => ({
                      value: dt.device_type_id.toString(),
                      label: `${dt.name_long} (${dt.name_short})`,
                    })) || []
                  }
                  value={form.values.device_type_id}
                  onChange={handleDeviceTypeChange}
                  searchable
                  clearable
                  required
                />
              </Tooltip>
            )}
            <Tooltip
              label="Device comes first, then a full name for the sensor type. Each word starts with a capital letter. Example: PV Inverter AC Power, Tracker Position"
              position="top"
              multiline
            >
              <TextInput
                label="Long Name"
                placeholder="e.g., PV Inverter AC Power"
                required
                {...form.getInputProps('name_long')}
                onChange={(event) => {
                  const longName = event.currentTarget.value
                  const shortName = longName
                    .toLowerCase()
                    .replace(/\s+/g, '_')
                    .replace(/[^a-z0-9_]/g, '')
                  form.setFieldValue('name_short', shortName)
                  setTimeout(() => form.validateField('name_short'), 0)
                  form.getInputProps('name_long').onChange(event)
                }}
              />
            </Tooltip>
            <Tooltip
              label="Automatically generated from the Long Name. All lowercase with underscores instead of spaces. You can edit this field if needed."
              position="top"
              multiline
            >
              <TextInput
                label="Short Name"
                placeholder="e.g., pv_inverter_ac_power"
                required
                {...form.getInputProps('name_short')}
                onChange={(event) => {
                  form.validateField('name_short')
                  form.getInputProps('name_short').onChange(event)
                }}
              />
            </Tooltip>
            <Tooltip
              label="Same as Long Name but remove the device name that is prepended. Example: If Long Name is 'Inverter AC Power', Metric Name should be 'AC Power'"
              position="top"
              multiline
            >
              <TextInput
                label="Metric Name"
                placeholder="e.g., AC Power"
                required
                {...form.getInputProps('name_metric')}
              />
            </Tooltip>
            <Popover position="top" withArrow shadow="md">
              <Popover.Target>
                <TextInput
                  label="Unit"
                  placeholder="W/m2"
                  {...form.getInputProps('unit')}
                />
              </Popover.Target>
              <Popover.Dropdown>
                <Stack gap="xs">
                  <Text size="sm" fw={500}>
                    Unit of measurement (optional)
                  </Text>
                  <Text size="xs" c="dimmed">
                    Examples: kW, %, °C, V
                  </Text>
                  <Text size="xs" fw={500}>
                    Existing units:
                  </Text>
                  <Text size="xs">
                    {getUniqueUnits().length > 0
                      ? getUniqueUnits().join(', ')
                      : 'No existing units found'}
                  </Text>
                  <Text size="xs" c="dimmed" style={{ fontStyle: 'italic' }}>
                    Try to stick to existing units when possible, but you can
                    type a new one if necessary.
                  </Text>
                </Stack>
              </Popover.Dropdown>
            </Popover>
            <TextInput
              label="Description"
              placeholder="Optional description of the sensor type"
              {...form.getInputProps('description')}
            />
            <Group justify="flex-end" gap="sm">
              <Button
                variant="subtle"
                onClick={close}
                disabled={
                  createSensorType.isPending || updateSensorType.isPending
                }
              >
                Cancel
              </Button>
              <Button
                type={editingSensorType ? 'button' : 'submit'}
                loading={
                  createSensorType.isPending || updateSensorType.isPending
                }
                onClick={editingSensorType ? handleUpdateClick : undefined}
              >
                {editingSensorType ? 'Update' : 'Create'}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {/* Confirmation Modal for Updates */}
      <Modal
        opened={isConfirmOpen}
        onClose={closeConfirm}
        title="Confirm Update"
        size="sm"
      >
        <Stack gap="md">
          <Text>
            Are you absolutely sure you want to update this sensor type? Changes
            to sensor types, especially the short name, can have serious
            consequences for existing data and system functionality.
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button variant="subtle" onClick={closeConfirm}>
              Cancel
            </Button>
            <Button
              color="red"
              onClick={() => {
                form.onSubmit(handleSubmit)()
              }}
              loading={updateSensorType.isPending}
            >
              Yes, Update Sensor Type
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}

export default SensorTypes
