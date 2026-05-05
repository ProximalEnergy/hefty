import { useGetPTPData } from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import {
  ActionIcon,
  Box,
  Group,
  Skeleton,
  Slider,
  Stack,
  Text,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { Data, Layout } from 'plotly.js'
import { useMemo, useState } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)

interface ThreePartOfferCardProps {
  projectId: string
  projectTimeZone?: string | null
  startDate: Date | null
  endDate: Date | null
}

export const ThreePartOfferCard = ({
  projectId,
  projectTimeZone,
  startDate,
  endDate,
}: ThreePartOfferCardProps) => {
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('dark')
  const [selectedCurveIndexOverride, setSelectedCurveIndexOverride] = useState<
    number | null
  >(null)

  const { data: threePartOfferData, isLoading: threePartOfferLoading } =
    useGetPTPData({
      pathParams: { projectId },
      queryParams: {
        endpoint: 'Submissions-Three-Part-Offer-RT',
        category: 'submissions',
        start: startDate ? dayjs(startDate).toISOString() : undefined,
        end: endDate ? dayjs(endDate).toISOString() : undefined,
      },
      queryOptions: {
        enabled: !!projectId && !!startDate && !!endDate,
      },
    })

  // Extract available curve indices and timestamps
  const { availableCurveIndices, curveTimestamps } = useMemo(() => {
    if (!threePartOfferData?.data || threePartOfferData.data.length === 0) {
      return { availableCurveIndices: [], curveTimestamps: [] }
    }

    const element =
      threePartOfferData.data.find(
        (el) =>
          el.definition === 'Generator' ||
          el.definition === 'Generator Configuration',
      ) || threePartOfferData.data[0]

    if (!element) {
      return { availableCurveIndices: [], curveTimestamps: [] }
    }

    const pricesDp = element.dataPoints.find((dp) => dp.keyName === 'Prices')

    if (!pricesDp) {
      return { availableCurveIndices: [], curveTimestamps: [] }
    }

    const pricesValues = pricesDp.values.filter(
      (v) =>
        v.intervalStartUtc &&
        !v.intervalStartUtc.includes('1753') &&
        !v.intervalStartUtc.includes('9998'),
    )

    if (pricesValues.length === 0) {
      return { availableCurveIndices: [], curveTimestamps: [] }
    }

    const totalIntervals = pricesValues.length
    const sampleEvery = Math.max(1, Math.floor(totalIntervals / 12))
    const indicesToShow = new Set<number>()

    indicesToShow.add(totalIntervals - 1)

    for (let i = 0; i < totalIntervals; i += sampleEvery) {
      indicesToShow.add(i)
    }

    const sortedIndices = Array.from(indicesToShow).sort((a, b) => a - b)
    const timestamps = sortedIndices.map((idx) => {
      const priceInterval = pricesValues[idx]
      return dayjs
        .utc(priceInterval.intervalStartUtc)
        .tz(projectTimeZone || 'UTC')
    })

    // Check if we're showing all curves (sampleEvery === 1 means we're showing all)
    const isShowingAllCurves = sampleEvery === 1

    return {
      availableCurveIndices: sortedIndices,
      curveTimestamps: timestamps,
      isShowingAllCurves,
      totalIntervals,
    }
  }, [threePartOfferData, projectTimeZone])

  const selectedCurveIndex = useMemo(() => {
    if (availableCurveIndices.length === 0) {
      return null
    }

    const maxIndex = availableCurveIndices.length - 1
    if (
      selectedCurveIndexOverride !== null &&
      selectedCurveIndexOverride >= 0 &&
      selectedCurveIndexOverride <= maxIndex
    ) {
      return selectedCurveIndexOverride
    }

    if (curveTimestamps.length === 0) {
      return maxIndex
    }

    // Default: find first curve at or after now(), otherwise use latest
    const now = projectTimeZone ? dayjs().tz(projectTimeZone) : dayjs().utc()
    const nowValue = now.valueOf()
    const firstFutureIndex = curveTimestamps.findIndex(
      (timestamp) => timestamp.valueOf() >= nowValue,
    )

    return firstFutureIndex >= 0 ? firstFutureIndex : maxIndex
  }, [
    availableCurveIndices.length,
    curveTimestamps,
    projectTimeZone,
    selectedCurveIndexOverride,
  ])

  // Transform Three-Part Offer data for display - show multiple curves over time
  const threePartOfferCurveData: Data[] = useMemo(() => {
    if (!threePartOfferData?.data || threePartOfferData.data.length === 0) {
      return []
    }

    const element =
      threePartOfferData.data.find(
        (el) =>
          el.definition === 'Generator' ||
          el.definition === 'Generator Configuration',
      ) || threePartOfferData.data[0]

    if (!element) {
      return []
    }

    const pricesDp = element.dataPoints.find((dp) => dp.keyName === 'Prices')
    const mwsDp = element.dataPoints.find((dp) => dp.keyName === 'MWs')

    if (!pricesDp || !mwsDp) {
      return []
    }

    const pricesValues = pricesDp.values.filter(
      (v) =>
        v.intervalStartUtc &&
        !v.intervalStartUtc.includes('1753') &&
        !v.intervalStartUtc.includes('9998'),
    )
    const mwsValues = mwsDp.values.filter(
      (v) =>
        v.intervalStartUtc &&
        !v.intervalStartUtc.includes('1753') &&
        !v.intervalStartUtc.includes('9998'),
    )

    if (pricesValues.length === 0 || mwsValues.length === 0) {
      return []
    }

    const traces: Data[] = []
    const selectedIndex =
      selectedCurveIndex !== null &&
      selectedCurveIndex >= 0 &&
      selectedCurveIndex < availableCurveIndices.length
        ? availableCurveIndices[selectedCurveIndex]
        : availableCurveIndices[availableCurveIndices.length - 1]

    availableCurveIndices.forEach((idx) => {
      const priceInterval = pricesValues[idx]
      const mwInterval = mwsValues.find(
        (v) => v.intervalStartUtc === priceInterval.intervalStartUtc,
      )

      if (!mwInterval || !priceInterval.data || !mwInterval.data) {
        return
      }

      const priceMwPairs: Array<{
        price: number
        mw: number
        segment: number
      }> = []

      priceInterval.data.forEach((priceData) => {
        const priceDataWithCoords = priceData as {
          value: number | null
          coords?: { Segment?: string | number; segment?: string | number }
        }
        const segmentStr =
          priceDataWithCoords.coords?.Segment ??
          priceDataWithCoords.coords?.segment
        const segment =
          segmentStr !== undefined
            ? typeof segmentStr === 'number'
              ? segmentStr
              : parseInt(String(segmentStr), 10)
            : null

        if (
          segment !== null &&
          !isNaN(segment) &&
          typeof priceDataWithCoords.value === 'number'
        ) {
          const mwData = mwInterval.data.find((d) => {
            const dWithCoords = d as {
              value: number | null
              coords?: {
                Segment?: string | number
                segment?: string | number
              }
            }
            const dSegmentStr =
              dWithCoords.coords?.Segment ?? dWithCoords.coords?.segment
            const dSegment =
              dSegmentStr !== undefined
                ? typeof dSegmentStr === 'number'
                  ? dSegmentStr
                  : parseInt(String(dSegmentStr), 10)
                : null
            return dSegment === segment
          })
          if (mwData) {
            const mwDataWithCoords = mwData as {
              value: number | null
              coords?: {
                Segment?: string | number
                segment?: string | number
              }
            }
            if (typeof mwDataWithCoords.value === 'number') {
              priceMwPairs.push({
                price: priceDataWithCoords.value,
                mw: mwDataWithCoords.value,
                segment,
              })
            }
          }
        }
      })

      priceMwPairs.sort((a, b) => a.segment - b.segment)

      if (priceMwPairs.length === 0) {
        return
      }

      const timestamp = dayjs
        .utc(priceInterval.intervalStartUtc)
        .tz(projectTimeZone || 'UTC')
      const isSelected = idx === selectedIndex

      const x = priceMwPairs.map((p) => p.mw)
      const y = priceMwPairs.map((p) => p.price)

      traces.push({
        x,
        y,
        type: 'scatter',
        mode: 'lines+markers',
        name: timestamp.format('MMM D, h:mm A'),
        line: {
          width: isSelected ? 4 : 2,
          color: isSelected
            ? theme.colors?.blue?.[6] || '#228be6'
            : theme.colors?.gray?.[4] || '#868e96',
          shape: 'linear',
          dash: isSelected ? 'solid' : 'dot',
        },
        marker: {
          size: isSelected ? 10 : 6,
          color: isSelected
            ? theme.colors?.blue?.[6] || '#228be6'
            : theme.colors?.gray?.[4] || '#868e96',
          opacity: isSelected ? 1 : 0.6,
        },
        opacity: isSelected ? 1 : 0.5,
        hovertemplate:
          '<b>%{fullData.name}</b><br>' +
          'MW: %{x:.1f}<br>' +
          'Price: $%{y:.2f}/MWh<extra></extra>',
      } as Data)
    })

    return traces
  }, [
    threePartOfferData,
    theme,
    projectTimeZone,
    selectedCurveIndex,
    availableCurveIndices,
  ])

  // Extract current three-part offer stats
  const threePartOfferStats = useMemo(() => {
    if (!threePartOfferData?.data || threePartOfferData.data.length === 0) {
      return null
    }

    const element =
      threePartOfferData.data.find(
        (el) =>
          el.definition === 'Generator' ||
          el.definition === 'Generator Configuration',
      ) || threePartOfferData.data[0]

    if (!element) {
      return null
    }

    const getLatestValue = (keyName: string): number | null => {
      const dp = element.dataPoints.find((dp) => dp.keyName === keyName)
      if (!dp) return null

      const realValues = dp.values.filter(
        (v) =>
          v.intervalStartUtc &&
          !v.intervalStartUtc.includes('1753') &&
          !v.intervalStartUtc.includes('9998'),
      )

      if (realValues.length === 0) return null

      const latest = realValues[realValues.length - 1]
      const value = latest.data?.[0]?.value
      return typeof value === 'number' ? value : null
    }

    return {
      startupFIP: getLatestValue('Startup_FIP'),
      startupFOP: getLatestValue('Startup_FOP'),
      eocFIP: getLatestValue('EOC_FIP'),
      eocFOP: getLatestValue('EOC_FOP'),
      minEnergyCost: getLatestValue('Min_Energy_Cost'),
      hotStartupCost: getLatestValue('Hot_Startup_Cost'),
      coldStartupCost: getLatestValue('Cold_Startup_Cost'),
      intStartupCost: getLatestValue('Int_Startup_Cost'),
    }
  }, [threePartOfferData])

  const layout: Partial<Layout> = useMemo(
    () => ({
      xaxis: {
        title: { text: 'Quantity (MW)' },
        type: 'linear',
        zeroline: true,
        zerolinecolor: theme.colors?.gray?.[4] || '#868e96',
      },
      yaxis: {
        title: { text: 'Price ($/MWh)' },
        type: 'linear',
        zeroline: true,
        zerolinecolor: theme.colors?.gray?.[4] || '#868e96',
      },
      hovermode: 'closest',
      height: 500,
      legend: {
        orientation: 'h',
        x: 0.5,
        y: -0.15,
        xanchor: 'center',
        yanchor: 'top',
        font: { size: 10 },
      },
    }),
    [theme],
  )

  return (
    <CustomCard
      title={
        <Group gap="xs">
          <Text>Three-Part Offer (Real-Time)</Text>
          <Tooltip
            label="ERCOT Three-Part Offer includes: (1) Startup Costs, (2) Minimum Energy Cost, and (3) Energy Offer Curve showing price vs quantity"
            withArrow
          >
            <ActionIcon variant="subtle" size="sm">
              <IconInfoCircle size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>
      }
      style={{ marginBottom: 'var(--mantine-spacing-md)' }}
    >
      {threePartOfferLoading ? (
        <Skeleton height={500} radius="md" />
      ) : threePartOfferStats === null &&
        threePartOfferCurveData.length === 0 ? (
        <Text c="dimmed" ta="center" py="xl">
          No three-part offer data available. Make sure
          Submissions-Three-Part-Offer-RT data exists.
        </Text>
      ) : (
        <Stack gap="md">
          {/* Offer Stats */}
          {threePartOfferStats && (
            <Stack gap="xs">
              <Text fw={600} size="sm" c="dimmed">
                Current Offer Parameters
              </Text>
              <Group grow>
                {threePartOfferStats.startupFIP !== null && (
                  <div>
                    <Text size="xs" c="dimmed">
                      Startup FIP
                    </Text>
                    <Text fw={500}>
                      ${threePartOfferStats.startupFIP.toFixed(2)}/MWh
                    </Text>
                  </div>
                )}
                {threePartOfferStats.startupFOP !== null && (
                  <div>
                    <Text size="xs" c="dimmed">
                      Startup FOP
                    </Text>
                    <Text fw={500}>
                      {threePartOfferStats.startupFOP.toFixed(2)} MW
                    </Text>
                  </div>
                )}
                {threePartOfferStats.eocFIP !== null && (
                  <div>
                    <Text size="xs" c="dimmed">
                      EOC FIP
                    </Text>
                    <Text fw={500}>
                      ${threePartOfferStats.eocFIP.toFixed(2)}/MWh
                    </Text>
                  </div>
                )}
                {threePartOfferStats.eocFOP !== null && (
                  <div>
                    <Text size="xs" c="dimmed">
                      EOC FOP
                    </Text>
                    <Text fw={500}>
                      {threePartOfferStats.eocFOP.toFixed(2)} MW
                    </Text>
                  </div>
                )}
                {threePartOfferStats.minEnergyCost !== null && (
                  <div>
                    <Text size="xs" c="dimmed">
                      Min Energy Cost
                    </Text>
                    <Text fw={500}>
                      ${threePartOfferStats.minEnergyCost.toFixed(2)}/MWh
                    </Text>
                  </div>
                )}
              </Group>
              {(threePartOfferStats.hotStartupCost !== null ||
                threePartOfferStats.coldStartupCost !== null ||
                threePartOfferStats.intStartupCost !== null) && (
                <Group grow mt="xs">
                  {threePartOfferStats.hotStartupCost !== null && (
                    <div>
                      <Text size="xs" c="dimmed">
                        Hot Startup Cost
                      </Text>
                      <Text fw={500}>
                        ${threePartOfferStats.hotStartupCost.toFixed(2)}
                      </Text>
                    </div>
                  )}
                  {threePartOfferStats.coldStartupCost !== null && (
                    <div>
                      <Text size="xs" c="dimmed">
                        Cold Startup Cost
                      </Text>
                      <Text fw={500}>
                        ${threePartOfferStats.coldStartupCost.toFixed(2)}
                      </Text>
                    </div>
                  )}
                  {threePartOfferStats.intStartupCost !== null && (
                    <div>
                      <Text size="xs" c="dimmed">
                        Intermediate Startup Cost
                      </Text>
                      <Text fw={500}>
                        ${threePartOfferStats.intStartupCost.toFixed(2)}
                      </Text>
                    </div>
                  )}
                </Group>
              )}
            </Stack>
          )}

          {/* Energy Offer Curve Chart */}
          {threePartOfferCurveData.length > 0 && (
            <Stack gap="md">
              {/* Timeline Slider */}
              {availableCurveIndices.length > 1 && (
                <Box px="md" pt="xs" style={{ position: 'relative' }}>
                  <Stack gap="xs">
                    <Group justify="space-between" align="center">
                      <Text size="xs" c="dimmed">
                        {selectedCurveIndex !== null &&
                        selectedCurveIndex < curveTimestamps.length
                          ? curveTimestamps[selectedCurveIndex].format(
                              'MMM D, YYYY h:mm A',
                            )
                          : 'Select time'}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {availableCurveIndices.length} curves
                      </Text>
                    </Group>
                    <Box style={{ position: 'relative' }}>
                      <Slider
                        value={
                          selectedCurveIndex !== null
                            ? selectedCurveIndex
                            : availableCurveIndices.length - 1
                        }
                        onChange={(value) =>
                          setSelectedCurveIndexOverride(value)
                        }
                        min={0}
                        max={availableCurveIndices.length - 1}
                        step={1}
                        marks={curveTimestamps
                          .map((timestamp, index) => {
                            // Only show marks for first, middle, and last
                            if (
                              index === 0 ||
                              index ===
                                Math.floor(curveTimestamps.length / 2) ||
                              index === curveTimestamps.length - 1
                            ) {
                              return {
                                value: index,
                                label: timestamp.format('h:mm A'),
                              }
                            }
                            return null
                          })
                          .filter(
                            (mark): mark is { value: number; label: string } =>
                              mark !== null,
                          )}
                        label={(value) => {
                          if (value >= 0 && value < curveTimestamps.length) {
                            return curveTimestamps[value].format('h:mm A')
                          }
                          return ''
                        }}
                        size="md"
                        styles={{
                          markLabel: {
                            fontSize: '10px',
                            marginTop: '4px',
                          },
                          track: {
                            marginTop: '12px',
                            marginBottom: '12px',
                            height: '8px',
                          },
                          thumb: {
                            width: '20px',
                            height: '20px',
                          },
                        }}
                      />
                      {(() => {
                        // Find the index closest to now()
                        const now = projectTimeZone
                          ? dayjs().tz(projectTimeZone)
                          : dayjs().utc()
                        const nowValue = now.valueOf()

                        // Find closest timestamp index
                        let closestIndex = 0
                        let minDiff = Infinity
                        curveTimestamps.forEach((timestamp, index) => {
                          const diff = Math.abs(timestamp.valueOf() - nowValue)
                          if (diff < minDiff) {
                            minDiff = diff
                            closestIndex = index
                          }
                        })

                        // Calculate position percentage
                        const maxIndex = availableCurveIndices.length - 1
                        const positionPercent =
                          maxIndex > 0 ? (closestIndex / maxIndex) * 100 : 0

                        return (
                          <Box
                            style={{
                              position: 'absolute',
                              left: `${positionPercent}%`,
                              top: '16px', // Center on track: 12px (marginTop) + 4px (half of 8px track height) - 4px (half of 8px dot height)
                              transform: 'translateX(-50%)',
                              width: '8px',
                              height: '8px',
                              borderRadius: '50%',
                              backgroundColor: theme.colors.red[6],
                              border: `2px solid ${
                                computedColorScheme === 'dark'
                                  ? theme.colors.dark[7]
                                  : theme.white
                              }`,
                              zIndex: 10,
                              pointerEvents: 'none',
                            }}
                          />
                        )
                      })()}
                    </Box>
                  </Stack>
                </Box>
              )}
              <PlotlyPlot
                data={threePartOfferCurveData}
                layout={layout}
                isLoading={threePartOfferLoading}
                error={null}
              />
            </Stack>
          )}
        </Stack>
      )}
    </CustomCard>
  )
}
