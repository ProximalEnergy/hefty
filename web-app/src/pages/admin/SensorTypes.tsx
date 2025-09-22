import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import {
  useCreateSensorTypeMutation,
  useGetSensorTypes,
  useUpdateSensorTypeMutation,
} from '@/api/v1/operational/sensor_types'
import { PageLoader } from '@/components/Loading'
import { SensorType } from '@/hooks/types'
import {
  ActionIcon,
  Button,
  Group,
  Modal,
  Popover,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core'
import { hasLength, useForm } from '@mantine/form'
import { useDisclosure } from '@mantine/hooks'
import { IconEdit, IconPlus } from '@tabler/icons-react'
import {
  type MRT_Cell,
  MRT_ColumnDef,
  MantineReactTable,
  useMantineReactTable,
} from 'mantine-react-table'
import { useMemo, useState } from 'react'

const SensorTypes = () => {
  const [isModalOpen, { open, close }] = useDisclosure(false)
  const [isConfirmOpen, { open: openConfirm, close: closeConfirm }] =
    useDisclosure(false)
  const [editingSensorType, setEditingSensorType] = useState<SensorType | null>(
    null,
  )

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
      name_short: '',
      name_long: '',
      name_metric: '',
      unit: '',
    },
    validate: {
      name_short: (value) => {
        if (!value || value.length === 0) {
          return 'Short name is required'
        }
        // Check for duplicates (excluding the current editing sensor type)
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
      device_type_id: '',
      name_short: sensorType.name_short,
      name_long: sensorType.name_long,
      name_metric: sensorType.name_metric,
      unit: sensorType.unit || '',
    })
    open()
  }

  const handleAdd = () => {
    setEditingSensorType(null)
    form.reset()
    open()
  }

  // Handle device type selection to pre-populate long name
  const handleDeviceTypeChange = (deviceTypeId: string | null) => {
    if (deviceTypeId && deviceTypes.data) {
      const selectedDeviceType = deviceTypes.data.find(
        (dt) => dt.device_type_id.toString() === deviceTypeId,
      )
      if (selectedDeviceType) {
        form.setFieldValue('device_type_id', deviceTypeId)
        // Pre-populate the long name with the device type name
        form.setFieldValue('name_long', selectedDeviceType.name_long)
      }
    } else {
      form.setFieldValue('device_type_id', '')
      form.setFieldValue('name_long', '')
    }
  }

  const handleSubmit = async (values: typeof form.values) => {
    try {
      // Remove device_type_id from values before submitting
      const { device_type_id, ...sensorTypeData } = values

      if (editingSensorType) {
        // Update existing sensor type
        await updateSensorType.mutateAsync({
          sensorTypeId: editingSensorType.sensor_type_id,
          sensorType: {
            ...editingSensorType,
            ...sensorTypeData,
          },
        })
      } else {
        // Create new sensor type
        await createSensorType.mutateAsync({
          sensor_type_id: 0, // Will be auto-assigned by backend
          ...sensorTypeData,
        })
      }
      close()
      closeConfirm()
    } catch (error) {
      console.error('Error saving sensor type:', error)
      // TODO: Add proper error handling/notification
    }
  }

  const handleUpdateClick = () => {
    openConfirm()
  }

  const columns = useMemo<MRT_ColumnDef<SensorType>[]>(
    () => [
      {
        header: 'ID',
        accessorKey: 'sensor_type_id',
        size: 100,
        mantineTableHeadCellProps: {
          align: 'center',
        },
        mantineTableBodyCellProps: {
          align: 'center',
        },
      },
      {
        header: 'Short Name',
        accessorKey: 'name_short',
        size: 200,
      },
      {
        header: 'Long Name',
        accessorKey: 'name_long',
        size: 300,
      },
      {
        header: 'Metric Name',
        accessorKey: 'name_metric',
        size: 300,
      },
      {
        header: 'Unit',
        accessorKey: 'unit',
        size: 150,
        mantineTableHeadCellProps: {
          align: 'center',
        },
        mantineTableBodyCellProps: {
          align: 'center',
        },
        Cell: ({ cell }: { cell: MRT_Cell<SensorType> }) => (
          <Text size="sm">{cell.getValue<string | null>() || '-'}</Text>
        ),
      },
      {
        header: 'Actions',
        accessorKey: 'actions',
        size: 120,
        mantineTableHeadCellProps: {
          align: 'center',
        },
        mantineTableBodyCellProps: {
          align: 'center',
        },
        Cell: ({ cell }: { cell: MRT_Cell<SensorType> }) => (
          <ActionIcon
            variant="subtle"
            color="blue"
            onClick={() => handleEdit(cell.row.original)}
          >
            <IconEdit style={{ width: 16, height: 16 }} />
          </ActionIcon>
        ),
        enableSorting: false,
        enableColumnFilter: false,
        enableGlobalFilter: false,
      },
    ],
    [handleEdit],
  )

  const table = useMantineReactTable({
    columns,
    data: sensorTypes.data ?? [],
    enableGrouping: true,
    enableColumnDragging: true,
    enableColumnResizing: true,
    enableColumnOrdering: true,
    enableRowSelection: false,
    enableMultiSort: true,
    enableGlobalFilter: true,
    enableColumnFilters: true,
    enableDensityToggle: true,
    enableFullScreenToggle: true,
    enableHiding: true,
    layoutMode: 'grid',
    initialState: {
      density: 'xs',
      columnVisibility: {
        sensor_type_id: true,
        name_short: true,
        name_long: true,
        name_metric: true,
        unit: true,
        actions: true,
      },
      sorting: [{ id: 'sensor_type_id', desc: false }],
      globalFilter: '',
      showGlobalFilter: true,
      pagination: {
        pageSize: 50,
        pageIndex: 0,
      },
    },
    mantineTableProps: {
      striped: true,
      highlightOnHover: true,
      style: { width: '100%' },
    },
  })

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

      <MantineReactTable table={table} />

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
                style={{
                  backgroundColor: 'var(--mantine-color-red-0)',
                  padding: '8px 12px',
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
              label="Device comes first, then a full name for the sensor type. Each word starts with a capital letter. Example: PV PCS AC Power, Tracker Position"
              position="top"
              multiline
            >
              <TextInput
                label="Long Name"
                placeholder="e.g., PV PCS AC Power"
                required
                {...form.getInputProps('name_long')}
                onChange={(event) => {
                  const longName = event.currentTarget.value
                  const shortName = longName
                    .toLowerCase()
                    .replace(/\s+/g, '_')
                    .replace(/[^a-z0-9_]/g, '')
                  form.setFieldValue('name_short', shortName)
                  // Trigger validation on short name after setting the value
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
                placeholder="e.g., pv_pcs_ac_power"
                required
                {...form.getInputProps('name_short')}
                onChange={(event) => {
                  // Trigger validation immediately
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
