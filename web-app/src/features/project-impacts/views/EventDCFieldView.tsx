import type { Project } from '@/api/v1/operational/projects'
import CustomCard from '@/components/CustomCard'
import type { Event } from '@/hooks/types'
import { Group, Indicator, SegmentedControl, Stack } from '@mantine/core'
import { useState } from 'react'
import DcFieldAnomaliesMap from '@/features/project-impacts/components/DcFieldAnomaliesMap'
import { EventLosses } from '@/features/project-impacts/components/EventLosses'
import {
  ConfirmRootCauseModal,
  EventRootCauseSelection,
} from '@/features/project-impacts/components/EventRootCauseSelection'
import { EventSummaryDetails } from '@/features/project-impacts/components/EventSummaryDetails'
import { EventTimeline } from '@/features/project-impacts/components/EventTimeline'
import { EventTraces } from '@/features/project-impacts/components/EventTraces'
import { useEventDCFieldViewModel } from '@/features/project-impacts/hooks/use-event-dc-field-view-model'
import { EventChatShim as EventChat } from '@/features/project-impacts/components/EventChatShim'

type EventDCFieldViewProps = {
  event: Event
  eventId: number
  eventMessageCount: number
  project: Project
  projectId: string
}

export function EventDCFieldView({
  event,
  eventId,
  eventMessageCount,
  project,
  projectId,
}: EventDCFieldViewProps) {
  const [largeCardView, setLargeCardView] = useState<'traces' | 'chat'>(
    'traces',
  )
  const largeCardTitle =
    largeCardView === 'traces' ? 'Event Traces' : 'Event Chat'
  const viewModel = useEventDCFieldViewModel({
    event,
    eventId,
    project,
    projectId,
  })

  return (
    <Stack p="md" h="100%">
      <ConfirmRootCauseModal
        opened={viewModel.rootCauseModalOpened}
        onCancel={() => {
          viewModel.closeRootCauseModal()
          viewModel.setSelectedRootCause(event.root_cause_id ?? null)
        }}
        onConfirm={() => {
          viewModel.updateRootCause(viewModel.selectedRootCause)
          viewModel.closeRootCauseModal()
        }}
        selectedRootCause={viewModel.selectedRootCause}
        rootCauses={viewModel.rootCauses}
      />
      <Group h="100%" align="stretch">
        <Stack flex={4} h="100%" style={{ minWidth: 0 }}>
          <Group align="stretch" flex={2}>
            <Stack flex={0} style={{ minWidth: '300px' }}>
              <EventSummaryDetails
                event={event}
                project={project}
                projectId={projectId}
              />
              <EventRootCauseSelection
                eventRootCauseId={event.root_cause_id}
                onRootCauseChange={(cause) => {
                  viewModel.setSelectedRootCause(cause)
                  viewModel.openRootCauseModal()
                }}
                rootCauseDeviceTypes={viewModel.rootCauseDeviceTypes}
                rootCauses={viewModel.rootCauses}
                selectedRootCause={viewModel.selectedRootCause}
                setSelectedRootCause={viewModel.setSelectedRootCause}
                setShowAllCauses={viewModel.setShowAllCauses}
                showAllCauses={viewModel.showAllCauses}
              />
              <EventLosses
                losses={viewModel.losses}
                deviceTypeId={event.device.device_type_id || -1}
              />
            </Stack>
            <Stack flex={1} style={{ minHeight: '400px' }}>
              <DcFieldAnomaliesMap event={event} projectId={projectId} />
            </Stack>
          </Group>
          <CustomCard
            title={largeCardTitle}
            fill
            style={{ height: '100%', minHeight: 0 }}
            headerChildren={
              <Indicator
                disabled={eventMessageCount === 0}
                inline
                label={eventMessageCount}
                offset={4}
                radius="xl"
                size={14}
              >
                <SegmentedControl
                  value={largeCardView}
                  onChange={(value) =>
                    setLargeCardView(value as 'traces' | 'chat')
                  }
                  data={[
                    { label: 'Traces', value: 'traces' },
                    { label: 'Chat', value: 'chat' },
                  ]}
                />
              </Indicator>
            }
          >
            {largeCardView === 'traces' && (
              <EventTraces
                data={viewModel.plotData}
                error={null}
                isLoading={viewModel.isTracesLoading}
                layout={viewModel.plotLayout}
                xAxisTimeZone={viewModel.xAxisTimeZone}
              />
            )}
            {largeCardView === 'chat' && (
              <EventChat eventId={eventId} projectId={projectId} />
            )}
          </CustomCard>
        </Stack>
        <Stack flex={1} h="100%">
          <CustomCard
            allowFullscreen={false}
            title="Timeline"
            style={{ height: '100%', flex: 1 }}
          >
            <EventTimeline
              isLoading={viewModel.isTimelineLoading}
              events={viewModel.historicalEvents}
              failureModes={viewModel.failureModes}
              projectId={projectId}
              selectedEvent={event}
              tickets={viewModel.tickets}
            />
          </CustomCard>
        </Stack>
      </Group>
    </Stack>
  )
}
