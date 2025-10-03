import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useGetProject } from '@/api/v1/operational/projects'
import { useGetMeterPowerAndExpectedPower } from '@/api/v1/protected/pv-expected-energy/plot/plot'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { DataTimeSeries, Quality } from '@/hooks/types'
import { getInterval, roundTime } from '@/utils/interval'
import {
  Button,
  Group,
  HoverCard,
  List,
  Menu,
  Space,
  Text,
  ThemeIcon,
  Tooltip,
  rem,
  useMantineTheme,
} from '@mantine/core'
import {
  IconArrowLeft,
  IconArrowRight,
  IconCaretDown,
  IconCheck,
  IconExclamationMark,
  IconLetterQ,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type * as Plotly from 'plotly.js'
// Import Plotly namespace for type assertion
import type { PlotRelayoutEvent } from 'plotly.js'
import { useState } from 'react'
import { useParams } from 'react-router-dom'

// Extend dayjs with timezone support
dayjs.extend(utc)
dayjs.extend(timezone)

const PowerPlotPVZoom = () => {
  const { projectId } = useParams()
  const theme = useMantineTheme()
  const [startTime, setStartTime] = useState<string>(
    dayjs()
      .minute(Math.floor(dayjs().minute() / 5) * 5)
      .second(0)
      .subtract(24, 'hours')
      .toISOString(),
  )
  const [endTime, setEndTime] = useState<string>(
    dayjs()
      .minute(Math.floor(dayjs().minute() / 5) * 5)
      .second(0)
      .toISOString(),
  )
  const [interval, setInterval] = useState<string>('5min')

  const handleDefaultView = () => {
    setEndTime(
      dayjs()
        .minute(Math.floor(dayjs().minute() / 5) * 5)
        .second(0)
        .toISOString(),
    )
    setStartTime(
      dayjs()
        .minute(Math.floor(dayjs().minute() / 5) * 5)
        .second(0)
        .subtract(24, 'hours')
        .toISOString(),
    )
    setInterval(getInterval(startTime, endTime))
  }

  const handleTimeRangeChange = (range: '48h' | '7d' | 'yesterday') => {
    let start = dayjs()
    const end = dayjs()

    if (range === '48h') {
      start = end.subtract(48, 'hours')
    } else if (range === '7d') {
      start = end.subtract(7, 'days')
    } else if (range === 'yesterday') {
      start = dayjs().subtract(1, 'day').startOf('day')
    }

    setStartTime(start.toISOString())
    setEndTime(end.toISOString())
    setInterval(getInterval(start.toISOString(), end.toISOString()))
  }

  // Color map based on the names returned by the specific hook
  const colorMap: Record<string, string> = {
    'Meter Active Power': theme.colors.green[7],
    'Expected Power': theme.colors.orange[7],
    'PPC Active Power Setpoint': theme.colors.blue[7], // Add setpoint color
    'PV Active Power': theme.colors.cyan[7], // Adjusted PV color for distinction
    'BESS Active Power': theme.colors.yellow[7],
  }

  const project = useGetProject({
    pathParams: { projectId: projectId || '-1' },
  })

  // TODO: Remove this in favor of a new database table.
  const includeSoiling = !['sigurd'].includes(project.data?.name_short || '')
  const includeDegradation = ['sigurd'].includes(project.data?.name_short || '')

  // Use the updated useGetMeterPowerAndExpectedPower hook
  const data = useGetMeterPowerAndExpectedPower({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      // Pass start and end times
      start: roundTime(startTime, interval, 'down'),
      end: roundTime(endTime, interval, 'up'),
      interval: interval,
      // Determine include_storage based on project type if needed
      include_storage: project.data?.project_type_id === ProjectTypeId.PV_BESS,
      // TODO: Replace 'false' with the correct condition based on project data
      include_setpoint: true, // Placeholder - set based on actual project properties
      include_soiling: includeSoiling,
      include_degradation: includeDegradation,
    },
    queryOptions: {
      enabled: !!project.data && !!startTime && !!endTime,
      refetchOnWindowFocus: false,
      staleTime: 60 * 1000, // 1 minute
    },
  })

  const handleRelayout = (event: Readonly<PlotRelayoutEvent>) => {
    const newStartTime = event['xaxis.range[0]']
    const newEndTime = event['xaxis.range[1]']

    if (newStartTime && newEndTime) {
      // Convert Plotly time values to proper ISO strings
      // Plotly returns time values as local time strings, but we need to interpret them as project timezone
      const projectTimezone = project.data?.time_zone || 'UTC'

      const newStartTimeStr =
        typeof newStartTime === 'number'
          ? new Date(newStartTime).toISOString()
          : dayjs.tz(String(newStartTime), projectTimezone).utc().toISOString()
      const newEndTimeStr =
        typeof newEndTime === 'number'
          ? new Date(newEndTime).toISOString()
          : dayjs.tz(String(newEndTime), projectTimezone).utc().toISOString()

      const currentStart = dayjs(startTime)
      const currentEnd = dayjs(endTime)
      const newStart = dayjs(newStartTimeStr)
      const newEnd = dayjs(newEndTimeStr)

      if (
        Math.abs(currentStart.diff(newStart, 'minute')) > 1 ||
        Math.abs(currentEnd.diff(newEnd, 'minute')) > 1
      ) {
        setStartTime(newStartTimeStr)
        setEndTime(newEndTimeStr)
        setInterval(getInterval(newStartTimeStr, newEndTimeStr))
      }
    }
  }

  const handlePan = (direction: 'left' | 'right') => {
    const range = dayjs(endTime).diff(dayjs(startTime), 'minute')
    const newStartTime =
      direction === 'left'
        ? dayjs(startTime).subtract(range, 'minute').toISOString()
        : dayjs(startTime).add(range, 'minute').toISOString()
    const newEndTime =
      direction === 'left'
        ? dayjs(endTime).subtract(range, 'minute').toISOString()
        : dayjs(endTime).add(range, 'minute').toISOString()
    setStartTime(newStartTime)
    setEndTime(newEndTime)
  }

  // Map data from the MeterPowerAndExpected type
  const plotData = data.data?.data.map((d: DataTimeSeries) => {
    const numericY = d.y.map((val: number | null) =>
      val === null ? null : parseFloat(String(val)),
    )

    // Determine mode and fill based on trace name
    const isMeterPower = d.name === 'Meter Active Power'
    const isSetpoint = d.name === 'PPC Active Power Setpoint'
    const isExpectedPower = d.name === 'Expected Power' // Check for Expected Power
    const mode =
      isMeterPower || isSetpoint || isExpectedPower ? 'lines' : 'lines+markers' // Set mode to lines for Meter, Setpoint, and Expected Power
    const fill = isMeterPower ? 'tozeroy' : 'none' // Only fill for meter

    return {
      x: d.x,
      y: numericY,
      name: d.name,
      type: 'scatter' as const,
      mode: mode, // Use determined mode
      connectgaps: isExpectedPower ? false : true,
      hoverlabel: {
        namelength: -1,
      },
      fill: fill, // Use determined fill
      line: {
        color:
          colorMap[d.name as keyof typeof colorMap] || theme.colors.gray[7],
        width: 2,
      },
      marker: {
        // Only show markers if mode includes them
        size: mode.includes('markers') ? 4 : 0,
        // Ensure setpoint markers are hidden even if mode logic changes
        opacity: isSetpoint ? 0 : 1,
      },
      visible: true,
    }
  }) as Partial<Plotly.Data>[] | undefined

  return (
    <CustomCard
      title="Meter Power"
      // Quality data might be available again at data.data.quality
      quality={
        data.data?.quality && <QualityCard quality={data.data.quality} />
      }
      style={{ flex: 2 }}
      headerChildren={
        <Group>
          <Tooltip label="Pan Left">
            <Button
              size="xs"
              variant="outline"
              onClick={() => handlePan('left')}
            >
              <IconArrowLeft />
            </Button>
          </Tooltip>
          <Button.Group>
            <Tooltip label="Reset to the last 24 hours. You can also zoom by scrolling.">
              <Button size="xs" variant="outline" onClick={handleDefaultView}>
                Last 24 Hours
              </Button>
            </Tooltip>
            <Menu>
              <Menu.Target>
                <Tooltip label="Select a time range">
                  <Button size="xs" variant="outline">
                    <IconCaretDown />
                  </Button>
                </Tooltip>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item onClick={() => handleTimeRangeChange('yesterday')}>
                  Yesterday
                </Menu.Item>
                <Menu.Item onClick={() => handleTimeRangeChange('48h')}>
                  Last 48 Hours
                </Menu.Item>
                <Menu.Item onClick={() => handleTimeRangeChange('7d')}>
                  Last 7 Days
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Button.Group>
          <Tooltip label="Pan Right">
            <Button
              size="xs"
              variant="outline"
              onClick={() => handlePan('right')}
            >
              <IconArrowRight />
            </Button>
          </Tooltip>
        </Group>
      }
    >
      <PlotlyPlot
        data={plotData}
        layout={
          project.data && {
            yaxis: {
              title: 'Power (MW)',
              fixedrange: true,
              // Restore explicit range
              range:
                project.data?.project_type_id === ProjectTypeId.PV_BESS
                  ? undefined
                  : [0, project.data.poi * 1.05],
            },
            xaxis: {
              type: 'date',
              fixedrange: false,
              tickangle: 0,
            },
          }
        }
        onRelayout={handleRelayout}
        // Use the loading state from the hook
        isLoading={data.isLoading || project.isLoading}
        error={data.error}
        config={{ responsive: true, scrollZoom: true }}
      />
    </CustomCard>
  )
}

