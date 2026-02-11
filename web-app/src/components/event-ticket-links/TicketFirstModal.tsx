import { CMMSTicket } from '@/api/v1/operational/project/cmms_tickets'
import {
  type EventCMMSTicket,
  useAddEventCMMSTicket,
  useDeleteEventCMMSTicket,
  useGetEventCMMSTickets,
  useGetSuggestedEvents,
} from '@/api/v1/protected/web-application/projects/event-cmms-tickets/event_cmms_tickets'
import { useGetEvents } from '@/hooks/api'
import CMMSTicketCard from '@/pages/projects/cmms/CMMSTicketCard'
import { Group, Modal, Skeleton, Stack, Text, Title } from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'
import { useMemo, useState } from 'react'

import EventCard from './EventCard'

const TicketFirstModal = ({
  opened,
  onClose,
  ticket,
  linkedEventIds,
  projectId,
}: {
  opened: boolean
  onClose: () => void
  ticket: CMMSTicket
  linkedEventIds: number[]
  projectId: string
}) => {
  const numericTicketId = Number(ticket.cmms_ticket_id)
  const canMutate = projectId !== '' && !Number.isNaN(numericTicketId)
  const [activeMutation, setActiveMutation] = useState<{
    eventId: number
    type: 'link' | 'unlink'
  } | null>(null)
  const [isAwaitingRefresh, setIsAwaitingRefresh] = useState(false)
  const addEventCMMSTicket = useAddEventCMMSTicket()
  const deleteEventCMMSTicket = useDeleteEventCMMSTicket()
  const eventTicketsQueryParams = useMemo(() => {
    if (Number.isNaN(numericTicketId)) {
      return {}
    }
    return { cmms_ticket_ids: [numericTicketId] }
  }, [numericTicketId])
  const eventCMMSTickets = useGetEventCMMSTickets({
    pathParams: { projectId: projectId },
    queryParams: eventTicketsQueryParams,
    queryOptions: {
      enabled: opened && canMutate,
    },
  })
  const eventTicketMap = useMemo(() => {
    const map = new Map<number, EventCMMSTicket>()
    eventCMMSTickets.data?.forEach((item) => {
      map.set(item.event_id, item)
    })
    return map
  }, [eventCMMSTickets.data])
  const suggestedEvents = useGetSuggestedEvents({
    pathParams: { projectId: projectId },
    queryParams: {
      cmms_ticket_id: String(ticket.cmms_ticket_id),
      cmms_integration_id: ticket.cmms_integration_id,
      cmms_device_id: Number(ticket.cmms_device_id) || undefined,
      source_created_at: ticket.created_at || undefined,
    },
  })

  const allEventIds = useMemo(() => {
    const baseIds = new Set<number>()
    linkedEventIds.forEach((eventId) => {
      if (eventId != null) {
        baseIds.add(eventId)
      }
    })
    suggestedEvents.data?.forEach((event) => {
      if (event.event_id != null) {
        baseIds.add(event.event_id)
      }
    })
    return Array.from(baseIds)
  }, [linkedEventIds, suggestedEvents.data])
  const shouldLoadAllEvents =
    suggestedEvents.isSuccess && allEventIds.length > 0
  const allEvents = useGetEvents({
    pathParams: { projectId: projectId },
    queryParams: { event_ids: allEventIds, open: false },
    queryOptions: {
      enabled: shouldLoadAllEvents,
    },
  })

  const linkedEventData = allEvents.data?.filter((event) =>
    linkedEventIds.includes(event.event_id),
  )
  const suggestedEventData = allEvents.data?.filter(
    (event) => !linkedEventIds.includes(event.event_id),
  )

  const isMutationPending =
    addEventCMMSTicket.isPending || deleteEventCMMSTicket.isPending

  const isEventDataLoading =
    suggestedEvents.isPending ||
    (shouldLoadAllEvents && allEvents.isPending) ||
    suggestedEvents.isRefetching ||
    allEvents.isRefetching ||
    isMutationPending ||
    isAwaitingRefresh

  const linkingEventId =
    activeMutation?.type === 'link' && addEventCMMSTicket.isPending
      ? activeMutation.eventId
      : null

  const unlinkingEventId =
    activeMutation?.type === 'unlink' && deleteEventCMMSTicket.isPending
      ? activeMutation.eventId
      : null

  const handleLinkEvent = (eventId: number) => {
    if (!canMutate) {
      return
    }
    if (linkedEventIds.includes(eventId)) {
      return
    }
    setActiveMutation({ eventId, type: 'link' })
    addEventCMMSTicket.mutate(
      {
        project_id: projectId,
        event_id: eventId,
        cmms_ticket_id: numericTicketId,
      },
      {
        onSettled: () => {
          setActiveMutation(null)
          setIsAwaitingRefresh(true)
          const refetchPromises: Array<Promise<unknown>> = [
            suggestedEvents.refetch(),
          ]

          if (shouldLoadAllEvents) {
            refetchPromises.push(allEvents.refetch())
          }

          void Promise.all(refetchPromises)
            .catch(() => {})
            .finally(() => {
              setIsAwaitingRefresh(false)
            })
        },
      },
    )
  }

  const handleUnlinkEvent = (eventId: number) => {
    if (!canMutate) {
      return
    }
    const eventTicket = eventTicketMap.get(eventId)
    if (!eventTicket) {
      return
    }
    setActiveMutation({ eventId, type: 'unlink' })
    deleteEventCMMSTicket.mutate(
      {
        project_id: projectId,
        event_cmms_ticket_id: eventTicket.event_cmms_ticket_id,
      },
      {
        onSettled: () => {
          setActiveMutation(null)
          setIsAwaitingRefresh(true)
          const refetchPromises: Array<Promise<unknown>> = [
            suggestedEvents.refetch(),
          ]

          if (shouldLoadAllEvents) {
            refetchPromises.push(allEvents.refetch())
          }

          void Promise.all(refetchPromises)
            .catch(() => {})
            .finally(() => {
              setIsAwaitingRefresh(false)
            })
        },
      },
    )
  }

  return (
    <Modal opened={opened} onClose={onClose} fullScreen={true}>
      <Stack w="100%" h="100%">
        <Group w="100%" h="100%" align="flex-start" style={{ flex: 1 }}>
          <Stack w="100%" h="100%" style={{ flex: 1 }}>
            <Title order={2}>Selected Ticket</Title>
            <CMMSTicketCard ticket={ticket} withBorder={true} />
          </Stack>
          <Stack w="100%" h="100%" style={{ flex: 1 }}>
            <Title order={2}>Linked Events</Title>
            {isEventDataLoading ? (
              <Skeleton height={120} radius="md" w="100%" />
            ) : (
              linkedEventData?.map((event) => (
                <EventCard
                  key={event.event_id}
                  event={event}
                  projectId={projectId}
                  isLinked={true}
                  onUnlink={
                    canMutate
                      ? () => handleUnlinkEvent(event.event_id)
                      : undefined
                  }
                  isUnlinking={unlinkingEventId === event.event_id}
                />
              ))
            )}
          </Stack>
          <Stack w="100%" h="100%" style={{ flex: 1 }}>
            <Title order={2}>Suggested Events</Title>
            {!ticket.cmms_device_id || !ticket.created_at ? (
              <>
                <Text>
                  <IconAlertTriangle size={12} /> Warning: suggested Events may
                  be incomplete or inaccurate due to missing data for this
                  ticket.
                </Text>
                {!ticket.cmms_device_id && <Text>CMMS Device ID Missing.</Text>}
                {!ticket.created_at && (
                  <Text>Source Creation Time Missing.</Text>
                )}
              </>
            ) : (
              <></>
            )}
            {isEventDataLoading ? (
              <Skeleton height={120} radius="md" w="100%" />
            ) : (
              suggestedEventData?.map((event) => (
                <EventCard
                  key={event.event_id}
                  event={event}
                  projectId={projectId}
                  isLinked={false}
                  onLink={
                    canMutate
                      ? () => handleLinkEvent(event.event_id)
                      : undefined
                  }
                  isLinking={linkingEventId === event.event_id}
                />
              ))
            )}
          </Stack>
        </Group>
      </Stack>
    </Modal>
  )
}

export default TicketFirstModal
