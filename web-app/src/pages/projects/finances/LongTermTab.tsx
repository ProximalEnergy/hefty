import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetProjectIdentifiers } from '@/api/v1/protected/web-application/projects/financial/market_performance'
import { useGetPTPData } from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import CustomCard from '@/components/CustomCard'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import {
  type PTPAcronymMetadata,
  getAcronymMetadata,
} from '@/utils/ptpAcronyms'
import {
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
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import {
  Data,
  Layout,
  PlotMouseEvent,
} from 'plotly.js/dist/plotly-custom.min.js'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'

dayjs.extend(utc)
dayjs.extend(timezone)

/** Bar trace with base for stacking (valid in Plotly; not in @types/plotly.js Data). */
type StackedBarTrace = Data & { base?: number[] }

type SettlementChargesGroupId =
  | 'energy_charges'
  | 'ancillary_services'
  | 'penalties'
  | 'other'

const GROUP_ORDER: SettlementChargesGroupId[] = [
  'energy_charges',
  'ancillary_services',
  'penalties',
  'other',
]

const GROUP_META: Record<
  SettlementChargesGroupId,
  { title: string; description: string }
> = {
  energy_charges: {
    title: 'Energy Markets',
    description:
      'Day-ahead + real-time energy settlement amounts and related energy ' +
      'market charges/adjustments.',
  },
  ancillary_services: {
    title: 'Ancillary Services',
    description:
      'Ancillary service-related charges (e.g. LA*, RU/RD, RRS, NS, ECR, VSS).',
  },
  penalties: {
    title: 'Deviations',
    description:
      'Settlement point deviation and base point deviation charges for ' +
      'deviations from set points or base points (e.g. SPD*, BPD*).',
  },
  other: {
    title: 'Other',
    description:
      'Unclassified settlement charge fields returned by PTP (including named ' +
      'special charges like NERC_ERO / CRR_Auction_Cost).',
  },
}

/**
 * Map UI_Group from CSV to internal group ID.
 * Uses UI_Group from acronym metadata when available.
 */
function mapUIGroupToGroupId(
  uiGroup: string | null | undefined,
): SettlementChargesGroupId {
  if (!uiGroup) {
    return 'other'
  }

  // Map UI_Group values to internal group IDs
  switch (uiGroup) {
    case 'Energy':
      return 'energy_charges'
    case 'Ancillary Services':
      return 'ancillary_services'
    case 'Deviation & Imbalance':
    case 'Deviations & Imbalance': // Handle both spellings
      return 'penalties'
    default:
      // All other groups (Fees/Admin, RUC/Uplift, Congestion/CRR, etc.) go to 'other'
      return 'other'
  }
}

/**
 * Categorize a keyname into a settlement charges group.
 * Uses UI_Group from acronym metadata when available, falls back to
 * description-based categorization if UI_Group is not available.
 */
function groupForKeyName(
  keyName: string,
  metadata: PTPAcronymMetadata | null = null,
): SettlementChargesGroupId {
  // Special case: RTEIAMT (Real-Time Energy Imbalance) should be in energy_charges
  if (keyName.toUpperCase() === 'RTEIAMT') {
    return 'energy_charges'
  }

  // Prioritize UI_Group from CSV if available
  if (metadata?.uiGroup) {
    return mapUIGroupToGroupId(metadata.uiGroup)
  }

  // Fallback to description-based categorization if UI_Group not available
  const desc = metadata?.description.toLowerCase() ?? ''
  const keyNameUpper = keyName.toUpperCase()

  // Deviation charges - settlement point deviation and base point deviation
  if (
    keyNameUpper.includes('SPD') ||
    keyNameUpper.includes('BPD') ||
    desc.includes('settlement point deviation') ||
    desc.includes('base point deviation')
  ) {
    return 'penalties'
  }

  // Ancillary services
  const isAncillaryService =
    desc.includes('ancillary service') ||
    desc.includes('reserve service') ||
    desc.includes('regulation') ||
    desc.includes('non-spin') ||
    desc.includes('non spinning') ||
    desc.includes('responsive reserve') ||
    desc.includes('contingency reserve') ||
    desc.includes('black start') ||
    desc.includes('voltage support') ||
    desc.includes('procured capacity')

  if (isAncillaryService) {
    if (
      desc.includes('energy imbalance') &&
      !desc.includes('ancillary service imbalance')
    ) {
      // Fall through to energy check
    } else {
      return 'ancillary_services'
    }
  }

  // Energy market charges
  // Check keyName patterns for common energy-related acronyms
  // (for cases where metadata might be missing)
  // Patterns: DAEP*, DAES*, RTES*, RTEP* (but not DAECR*, RTECR* which are CRR/ancillary)
  const keyNameEnergyPatterns =
    (keyNameUpper.startsWith('DAEP') || // Day-Ahead Energy Payment
      keyNameUpper.startsWith('DAES') || // Day-Ahead Energy Settlement
      keyNameUpper.startsWith('RTES') || // Real-Time Energy Settlement (includes RTESOGSAMT)
      keyNameUpper.startsWith('RTEP')) && // Real-Time Energy Payment
    !keyNameUpper.includes('CR') && // Exclude CRR-related
    !keyNameUpper.includes('CRR') // Exclude CRR-related

  const isEnergyCharge =
    keyNameEnergyPatterns ||
    desc.includes('energy settlement') ||
    desc.includes('energy charge') ||
    desc.includes('energy payment') ||
    desc.includes('energy amount') || // Catch "Real-Time Energy Amount" like RTESOGSAMT
    (desc.includes('energy imbalance') &&
      !desc.includes('ancillary service imbalance')) ||
    desc.includes('market revenue energy') ||
    (desc.includes('day-ahead') && desc.includes('energy')) ||
    (desc.includes('real-time') && desc.includes('energy')) ||
    (desc.includes('realtime') && desc.includes('energy')) // Alternative spelling

  if (isEnergyCharge) {
    return 'energy_charges'
  }

  return 'other'
}

function parseNumberOrZero(value: unknown): number {
  if (value === null || value === undefined) {
    return 0
  }
  const parsed = typeof value === 'number' ? value : parseFloat(String(value))
  return Number.isFinite(parsed) ? parsed : 0
}

/**
 * Check if a keyname represents a deviation charge (SPD* or BPD*).
 * Deviation charges should be negated to show as negative values.
 */
function isDeviationCharge(keyName: string): boolean {
  const keyNameUpper = keyName.toUpperCase()
  return keyNameUpper.includes('SPD') || keyNameUpper.includes('BPD')
}

/**
 * Check if a keyname should be negated in the total revenue chart.
 * These keys appear to have opposite signs and need to be flipped.
 */
function shouldNegateForRevenueChart(keyName: string): boolean {
  const keyNameUpper = keyName.toUpperCase()
  return (
    keyNameUpper === 'DAEPAMT' ||
    keyNameUpper === 'DAESAMT' ||
    keyNameUpper === 'RTEIAMT'
  )
}

/**
 * Get the value for a key from a row.
 * Note: dailyRows already has deviation charges negated, so we just return the value as-is.
 */
function getValueForKey(row: DailyValue | undefined, keyName: string): number {
  const raw = row?.[keyName]
  return parseNumberOrZero(raw)
}

function formatCurrency(value: number): string {
  return `$${value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

interface LongTermTabProps {
  projectId: string
}

interface DailyValue {
  date: string
  [key: string]: string | number | null
}

export const LongTermTab = ({ projectId }: LongTermTabProps) => {
  const project = useSelectProject(projectId)
  const [searchParams, setSearchParams] = useSearchParams()
  const theme = useMantineTheme()

  // Get QSE parent identifier from database
  const { data: identifiersData, isLoading: identifiersLoading } =
    useGetProjectIdentifiers({
      pathParams: { projectId },
      queryOptions: {
        enabled: !!projectId,
      },
    })
  const parentIdentifier = identifiersData?.parent_identifier
  const [revenueViewModes, setRevenueViewModes] = useState<
    Record<SettlementChargesGroupId, 'cumulative' | 'grouped' | 'detailed'>
  >({
    energy_charges: 'detailed',
    ancillary_services: 'grouped',
    penalties: 'grouped',
    other: 'grouped',
  })
  const [totalRevenueViewMode, setTotalRevenueViewMode] = useState<
    'cumulative' | 'grouped' | 'detailed'
  >('grouped')

  // Handler to navigate to Week View tab with date range ±1 day around clicked date
  const handlePlotClick = useCallback(
    (event: Readonly<PlotMouseEvent>) => {
      if (!project.data?.time_zone || event.points.length === 0) {
        return
      }

      const clickedPoint = event.points[0]
      const clickedDate = clickedPoint.x

      // Extract date string (could be string or Date object)
      let dateStr: string
      if (typeof clickedDate === 'string') {
        dateStr = clickedDate
      } else if (clickedDate instanceof Date) {
        const tz = project.data.time_zone
        dateStr = dayjs(clickedDate).tz(tz).format('YYYY-MM-DD')
      } else if (Array.isArray(clickedDate) && clickedDate.length > 0) {
        dateStr = String(clickedDate[0])
      } else {
        return
      }

      // Parse the date in the project's timezone
      const tz = project.data.time_zone
      const clickedDay = dayjs.tz(dateStr, 'YYYY-MM-DD', tz).startOf('day')

      if (!clickedDay.isValid()) {
        return
      }

      // Calculate ±1 day range
      const startDate = clickedDay.subtract(1, 'day')
      const endDate = clickedDay.add(1, 'day')

      // Update search params to navigate to Week View tab
      const nextParams = new URLSearchParams(searchParams)
      nextParams.set('tab', 'week-view')
      nextParams.set('start', startDate.format('YYYY-MM-DD'))
      nextParams.set('end', endDate.format('YYYY-MM-DD'))
      setSearchParams(nextParams)
    },
    [project.data, searchParams, setSearchParams],
  )

  // Get selected dates from URL params
  const startParam = searchParams.get('ltStart')
  const endParam = searchParams.get('ltEnd')

  // Default date range: past 30 days (inclusive), ending today.
  useEffect(() => {
    if (!project.data?.time_zone) {
      return
    }
    if (startParam && endParam) {
      return
    }

    const tz = project.data.time_zone
    const end = dayjs().tz(tz).startOf('day')
    const start = end.subtract(29, 'day')

    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('ltStart', start.format('YYYY-MM-DD'))
    nextParams.set('ltEnd', end.format('YYYY-MM-DD'))
    setSearchParams(nextParams, { replace: true })
  }, [
    project.data?.time_zone,
    searchParams,
    setSearchParams,
    startParam,
    endParam,
  ])

  // Calculate date range for API query
  const { startDate, endDate } = useMemo(() => {
    if (!project.data?.time_zone) {
      return { startDate: null, endDate: null }
    }
    const tz = project.data.time_zone

    // Use selected dates or default
    if (!startParam || !endParam) {
      return { startDate: null, endDate: null }
    }

    // Parse date strings in the target timezone to avoid timezone shifts.
    const start = dayjs.tz(startParam, 'YYYY-MM-DD', tz).startOf('day').toDate()
    const end = dayjs.tz(endParam, 'YYYY-MM-DD', tz).endOf('day').toDate()

    return { startDate: start, endDate: end }
  }, [project.data?.time_zone, startParam, endParam])

  // Use Settlement-Charges only. It returns daily operating-day intervals.
  const { data: settlementChargesData, isLoading: settlementChargesLoading } =
    useGetPTPData({
      pathParams: { projectId },
      queryParams: {
        endpoint: 'Settlement-Charges',
        category: 'settlement',
        start: startDate ? dayjs(startDate).toISOString() : undefined,
        end: endDate ? dayjs(endDate).toISOString() : undefined,
        element_id: parentIdentifier,
      },
      queryOptions: {
        enabled: !!projectId && !!startDate && !!endDate && !!parentIdentifier,
      },
    })
  // Show skeleton while waiting for identifiers (settlement query is disabled
  // until parentIdentifier exists), for date range (before useEffect sets
  // ltStart/ltEnd), or while settlement data is loading
  const waitingForDateRange =
    !!projectId && !!project.data?.time_zone && (!startParam || !endParam)
  const settlementLoading =
    settlementChargesLoading || identifiersLoading || waitingForDateRange

  const tz = project.data?.time_zone

  const selectedDateKeys = useMemo(() => {
    if (!tz || !startParam || !endParam) {
      return []
    }
    const start = dayjs.tz(startParam, 'YYYY-MM-DD', tz).startOf('day')
    const end = dayjs.tz(endParam, 'YYYY-MM-DD', tz).startOf('day')
    const keys: string[] = []

    let cursor = start
    let guard = 0
    while (!cursor.isAfter(end, 'day')) {
      keys.push(cursor.format('YYYY-MM-DD'))
      cursor = cursor.add(1, 'day')
      guard += 1
      if (guard > 3700) {
        break
      }
    }
    return keys
  }, [tz, startParam, endParam])

  const { keyNames, valuesByKeyByDate } = useMemo(() => {
    if (!tz) {
      return {
        keyNames: [] as string[],
        valuesByKeyByDate: {} as Record<string, Record<string, number>>,
      }
    }

    const allElements = settlementChargesData?.data ?? []
    // Find element by parent identifier from QSE integration
    const element = parentIdentifier
      ? allElements.find((el) => el.identifier === parentIdentifier) ||
        allElements[0]
      : allElements[0]

    const dataPoints = element?.dataPoints ?? []

    // Filter to only daily totals (1440 minutes granularity)
    // Settlement-Charges endpoint should only return daily, but verify
    const dailyKeyNames = dataPoints
      .filter((dp) => {
        const metadata =
          getAcronymMetadata(dp.keyName, 'Settlement-Charges') ||
          getAcronymMetadata(
            dp.keyName,
            'Settlement-Charges-Market-Versioned',
          ) ||
          getAcronymMetadata(dp.keyName)
        // Only include if it's daily (1440 minutes) or if metadata is not available
        // (fallback to include it if we can't verify)
        return !metadata || metadata.granularityMinutes === 1440
      })
      .map((dp) => dp.keyName)
      .sort()

    const keyNames = dailyKeyNames
    const valuesByKeyByDate: Record<string, Record<string, number>> = {}

    // Only process daily keynames
    dataPoints
      .filter((dp) => dailyKeyNames.includes(dp.keyName))
      .forEach((dp) => {
        const keyName = dp.keyName
        valuesByKeyByDate[keyName] = {}

        dp.values?.forEach((val) => {
          if (!val.intervalStartUtc) {
            return
          }
          const dateKey = dayjs
            .utc(val.intervalStartUtc)
            .tz(tz)
            .format('YYYY-MM-DD')

          // Settlement-Charges returns a single value per day, but keep a
          // "choose best" fallback for safety.
          const data = val.data ?? []
          if (data.length === 0) {
            valuesByKeyByDate[keyName][dateKey] = 0
            return
          }

          type DataPointWithSequence = { value: unknown; sequence?: unknown }
          const best = data
            .map((d) => d as DataPointWithSequence)
            .sort((a, b) => {
              const aSeq = typeof a.sequence === 'number' ? a.sequence : 0
              const bSeq = typeof b.sequence === 'number' ? b.sequence : 0
              return bSeq - aSeq
            })[0]

          valuesByKeyByDate[keyName][dateKey] = parseNumberOrZero(best?.value)
        })
      })

    return { keyNames, valuesByKeyByDate }
  }, [settlementChargesData, tz, parentIdentifier])

  const dailyRows = useMemo(() => {
    if (!tz || selectedDateKeys.length === 0 || keyNames.length === 0) {
      return [] as DailyValue[]
    }

    const rows = selectedDateKeys.map((dateKey) => {
      const row: DailyValue = { date: dateKey }
      keyNames.forEach((k) => {
        const rawValue = valuesByKeyByDate[k]?.[dateKey] ?? 0
        // Negate deviation charges so they show as negative
        // Also negate specific keys that need to be flipped for revenue chart
        row[k] =
          isDeviationCharge(k) || shouldNegateForRevenueChart(k)
            ? -rawValue
            : rawValue
      })
      return row
    })

    return rows.sort((a, b) => (dayjs(b.date).isAfter(dayjs(a.date)) ? 1 : -1))
  }, [keyNames, selectedDateKeys, tz, valuesByKeyByDate])

  // Fallback labels for acronyms not in CSV
  const acronymFallbacks: Record<string, string> = useMemo(
    () => ({
      QNSAMT: 'Non-Spinning Reserve Amount (Quarterly)',
    }),
    [],
  )

  // Get field labels from acronym metadata, with fallback to keyname
  const fieldLabels = useMemo<Record<string, string>>(() => {
    const labels: Record<string, string> = {}
    keyNames.forEach((keyName) => {
      // Try Settlement-Charges endpoint first, then Settlement-Charges-Market-Versioned, then any match
      const metadata =
        getAcronymMetadata(keyName, 'Settlement-Charges') ||
        getAcronymMetadata(keyName, 'Settlement-Charges-Market-Versioned') ||
        getAcronymMetadata(keyName)
      if (metadata) {
        // Use description, but shorten if too long
        const desc = metadata.description
        // Remove "The Best-Available" prefix and "Daily Total" suffix for cleaner labels
        let label = desc
          .replace(/^The Best-Available /i, '')
          .replace(/ Daily Total$/i, '')
          .trim()
        // If still too long, truncate
        if (label.length > 60) {
          label = label.substring(0, 57) + '...'
        }
        labels[keyName] = label
      } else if (acronymFallbacks[keyName]) {
        // Use fallback if available
        labels[keyName] = acronymFallbacks[keyName]
      } else {
        labels[keyName] = keyName
      }
    })
    return labels
  }, [keyNames, acronymFallbacks])

  // Get full descriptions for tooltips
  // Try Settlement-Charges first, then Settlement-Charges-Market-Versioned, then fallback to any match
  const fieldDescriptions = useMemo<Record<string, string>>(() => {
    const descriptions: Record<string, string> = {}
    keyNames.forEach((keyName) => {
      // Try Settlement-Charges endpoint first, then Settlement-Charges-Market-Versioned, then any endpoint
      const metadata =
        getAcronymMetadata(keyName, 'Settlement-Charges') ||
        getAcronymMetadata(keyName, 'Settlement-Charges-Market-Versioned') ||
        getAcronymMetadata(keyName)
      descriptions[keyName] = metadata?.description || keyName
    })
    return descriptions
  }, [keyNames])

  const totalsByKeyName = useMemo(() => {
    const totals: Record<string, number> = {}
    keyNames.forEach((k) => {
      totals[k] = 0
    })
    dailyRows.forEach((row) => {
      keyNames.forEach((k) => {
        // Use getValueForKey to handle deviation charge negation
        totals[k] += getValueForKey(row, k)
      })
    })
    return totals
  }, [dailyRows, keyNames])

  const groupedKeyNames = useMemo(() => {
    const grouped: Record<SettlementChargesGroupId, string[]> = {
      energy_charges: [],
      ancillary_services: [],
      penalties: [],
      other: [],
    }

    keyNames.forEach((k) => {
      const metadata =
        getAcronymMetadata(k, 'Settlement-Charges') ||
        getAcronymMetadata(k, 'Settlement-Charges-Market-Versioned') ||
        getAcronymMetadata(k)
      const groupId = groupForKeyName(k, metadata)
      grouped[groupId].push(k)
    })

    GROUP_ORDER.forEach((groupId) => {
      grouped[groupId].sort()
    })

    return grouped
  }, [keyNames])

  /**
   * Group keys within a card category into meaningful subgroups.
   * Returns a map of subgroup name -> array of keynames.
   */
  function getSubgroupsForCard(
    keys: string[],
    groupId: SettlementChargesGroupId,
  ): Record<string, string[]> {
    const subgroups: Record<string, string[]> = {}

    if (groupId === 'ancillary_services') {
      // Group by UI_Subgroup (ECRS, Non-Spin Reserve, RegUp, RegDown, Responsive Reserve, Voltage Support, Black Start)
      // Combine RegUp and RegDown into a single "Regulation" category
      keys.forEach((k) => {
        const metadata =
          getAcronymMetadata(k, 'Settlement-Charges') ||
          getAcronymMetadata(k, 'Settlement-Charges-Market-Versioned') ||
          getAcronymMetadata(k)
        let subgroup = metadata?.uiSubgroup || 'Other Ancillary Services'

        // Combine RegUp and RegDown into "Regulation"
        if (subgroup === 'RegUp' || subgroup === 'RegDown') {
          subgroup = 'Regulation'
        }

        if (!subgroups[subgroup]) {
          subgroups[subgroup] = []
        }
        subgroups[subgroup].push(k)
      })
    } else if (groupId === 'penalties') {
      // Group by deviation type: SPD, BPD, Energy Imbalance, Other
      keys.forEach((k) => {
        const keyUpper = k.toUpperCase()
        const metadata =
          getAcronymMetadata(k, 'Settlement-Charges') ||
          getAcronymMetadata(k, 'Settlement-Charges-Market-Versioned') ||
          getAcronymMetadata(k)
        const desc = metadata?.description.toLowerCase() || ''

        let subgroup = 'Other Deviations'
        if (keyUpper.includes('SPD') || desc.includes('set point deviation')) {
          subgroup = 'Set Point Deviation (SPD)'
        } else if (
          keyUpper.includes('BPD') ||
          desc.includes('base point deviation')
        ) {
          subgroup = 'Base Point Deviation (BPD)'
        } else if (
          desc.includes('energy imbalance') &&
          !desc.includes('ancillary service imbalance')
        ) {
          subgroup = 'Energy Imbalance'
        }

        if (!subgroups[subgroup]) {
          subgroups[subgroup] = []
        }
        subgroups[subgroup].push(k)
      })
    } else if (groupId === 'other') {
      // Group by UI_Group patterns or key patterns
      keys.forEach((k) => {
        const metadata =
          getAcronymMetadata(k, 'Settlement-Charges') ||
          getAcronymMetadata(k, 'Settlement-Charges-Market-Versioned') ||
          getAcronymMetadata(k)
        const uiGroup = metadata?.uiGroup || ''
        const keyUpper = k.toUpperCase()

        let subgroup = 'Other Charges'
        if (uiGroup.includes('Fees') || uiGroup.includes('Admin')) {
          subgroup = 'Fees & Admin'
        } else if (
          uiGroup.includes('CRR') ||
          uiGroup.includes('Congestion') ||
          keyUpper.includes('CRR') ||
          keyUpper.includes('PTP')
        ) {
          subgroup = 'Congestion & CRR/PTP'
        } else if (uiGroup.includes('RUC') || uiGroup.includes('Uplift')) {
          subgroup = 'RUC & Uplift'
        } else if (keyUpper.startsWith('DA') && !keyUpper.startsWith('DAE')) {
          // Day-Ahead non-energy
          subgroup = 'Day-Ahead Other'
        } else if (keyUpper.startsWith('RT') && !keyUpper.startsWith('RTE')) {
          // Real-Time non-energy
          subgroup = 'Real-Time Other'
        }

        if (!subgroups[subgroup]) {
          subgroups[subgroup] = []
        }
        subgroups[subgroup].push(k)
      })
    } else if (groupId === 'energy_charges') {
      // Group DAEPAMT and DAESAMT into "Day Ahead", RTEIAMT into "Real Time"
      keys.forEach((k) => {
        const keyUpper = k.toUpperCase()
        let subgroup = 'Other'

        if (keyUpper === 'DAEPAMT' || keyUpper === 'DAESAMT') {
          subgroup = 'Day Ahead'
        } else if (keyUpper === 'RTEIAMT') {
          subgroup = 'Real Time'
        }

        if (!subgroups[subgroup]) {
          subgroups[subgroup] = []
        }
        subgroups[subgroup].push(k)
      })
    }

    return subgroups
  }

  return (
    <Stack gap="md">
      <Group justify="flex-end">
        <AdvancedDatePicker
          includeTodayInDateRange
          startParamKey="ltStart"
          endParamKey="ltEnd"
        />
      </Group>

      {settlementLoading ? (
        <CustomCard>
          <Skeleton height={400} radius="md" />
        </CustomCard>
      ) : keyNames.length === 0 || dailyRows.length === 0 ? (
        <CustomCard>
          <Text c="dimmed" ta="center" py="xl">
            No daily settlement data available for the selected date range.
          </Text>
        </CustomCard>
      ) : (
        <>
          {/* Total Revenue Card - Sum of all groups */}
          {(() => {
            // Combine all keys from all groups
            const allKeys = Object.values(groupedKeyNames).flat()
            if (allKeys.length === 0) {
              return null
            }

            const totalRevenue = allKeys.reduce(
              (sum, k) => sum + (totalsByKeyName[k] ?? 0),
              0,
            )

            const chartDates = [...dailyRows]
              .map((r) => r.date)
              .sort((a, b) => (dayjs(a).isAfter(dayjs(b), 'day') ? 1 : -1))

            // Separate DA and RT keys from all groups
            const allDaKeys = allKeys.filter((k) =>
              k.toUpperCase().startsWith('DA'),
            )
            const allRtKeys = allKeys.filter((k) =>
              k.toUpperCase().startsWith('RT'),
            )
            const allOtherKeys = allKeys.filter(
              (k) =>
                !k.toUpperCase().startsWith('DA') &&
                !k.toUpperCase().startsWith('RT'),
            )

            // Helper function to get better RT series name
            const getRTSeriesName = (keyName: string): string => {
              const keyUpper = keyName.toUpperCase()
              if (keyUpper === 'RTEIAMT') {
                return 'Real Time'
              }
              const label = fieldLabels[keyName] || keyName
              return label
                .replace(/^The Best-Available /i, '')
                .replace(/ Real-Time /i, ' ')
                .replace(/ Daily Total$/i, '')
                .trim()
            }

            // Generate chart data based on revenue view mode
            const totalChartData: Data[] =
              totalRevenueViewMode === 'cumulative'
                ? (() => {
                    let cumulativeTotal = 0
                    const cumulativeValues: number[] = []

                    chartDates.forEach((dateKey) => {
                      const row = dailyRows.find((r) => r.date === dateKey)
                      const dayTotal = allKeys.reduce((sum, k) => {
                        return sum + getValueForKey(row, k)
                      }, 0)
                      cumulativeTotal += dayTotal
                      cumulativeValues.push(cumulativeTotal)
                    })

                    return [
                      {
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: 'Cumulative Total',
                        x: chartDates,
                        y: cumulativeValues,
                        line: {
                          width: 2,
                          color: theme.colors.blue[6],
                        },
                        marker: {
                          size: 4,
                          color: theme.colors.blue[6],
                        },
                        hovertemplate:
                          '<b>Cumulative Total</b><br>%{x}<br>%{y:$,.2f}<extra></extra>',
                      },
                    ]
                  })()
                : totalRevenueViewMode === 'grouped'
                  ? (() => {
                      // Grouped mode: show 4 groups with proper stacking for positive/negative
                      // First, calculate all group values
                      const groupValues: Record<
                        SettlementChargesGroupId,
                        number[]
                      > = {
                        energy_charges: [],
                        ancillary_services: [],
                        penalties: [],
                        other: [],
                      }

                      GROUP_ORDER.forEach((groupId) => {
                        const groupKeys = groupedKeyNames[groupId]
                        groupValues[groupId] = chartDates.map((dateKey) => {
                          const row = dailyRows.find((r) => r.date === dateKey)
                          return groupKeys.reduce((sum, k) => {
                            return sum + getValueForKey(row, k)
                          }, 0)
                        })
                      })

                      // Get colors for each group
                      const getGroupColor = (
                        groupId: SettlementChargesGroupId,
                      ): string => {
                        switch (groupId) {
                          case 'energy_charges':
                            return theme.colors.blue[6]
                          case 'ancillary_services':
                            return theme.colors.yellow[6]
                          case 'penalties':
                            return theme.colors.red[6]
                          case 'other':
                            return theme.colors.gray[6]
                          default:
                            return theme.colors.gray[6]
                        }
                      }

                      const traces: StackedBarTrace[] = []

                      // Build positive traces (stacked upward from zero)
                      GROUP_ORDER.forEach((groupId) => {
                        const groupKeys = groupedKeyNames[groupId]
                        if (groupKeys.length === 0) {
                          return
                        }

                        const values = groupValues[groupId]
                        const positiveValues = values.map((v) =>
                          v > 0 ? v : 0,
                        )
                        const actualValues = values

                        // Calculate base for stacking positive values
                        const bases = chartDates.map((_, dateIdx) => {
                          let base = 0
                          const currentGroupIdx = GROUP_ORDER.indexOf(groupId)
                          for (let i = 0; i < currentGroupIdx; i++) {
                            const prevGroupId = GROUP_ORDER[i]
                            const prevValue = groupValues[prevGroupId][dateIdx]
                            if (prevValue > 0) {
                              base += prevValue
                            }
                          }
                          return base
                        })

                        traces.push({
                          type: 'bar' as const,
                          name: GROUP_META[groupId].title,
                          x: chartDates,
                          y: positiveValues,
                          base: bases,
                          hovertemplate: `<b>${GROUP_META[groupId].title}</b><br>%{customdata:$,.2f}<extra></extra>`,
                          customdata: actualValues,
                          marker: {
                            color: getGroupColor(groupId),
                          },
                        })
                      })

                      // Build negative traces (stacked downward from zero)
                      // Process in reverse order for proper stacking
                      GROUP_ORDER.slice()
                        .reverse()
                        .forEach((groupId) => {
                          const groupKeys = groupedKeyNames[groupId]
                          if (groupKeys.length === 0) {
                            return
                          }

                          const values = groupValues[groupId]
                          const negativeValues = values.map((v) =>
                            v < 0 ? v : 0,
                          )
                          const actualValues = values

                          // Calculate base for stacking negative values
                          const bases = chartDates.map((_, dateIdx) => {
                            let base = 0
                            const currentGroupIdx = GROUP_ORDER.indexOf(groupId)
                            for (
                              let i = GROUP_ORDER.length - 1;
                              i > currentGroupIdx;
                              i--
                            ) {
                              const prevGroupId = GROUP_ORDER[i]
                              const prevValue =
                                groupValues[prevGroupId][dateIdx]
                              if (prevValue < 0) {
                                base += prevValue
                              }
                            }
                            return base
                          })

                          traces.push({
                            type: 'bar' as const,
                            name: GROUP_META[groupId].title,
                            x: chartDates,
                            y: negativeValues,
                            base: bases,
                            hoverinfo: 'skip' as const, // Skip hover on negative traces to avoid duplicates
                            customdata: actualValues,
                            marker: {
                              color: getGroupColor(groupId),
                            },
                            showlegend: false, // Hide duplicate legend entries
                          })
                        })

                      return traces
                    })()
                  : // Detailed mode: show individual fields
                    [
                      // Day-Ahead: combine all DA fields into single "Day Ahead" series
                      ...(allDaKeys.length > 0
                        ? [
                            {
                              type: 'bar' as const,
                              name: 'Day Ahead',
                              x: chartDates,
                              y: chartDates.map((dateKey) => {
                                const row = dailyRows.find(
                                  (r) => r.date === dateKey,
                                )
                                return allDaKeys.reduce((sum, k) => {
                                  return sum + getValueForKey(row, k)
                                }, 0)
                              }),
                              hovertemplate:
                                '<b>Day Ahead</b><br>%{x}<br>%{y:$,.2f}<extra></extra>',
                              marker: {
                                color: theme.colors.blue[6],
                              },
                            },
                          ]
                        : []),
                      // Real-Time: individual series with better names
                      ...allRtKeys.map((k) => {
                        const y = chartDates.map((dateKey) => {
                          const row = dailyRows.find((r) => r.date === dateKey)
                          return getValueForKey(row, k)
                        })

                        return {
                          type: 'bar' as const,
                          name: getRTSeriesName(k),
                          x: chartDates,
                          y,
                          hovertemplate:
                            '%{fullData.name}<br>%{x}: %{y:$,.2f}<extra></extra>',
                          marker: {
                            color: y.map((v) =>
                              v >= 0
                                ? theme.colors.orange[6]
                                : theme.colors.red[6],
                            ),
                          },
                        }
                      }),
                      // Other fields: keep as individual series
                      ...allOtherKeys.map((k) => {
                        const y = chartDates.map((dateKey) => {
                          const row = dailyRows.find((r) => r.date === dateKey)
                          return getValueForKey(row, k)
                        })

                        return {
                          type: 'bar' as const,
                          name: fieldLabels[k] || k,
                          x: chartDates,
                          y,
                          hovertemplate:
                            '%{fullData.name}<br>%{x}: %{y:$,.2f}<extra></extra>',
                          marker: {
                            color: y.map((v) =>
                              v >= 0
                                ? theme.colors.green[6]
                                : theme.colors.red[6],
                            ),
                          },
                        }
                      }),
                    ]

            const totalChartLayout: Partial<Layout> = {
              xaxis: {
                title: { text: 'Date' },
                type: 'category',
                tickangle: -35,
              },
              yaxis: {
                title: { text: '$' },
                tickformat: '$,.0f',
                zeroline: true,
              },
              barmode:
                totalRevenueViewMode === 'cumulative'
                  ? undefined
                  : totalRevenueViewMode === 'grouped'
                    ? 'stack'
                    : 'relative',
              legend: {
                traceorder: 'normal', // Show legend in the order traces are added (Energy Markets first, Other last)
              },
              height: 360,
              margin: { l: 80, r: 20, t: 50, b: 120 },
            }

            const totalMinWidth = Math.max(
              900,
              160 + 140 * totalChartData.length,
            )

            return (
              <CustomCard
                key="total-revenue"
                title="Total Revenue"
                info={
                  <Text size="sm">
                    Combined revenue from all settlement charge categories
                    <br />
                    {allKeys.length} data points across all groups
                  </Text>
                }
                headerChildren={
                  <Group gap="xs" align="center">
                    <Text size="sm" c="dimmed">
                      Revenue:
                    </Text>
                    <SegmentedControl
                      value={totalRevenueViewMode}
                      onChange={(value) =>
                        setTotalRevenueViewMode(
                          value as 'cumulative' | 'grouped' | 'detailed',
                        )
                      }
                      data={[
                        {
                          label: (
                            <Tooltip label="Line chart showing cumulative revenue over the period">
                              <span>Cumulative</span>
                            </Tooltip>
                          ),
                          value: 'cumulative',
                        },
                        {
                          label: (
                            <Tooltip label="Stacked column charts grouped by category">
                              <span>Grouped</span>
                            </Tooltip>
                          ),
                          value: 'grouped',
                        },
                        {
                          label: (
                            <Tooltip label="Stacked column charts with detailed breakdown of individual components">
                              <span>Detailed</span>
                            </Tooltip>
                          ),
                          value: 'detailed',
                        },
                      ]}
                      size="xs"
                    />
                    <Text fw={700} ml="md">
                      {formatCurrency(totalRevenue)}
                    </Text>
                  </Group>
                }
              >
                <Tabs defaultValue="chart" mt="sm">
                  <Tabs.List>
                    <Tabs.Tab value="chart">Chart</Tabs.Tab>
                    <Tabs.Tab value="table">Table</Tabs.Tab>
                  </Tabs.List>

                  <Tabs.Panel value="chart" pt="sm">
                    <PlotlyPlot
                      data={totalChartData}
                      layout={totalChartLayout}
                      onClick={handlePlotClick}
                    />
                  </Tabs.Panel>

                  <Tabs.Panel value="table" pt="sm">
                    <Table.ScrollContainer minWidth={totalMinWidth}>
                      <Table striped highlightOnHover>
                        <Table.Thead>
                          <Table.Tr>
                            <Table.Th
                              style={{
                                whiteSpace: 'nowrap',
                                minWidth: '100px',
                              }}
                            >
                              Date
                            </Table.Th>
                            {allKeys.map((k) => (
                              <Tooltip
                                key={k}
                                label={fieldDescriptions[k]}
                                multiline
                                w={300}
                                withArrow
                              >
                                <Table.Th style={{ textAlign: 'right' }}>
                                  <Text size="xs" fw={600}>
                                    {fieldLabels[k] || k}
                                  </Text>
                                  <Text size="xs" c="dimmed" ff="monospace">
                                    {k}
                                  </Text>
                                </Table.Th>
                              </Tooltip>
                            ))}
                          </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                          {dailyRows.map((row) => (
                            <Table.Tr key={row.date}>
                              <Table.Td style={{ whiteSpace: 'nowrap' }}>
                                {dayjs(row.date).format('MMM D, YYYY')}
                              </Table.Td>
                              {allKeys.map((k) => {
                                const value = getValueForKey(row, k)
                                return (
                                  <Tooltip
                                    key={k}
                                    label={fieldDescriptions[k]}
                                    multiline
                                    w={300}
                                    withArrow
                                  >
                                    <Table.Td style={{ textAlign: 'right' }}>
                                      {formatCurrency(value)}
                                    </Table.Td>
                                  </Tooltip>
                                )
                              })}
                            </Table.Tr>
                          ))}
                          {dailyRows.length > 1 && (
                            <Table.Tr style={{ fontWeight: 600 }}>
                              <Table.Td style={{ whiteSpace: 'nowrap' }}>
                                Total
                              </Table.Td>
                              {allKeys.map((k) => (
                                <Tooltip
                                  key={k}
                                  label={fieldDescriptions[k]}
                                  multiline
                                  w={300}
                                  withArrow
                                >
                                  <Table.Td style={{ textAlign: 'right' }}>
                                    {formatCurrency(totalsByKeyName[k] ?? 0)}
                                  </Table.Td>
                                </Tooltip>
                              ))}
                            </Table.Tr>
                          )}
                        </Table.Tbody>
                      </Table>
                    </Table.ScrollContainer>
                  </Tabs.Panel>
                </Tabs>
              </CustomCard>
            )
          })()}

          {GROUP_ORDER.map((groupId) => {
            const keys = groupedKeyNames[groupId]
            // Show card if there are any keys in this group, regardless of totals
            // (cards are not filtered by zero values)
            if (keys.length === 0) {
              return null
            }

            const groupTotal = keys.reduce(
              (sum, k) => sum + (totalsByKeyName[k] ?? 0),
              0,
            )

            const chartDates = [...dailyRows]
              .map((r) => r.date)
              .sort((a, b) => (dayjs(a).isAfter(dayjs(b), 'day') ? 1 : -1))

            // Separate DA and RT keys
            const daKeys = keys.filter((k) => k.toUpperCase().startsWith('DA'))
            const rtKeys = keys.filter((k) => k.toUpperCase().startsWith('RT'))
            const otherKeys = keys.filter(
              (k) =>
                !k.toUpperCase().startsWith('DA') &&
                !k.toUpperCase().startsWith('RT'),
            )

            // Helper function to get better RT series name
            const getRTSeriesName = (keyName: string): string => {
              const keyUpper = keyName.toUpperCase()
              if (keyUpper === 'RTEIAMT') {
                return 'Real Time'
              }
              // Use the field label but simplify if it's too long
              const label = fieldLabels[keyName] || keyName
              // Remove common prefixes/suffixes
              return label
                .replace(/^The Best-Available /i, '')
                .replace(/ Real-Time /i, ' ')
                .replace(/ Daily Total$/i, '')
                .trim()
            }

            // Helper function to get nice short names for energy card fields in detailed mode
            const getEnergyFieldName = (keyName: string): string => {
              const keyUpper = keyName.toUpperCase()
              if (keyUpper === 'DAEPAMT') {
                return 'Day Ahead Charges'
              }
              if (keyUpper === 'DAESAMT') {
                return 'Day Ahead Payments'
              }
              if (keyUpper === 'RTEIAMT') {
                return 'Real-Time'
              }
              return fieldLabels[keyName] || keyName
            }

            // Get the view mode for this specific card
            const cardViewMode = revenueViewModes[groupId]

            // Generate chart data based on revenue view mode
            const chartData: Data[] =
              cardViewMode === 'cumulative'
                ? (() => {
                    // Cumulative mode: line chart showing cumulative totals
                    let cumulativeTotal = 0
                    const cumulativeValues: number[] = []

                    chartDates.forEach((dateKey) => {
                      const row = dailyRows.find((r) => r.date === dateKey)
                      const dayTotal = keys.reduce((sum, k) => {
                        return sum + getValueForKey(row, k)
                      }, 0)
                      cumulativeTotal += dayTotal
                      cumulativeValues.push(cumulativeTotal)
                    })

                    return [
                      {
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: 'Cumulative Total',
                        x: chartDates,
                        y: cumulativeValues,
                        line: {
                          width: 2,
                          color: theme.colors.blue[6],
                        },
                        marker: {
                          size: 4,
                          color: theme.colors.blue[6],
                        },
                        hovertemplate:
                          '<b>Cumulative Total</b><br>%{x}<br>%{y:$,.2f}<extra></extra>',
                      },
                    ]
                  })()
                : cardViewMode === 'grouped'
                  ? (() => {
                      // Grouped mode: show subgroups with proper stacking
                      const subgroups = getSubgroupsForCard(keys, groupId)
                      const subgroupNames = Object.keys(subgroups).sort()

                      if (subgroupNames.length === 0) {
                        return []
                      }

                      // Calculate values for each subgroup
                      const subgroupValues: Record<string, number[]> = {}
                      subgroupNames.forEach((subgroupName) => {
                        const subgroupKeys = subgroups[subgroupName]
                        subgroupValues[subgroupName] = chartDates.map(
                          (dateKey) => {
                            const row = dailyRows.find(
                              (r) => r.date === dateKey,
                            )
                            return subgroupKeys.reduce((sum, k) => {
                              return sum + getValueForKey(row, k)
                            }, 0)
                          },
                        )
                      })

                      // Get colors for subgroups
                      const getSubgroupColor = (
                        subgroupName: string,
                        index: number,
                      ): string => {
                        // For energy_charges card, use specific colors
                        if (groupId === 'energy_charges') {
                          if (subgroupName === 'Real Time') {
                            return theme.colors.orange[6]
                          }
                          if (subgroupName === 'Day Ahead') {
                            return theme.colors.blue[6]
                          }
                        }

                        const colors = [
                          theme.colors.blue[6],
                          theme.colors.yellow[6],
                          theme.colors.green[6],
                          theme.colors.orange[6],
                          theme.colors.grape[6],
                          theme.colors.cyan[6],
                          theme.colors.pink[6],
                          theme.colors.violet[6],
                        ]
                        return colors[index % colors.length]
                      }

                      const traces: StackedBarTrace[] = []

                      // Build positive traces (stacked upward from zero)
                      subgroupNames.forEach((subgroupName, idx) => {
                        const values = subgroupValues[subgroupName]
                        const positiveValues = values.map((v) =>
                          v > 0 ? v : 0,
                        )
                        const actualValues = values

                        // Calculate base for stacking positive values
                        const bases = chartDates.map((_, dateIdx) => {
                          let base = 0
                          for (let i = 0; i < idx; i++) {
                            const prevSubgroupName = subgroupNames[i]
                            const prevValue =
                              subgroupValues[prevSubgroupName][dateIdx]
                            if (prevValue > 0) {
                              base += prevValue
                            }
                          }
                          return base
                        })

                        traces.push({
                          type: 'bar' as const,
                          name: subgroupName,
                          x: chartDates,
                          y: positiveValues,
                          base: bases,
                          hovertemplate: `<b>${subgroupName}</b><br>%{customdata:$,.2f}<extra></extra>`,
                          customdata: actualValues,
                          marker: {
                            color: getSubgroupColor(subgroupName, idx),
                          },
                        })
                      })

                      // Build negative traces (stacked downward from zero)
                      subgroupNames
                        .slice()
                        .reverse()
                        .forEach((_, reverseIdx) => {
                          const idx = subgroupNames.length - 1 - reverseIdx
                          const subgroupName = subgroupNames[idx]
                          const values = subgroupValues[subgroupName]
                          const negativeValues = values.map((v) =>
                            v < 0 ? v : 0,
                          )
                          const actualValues = values

                          // Calculate base for stacking negative values
                          const bases = chartDates.map((_, dateIdx) => {
                            let base = 0
                            for (
                              let i = subgroupNames.length - 1;
                              i > idx;
                              i--
                            ) {
                              const prevSubgroupName = subgroupNames[i]
                              const prevValue =
                                subgroupValues[prevSubgroupName][dateIdx]
                              if (prevValue < 0) {
                                base += prevValue
                              }
                            }
                            return base
                          })

                          traces.push({
                            type: 'bar' as const,
                            name: subgroupName,
                            x: chartDates,
                            y: negativeValues,
                            base: bases,
                            hoverinfo: 'skip' as const,
                            customdata: actualValues,
                            marker: {
                              color: getSubgroupColor(subgroupName, idx),
                            },
                            showlegend: false,
                          })
                        })

                      return traces
                    })()
                  : [
                      // Detailed mode: show individual series
                      // For energy_charges card, use short names; for others use field labels
                      ...(groupId === 'energy_charges'
                        ? [
                            // Energy card: use short names
                            ...keys.map((k) => {
                              const y = chartDates.map((dateKey) => {
                                const row = dailyRows.find(
                                  (r) => r.date === dateKey,
                                )
                                return getValueForKey(row, k)
                              })

                              const keyUpper = k.toUpperCase()
                              // Use orange for Real Time (RTEIAMT), blue for Day Ahead (DAEPAMT, DAESAMT)
                              const baseColor =
                                keyUpper === 'RTEIAMT'
                                  ? theme.colors.orange[6]
                                  : keyUpper === 'DAEPAMT' ||
                                      keyUpper === 'DAESAMT'
                                    ? theme.colors.blue[6]
                                    : theme.colors.blue[6]

                              return {
                                type: 'bar' as const,
                                name: getEnergyFieldName(k),
                                x: chartDates,
                                y,
                                hovertemplate:
                                  '%{fullData.name}<br>%{x}: %{y:$,.2f}<extra></extra>',
                                marker: {
                                  color: y.map((v) =>
                                    v >= 0 ? baseColor : theme.colors.red[6],
                                  ),
                                },
                              }
                            }),
                          ]
                        : [
                            // Other cards: use field labels
                            // Day-Ahead: show individual series with proper names from CSV metadata
                            ...daKeys.map((k) => {
                              const y = chartDates.map((dateKey) => {
                                const row = dailyRows.find(
                                  (r) => r.date === dateKey,
                                )
                                return getValueForKey(row, k)
                              })

                              return {
                                type: 'bar' as const,
                                name: fieldLabels[k] || k,
                                x: chartDates,
                                y,
                                hovertemplate:
                                  '%{fullData.name}<br>%{x}: %{y:$,.2f}<extra></extra>',
                                marker: {
                                  color: y.map((v) =>
                                    v >= 0
                                      ? theme.colors.blue[6]
                                      : theme.colors.red[6],
                                  ),
                                },
                              }
                            }),
                            // Real-Time: individual series with better names
                            ...rtKeys.map((k) => {
                              const y = chartDates.map((dateKey) => {
                                const row = dailyRows.find(
                                  (r) => r.date === dateKey,
                                )
                                return getValueForKey(row, k)
                              })

                              return {
                                type: 'bar' as const,
                                name: getRTSeriesName(k),
                                x: chartDates,
                                y,
                                hovertemplate:
                                  '%{fullData.name}<br>%{x}: %{y:$,.2f}<extra></extra>',
                                marker: {
                                  color: y.map((v) =>
                                    v >= 0
                                      ? theme.colors.orange[6]
                                      : theme.colors.red[6],
                                  ),
                                },
                              }
                            }),
                            // Other fields: keep as individual series
                            ...otherKeys.map((k) => {
                              const y = chartDates.map((dateKey) => {
                                const row = dailyRows.find(
                                  (r) => r.date === dateKey,
                                )
                                return getValueForKey(row, k)
                              })

                              return {
                                type: 'bar' as const,
                                name: fieldLabels[k] || k,
                                x: chartDates,
                                y,
                                hovertemplate:
                                  '%{fullData.name}<br>%{x}: %{y:$,.2f}<extra></extra>',
                                marker: {
                                  color: y.map((v) =>
                                    v >= 0
                                      ? theme.colors.green[6]
                                      : theme.colors.red[6],
                                  ),
                                },
                              }
                            }),
                          ]),
                    ]

            const chartLayout: Partial<Layout> = {
              xaxis: {
                title: { text: 'Date' },
                type: 'category',
                tickangle: -35,
              },
              yaxis: {
                title: { text: '$' },
                tickformat: '$,.0f',
                zeroline: true,
              },
              barmode:
                cardViewMode === 'cumulative'
                  ? undefined
                  : cardViewMode === 'grouped'
                    ? 'stack'
                    : 'relative',
              height: 360,
              margin: { l: 80, r: 20, t: 50, b: 120 },
            }

            const minWidth = Math.max(900, 160 + 140 * keys.length)

            return (
              <CustomCard
                key={groupId}
                title={GROUP_META[groupId].title}
                info={
                  <Text size="sm">
                    {GROUP_META[groupId].description}
                    <br />
                    {keys.length} data points
                  </Text>
                }
                headerChildren={
                  <Group gap="xs" align="center">
                    <Text size="sm" c="dimmed">
                      Revenue:
                    </Text>
                    <SegmentedControl
                      value={revenueViewModes[groupId]}
                      onChange={(value) =>
                        setRevenueViewModes((prev) => ({
                          ...prev,
                          [groupId]: value as
                            | 'cumulative'
                            | 'grouped'
                            | 'detailed',
                        }))
                      }
                      data={[
                        {
                          label: (
                            <Tooltip label="Line chart showing cumulative revenue over the period">
                              <span>Cumulative</span>
                            </Tooltip>
                          ),
                          value: 'cumulative',
                        },
                        {
                          label: (
                            <Tooltip label="Stacked column charts grouped by category">
                              <span>Grouped</span>
                            </Tooltip>
                          ),
                          value: 'grouped',
                        },
                        {
                          label: (
                            <Tooltip label="Stacked column charts with detailed breakdown of individual components">
                              <span>Detailed</span>
                            </Tooltip>
                          ),
                          value: 'detailed',
                        },
                      ]}
                      size="xs"
                    />
                    <Text fw={700} ml="md">
                      {formatCurrency(groupTotal)}
                    </Text>
                  </Group>
                }
              >
                <Tabs defaultValue="chart" mt="sm">
                  <Tabs.List>
                    <Tabs.Tab value="chart">Chart</Tabs.Tab>
                    <Tabs.Tab value="table">Table</Tabs.Tab>
                  </Tabs.List>

                  <Tabs.Panel value="chart" pt="sm">
                    <PlotlyPlot
                      data={chartData}
                      layout={chartLayout}
                      onClick={handlePlotClick}
                    />
                  </Tabs.Panel>

                  <Tabs.Panel value="table" pt="sm">
                    <Table.ScrollContainer minWidth={minWidth}>
                      <Table striped highlightOnHover>
                        <Table.Thead>
                          <Table.Tr>
                            <Table.Th
                              style={{
                                whiteSpace: 'nowrap',
                                minWidth: '100px',
                              }}
                            >
                              Date
                            </Table.Th>
                            {keys.map((k) => (
                              <Tooltip
                                key={k}
                                label={fieldDescriptions[k]}
                                multiline
                                w={300}
                                withArrow
                              >
                                <Table.Th style={{ textAlign: 'right' }}>
                                  <Text size="xs" fw={600}>
                                    {fieldLabels[k] || k}
                                  </Text>
                                  <Text size="xs" c="dimmed" ff="monospace">
                                    {k}
                                  </Text>
                                </Table.Th>
                              </Tooltip>
                            ))}
                          </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                          {dailyRows.map((row) => (
                            <Table.Tr key={row.date}>
                              <Table.Td style={{ whiteSpace: 'nowrap' }}>
                                {dayjs(row.date).format('MMM D, YYYY')}
                              </Table.Td>
                              {keys.map((k) => {
                                const value = getValueForKey(row, k)
                                return (
                                  <Tooltip
                                    key={k}
                                    label={fieldDescriptions[k]}
                                    multiline
                                    w={300}
                                    withArrow
                                  >
                                    <Table.Td style={{ textAlign: 'right' }}>
                                      {formatCurrency(value)}
                                    </Table.Td>
                                  </Tooltip>
                                )
                              })}
                            </Table.Tr>
                          ))}
                          {dailyRows.length > 1 && (
                            <Table.Tr style={{ fontWeight: 600 }}>
                              <Table.Td style={{ whiteSpace: 'nowrap' }}>
                                Total
                              </Table.Td>
                              {keys.map((k) => (
                                <Tooltip
                                  key={k}
                                  label={fieldDescriptions[k]}
                                  multiline
                                  w={300}
                                  withArrow
                                >
                                  <Table.Td style={{ textAlign: 'right' }}>
                                    {formatCurrency(totalsByKeyName[k] ?? 0)}
                                  </Table.Td>
                                </Tooltip>
                              ))}
                            </Table.Tr>
                          )}
                        </Table.Tbody>
                      </Table>
                    </Table.ScrollContainer>
                  </Tabs.Panel>
                </Tabs>
              </CustomCard>
            )
          })}
        </>
      )}
    </Stack>
  )
}
