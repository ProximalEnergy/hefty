import { useGetCompanyTeams } from '@/api/admin'
import { useGetSelfCompanyUsers } from '@/api/v1/admin/users'
import {
  CalendarEvent,
  CalendarEventCategory,
  useCalendarOccurrenceAction,
  useCreateCalendarEvent,
  useGetCalendarEventCategories,
} from '@/api/v1/operational/calendar'
// Use DateTimePicker for start/end
import {
  Button,
  Checkbox,
  ColorSwatch,
  ComboboxItem,
  ComboboxLikeRenderOptionInput,
  Group,
  Modal,
  MultiSelect,
  // If you allow changing notify_offsets
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core'
import { DateInput, DateTimePicker } from '@mantine/dates'
import { UseFormReturnType, useForm } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import { IconUsers } from '@tabler/icons-react'
import { useEffect, useMemo } from 'react'

// Note: Recurrence (rrule) related imports and logic will be mostly removed or disabled

// For notification offsets if you choose to include them
const notificationOffsetOptions = [
  { value: '0d', label: 'On the day of the event' },
  { value: '1d', label: '1 day before' },
  { value: '3d', label: '3 days before' },
  { value: '7d', label: '7 days before' },
  { value: '14d', label: '14 days before' },
]

// Helper to create a 'local' Date object from a UTC ISO string for display purposes.
// The picker will show the time as if it were local, but we treat it as UTC.
const utcToLocalDate = (utcIsoString: string): Date => {
  const date = new Date(utcIsoString)
  return new Date(
    date.getUTCFullYear(),
    date.getUTCMonth(),
    date.getUTCDate(),
    date.getUTCHours(),
    date.getUTCMinutes(),
    date.getUTCSeconds(),
  )
}

// Helper to convert a 'local' Date object from the picker back to a UTC ISO string for the API.
const localDateToUtcIsoString = (localDate: Date): string => {
  return new Date(
    Date.UTC(
      localDate.getFullYear(),
      localDate.getMonth(),
      localDate.getDate(),
      localDate.getHours(),
      localDate.getMinutes(),
      localDate.getSeconds(),
    ),
  ).toISOString()
}

interface DetachAndEditOccurrenceModalProps {
  opened: boolean
  onClose: () => void
  onSuccess: () => void // To refetch events and close
  projectId: string
  originalSeriesItem: CalendarEvent // The master series data
  occurrenceOriginalStartTime: string // ISO string of the specific occurrence's original start time
  occurrenceOriginalEndTime: string // ISO string of the specific occurrence's original end time
}

// Form values will be for a new, non-recurring event
interface FormValues {
  title: string
  description: string
  start_time: Date | null // Changed to Date | null
  end_time: Date | null // Changed to Date | null
  all_day: boolean
  calendar_item_category_id: string
  enable_notifications: boolean
  notify_offsets: string[]
  assignee_user_ids: string[]
  assignee_team_ids: string[]
  assignees_mixed: string[]
}

const renderCategoryOption = (
  input: ComboboxLikeRenderOptionInput<ComboboxItem>,
) => {
  const option = input.option as ComboboxItem & { color_code: string }
  return (
    <Group>
      <ColorSwatch color={option.color_code || 'transparent'} size={14} />
      <Text>{option.label}</Text>
    </Group>
  )
}

export const DetachAndEditOccurrenceModal = ({
  opened,
  onClose,
  onSuccess,
  projectId,
  originalSeriesItem,
  occurrenceOriginalStartTime,
  occurrenceOriginalEndTime,
}: DetachAndEditOccurrenceModalProps) => {
  const cancelOccurrenceAction = useCalendarOccurrenceAction()
  const createStandaloneEvent = useCreateCalendarEvent()

  const { data: fetchedCategories, isLoading: isLoadingCategories } =
    useGetCalendarEventCategories({
      pathParams: { projectId },
      queryOptions: { enabled: !!projectId && opened },
    })

  // Company users for assignment
  const { data: companyUsers } = useGetSelfCompanyUsers({})

  // Fetch company teams
  const { data: teams } = useGetCompanyTeams({})

  const combinedAssigneeOptions = useMemo(() => {
    const userOpts = (companyUsers || []).map((u) => ({
      value: `user:${u.user_id}`,
      label: u.name_long,
      kind: 'user' as const,
    }))
    const teamOpts = (teams || []).map((t) => ({
      value: `team:${t.team_id}`,
      label: t.name_long,
      kind: 'team' as const,
    }))
    return [...teamOpts, ...userOpts]
  }, [companyUsers, teams])

  const renderAssigneeOption = (
    input: ComboboxLikeRenderOptionInput<ComboboxItem>,
  ) => {
    const option = input.option as ComboboxItem & { kind?: 'user' | 'team' }
    const isTeam = option.kind === 'team'
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

  const categoryOptionsForSelect = useMemo(() => {
    if (
      isLoadingCategories ||
      !fetchedCategories ||
      fetchedCategories.length === 0
    ) {
      return [
        {
          label: isLoadingCategories ? 'Loading...' : 'No categories',
          value: '',
          color_code: 'transparent',
        },
      ]
    }
    return fetchedCategories.map((cat: CalendarEventCategory) => ({
      label: cat.long_name,
      value: cat.category_id,
      color_code: cat.color_code,
    }))
  }, [fetchedCategories, isLoadingCategories])

  const form: UseFormReturnType<FormValues> = useForm<FormValues>({
    initialValues: {
      title: '',
      description: '',
      start_time: new Date(), // Changed to new Date()
      end_time: new Date(new Date().getTime() + 60 * 60 * 1000), // Default +1 hour, as Date
      all_day: false,
      calendar_item_category_id: '',
      enable_notifications: false,
      notify_offsets: [],
      assignee_user_ids: [],
      assignee_team_ids: [],
      assignees_mixed: [],
    },
    validate: {
      title: (value) => (value.trim().length > 0 ? null : 'Title is required'),
      calendar_item_category_id: (value) =>
        value ? null : 'Category is required',
      start_time: (value, values) => {
        if (!value) return 'Start time is required'
        if (
          !values.all_day &&
          values.end_time &&
          value.getTime() >= values.end_time.getTime() // Compare Date objects
        ) {
          return 'Start time must be before end time'
        }
        return null
      },
      end_time: (value, values) => {
        if (!values.all_day && !value) return 'End time is required'
        // Additional validation if needed: ensure end_time is a Date if not all_day
        if (!values.all_day && value && !(value instanceof Date))
          return 'Invalid end time'
        return null
      },
    },
  })

  useEffect(() => {
    if (opened && originalSeriesItem && occurrenceOriginalStartTime) {
      const initialStartTime = utcToLocalDate(occurrenceOriginalStartTime)
      const initialEndTime = occurrenceOriginalEndTime
        ? utcToLocalDate(occurrenceOriginalEndTime)
        : new Date(initialStartTime.getTime() + 60 * 60 * 1000) // Already Date objects

      form.setValues({
        title: originalSeriesItem.title,
        description: originalSeriesItem.description || '',
        start_time: initialStartTime, // Set as Date
        end_time: initialEndTime, // Set as Date
        all_day: originalSeriesItem.all_day,
        calendar_item_category_id: originalSeriesItem.calendar_item_category_id,
        enable_notifications: !!(
          originalSeriesItem.notify_method?.includes('email') &&
          originalSeriesItem.notify_offsets?.length
        ),
        notify_offsets: originalSeriesItem.notify_offsets || [],
        assignee_user_ids: originalSeriesItem.assignee_user_ids || [],
        assignee_team_ids: originalSeriesItem.assignee_team_ids || [],
        assignees_mixed: [
          ...(originalSeriesItem.assignee_user_ids || []).map(
            (id) => `user:${id}`,
          ),
          ...(originalSeriesItem.assignee_team_ids || []).map(
            (id) => `team:${id}`,
          ),
        ],
      })
    } else if (!opened) {
      form.reset()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    opened,
    originalSeriesItem,
    occurrenceOriginalStartTime,
    occurrenceOriginalEndTime,
    // form.setValues should not be a dependency, but form itself if its identity changes
  ])

  const handleSubmit = async (values: FormValues) => {
    // Ensure start_time and end_time are valid Date objects before calling toISOString
    // Validation should catch nulls for non-all-day events.
    if (!values.start_time) {
      notifications.show({
        title: 'Error',
        message: 'Start time is missing.',
        color: 'red',
      })
      return
    }
    if (!values.all_day && !values.end_time) {
      notifications.show({
        title: 'Error',
        message: 'End time is missing for timed event.',
        color: 'red',
      })
      return
    }

    const originalOccurrenceDate = new Date(occurrenceOriginalStartTime)
      .toISOString()
      .split('T')[0]

    try {
      // Step 1: Cancel the original occurrence
      await cancelOccurrenceAction.mutateAsync({
        projectId,
        calendarItemId: originalSeriesItem.calendar_item_id,
        exceptionDate: originalOccurrenceDate,
        payload: { is_cancelled: true },
      })

      // Step 2: Create the new standalone event
      const selectedCategoryObject = fetchedCategories?.find(
        (cat) => cat.category_id === values.calendar_item_category_id,
      )
      const itemColorForSubmission =
        selectedCategoryObject?.color_code ||
        originalSeriesItem.color ||
        '#868e96'

      const eventDataForApi = {
        title: values.title,
        description: values.description || undefined,
        start_time: localDateToUtcIsoString(values.start_time), // Convert Date to ISO string
        end_time: values.all_day
          ? (() => {
              const nextDay = new Date(values.start_time as Date)
              nextDay.setDate(nextDay.getDate() + 1)
              const nextDayIso = localDateToUtcIsoString(nextDay)
              return nextDayIso.split('T')[0] + 'T00:00:00.000Z'
            })()
          : localDateToUtcIsoString(values.end_time as Date), // Convert Date to ISO string
        all_day: values.all_day,
        calendar_item_category_id: values.calendar_item_category_id,
        rrule: undefined, // Explicitly no rrule for the new standalone event
        color: itemColorForSubmission,
        timezone: originalSeriesItem.timezone || 'UTC',
        notify_method:
          values.enable_notifications && values.notify_offsets.length > 0
            ? ['email']
            : undefined,
        notify_offsets:
          values.enable_notifications && values.notify_offsets.length > 0
            ? values.notify_offsets
            : undefined,
        assignee_user_ids: values.assignee_user_ids?.length
          ? values.assignee_user_ids
          : undefined,
        assignee_team_ids: values.assignee_team_ids?.length
          ? values.assignee_team_ids
          : undefined,
      }

      await createStandaloneEvent.mutateAsync({
        projectId,
        event: eventDataForApi,
      })

      notifications.show({
        title: 'Success',
        message: 'Occurrence saved.',
        color: 'green',
      })
      onSuccess() // Close modal and refetch all events
    } catch (error) {
      console.error('Error detaching and editing occurrence:', error)
      notifications.show({
        title: 'Error',
        message:
          'Failed to detach and create new event. The original occurrence might have been cancelled. Please check and try creating a new event manually if needed.',
        color: 'red',
        autoClose: 7000,
      })
      // Optionally, you might want to refetch here too, to see the (potentially only) cancelled state
      // onSuccess();
    }
  }

  const isLoading =
    cancelOccurrenceAction.isPending ||
    createStandaloneEvent.isPending ||
    isLoadingCategories

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={`Edit Occurrence: ${originalSeriesItem?.title || ''}`}
      size="lg" // Potentially larger like CalendarItemModal
      centered
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack>
          <TextInput
            label="Title"
            placeholder="Enter item title"
            required
            {...form.getInputProps('title')}
          />
          <Select
            label="Category"
            data={categoryOptionsForSelect}
            required
            disabled={
              isLoadingCategories ||
              !fetchedCategories ||
              fetchedCategories.length === 0
            }
            renderOption={renderCategoryOption}
            {...form.getInputProps('calendar_item_category_id')}
          />
          <Textarea
            label="Description"
            placeholder="Enter item description"
            {...form.getInputProps('description')}
            minRows={3}
          />
          {/* <Checkbox
            label="All-day event"
            {...form.getInputProps('all_day', { type: 'checkbox' })}
            mt="xs"
          /> */}

          {!form.values.all_day ? (
            <Group grow>
              <DateTimePicker
                label="Start Time"
                placeholder="Pick date and time"
                required
                valueFormat="DD MMM YYYY hh:mm A"
                {...form.getInputProps('start_time')}
                onChange={(date) =>
                  form.setFieldValue(
                    'start_time',
                    date, // Set as Date or null
                  )
                }
              />
              <DateTimePicker
                label="End Time"
                placeholder="Pick date and time"
                required
                valueFormat="DD MMM YYYY hh:mm A"
                {...form.getInputProps('end_time')}
                onChange={
                  (date) => form.setFieldValue('end_time', date) // Set as Date or null
                }
              />
            </Group>
          ) : (
            <DateInput
              label="Date"
              placeholder="Pick date"
              required
              {...form.getInputProps('start_time')} // For all-day, start_time holds the date
              onChange={(date) => {
                form.setFieldValue('start_time', date) // Set as Date or null
                // For all-day, you might want end_time to also reflect this date, possibly end of day or exclusive next day
                if (date) {
                  const endDateForAllDay = new Date(date)
                  // Example: make end_time the start of the next day for FullCalendar compatibility if it's exclusive
                  // Or, set it to end of selected day if your backend/FC interprets it inclusively
                  endDateForAllDay.setDate(date.getDate() + 1) // FC interprets exclusive end for all-day
                  endDateForAllDay.setHours(0, 0, 0, 0)
                  form.setFieldValue('end_time', endDateForAllDay) // Set as Date
                } else {
                  form.setFieldValue('end_time', null) // Set as null
                }
              }}
            />
          )}

          {/* Recurrence section is intentionally omitted as this becomes a non-recurring event */}

          <Checkbox
            label="Enable Email Reminders"
            {...form.getInputProps('enable_notifications', {
              type: 'checkbox',
            })}
            mt="md"
          />
          {form.values.enable_notifications && (
            <MultiSelect
              label="Remind Me"
              data={notificationOffsetOptions}
              placeholder="Select reminder times"
              {...form.getInputProps('notify_offsets')}
              comboboxProps={{ shadow: 'md' }}
            />
          )}

          <MultiSelect
            label="Assign to users or teams"
            placeholder="Select assignees"
            data={combinedAssigneeOptions as ComboboxItem[]}
            searchable
            clearable
            renderOption={renderAssigneeOption}
            {...form.getInputProps('assignees_mixed')}
            onChange={(vals) => {
              form.setFieldValue('assignees_mixed', vals)
              const userIds = vals
                .filter((v) => v.startsWith('user:'))
                .map((v) => v.split(':')[1])
              const teamIds = vals
                .filter((v) => v.startsWith('team:'))
                .map((v) => v.split(':')[1])
              form.setFieldValue('assignee_user_ids', userIds)
              form.setFieldValue('assignee_team_ids', teamIds)
            }}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button type="submit" loading={isLoading}>
              Save
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  )
}
