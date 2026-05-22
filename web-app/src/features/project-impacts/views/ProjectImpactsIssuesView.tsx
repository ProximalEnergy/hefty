import { PageError } from '@/components/Error'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import {
  Group,
  LoadingOverlay,
  MultiSelect,
  Stack,
  Switch,
} from '@mantine/core'
import { ProjectImpactsDeviceMultiSelect } from '@/features/project-impacts/components/ProjectImpactsDeviceMultiSelect'
import { ProjectImpactsIssuesTable } from '@/features/project-impacts/components/ProjectImpactsIssuesTable'
import { useProjectImpactsIssuesViewModel } from '@/features/project-impacts/hooks/use-project-impacts-issues-view-model'
import type { ProjectImpactsContext } from '@/features/project-impacts/types/project-impacts-types'

type ProjectImpactsIssuesViewProps = {
  context: ProjectImpactsContext
}

export function ProjectImpactsIssuesView({
  context,
}: ProjectImpactsIssuesViewProps) {
  const viewModel = useProjectImpactsIssuesViewModel({ context })

  if (viewModel.issuesError !== null) {
    return <PageError text="Error loading project issues data" />
  }

  return (
    <Stack h="100%" pt="md">
      <Group justify="space-between">
        <Switch
          checked={viewModel.includeClosedIssues}
          onChange={(event) =>
            viewModel.setClosedIssuesState({
              rangeKey: viewModel.selectedDateRangeKey,
              value: event.currentTarget.checked,
            })
          }
          label="Include Closed Issues"
        />
        <Group>
          <AdvancedDatePicker
            defaultRange="today"
            includeClearButton={false}
            includeIncrementButtons={false}
            includeTodayInDateRange={true}
          />
          <MultiSelect
            data={viewModel.deviceTypeOptions}
            disabled={viewModel.isLoading}
            placeholder={
              viewModel.selectedDeviceTypes.length === 0
                ? 'Select device types...'
                : undefined
            }
            value={viewModel.selectedDeviceTypes}
            onChange={viewModel.setSelectedDeviceTypes}
            clearable
          />
          <ProjectImpactsDeviceMultiSelect
            unique_devices={viewModel.issueDevices.data?.unique_devices ?? []}
            selected_devices={viewModel.selectedDevices}
            onChange={viewModel.setSelectedDevices}
          />
        </Group>
      </Group>
      {viewModel.isLoading ? (
        <div style={{ position: 'relative', height: '100%', width: '100%' }}>
          <LoadingOverlay visible={true} />
        </div>
      ) : (
        <ProjectImpactsIssuesTable
          data={viewModel.filteredIssueRows}
          projectId={viewModel.projectId}
          timeZone={viewModel.timeZone}
        />
      )}
    </Stack>
  )
}
