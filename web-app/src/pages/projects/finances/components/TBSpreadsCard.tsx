import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetPTPData } from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import {
  Box,
  Group,
  SegmentedControl,
  Skeleton,
  Stack,
  Table,
  Tabs,
  Text,
  Tooltip,
  useMantineTheme,
} from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type { Data, Layout } from 'plotly.js'
import { useEffect, useMemo, useState } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)

type HighlightInterval = { start: string; end: string }

type TBRow = {
  tb: string
  spread: number | null
  increment: number | null
  intervals: HighlightInterval[]
  note?: string
}

interface TBSpreadsCardProps {
  projectId: string
  projectTimeZone?: string | null
  onHighlightIntervalsChange?: (intervals: HighlightInterval[] | null) => void
}

type HourlyPricePoint = {
  start: dayjs.Dayjs
  end: dayjs.Dayjs
  value: number
}

const formatDollars = (value: number) => {
  const rounded = Math.round(value)
  return `$${rounded.toLocaleString('en-US')}`
}

const buildHighlightIntervals = (points: HourlyPricePoint[]) => {
  return points.map((p) => ({
    start: p.start.format(),
    end: p.end.format(),
  }))
}

const computeTB = (points: HourlyPricePoint[], n: number) => {
  if (points.length === 0) {
    return {
      spread: null as number | null,
      increment: null as number | null,
      intervals: [] as HighlightInterval[],
    }
  }

  const nInt = Math.max(1, Math.floor(n))
  const sorted = [...points].sort((a, b) => {
    if (a.value !== b.value) return a.value - b.value
    return a.start.valueOf() - b.start.valueOf()
  })

  const bottom = sorted.slice(0, Math.min(nInt, sorted.length))
  const top = sorted.slice(Math.max(sorted.length - nInt, 0))

  const bottomSum = bottom.reduce((acc, p) => acc + p.value, 0)
  const topSum = top.reduce((acc, p) => acc + p.value, 0)
  const spread = topSum - bottomSum

  const prevN = Math.max(0, nInt - 1)
  const increment =
    prevN === 0
      ? spread
      : (() => {
          const bottomPrev = sorted.slice(0, Math.min(prevN, sorted.length))
          const topPrev = sorted.slice(Math.max(sorted.length - prevN, 0))
          const bottomPrevSum = bottomPrev.reduce((acc, p) => acc + p.value, 0)
          const topPrevSum = topPrev.reduce((acc, p) => acc + p.value, 0)
          return spread - (topPrevSum - bottomPrevSum)
        })()

  return {
    spread,
    increment,
    intervals: [
      ...buildHighlightIntervals(top),
      ...buildHighlightIntervals(bottom),
    ],
  }
}

