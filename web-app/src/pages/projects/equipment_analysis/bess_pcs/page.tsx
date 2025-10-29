import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetEquipmentAnalysisBESSPCS } from '@/api/v1/protected/web-application/projects/equipment-analysis/bess_pcs'
import CustomCard from '@/components/CustomCard'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectFilter } from '@/hooks/custom'
import { Stack } from '@mantine/core'
import { useParams } from 'react-router'

const MAX_DAYS = 7

const Page = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.BESS, ProjectTypeId.PV_BESS],
  })

  const { projectId } = useParams<{ projectId: string }>()

  const project = useSelectProject(projectId!)

  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  let startRequest, endRequest
  if (project.data) {
    startRequest = start && start.tz(project.data.time_zone, true).toISOString()
    endRequest = end && end.tz(project.data.time_zone, true).toISOString()
  }

  const data = useGetEquipmentAnalysisBESSPCS({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: startRequest,
      end: endRequest,
    },
    queryOptions: { enabled: !!projectId && !!startRequest && !!endRequest },
  })

  // Project data loading
  if (project.isLoading) {
    return <PageLoader />
  }

  // Project data error
  if (project.error) {
    return <PageError error={project.error} />
  }

  return (
    <Stack p="md" h="100%">
      <AdvancedDatePicker
        includeClearButton={false}
        includeTodayInDateRange
        limits={{
          day: 7,
          week: 1,
          month: 0,
          quarter: 0,
          year: 0,
        }}
        maxDays={MAX_DAYS}
        disableQuickActions
        defaultRange="past-3-days"
      />
      <CustomCard
        title="PCS Power"
        info="Positive values indicate discharging, negative values indicate charging."
        style={{ flex: 1 }}
      >
        <PlotlyPlot
          data={
            data.data &&
            data.data.map((d) => ({
              x: d.x,
              y: d.y,
              name: d.name,
            }))
          }
          layout={{
            yaxis: { title: { text: 'MW' } },
          }}
          isLoading={data.isLoading}
          error={data.error}
        />
      </CustomCard>
    </Stack>
  )
}

export default Page
