import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useGetProject } from '@/api/v1/operational/projects'
import { useGetEquipmentAnalysisBESS } from '@/api/v1/protected/web-application/projects/equipment-analysis/bess'
import CustomCard from '@/components/CustomCard'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectFilter } from '@/hooks/custom'
import { Stack } from '@mantine/core'
import { useParams } from 'react-router-dom'

const MAX_DAYS = 7

const Page = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.BESS, ProjectTypeId.PV_BESS],
  })

  const { projectId } = useParams()

  const project = useGetProject({
    pathParams: { projectId: projectId || '-1' },
  })

  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  let startRequest, endRequest
  if (project.data) {
    startRequest = start && start.tz(project.data.time_zone, true).toISOString()
    endRequest = end && end.tz(project.data.time_zone, true).toISOString()
  }

  const data = useGetEquipmentAnalysisBESS({
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
      {project.data?.has_bess_enclosures && (
        <CustomCard title="BESS DC Enclosure" style={{ flex: 1 }}>
          <PlotlyPlot
            data={
              data.data?.bess_enclosure &&
              data.data.bess_enclosure.map((d) => ({
                x: d.x,
                y: d.y,
                name: d.name,
              }))
            }
            layout={{
              yaxis: {
                title: 'SOC (%)',
                tickformat: ',.0%',
                range: [0, 1],
              },
            }}
            isLoading={data.isLoading}
            error={data.error}
          />
        </CustomCard>
      )}

      {project.data?.has_bess_banks && (
        <CustomCard title="BESS Bank" style={{ flex: 1 }}>
          <PlotlyPlot
            data={
              data.data?.bess_bank &&
              data.data.bess_bank.map((d) => ({
                x: d.x,
                y: d.y,
                name: d.name,
              }))
            }
            layout={{
              yaxis: {
                title: 'SOC (%)',
                tickformat: ',.0%',
                range: [0, 1],
              },
            }}
            isLoading={data.isLoading}
            error={data.error}
          />
        </CustomCard>
      )}

      {project.data?.has_bess_strings && (
        <CustomCard title="BESS String" style={{ flex: 1 }}>
          <PlotlyPlot
            data={
              data.data?.bess_string &&
              data.data.bess_string.map((d) => ({
                x: d.x,
                y: d.y,
                name: d.name,
              }))
            }
            layout={{
              yaxis: {
                title: 'SOC (%)',
                tickformat: ',.0%',
                range: [0, 1],
              },
            }}
            isLoading={data.isLoading}
            error={data.error}
          />
        </CustomCard>
      )}
    </Stack>
  )
}

export default Page
