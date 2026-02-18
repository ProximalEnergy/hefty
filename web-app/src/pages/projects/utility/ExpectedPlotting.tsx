import { DeviceTypeEnum, EventLossTypeEnum } from '@/api/enumerations'
import {
  EventLosses5MinSeries,
  useGetEventLosses5MinSingle,
} from '@/api/v1/operational/project/events'
import { useSelectProject } from '@/api/v1/operational/projects'
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
  Loader,
  Select,
  Stack,
  Text,
  Title,
  useMantineTheme,
} from '@mantine/core'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type { Data as PlotData } from 'plotly.js'
import { useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'

dayjs.extend(utc)
dayjs.extend(timezone)

type LossGroupEntry = {
  label: string
  series: EventLosses5MinSeries
  groupDeviceId: number | null
}

const Page = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const deviceId = searchParams.get('deviceId')
  const { start, end } = useValidateDateRange({})
  const [includeDegradation, setIncludeDegradation] = useState(false)
  let startQuery: string | undefined = undefined
  let endQuery: string | undefined = undefined
  const theme = useMantineTheme()

  const project = useSelectProject(projectId!)

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
      device_type_ids: [
        DeviceTypeEnum.METER,
        DeviceTypeEnum.PV_INVERTER,
        DeviceTypeEnum.PV_DC_COMBINER,
      ],
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

  const eventLosses5Min = useGetEventLosses5MinSingle({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: startQuery || '',
      end: endQuery || '',
      event_loss_type_ids: [EventLossTypeEnum.PROXIMAL_ENERGY],
      device_id: selectedDevice?.device_id || -1,
    },
    queryOptions: {
      enabled: !!selectedDevice && !!start && !!end && !!projectId,
    },
  })
  const projectTimeZone = project.data?.time_zone ?? 'UTC'

  const lossGroups = useMemo<LossGroupEntry[]>(() => {
    if (!eventLosses5Min.data) {
      return []
    }
    return eventLosses5Min.data.flatMap((entry) => {
      if ('data' in entry) {
        const fallbackLabel =
          entry.device_id ??
          entry.device_type_id ??
          entry.root_cause_id ??
          entry.failure_mode_id ??
          'Device'
        const label = String(fallbackLabel)
        return entry.data.map((series) => ({
          label,
          series,
          groupDeviceId: entry.device_id ?? null,
        }))
      }
      return [
        {
          label: String(entry.event_loss_type_id),
          series: entry,
          groupDeviceId: null,
        },
      ]
    })
  }, [eventLosses5Min.data])

  const lossDeviceIds = useMemo(() => {
    if (!lossGroups.length) {
      return []
    }
    const ids = lossGroups
      .map((group) => group.groupDeviceId)
      .filter((id): id is number => id !== null)
    return Array.from(new Set(ids))
  }, [lossGroups])

  const lossDevices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_ids: lossDeviceIds,
    },
    queryOptions: {
      enabled: !!projectId && lossDeviceIds.length > 0,
    },
  })

  const lossTraces = useMemo(() => {
    if (!lossGroups.length) {
      return []
    }
    const deviceNameById = new Map<number, string>()
    lossDevices.data?.forEach((device) => {
      if (device.device_id != null) {
        deviceNameById.set(
          device.device_id,
          device.name_full || `Device ${device.device_id}`,
        )
      }
    })
    return lossGroups.map(({ label, series, groupDeviceId }, index) => {
      const resolvedLabel =
        (groupDeviceId != null
          ? deviceNameById.get(groupDeviceId)
          : undefined) || label
      return {
        x: series.losses.time.map((time) =>
          dayjs(time).tz(projectTimeZone, true).format('YYYY-MM-DD HH:mm:ss'),
        ),
        y: series.losses.loss.map((loss) => loss * 1_000),
        name: `Event Losses - ${resolvedLabel}`,
        fill: 'tonexty',
        stackgroup: 'losses',
        fillcolor: theme.colors.gray[2],
        line: { color: theme.colors.gray[6 - (index % 4)] },
      } satisfies PlotData
    })
  }, [lossDevices.data, lossGroups, projectTimeZone, theme.colors.gray])

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

  const expectedTimes = expected.data?.times?.map((time) =>
    dayjs(time).tz(projectTimeZone, true).format('YYYY-MM-DD HH:mm:ss'),
  )

  const expectedPlotData: PlotData[] = [
    {
      x: expectedTimes,
      y: expected.data?.actual.power,
      name: 'Actual',
      fill: 'tozeroy',
      stackgroup: 'losses',
      fillcolor: theme.colors.blue[2],
    },
    {
      x: expectedTimes,
      y: expected.data?.expected_soiled.power,
      name: 'Expected (Soiled)',
    },
    {
      x: expectedTimes,
      y: expected.data?.expected_soiled.difference,
      name: 'Difference (Soiled)',
      fill: 'tozeroy',
      fillpattern: {
        shape: '/',
      },
    },
    {
      x: expectedTimes,
      y: expected.data?.expected_soiled.version.map((version) =>
        version ? 0 : null,
      ),
      text: expected.data?.expected_soiled.version.map((version) =>
        version != null ? String(version) : '',
      ),
      name: 'Version (Soiled)',
      hovertemplate: 'v%{text}',
      mode: 'markers',
      marker: {
        color: expected.data?.expected_soiled.version.map((version) =>
          version ? versionColorMap[version] : theme.colors.gray[4],
        ),
        size: 4,
      },
    },
    {
      x: expectedTimes,
      y: expected.data?.expected_clean.power,
      name: 'Expected (Clean)',
      visible: 'legendonly',
    },
    {
      x: expectedTimes,
      y: expected.data?.expected_clean.difference,
      name: 'Difference (Clean)',
      visible: 'legendonly',
      fill: 'tozeroy',
      fillpattern: {
        shape: '/',
      },
    },
    {
      x: expectedTimes,
      y: expected.data?.expected_clean.version.map((version) =>
        version ? 0 : null,
      ),
      text: expected.data?.expected_clean.version.map((version) =>
        version != null ? String(version) : '',
      ),
      name: 'Version (Clean)',
      hovertemplate: 'v%{text}',
      mode: 'markers',
      marker: {
        color: expected.data?.expected_clean.version.map((version) =>
          version ? versionColorMap[version] : theme.colors.gray[4],
        ),
        size: 4,
      },
      visible: 'legendonly',
    },
    ...Object.entries(expected.data?.poa || {}).map(([key, value]) => ({
      x: expectedTimes,
      y: value,
      name: key,
      legendgroup: 'POA',
      showlegend: false,
      yaxis: 'y2',
      visible: 'legendonly',
    })),
    {
      x: expectedTimes,
      y: expectedTimes?.map(() => null),
      name: 'POA',
      yaxis: 'y2',
      legendgroup: 'POA',
      visible: 'legendonly',
    },
    ...Object.entries(expected.data?.soiling || {}).map(([key, value]) => ({
      x: expectedTimes,
      y: value,
      name: key,
      legendgroup: 'Soiling',
      showlegend: false,
      yaxis: 'y3',
      visible: 'legendonly',
    })),
    {
      x: expectedTimes,
      y: expectedTimes?.map(() => null),
      name: 'Soiling',
      yaxis: 'y3',
      legendgroup: 'Soiling',
      visible: 'legendonly',
    },
  ]

  const plotData: PlotData[] = [...expectedPlotData, ...lossTraces]

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
        {eventLosses5Min.isPending && (
          <>
            <Loader size="sm" />
            <Text>Loading event losses...</Text>
          </>
        )}
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
          data={plotData}
          layout={{
            yaxis: {
              title: { text: 'Power (kW)' },
            },
            yaxis2: {
              title: { text: 'POA' },
              overlaying: 'y',
              side: 'right',
            },
            yaxis3: {
              title: { text: 'Soiling' },
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
