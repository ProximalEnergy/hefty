import CustomCard, { iconSize, iconStroke } from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetClearskyPOA } from '@/hooks/api'
import { DataTimeSeries } from '@/hooks/types'
import {
  ActionIcon,
  Box,
  Button,
  Checkbox,
  Group,
  HoverCard,
  Modal,
  Popover,
  Select,
  Slider,
  Stack,
  Text,
} from '@mantine/core'
import { DateInput } from '@mantine/dates'
import { IconInfoCircle, IconSettings } from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezonePlugin from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { Layout, Shape } from 'plotly.js'
import React, { useEffect, useMemo } from 'react'

dayjs.extend(utc)
dayjs.extend(timezonePlugin)

interface ClearskyFilterProps {
  date: dayjs.Dayjs
  setDate: React.Dispatch<React.SetStateAction<dayjs.Dayjs | undefined>>
  minPOA: number
  setMinPOA: React.Dispatch<React.SetStateAction<number>>
  maxPOA1stDerivative: number
  setMaxPOA1stDerivative: React.Dispatch<React.SetStateAction<number>>
  maxPOA1stDerivativeStd: number
  setMaxPOA1stDerivativeStd: React.Dispatch<React.SetStateAction<number>>
  handleGenerateData: () => void
  timezone: string | undefined
  projectId: string
  usePOA1d: boolean
  setUsePOA1d: React.Dispatch<React.SetStateAction<boolean>>
  usePOA1dStd: boolean
  setUsePOA1dStd: React.Dispatch<React.SetStateAction<boolean>>
  resampleRate: string
  setResampleRate: React.Dispatch<React.SetStateAction<string>>
}

