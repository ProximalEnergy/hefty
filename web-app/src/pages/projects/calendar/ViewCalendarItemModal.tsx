import { useGetCompanyTeamsWithMembers } from '@/api/admin'
import { useGetCompanyUsers } from '@/api/operational'
import {
  CalendarEvent,
  CalendarEventCategory,
  useCalendarOccurrenceAction,
  useDeleteCalendarEvent,
} from '@/api/v1/operational/calendar'
import {
  Box,
  Button,
  ColorSwatch,
  Divider,
  Group,
  Menu,
  Modal,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconUsers } from '@tabler/icons-react'
import { useMemo } from 'react'
import { useParams } from 'react-router'
import { rrulestr } from 'rrule'

interface ViewCalendarItemModalProps {
  opened: boolean
  onClose: () => void
  onEdit: (item: CalendarEvent, editMode: 'item' | 'series') => void
  onDeleteSuccess: () => void
  item?: CalendarEvent
  occurrenceDate?: Date | null
  isReadOnly?: boolean
  categories?: CalendarEventCategory[]
}

// Helper to format dates/times
const formatDateTime = (dateString: string, allDay: boolean): string => {
  const date = new Date(dateString)
  if (allDay) {
    // For all-day events, show only the date part in local timezone
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      timeZone: 'UTC', // Treat date part as timezone-agnostic
    })
  }
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  })
}

// Simple helper to describe recurrence
const describeRecurrence = (rruleString?: string): string => {
  if (!rruleString) {
    return 'Does not repeat'
  }
  try {
    const rule = rrulestr(rruleString)
    return `Repeats ${rule.toText()}`
  } catch (e) {
    console.error('Error parsing RRULE:', e)
    return 'Repeats (custom rule)'
  }
}

const notificationOffsetOptions: { [key: string]: string } = {
  '0d': 'On the day of the event',
  '1d': '1 day before',
  '3d': '3 days before',
  '7d': '7 days before',
  '14d': '14 days before',
}

const describeNotifications = (
  methods?: string[],
  offsets?: string[],
): string | undefined => {
  if (!methods || methods.length === 0 || !offsets || offsets.length === 0) {
    return undefined
  }

  const methodDescriptions = methods
    .map((method) => {
      if (method.toLowerCase() === 'email') return 'Email'
      return method // Or some other formatting
    })
    .join(', ')

  const offsetDescriptions = offsets
    .map((offset) => notificationOffsetOptions[offset] || offset)
    .join(', ')

  if (methodDescriptions && offsetDescriptions) {
    return `Reminders via ${methodDescriptions}: ${offsetDescriptions}.`
  }
  return undefined
}

// Helper function to parse text and convert URLs to clickable links
const ClickableUrls = ({ text }: { text: string }) => {
  const urlRegex = /(https?:\/\/[^\s]+)/g
  const parts = text.split(urlRegex)

  return (
    <>
      {parts.map((part, index) => {
        if (part.match(urlRegex)) {
          return (
            <a
              key={index}
              href={part}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                wordBreak: 'break-all',
              }}
            >
              {part}
            </a>
          )
        }
        return part
      })}
    </>
  )
}

