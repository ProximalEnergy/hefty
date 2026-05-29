import type { Project } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import ProjectEventsMap from '@/components/ProjectEventsMap'
import { useTipsEventsTable } from '@/components/Tips'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useProjectFilter } from '@/hooks/custom'
import { buildTimeSearchParams } from '@/utils/build-time-search-params'
import { Box, Group, Stack, Switch } from '@mantine/core'
import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { ProjectImpactsDeviceMultiSelect } from '@/features/project-impacts/components/ProjectImpactsDeviceMultiSelect'
import { ProjectImpactsDeviceTypeMultiSelect } from '@/features/project-impacts/components/ProjectImpactsDeviceTypeMultiSelect'
import { useProjectImpactsEventViewStableContext } from '@/features/project-impacts/hooks/use-project-impacts-event-view-stable-context'
import { useProjectImpactsEventViewUnstableContext } from '@/features/project-impacts/hooks/use-project-impacts-event-view-unstable-context'
import type { ProjectImpactsContext } from '@/features/project-impacts/types/project-impacts-types'
import {
  buildClosedImpactDateRangeKey,
  dateRangeDefaultsToIncludingClosed,
} from '@/features/project-impacts/utils/closed-impact-date-range'
import { EventTable } from '@/components/EventTable'

type ProjectImpactsEventViewProps = {
  context: ProjectImpactsContext
}

export function ProjectImpactsEventView({
  context,
}: ProjectImpactsEventViewProps) {
  useTipsEventsTable()
  useProjectFilter({
    hasEventIntegration: true,
  })

  const [selectedDevices, setSelectedDevices] = useState<string[]>([])
  const [selectedDeviceTypes, setSelectedDeviceTypes] = useState<string[]>([])

  const [searchParams] = useSearchParams()
  const { start, end } = buildTimeSearchParams(searchParams)
  const selectedDateRangeKey = buildClosedImpactDateRangeKey({ start, end })
  const defaultShowClosedEvents = dateRangeDefaultsToIncludingClosed({
    start,
    end,
  })
  const [closedEventsState, setClosedEventsState] = useState<{
    rangeKey: string | null
    value: boolean
  }>({ rangeKey: '', value: false })
  const showClosedEvents =
    closedEventsState.rangeKey === selectedDateRangeKey
      ? closedEventsState.value
      : defaultShowClosedEvents

  const stableContext = useProjectImpactsEventViewStableContext({
    projectId: context.projectId,
  })
  const unstableContext = useProjectImpactsEventViewUnstableContext({
    projectId: context.projectId,
    startQuery: start.toISOString(),
    endQuery: end.toISOString(),
    selectedDeviceTypes,
    selectedDevices,
    showClosedEvents,
  })

  return (
    <Stack pt="md" h="100%" mih={0}>
      <Group justify="space-between">
        <Switch
          checked={showClosedEvents}
          onChange={(event) =>
            setClosedEventsState({
              rangeKey: selectedDateRangeKey,
              value: event.currentTarget.checked,
            })
          }
          label="Include Closed Events"
        />
        <Group>
          <AdvancedDatePicker
            defaultRange="today"
            includeClearButton={false}
            includeIncrementButtons={false}
            includeTodayInDateRange={true}
          />
          <ProjectImpactsDeviceTypeMultiSelect
            unique_types={stableContext.eventDevices.data?.unique_types ?? []}
            selected_device_types={selectedDeviceTypes}
            onChange={(value) => setSelectedDeviceTypes(value)}
          />
          <ProjectImpactsDeviceMultiSelect
            unique_devices={
              stableContext.eventDevices.data?.unique_devices ?? []
            }
            selected_devices={selectedDevices}
            onChange={(value) => setSelectedDevices(value)}
          />
        </Group>
      </Group>
      {unstableContext.eventsSummary.isLoading ? (
        <PageLoader />
      ) : (
        <Stack flex={1} h="100%" mih={0}>
          <Box flex={1} mih={0}>
            <EventTable
              data={unstableContext.eventsSummary.data ?? []}
              height="100%"
              project={context.project as Project}
            />
          </Box>
          <ProjectEventsMap
            events={unstableContext.eventsSummary.data ?? []}
            project={context.project as Project}
          />
        </Stack>
      )}
    </Stack>
  )
}
