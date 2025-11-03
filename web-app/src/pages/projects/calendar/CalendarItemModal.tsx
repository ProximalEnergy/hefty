import { useGetCompanyTeams } from '@/api/admin'
import { useGetCompanyUsers } from '@/api/operational'
import {
  CalendarEventCategory,
  useCreateCalendarEvent,
  useDeleteCalendarEvent,
  useGetCalendarEventCategories,
  useUpdateCalendarEvent,
} from '@/api/v1/operational/calendar'
import {
  Button,
  Checkbox,
  ColorSwatch,
  ComboboxItem,
  ComboboxLikeRenderOptionInput,
  Group,
  Modal,
  MultiSelect,
  NumberInput,
  SegmentedControl,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core'
import { DateInput } from '@mantine/dates'
import { UseFormReturnType, useForm } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import { IconUsers } from '@tabler/icons-react'
import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router'
import { ByWeekday, Frequency, Options, RRule, rrulestr } from 'rrule'

interface CalendarItemModalProps {
  opened: boolean
  onClose: () => void
  item?: any
  startDate?: Date
  endDate?: Date
  onSuccessRefetch: () => void
  projectId?: string
  projects?: { project_id: string; name_long: string }[]
}

interface RecurrenceFormValues {
  repeats: 'never' | 'custom'
  frequency?: string
  interval: number
  weekdays: string[]
  monthlyMode?: 'dayOfMonth' | 'dayOfWeek'
  monthDay?: number
  weekOrdinal?: number
  monthWeekday?: string
  endCondition: 'never' | 'on' | 'after'
  endDate?: string
  occurrences?: number
}

interface FormValues extends RecurrenceFormValues {
  title: string
  description: string
  start_time: string
  end_time: string
  all_day: boolean
  calendar_item_category_id: string
  enable_notifications: boolean
  notify_offsets: string[]
  project_id: string
  assignee_user_ids: string[]
  assignee_team_ids: string[]
  assignees_mixed: string[]
}

const frequencyOptions = [
  { value: Frequency.DAILY.toString(), label: 'Days' },
  { value: Frequency.WEEKLY.toString(), label: 'Weeks' },
  { value: Frequency.MONTHLY.toString(), label: 'Months' },
  { value: Frequency.YEARLY.toString(), label: 'Years' },
]

const weekdayOptions = [
  { label: 'Mon', value: '0' },
  { label: 'Tue', value: '1' },
  { label: 'Wed', value: '2' },
  { label: 'Thu', value: '3' },
  { label: 'Fri', value: '4' },
  { label: 'Sat', value: '5' },
  { label: 'Sun', value: '6' },
]

const weekOrdinalOptions = [
  { label: 'First', value: '1' },
  { label: 'Second', value: '2' },
  { label: 'Third', value: '3' },
  { label: 'Fourth', value: '4' },
  { label: 'Last', value: '-1' },
]

const rruleWeekdays: { [key: string]: any } = {
  '0': RRule.MO,
  '1': RRule.TU,
  '2': RRule.WE,
  '3': RRule.TH,
  '4': RRule.FR,
  '5': RRule.SA,
  '6': RRule.SU,
}

const notificationOffsetOptions = [
  { value: '0d', label: 'On the day of the event' },
  { value: '1d', label: '1 day before' },
  { value: '3d', label: '3 days before' },
  { value: '7d', label: '7 days before' },
  { value: '14d', label: '14 days before' },
]

// Helper function to parse RRULE string
const parseRRule = (rruleString?: string): RecurrenceFormValues => {
  const defaultValues: RecurrenceFormValues = {
    repeats: 'never',
    interval: 1,
    weekdays: [],
    monthlyMode: 'dayOfMonth',
    monthDay: new Date().getDate(),
    weekOrdinal: 1,
    monthWeekday: '0',
    endCondition: 'never',
  }

  if (!rruleString || rruleString.trim() === '') {
    return defaultValues
  }

  try {
    const rule = rrulestr(rruleString).options

    const freq = rule.freq
    const interval = rule.interval || 1
    const until = rule.until ? rule.until.toISOString() : undefined
    const count = rule.count

    let weekdays: string[] = []
    let monthlyMode: 'dayOfMonth' | 'dayOfWeek' = defaultValues.monthlyMode!
    let monthDay: number | undefined = defaultValues.monthDay
    let weekOrdinal: number | undefined = defaultValues.weekOrdinal
    let monthWeekday: string | undefined = defaultValues.monthWeekday

    if (freq === Frequency.WEEKLY) {
      weekdays = rule.byweekday?.map((day: any) => day.toString()) || []
    } else if (freq === Frequency.MONTHLY) {
      if (
        rule.bymonthday &&
        rule.bymonthday.length > 0 &&
        (!rule.bysetpos || rule.bysetpos.length === 0)
      ) {
        monthlyMode = 'dayOfMonth'
        monthDay = rule.bymonthday[0]
      } else if (
        rule.byweekday &&
        rule.byweekday.length > 0 &&
        rule.bysetpos &&
        rule.bysetpos.length > 0
      ) {
        monthlyMode = 'dayOfWeek'
        monthWeekday = rule.byweekday[0].toString()
        weekOrdinal = rule.bysetpos[0]
      } else {
        monthDay = new Date(rule.dtstart).getDate()
      }
    }

    let endCondition: 'never' | 'on' | 'after' = 'never'
    if (until) {
      endCondition = 'on'
    } else if (count) {
      endCondition = 'after'
    }

    const parsedResult = {
      repeats: 'custom' as const,
      frequency: freq?.toString(),
      interval,
      weekdays,
      monthlyMode,
      monthDay,
      weekOrdinal,
      monthWeekday,
      endCondition,
      endDate: until,
      occurrences: count ?? undefined,
    }
    return parsedResult
  } catch (e) {
    console.error(
      `[parseRRule] Error during parsing or processing RRULE string: "${rruleString}"`,
      e,
    )
    return defaultValues
  }
}

// Helper function to generate RRULE string
const generateRRule = (values: FormValues): string | undefined => {
  if (values.repeats !== 'custom' || !values.frequency) {
    return undefined
  }

  const freq = parseInt(values.frequency) as Frequency

  const options: Partial<Options> = {
    freq: freq,
    interval: values.interval,
    dtstart: new Date(values.start_time),
  }

  options.byweekday = null
  options.bysetpos = null
  options.bymonthday = null

  if (freq === Frequency.WEEKLY && values.weekdays.length > 0) {
    options.byweekday = values.weekdays.map(
      (dayIndex) => rruleWeekdays[dayIndex],
    ) as ByWeekday[]
  } else if (freq === Frequency.MONTHLY) {
    if (values.monthlyMode === 'dayOfMonth' && values.monthDay) {
      options.bymonthday = [values.monthDay]
    } else if (
      values.monthlyMode === 'dayOfWeek' &&
      values.monthWeekday &&
      values.weekOrdinal
    ) {
      const weekday = rruleWeekdays[values.monthWeekday]
      if (weekday) {
        options.byweekday = [weekday]
        options.bysetpos = [values.weekOrdinal]
      }
    }
  }

  if (values.endCondition === 'on' && values.endDate) {
    const untilDate = new Date(values.endDate)
    const startTime = new Date(values.start_time)
    untilDate.setHours(
      startTime.getHours(),
      startTime.getMinutes(),
      startTime.getSeconds(),
      startTime.getMilliseconds(),
    )
    options.until = new Date(
      Date.UTC(
        untilDate.getFullYear(),
        untilDate.getMonth(),
        untilDate.getDate(),
        untilDate.getHours(),
        untilDate.getMinutes(),
        untilDate.getSeconds(),
        untilDate.getMilliseconds(),
      ),
    )
  } else if (values.endCondition === 'after' && values.occurrences) {
    options.count = values.occurrences
  }

  try {
    if (!options.dtstart) {
      return undefined
    }
    const rule = new RRule(options as any)
    if (options.until && options.until < options.dtstart) {
      return undefined
    }
    return rule.toString()
  } catch (e) {
    console.error('Error generating RRULE string:', e)
    return undefined
  }
}

// Custom renderer for category options
const renderCategoryOption = (
  input: ComboboxLikeRenderOptionInput<ComboboxItem>,
) => {
  const option = input.option as {
    value: string
    label: string
    color_code: string
  }
  if (!option.color_code) {
    return null
  }
  return (
    <Group gap="xs" wrap="nowrap">
      <ColorSwatch
        color={option.color_code || '#868e96'}
        size={10}
        radius="xl"
      />
      <Text
        size="sm"
        style={{ flexGrow: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}
      >
        {option.label}
      </Text>
    </Group>
  )
}

export const CalendarItemModal = ({
  opened,
  onClose,
  item,
  startDate,
  endDate,
  onSuccessRefetch,
  projectId: contextualProjectId,
  projects,
}: CalendarItemModalProps) => {
  const { projectId: projectIdFromUrl } = useParams<{ projectId: string }>()

  const [prevItemId, setPrevItemId] = useState<string | undefined | null>(
    undefined,
  )

  const createCalendarEvent = useCreateCalendarEvent()
  const updateCalendarEvent = useUpdateCalendarEvent()
  const deleteCalendarEvent = useDeleteCalendarEvent()

  const { data: fetchedCategories, isLoading: isLoadingCategories } =
    useGetCalendarEventCategories({
      pathParams: {
        projectId: contextualProjectId || projectIdFromUrl || '',
      },
      queryOptions: {
        enabled: !!(contextualProjectId || projectIdFromUrl),
      },
    })

  const categoryOptionsForSelect = useMemo(() => {
    if (
      isLoadingCategories ||
      !fetchedCategories ||
      fetchedCategories.length === 0
    ) {
      return [
        {
          label: isLoadingCategories
            ? 'Loading categories...'
            : 'No categories available',
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

  // Fetch company users to assign, restricted to current user's company
  const { data: companyUsers } = useGetCompanyUsers({})
  // Maps omitted; names are rendered directly from option labels

  // Fetch company teams
  const { data: teams } = useGetCompanyTeams({})
  // Team map omitted; names are rendered directly from option labels

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

  const form: UseFormReturnType<FormValues> = useForm<FormValues>({
    initialValues: {
      title: '',
      description: '',
      start_time: startDate
        ? startDate.toISOString()
        : new Date().toISOString(),
      end_time: endDate
        ? endDate.toISOString()
        : new Date(
            (startDate || new Date()).getTime() + 60 * 60 * 1000,
          ).toISOString(),
      all_day: false,
      calendar_item_category_id: '',
      repeats: 'never',
      frequency: Frequency.DAILY.toString(),
      interval: 1,
      weekdays: [],
      monthlyMode: 'dayOfMonth',
      monthDay: new Date().getDate(),
      weekOrdinal: 1,
      monthWeekday: '0',
      endCondition: 'never',
      occurrences: 1,
      endDate: undefined,
      enable_notifications: false,
      notify_offsets: [],
      project_id: contextualProjectId || projectIdFromUrl || '',
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
          new Date(value) >= new Date(values.end_time)
        ) {
          return 'Start time must be before end time'
        }
        return null
      },
      end_time: () => {
        return null
      },
      interval: (value) =>
        value > 0 ? null : 'Interval must be greater than 0',
      occurrences: (value, values) =>
        values.repeats === 'custom' && values.endCondition === 'after'
          ? value && value > 0
            ? null
            : 'Occurrences must be greater than 0'
          : null,
      endDate: (value, values) =>
        values.repeats === 'custom' && values.endCondition === 'on'
          ? value
            ? null
            : 'End date is required'
          : null,
      project_id: (value) =>
        !item && projects && !value ? 'Project is required' : null,
    },
  })

  useEffect(() => {
    if (opened) {
      const currentItemId = item ? item.calendar_item_id : null
      const currentRRule = item?.rrule
      const parsedRRuleValues = parseRRule(currentRRule)

      const initialEnableNotifications = !!(
        item?.notify_method?.includes('email') &&
        item?.notify_offsets?.length > 0
      )
      const initialNotifyOffsets = initialEnableNotifications
        ? item.notify_offsets
        : []

      form.setValues({
        title: item?.title || '',
        description: item?.description || '',
        start_time:
          item?.start_time ||
          startDate?.toISOString() ||
          new Date().toISOString(),
        end_time:
          item?.end_time || endDate?.toISOString() || new Date().toISOString(),
        all_day: true,
        calendar_item_category_id: item?.calendar_item_category_id || '',
        ...parsedRRuleValues,
        enable_notifications: initialEnableNotifications,
        notify_offsets: initialNotifyOffsets,
        project_id:
          item?.project_id || contextualProjectId || projectIdFromUrl || '',
        assignee_user_ids: item?.assignee_user_ids || [],
        assignee_team_ids: item?.assignee_team_ids || [],
        assignees_mixed: [
          ...(item?.assignee_user_ids || []).map((id: string) => `user:${id}`),
          ...(item?.assignee_team_ids || []).map((id: string) => `team:${id}`),
        ],
      })
      setPrevItemId(currentItemId)
    } else {
      const defaultStartTime = startDate
        ? startDate.toISOString()
        : new Date().toISOString()
      const defaultEndTime = endDate
        ? endDate.toISOString()
        : new Date(
            (startDate || new Date()).getTime() + 60 * 60 * 1000,
          ).toISOString()
      const initialAllDay = startDate
        ? startDate.toISOString().split('T')[1] === '00:00:00.000Z' && endDate
          ? endDate.toISOString().split('T')[1] === '00:00:00.000Z' &&
            (endDate.getTime() - startDate.getTime()) %
              (24 * 60 * 60 * 1000) ===
              0
          : false
        : false
      form.setValues({
        title: '',
        description: '',
        start_time: defaultStartTime,
        end_time: defaultEndTime,
        all_day: initialAllDay,
        calendar_item_category_id: '',
        repeats: 'never',
        frequency: Frequency.DAILY.toString(),
        interval: 1,
        weekdays: [],
        monthlyMode: 'dayOfMonth',
        monthDay: new Date(defaultStartTime).getDate(),
        weekOrdinal: 1,
        monthWeekday: '0',
        endCondition: 'never',
        occurrences: 1,
        endDate: undefined,
        enable_notifications: false,
        notify_offsets: [],
        project_id: contextualProjectId || projectIdFromUrl || '',
        assignee_user_ids: [],
        assignee_team_ids: [],
        assignees_mixed: [],
      })
      setPrevItemId(undefined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    opened,
    item,
    startDate,
    endDate,
    form.setValues,
    categoryOptionsForSelect,
  ])

  useEffect(() => {
    if (
      !opened ||
      isLoadingCategories ||
      !fetchedCategories ||
      fetchedCategories.length === 0 ||
      !contextualProjectId
    ) {
      return
    }

    let targetCategoryId: string | undefined = undefined

    const currentContextItemId = item ? item.calendar_item_id : null

    if (item) {
      let matchedCategory: CalendarEventCategory | undefined
      if (item.color) {
        matchedCategory = fetchedCategories.find(
          (cat) => cat.color_code === item.color,
        )
      }
      if (
        !matchedCategory &&
        item.category &&
        typeof item.category === 'string'
      ) {
        matchedCategory = fetchedCategories.find(
          (cat) =>
            cat.short_name.toUpperCase() ===
              (item.category as string).toUpperCase() ||
            cat.long_name.toUpperCase() ===
              (item.category as string).toUpperCase(),
        )
      }

      if (matchedCategory) {
        targetCategoryId = matchedCategory.category_id
      } else {
        targetCategoryId = fetchedCategories[0]?.category_id
      }
    }

    if (targetCategoryId) {
      const currentCategoryId = form.values.calendar_item_category_id
      if (
        prevItemId === currentContextItemId &&
        (currentCategoryId === '' || currentCategoryId === undefined)
      ) {
        form.setFieldValue('calendar_item_category_id', targetCategoryId)
      } else if (prevItemId !== currentContextItemId && opened) {
        form.setFieldValue('calendar_item_category_id', targetCategoryId)
      }
    }
  }, [
    opened,
    isLoadingCategories,
    fetchedCategories,
    item,
    contextualProjectId,
    form.setFieldValue,
    prevItemId,
  ])

  // Handle form field changes that need side effects
  const handleFrequencyChange = (value: string) => {
    form.setFieldValue('frequency', value)

    if (value !== Frequency.WEEKLY.toString()) {
      form.setFieldValue('weekdays', [])
    }
    if (value !== Frequency.MONTHLY.toString()) {
      form.setFieldValue('monthlyMode', undefined)
      form.setFieldValue('monthDay', undefined)
      form.setFieldValue('weekOrdinal', undefined)
      form.setFieldValue('monthWeekday', undefined)
    }
  }

  const handleEndConditionChange = (value: 'never' | 'on' | 'after') => {
    form.setFieldValue('endCondition', value)

    if (value === 'never') {
      form.setFieldValue('endDate', undefined)
      form.setFieldValue('occurrences', undefined)
    } else if (value === 'on') {
      form.setFieldValue('occurrences', undefined)
      if (!form.values.endDate) {
        const nextDay = new Date(form.values.start_time)
        nextDay.setDate(nextDay.getDate() + 1)
        form.setFieldValue('endDate', nextDay.toISOString())
      }
    } else if (value === 'after') {
      form.setFieldValue('endDate', undefined)
      if (!form.values.occurrences) {
        form.setFieldValue('occurrences', 1)
      }
    }
  }

  const handleStartTimeChange = (value: string) => {
    form.setFieldValue('start_time', value)
    form.setFieldValue('end_time', value)
  }

  // Handle weekly frequency selection - set default weekday
  const handleWeeklyFrequencySelection = () => {
    if (form.values.frequency === Frequency.WEEKLY.toString()) {
      const hasSelection = (form.values.weekdays || []).length > 0
      if (!hasSelection && !item) {
        const start = new Date(form.values.start_time)
        // Map JS Sunday(0)..Saturday(6) -> our Mon(0)..Sun(6)
        const mondayIndexed = ((start.getUTCDay() + 6) % 7).toString()
        form.setFieldValue('weekdays', [mondayIndexed])
      }
    }
  }

  const handleSubmit = async (values: FormValues) => {
    const finalProjectId = item?.project_id || values.project_id
    if (!finalProjectId) {
      console.error('No project ID provided for calendar item submission.')
      notifications.show({
        title: 'Error',
        message: 'Project ID not found. Cannot save calendar item.',
        color: 'red',
      })
      return
    }

    const rruleString = generateRRule(values)

    const selectedCategoryObject = fetchedCategories?.find(
      (cat) => cat.category_id === values.calendar_item_category_id,
    )
    const itemColorForSubmission =
      selectedCategoryObject?.color_code || item?.color || '#868e96'

    const eventDataForApi = {
      title: values.title,
      description: values.description || undefined,
      start_time: values.start_time,
      end_time: values.all_day
        ? new Date(
            new Date(values.start_time).setDate(
              new Date(values.start_time).getDate() + 1,
            ),
          )
            .toISOString()
            .split('T')[0] + 'T00:00:00.000Z'
        : values.end_time,
      all_day: values.all_day,
      calendar_item_category_id: values.calendar_item_category_id,
      rrule: rruleString,
      color: itemColorForSubmission,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone, // Default to user's browser timezone
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

    try {
      if (item && item.calendar_item_id) {
        // We are editing an existing item.
        await updateCalendarEvent.mutateAsync({
          projectId: finalProjectId,
          calendarItemId: item.calendar_item_id,
          event: eventDataForApi,
        })
      } else {
        // Whether it was an edit (original now deleted) or a new item, create it.
        await createCalendarEvent.mutateAsync({
          projectId: finalProjectId,
          event: eventDataForApi,
        })
      }

      notifications.show({
        title: 'Success',
        message: `Calendar item has been ${
          item ? 'updated' : 'created'
        } successfully.`,
        color: 'green',
      })

      onClose()
      onSuccessRefetch()
    } catch (error) {
      console.error('Failed to save calendar item:', error)
      notifications.show({
        title: 'Error',
        message: 'Failed to save calendar item. Please try again.',
        color: 'red',
      })
    }
  }

  const handleDelete = async () => {
    if (item && item.calendar_item_id) {
      try {
        await deleteCalendarEvent.mutateAsync({
          projectId: item.project_id,
          eventId: item.calendar_item_id,
        })
        notifications.show({
          title: 'Success',
          message: 'Calendar item deleted successfully.',
          color: 'green',
        })
        onClose()
        onSuccessRefetch()
      } catch (error) {
        console.error('Failed to delete calendar item:', error)
        notifications.show({
          title: 'Error',
          message: 'Failed to delete calendar item. Please try again.',
          color: 'red',
        })
      }
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={item ? 'Edit Item' : 'Create Item'}
      size="lg"
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack>
          <Group justify="space-between">
            <Title order={3}>Event Details</Title>
            {item && (
              <Button
                variant="subtle"
                color="red"
                onClick={handleDelete}
                loading={deleteCalendarEvent.isPending}
              >
                Delete Event
              </Button>
            )}
          </Group>

          {!item && projects && (
            <Select
              label="Project"
              placeholder="Select a project"
              data={projects.map((p) => ({
                value: p.project_id,
                label: p.name_long,
              }))}
              {...form.getInputProps('project_id')}
              required
              searchable
            />
          )}

          <TextInput
            label="Title"
            placeholder="e.g., Scheduled Maintenance"
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
          />
          <DateInput
            label="Date"
            placeholder="Select date"
            required
            value={
              new Date(form.values.start_time.substring(0, 10) + 'T00:00:00')
            }
            onChange={(date) => {
              if (date) {
                const newStartTime = new Date(
                  Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()),
                ).toISOString()
                handleStartTimeChange(newStartTime)
              }
            }}
          />

          <SegmentedControl
            data={[
              { label: 'Does not repeat', value: 'never' },
              { label: 'Repeats...', value: 'custom' },
            ]}
            {...form.getInputProps('repeats')}
          />

          {form.values.repeats === 'custom' && (
            <Stack gap="sm">
              <Group grow>
                <NumberInput
                  label="Repeat every"
                  min={1}
                  step={1}
                  {...form.getInputProps('interval')}
                />
                <Select
                  label="Frequency"
                  data={frequencyOptions}
                  value={form.values.frequency}
                  onChange={(value) => {
                    if (value) {
                      handleFrequencyChange(value)
                      handleWeeklyFrequencySelection()
                    }
                  }}
                />
              </Group>

              {form.values.frequency === Frequency.WEEKLY.toString() && (
                <Checkbox.Group
                  label="Repeat on"
                  {...form.getInputProps('weekdays')}
                >
                  <Group mt="xs">
                    {weekdayOptions.map((day) => (
                      <Checkbox
                        key={day.value}
                        label={day.label}
                        value={day.value}
                      />
                    ))}
                  </Group>
                </Checkbox.Group>
              )}

              {form.values.frequency === Frequency.MONTHLY.toString() && (
                <Stack gap="xs">
                  <SegmentedControl
                    data={[
                      { label: 'On day of month', value: 'dayOfMonth' },
                      { label: 'On the', value: 'dayOfWeek' },
                    ]}
                    {...form.getInputProps('monthlyMode')}
                    fullWidth
                  />
                  {form.values.monthlyMode === 'dayOfMonth' && (
                    <NumberInput
                      label="Day of Month"
                      placeholder="Enter day (1-31)"
                      min={1}
                      max={31}
                      step={1}
                      {...form.getInputProps('monthDay')}
                    />
                  )}
                  {form.values.monthlyMode === 'dayOfWeek' && (
                    <Group grow>
                      <Select
                        label="Ordinal"
                        data={weekOrdinalOptions}
                        {...form.getInputProps('weekOrdinal')}
                        onChange={(value) =>
                          form.setFieldValue(
                            'weekOrdinal',
                            parseInt(value || '1'),
                          )
                        }
                      />
                      <Select
                        label="Day of Week"
                        data={weekdayOptions}
                        {...form.getInputProps('monthWeekday')}
                      />
                    </Group>
                  )}
                </Stack>
              )}

              <Stack gap={2}>
                <Text size="sm" fw={500}>
                  Ends
                </Text>
                <SegmentedControl
                  data={[
                    { label: 'Never', value: 'never' },
                    { label: 'On', value: 'on' },
                    { label: 'After', value: 'after' },
                  ]}
                  value={form.values.endCondition}
                  onChange={(value) => {
                    if (value) {
                      handleEndConditionChange(
                        value as 'never' | 'on' | 'after',
                      )
                    }
                  }}
                />
              </Stack>

              {form.values.endCondition === 'on' && (
                <DateInput
                  label="End Date"
                  placeholder="Select end date"
                  required
                  value={
                    form.values.endDate ? new Date(form.values.endDate) : null
                  }
                  onChange={(date) =>
                    form.setFieldValue('endDate', date?.toISOString())
                  }
                />
              )}

              {form.values.endCondition === 'after' && (
                <NumberInput
                  label="Occurrences"
                  placeholder="Number of occurrences"
                  required
                  min={1}
                  step={1}
                  {...form.getInputProps('occurrences')}
                />
              )}
            </Stack>
          )}

          <Checkbox
            label="Send email reminder"
            {...form.getInputProps('enable_notifications', {
              type: 'checkbox',
            })}
            mt="md"
          />
          {form.values.enable_notifications && (
            <MultiSelect
              label="Notify me before event"
              placeholder="Select reminder times"
              data={notificationOffsetOptions}
              {...form.getInputProps('notify_offsets')}
              mt="xs"
              comboboxProps={{ withinPortal: true }}
            />
          )}

          <MultiSelect
            label="Assign to users or teams"
            placeholder="Select assignees"
            data={combinedAssigneeOptions as any}
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
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              loading={
                createCalendarEvent.isPending || updateCalendarEvent.isPending
              }
            >
              {item ? 'Update' : 'Create'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  )
}
