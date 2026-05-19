import { useSelectProject } from '@/api/v1/operational/projects'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { MarketPricesPowerCard } from '@/pages/projects/finances/components/MarketPricesPowerCard'
import { SppDailyProfileCard } from '@/pages/projects/finances/components/SppDailyProfileCard'
import { Group, Stack } from '@mantine/core'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router'

dayjs.extend(utc)
dayjs.extend(timezone)

interface WeekViewTabProps {
  projectId: string
}

export const WeekViewTab = ({ projectId }: WeekViewTabProps) => {
  const project = useSelectProject(projectId)
  const [searchParams, setSearchParams] = useSearchParams()
  const maxRangeDays = 7

  // Get selected dates from URL params (set by AdvancedDatePicker)
  const startParam = searchParams.get('start')
  const endParam = searchParams.get('end')

  // Set default date range on initial load: past 7 days (incl. today)
  useEffect(() => {
    if (!project.data?.time_zone) {
      return
    }
    if (!startParam || !endParam) {
      const tz = project.data.time_zone
      const now = dayjs().tz(tz)
      const sixDaysAgoStart = now.subtract(6, 'day').startOf('day')
      const todayEnd = now.endOf('day')

      const nextParams = new URLSearchParams(searchParams)
      nextParams.set('start', sixDaysAgoStart.format('YYYY-MM-DD'))
      nextParams.set('end', todayEnd.format('YYYY-MM-DD'))
      setSearchParams(nextParams, { replace: true })
    }
  }, [
    project.data?.time_zone,
    startParam,
    endParam,
    searchParams,
    setSearchParams,
  ])

  // Clamp any selected range to max 7 days.
  useEffect(() => {
    if (!project.data?.time_zone || !startParam || !endParam) {
      return
    }

    const tz = project.data.time_zone
    const start = dayjs.tz(startParam, 'YYYY-MM-DD', tz).startOf('day')
    const end = dayjs.tz(endParam, 'YYYY-MM-DD', tz).startOf('day')

    const startDay = end.isBefore(start) ? end : start
    const endDay = end.isBefore(start) ? start : end
    const maxEndDay = startDay.add(maxRangeDays - 1, 'day')
    const clampedEndDay = endDay.isAfter(maxEndDay) ? maxEndDay : endDay

    const nextStart = startDay.format('YYYY-MM-DD')
    const nextEnd = clampedEndDay.format('YYYY-MM-DD')
    if (nextStart === startParam && nextEnd === endParam) {
      return
    }

    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('start', nextStart)
    nextParams.set('end', nextEnd)
    setSearchParams(nextParams, { replace: true })
  }, [
    project.data?.time_zone,
    startParam,
    endParam,
    searchParams,
    setSearchParams,
    maxRangeDays,
  ])

  // Calculate date range for MarketPricesPowerCard.
  const { marketPricesStartDate, marketPricesEndDate } = useMemo(() => {
    if (!project.data?.time_zone) {
      return { marketPricesStartDate: null, marketPricesEndDate: null }
    }
    const tz = project.data.time_zone

    // If dates are selected from the picker, use them
    if (startParam && endParam) {
      // Parse date strings in the target timezone to avoid timezone shifts
      const start = dayjs
        .tz(startParam, 'YYYY-MM-DD', tz)
        .startOf('day')
        .toDate()
      const end = dayjs.tz(endParam, 'YYYY-MM-DD', tz).endOf('day').toDate()
      return { marketPricesStartDate: start, marketPricesEndDate: end }
    }

    // Default: past 7 days (incl. today)
    const now = dayjs().tz(tz)
    const sixDaysAgoStart = now.subtract(6, 'day').startOf('day')
    const todayEnd = now.endOf('day')
    return {
      marketPricesStartDate: sixDaysAgoStart.toDate(),
      marketPricesEndDate: todayEnd.toDate(),
    }
  }, [project.data, startParam, endParam])

  return (
    <Stack gap="md">
      <Group justify="flex-end">
        <AdvancedDatePicker
          includeTodayInDateRange
          maxDays={maxRangeDays}
          limits={{
            day: maxRangeDays,
            week: 1,
            month: 0,
            quarter: 0,
            year: 0,
          }}
          disableQuickActions={[
            'past-month',
            'last-month',
            'last-quarter',
            'last-year',
            'ytd',
          ]}
        />
      </Group>

      <MarketPricesPowerCard
        projectId={projectId}
        projectTimeZone={project.data?.time_zone}
        startDate={marketPricesStartDate}
        endDate={marketPricesEndDate}
        useCustomDateRange={true}
      />

      <SppDailyProfileCard
        projectId={projectId}
        projectTimeZone={project.data?.time_zone}
        startDate={marketPricesStartDate}
        endDate={marketPricesEndDate}
      />
    </Stack>
  )
}