const ClearskyFilter: React.FC<ClearskyFilterProps> = ({
  date,
  setDate,
  minPOA,
  setMinPOA,
  maxPOA1stDerivative,
  setMaxPOA1stDerivative,
  maxPOA1stDerivativeStd,
  setMaxPOA1stDerivativeStd,
  handleGenerateData,
  timezone,
  projectId,
  usePOA1d,
  usePOA1dStd,
  setUsePOA1d,
  setUsePOA1dStd,
  resampleRate,
  setResampleRate,
}) => {
  const {
    data: poaData,
    isLoading: poaDataLoading,
    error: poaDataError,
    refetch,
  } = useGetClearskyPOA({
    pathParams: { projectId: projectId || '' },
    queryParams: {
      start: date?.toISOString() ?? '',
      end: date?.add(1, 'day').toISOString() ?? '',
      resample_rate: resampleRate,
    },
    queryOptions: {
      enabled: !!date && !!timezone,
    },
  })

  const {
    data: plotData,
    layout,
    validPoints,
  } = useMemo(() => {
    return processPoaData(
      poaData || [],
      maxPOA1stDerivative,
      minPOA,
      maxPOA1stDerivativeStd,
      timezone || '',
      usePOA1d,
      usePOA1dStd,
      resampleRate,
    )
  }, [
    poaData,
    maxPOA1stDerivative,
    minPOA,
    maxPOA1stDerivativeStd,
    timezone,
    usePOA1d,
    usePOA1dStd,
    resampleRate,
  ])

  const [confirmModalOpen, setConfirmModalOpen] = React.useState(false)
  const [confirmStdModalOpen, setConfirmStdModalOpen] = React.useState(false)

  const handlePOA1dChange = (checked: boolean) => {
    if (!checked) {
      setConfirmModalOpen(true)
    } else {
      setUsePOA1d(true)
    }
  }

  const handlePOA1dStdChange = (checked: boolean) => {
    if (!checked) {
      setConfirmStdModalOpen(true)
    } else {
      setUsePOA1dStd(true)
    }
  }

  useEffect(() => {
    refetch()
  }, [resampleRate])

  return (
    <>
      <Modal
        opened={confirmModalOpen}
        onClose={() => setConfirmModalOpen(false)}
        title="Disable Max POA Derivative Filter"
        centered
      >
        <Text size="sm">
          Are you sure you want to disable the Max POA Derivative filter? This
          may lead to less accurate results.
        </Text>

        <Group justify="flex-end" mt="lg">
          <Button variant="default" onClick={() => setConfirmModalOpen(false)}>
            Cancel
          </Button>
          <Button
            color="red"
            onClick={() => {
              setUsePOA1d(false)
              setConfirmModalOpen(false)
            }}
          >
            Disable
          </Button>
        </Group>
      </Modal>

      <Modal
        opened={confirmStdModalOpen}
        onClose={() => setConfirmStdModalOpen(false)}
        title="Disable Max POA Derivative Std Dev Filter"
        centered
      >
        <Text size="sm">
          Are you sure you want to disable the Max POA Derivative Std Dev
          filter? This may lead to less accurate results.
        </Text>

        <Group justify="flex-end" mt="lg">
          <Button
            variant="default"
            onClick={() => setConfirmStdModalOpen(false)}
          >
            Cancel
          </Button>
          <Button
            color="red"
            onClick={() => {
              setUsePOA1dStd(false)
              setConfirmStdModalOpen(false)
            }}
          >
            Disable
          </Button>
        </Group>
      </Modal>

      <Group grow align="stretch">
        <CustomCard
          title="Clearsky Filter Options"
          headerChildren={
            <Popover>
              <Popover.Target>
                <ActionIcon variant="default">
                  <IconSettings size={iconSize} stroke={iconStroke} />
                </ActionIcon>
              </Popover.Target>
              <Popover.Dropdown>
                <Text size="sm">Sample Rate</Text>
                <Select
                  data={['5min', '10min', '15min', '30min', '60min']}
                  value={resampleRate}
                  onChange={(value) => setResampleRate(value || '')}
                />
              </Popover.Dropdown>
            </Popover>
          }
        >
          <Stack gap="xs">
            <Group>
              <Text size="sm" flex={1.25}>
                Date
              </Text>
              <DateInput
                flex={1}
                // NOTE: READ THE FOLLOWING IF DEBUGGING OFF BY ONE ERROR
                // `date` represents the point in time localized to the project timezone.
                // `date.toDate()` represents the point in time in the user's local timezone.
                // The toDate() point in time MAY OR MAY NOT be the same "date" (.i.e calendar date)
                // as the `date` point in time. Passing .tz(..., true) ensures that the point in time
                // is the same "date" as the `date` point in time.
                value={date.tz(dayjs.tz.guess(), true).toDate()}
                onChange={(date) =>
                  date && setDate(dayjs(date).tz(timezone, true))
                }
                maxDate={dayjs()
                  .tz(timezone)
                  .startOf('day')
                  .subtract(1, 'day')
                  .tz(dayjs.tz.guess(), true)
                  .toDate()}
              />
            </Group>
            <Group>
              <Text size="sm" flex={1.25}>
                Min POA
              </Text>
              <Box flex={1}>
                <Slider
                  value={minPOA}
                  onChange={setMinPOA}
                  min={0}
                  max={1000}
                  step={50}
                />
              </Box>
            </Group>
            <Group>
              <Group flex={1.25} gap="xs">
                <Checkbox
                  checked={usePOA1d}
                  onChange={(event) =>
                    handlePOA1dChange(event.currentTarget.checked)
                  }
                />
                <HoverCard position="right">
                  <HoverCard.Target>
                    <IconInfoCircle size="1.25rem" />
                  </HoverCard.Target>
                  <HoverCard.Dropdown w="25%">
                    Maximum allowed POA 1st derivative. Represents how quickly
                    the POA is changing. Lower values will remove periods with
                    sudden changes in POA. Recommended value of 1.
                  </HoverCard.Dropdown>
                </HoverCard>
                <Text size="sm">Max POA Derivative</Text>
              </Group>
              <Box flex={1}>
                <Slider
                  value={maxPOA1stDerivative}
                  onChange={setMaxPOA1stDerivative}
                  min={0}
                  max={10}
                  step={0.1}
                  disabled={!usePOA1d}
                />
              </Box>
            </Group>
            <Group>
              <Group flex={1.25} gap="xs">
                <Checkbox
                  checked={usePOA1dStd}
                  onChange={(event) =>
                    handlePOA1dStdChange(event.currentTarget.checked)
                  }
                />
                <HoverCard position="right">
                  <HoverCard.Target>
                    <IconInfoCircle size="1.25rem" />
                  </HoverCard.Target>
                  <HoverCard.Dropdown w="25%">
                    Maximum allowed standard deviation of the first derivative
                    of the POA. This value is a measure of the coherence of
                    meteorological stations in different locations onsite.
                    Recommended value of 1.
                  </HoverCard.Dropdown>
                </HoverCard>
                <Text size="sm">Max POA Derivative Std Dev</Text>
              </Group>
              <Box flex={1}>
                <Slider
                  value={maxPOA1stDerivativeStd}
                  onChange={setMaxPOA1stDerivativeStd}
                  min={0}
                  max={10}
                  step={0.1}
                  disabled={!usePOA1dStd}
                />
              </Box>
            </Group>
            <Button onClick={handleGenerateData} disabled={validPoints === 0}>
              {validPoints
                ? `Generate Data (${validPoints} points)`
                : 'No valid points'}
            </Button>
          </Stack>
        </CustomCard>

        <CustomCard title="Clearsky Filter Data">
          <div style={{ height: '100%', width: '100%' }}>
            <PlotlyPlot
              data={plotData}
              layout={layout}
              isLoading={poaDataLoading}
              error={poaDataError}
            />
          </div>
        </CustomCard>
      </Group>
    </>
  )
}

