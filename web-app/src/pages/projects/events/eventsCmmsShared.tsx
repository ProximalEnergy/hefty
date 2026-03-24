import { useGetCMMSPermissions } from '@/api/v1/operational/project/cmms_permissions'
import {
  type CMMSTicket,
  useGetCMMSTickets,
} from '@/api/v1/operational/project/cmms_tickets'
import {
  type EventCMMSTicket,
  useGetEventCMMSTicketsByEventIds,
} from '@/api/v1/protected/web-application/projects/event-cmms-tickets/event_cmms_tickets'
import type { EnrichedEvent } from '@/api/v1/protected/web-application/projects/events/events'
import type { EventFirstModalEvent, EventSummary } from '@/hooks/types'
import {
  ActionIcon,
  Badge,
  Box,
  Group,
  Skeleton,
  Text,
  Tooltip,
} from '@mantine/core'
import {
  IconCircleCheck,
  IconLink,
  IconPlugConnected,
  IconPlugOff,
  IconPlus,
} from '@tabler/icons-react'
import type { MouseEvent } from 'react'
import { useMemo } from 'react'
import { Link, useParams } from 'react-router'

/** Build payload for EventFirstModal from homepage or events-list rows. */
export function eventToModalEventForCmms(
  row: EventSummary | EnrichedEvent,
): EventFirstModalEvent {
  if ('device_type_name' in row) {
    const s = row
    return {
      event_id: s.event_id,
      event_type_id: null,
      device_id: 0,
      device_name_full: s.device_name_full,
      time_start: s.time_start,
      time_end: s.time_end,
      time_detected: s.time_start,
      time_last_analyzed: null,
      failure_mode_id: null,
      failure_mode: s.failure_mode
        ? {
            failure_mode_id: 0,
            device_type_id: 0,
            name_short: s.failure_mode,
            name_long: s.failure_mode,
          }
        : null,
      root_cause_id: null,
      loss_total_financial: s.loss_total_financial,
      loss_daily_financial: s.loss_daily_financial,
    }
  }
  const e = row as EnrichedEvent
  return {
    event_id: e.event_id,
    event_type_id: e.event_type_id ?? null,
    device_id: e.device_id,
    device_name_full: e.device_name_full,
    time_start: e.time_start,
    time_end: e.time_end,
    time_detected: e.time_detected,
    time_last_analyzed: e.time_last_analyzed,
    failure_mode_id: e.failure_mode_id,
    failure_mode: e.failure_mode ?? null,
    root_cause_id: e.root_cause_id,
    loss_total_financial: e.loss_total_financial,
    loss_daily_financial: e.loss_daily_financial,
  }
}

export function EventsCmmsHeaderBadges({
  hasCmmsIntegration,
  permissionsLoading,
}: {
  hasCmmsIntegration: boolean
  permissionsLoading: boolean
}) {
  if (permissionsLoading) {
    return null
  }
  if (hasCmmsIntegration) {
    return (
      <Tooltip label="CMMS integration is enabled for this project">
        <Badge
          size="sm"
          color="teal"
          variant="light"
          leftSection={<IconPlugConnected size={12} />}
        >
          CMMS
        </Badge>
      </Tooltip>
    )
  }
  return (
    <Tooltip label="No CMMS integration configured for this project">
      <Badge
        size="sm"
        color="gray"
        variant="light"
        leftSection={<IconPlugOff size={12} />}
      >
        No CMMS
      </Badge>
    </Tooltip>
  )
}

function ticketByIdMap(
  tickets: CMMSTicket[] | undefined,
): Map<number, CMMSTicket> {
  const m = new Map<number, CMMSTicket>()
  tickets?.forEach((t) => m.set(t.cmms_ticket_id, t))
  return m
}

/** Short label + extra tooltip lines from linked rows and ticket payloads. */
function linkedCmmsDisplayForEvent(
  rows: EventCMMSTicket[],
  byId: Map<number, CMMSTicket>,
): { label: string; tooltipExtra: string } {
  const detailLines: string[] = []
  const statusSeen = new Set<string>()
  rows.forEach((r) => {
    const t = byId.get(r.cmms_ticket_id)
    const statusRaw = t?.status?.trim()
    const status = statusRaw || 'Unknown'
    statusSeen.add(status)
    const key = t?.key?.trim() || `#${r.cmms_ticket_id}`
    detailLines.push(`${key}: ${status}`)
  })
  const uniqueStatuses = [...statusSeen]
  let label: string
  if (uniqueStatuses.every((s) => s === 'Unknown')) {
    label = 'Linked'
  } else if (uniqueStatuses.length === 1) {
    label = uniqueStatuses[0]!
  } else if (uniqueStatuses.length === 2) {
    label = uniqueStatuses.join(' · ')
  } else {
    label = `${uniqueStatuses.slice(0, 2).join(' · ')} +${
      uniqueStatuses.length - 2
    }`
  }
  return {
    label,
    tooltipExtra: detailLines.join('\n'),
  }
}

