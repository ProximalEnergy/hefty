import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import CustomCard from '@/components/CustomCard'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { traceColors } from '@/components/plots/PlotlyPlotUtils'
import { useGetDevicesV2 } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import { Stack, useMantineTheme } from '@mantine/core'
import { useParams } from 'react-router'

const MAX_DAYS = 7

const Page = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.PV, ProjectTypeId.PV_BESS],
  })

  const { projectId } = useParams<{ projectId: string }>()
  const theme = useMantineTheme()

  const { start, end } = useValidateDateRange({
    maxDays: MAX_DAYS,
  })

  const project = useSelectProject(projectId!)

  const { data, isLoading, error } = useGetTimeSeries({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      sensor_type_name_shorts: [
        'met_station_poa',
        'met_station_ghi',
        'met_station_ambient_temperature',
        'met_station_wind_speed',
      ],
      start: start?.tz(project.data?.time_zone, true).toISOString(),
      end: end?.tz(project.data?.time_zone, true).toISOString(),
    },
  })

  const { data: devices } = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [4, 6],
    },
  })

  // Check and see which sensors are available at the project
  const hasIrradiance =
    project.data?.spec.used_sensor_type_ids?.includes(4) ||
    project.data?.spec.used_sensor_type_ids?.includes(5)
  const hasTemperature = project.data?.spec.used_sensor_type_ids?.includes(6)
  const hasWindSpeed = project.data?.spec.used_sensor_type_ids?.includes(7)

  // Count the number of sensors that are available at the project
  const numRows = [hasIrradiance, hasTemperature, hasWindSpeed].filter(
    (v) => v,
  ).length

  // Create a mapping of hasIrradiance, hasTemperature, hasWindSpeed to the yaxis index
  const yAxisMap: { [key: string]: number } = {}
  let index = 1

  Object.entries({
    irradiance: hasIrradiance,
    temperature: hasTemperature,
    windSpeed: hasWindSpeed,
  }).forEach(([key, value]) => {
    if (value) {
      yAxisMap[key] = index++
    }
  })

  // Create a new object with yAxisMap but reversed
  const reversedYAxisMap = Object.entries(yAxisMap).reduce(
    (acc, [key, value]) => {
      acc[value] = key as keyof typeof axisLabelMap
      return acc
    },
    {} as { [key: number]: keyof typeof axisLabelMap },
  )

  const axisLabelMap = {
    irradiance: 'Irradiance (W/m<sup>2</sup>)',
    temperature: 'Temp. (°C)',
    windSpeed: 'Wind Speed (m/s)',
  }

  const uniqueDeviceNames = Array.from(
    new Set(data?.map((d) => d.device_name_long)),
  )

  const traceColorsTheme = traceColors(theme)

  // Map each unique device name to a color
  const colorMap = uniqueDeviceNames.reduce(
    (acc, cur, idx) => {
      acc[cur] = traceColorsTheme[idx % traceColorsTheme.length]
      return acc
    },
    {} as { [key: string]: string },
  )

  // New object to hold the name references
  const name_ref: { [key: string]: string } = {}

  // Iterate through devices to populate name_ref
  devices?.forEach((device) => {
    if (device.device_type_id === 4 && device.parent_device_id) {
      const parentDevice = devices.find(
        (d) =>
          d.device_type_id === 6 && d.device_id === device.parent_device_id,
      )
      if (parentDevice) {
        name_ref[device.name_long ?? ''] = parentDevice.name_long ?? ''
      }
    }
  })

  // Prepare plot data based on available sensors
  const plotData = []

  // Add irradiance data if available
  if (hasIrradiance) {
    // Add POA data
    const poaData =
      data
        ?.filter((d) => d.sensor_type_name === 'met_station_poa')
        .map((d) => ({
          x: d.x,
          y: d.y,
          yaxis: `y${yAxisMap.irradiance}`,
          name:
            'Block ' +
            (name_ref[d.device_name_long] || d.device_name_long) +
            ' ' +
            d.name,
          hoverlabel: { namelength: -1 },
          line: { color: colorMap[d.device_name_long] },
        })) || []

    // Add GHI data
    const ghiData =
      data
        ?.filter((d) => d.sensor_type_name === 'met_station_ghi')
        .map((d) => ({
          x: d.x,
          y: d.y,
          yaxis: `y${yAxisMap.irradiance}`,
          name:
            'Block ' +
            (name_ref[d.device_name_long] || d.device_name_long) +
            ' ' +
            d.name,
          hoverlabel: { namelength: -1 },
          line: { color: colorMap[d.device_name_long] },
        })) || []

    plotData.push(...poaData, ...ghiData)
  }

  // Add temperature data if available
  if (hasTemperature) {
    const tempData =
      data
        ?.filter(
          (d) => d.sensor_type_name === 'met_station_ambient_temperature',
        )
        .map((d) => ({
          x: d.x,
          y: d.y,
          yaxis: `y${yAxisMap.temperature}`,
          name:
            'Block ' +
            (name_ref[d.device_name_long] || d.device_name_long) +
            ' ' +
            d.name,
          hoverlabel: { namelength: -1 },
          line: { color: colorMap[d.device_name_long] },
        })) || []

    plotData.push(...tempData)
  }

  // Add wind speed data if available
  if (hasWindSpeed) {
    const windData =
      data
        ?.filter((d) => d.sensor_type_name === 'met_station_wind_speed')
        .map((d) => ({
          x: d.x,
          y: d.y,
          yaxis: `y${yAxisMap.windSpeed}`,
          name:
            'Block ' +
            (name_ref[d.device_name_long] || d.device_name_long) +
            ' ' +
            d.name,
          hoverlabel: { namelength: -1 },
          line: { color: colorMap[d.device_name_long] },
        })) || []

    plotData.push(...windData)
  }

  return (
    <Stack h="100%" p="md">
      <AdvancedDatePicker
        maxDays={MAX_DAYS}
        disableQuickActions={true}
        includeClearButton={false}
        defaultRange="today"
        includeTodayInDateRange
      />
      <CustomCard title="Met Stations" style={{ height: '100%' }}>
        <PlotlyPlot
          data={plotData}
          layout={{
            grid: { rows: numRows, columns: 1 },
            yaxis: {
              title: { text: axisLabelMap[reversedYAxisMap[1]] },
              automargin: true,
            },
            yaxis2: {
              title: { text: axisLabelMap[reversedYAxisMap[2]] },
              automargin: true,
            },
            yaxis3: {
              title: { text: axisLabelMap[reversedYAxisMap[3]] },
              automargin: true,
            },
          }}
          isLoading={isLoading}
          error={error}
        />
      </CustomCard>
    </Stack>
  )
}

export default Page
