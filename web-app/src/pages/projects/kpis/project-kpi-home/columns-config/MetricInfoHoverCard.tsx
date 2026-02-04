// Metric info icon component that displays a description, units, and thresholds in a hover card.
// Used with KPI metric info icons to provide detailed context about KPI metrics.
import { HoverCard, Stack, Text } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'

type MetricInfoHoverCardProps = {
  description: string
  unit?: string | null
  critical_low?: number | null
  warning_low?: number | null
  warning_high?: number | null
  critical_high?: number | null
}

const formatThresholdValue = (
  value: number,
  unit: string | null | undefined,
): string => {
  const fractionDigits = value > 100 ? 0 : 1
  if (unit === '%') {
    return value.toLocaleString('en-US', {
      style: 'percent',
      maximumFractionDigits: fractionDigits,
      minimumFractionDigits: fractionDigits,
    })
  } else {
    const formatted = value.toLocaleString('en-US', {
      style: 'decimal',
      maximumFractionDigits: fractionDigits,
      minimumFractionDigits: fractionDigits,
    })
    return unit ? `${formatted} ${unit}` : formatted
  }
}

const MetricInfoHoverCard = ({
  description,
  unit,
  critical_low,
  warning_low,
  warning_high,
  critical_high,
}: MetricInfoHoverCardProps) => {
  const hasThresholds =
    (critical_low !== null && critical_low !== undefined) ||
    (warning_low !== null && warning_low !== undefined) ||
    (warning_high !== null && warning_high !== undefined) ||
    (critical_high !== null && critical_high !== undefined)

  return (
    <HoverCard shadow="md" withArrow position="right">
      <HoverCard.Target>
        <IconInfoCircle
          size={14}
          stroke={1.5}
          style={{ display: 'block', cursor: 'help' }}
        />
      </HoverCard.Target>
      <HoverCard.Dropdown maw={300}>
        <Stack gap="xs">
          <Text
            size="xs"
            style={{ whiteSpace: 'normal', wordWrap: 'break-word' }}
          >
            {description}
          </Text>
          {hasThresholds && (
            <Stack gap={2}>
              <Text size="xs" fw={600}>
                Thresholds:
              </Text>
              {critical_high !== null && critical_high !== undefined && (
                <Text size="xs" c="red">
                  Critical High: {formatThresholdValue(critical_high, unit)}
                </Text>
              )}
              {warning_high !== null && warning_high !== undefined && (
                <Text size="xs" c="orange">
                  Warning High: {formatThresholdValue(warning_high, unit)}
                </Text>
              )}
              {warning_low !== null && warning_low !== undefined && (
                <Text size="xs" c="orange">
                  Warning Low: {formatThresholdValue(warning_low, unit)}
                </Text>
              )}
              {critical_low !== null && critical_low !== undefined && (
                <Text size="xs" c="red">
                  Critical Low: {formatThresholdValue(critical_low, unit)}
                </Text>
              )}
            </Stack>
          )}
        </Stack>
      </HoverCard.Dropdown>
    </HoverCard>
  )
}

export default MetricInfoHoverCard
