import { Box, useComputedColorScheme, useMantineTheme } from '@mantine/core'

interface StatSparklineProps {
  data: number[]
  width?: number
  height?: number
  color?: string
}

export function StatSparkline({
  data,
  width = 60,
  height = 20,
  color,
}: StatSparklineProps) {
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()
  const sparklineColor =
    color ||
    (colorScheme === 'dark' ? theme.colors.gray[4] : theme.colors.gray[6])

  if (!data || data.length === 0) {
    return null
  }

  // Normalize data to fit in the height
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1 // Avoid division by zero

  const points = data.map((value, index) => {
    const x = (index / (data.length - 1 || 1)) * width
    const y = height - ((value - min) / range) * height
    return `${x},${y}`
  })

  const pathData = `M ${points.join(' L ')}`

  return (
    <Box
      component="svg"
      width={width}
      height={height}
      style={{ overflow: 'visible' }}
    >
      <path
        d={pathData}
        fill="none"
        stroke={sparklineColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Box>
  )
}
