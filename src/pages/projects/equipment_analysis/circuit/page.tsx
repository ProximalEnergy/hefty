import {
  Alert,
  Group,
  RingProgress,
  Skeleton,
  Stack,
  Text,
} from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'

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

const CircuitPage = () => {
  return (
    <Stack p="md">
      <Alert
        icon={<IconInfoCircle size={16} />}
        title="Placeholder Data"
        color="yellow"
      >
        These gauges are placeholders and will be connected to data in a future
        update. If you would like to see any specific plots, please let us know
        via the feedback button at the bottom left of the navigation sidebar.
        The Proximal Team is grateful for your feedback!
      </Alert>
      <Group w="100%" justify="space-evenly" align="flex-end">
        <RingProgressCard
          title="Power Output"
          subtitle="Out of nameplate capacity (Example Only)"
          value={80}
          total={100}
          isLoading={false}
          color="grey"
        />
        <RingProgressCard
          title="Circuits"
          subtitle="Generating Power (Example Only)"
          value={4}
          total={5}
          isLoading={false}
          color="grey"
        />
      </Group>
    </Stack>
  )
}

export default CircuitPage
