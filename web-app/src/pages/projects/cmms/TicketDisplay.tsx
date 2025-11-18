import {
  CMMSTicket,
  useGetCMMSTickets,
} from '@/api/v1/operational/project/cmms_tickets'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import {
  Group,
  MultiSelect,
  ScrollArea,
  Stack,
  Switch,
  Text,
} from '@mantine/core'
import { useMemo, useState } from 'react'
import { useParams } from 'react-router'

import CMMSTicketCard from './CMMSTicketCard'
import PlaceholderTicket from './PlaceholderTicket'

const Page = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([])
  const [showClosed, setShowClosed] = useState(false)

  // Calculate start date for last 90 days (computed once on mount)
  const [startDate] = useState(
    () =>
      new Date(new Date().getTime() - 90 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0],
  )

  const tickets = useGetCMMSTickets({
    pathParams: { projectId: projectId || '' },
    queryParams: {
      start: startDate,
    },
    queryOptions: { enabled: !!projectId },
  })

  const availableStatuses = useMemo(() => {
    if (!tickets.data?.data) return []
    const statuses = new Set(
      tickets.data.data.map((ticket) => ticket.status || ''),
    )
    return Array.from(statuses).filter(Boolean)
  }, [tickets.data])

  const sortedAndFilteredTickets = useMemo(() => {
    if (!tickets.data?.data) return []

    const statusOrder: { [key: string]: number } = {
      open: 1,
      'in progress': 2,
      'awaiting triage': 3,
      resolved: 4,
      closed: 5,
    }

    let filteredTickets = tickets.data.data

    if (!showClosed) {
      filteredTickets = filteredTickets.filter(
        (ticket) => ticket.status?.toLowerCase() !== 'closed',
      )
    }

    if (selectedStatuses.length > 0) {
      filteredTickets = filteredTickets.filter((ticket) =>
        selectedStatuses.includes(ticket.status || ''),
      )
    }

    return filteredTickets.sort((a, b) => {
      const statusA = a.status?.toLowerCase() || ''
      const statusB = b.status?.toLowerCase() || ''
      return (statusOrder[statusA] || 99) - (statusOrder[statusB] || 99)
    })
  }, [tickets.data, selectedStatuses, showClosed])

  if (tickets.isLoading) {
    return <PageLoader />
  }

  const renderContent = () => {
    if (!tickets.data?.metadata.integration_configured) {
      return <PlaceholderTicket />
    }

    if (tickets.data?.data.length === 0) {
      return <Text>No tickets created in the last 90 days.</Text>
    }

    return (
      <>
        <Group>
          <MultiSelect
            label="Filter by status"
            placeholder="Select statuses"
            data={availableStatuses}
            value={selectedStatuses}
            onChange={setSelectedStatuses}
            clearable
          />
          <Switch
            label="Show closed tickets"
            checked={showClosed}
            onChange={(event) => setShowClosed(event.currentTarget.checked)}
          />
        </Group>
        <ScrollArea.Autosize flex={1} type="scroll">
          <Stack gap="md">
            {sortedAndFilteredTickets.map((ticket: CMMSTicket) => (
              <CMMSTicketCard key={ticket.id} ticket={ticket} />
            ))}
          </Stack>
        </ScrollArea.Autosize>
      </>
    )
  }

  return (
    <Stack h="100%" p="md">
      <PageTitle
        info="CMMS stands for Computerized Maintenance Management System. It's a software
        application that helps you manage and track your assets, work orders, and
        maintenance activities. You can use it to schedule preventive
        maintenance, respond to corrective maintenance requests, and analyze
        maintenance data to improve your asset performance."
      >
        CMMS Tickets
      </PageTitle>
      {renderContent()}
    </Stack>
  )
}

export default Page
