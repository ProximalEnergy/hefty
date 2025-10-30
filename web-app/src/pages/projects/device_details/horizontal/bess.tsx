import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetDeviceDetailsHorizontalBESS } from '@/api/v1/protected/web-application/projects/device-details/horizontal/bess'
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
import { useNavigate, useParams, useSearchParams } from 'react-router'

const MAX_DAYS = 7

const Page = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.BESS, ProjectTypeId.PV_BESS],
  })
  const navigate = useNavigate()

  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams] = useSearchParams()

  const [sharedXRange, setSharedXRange] = useState<
    [string, string] | undefined
  >(undefined)

  const project = useSelectProject(projectId!)

  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  let startRequest, endRequest
  if (project.data) {
    startRequest = start && start.tz(project.data.time_zone, true).toISOString()
    endRequest = end && end.tz(project.data.time_zone, true).toISOString()
  }

  const deviceDetails = useGetDeviceDetailsHorizontalBESS({
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

  const batteryTitle = getBatteryTitle(project.data?.spec.used_sensor_type_ids)

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
      <PageTitle info="View all BESS PCSs and the highest level of the BESS hierarchy in a single view. Click on a single trace to zoom in to its vertical device detail view.">
        BESS Device Details
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
            deviceDetails.data
              ? [
                  ...deviceDetails.data.meter_power.map((meterPower) => ({
                    x: deviceDetails.data.times,
                    y: meterPower.values,
                    name: 'Power',
                    customdata: meterPower.device_id,
                    yaxis: 'y1',
                    fill: 'tozeroy',
                  })),
                  ...deviceDetails.data.meter_soc.map((meterSoc) => ({
                    x: deviceDetails.data.times,
                    y: meterSoc.values,
                    name: 'SOC',
                    customdata: meterSoc.device_id,
                    yaxis: 'y2',
                  })),
                ]
              : undefined
          }
          layout={{
            xaxis: {
              range: sharedXRange,
              autorange: sharedXRange === undefined ? true : false,
            },
            yaxis: {
              title: { text: 'Power (MW)' },
            },
            yaxis2: {
              title: { text: 'State of Charge' },
              overlaying: 'y',
              side: 'right',
              tickformat: ',.0%',
              showgrid: false,
              zeroline: false,
            },
            hovermode: 'closest',
            showlegend: false,
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
              title: { text: 'Power (MW)' },
            },
            hovermode: 'closest',
          }}
          onRelayout={handleRelayout}
          isLoading={deviceDetails.isLoading}
          error={deviceDetails.error}
          onClick={handlePlotClick}
        />
      </CustomCard>
      {batteryTitle && (
        <CustomCard title={batteryTitle} style={{ flex: 3 }}>
          <PlotlyPlot
            data={
              deviceDetails.data &&
              deviceDetails.data.battery.map((battery) => ({
                x: deviceDetails.data.times,
                y: battery.values,
                name: battery.name,
                customdata: battery.device_id,
              }))
            }
            layout={{
              xaxis: {
                range: sharedXRange,
                autorange: sharedXRange === undefined ? true : false,
              },
              yaxis: {
                tickformat: ',.0%',
                title: { text: 'State of Charge' },
              },
              hovermode: 'closest',
            }}
            onRelayout={handleRelayout}
            isLoading={deviceDetails.isLoading}
            onClick={handlePlotClick}
            error={deviceDetails.error}
          />
        </CustomCard>
      )}
    </Stack>
  )
}

function getBatteryTitle(usedSensorTypeIds: number[] | undefined) {
  if (!usedSensorTypeIds) {
    return undefined
  }
  if (usedSensorTypeIds.includes(43)) {
    return 'DC Enclosure'
  } else if (usedSensorTypeIds.includes(44)) {
    return 'BESS Bank'
  } else if (usedSensorTypeIds.includes(45)) {
    return 'BESS String'
  }
  return undefined
}

export default Page
