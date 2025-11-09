import { useGetCompanyTeams, useGetCompanyTeamsWithMembers } from '@/api/admin'
import { useGetCompanyUsers } from '@/api/operational'
import { CalendarEvent } from '@/api/v1/operational/calendar'
import { useGetProjects } from '@/api/v1/operational/projects'
import {
  useGetPortfolioCalendarCategories,
  useGetPortfolioCalendarEvents,
} from '@/api/v1/protected/web-application/portfolio/calendar'
import { PageTitle } from '@/components/PageTitle'
import { useUser } from '@clerk/clerk-react'
import type { CalendarApi, EventApi, EventClickArg } from '@fullcalendar/core'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import listPlugin from '@fullcalendar/list'
import FullCalendar from '@fullcalendar/react'
import rrulePlugin from '@fullcalendar/rrule'
import type { ComboboxItem, ComboboxLikeRenderOptionInput } from '@mantine/core'
import {
  Box,
  Button,
  Group,
  Loader,
  MultiSelect,
  Paper,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconUsers } from '@tabler/icons-react'
import { useMemo, useRef, useState } from 'react'

import { CalendarItemModal } from '../projects/calendar/CalendarItemModal'
import { DetachAndEditOccurrenceModal } from '../projects/calendar/DetachAndEditOccurrenceModal'
import classes from '../projects/calendar/ProjectCalendar.module.css'
import { ViewCalendarItemModal } from '../projects/calendar/ViewCalendarItemModal'

