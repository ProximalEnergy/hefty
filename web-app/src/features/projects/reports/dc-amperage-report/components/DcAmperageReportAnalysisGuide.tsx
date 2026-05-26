import { Stack, Text } from '@mantine/core'

export function DcAmperageReportAnalysisGuide() {
  return (
    <Stack gap="xs">
      <Text fw={600}>How to interpret this matrix</Text>
      <Text size="sm">
        Each cell compares a combiner&apos;s normalized DC current against peer
        combiners, either within the inverter or across the entire project.
      </Text>
      <Text size="sm">Blue: materially below peer expectation</Text>
      <Text size="sm">Gray: performing at or near peer expectation</Text>
      <Text size="sm">Orange: materially above peer expectation</Text>
      <Text size="sm">Both blue and orange indicate abnormal behavior.</Text>
    </Stack>
  )
}
