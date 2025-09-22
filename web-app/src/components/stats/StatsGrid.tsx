import { Statistic, StatisticIcon } from '@/hooks/types'
import { Card, Group, SimpleGrid, Skeleton, Text, Tooltip } from '@mantine/core'
import {
  Icon,
  IconArrowDownRight,
  IconArrowUpRight,
  IconBatteryCharging,
  IconBolt,
  IconBuilding,
  IconChartBar,
  IconDiscountCheck,
  IconExclamationCircle,
  IconHeart,
  IconTemperature,
} from '@tabler/icons-react'

type StatsGridProps = {
  data: Statistic[]
  isLoading?: boolean
}

const icons: Record<StatisticIcon, Icon> = {
  events: IconExclamationCircle,
  pcs: IconBolt,
  temp: IconTemperature,
  soc: IconBatteryCharging,
  soh: IconHeart,
  availability: IconDiscountCheck,
  performance: IconChartBar,
  project: IconBuilding,
}

export function StatsGrid({ data, isLoading }: StatsGridProps) {
  if (isLoading) {
    return (
      <SimpleGrid cols={{ base: 1, xs: 2, md: 5 }}>
        {Array(5)
          .fill(0)
          .map((_, index) => (
            <Card key={index} withBorder p="md" radius="md">
              <Group justify="space-between">
                <Skeleton height={12} width="50%" radius="xl" />
                <Skeleton height={20} circle />
              </Group>
              <Group align="flex-end" gap="xs" mt={25}>
                <Skeleton height={25} width="70%" radius="xl" />
                <Skeleton height={15} width="20%" radius="xl" />
              </Group>
            </Card>
          ))}
      </SimpleGrid>
    )
  }
  const stats = data.map((stat) => {
    const Icon = icons[stat.icon]
    const DiffIcon =
      stat.diff && stat.diff > 0 ? IconArrowUpRight : IconArrowDownRight

    let diffColor = stat.diff && stat.diff > 0 ? 'teal' : 'red'
    if (stat.title === 'SOC (avg)' && stat.diff != null) {
      const absDiff = Math.abs(stat.diff)
      if (absDiff < 4) {
        diffColor = 'green'
      } else if (absDiff > 10) {
        diffColor = 'red'
      } else {
        diffColor = 'yellow' // Or any other color for intermediate
      }
    } else if (stat.title === 'Cell Temperature (avg)' && stat.diff != null) {
      const absDiff = Math.abs(stat.diff)
      if (absDiff < 1) {
        diffColor = 'green'
      } else if (absDiff > 5) {
        diffColor = 'red'
      } else {
        diffColor = 'yellow'
      }
    } else if (stat.title === 'SOH (avg)' && stat.diff != null) {
      const absDiff = Math.abs(stat.diff)
      if (absDiff < 0.3) {
        diffColor = 'green'
      } else if (absDiff > 1) {
        diffColor = 'red'
      } else {
        diffColor = 'yellow'
      }
    }

    return (
      <Tooltip
        key={stat.title}
        label={stat.description}
        withArrow
        disabled={!stat.description}
      >
        <Card withBorder p="md" radius="md">
          <Group justify="space-between">
            <Text size="sm" c="dimmed">
              {stat.title}
            </Text>
            <Icon size="1.2rem" stroke={1.5} />
          </Group>

          <Group align="flex-end" gap="xs" mt={15}>
            <Text fz={32} fw={700}>
              {stat.value}
            </Text>
            {stat.diff !== undefined && stat.diff !== null && (
              <Text c={diffColor} fz="sm" fw={500}>
                {stat.title.includes('(avg)') ? (
                  <span>{`Δ${stat.diff.toFixed(1)}${
                    stat.title.includes('SOC') || stat.title.includes('SOH')
                      ? '%'
                      : '°C'
                  }`}</span>
                ) : (
                  <>
                    <span>
                      {stat.diff > 0 ? '+' : ''}
                      {stat.diff.toFixed(1)}%
                    </span>
                    <DiffIcon size="1rem" stroke={1.5} />
                  </>
                )}
              </Text>
            )}
          </Group>
        </Card>
      </Tooltip>
    )
  })

  return <SimpleGrid cols={{ base: 1, xs: 2, md: 5 }}>{stats}</SimpleGrid>
}
