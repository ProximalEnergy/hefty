import { useGetCMMSTickets } from '@/api/v1/operational/project/cmms_tickets'
import {
  type EventCMMSTicket,
  useAddEventCMMSTicket,
  useDeleteEventCMMSTicket,
  useGetEventCMMSTickets,
  useGetSuggestedTickets,
} from '@/api/v1/protected/web-application/projects/event-cmms-tickets/event_cmms_tickets'
import EventCard from '@/components/event-ticket-links/EventCard'
import { Event } from '@/hooks/types'
import { Group, Modal, Skeleton, Stack, Text, Title } from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'
import { useMemo, useState } from 'react'

import CMMSTicketCard from '../../cmms/CMMSTicketCard'

const EventFirstModal = ({
  opened,
  onClose,
  event,
  linkedTicketIds,
  projectId,
}: {
  opened: boolean
  onClose: () => void
  event: Event
  linkedTicketIds: number[]
  projectId: string
}) => {
  const numericEventId = Number(event.event_id)
  const canMutate = projectId !== '' && Number.isFinite(numericEventId)

  const [activeMutation, setActiveMutation] = useState<{
    ticketId: number
    type: 'link' | 'unlink'
  } | null>(null)
  const [isAwaitingRefresh, setIsAwaitingRefresh] = useState(false)

  const addEventCMMSTicket = useAddEventCMMSTicket()
  const deleteEventCMMSTicket = useDeleteEventCMMSTicket()

  const eventTicketsEnabled = opened && canMutate
  const eventCMMSTickets = useGetEventCMMSTickets({
    pathParams: { project_id: projectId },
    queryParams: { event_ids: [numericEventId] },
    queryOptions: { enabled: eventTicketsEnabled },
  })
  const eventTicketRecords = useMemo(
    () => eventCMMSTickets.data ?? [],
    [eventCMMSTickets.data],
  )
  const hasEventTicketsError = eventCMMSTickets.isError
  const isEventTicketsResolved =
    !eventTicketsEnabled ||
    eventCMMSTickets.status === 'success' ||
    eventCMMSTickets.status === 'error'

  const eventTicketMap = useMemo(() => {
    const map = new Map<number, EventCMMSTicket>()
    eventTicketRecords.forEach((record) => {
      map.set(record.cmms_ticket_id, record)
    })
    return map
  }, [eventTicketRecords])

  const ticketIdsFromQuery = useMemo(
    () => eventTicketRecords.map((record) => record.cmms_ticket_id),
    [eventTicketRecords],
  )

  const baseTicketIds = useMemo(() => {
    const ids = new Set<number>()
    linkedTicketIds.forEach((id) => {
      if (typeof id === 'number') {
        ids.add(id)
      }
    })
    ticketIdsFromQuery.forEach((id) => {
      if (typeof id === 'number') {
        ids.add(id)
      }
    })
    return Array.from(ids)
  }, [linkedTicketIds, ticketIdsFromQuery])

  const linkedTicketsEnabled = opened && baseTicketIds.length > 0
  const linkedTicketsQuery = useGetCMMSTickets({
    pathParams: { project_id: projectId },
    queryParams: {
      cmms_ticket_ids: baseTicketIds,
      include_json_raw: false,
    },
    queryOptions: {
      enabled: linkedTicketsEnabled,
    },
  })
  const linkedTicketsData = useMemo(
    () => linkedTicketsQuery.data?.data ?? [],
    [linkedTicketsQuery.data],
  )
  const hasLinkedTicketsError = linkedTicketsQuery.isError
  const isLinkedTicketsResolved =
    !linkedTicketsEnabled ||
    linkedTicketsQuery.status === 'success' ||
    linkedTicketsQuery.status === 'error'

  const bootstrapTicketsEnabled =
    opened && canMutate && baseTicketIds.length === 0
  const bootstrapTicketsQuery = useGetCMMSTickets({
    pathParams: { project_id: projectId },
    queryParams: {
      max_results: 5,
    },
    queryOptions: {
      enabled: bootstrapTicketsEnabled,
    },
  })
  const bootstrapTickets = useMemo(
    () => bootstrapTicketsQuery.data?.data ?? [],
    [bootstrapTicketsQuery.data],
  )
  const hasBootstrapTicketsError = bootstrapTicketsQuery.isError
  const isBootstrapTicketsResolved =
    !bootstrapTicketsEnabled ||
    bootstrapTicketsQuery.status === 'success' ||
    bootstrapTicketsQuery.status === 'error'

  const cmmsIntegrationId = useMemo(() => {
    for (const ticket of linkedTicketsData) {
      if (ticket.cmms_integration_id != null) {
        return ticket.cmms_integration_id
      }
    }
    for (const ticket of bootstrapTickets) {
      if (ticket.cmms_integration_id != null) {
        return ticket.cmms_integration_id
      }
    }
    return null
  }, [linkedTicketsData, bootstrapTickets])

  const suggestionsEnabled = opened && canMutate && cmmsIntegrationId != null
  const suggestedTicketsQueryEnabled = suggestionsEnabled
  const suggestedTickets = useGetSuggestedTickets({
    pathParams: { project_id: projectId },
    queryParams: {
      event_id: numericEventId,
      cmms_integration_id: cmmsIntegrationId ?? -1,
    },
    queryOptions: {
      enabled: suggestedTicketsQueryEnabled,
    },
  })
  const hasSuggestedTicketsError = suggestedTickets.isError
  const isSuggestedTicketsResolved =
    !suggestedTicketsQueryEnabled ||
    suggestedTickets.status === 'success' ||
    suggestedTickets.status === 'error'

  const suggestedTicketIds = useMemo(
    () => suggestedTickets.data?.map((ticket) => ticket.cmms_ticket_id) ?? [],
    [suggestedTickets.data],
  )

  const allTicketIds = useMemo(() => {
    const ids = new Set<number>()
    baseTicketIds.forEach((id) => ids.add(id))
    suggestedTicketIds.forEach((id) => {
      if (typeof id === 'number') {
        ids.add(id)
      }
    })
    return Array.from(ids)
  }, [baseTicketIds, suggestedTicketIds])

  const allTicketsEnabled = opened && allTicketIds.length > 0
  const allTicketsQuery = useGetCMMSTickets({
    pathParams: { project_id: projectId },
    queryParams: {
      cmms_ticket_ids: allTicketIds,
      include_json_raw: false,
    },
    queryOptions: {
      enabled: allTicketsEnabled,
    },
  })
  const hasAllTicketsError = allTicketsQuery.isError
  const isAllTicketsResolved =
    !allTicketsEnabled ||
    allTicketsQuery.status === 'success' ||
    allTicketsQuery.status === 'error'
  const allTicketsData = useMemo(
    () => allTicketsQuery.data?.data ?? [],
    [allTicketsQuery.data],
  )

  const linkedTicketIdSet = useMemo(
    () => new Set(baseTicketIds),
    [baseTicketIds],
  )

  const linkedTicketData = useMemo(
    () =>
      allTicketsData.filter((ticket) =>
        linkedTicketIdSet.has(ticket.cmms_ticket_id),
      ),
    [allTicketsData, linkedTicketIdSet],
  )

  const suggestedTicketData = useMemo(
    () =>
      allTicketsData.filter(
        (ticket) => !linkedTicketIdSet.has(ticket.cmms_ticket_id),
      ),
    [allTicketsData, linkedTicketIdSet],
  )

  const isMutationPending =
    addEventCMMSTicket.isPending || deleteEventCMMSTicket.isPending
  const isEventTicketsLoading = eventTicketsEnabled && !isEventTicketsResolved
  const isLinkedTicketsLoading =
    linkedTicketsEnabled && !isLinkedTicketsResolved
  const isBootstrapTicketsLoading =
    bootstrapTicketsEnabled && !isBootstrapTicketsResolved
  const isIntegrationLoading =
    isEventTicketsLoading || isLinkedTicketsLoading || isBootstrapTicketsLoading
  const isSuggestedTicketsLoading =
    suggestedTicketsQueryEnabled && !isSuggestedTicketsResolved
  const isAllTicketsLoading = allTicketsEnabled && !isAllTicketsResolved
  const hasIntegrationError =
    hasEventTicketsError || hasLinkedTicketsError || hasBootstrapTicketsError
  const hasLinkedSectionError = hasIntegrationError || hasAllTicketsError
  const hasSuggestedSectionError =
    hasIntegrationError || hasAllTicketsError || hasSuggestedTicketsError
  const isLinkedSectionLoading =
    isIntegrationLoading ||
    isAllTicketsLoading ||
    isMutationPending ||
    isAwaitingRefresh
  const isSuggestedSectionLoading =
    isIntegrationLoading ||
    isAllTicketsLoading ||
    isSuggestedTicketsLoading ||
    isMutationPending ||
    isAwaitingRefresh
  const linkingTicketId =
    activeMutation?.type === 'link' && addEventCMMSTicket.isPending
      ? activeMutation.ticketId
      : null

  const unlinkingTicketId =
    activeMutation?.type === 'unlink' && deleteEventCMMSTicket.isPending
      ? activeMutation.ticketId
      : null

  const handleAfterMutation = () => {
    setActiveMutation(null)
    setIsAwaitingRefresh(true)
    const refetches: Array<Promise<unknown>> = [
      eventCMMSTickets.refetch(),
      allTicketsQuery.refetch(),
    ]
    if (suggestionsEnabled) {
      refetches.push(suggestedTickets.refetch())
    }
    if (baseTicketIds.length > 0) {
      refetches.push(linkedTicketsQuery.refetch())
    } else {
      refetches.push(bootstrapTicketsQuery.refetch())
    }
    void Promise.all(refetches)
      .catch(() => {})
      .finally(() => {
        setIsAwaitingRefresh(false)
      })
  }

  const handleLinkTicket = (ticketId: number) => {
    if (!canMutate) {
      return
    }
    if (linkedTicketIdSet.has(ticketId)) {
      return
    }
    setActiveMutation({ ticketId, type: 'link' })
    addEventCMMSTicket.mutate(
      {
        project_id: projectId,
        event_id: numericEventId,
        cmms_ticket_id: ticketId,
      },
      {
        onSettled: handleAfterMutation,
      },
    )
  }

  const handleUnlinkTicket = (ticketId: number) => {
    if (!canMutate) {
      return
    }
    const linkRecord = eventTicketMap.get(ticketId)
    if (!linkRecord) {
      return
    }
    setActiveMutation({ ticketId, type: 'unlink' })
    deleteEventCMMSTicket.mutate(
      {
        project_id: projectId,
        event_cmms_ticket_id: linkRecord.event_cmms_ticket_id,
      },
      {
        onSettled: handleAfterMutation,
      },
    )
  }

  return (
    <Modal opened={opened} onClose={onClose} size="100%" fullScreen={false}>
      <Stack w="100%" h="80vh">
        <Group w="100%" h="100%" align="flex-start" style={{ flex: 1 }}>
          <Stack w="100%" h="100%" style={{ flex: 1 }}>
            <Title order={2}>Selected Event</Title>
            <EventCard event={event} projectId={projectId} canLink={false} />
          </Stack>
          <Stack w="100%" h="100%" style={{ flex: 1 }}>
            <Title order={2}>Linked Tickets</Title>
            {isLinkedSectionLoading ? (
              <Skeleton height={120} radius="md" w="100%" />
            ) : hasLinkedSectionError ? (
              <Text c="red" size="sm">
                Unable to load linked tickets.
              </Text>
            ) : linkedTicketData.length > 0 ? (
              linkedTicketData.map((ticket) => (
                <CMMSTicketCard
                  key={ticket.cmms_ticket_id}
                  ticket={ticket}
                  withBorder={true}
                  canLink={canMutate}
                  isLinked={true}
                  onUnlink={() => handleUnlinkTicket(ticket.cmms_ticket_id)}
                  isUnlinking={unlinkingTicketId === ticket.cmms_ticket_id}
                />
              ))
            ) : (
              <Text c="dimmed">No tickets linked to this event yet.</Text>
            )}
          </Stack>
          <Stack w="100%" h="100%" style={{ flex: 1 }}>
            <Title order={2}>Suggested Tickets</Title>
            {hasIntegrationError && (
              <Text c="red" size="sm">
                Unable to load CMMS integration data. Suggestions may be
                unavailable right now.
              </Text>
            )}
            {cmmsIntegrationId == null &&
              !isIntegrationLoading &&
              !hasIntegrationError && (
                <Text c="dimmed">
                  <IconAlertTriangle size={12} /> Unable to locate a CMMS
                  integration for this project. Suggestions may be unavailable.
                </Text>
              )}
            {isSuggestedSectionLoading ? (
              <Skeleton height={120} radius="md" w="100%" />
            ) : hasSuggestedSectionError ? (
              <Text c="red" size="sm">
                Unable to load suggested tickets.
              </Text>
            ) : suggestedTicketData.length > 0 ? (
              suggestedTicketData.map((ticket) => {
                return (
                  <CMMSTicketCard
                    key={ticket.cmms_ticket_id}
                    ticket={ticket}
                    withBorder={true}
                    canLink={canMutate}
                    isLinked={false}
                    onLink={() => handleLinkTicket(ticket.cmms_ticket_id)}
                    isLinking={linkingTicketId === ticket.cmms_ticket_id}
                  />
                )
              })
            ) : (
              <Text c="dimmed">
                No suggested tickets available for this event.
              </Text>
            )}
          </Stack>
        </Group>
      </Stack>
    </Modal>
  )
}

export default EventFirstModal
