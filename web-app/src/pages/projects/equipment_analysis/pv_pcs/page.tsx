import { useGetKPISummaryCards } from '@/api/v1/operational/project/kpi_data'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetEquipmentAnalysisPCSv2 } from '@/api/v1/protected/web-application/projects/equipment-analysis/pv_pcs'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetHeatmap } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import {
  ActionIcon,
  Button,
  Checkbox,
  Group,
  RingProgress,
  Skeleton,
  Slider,
  Stack,
  Text,
} from '@mantine/core'
import {
  IconExternalLink,
  IconPlayerPauseFilled,
  IconPlayerPlayFilled,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'

dayjs.extend(utc)
dayjs.extend(timezone)

const colorFromPercent = (numerator: number, denominator: number) => {
  const percent = (numerator / denominator) * 100
  if (percent >= 90) {
    return 'green'
  } else if (percent >= 75) {
    return 'yellow'
  } else {
    return 'red'
  }
}

const PCSHeatmap = ({
  startQuery,
  endQuery,
}: {
  startQuery: string | undefined
  endQuery: string | undefined
}) => {
  const { projectId } = useParams<{ projectId: string }>()

  const { data, isLoading, error } = useGetHeatmap({
    pathParams: {
      projectId: projectId || '-1',
      sensorTypeName: 'pv_pcs_ac_power',
    },
    queryParams: {
      fillna_zero: false,
      start: startQuery,
      end: endQuery,
    },
  })

  return (
    <PlotlyPlot
      data={[
        {
          z: data?.z,
          x: data?.x,
          y: data?.y,
          type: 'heatmap',
          colorbar: {
            title: {
              text: 'Power (MW)',
            },
            ticksuffix: ' MW',
          },
        },
      ]}
      layout={{
        xaxis: {
          tickangle: -45,
        },
        yaxis: {
          type: 'category',
          dtick: 1,
          tick0: 0,
          title: {
            text: 'Inverter Name',
          },
        },
        height: 450,
      }}
      colorscale={'primary'}
      isLoading={isLoading}
      error={error}
    />
  )
}

interface RingProgressCardProps {
  title: string
  subtitle: string
  value: number | null
  total: number | null
  color?: string
  isLoading: boolean
  size?: number
  skeletonHeight?: number
  skeletonMargin?: number
}

const RingProgressCard: React.FC<RingProgressCardProps> = ({
  title,
  subtitle,
  value,
  total,
  color = 'grey',
  isLoading,
  size = 150,
  skeletonHeight = 111,
  skeletonMargin = 19.5,
}) => {
  return (
    <Stack align="center" gap={0}>
      <Text>{title}</Text>
      <Text size="sm">{subtitle}</Text>
      {isLoading ? (
        <Skeleton height={skeletonHeight} circle m={skeletonMargin} />
      ) : (
        <RingProgress
          size={size}
          thickness={Math.max(4, Math.floor(size / 16))}
          style={{ '--rp-size': `${size}px` } as React.CSSProperties}
          label={
            <Text size="lg" fw={700} ta="center">
              {value !== null && total !== null
                ? `${value}/${total}`
                : 'No Data'}
            </Text>
          }
          sections={[
            {
              value:
                value !== null && total !== null ? (value / total) * 100 : 0,
              color,
            },
          ]}
        />
      )}
    </Stack>
  )
}

const PCSEquipmentAnalysis = () => {
  useProjectFilter({
    projectTypes: [ProjectTypeId.PV, ProjectTypeId.PV_BESS],
  })

  const { projectId } = useParams<{ projectId: string }>()
  const [sliderValue, setSliderValue] = useState(0)
  const [initialSliderValueSet, setInitialSliderValueSet] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const intervalRef = useRef<number | null>(null)
  const { start, end } = useValidateDateRange({})

  const [blockNormalize, setBlockNormalize] = useState(false)
  const [pcsNormalize, setPcsNormalize] = useState(false)

  let startQuery: string | undefined = undefined
  let endQuery: string | undefined = undefined

  const project = useSelectProject(projectId!)

  if (project.data) {
    if (start) {
      startQuery = start.tz(project.data.time_zone, true).format('YYYY-MM-DD')
    }
    if (end) {
      endQuery = end.tz(project.data.time_zone, true).toISOString()
    }
  }

  const includeEnergy =
    (start && !start.isSame(dayjs().startOf('day'))) || false

  const { data: produced } = useGetKPISummaryCards({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { kpi_type_ids: [6] },
    queryOptions: {
      enabled: includeEnergy,
    },
  })

  const data = useGetEquipmentAnalysisPCSv2({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { start: startQuery, end: endQuery },
    queryOptions: { enabled: !!projectId },
  })

  const dataLength = data.data?.total_power_output.value.length

  const startISO = start?.toISOString()

  useEffect(() => {
    queueMicrotask(() => setInitialSliderValueSet(false))
    queueMicrotask(() => setSliderValue(0))
  }, [startISO])

  useEffect(() => {
    if (data.isLoading || initialSliderValueSet) {
      return
    }
    if (!dataLength) {
      queueMicrotask(() => setSliderValue(0))
      return
    }

    // Check if we're looking at today's data
    const isToday = start && start.isSame(dayjs().startOf('day'))

    if (isToday) {
      // For today, show the most current available time
      queueMicrotask(() => setSliderValue(dataLength - 1))
    } else {
      // For previous days, show middle of the day
      queueMicrotask(() => setSliderValue(Math.floor(dataLength / 2)))
    }
    queueMicrotask(() => setInitialSliderValueSet(true))
  }, [dataLength, data.isLoading, initialSliderValueSet, start, startISO])

  useEffect(() => {
    if (dataLength === 1) {
      queueMicrotask(() => setSliderValue(0))
    }
    if (isPlaying && dataLength) {
      intervalRef.current = window.setInterval(() => {
        queueMicrotask(() =>
          setSliderValue((prevValue) => (prevValue + 1) % dataLength),
        )
      }, 5000 / dataLength)
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [isPlaying, dataLength])

  const togglePlay = () => {
    setIsPlaying((prev) => !prev)
  }

  if (project.isLoading) {
    return <PageLoader />
  }

  let hasPCSModules = false
  if (project.data?.spec.used_sensor_type_ids?.includes(3)) {
    hasPCSModules = true
  }

  const getTimeFromSliderValue = (value: number) => {
    const startOfDay = dayjs().tz(project.data?.time_zone).startOf('day')
    const currentTime = startOfDay.add(value * 5, 'minute')
    return currentTime.format('HH:mm')
  }
  const blockData = blockNormalize
    ? data.data?.block_power_distribution_norm
    : data.data?.block_power_distribution
  const pcsData = pcsNormalize
    ? data.data?.pcs_power_distribution_norm
    : data.data?.pcs_power_distribution
  const startLink = start?.subtract(3, 'day').format('YYYY-MM-DD')
  const endLink = dayjs(end).add(2, 'day').isBefore(dayjs())
    ? dayjs(end).add(2, 'day').format('YYYY-MM-DD')
    : dayjs().subtract(1, 'day').format('YYYY-MM-DD')

  return (
    <Stack p="md">
      <Skeleton visible={data.isLoading}>
        <Group>
          <AdvancedDatePicker
            maxDays={1}
            includeTodayInDateRange
            disableQuickActions
            defaultRange="today"
            includeClearButton={false}
          />
          {includeEnergy && produced?.[0]?.value ? (
            <Link
              to={`/projects/${projectId}/kpis/type/6?start=${startLink}&end=${endLink}`}
              style={{ textDecoration: 'none', color: 'inherit' }}
            >
              <Button rightSection={<IconExternalLink size={16} />}>
                Daily Energy: {produced?.[0]?.value} MWh
              </Button>
            </Link>
          ) : null}
          {dataLength && dataLength > 1 && (
            <>
              <Slider
                value={sliderValue}
                label={getTimeFromSliderValue(sliderValue)}
                onChange={setSliderValue}
                min={0}
                max={
                  data.data?.total_power_output.value.length
                    ? data.data.total_power_output.value.length - 1
                    : 0
                }
                step={1}
                style={{ flex: 1 }}
              />
              <ActionIcon onClick={togglePlay}>
                {isPlaying ? (
                  <IconPlayerPauseFilled size={16} />
                ) : (
                  <IconPlayerPlayFilled size={16} />
                )}
              </ActionIcon>
            </>
          )}
        </Group>
      </Skeleton>
      <Group w="100%" justify="space-evenly" align="flex-end">
        <RingProgressCard
          title="AC Capacity (MW)"
          subtitle="Out of nameplate capacity"
          value={
            data.data?.total_power_output.value[
              dataLength && dataLength > 1 ? sliderValue : 0
            ] ?? null
          }
          total={data.data?.total_power_output.total_nameplate ?? null}
          isLoading={data.isLoading}
          color="grey"
        />
        <RingProgressCard
          title="Blocks"
          subtitle="Generating Power"
          value={
            data.data?.generating_power_block.value[
              dataLength && dataLength > 1 ? sliderValue : 0
            ] ?? null
          }
          total={data.data?.generating_power_block.total ?? null}
          isLoading={data.isLoading}
          color={
            data.data
              ? colorFromPercent(
                  data.data.generating_power_block.value[
                    dataLength && dataLength > 1 ? sliderValue : 0
                  ],
                  data.data.generating_power_block.total,
                )
              : 'grey'
          }
        />
        <RingProgressCard
          title="PCSs"
          subtitle="Generating Power"
          value={
            data.data?.generating_power_pcs.value[
              dataLength && dataLength > 1 ? sliderValue : 0
            ] ?? null
          }
          total={data.data?.generating_power_pcs.total ?? null}
          isLoading={data.isLoading}
          color={
            data.data
              ? colorFromPercent(
                  data.data.generating_power_pcs.value[
                    dataLength && dataLength > 1 ? sliderValue : 0
                  ],
                  data.data.generating_power_pcs.total,
                )
              : 'grey'
          }
        />
        {hasPCSModules && (
          <RingProgressCard
            title="PCS Modules"
            subtitle="Generating Power"
            value={
              data.data?.generating_power_pcs_module?.value[
                dataLength && dataLength > 1 ? sliderValue : 0
              ] ?? null
            }
            total={data.data?.generating_power_pcs_module?.total ?? null}
            isLoading={data.isLoading}
            color={
              data.data
                ? colorFromPercent(
                    data.data.generating_power_pcs_module?.value[
                      dataLength && dataLength > 1 ? sliderValue : 0
                    ] ?? 0,
                    data.data.generating_power_pcs_module?.total ?? 0,
                  )
                : 'grey'
            }
          />
        )}
      </Group>
      <CustomCard
        title="Block Output Distribution"
        style={{ height: '250px' }}
        info="This plot shows the power output of each block. Clicking the 'Normalize by DC Input' button will equalize the performance of each block against its installed DC capacity, which is useful since installed capacity often differs per block. Look for large differences in performance between equipment to narrow down possible issues."
        headerChildren={
          <Checkbox
            label="Normalize by DC Input"
            value={blockNormalize ? 'true' : 'false'}
            onChange={(event) => setBlockNormalize(event.currentTarget.checked)}
          />
        }
      >
        <PlotlyPlot
          data={
            data.data && [
              {
                x: blockData?.x,
                y: blockData?.y[dataLength && dataLength > 1 ? sliderValue : 0],
                customdata: blockData?.customdata,
                type: 'bar',
              },
            ]
          }
          layout={
            data.data && {
              xaxis: { type: 'category', title: { text: 'Block' } },
              yaxis: {
                range: [0, blockData ? blockData.yaxis_range_max * 1.05 : 1.05],
                title: { text: blockNormalize ? 'Power (%)' : 'Power (MW)' },
              },
            }
          }
          isLoading={data.isLoading}
          error={data.error}
        />
      </CustomCard>
      <CustomCard
        title="PCS Output Distribution"
        style={{ height: '250px' }}
        info="This plot shows the power output of each PCS. Clicking the 'Normalize by DC Input' button will equalize the performance of each inverter against its installed DC capacity, which is useful since installed capacity is often different per equipment. Look for large differences in performance between equipment to narrow down possible issues."
        headerChildren={
          <Checkbox
            label="Normalize by DC Input"
            value={pcsNormalize ? 'true' : 'false'}
            onChange={(event) => setPcsNormalize(event.currentTarget.checked)}
          />
        }
      >
        <PlotlyPlot
          data={
            data.data && [
              {
                x: pcsData?.x,
                y: pcsData?.y[dataLength && dataLength > 1 ? sliderValue : 0],
                customdata: pcsData?.customdata,
                type: 'bar',
              },
            ]
          }
          layout={
            data.data && {
              xaxis: { type: 'category', title: { text: 'PCS' } },
              yaxis: {
                range: [0, pcsData ? pcsData.yaxis_range_max * 1.05 : 1.05],
                title: { text: pcsNormalize ? 'Power (%)' : 'Power (MW)' },
              },
            }
          }
          isLoading={data.isLoading}
          error={data.error}
        />
      </CustomCard>
      {hasPCSModules && (
        <CustomCard
          title="PCS Module Output Distribution"
          style={{ height: '250px' }}
        >
          <PlotlyPlot
            data={
              data.data && [
                {
                  x: data.data.pcs_module_power_distribution?.x,
                  y: data.data.pcs_module_power_distribution?.y[
                    dataLength && dataLength > 1 ? sliderValue : 0
                  ],
                  customdata:
                    data.data.pcs_module_power_distribution?.customdata,
                  type: 'bar',
                },
              ]
            }
            layout={
              data.data && {
                xaxis: { type: 'category', title: { text: 'PCS Module' } },
                yaxis: {
                  range: [
                    0,
                    (data.data.pcs_module_power_distribution?.yaxis_range_max ??
                      1) * 1.05,
                  ],
                  title: { text: 'Power (MW)' },
                },
              }
            }
            isLoading={data.isLoading}
            error={data.error}
          />
        </CustomCard>
      )}
      <CustomCard
        title={
          'PCS Power Heatmap' +
          (dataLength && dataLength > 1 ? '' : ' (Last 24 hours)')
        }
        style={{ height: '500px' }}
        info="This plot shows the power output of each PCS over time. Look for large differences in performance between equipment to narrow down possible issues."
      >
        <PCSHeatmap startQuery={startQuery} endQuery={endQuery} />
      </CustomCard>
    </Stack>
  )
}

export default PCSEquipmentAnalysis
