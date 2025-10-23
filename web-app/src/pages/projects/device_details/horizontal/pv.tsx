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
import { PlotMouseEvent, PlotRelayoutEvent } from 'plotly.js'
import { useCallback, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

const MAX_DAYS = 7

const Page = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.PV, ProjectTypeId.PV_BESS],
  })
  const navigate = useNavigate()

  const { projectId } = useParams()
  const [searchParams] = useSearchParams()

  const [sharedXRange, setSharedXRange] = useState<
    [string, string] | undefined
  >(undefined)

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

  // Handler for plot resizing
  const handleRelayout = useCallback((event: Partial<PlotRelayoutEvent>) => {
    if (
      event['xaxis.range[0]'] !== undefined &&
      event['xaxis.range[1]'] !== undefined
    ) {
      setSharedXRange([
        event['xaxis.range[0]'].toString(),
        event['xaxis.range[1]'].toString(),
      ])
    } else if (event['xaxis.autorange']) {
      setSharedXRange(undefined)
    }
  }, [])

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
      <CustomCard title="Project" style={{ flex: 2 }}>
        <PlotlyPlot
          data={
            deviceDetails.data &&
            deviceDetails.data.meter_power.map((meterPower) => ({
              x: deviceDetails.data.times,
              y: meterPower.values,
              name: meterPower.name,
              fill: 'tozeroy',
              customdata: meterPower.device_id,
            }))
          }
          layout={{
            xaxis: {
              range: sharedXRange,
              autorange: sharedXRange === undefined ? true : false,
            },
            yaxis: {
              title: { text: 'Power (MW)' },
            },
          }}
          onRelayout={handleRelayout}
          isLoading={deviceDetails.isLoading}
          error={deviceDetails.error}
        />
      </CustomCard>
      <CustomCard title="Met Station" style={{ flex: 3 }}>
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
            xaxis: {
              range: sharedXRange,
              autorange: sharedXRange === undefined ? true : false,
            },
            yaxis: {
              title: { text: 'POA (W/m²)' },
            },
            hovermode: 'closest',
          }}
          onRelayout={handleRelayout}
          isLoading={deviceDetails.isLoading}
          error={deviceDetails.error}
        />
      </CustomCard>
      <CustomCard title="PCS" style={{ flex: 3 }}>
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
            xaxis: {
              range: sharedXRange,
              autorange: sharedXRange === undefined ? true : false,
            },
            yaxis: {
              title: { text: 'AC Power (MW)' },
            },
            hovermode: 'closest',
          }}
          onRelayout={handleRelayout}
          isLoading={deviceDetails.isLoading}
          onClick={handlePlotClick}
          error={deviceDetails.error}
        />
      </CustomCard>
    </Stack>
  )
}

export default Page
