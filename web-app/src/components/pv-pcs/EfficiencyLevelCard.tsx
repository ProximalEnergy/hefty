import { Card, Group, Text } from '@mantine/core'

interface EfficiencyLevelCardProps {
  avgEfficiency: string
}

export const EfficiencyLevelCard = ({
  avgEfficiency,
}: EfficiencyLevelCardProps) => {
  if (avgEfficiency === 'N/A') {
    return null
  }

  return (
    <Card withBorder p="md" radius="md">
      <Group justify="space-between">
        <Text size="sm" c="dimmed">
          Efficiency Level (Last Hour)
        </Text>
        <Text fz={24} fw={700}>
          {avgEfficiency}
        </Text>
      </Group>
    </Card>
  )
}