/** CMMS permissions + batched event–ticket links for the current project. */
export function useProjectEventsCmms(eventIds: number[]) {
  const { projectId } = useParams<{ projectId: string }>()
  const cmmsPermissions = useGetCMMSPermissions({
    pathParams: { project_id: projectId! },
    queryOptions: { enabled: !!projectId },
  })
  const hasCmmsIntegration =
    cmmsPermissions.data?.some((permission) => permission.can_view) ?? false

  const eventCmmsLinks = useGetEventCMMSTicketsByEventIds({
    pathParams: { project_id: projectId! },
    eventIds,
    queryOptions: {
      enabled: !!projectId && eventIds.length > 0 && hasCmmsIntegration,
    },
  })

  const linkCountByEventId = useMemo(() => {
    const m = new Map<number, number>()
    eventCmmsLinks.data?.forEach((r) => {
      m.set(r.event_id, (m.get(r.event_id) ?? 0) + 1)
    })
    return m
  }, [eventCmmsLinks.data])

  const linkRowsByEventId = useMemo(() => {
    const m = new Map<number, EventCMMSTicket[]>()
    eventCmmsLinks.data?.forEach((r) => {
      const list = m.get(r.event_id) ?? []
      list.push(r)
      m.set(r.event_id, list)
    })
    return m
  }, [eventCmmsLinks.data])

  const linkedCmmsTicketIds = useMemo(() => {
    const s = new Set<number>()
    eventCmmsLinks.data?.forEach((r) => s.add(r.cmms_ticket_id))
    return Array.from(s)
  }, [eventCmmsLinks.data])

  const linkedTicketsDetailQuery = useGetCMMSTickets({
    pathParams: { project_id: projectId! },
    queryParams: {
      cmms_ticket_ids: linkedCmmsTicketIds,
      include_json_raw: false,
    },
    queryOptions: {
      enabled:
        !!projectId && hasCmmsIntegration && linkedCmmsTicketIds.length > 0,
    },
  })

  const ticketDetailsById = useMemo(
    () => ticketByIdMap(linkedTicketsDetailQuery.data?.data),
    [linkedTicketsDetailQuery.data],
  )

  const linkedDisplayByEventId = useMemo(() => {
    const m = new Map<number, { label: string; tooltipExtra: string }>()
    linkRowsByEventId.forEach((rows, eventId) => {
      m.set(eventId, linkedCmmsDisplayForEvent(rows, ticketDetailsById))
    })
    return m
  }, [linkRowsByEventId, ticketDetailsById])

  const linkedTicketDetailsLoading =
    linkedCmmsTicketIds.length > 0 &&
    linkedTicketsDetailQuery.isLoading &&
    !linkedTicketsDetailQuery.data

  return {
    projectId: projectId ?? '',
    hasCmmsIntegration,
    permissionsLoading: cmmsPermissions.isLoading,
    linksLoading: eventCmmsLinks.isLoading,
    linksData: eventCmmsLinks.data,
    linkCountByEventId,
    linkedDisplayByEventId,
    linkedTicketDetailsLoading,
  }
}

export function EventsCmmsTableCell({
  projectId,
  hasCmmsIntegration,
  linksLoading,
  linkCount,
  linkedTicketDetailsLoading,
  linkedDisplay,
  onOpenLinkage,
}: {
  projectId: string
  hasCmmsIntegration: boolean
  linksLoading: boolean
  linkCount: number
  linkedTicketDetailsLoading: boolean
  linkedDisplay: { label: string; tooltipExtra: string } | null
  onOpenLinkage: () => void
}) {
  if (!hasCmmsIntegration) {
    return null
  }
  if (linksLoading) {
    return <Skeleton height={28} width={72} radius="sm" />
  }
  const stopRowNav = (e: MouseEvent) => {
    e.stopPropagation()
  }
  if (linkCount > 0) {
    const baseTip = `${linkCount} CMMS ticket${
      linkCount !== 1 ? 's' : ''
    } linked — click to open ticket linkage suite`
    const tip =
      linkedDisplay?.tooltipExtra != null && linkedDisplay.tooltipExtra !== ''
        ? `${baseTip}\n\n${linkedDisplay.tooltipExtra}`
        : baseTip
    return (
      <Box onClick={stopRowNav}>
        <Tooltip label={tip} multiline maw={320}>
          <Group
            gap={6}
            wrap="nowrap"
            align="center"
            style={{ cursor: 'pointer' }}
            onClick={(e) => {
              e.stopPropagation()
              onOpenLinkage()
            }}
          >
            <IconCircleCheck
              size={22}
              stroke={1.5}
              color="var(--mantine-color-green-6)"
              aria-hidden
            />
            {linkedTicketDetailsLoading ? (
              <Skeleton height={14} width={72} radius="sm" />
            ) : (
              <Text size="xs" c="dimmed" lineClamp={1} maw={140}>
                {linkedDisplay?.label ?? 'Linked'}
              </Text>
            )}
          </Group>
        </Tooltip>
      </Box>
    )
  }
  return (
    <Box onClick={stopRowNav}>
      <Group gap={4} wrap="nowrap">
        <Tooltip label="Open ticket linkage suite">
          <ActionIcon
            variant="light"
            color="gray"
            size="sm"
            onClick={() => {
              onOpenLinkage()
            }}
            aria-label="Open ticket linkage suite"
          >
            <IconLink size={18} stroke={1.5} />
          </ActionIcon>
        </Tooltip>
        <Tooltip label="View or create CMMS tickets">
          <ActionIcon
            variant="light"
            color="gray"
            size="sm"
            component={Link}
            to={`/projects/${projectId}/cmms/ticket-display`}
            aria-label="View or create CMMS tickets"
          >
            <IconPlus size={18} stroke={1.5} />
          </ActionIcon>
        </Tooltip>
      </Group>
    </Box>
  )
}
