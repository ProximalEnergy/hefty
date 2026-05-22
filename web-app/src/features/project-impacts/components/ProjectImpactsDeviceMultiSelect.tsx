import { MultiSelect } from '@mantine/core'

type ProjectImpactsDeviceMultiSelectProps = {
  unique_devices: {
    device_id: number
    device_name_full: string
  }[]
  selected_devices: string[]
  onChange: (value: string[]) => void
}

export function ProjectImpactsDeviceMultiSelect(
  context: ProjectImpactsDeviceMultiSelectProps,
) {
  return (
    <MultiSelect
      data={context.unique_devices.map((device) => ({
        value: device.device_id.toString(),
        label: device.device_name_full,
      }))}
      placeholder={
        context.selected_devices.length == 0 ? 'Search devices...' : undefined
      }
      value={context.selected_devices}
      onChange={context.onChange}
      clearable
      searchable
      limit={50}
    />
  )
}
