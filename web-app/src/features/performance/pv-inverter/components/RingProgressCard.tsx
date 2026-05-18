import { RingProgress, Skeleton, Stack, Text } from '@mantine/core'
import type { CSSProperties } from 'react'

type RingProgressCardProps = {
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

export function RingProgressCard({
  title,
  subtitle,
  value,
  total,
  color = 'grey',
  isLoading,
  size = 150,
  skeletonHeight = 111,
  skeletonMargin = 19.5,
}: RingProgressCardProps) {
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
          style={{ '--rp-size': `${size}px` } as CSSProperties}
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
