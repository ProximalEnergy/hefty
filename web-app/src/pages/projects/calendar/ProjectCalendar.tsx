import {
  CalendarEvent,
  useGetCalendarEventCategories,
  useGetCalendarEvents,
} from '@/api/v1/operational/calendar'
import { useGetProject } from '@/api/v1/operational/projects'
import { PageTitle } from '@/components/PageTitle'
import { DateSelectArg, EventClickArg } from '@fullcalendar/core'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import listPlugin from '@fullcalendar/list'
import FullCalendar from '@fullcalendar/react'
import rrulePlugin from '@fullcalendar/rrule'
import { Box, Paper, Stack, Text } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router'

import { CalendarItemModal } from './CalendarItemModal'
import { DetachAndEditOccurrenceModal } from './DetachAndEditOccurrenceModal'
import classes from './ProjectCalendar.module.css'
import { ViewCalendarItemModal } from './ViewCalendarItemModal'

export const ProjectCalendar = () => {
  const { projectId } = useParams()
  const project = useGetProject({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { deep: true },
  })

  const {
    data: calendarItems,
    isLoading: isLoadingCalendarItems,
    refetch: refetchCalendarItems,
  } = useGetCalendarEvents({
    pathParams: { projectId: projectId || '-1' },
  })
  const { data: categories } = useGetCalendarEventCategories({
    pathParams: { projectId: projectId || '-1' },
  })

  const [modalOpened, { open: openModal, close: closeModal }] =
    useDisclosure(false)
  const [selectedItem, setSelectedItem] = useState<any | undefined>()
  const [selectedDates, setSelectedDates] = useState<
    { start: Date; end: Date } | undefined
  >()
  const [currentCalendarEvents, setCurrentCalendarEvents] = useState<any[]>([])
  const [selectedOccurrenceDate, setSelectedOccurrenceDate] =
    useState<Date | null>(null)
  const [selectedOccurrenceEndDate, setSelectedOccurrenceEndDate] =
    useState<Date | null>(null)

  const [calendarViewInfo, setCalendarViewInfo] = useState<{
    view: string
    activeStart: Date
    activeEnd: Date
  } | null>(null)
  const calendarRef = useRef<FullCalendar>(null)

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

  useEffect(() => {
    if (!isLoadingCalendarItems && calendarItems) {
      const defaultEventColor = '#3788d8'
      const events = (calendarItems || []).map((item) => {
        let eventStartForFC: string
        let eventEndForFC: string | undefined
        let durationForFC: string | undefined

        if (item.all_day) {
          eventStartForFC = item.start_time.substring(0, 10) // "YYYY-MM-DD"
          eventEndForFC = undefined // For recurring all-day, rrule defines occurrences
        } else {
          eventStartForFC = item.start_time // Full ISO string for timed events
          if (item.rrule) {
            // Timed recurring: use duration, end is undefined for FullCalendar event object
            eventEndForFC = undefined
            const startTime = new Date(item.start_time).getTime()
            // item.end_time for timed recurring events should store the end of the *first* instance
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
            // Timed non-recurring
            eventEndForFC = item.end_time
          }
        }

        return {
          id: item.calendar_item_id,
          title: item.title,
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
          },
          exdate: item.exdates,
        }
      })
      setCurrentCalendarEvents(events)

      // Restore calendar view
      if (calendarRef.current && calendarViewInfo) {
        const calendarApi = calendarRef.current.getApi()
        // Check if the current view in FullCalendar matches what we stored,
        // and if the start date of the current view is different from what we want to restore.
        // Only navigate if necessary to avoid potential loops or unnecessary re-renders.
        if (
          calendarApi.view.type !== calendarViewInfo.view ||
          calendarApi.view.activeStart.getTime() !==
            calendarViewInfo.activeStart.getTime()
        ) {
          calendarApi.changeView(
            calendarViewInfo.view,
            calendarViewInfo.activeStart,
          )
        } else {
          // If view type is the same, but maybe events reloaded, ensure date is still correct.
          // This might be redundant if changeView above handles it, but can be a fallback.
          // Or, if only events changed and view/date were already correct, this might not be needed.
          // For simplicity, let's ensure gotoDate is called if the activeStart doesn't match.
          if (
            calendarApi.view.activeStart.getTime() !==
            calendarViewInfo.activeStart.getTime()
          ) {
            calendarApi.gotoDate(calendarViewInfo.activeStart)
          }
        }
      }
    }
  }, [isLoadingCalendarItems, calendarItems, calendarViewInfo])

  const handleItemClick = (info: EventClickArg) => {
    const clickedItem = (calendarItems || []).find(
      (e) => info.event.id === e.calendar_item_id,
    )
    if (clickedItem) {
      setSelectedItem(clickedItem)
      setSelectedOccurrenceDate(info.event.start)
      setSelectedOccurrenceEndDate(info.event.end)
      openViewModal()
    } else {
      console.error(
        'Could not find matching calendar item for clicked event id:',
        info.event.id,
      )
    }
  }

  const handleSelect = (info: DateSelectArg) => {
    setSelectedDates({
      start: info.start,
      end: info.end,
    })
    setSelectedItem(undefined)
    openModal()
  }

  const handleModalClose = () => {
    closeModal()
    setSelectedItem(undefined)
    setSelectedDates(undefined)
    setSelectedOccurrenceDate(null)
  }

  const handleEditClick = (
    itemToEdit: CalendarEvent,
    editMode: 'item' | 'series',
  ) => {
    closeViewModal()
    if (editMode === 'item' && itemToEdit.rrule && selectedOccurrenceDate) {
      setPropsForDetachModal({
        originalSeriesItem: itemToEdit,
        occurrenceOriginalStartTime: selectedOccurrenceDate.toISOString(),
        occurrenceOriginalEndTime: selectedOccurrenceEndDate
          ? selectedOccurrenceEndDate.toISOString()
          : new Date(
              selectedOccurrenceDate.getTime() + 60 * 60 * 1000,
            ).toISOString(),
      })
      openDetachModal()
    } else {
      setSelectedItem(itemToEdit)
      openModal()
    }
  }

  return (
    <Stack p="md" h="100%">
      <PageTitle
        info={
          <Text>
            This calendar displays events and tasks for the project. Click on a
            date to create a new item, or click on an existing item to view or
            edit it.
          </Text>
        }
      >
        {project.data?.name_long} Calendar
      </PageTitle>
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
          <FullCalendar
            ref={calendarRef}
            plugins={[
              dayGridPlugin,
              interactionPlugin,
              rrulePlugin,
              listPlugin,
            ]}
            initialView="dayGridMonth"
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'dayGridMonth,list',
            }}
            buttonText={{
              today: 'Today',
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
              },
            }}
            editable={true}
            selectable={true}
            selectMirror={true}
            dayMaxEvents={true}
            weekends={true}
            events={currentCalendarEvents}
            dayCellClassNames={getDayCellClassNames}
            height="100%"
            select={handleSelect}
            eventClick={handleItemClick}
            firstDay={1}
            timeZone="UTC"
            datesSet={(dateInfo) => {
              setCalendarViewInfo({
                view: dateInfo.view.type,
                activeStart: dateInfo.start,
                activeEnd: dateInfo.end,
              })
            }}
          />
        </Box>
      </Paper>
      <CalendarItemModal
        opened={modalOpened}
        onClose={handleModalClose}
        item={selectedItem}
        startDate={selectedDates?.start}
        endDate={selectedDates?.end}
        onSuccessRefetch={refetchCalendarItems}
      />
      <ViewCalendarItemModal
        opened={viewModalOpened}
        onClose={closeViewModal}
        onEdit={handleEditClick}
        onDeleteSuccess={refetchCalendarItems}
        item={selectedItem as CalendarEvent | undefined}
        occurrenceDate={selectedOccurrenceDate}
        categories={categories}
      />
      {propsForDetachModal && projectId && (
        <DetachAndEditOccurrenceModal
          opened={detachModalOpened}
          onClose={closeDetachModal}
          onSuccess={() => {
            closeDetachModal()
            refetchCalendarItems()
          }}
          projectId={projectId}
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
