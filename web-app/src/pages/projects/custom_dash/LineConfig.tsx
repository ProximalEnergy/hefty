import { SensorTypeEnum } from '@/api/enumerations'
import { SensorType } from '@/api/v1/operational/sensor_types'
import { Tag } from '@/hooks/projectTags'
import { Device } from '@/hooks/types'
import {
  ActionIcon,
  Box,
  Button,
  CheckIcon,
  Checkbox,
  Combobox,
  Group,
  Input,
  NumberInput,
  Pill,
  PillsInput,
  Select,
  Skeleton,
  Stack,
  Text,
  Title,
  Tooltip,
  useCombobox,
} from '@mantine/core'
import { IconPlus, IconX } from '@tabler/icons-react'
import { UseQueryResult } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { useMemo, useState } from 'react'

import { LineConfig as LineConfigType } from './CustomDash'

const MAX_DISPLAYED_VALUES = 2

interface Trace {
  id: string
  sensorTypeId: string | null
  tagIds: number[]
  aggregationMethod: string | null
  withThreshold: boolean
  minimum: number | null
  maximum: number | null
}

const LineConfig = ({
  mode,
  stack,
  sensorTypes,
  tags,
  devices,
  onAdd,
  initialConfig,
}: {
  mode: 'create' | 'edit'
  stack: { close: (drawerId: 'line-config') => void }
  sensorTypes: UseQueryResult<SensorType[], AxiosError<unknown>>
  tags: UseQueryResult<Tag[], AxiosError<unknown>>
  devices: UseQueryResult<Device[], AxiosError<unknown>>
  onAdd: (config: LineConfigType) => void
  initialConfig?: LineConfigType
}) => {
  const [traces, setTraces] = useState<Trace[]>(() => {
    if (initialConfig?.traces) {
      return initialConfig.traces.map((trace) => ({
        id: trace.id || Date.now().toString() + Math.random(),
        sensorTypeId: trace.sensorTypeId,
        tagIds: trace.tagIds || [],
        aggregationMethod: trace.aggregationMethod,
        withThreshold: trace.maximum !== null || trace.minimum !== null,
        minimum: trace.minimum ?? null,
        maximum: trace.maximum ?? null,
      }))
    }
    return [
      {
        id: '1',
        sensorTypeId: null,
        tagIds: [],
        aggregationMethod: null,
        withThreshold: false,
        minimum: null,
        maximum: null,
      },
    ]
  })
  const allowCreate = traces.every(
    (trace) => trace.sensorTypeId && trace.aggregationMethod,
  )
  const addTrace = () => {
    const newTrace: Trace = {
      id: Date.now().toString(),
      sensorTypeId: null,
      tagIds: [],
      aggregationMethod: null,
      withThreshold: false,
      minimum: null,
      maximum: null,
    }
    setTraces([...traces, newTrace])
  }

  const removeTrace = (traceId: string) => {
    if (traces.length > 1) {
      setTraces(traces.filter((trace) => trace.id !== traceId))
    }
  }

  const updateTrace = (
    traceId: string,
    field: keyof Trace,
    value: string | boolean | number | null | number[],
  ) => {
    setTraces(
      traces.map((trace) =>
        trace.id === traceId ? { ...trace, [field]: value } : trace,
      ),
    )
  }

  const addLineChart = () => {
    // Validate that all traces have required fields
    const validTraces = traces.filter(
      (trace) => trace.sensorTypeId && trace.aggregationMethod,
    )

    if (validTraces.length === 0) {
      // You might want to show an error message here
      return
    }

    const config: LineConfigType = {
      traces: validTraces,
    }

    onAdd(config)
  }
  const sensorTypesData = sensorTypes.data
    ?.sort((a, b) => a.name_long.localeCompare(b.name_long))
    .filter(
      (sensorType) =>
        sensorType.sensor_type_id !== SensorTypeEnum.GHOST_UNKNOWN,
    )
  return (
    <Stack>
      {mode === 'create' && <Title>Add Line Chart</Title>}
      {mode === 'edit' && <Title>Edit Line Chart</Title>}
      <Text>
        Select a sensor type and an aggregation method to add a line chart. You
        may add multiple traces to the chart by pressing the green plus button.
      </Text>
      <Text>
        If an aggregation method of None is selected, you may select individual
        tags to display on the chart.
      </Text>

      {sensorTypes.isLoading || tags.isLoading || devices.isLoading ? (
        <Skeleton height={90} />
      ) : (
        <Stack gap="md">
          {traces.map((trace) => (
            <Box
              key={trace.id}
              p="md"
              style={{ border: '1px solid #e9ecef', borderRadius: '8px' }}
            >
              <Group justify="flex-end">
                <Checkbox
                  label="Add Threshold"
                  checked={trace.withThreshold}
                  onChange={(event) =>
                    updateTrace(
                      trace.id,
                      'withThreshold',
                      event.currentTarget.checked,
                    )
                  }
                />
              </Group>
              <Group>
                <ActionIcon
                  variant="light"
                  color="green"
                  onClick={addTrace}
                  title="Add another trace"
                >
                  <IconPlus size={16} />
                </ActionIcon>

                {traces.length > 1 && (
                  <ActionIcon
                    variant="light"
                    color="red"
                    onClick={() => removeTrace(trace.id)}
                    title="Remove this trace"
                  >
                    <IconX size={16} />
                  </ActionIcon>
                )}

                <Select
                  data={
                    sensorTypesData?.map((sensorType) => ({
                      value: sensorType.sensor_type_id.toString(),
                      label: sensorType.name_long,
                    })) || []
                  }
                  label="Sensor Type"
                  placeholder="Select Sensor Type..."
                  value={trace.sensorTypeId}
                  onChange={(value) =>
                    updateTrace(trace.id, 'sensorTypeId', value)
                  }
                  flex={1}
                  searchable
                  clearable
                />

                <Select
                  data={[
                    { value: 'none', label: 'None' },
                    { value: 'sum', label: 'Sum' },
                    { value: 'avg', label: 'Mean' },
                    { value: 'median', label: 'Median' },
                    { value: 'min', label: 'Minimum' },
                    { value: 'max', label: 'Maximum' },
                    { value: 'std', label: 'Standard Deviation' },
                    { value: 'count', label: 'Count' },
                  ]}
                  label="Aggregation"
                  placeholder="Select Aggregation Method..."
                  value={trace.aggregationMethod}
                  onChange={(value) =>
                    updateTrace(trace.id, 'aggregationMethod', value)
                  }
                  flex={1}
                  clearable
                />
                {trace.aggregationMethod === 'none' && !!trace.sensorTypeId && (
                  <TagsComboBox
                    trace={trace}
                    tags={tags}
                    devices={devices}
                    updateTrace={updateTrace}
                  />
                )}
              </Group>
              {trace.withThreshold && (
                <Group justify="center">
                  <NumberInput
                    label="Minimum"
                    value={trace.minimum ?? undefined}
                    onChange={(value) =>
                      updateTrace(trace.id, 'minimum', value)
                    }
                  />
                  <NumberInput
                    label="Maximum"
                    value={trace.maximum ?? undefined}
                    onChange={(value) =>
                      updateTrace(trace.id, 'maximum', value)
                    }
                  />
                </Group>
              )}
            </Box>
          ))}
        </Stack>
      )}

      <Group justify="flex-end">
        <Button variant="default" onClick={() => stack.close('line-config')}>
          Return
        </Button>
        <Tooltip
          label="At least one trace must be selected."
          disabled={allowCreate}
        >
          <Button onClick={addLineChart} disabled={!allowCreate}>
            {mode === 'edit'
              ? 'Update Line Chart Component'
              : 'Add Line Chart Component'}
          </Button>
        </Tooltip>
      </Group>
    </Stack>
  )
}