export const ViewCalendarItemModal = ({
  opened,
  onClose,
  onEdit,
  onDeleteSuccess,
  item,
  occurrenceDate,
  isReadOnly,
  categories,
}: ViewCalendarItemModalProps) => {
  const { projectId: projectIdFromParams } = useParams<{ projectId: string }>()
  const projectId = item?.project_id || projectIdFromParams

  const deleteCalendarEvent = useDeleteCalendarEvent()
  const occurrenceAction = useCalendarOccurrenceAction()

  // Resolve user names for assignees from company users endpoint
  const { data: companyUsers } = useGetCompanyUsers({})
  const userIdToName = useMemo(() => {
    const m = new Map<string, string>()
    ;(companyUsers || []).forEach((u) => m.set(u.user_id, u.name_long))
    return m
  }, [companyUsers])

  // Resolve team names and members for assignees from company teams endpoint
  const { data: teamsWithMembers } = useGetCompanyTeamsWithMembers({})
  const teamIdToName = useMemo(() => {
    const m = new Map<string, string>()
    ;(teamsWithMembers || []).forEach((t) => {
      m.set(t.team_id, t.name_long)
    })
    return m
  }, [teamsWithMembers])

  const teamIdToMembers = useMemo(() => {
    const m = new Map<string, string[]>()
    ;(teamsWithMembers || []).forEach((t) => {
      m.set(
        t.team_id,
        t.members.map((m) => m.name_long),
      )
    })
    return m
  }, [teamsWithMembers])

  const category = useMemo(() => {
    if (!categories || !item) {
      return undefined
    }
    return categories.find(
      (cat) => cat.category_id === item.calendar_item_category_id,
    )
  }, [categories, item])

  const handleEditClick = () => {
    if (item) {
      onEdit(item, 'item')
    }
  }

  const handleEditSeriesClick = () => {
    if (item) {
      onEdit(item, 'series')
    }
  }

  const handleDeleteClick = async () => {
    if (!item || !projectId) return

    try {
      await deleteCalendarEvent.mutateAsync({
        projectId: projectId,
        eventId: item.calendar_item_id,
      })
      notifications.show({
        title: 'Success',
        message: 'Item deleted successfully',
        color: 'green',
      })
      onDeleteSuccess()
      onClose()
    } catch (error) {
      console.error('Error deleting calendar item:', error)
      notifications.show({
        title: 'Error',
        message: 'Failed to delete item',
        color: 'red',
      })
    }
  }

  // New handler for deleting a single occurrence
  const handleDeleteOccurrenceClick = async () => {
    if (!item || !projectId || !occurrenceDate) {
      notifications.show({
        title: 'Error',
        message: 'Cannot determine the specific occurrence date.',
        color: 'red',
      })
      return
    }

    const actualOccurrenceDate = new Date(occurrenceDate)
    const exceptionDateStr = actualOccurrenceDate.toISOString().split('T')[0]

    const seriesCalendarItemId = item.calendar_item_id

    try {
      await occurrenceAction.mutateAsync({
        projectId: projectId!,
        calendarItemId: seriesCalendarItemId,
        exceptionDate: exceptionDateStr,
        payload: { is_cancelled: true },
      })
      notifications.show({
        title: 'Success',
        message: `Occurrence on ${exceptionDateStr} cancelled.`,
        color: 'green',
      })
      onDeleteSuccess() // This should refetch calendar events via query invalidation in the hook
      onClose()
    } catch (error) {
      console.error('Error cancelling occurrence:', error)
      notifications.show({
        title: 'Error',
        message: 'Failed to cancel occurrence.',
        color: 'red',
      })
    }
  }

  if (!item) return null // Don't render if no item is selected

  const recurrenceText = describeRecurrence(item.rrule)
  const notificationText = describeNotifications(
    item.notify_method,
    item.notify_offsets,
  )

  const assignedUserNames = (item?.assignee_user_ids || [])
    .map((id) => {
      const userName = userIdToName.get(id)
      if (userName) {
        return userName
      }
      // If users are still loading, show a loading indicator
      if (companyUsers === undefined) {
        return 'Loading...'
      }
      // If users loaded but name not found, show the ID
      return `User ${id}`
    })
    .join(', ')

  const assignedTeamNames = (item?.assignee_team_ids || [])
    .map((id) => {
      const teamName = teamIdToName.get(id)
      if (teamName) {
        return teamName
      }
      // If teams are still loading, show a loading indicator
      if (teamsWithMembers === undefined) {
        return 'Loading...'
      }
      // If teams loaded but name not found, show the ID
      return `Team ${id}`
    })
    .join(', ')

  const hasAssignments = assignedUserNames || assignedTeamNames

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Text style={{ overflowWrap: 'break-word', wordBreak: 'break-all' }}>
          {item.title}
        </Text>
      }
      size="md"
    >
      <Stack gap="md">
        <Group gap="xs" align="center">
          <ColorSwatch
            color={item.color || category?.color_code || '#868e96'}
            size={14}
          />
          <Text fw={500}>
            {category ? category.long_name : 'Unknown Category'}
          </Text>
        </Group>

        <Divider />

        <Box>
          <Text fw={500}>Date</Text>
          <Text>
            {formatDateTime(item.start_time, item.all_day)}
            {!item.all_day &&
              item.start_time !== item.end_time &&
              ` to ${formatDateTime(item.end_time, item.all_day)}`}
          </Text>
          {item.rrule && <Text size="sm">{recurrenceText}</Text>}
        </Box>

        {hasAssignments && (
          <Box>
            <Text fw={500}>Assigned</Text>
            {assignedTeamNames && (
              <Group gap="xs" align="center" mb="xs">
                <IconUsers size={14} />
                <Text size="sm">
                  {(item?.assignee_team_ids || []).map((teamId, index) => {
                    const teamName = teamIdToName.get(teamId)
                    const teamMembers = teamIdToMembers.get(teamId) || []
                    const memberText =
                      teamMembers.length > 0
                        ? `Members: ${teamMembers.join(', ')}`
                        : 'No members'

                    return (
                      <span key={teamId}>
                        {index > 0 && ', '}
                        <Tooltip label={memberText} withArrow>
                          <span style={{ cursor: 'help' }}>
                            {teamName || `Team ${teamId}`}
                          </span>
                        </Tooltip>
                      </span>
                    )
                  })}
                </Text>
              </Group>
            )}
            {assignedUserNames && <Text size="sm">{assignedUserNames}</Text>}
          </Box>
        )}

        {item.description && (
          <Box>
            <Text fw={500}>Description</Text>
            <Text
              component="div"
              style={{
                whiteSpace: 'pre-wrap',
                overflowWrap: 'break-word',
              }}
            >
              <ClickableUrls text={item.description} />
            </Text>
          </Box>
        )}

        {notificationText && (
          <Box>
            <Text fw={500}>Reminders</Text>
            <Text size="sm">{notificationText}</Text>
          </Box>
        )}

        <Divider />

        {!isReadOnly && (
          <Group justify="space-between" mt="sm">
            {item.rrule ? (
              <Menu shadow="md" width={200}>
                <Menu.Target>
                  <Button
                    variant="filled"
                    color="red"
                    loading={
                      deleteCalendarEvent.isPending ||
                      occurrenceAction.isPending
                    }
                  >
                    Delete
                  </Button>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Item
                    onClick={handleDeleteOccurrenceClick}
                    color="red"
                    disabled={
                      occurrenceAction.isPending ||
                      deleteCalendarEvent.isPending
                    }
                  >
                    Delete Occurrence
                  </Menu.Item>
                  <Menu.Item onClick={handleDeleteClick} color="red">
                    Delete Series
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            ) : (
              <Button
                variant="filled"
                color="red"
                onClick={handleDeleteClick}
                loading={deleteCalendarEvent.isPending}
              >
                Delete
              </Button>
            )}
            <Group>
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
              {item.rrule ? (
                <Menu shadow="md" width={200}>
                  <Menu.Target>
                    <Button>Edit</Button>
                  </Menu.Target>
                  <Menu.Dropdown>
                    <Menu.Item onClick={handleEditClick}>
                      Edit Occurrence
                    </Menu.Item>
                    <Menu.Item onClick={handleEditSeriesClick}>
                      Edit Series
                    </Menu.Item>
                  </Menu.Dropdown>
                </Menu>
              ) : (
                <Button onClick={handleEditClick}>Edit Item</Button>
              )}
            </Group>
          </Group>
        )}
        {isReadOnly && (
          <Group justify="flex-end" mt="sm">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </Group>
        )}
      </Stack>
    </Modal>
  )
}