function QualityCard({ quality }: { quality: Quality }) {
  const theme = useMantineTheme() // Need theme here too
  const colorMap = {
    good: theme.colors.green[7],
    warning: theme.colors.yellow[7],
    bad: theme.colors.red[7],
  }

  const iconMap = {
    good: <IconCheck style={{ width: rem(16), height: rem(16) }} />,
    warning: (
      <IconExclamationMark style={{ width: rem(16), height: rem(16) }} />
    ),
    bad: <IconExclamationMark style={{ width: rem(16), height: rem(16) }} />,
  }

  return (
    <HoverCard shadow="md">
      <HoverCard.Target>
        <ThemeIcon color={colorMap[quality.level]} size={20} radius="xl">
          <IconLetterQ style={{ width: rem(16), height: rem(16) }} />
        </ThemeIcon>
      </HoverCard.Target>
      <HoverCard.Dropdown>
        <Text>{quality.message}</Text>
        <Space h="xs" />
        <List spacing="xs" size="sm" center>
          {quality.details.map((detail, i) => (
            <List.Item
              key={i}
              icon={
                <ThemeIcon color={colorMap[detail.level]} size={20} radius="xl">
                  {iconMap[detail.level]}
                </ThemeIcon>
              }
            >
              {detail.message}
            </List.Item>
          ))}
        </List>
      </HoverCard.Dropdown>
    </HoverCard>
  )
}

export default PowerPlotPVZoom