// Helper function
const processPoaData = (
  poaData: DataTimeSeries[],
  maxPOA1stDerivative: number,
  minPOA: number,
  maxPOA1stDerivativeStd: number,
  timezone: string,
  usePOA1d: boolean,
  usePOA1dStd: boolean,
  resampleRate: string,
): { data: DataTimeSeries[]; layout: Partial<Layout>; validPoints: number } => {
  let validPoints = 0
  if (!poaData) return { data: [], layout: {}, validPoints }

  const poa1dTrace = poaData.find((trace) => trace.name === 'POA 1D')
  // const poa2dTrace = poaData.find((trace) => trace.name === "POA 2D");
  const poa1dStdTrace = poaData.find((trace) => trace.name === 'POA 1D Std Dev')
  if (!poa1dTrace || !poa1dStdTrace)
    return { data: poaData, layout: {}, validPoints }

  const otherTraces = poaData.filter(
    (trace) => !['POA 1D', 'POA 1D Std Dev'].includes(trace.name),
  )

  const shapes: Partial<Shape>[] = []
  let currentShape: Partial<Shape> | null = null

  poa1dTrace.x.forEach((x: string | number, i: number) => {
    const y1d = poa1dTrace.y[i]
    // const y2d = poa2dTrace.y[i];
    const y1dStd = poa1dStdTrace.y[i]

    const meanOther =
      otherTraces.reduce((sum, trace) => sum + (trace.y[i] || 0), 0) /
      otherTraces.length

    const isValidPoint =
      (usePOA1d ? y1d != null : true) &&
      // y2d != null &&
      (usePOA1dStd ? y1dStd != null : true) &&
      (usePOA1d ? Math.abs(y1d) < maxPOA1stDerivative : true) &&
      (usePOA1dStd ? y1dStd < maxPOA1stDerivativeStd : true) &&
      meanOther > minPOA

    if (isValidPoint) {
      validPoints++
      if (!currentShape) {
        currentShape = {
          type: 'rect',
          xref: 'x',
          yref: 'paper',
          x0: x,
          y0: 0,
          x1: x,
          y1: 1,
          fillcolor: 'rgba(0, 255, 0, 0.2)',
          line: { width: 0 },
        }
      } else {
        currentShape.x1 = x
      }
    } else if (currentShape) {
      shapes.push(currentShape)
      currentShape = null
    }
  })

  if (currentShape) {
    shapes.push(currentShape)
  }
  const minOffset = Number(resampleRate.split('min')[0]) / 2

  // Adjust single-point shapes
  shapes.forEach((shape) => {
    if (shape.x0 === shape.x1) {
      const hourOffset = dayjs(shape.x0).tz(timezone).utcOffset() / 60
      const x0 = dayjs(shape.x0)
        .tz(timezone)
        .subtract(minOffset, 'minute')
        .add(hourOffset, 'hour')
        .toISOString()
      const x1 = dayjs(shape.x1)
        .tz(timezone)
        .add(minOffset, 'minute')
        .add(hourOffset, 'hour')
        .toISOString()
      shape.x0 = x0
      shape.x1 = x1
    }
  })

  const layout: Partial<Layout> = {
    shapes: shapes,
    showlegend: true,
    yaxis: {
      title: 'POA',
    },
    yaxis2: {
      title: 'Filters',
      showgrid: false,
      zeroline: false,
      side: 'right' as const,
      overlaying: 'y',
    },
  }

  return { data: poaData, layout, validPoints }
}

export default ClearskyFilter
