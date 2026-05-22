import { Text } from '@mantine/core'

type RealtimeGaugeValueProps = {
  value: number | null
  isLoading: boolean
}

export const RealtimeGaugeValue = ({
  value,
  isLoading,
}: RealtimeGaugeValueProps) => {
  const display = isLoading ? '…' : value != null ? value.toFixed(0) : '—'
  const isWide = display.length >= 3
  return (
    <Text
      fw={600}
      ta="center"
      c={value != null ? 'inherit' : 'dimmed'}
      ff="monospace"
      style={{
        lineHeight: 1,
        fontSize: isWide ? 9 : 11,
      }}
    >
      {display}
    </Text>
  )
}
