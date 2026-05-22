import { MultiSelect } from '@mantine/core'

type ProjectImpactsDeviceTypeMultiSelectProps = {
  unique_types: {
    device_type_id: number
    device_type_name: string
  }[]
  selected_device_types: string[]
  onChange: (value: string[]) => void
}

export function ProjectImpactsDeviceTypeMultiSelect(
  context: ProjectImpactsDeviceTypeMultiSelectProps,
) {
  return (
    <MultiSelect
      data={context.unique_types.map((type) => ({
        value: type.device_type_id.toString(),
        label: type.device_type_name,
      }))}
      value={context.selected_device_types}
      onChange={context.onChange}
      placeholder={
        context.selected_device_types.length == 0
          ? 'Select device types...'
          : undefined
      }
      clearable
      searchable
      limit={50}
    />
  )
}