export default LineConfig

function TagsComboBox({
  trace,
  tags,
  devices,
  updateTrace,
}: {
  trace: Trace
  tags: UseQueryResult<Tag[], AxiosError<unknown>>
  devices: UseQueryResult<Device[], AxiosError<unknown>>
  updateTrace: (
    traceId: string,
    field: keyof Trace,
    value: string | boolean | number | null | number[],
  ) => void
}) {
  const combobox = useCombobox({
    onDropdownClose: () => combobox.resetSelectedOption(),
    onDropdownOpen: () => combobox.updateSelectedOptionIndex('active'),
  })

  const [search, setSearch] = useState('')

  const optionsData = useMemo(() => {
    const sensorTypeId = Number(trace.sensorTypeId)

    return (
      tags.data
        ?.filter((tag) => tag.sensor_type_id === sensorTypeId)
        .sort((a, b) => a.name_scada.localeCompare(b.name_scada))
        .map((tag) => ({
          value: tag.tag_id.toString(),
          label:
            devices.data?.find((d) => d.device_id === tag.device_id)
              ?.name_full ?? '',
        })) ?? []
    )
  }, [tags.data, devices.data, trace.sensorTypeId])

  const selected = trace.tagIds.map(String)

  const filteredOptions = optionsData.filter((o) =>
    o.label.toLowerCase().includes(search.toLowerCase()),
  )

  const setSelected = (next: string[]) =>
    updateTrace(trace.id, 'tagIds', next.map(Number))

  const toggleValue = (val: string) =>
    setSelected(
      selected.includes(val)
        ? selected.filter((v) => v !== val)
        : [...selected, val],
    )

  const displayed = selected
    .slice(
      0,
      MAX_DISPLAYED_VALUES === selected.length
        ? MAX_DISPLAYED_VALUES
        : MAX_DISPLAYED_VALUES - 1,
    )
    .map((val) => {
      const label = optionsData.find((o) => o.value === val)?.label ?? val
      return (
        <Pill key={val} withRemoveButton onRemove={() => toggleValue(val)}>
          {label}
        </Pill>
      )
    })

  return (
    <Combobox
      store={combobox}
      onOptionSubmit={toggleValue}
      withinPortal={false}
    >
      <Combobox.DropdownTarget>
        <PillsInput
          label="Tags"
          pointer
          onClick={() => combobox.toggleDropdown()}
          rightSection={
            selected.length > 0 ? (
              <ActionIcon
                size="sm"
                variant="subtle"
                onClick={(e) => {
                  e.stopPropagation()
                  setSelected([])
                }}
              >
                <IconX size={14} />
              </ActionIcon>
            ) : null
          }
        >
          <Pill.Group>
            {selected.length > 0 ? (
              <>
                {displayed}
                {selected.length > MAX_DISPLAYED_VALUES && (
                  <Pill>
                    +{selected.length - (MAX_DISPLAYED_VALUES - 1)} more
                  </Pill>
                )}
              </>
            ) : (
              <Input.Placeholder>Select tags</Input.Placeholder>
            )}

            <Combobox.EventsTarget>
              <PillsInput.Field
                type="hidden"
                onBlur={() => combobox.closeDropdown()}
                onKeyDown={(e) => {
                  if (e.key === 'Backspace' && selected.length > 0) {
                    e.preventDefault()
                    setSelected(selected.slice(0, -1))
                  }
                }}
              />
            </Combobox.EventsTarget>
          </Pill.Group>
        </PillsInput>
      </Combobox.DropdownTarget>

      <Combobox.Dropdown>
        <Combobox.Search
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
          placeholder="Search tags"
        />

        <Combobox.Options>
          {filteredOptions.length > 0 ? (
            filteredOptions.map((opt) => (
              <Combobox.Option
                key={opt.value}
                value={opt.value}
                active={selected.includes(opt.value)}
              >
                <Group gap="sm">
                  {selected.includes(opt.value) && <CheckIcon size={12} />}
                  <Text size="sm">{opt.label}</Text>
                </Group>
              </Combobox.Option>
            ))
          ) : (
            <Combobox.Empty>No results</Combobox.Empty>
          )}
        </Combobox.Options>
      </Combobox.Dropdown>
    </Combobox>
  )
}
