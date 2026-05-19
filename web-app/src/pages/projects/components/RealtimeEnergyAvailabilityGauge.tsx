import { getRealtimeGaugeColor } from '@/pages/projects/components/realtimeGaugeUtils'
import { RingProgress, Text, Tooltip } from '@mantine/core'

export const RealtimeEnergyAvailabilityGauge = ({
  value,
  availableStrings,
  totalStrings,
  isLoading,
  onClick,
}: {
  value: number | null
  availableStrings: number | null
  totalStrings: number | null
  isLoading: boolean
  onClick?: () => void
}) => {
  const sectionValue = value != null ? Math.min(100, value) : 0
  const color = value != null ? getRealtimeGaugeColor(value) : 'gray'

  const stringsLabel =
    availableStrings != null && totalStrings != null
      ? `${availableStrings} / ${totalStrings} strings available`
      : '—'

  return (
    <Tooltip label={`Storage Energy Availability: ` + stringsLabel}>
      <RingProgress
        size={32}
        thickness={3}
        onClick={onClick}
        style={
          {
            '--rp-size': '32px',
            cursor: onClick ? 'pointer' : 'default',
          } as React.CSSProperties
        }
        label={
          <Text
            size="11px"
            fw={600}
            ta="center"
            c={value != null ? 'inherit' : 'dimmed'}
            style={{
              lineHeight: 1,
              fontSize: 11,
            }}
          >
            {isLoading ? '…' : value != null ? `${value.toFixed(0)}` : '—'}
          </Text>
        }
        sections={[{ value: sectionValue, color }]}
      />
    </Tooltip>
  )
}
