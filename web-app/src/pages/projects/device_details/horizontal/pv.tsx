import { ProjectTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetDeviceDetailsHorizontalPV } from '@/api/v1/protected/web-application/projects/device-details/horizontal/pv'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectFilter } from '@/hooks/custom'
import { SegmentedControl, Stack } from '@mantine/core'
import { PlotMouseEvent, PlotRelayoutEvent } from 'plotly.js'
import { useCallback, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router'

const MAX_DAYS = 7

const Page = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeEnum.PV, ProjectTypeEnum.PVS],
  })
  const navigate = useNavigate()

  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams] = useSearchParams()

  const [sharedXRange, setSharedXRange] = useState<
    [string, string] | undefined
  >(undefined)
  const [pcsChartType, setPcsChartType] = useState<'line' | 'heatmap'>('line')

  const project = useSelectProject(projectId!)

  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  let startRequest, endRequest
  if (project.data) {
    startRequest = start && start.tz(project.data.time_zone, true).toISOString()
    endRequest = end && end.tz(project.data.time_zone, true).toISOString()
  }

  const deviceDetails = useGetDeviceDetailsHorizontalPV({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      start: startRequest || '',
      end: endRequest || '',
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

    let deviceId: string | number | undefined

    if (pcsChartType === 'line') {
      // Line chart: customdata is directly the device_id
      const customdata = points[0].data.customdata
      if (customdata !== undefined && !Array.isArray(customdata)) {
        deviceId = customdata as string | number
      }
    } else if (pcsChartType === 'heatmap') {
      // Heatmap: use the y value (PCS name) to find the device_id
      const pcsName = points[0].y as string
      const pcs = deviceDetails.data?.pcs.find((p) => p.name === pcsName)
      deviceId = pcs?.device_id
    }

    if (deviceId !== undefined) {
      navigate(
        `/projects/${projectId}/device-details/vertical?device_id=${deviceId}&${searchParams.toString()}`,
      )
    }
  }

  return (
    <Stack p="md" h="100%">
      <PageTitle info="See project, met station, and PCS data in a single view. Click on a single PCS trace to zoom in to its vertical device detail view.">
        PV Device Details
      </PageTitle>
      <AdvancedDatePicker
        defaultRange="past-3-days"
        includeTodayInDateRange
        includeClearButton={false}
        maxDays={MAX_DAYS}
        disableQuickActions={true}
      />
      <CustomCard title="Project" style={{ flex: 1, minHeight: '250px' }}>
        <PlotlyPlot
          data={
            deviceDetails.data &&
            deviceDetails.data.meter_power.map((meterPower) => ({
              x: deviceDetails.data.times,
              y: meterPower.values,
              name: meterPower.name ?? undefined,
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
      <CustomCard title="Met Station" style={{ flex: 1, minHeight: '250px' }}>
        <PlotlyPlot
          data={
            deviceDetails.data &&
            deviceDetails.data.met.map((met) => ({
              x: deviceDetails.data.times,
              y: met.values,
              name: met.name ?? undefined,
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
      <CustomCard
        title="PCS"
        style={{ flex: 1, minHeight: '250px' }}
        headerChildren={
          <SegmentedControl
            size="xs"
            value={pcsChartType}
            onChange={(value) => setPcsChartType(value as 'line' | 'heatmap')}
            data={[
              { label: 'Line', value: 'line' },
              { label: 'Heatmap', value: 'heatmap' },
            ]}
          />
        }
      >
        <PlotlyPlot
          key={pcsChartType}
          data={(() => {
            if (!deviceDetails.data) return undefined
            switch (pcsChartType) {
              case 'line':
                return deviceDetails.data.pcs.map((pcs) => ({
                  x: deviceDetails.data.times,
                  y: pcs.values,
                  name: pcs.name ?? undefined,
                  customdata: pcs.device_id,
                }))
              case 'heatmap':
                return [
                  {
                    x: deviceDetails.data.times,
                    y: deviceDetails.data.pcs.map((pcs) => pcs.name),
                    z: deviceDetails.data.pcs.map((pcs) => pcs.values),
                    type: 'heatmap',
                    colorbar: {
                      orientation: 'h',
                      yref: 'container',
                      yanchor: 'bottom',
                      y: 0,
                      ticksuffix: ' MW',
                      thickness: 15,
                      title: {
                        text: 'AC Power',
                      },
                    },
                    colorscale: 'Portland',
                  },
                ]
              default:
                return undefined
            }
          })()}
          layout={{
            xaxis: {
              range: sharedXRange,
              autorange: sharedXRange === undefined ? true : false,
            },
            yaxis: {
              title: {
                text: pcsChartType === 'heatmap' ? 'PCS' : 'AC Power (MW)',
              },
              type: pcsChartType === 'heatmap' ? 'category' : undefined,
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