export const TBSpreadsCard = ({
  projectId,
  projectTimeZone,
  onHighlightIntervalsChange,
}: TBSpreadsCardProps) => {
  const theme = useMantineTheme()
  const project = useSelectProject(projectId)

  const STORAGE_KEY = 'tb-spreads-units'
  const [units, setUnits] = useState<'per_mw' | 'total'>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored === 'total' ? 'total' : 'per_mw'
    } catch {
      return 'per_mw'
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, units)
    } catch {
      // ignore
    }
  }, [units])

  const { start, end, dayStarts } = useMemo(() => {
    if (!projectTimeZone) {
      return {
        start: undefined,
        end: undefined,
        dayStarts: [] as dayjs.Dayjs[],
      }
    }

    const now = dayjs().tz(projectTimeZone)
    const todayStart = now.startOf('day')
    const yesterdayStart = todayStart.subtract(1, 'day')
    const dayBeforeYesterdayStart = todayStart.subtract(2, 'day')

    return {
      start: dayBeforeYesterdayStart.toISOString(),
      end: todayStart.toISOString(),
      dayStarts: [dayBeforeYesterdayStart, yesterdayStart],
    }
  }, [projectTimeZone])

  const { data: marketPricesData, isLoading } = useGetPTPData({
    pathParams: { projectId },
    queryParams: {
      endpoint: 'Market-Prices',
      category: 'market',
      start,
      end,
    },
    queryOptions: {
      enabled: !!projectId && !!projectTimeZone && !!start && !!end,
    },
  })

  const { data: powerData, isLoading: powerLoading } = useGetPTPData({
    pathParams: { projectId },
    queryParams: {
      endpoint: 'Real-Time-Unit-Position',
      category: 'analysis',
      start,
      end,
    },
    queryOptions: {
      enabled: !!projectId && !!projectTimeZone && !!start && !!end,
    },
  })

  const dayData = useMemo(() => {
    if (!projectTimeZone || dayStarts.length !== 2) return []

    const projectEnergyMWh = project.data?.capacity_bess_energy_bol_dc ?? null
    const projectPowerMW = project.data?.capacity_bess_power_ac ?? null
    const durationHours =
      projectEnergyMWh && projectPowerMW && projectPowerMW > 0
        ? projectEnergyMWh / projectPowerMW
        : null
    const durationLabel =
      durationHours === null
        ? null
        : (() => {
            const rounded = Math.round(durationHours)
            const isInt = Math.abs(durationHours - rounded) < 1e-6
            if (isInt) return `${rounded}.0`
            if (durationHours < 10) return durationHours.toFixed(1)
            return Math.round(durationHours).toString()
          })()

    const element =
      marketPricesData?.data?.find((el) =>
        el.dataPoints?.some((dp) => dp.keyName === 'RTSPP'),
      ) ?? marketPricesData?.data?.[0]

    const rt = element?.dataPoints?.find((dp) => dp.keyName === 'RTSPP')

    // RTSPP comes in 15-min intervals. We compute an hourly average per hour
    // (simple mean; intervals are equal duration).
    const hourToValues = new Map<string, number[]>()
    ;(rt?.values ?? []).forEach((v) => {
      const value = v.data?.[0]?.value
      if (value === null || value === undefined) return

      const startTz = dayjs.utc(v.intervalStartUtc).tz(projectTimeZone)
      const hourKey = startTz.startOf('hour').format()
      const existing = hourToValues.get(hourKey) ?? []
      existing.push(value)
      hourToValues.set(hourKey, existing)
    })

    const hourly: HourlyPricePoint[] = Array.from(hourToValues.entries()).map(
      ([hourKey, values]) => {
        const start = dayjs(hourKey).tz(projectTimeZone)
        const end = start.add(1, 'hour')
        const avg =
          values.length === 0
            ? 0
            : values.reduce((acc, v) => acc + v, 0) / values.length
        return { start, end, value: avg }
      },
    )

    const rtIntervals = (rt?.values ?? [])
      .map((v) => {
        const price = v.data?.[0]?.value
        if (price === null || price === undefined) return null
        if (!v.intervalStartUtc || !v.intervalEndUtc) return null
        const startUtc = dayjs.utc(v.intervalStartUtc)
        const endUtc = dayjs.utc(v.intervalEndUtc)
        const startTz = startUtc.tz(projectTimeZone)
        return {
          startUtc,
          endUtc,
          startUtcKey: v.intervalStartUtc,
          startTz,
          price,
        }
      })
      .filter(
        (
          x,
        ): x is {
          startUtc: dayjs.Dayjs
          endUtc: dayjs.Dayjs
          startUtcKey: string
          startTz: dayjs.Dayjs
          price: number
        } => !!x,
      )

    const powerElement =
      powerData?.data?.find(
        (el) =>
          el.definition === 'Generator' &&
          el.dataPoints?.some((dp) => dp.keyName === 'GEN_Production'),
      ) ?? powerData?.data?.[0]
    const gen = powerElement?.dataPoints?.find(
      (dp) => dp.keyName === 'GEN_Production',
    )

    const powerByStartUtc = new Map<string, number>()
    ;(gen?.values ?? []).forEach((v) => {
      const power = v.data?.[0]?.value
      if (power === null || power === undefined) return
      powerByStartUtc.set(v.intervalStartUtc, power)
    })

    const byDay = dayStarts.map((dayStart) => {
      const dayEnd = dayStart.add(1, 'day')
      const points = hourly.filter(
        (p) =>
          (p.start.isAfter(dayStart) || p.start.isSame(dayStart)) &&
          p.start.isBefore(dayEnd),
      )

      const tb1 = computeTB(points, 1)
      const tb2 = computeTB(points, 2)
      const tb3 = computeTB(points, 3)
      const tb4 = computeTB(points, 4)

      const tbX =
        durationHours !== null && durationHours >= 1
          ? (() => {
              const floorN = Math.max(1, Math.floor(durationHours))
              const ceilN = Math.max(1, Math.ceil(durationHours))

              const tbFloor = computeTB(points, floorN)
              const tbCeil = computeTB(points, ceilN)

              if (tbFloor.spread === null || tbCeil.spread === null) {
                return { spread: null as number | null, intervals: [] }
              }

              if (floorN === ceilN) {
                return { spread: tbFloor.spread, intervals: tbFloor.intervals }
              }

              const frac = durationHours - floorN
              const spread =
                tbFloor.spread + frac * (tbCeil.spread - tbFloor.spread)

              // For highlighting, use the full-hour set (ceil).
              return { spread, intervals: tbCeil.intervals }
            })()
          : null

      const achievedRtRevenue = (() => {
        // Sum over the day: (power MW * interval hours) * RTSPP ($/MWh)
        let total = 0
        rtIntervals.forEach((interval) => {
          if (
            interval.startTz.isBefore(dayStart) ||
            interval.startTz.isAfter(dayEnd)
          ) {
            return
          }

          const power = powerByStartUtc.get(interval.startUtcKey)
          if (power === undefined) return

          const hours = interval.endUtc.diff(interval.startUtc, 'minute') / 60.0
          if (!Number.isFinite(hours) || hours <= 0) return

          total += power * hours * interval.price
        })
        return total
      })()

      return {
        dayStart,
        label: dayStart.format('MMM D'),
        achievedRtRevenue,
        rows: [
          { tb: 'TB1', ...tb1 },
          { tb: 'TB2', ...tb2 },
          { tb: 'TB3', ...tb3 },
          { tb: 'TB4', ...tb4 },
          ...(tbX && durationLabel
            ? [
                {
                  tb: `TB${durationLabel}`,
                  spread: tbX.spread,
                  increment: null,
                  intervals: tbX.intervals,
                  note: 'Project duration',
                },
              ]
            : []),
        ] satisfies TBRow[],
      }
    })

    return byDay
  }, [dayStarts, marketPricesData, powerData, project.data, projectTimeZone])

  const highlightFill = useMemo(() => {
    const hex =
      theme.colors[theme.primaryColor]?.[6] ??
      theme.colors.blue?.[6] ??
      '#228be6'
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `rgba(${r}, ${g}, ${b}, 0.15)`
  }, [theme])

  const powerMW = project.data?.capacity_bess_power_ac ?? null
  const multiplier = units === 'total' ? powerMW : 1

  return (
    <CustomCard
      title="TB Spreads"
      headerChildren={
        <SegmentedControl
          size="xs"
          value={units}
          onChange={(value) => setUnits(value as 'per_mw' | 'total')}
          data={[
            { label: '$/MW', value: 'per_mw' },
            { label: '$', value: 'total' },
          ]}
        />
      }
      info={
        <Text size="sm">
          TB spreads benchmark daily arbitrage opportunity.
          <br />
          TB1 = max hourly price − min hourly price.
          <br />
          TB4 = sum(4 highest hours) − sum(4 lowest hours).
          <br />
          Here we use RTSPP averaged to hourly.
          <br />
          {(() => {
            const energy = project.data?.capacity_bess_energy_bol_dc ?? null
            const power = project.data?.capacity_bess_power_ac ?? null
            if (!energy || !power || power <= 0) {
              return 'TBX uses X = BOL energy (MWh) / BOL power (MW).'
            }
            const x = energy / power
            const rounded = Math.round(x)
            const isInt = Math.abs(x - rounded) < 1e-6
            const xLabel = isInt ? `${rounded}.0` : x.toFixed(x < 10 ? 1 : 0)
            return `TB${xLabel} uses X = BOL energy (MWh) / BOL power (MW).`
          })()}
        </Text>
      }
      style={{ height: '100%' }}
      allowFullscreen={false}
    >
      {isLoading || powerLoading ? (
        <Skeleton height={600} radius="md" />
      ) : dayData.length === 0 ? (
        <Text c="dimmed" ta="center" py="xl">
          No data available.
        </Text>
      ) : (
        <Tabs
          defaultValue={dayData[1]?.label ?? dayData[0]!.label}
          keepMounted={false}
        >
          <Tabs.List grow>
            {dayData.map((d) => (
              <Tabs.Tab key={d.label} value={d.label}>
                {d.label}
              </Tabs.Tab>
            ))}
          </Tabs.List>

          {dayData.map((d) => (
            <Tabs.Panel
              key={d.label}
              value={d.label}
              pt="md"
              onMouseLeave={() => onHighlightIntervalsChange?.(null)}
            >
              <Box mb="md">
                <PlotlyPlot
                  data={((): Data[] => {
                    const x = d.rows.map((r) => r.tb)
                    const barY = d.rows.map((r) => {
                      if (r.spread === null || multiplier === null) return null
                      return r.spread * multiplier
                    })

                    const tbDurationRow = d.rows.find(
                      (r) => r.note === 'Project duration',
                    )
                    const achieved =
                      units === 'per_mw'
                        ? powerMW
                          ? d.achievedRtRevenue / powerMW
                          : null
                        : d.achievedRtRevenue

                    const traces: Data[] = [
                      {
                        x,
                        y: barY,
                        type: 'bar',
                        name: units === 'per_mw' ? 'TB ($/MW)' : 'TB ($)',
                        marker: { color: theme.colors.orange[6] },
                        hovertemplate:
                          units === 'per_mw'
                            ? '%{x}<br>%{y:$,.0f}/MW<extra></extra>'
                            : '%{x}<br>%{y:$,.0f}<extra></extra>',
                      },
                    ]

                    if (
                      tbDurationRow &&
                      achieved !== null &&
                      Number.isFinite(achieved)
                    ) {
                      traces.push({
                        x: [tbDurationRow.tb],
                        y: [achieved],
                        type: 'bar',
                        name:
                          units === 'per_mw'
                            ? 'Realized Arbitrage ($/MW)'
                            : 'Realized Arbitrage ($)',
                        marker: { color: theme.colors.green[6] },
                        width: 0.35, // narrow "nested" bar
                        hovertemplate:
                          units === 'per_mw'
                            ? 'Realized Arbitrage<br>%{y:$,.0f}/MW<extra></extra>'
                            : 'Realized Arbitrage<br>%{y:$,.0f}<extra></extra>',
                      })
                    }

                    return traces
                  })()}
                  layout={
                    {
                      height: 210,
                      margin: { l: 40, r: 10, t: 10, b: 40 },
                      barmode: 'overlay',
                      showlegend: false,
                      xaxis: { type: 'category' },
                      yaxis: {
                        title: {
                          text:
                            units === 'per_mw' ? 'Spread ($/MW)' : 'Spread ($)',
                        },
                        tickprefix: '$',
                      },
                      plot_bgcolor: 'transparent',
                      paper_bgcolor: 'transparent',
                    } satisfies Partial<Layout>
                  }
                  config={{ displayModeBar: false }}
                  onHover={(e) => {
                    const xVal = e.points?.[0]?.x
                    const tb = typeof xVal === 'string' ? xVal : String(xVal)
                    const row = d.rows.find((r) => r.tb === tb)
                    if (row) {
                      onHighlightIntervalsChange?.(row.intervals)
                    }
                  }}
                  isLoading={false}
                  error={null}
                />
              </Box>
              <Table
                striped
                highlightOnHover
                withRowBorders
                verticalSpacing="sm"
              >
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>TB#</Table.Th>
                    <Table.Th>Spread</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {d.rows.map((row) => {
                    const spread =
                      row.spread === null || multiplier === null
                        ? null
                        : row.spread * multiplier
                    return (
                      <Table.Tr
                        key={row.tb}
                        onMouseEnter={() =>
                          onHighlightIntervalsChange?.(row.intervals)
                        }
                        style={{ cursor: 'pointer' }}
                      >
                        <Table.Td>
                          <Text fw={600} size="sm">
                            {row.tb}
                          </Text>
                          {row.note && (
                            <Text size="xs" c="dimmed">
                              {String(row.note)}
                            </Text>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs" wrap="nowrap">
                            <Text fw={600} size="sm">
                              {spread === null
                                ? 'N/A'
                                : units === 'per_mw'
                                  ? `${formatDollars(spread)}/MW`
                                  : formatDollars(spread)}
                            </Text>
                          </Group>
                          {/* Subtle legend hint for highlight color */}
                          <Box
                            mt={6}
                            style={{
                              height: 6,
                              borderRadius: 999,
                              background: highlightFill,
                            }}
                          />
                        </Table.Td>
                      </Table.Tr>
                    )
                  })}
                </Table.Tbody>
              </Table>
              <Stack gap={4} mt="md">
                <Group gap={6} align="center">
                  <Text size="xs" c="dimmed" fw={600}>
                    Realized Arbitrage
                  </Text>
                  <Tooltip
                    withArrow
                    label="Computed as RT SPP × delivered energy (metered). Excludes any Virtuals bidding."
                  >
                    <Box
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        cursor: 'help',
                      }}
                    >
                      <IconInfoCircle size={14} />
                    </Box>
                  </Tooltip>
                </Group>
                {(() => {
                  const value =
                    units === 'per_mw'
                      ? powerMW
                        ? d.achievedRtRevenue / powerMW
                        : null
                      : d.achievedRtRevenue

                  const tbxRow = d.rows.find(
                    (r) => r.note === 'Project duration',
                  )
                  const tbx =
                    units === 'per_mw'
                      ? (tbxRow?.spread ?? null)
                      : powerMW && tbxRow?.spread != null
                        ? tbxRow.spread * powerMW
                        : null

                  const pct =
                    value != null &&
                    tbx != null &&
                    Number.isFinite(value) &&
                    Number.isFinite(tbx) &&
                    tbx !== 0
                      ? (value / tbx) * 100
                      : null

                  const valueText =
                    value != null && Number.isFinite(value)
                      ? units === 'per_mw'
                        ? `${formatDollars(value)}/MW`
                        : formatDollars(value)
                      : 'N/A'

                  const pctText =
                    pct != null && Number.isFinite(pct)
                      ? `${pct.toFixed(0)}% of ${tbxRow?.tb ?? 'TB'}`
                      : null

                  return (
                    <Stack gap={2}>
                      <Text fz={24} fw={700}>
                        {valueText}
                      </Text>
                      {pctText && (
                        <Text size="xs" c="dimmed">
                          {pctText}
                        </Text>
                      )}
                    </Stack>
                  )
                })()}
              </Stack>
            </Tabs.Panel>
          ))}
        </Tabs>
      )}
    </CustomCard>
  )
}
