import { useGetKPITypes } from '@/api/v1/operational/kpi_types'
import { useGetProjects } from '@/api/v1/operational/projects'
import {
  useScheduleKPIBackfill,
  useTriggerKPIBackfill,
} from '@/api/v1/protected/kpi_backfill'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import {
  Button,
  Card,
  Container,
  Group,
  Modal,
  MultiSelect,
  NumberInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { AxiosError } from 'axios'
import { useMemo, useState } from 'react'

type BackfillAction = 'immediate' | 'schedule'

const pad2 = (value: number) => String(value).padStart(2, '0')

const getDefaultScheduleText = () => {
  const now = new Date()
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(
    now.getDate(),
  )} 23:00`
}

const parseScheduleText = (value: string) => {
  const match = value.trim().match(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})$/)
  if (!match) {
    return null
  }

  const [, year, month, day, hour, minute] = match
  const parsed = new Date(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
    0,
    0,
  )

  if (
    parsed.getFullYear() !== Number(year) ||
    parsed.getMonth() !== Number(month) - 1 ||
    parsed.getDate() !== Number(day) ||
    parsed.getHours() !== Number(hour) ||
    parsed.getMinutes() !== Number(minute)
  ) {
    return null
  }

  return parsed
}

const KPIBackfill = () => {
  const { data: projects, isLoading: isLoadingProjects } = useGetProjects({
    personalPortfolio: false,
  })
  const { data: kpiTypes, isLoading: isLoadingKpis } = useGetKPITypes({})
  const { start, end } = useValidateDateRange({})
  const [selectedProjects, setSelectedProjects] = useState<string[]>([])
  const [selectedKpis, setSelectedKpis] = useState<string[]>([])
  const [backfillDays, setBackfillDays] = useState(0)
  const [daysPerChunk, setDaysPerChunk] = useState(1)
  const [showScheduleModal, setShowScheduleModal] = useState(false)
  const [showAllConfirm, setShowAllConfirm] = useState(false)
  const [pendingAction, setPendingAction] = useState<BackfillAction | null>(
    null,
  )
  const [scheduleText, setScheduleText] = useState(getDefaultScheduleText())

  const projectOptions = useMemo(
    () =>
      (projects ?? [])
        .map((project) => ({
          value: project.name_short,
          label: project.name_long || project.name_short,
        }))
        .sort((a, b) => a.label.localeCompare(b.label)),
    [projects],
  )

  const kpiOptions = useMemo(
    () =>
      (kpiTypes ?? [])
        .map((kpi) => ({
          value: String(kpi.kpi_type_id),
          label: kpi.name_long
            ? `${kpi.kpi_type_id} — ${kpi.name_long}`
            : kpi.name_short,
        }))
        .sort((a, b) => a.label.localeCompare(b.label)),
    [kpiTypes],
  )

  const formattedStart = start?.format('YYYY-MM-DD')
  const formattedEnd = end?.subtract(1, 'day').format('YYYY-MM-DD')

  const { mutateAsync: triggerBackfill, isPending: isSubmittingImmediate } =
    useTriggerKPIBackfill()
  const { mutateAsync: scheduleBackfill, isPending: isSubmittingScheduled } =
    useScheduleKPIBackfill()
  const isSubmitting = isSubmittingImmediate || isSubmittingScheduled

  const disableSubmit =
    !formattedStart || !formattedEnd || backfillDays < 0 || daysPerChunk < 1
  const willRunAllProjects = selectedProjects.length === 0
  const willRunAllKpis = selectedKpis.length === 0

  const getPayload = () => ({
    start: formattedStart!,
    end: formattedEnd!,
    backfill_days: backfillDays,
    days_per_chunk: daysPerChunk,
    project_name_short_list:
      selectedProjects.length > 0 ? selectedProjects : undefined,
    kpi_type_ids:
      selectedKpis.length > 0
        ? selectedKpis.map((id) => Number(id))
        : undefined,
  })

  const getErrorMessage = (error: unknown) => {
    if (error instanceof AxiosError) {
      const detail = error.response?.data?.detail
      if (typeof detail === 'string') {
        return detail
      }
      if (
        Array.isArray(detail) &&
        detail[0] &&
        typeof detail[0].msg === 'string'
      ) {
        return detail[0].msg
      }
      return error.message
    }

    if (error instanceof Error) {
      return error.message
    }

    return 'An unknown error occurred.'
  }

  const submitImmediate = async () => {
    await triggerBackfill(getPayload())
    notifications.show({
      title: 'KPI backfill queued',
      message: 'Lambda accepted the request.',
      color: 'green',
    })
  }

  const submitScheduled = async (scheduledDate: Date) => {
    await scheduleBackfill({
      ...getPayload(),
      scheduled_for: scheduledDate.toISOString(),
    })
    notifications.show({
      title: 'KPI backfill scheduled',
      message: 'Scheduler accepted the request.',
      color: 'green',
    })
  }

  const runAction = async (action: BackfillAction) => {
    try {
      if (action === 'immediate') {
        await submitImmediate()
        return
      }
      setScheduleText(getDefaultScheduleText())
      setShowScheduleModal(true)
    } catch (error) {
      notifications.show({
        title: 'Failed to trigger KPI backfill',
        message: getErrorMessage(error),
        color: 'red',
      })
    }
  }

  const startAction = async (action: BackfillAction) => {
    if (disableSubmit) {
      notifications.show({
        title: 'Missing information',
        message: 'Choose a valid date range to continue.',
        color: 'yellow',
      })
      return
    }

    if (willRunAllProjects || willRunAllKpis) {
      setPendingAction(action)
      setShowAllConfirm(true)
      return
    }

    await runAction(action)
  }

  const handleConfirmAll = async () => {
    const action = pendingAction ?? 'immediate'
    setPendingAction(null)
    setShowAllConfirm(false)
    await runAction(action)
  }

  const handleScheduleSubmit = async () => {
    const parsed = parseScheduleText(scheduleText)
    if (!parsed) {
      notifications.show({
        title: 'Invalid schedule time',
        message: 'Use YYYY-MM-DD HH:MM in your local time.',
        color: 'yellow',
      })
      return
    }

    try {
      await submitScheduled(parsed)
      setShowScheduleModal(false)
    } catch (error) {
      notifications.show({
        title: 'Failed to schedule KPI backfill',
        message: getErrorMessage(error),
        color: 'red',
      })
    }
  }

  return (
    <Container size="md" py="lg">
      <Stack gap="lg">
        <div>
          <Title order={2}>KPI Backfill Utility</Title>
          <Text c="dimmed" size="sm">
            Trigger the KPI backfill lambda for a custom date window, project
            list, and KPI set.
          </Text>
        </div>

        <Card withBorder p="lg">
          <Stack gap="md">
            <Modal
              opened={showAllConfirm}
              onClose={() => {
                setPendingAction(null)
                setShowAllConfirm(false)
              }}
              title="Run across all selections?"
              centered
            >
              <Stack gap="md">
                <Text size="sm">
                  This request will run for all
                  {willRunAllProjects ? ' projects' : ''}
                  {willRunAllProjects && willRunAllKpis ? ' and' : ''}
                  {willRunAllKpis ? ' KPIs' : ''}.
                </Text>
                <Text size="sm">Do you want to proceed?</Text>
                <Group justify="flex-end">
                  <Button
                    variant="default"
                    onClick={() => {
                      setPendingAction(null)
                      setShowAllConfirm(false)
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    color="red"
                    loading={isSubmitting}
                    onClick={handleConfirmAll}
                  >
                    Proceed
                  </Button>
                </Group>
              </Stack>
            </Modal>

            <Modal
              opened={showScheduleModal}
              onClose={() => setShowScheduleModal(false)}
              title="Schedule KPI Backfill"
              centered
            >
              <Stack gap="md">
                <TextInput
                  label="Scheduled time (local)"
                  value={scheduleText}
                  onChange={(event) =>
                    setScheduleText(event.currentTarget.value)
                  }
                  placeholder="YYYY-MM-DD HH:MM"
                  description="Format: YYYY-MM-DD HH:MM (24-hour clock)"
                />
                <Group justify="flex-end">
                  <Button
                    variant="default"
                    onClick={() => setShowScheduleModal(false)}
                  >
                    Cancel
                  </Button>
                  <Button loading={isSubmitting} onClick={handleScheduleSubmit}>
                    Schedule
                  </Button>
                </Group>
              </Stack>
            </Modal>

            <div>
              <Text fw={500} size="sm">
                Date range
              </Text>
              <AdvancedDatePicker
                includeClearButton={false}
                includeTodayInDateRange
                defaultRange="past-week"
                width="100%"
              />
              <Text
                size="sm"
                c={formattedStart && formattedEnd ? 'dimmed' : 'red'}
              >
                {formattedStart && formattedEnd
                  ? `${formattedStart} → ${formattedEnd}`
                  : 'Select a start and end date.'}
              </Text>
            </div>

            <MultiSelect
              label="Projects"
              placeholder={
                isLoadingProjects ? 'Loading projects…' : 'All Projects'
              }
              data={projectOptions}
              value={selectedProjects}
              onChange={setSelectedProjects}
              searchable
              nothingFoundMessage="No projects found"
              maxDropdownHeight={260}
              withCheckIcon
              clearable
            />

            <MultiSelect
              label="KPIs"
              placeholder={isLoadingKpis ? 'Loading KPIs…' : 'All KPIs'}
              data={kpiOptions}
              value={selectedKpis}
              onChange={setSelectedKpis}
              searchable
              nothingFoundMessage="No KPIs found"
              maxDropdownHeight={260}
              withCheckIcon
              clearable
            />

            <Group align="flex-end" gap="md">
              <NumberInput
                label="Backfill days"
                description="Number of days before the start date to backfill."
                value={backfillDays}
                onChange={(value) => setBackfillDays(Number(value) || 0)}
                min={0}
                step={1}
                w="200px"
                clampBehavior="strict"
              />
              <NumberInput
                label="Days per chunk"
                description="How many days each processing chunk should include."
                value={daysPerChunk}
                onChange={(value) => {
                  const parsed = Number(value)
                  setDaysPerChunk(parsed >= 1 ? parsed : 1)
                }}
                min={1}
                step={1}
                w="200px"
                clampBehavior="strict"
              />
            </Group>

            <Group>
              <Button
                onClick={() => void startAction('immediate')}
                disabled={disableSubmit}
                loading={isSubmitting}
              >
                Trigger KPI Backfill Now
              </Button>
              <Button
                variant="light"
                onClick={() => void startAction('schedule')}
                disabled={disableSubmit}
                loading={isSubmitting}
              >
                Schedule KPI Backfill
              </Button>
            </Group>
          </Stack>
        </Card>
      </Stack>
    </Container>
  )
}

export default KPIBackfill
