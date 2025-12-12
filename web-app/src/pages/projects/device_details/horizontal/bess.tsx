import { ProjectTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetDeviceDetailsHorizontalBESS } from '@/api/v1/protected/web-application/projects/device-details/horizontal/bess'
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
    projectTypes: [ProjectTypeEnum.BESS, ProjectTypeEnum.PVS],
  })
  const navigate = useNavigate()

  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams] = useSearchParams()

  const [sharedXRange, setSharedXRange] = useState<
    [string, string] | undefined
  >(undefined)
  const [batteryChartType, setBatteryChartType] = useState<'line' | 'heatmap'>(
    'line',
  )
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

  const handleBatteryPlotClick = (event: PlotMouseEvent) => {
    const { points } = event

    if (points.length !== 1) {
      return
    }

    let deviceId: string | number | undefined

    if (batteryChartType === 'line') {
      // Line chart: customdata is directly the device_id
      const customdata = points[0].data.customdata
      if (customdata !== undefined && !Array.isArray(customdata)) {
        deviceId = customdata as string | number
      }
    } else if (batteryChartType === 'heatmap') {
      // Heatmap: use the y value (battery name) to find the device_id
      const batteryName = points[0].y as string
      const battery = deviceDetails.data?.battery.find(
        (b) => b.name === batteryName,
      )
      deviceId = battery?.device_id
    }

    if (deviceId !== undefined) {
      navigate(
        `/projects/${projectId}/device-details/vertical?device_id=${deviceId}&${searchParams.toString()}`,
      )
    }
  }

  const handlePcsPlotClick = (event: PlotMouseEvent) => {
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
    <Stack p="md" style={{ overflow: 'auto', height: '100%' }}>
      <PageTitle info="View all BESS PCSs and the highest level of the BESS hierarchy in a single view. Click on a single trace to zoom in to its vertical device detail view.">
        BESS Device Details
      </PageTitle>
      <AdvancedDatePicker
        defaultRange="past-3-days"
        includeTodayInDateRange
        includeClearButton={false}
        maxDays={MAX_DAYS}
      />
      <CustomCard
        title="Project"
        style={{ flex: '0 0 auto', minHeight: '250px' }}
      >
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
      <CustomCard
        title="PCS"
        style={{ flex: '0 0 auto', minHeight: '250px' }}
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
                  name: pcs.name,
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
                text: pcsChartType === 'heatmap' ? 'PCS' : 'Power (MW)',
              },
              type: pcsChartType === 'heatmap' ? 'category' : undefined,
            },
            hovermode: 'closest',
          }}
          onRelayout={handleRelayout}
          isLoading={deviceDetails.isLoading}
          onClick={handlePcsPlotClick}
          error={deviceDetails.error}
        />
      </CustomCard>
      {batteryTitle && (
        <CustomCard
          title={batteryTitle}
          style={{ flex: '0 0 auto', minHeight: '250px' }}
          headerChildren={
            <SegmentedControl
              size="xs"
              value={batteryChartType}
              onChange={(value) =>
                setBatteryChartType(value as 'line' | 'heatmap')
              }
              data={[
                { label: 'Line', value: 'line' },
                { label: 'Heatmap', value: 'heatmap' },
              ]}
            />
          }
        >
          <PlotlyPlot
            key={batteryChartType}
            data={(() => {
              if (!deviceDetails.data) return undefined
              switch (batteryChartType) {
                case 'line':
                  return deviceDetails.data.battery.map((battery) => ({
                    x: deviceDetails.data.times,
                    y: battery.values,
                    name: battery.name,
                    customdata: battery.device_id,
                  }))
                case 'heatmap':
                  return [
                    {
                      x: deviceDetails.data.times,
                      y: deviceDetails.data.battery.map((b) => b.name),
                      z: deviceDetails.data.battery.map((b) => b.values),
                      type: 'heatmap',
                      colorbar: {
                        orientation: 'h',
                        yref: 'container',
                        yanchor: 'bottom',
                        y: 0,
                        tickformat: ',.0%',
                        thickness: 15,
                        title: {
                          text: 'SOC',
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
                tickformat: batteryChartType === 'heatmap' ? undefined : ',.0%',
                title: {
                  text:
                    batteryChartType === 'heatmap'
                      ? batteryTitle
                      : 'State of Charge',
                },
                type: batteryChartType === 'heatmap' ? 'category' : undefined,
              },
              hovermode: 'closest',
            }}
            onRelayout={handleRelayout}
            isLoading={deviceDetails.isLoading}
            onClick={handleBatteryPlotClick}
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