export const PortfolioCalendar = () => {
  const { data: projects, isLoading: isLoadingProjects } = useGetProjects({
    queryParams: { deep: true },
  })
  const projectIds = projects?.map((p) => p.project_id) || []

  const {
    data: calendarItems,
    isLoading: isLoadingCalendarItems,
    refetch: refetchCalendarItems,
  } = useGetPortfolioCalendarEvents({ projectIds: projectIds })

  const { data: categories } = useGetPortfolioCalendarCategories()

  // Fetch company users and teams for assignment filter
  const { user } = useUser()
  const { data: companyUsers } = useGetCompanyUsers({})
  const { data: teams } = useGetCompanyTeams({})
  const { data: teamsWithMembers } = useGetCompanyTeamsWithMembers({})

  // Filter state
  const [selectedAssignees, setSelectedAssignees] = useState<string[]>([])
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [selectedProjects, setSelectedProjects] = useState<string[]>([])

  // Check if any filters are active
  const hasActiveFilters =
    selectedAssignees.length > 0 ||
    selectedCategories.length > 0 ||
    selectedProjects.length > 0

  // Clear all filters
  const clearFilters = () => {
    setSelectedAssignees([])
    setSelectedCategories([])
    setSelectedProjects([])
  }

  // Show my tasks (current user + teams they're part of)
  const showMyTasks = () => {
    const myUserAssignment = `user:${user?.id}`
    const myTeamAssignments = (teamsWithMembers || [])
      .filter((team) =>
        team.members?.some((member) => member.user_id === user?.id),
      )
      .map((team) => `team:${team.team_id}`)

    setSelectedAssignees([myUserAssignment, ...myTeamAssignments])
    setSelectedCategories([])
    setSelectedProjects([])
  }

  const [modalOpened, { open: openModal, close: closeModal }] =
    useDisclosure(false)
  const [selectedItem, setSelectedItem] = useState<CalendarEvent | null>(null)
  const [selectedDates, setSelectedDates] = useState<
    { start: Date; end: Date } | undefined
  >()
  const [selectedOccurrenceDate, setSelectedOccurrenceDate] =
    useState<Date | null>(null)

  const [initialScrollDone, setInitialScrollDone] = useState(false)
  const todayClickedRef = useRef(false)

  const calendarRef = useRef<FullCalendar>(null)
  const calendarContainerRef = useRef<HTMLDivElement>(null)

  const [viewModalOpened, { open: openViewModal, close: closeViewModal }] =
    useDisclosure(false)

  const [
    detachModalOpened,
    { open: openDetachModal, close: closeDetachModal },
  ] = useDisclosure(false)
  const [propsForDetachModal, setPropsForDetachModal] = useState<{
    originalSeriesItem: CalendarEvent
    occurrenceOriginalStartTime: string
    occurrenceOriginalEndTime: string
  } | null>(null)

  // Filter options
  const assigneeOptions = useMemo(() => {
    const userOpts = (companyUsers || []).map((u) => ({
      value: `user:${u.user_id}`,
      label: u.user_id === user?.id ? `Me (${u.name_long})` : u.name_long,
    }))
    const teamOpts = (teams || []).map((t) => ({
      value: `team:${t.team_id}`,
      label: t.name_long,
    }))

    // Put current user at the top
    const currentUserOpt = userOpts.find((u) => u.value === `user:${user?.id}`)
    const otherUserOpts = userOpts.filter((u) => u.value !== `user:${user?.id}`)

    return currentUserOpt
      ? [currentUserOpt, ...teamOpts, ...otherUserOpts]
      : [...teamOpts, ...userOpts]
  }, [companyUsers, teams, user?.id])

  const renderAssigneeOption = (
    input: ComboboxLikeRenderOptionInput<ComboboxItem>,
  ) => {
    const option = input.option as ComboboxItem & { kind?: 'user' | 'team' }
    const isTeam = option.value.startsWith('team:')
    return (
      <Group gap="xs" wrap="nowrap">
        {isTeam && <IconUsers size={14} />}
        <Text
          size="sm"
          style={{ flexGrow: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}
        >
          {option.label}
        </Text>
      </Group>
    )
  }

  const categoryOptions = useMemo(() => {
    return (categories || []).map((cat) => ({
      value: cat.category_id,
      label: cat.long_name,
    }))
  }, [categories])

  const projectOptions = useMemo(() => {
    return (projects || []).map((p) => ({
      value: p.project_id,
      label: p.name_long,
    }))
  }, [projects])

  const currentCalendarEvents = useMemo(() => {
    if (!calendarItems || !projects) {
      return []
    }

    // Apply filters
    let filteredItems = calendarItems

    // Filter by assignees
    if (selectedAssignees.length > 0) {
      filteredItems = filteredItems.filter((item) => {
        const itemUserIds = item.assignee_user_ids || []
        const itemTeamIds = item.assignee_team_ids || []

        return selectedAssignees.some((assignee) => {
          if (assignee.startsWith('user:')) {
            const userId = assignee.split(':')[1]
            return itemUserIds.includes(userId)
          } else if (assignee.startsWith('team:')) {
            const teamId = assignee.split(':')[1]
            return itemTeamIds.includes(teamId)
          }
          return false
        })
      })
    }

    // Filter by categories
    if (selectedCategories.length > 0) {
      filteredItems = filteredItems.filter((item) =>
        selectedCategories.includes(item.calendar_item_category_id),
      )
    }

    // Filter by projects
    if (selectedProjects.length > 0) {
      filteredItems = filteredItems.filter((item) =>
        selectedProjects.includes(item.project_id),
      )
    }

    const projectMap = new Map(projects.map((p) => [p.project_id, p.name_long]))

    const defaultEventColor = '#3788d8'
    return filteredItems.map((item) => {
      let eventStartForFC: string
      let eventEndForFC: string | undefined
      let durationForFC: string | undefined

      if (item.all_day) {
        eventStartForFC = item.start_time.substring(0, 10) // "YYYY-MM-DD"
        eventEndForFC = undefined
      } else {
        eventStartForFC = item.start_time
        if (item.rrule) {
          eventEndForFC = undefined
          const startTime = new Date(item.start_time).getTime()
          const endTime = new Date(item.end_time).getTime()
          if (endTime > startTime) {
            const diffMs = endTime - startTime
            const hours = Math.floor(diffMs / (1000 * 60 * 60))
            const minutes = Math.floor(
              (diffMs % (1000 * 60 * 60)) / (1000 * 60),
            )
            durationForFC = `${String(hours).padStart(2, '0')}:${String(
              minutes,
            ).padStart(2, '0')}`
          }
        } else {
          eventEndForFC = item.end_time
        }
      }

      const projectName = projectMap.get(item.project_id) || ''
      const title = projectName ? `${item.title} - ${projectName}` : item.title

      return {
        id: item.calendar_item_id,
        title: title,
        start: eventStartForFC,
        end: eventEndForFC,
        allDay: item.all_day,
        rrule: item.rrule,
        duration: durationForFC,
        backgroundColor: item.color || defaultEventColor,
        borderColor: item.color || defaultEventColor,
        extendedProps: {
          calendar_item_category_id: item.calendar_item_category_id,
          description: item.description,
          project_id: item.project_id,
          assignee_user_ids: item.assignee_user_ids,
          assignee_team_ids: item.assignee_team_ids,
        },
        exdate: item.exdates,
      }
    })
  }, [
    calendarItems,
    projects,
    selectedAssignees,
    selectedCategories,
    selectedProjects,
  ])

  const handleEventsSet = (_events: EventApi[]) => {
    const calendarApi: CalendarApi | undefined = calendarRef.current?.getApi()
    const calendarElement = calendarContainerRef.current
    if (!calendarApi || !calendarElement) return

    const isInitialLoad = !initialScrollDone
    const isTodayClick = todayClickedRef.current

    if ((isInitialLoad || isTodayClick) && calendarApi.view.type === 'list') {
      const today = new Date()
      const todayString = today.toISOString().split('T')[0]

      // First try to find today's element
      let targetElement = calendarElement.querySelector(
        `tr[data-date="${todayString}"]`,
      )

      // If today's element is not found, look for the first future day
      if (!targetElement) {
        const futureDayElement = calendarElement.querySelector('.fc-day-future')
        if (futureDayElement) {
          targetElement = futureDayElement
        }
      }

      if (targetElement) {
        targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }

    if (isTodayClick) {
      todayClickedRef.current = false
    }
    if (isInitialLoad) {
      setInitialScrollDone(true)
    }
  }

  const handleItemClick = (info: EventClickArg) => {
    const clickedItem = (calendarItems || []).find(
      (e) => info.event.id === e.calendar_item_id,
    )
    if (clickedItem) {
      const ext = info.event.extendedProps || {}
      const itemWithFullTitleAndAssignments = {
        ...clickedItem,
        title: info.event.title,
        assignee_user_ids:
          ext.assignee_user_ids || clickedItem.assignee_user_ids || [],
        assignee_team_ids:
          ext.assignee_team_ids || clickedItem.assignee_team_ids || [],
      }
      setSelectedItem(itemWithFullTitleAndAssignments)
      setSelectedOccurrenceDate(info.event.start)
      openViewModal()
    }
  }

  const handleModalClose = () => {
    closeModal()
    setSelectedItem(null)
    setSelectedDates(undefined)
    setSelectedOccurrenceDate(null)
  }

  const handleEditClick = (
    itemToEdit: CalendarEvent,
    editMode: 'item' | 'series',
  ) => {
    closeViewModal()

    // Find the original item from the raw `calendarItems` array to ensure we have the clean title
    const originalItem = (calendarItems || []).find(
      (e) => e.calendar_item_id === itemToEdit.calendar_item_id,
    )

    if (!originalItem) {
      console.error('Could not find original calendar item to edit.')
      return
    }

    if (editMode === 'item' && originalItem.rrule && selectedOccurrenceDate) {
      setPropsForDetachModal({
        originalSeriesItem: originalItem,
        occurrenceOriginalStartTime: selectedOccurrenceDate.toISOString(),
        occurrenceOriginalEndTime: new Date(
          selectedOccurrenceDate.getTime() + 60 * 60 * 1000,
        ).toISOString(),
      })
      openDetachModal()
    } else {
      setSelectedItem(originalItem)
      openModal()
    }
  }

  return (
    <Stack p="md" h="100%">
      <PageTitle
        info={
          <Text>
            This calendar displays events and tasks across all projects in the
            portfolio. Use the filters to narrow down the view.
          </Text>
        }
      >
        Portfolio Calendar
      </PageTitle>

      {/* Filters */}
      <Group gap="md" wrap="wrap" align="end">
        <Tooltip label="Show both personal and team tasks" withArrow>
          <Button variant="filled" onClick={showMyTasks} size="sm">
            Show My Tasks
          </Button>
        </Tooltip>
        <MultiSelect
          label="Filter by Assignees"
          placeholder="Select assignees"
          data={assigneeOptions}
          value={selectedAssignees}
          onChange={setSelectedAssignees}
          searchable
          clearable
          renderOption={renderAssigneeOption}
          style={{ minWidth: 200 }}
        />
        <MultiSelect
          label="Filter by Categories"
          placeholder="Select categories"
          data={categoryOptions}
          value={selectedCategories}
          onChange={setSelectedCategories}
          searchable
          clearable
          style={{ minWidth: 200 }}
        />
        <MultiSelect
          label="Filter by Projects"
          placeholder="Select projects"
          data={projectOptions}
          value={selectedProjects}
          onChange={setSelectedProjects}
          searchable
          clearable
          style={{ minWidth: 200 }}
        />
        <Button
          variant="outline"
          onClick={clearFilters}
          disabled={!hasActiveFilters}
          size="sm"
        >
          Clear Filters
        </Button>
      </Group>

      <Paper
        p="md"
        withBorder
        flex={1}
        display="flex"
        style={{
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <Box
          flex={1}
          style={{
            overflow: 'auto',
          }}
          className={classes.calendarWrapper}
        >
          {isLoadingCalendarItems || isLoadingProjects ? (
            <Stack h="100%" align="center" justify="center">
              <Loader />
            </Stack>
          ) : (
            <div ref={calendarContainerRef} style={{ height: '100%' }}>
              <FullCalendar
                ref={calendarRef}
                plugins={[
                  dayGridPlugin,
                  interactionPlugin,
                  rrulePlugin,
                  listPlugin,
                ]}
                initialView="list"
                headerToolbar={{
                  left: 'prev,next today',
                  center: 'title',
                  right: 'dayGridMonth,list',
                }}
                customButtons={{
                  today: {
                    text: 'Today',
                    click: () => {
                      todayClickedRef.current = true
                      calendarRef.current?.getApi()?.today()
                    },
                  },
                }}
                views={{
                  dayGridMonth: {
                    buttonText: 'Month',
                  },
                  timeGridWeek: {
                    buttonText: 'Week',
                  },
                  list: {
                    duration: { months: 3 },
                    buttonText: 'List',
                    dayCellClassNames: getListDayClassNames,
                  },
                }}
                dayMaxEvents={true}
                weekends={true}
                events={currentCalendarEvents}
                dayCellClassNames={getDayCellClassNames}
                height="100%"
                eventClick={handleItemClick}
                firstDay={1}
                timeZone="UTC"
                eventsSet={handleEventsSet}
              />
            </div>
          )}
        </Box>
      </Paper>
      <CalendarItemModal
        opened={modalOpened}
        onClose={handleModalClose}
        item={selectedItem ?? undefined}
        startDate={selectedDates?.start}
        endDate={selectedDates?.end}
        onSuccessRefetch={refetchCalendarItems}
        projectId={selectedItem?.project_id}
        projects={projects}
      />
      <ViewCalendarItemModal
        opened={viewModalOpened}
        onClose={closeViewModal}
        onEdit={handleEditClick}
        onDeleteSuccess={refetchCalendarItems}
        item={selectedItem ?? undefined}
        occurrenceDate={selectedOccurrenceDate}
        categories={categories}
      />
      {propsForDetachModal && (
        <DetachAndEditOccurrenceModal
          opened={detachModalOpened}
          onClose={closeDetachModal}
          onSuccess={() => {
            closeDetachModal()
            refetchCalendarItems()
          }}
          projectId={propsForDetachModal.originalSeriesItem.project_id}
          originalSeriesItem={propsForDetachModal.originalSeriesItem}
          occurrenceOriginalStartTime={
            propsForDetachModal.occurrenceOriginalStartTime
          }
          occurrenceOriginalEndTime={
            propsForDetachModal.occurrenceOriginalEndTime
          }
        />
      )}
    </Stack>
  )
}

const getDayCellClassNames = (arg: { date: Date }) => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  if (arg.date < today) {
    return [classes.previousDays]
  }
  return []
}

const getListDayClassNames = (arg: { date: Date }) => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  if (arg.date < today) {
    return [classes.previousDays]
  }
  return []
}
