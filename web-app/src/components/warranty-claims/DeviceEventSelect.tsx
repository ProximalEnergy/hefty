import type { components } from '@/api/schema'
import { useGetEventsForDevice } from '@/api/v1/operational/project/events'
import { Select } from '@mantine/core'
import { useMemo } from 'react'

type ProjectEvent = components['schemas']['EventInterface']

function formatEventRange(
  startIso: string,
  endIso: string | null | undefined,
): string {
  const start = new Date(startIso)
  if (Number.isNaN(start.getTime())) return startIso
  const end = endIso ? new Date(endIso) : null
  const startYmd = start.toISOString().slice(0, 10)
  if (!end || Number.isNaN(end.getTime())) {
    return `${startYmd} → ongoing`
  }
  const endYmd = end.toISOString().slice(0, 10)
  if (startYmd === endYmd) return startYmd
  if (startYmd.slice(0, 4) === endYmd.slice(0, 4)) {
    return `${startYmd} → ${endYmd.slice(5)}`
  }
  return `${startYmd} → ${endYmd}`
}

interface Props {
  projectId: string
  deviceId: number
  value: number | null
  onChange: (eventId: number | null) => void
  disabled?: boolean
  initialEvents?: ProjectEvent[]
  size?: string
}

export default function DeviceEventSelect({
  projectId,
  deviceId,
  value,
  onChange,
  disabled,
  initialEvents = [],
  size = 'xs',
}: Props) {
  const { data: events, isLoading } = useGetEventsForDevice({
    pathParams: { projectId },
    queryParams: { device_ids: [deviceId], open: false },
  })

  const options = useMemo(() => {
    const eventById = new Map<number, ProjectEvent>()
    for (const event of initialEvents) eventById.set(event.event_id, event)
    for (const event of events ?? []) eventById.set(event.event_id, event)

    return Array.from(eventById.values())
      .slice()
      .sort((a, b) =>
        a.time_start < b.time_start ? 1 : a.time_start > b.time_start ? -1 : 0,
      )
      .map((e) => {
        const range = formatEventRange(e.time_start, e.time_end)
        const fm = e.failure_mode?.name_long
          ? ` · ${e.failure_mode.name_long}`
          : ''
        return {
          value: String(e.event_id),
          label: `#${e.event_id} · ${range}${fm}`,
        }
      })
  }, [events, initialEvents])

  return (
    <Select
      size={size}
      placeholder={
        isLoading
          ? 'Loading…'
          : options.length === 0
            ? 'No events found'
            : 'Select event'
      }
      data={options}
      value={value != null ? String(value) : null}
      onChange={(v) => onChange(v ? Number(v) : null)}
      clearable
      searchable
      disabled={disabled || options.length === 0}
      loading={isLoading}
      nothingFoundMessage="No matching events"
    />
  )
}
