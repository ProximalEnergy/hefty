import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useGetProject } from '@/api/v1/operational/projects'
import { useGetDeviceDetailsHorizontalPV } from '@/api/v1/protected/web-application/projects/device-details/horizontal/pv'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectFilter } from '@/hooks/custom'
import { Stack } from '@mantine/core'
import { PlotMouseEvent } from 'plotly.js'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

const MAX_DAYS = 7

const Page = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.PV, ProjectTypeId.PV_BESS],
  })

  const { projectId } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
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

  const deviceDetails = useGetDeviceDetailsHorizontalPV({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: startRequest,
      end: endRequest,
    },
    queryOptions: { enabled: !!projectId && !!startRequest && !!endRequest },
  })

  if (project.isLoading) {
    return <PageLoader />
  }

  const handlePlotClick = (event: PlotMouseEvent) => {
    const { points } = event

    if (points.length !== 1) {
      return
    }

    const deviceId = points[0].data.customdata

    navigate(
      `/projects/${projectId}/device-details/vertical?device_id=${deviceId}&${searchParams.toString()}`,
    )
  }

  return (
    <Stack p="md" h="100%">
      <PageTitle info="View all Met Stations and PV PCSs in a single view. Click on a single PV PCS trace to zoom in to its vertical device detail view.">
        PV Device Details
      </PageTitle>
      <AdvancedDatePicker
        defaultRange="past-3-days"
        includeTodayInDateRange
        includeClearButton={false}
        maxDays={MAX_DAYS}
      />
      <CustomCard title="Met Station" style={{ flex: 1 }}>
        <PlotlyPlot
          data={
            deviceDetails.data &&
            deviceDetails.data.met.map((met) => ({
              x: deviceDetails.data.times,
              y: met.values,
              name: met.name,
              customdata: met.device_id,
            }))
          }
          layout={{
            yaxis: {
              title: 'POA (W/m²)',
            },
            hovermode: 'closest',
          }}
          isLoading={deviceDetails.isLoading}
          error={deviceDetails.error}
        />
      </CustomCard>
      <CustomCard title="PCS" style={{ flex: 2 }}>
        <PlotlyPlot
          data={
            deviceDetails.data &&
            deviceDetails.data.pcs.map((pcs) => ({
              x: deviceDetails.data.times,
              y: pcs.values,
              name: pcs.name,
              customdata: pcs.device_id,
            }))
          }
          layout={{
            yaxis: {
              title: 'AC Power (MW)',
            },
            hovermode: 'closest',
          }}
          isLoading={deviceDetails.isLoading}
          onClick={handlePlotClick}
          error={deviceDetails.error}
        />
      </CustomCard>
    </Stack>
  )
}

export default Page
