import { useGetProject } from '@/api/v1/operational/projects'
import {
  DeviceDetailsSingle,
  useGetDeviceDetailsSingle,
} from '@/api/v1/protected/web-application/projects/device-details/single'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetDevice } from '@/hooks/api'
import { ActionIcon, Group, Stack, Tooltip } from '@mantine/core'
import { IconArrowBackUp } from '@tabler/icons-react'
import { Link, useParams, useSearchParams } from 'react-router'

const MAX_DAYS = 7

const Page = () => {
  const { deviceId, projectId } = useParams()
  const [searchParams] = useSearchParams()

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

  const device = useGetDevice({
    pathParams: { deviceId: deviceId || '-1', projectId: projectId || '-1' },
    queryParams: { deep: true },
  })

  const deviceData = useGetDeviceDetailsSingle({
    pathParams: { deviceId: deviceId || '-1', projectId: projectId || '-1' },
    queryParams: {
      start: startRequest,
      end: endRequest,
    },
    queryOptions: {
      enabled: !!startRequest && !!endRequest,
    },
  })

  function cleanSearchParams() {
    const params = new URLSearchParams(searchParams)
    params.set('device_id', deviceId || '-1')
    return params.toString()
  }

  if (device.isLoading) {
    return <PageLoader />
  }

  return (
    <Stack p="md" h="100%">
      <PageTitle>{`${device.data?.device_type?.name_long} ${device.data?.name_long} Device Details`}</PageTitle>
      <Group>
        <AdvancedDatePicker
          defaultRange="today"
          includeTodayInDateRange
          includeClearButton={false}
          maxDays={MAX_DAYS}
        />
        <Link
          to={`/projects/${projectId}/device-details/vertical?${cleanSearchParams()}`}
        >
          <Tooltip
            label="To vertical device details"
            withArrow
            position="bottom"
          >
            <ActionIcon variant="light" size="input-sm">
              <IconArrowBackUp
                style={{ width: '70%', height: '70%' }}
                stroke={1.5}
              />
            </ActionIcon>
          </Tooltip>
        </Link>
      </Group>
      <CustomCard title="Device Details" style={{ flex: 1 }}>
        <PlotlyPlot
          {...PlotDataStacked({ dataRaw: deviceData.data })}
          isLoading={deviceData.isLoading}
          error={deviceData.error}
        />
      </CustomCard>
    </Stack>
  )
}

// const PlotDataDefault = ({
//   dataRaw,
// }: {
//   dataRaw: DeviceDetailsSingle | undefined;
// }) => {
//   if (!dataRaw) {
//     return { data: [], layout: {} };
//   }

//   const data = dataRaw.data?.map((item) => ({
//     x: dataRaw.time,
//     y: item.values,
//     name: item.name,
//   }));

//   return { data, layout: {} };
// };

const PlotDataStacked = ({
  dataRaw,
}: {
  dataRaw: DeviceDetailsSingle | undefined
}) => {
  if (!dataRaw) {
    return { data: [], layout: {} }
  }

  // Reorganize data by units
  const organizedData = {
    time: dataRaw.time,
    data: dataRaw.data.reduce(
      (
        acc: Record<string, Array<{ name: string; values: number[] }>>,
        item,
      ) => {
        const unit = item.unit || 'Dimensionless'
        if (!acc[unit]) {
          acc[unit] = []
        }
        acc[unit].push({
          name: item.name,
          values: item.values,
        })
        return acc
      },
      {},
    ),
  }

  // Iterate over the organized data units and then the data in each unit
  const data = Object.entries(organizedData.data).flatMap(
    ([, items], index) => {
      return items.map((item) => ({
        x: organizedData.time,
        y: item.values,
        name: item.name,
        yaxis: index === 0 ? 'y' : `y${index + 1}`,
      }))
    },
  )

  // Loop over each unit and create a new yaxis (object with axis name as the key)
  const axes = Object.entries(organizedData.data).reduce(
    (acc: Record<string, object>, [unit], index) => {
      const key = index === 0 ? 'yaxis' : `yaxis${index + 1}`
      acc[key] = {
        title: unit,
        showgrid: false,
        autoshift: true,
        side: index % 2 === 0 ? 'left' : 'right',
        overlaying: index === 0 ? undefined : 'y',
        anchor: index === 0 ? undefined : 'free',
      }
      return acc
    },
    {},
  )

  return {
    data,
    layout: {
      ...axes,
      hoverlabel: {
        namelength: -1,
      },
    },
  }
}

export default Page
