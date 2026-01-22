import { useGetKPITypes } from '@/api/v1/operational/kpi_types'
import { useGetProjects } from '@/api/v1/operational/projects'
import { useTriggerKPIBackfill } from '@/api/v1/protected/kpi_backfill'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import {
  Button,
  Card,
  Container,
  Group,
  MultiSelect,
  NumberInput,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMemo, useState } from 'react'

const KPIBackfill = () => {
  const { data: projects, isLoading: isLoadingProjects } = useGetProjects({
    personalPortfolio: false,
  })
  const { data: kpiTypes, isLoading: isLoadingKpis } = useGetKPITypes({})
  const { start, end } = useValidateDateRange({})
  const [selectedProjects, setSelectedProjects] = useState<string[]>([])
  const [selectedKpis, setSelectedKpis] = useState<string[]>([])
  const [backfillDays, setBackfillDays] = useState(0)

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

  const { mutateAsync: triggerBackfill, isPending: isSubmitting } =
    useTriggerKPIBackfill()

  const disableSubmit =
    !formattedStart ||
    !formattedEnd ||
    selectedProjects.length === 0 ||
    selectedKpis.length === 0 ||
    backfillDays < 0

  const handleSubmit = async () => {
    if (disableSubmit) {
      notifications.show({
        title: 'Missing information',
        message:
          'Choose a date range plus at least one project and KPI to continue.',
        color: 'yellow',
      })
      return
    }

    try {
      await triggerBackfill({
        start: formattedStart!,
        end: formattedEnd!,
        backfill_days: backfillDays,
        project_name_short_list: selectedProjects,
        kpi_type_ids: selectedKpis.map((id) => Number(id)),
      })
      notifications.show({
        title: 'KPI backfill queued',
        message: 'Lambda accepted the request.',
        color: 'green',
      })
    } catch (error) {
      notifications.show({
        title: 'Failed to trigger KPI backfill',
        message:
          error instanceof Error ? error.message : 'An unknown error occurred.',
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
                isLoadingProjects ? 'Loading projects…' : 'Search projects'
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
              placeholder={isLoadingKpis ? 'Loading KPIs…' : 'Search KPIs'}
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
            </Group>

            <Button
              onClick={handleSubmit}
              disabled={disableSubmit}
              loading={isSubmitting}
            >
              Trigger KPI backfill
            </Button>
          </Stack>
        </Card>
      </Stack>
    </Container>
  )
}

export default KPIBackfill
