import { useGetProject } from '@/api/v1/operational/projects'
import { useGetUtilityExpected } from '@/api/v1/protected/pv-expected-energy/plot/plot'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { traceColors } from '@/components/plots/PlotlyPlotUtils'
import { useGetDevicesV2 } from '@/hooks/api'
import {
  Badge,
  Breadcrumbs,
  Chip,
  Group,
  Select,
  Stack,
  Title,
  useMantineTheme,
} from '@mantine/core'
import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'

const Page = () => {
  const { projectId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const deviceId = searchParams.get('deviceId')
  const { start, end } = useValidateDateRange({})
  const [includeDegradation, setIncludeDegradation] = useState(false)
  let startQuery: string | undefined = undefined
  let endQuery: string | undefined = undefined
  const theme = useMantineTheme()

  const project = useGetProject({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  if (project.data) {
    if (start) {
      // Convert to YYYY-MM-DD format
      startQuery = start.tz(project.data.time_zone, true).toISOString()
    }
    if (end) {
      // Convert to YYYY-MM-DD format
      endQuery = end.tz(project.data.time_zone, true).toISOString()
    }
  }

  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [5, 2, 9],
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  const selectedDevice = devices.data?.find(
    (device) => device.device_id === Number(deviceId),
  )

  const expected = useGetUtilityExpected({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_id: Number(deviceId),
      start: startQuery || '',
      end: endQuery || '',
      warranted_degradation: includeDegradation,
    },
    queryOptions: {
      enabled: !!selectedDevice && !!start && !!end,
    },
  })
  const parentDevices = expected.data?.parent_devices

  if (devices.isLoading) return <PageLoader />

  const uniqueVersions = [
    ...(expected.data?.expected_clean.unique_versions || []),
    ...(expected.data?.expected_soiled.unique_versions || []),
  ]

  const versionColorMap = Object.fromEntries(
    uniqueVersions.map((version, index) => [
      version,
      traceColors(theme)[index],
    ]),
  )

  return (
    <Stack h="100%" p="md">
      <Group>
        <Title order={1}>Expected Power Plotting</Title>
        <Chip
          checked={includeDegradation}
          onChange={(event) => setIncludeDegradation(event)}
        >
          Include Degradation
        </Chip>
      </Group>
      <Group>
        <AdvancedDatePicker
          includeClearButton={false}
          defaultRange="past-week"
          includeTodayInDateRange
        />
        <Select
          data={
            devices.data?.map((device) => ({
              value: String(device.device_id || -1), // Convert to string
              label: device.name_full || '',
            })) || []
          }
          placeholder="Select a device..."
          value={deviceId || null}
          onChange={(value) => {
            searchParams.set('deviceId', value || '')
            setSearchParams(searchParams)
          }}
          searchable
        />
        <Breadcrumbs separator="→">
          {parentDevices
            ?.slice()
            .reverse()
            .map((item) => (
              <Badge
                key={item.name_full}
                variant="outline"
                size="lg"
                radius="md"
              >
                {item.name_full}
              </Badge>
            ))}
        </Breadcrumbs>
      </Group>
      <CustomCard title="Expected Power Plotting" style={{ height: '100%' }}>
        <PlotlyPlot
          data={[
            {
              x: expected.data?.times,
              y: expected.data?.actual.power,
              name: 'Actual',
              fill: 'tozeroy',
            },
            {
              x: expected.data?.times,
              y: expected.data?.expected_soiled.power,
              name: 'Expected (Soiled)',
            },
            {
              x: expected.data?.times,
              y: expected.data?.expected_soiled.difference,
              name: 'Difference (Soiled)',
              fill: 'tozeroy',
              fillpattern: {
                shape: '/',
              },
            },
            {
              x: expected.data?.times,
              y: expected.data?.expected_soiled.version.map((version) =>
                version ? 0 : null,
              ),
              text: expected.data?.expected_soiled.version,
              name: 'Version (Soiled)',
              hovertemplate: 'v%{text}',
              mode: 'markers',
              marker: {
                color: expected.data?.expected_soiled.version.map((version) => {
                  return versionColorMap[version]
                }),
                size: 4,
              },
            },
            {
              x: expected.data?.times,
              y: expected.data?.expected_clean.power,
              name: 'Expected (Clean)',
              visible: 'legendonly',
            },
            {
              x: expected.data?.times,
              y: expected.data?.expected_clean.difference,
              name: 'Difference (Clean)',
              visible: 'legendonly',
              fill: 'tozeroy',
              fillpattern: {
                shape: '/',
              },
            },
            {
              x: expected.data?.times,
              y: expected.data?.expected_clean.version.map((version) =>
                version ? 0 : null,
              ),
              text: expected.data?.expected_clean.version,
              name: 'Version (Clean)',
              hovertemplate: 'v%{text}',
              mode: 'markers',
              marker: {
                color: expected.data?.expected_clean.version.map((version) => {
                  return versionColorMap[version]
                }),
                size: 4,
              },
              visible: 'legendonly',
            },
            ...Object.entries(expected.data?.poa || {}).map(([key, value]) => ({
              x: expected.data?.times,
              y: value,
              name: key,
              legendgroup: 'POA',
              showlegend: false,
              yaxis: 'y2',
              visible: 'legendonly',
            })),
            {
              x: expected.data?.times,
              y: expected.data?.times.map(() => null),
              name: 'POA',
              yaxis: 'y2',
              legendgroup: 'POA',
              visible: 'legendonly',
            },
            ...Object.entries(expected.data?.soiling || {}).map(
              ([key, value]) => ({
                x: expected.data?.times,
                y: value,
                name: key,
                legendgroup: 'Soiling',
                showlegend: false,
                yaxis: 'y3',
                visible: 'legendonly',
              }),
            ),
            {
              x: expected.data?.times,
              y: expected.data?.times.map(() => null),
              name: 'Soiling',
              yaxis: 'y3',
              legendgroup: 'Soiling',
              visible: 'legendonly',
            },
          ]}
          layout={{
            yaxis: {
              title: 'Power (kW)',
            },
            yaxis2: {
              title: 'POA',
              overlaying: 'y',
              side: 'right',
            },
            yaxis3: {
              title: 'Soiling',
              overlaying: 'y',
              side: 'right',
              // @ts-expect-error - This is a valid property
              autoshift: true,
              anchor: 'free',
            },
            hoverlabel: {
              namelength: -1,
            },
          }}
          isLoading={expected.isLoading}
          error={expected.error}
        />
      </CustomCard>
    </Stack>
  )
}

export default Page
