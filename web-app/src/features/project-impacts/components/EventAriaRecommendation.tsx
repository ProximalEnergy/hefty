import { Event } from '@/hooks/types'
import { Divider, Group, Stack, Text } from '@mantine/core'
import dayjs, { Dayjs } from 'dayjs'

type EventAriaRecommendationProps = {
  dailyLoss: number
  event: Event
}

const getNextScheduledMaintenance = (date: Dayjs) => {
  let nextDate = date.add(1, 'day')
  while (![1, 15].includes(nextDate.date())) {
    nextDate = nextDate.add(1, 'day')
  }
  return nextDate
}

export function EventAriaRecommendation({
  event,
  dailyLoss,
}: EventAriaRecommendationProps) {
  const today = dayjs()

  const nextMaintenance = getNextScheduledMaintenance(today)
  const daysUntilMaintenance = nextMaintenance.diff(today, 'days')
  const noActionLoss = daysUntilMaintenance * dailyLoss

  const flightCost = 500
  const lodgingCost = 1000

  const actionLoss = flightCost + lodgingCost + 2 * dailyLoss
  const actionBenefit = noActionLoss - actionLoss
  if (dailyLoss === 0) {
    return (
      <Stack p={0} w="100%" gap={0} align="space-between">
        <Text size="lg" fw={500}>
          Repair on next
        </Text>
        <Text size="lg" fw={500}>
          scheduled maintenance.
        </Text>
      </Stack>
    )
  }

  return (
    <Stack p={0} w="100%" gap={0} align="space-between">
      {!event.time_end ? (
        <>
          {actionBenefit > 0 ? (
            <>
              <Text size="lg" fw={500}>
                Repair immediately.
              </Text>
              <Divider my="lg" />
            </>
          ) : (
            <>
              <Text size="lg" fw={500}>
                Repair on next
              </Text>
              <Text size="lg" fw={500}>
                scheduled maintenance.
              </Text>
              <Divider my="lg" />
            </>
          )}
          <Group justify="space-between">
            <Text fw={500} size="md">
              Cost to Fix (Scheduled)
            </Text>
            <Text fw={500} size="md">
              ${noActionLoss.toFixed(2)}
            </Text>
          </Group>
          <Group justify="space-between">
            <Text size="sm">Next Maintenance:</Text>
            <Text size="sm">
              {nextMaintenance.format('MM/DD/YYYY')} ({daysUntilMaintenance}{' '}
              days)
            </Text>
          </Group>
          <Text size="sm">
            ${dailyLoss.toFixed(2)}/day × {daysUntilMaintenance} days
          </Text>
          <Group justify="space-between">
            <Text size="md" fw={500}>
              Cost to Fix (ASAP)
            </Text>
            <Text size="md" fw={500}>
              ${actionLoss.toFixed(2)}
            </Text>
          </Group>
          <Text size="sm">Flight: ${flightCost.toFixed(2)} +</Text>
          <Text size="sm">Lodging: ${lodgingCost.toFixed(2)} +</Text>
          <Text size="sm">Loss: ${dailyLoss.toFixed(2)}/day × 2 days</Text>
        </>
      ) : (
        <Text size="lg" fw={500}>
          No issue at this time.
        </Text>
      )}
    </Stack>
  )
}
