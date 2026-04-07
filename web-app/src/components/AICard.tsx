import type { DailyPerformanceStats } from '@/api/v1/ai/daily_performance_summary'
import { useDailyPerformanceSummary } from '@/hooks/useDailyPerformanceSummary'
import {
  ActionIcon,
  Box,
  Card,
  Divider,
  Group,
  Loader,
  Stack,
  Text,
  Title,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { IconBrain, IconRefresh } from '@tabler/icons-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'

interface AICardProps {
  stats: DailyPerformanceStats | null
  isLoading?: boolean
  hasBudgetedSeries?: boolean
  hasSelectedDate?: boolean
}

const AICard = ({
  stats,
  isLoading = false,
  hasBudgetedSeries = true,
  hasSelectedDate = false,
}: AICardProps) => {
  const { projectId } = useParams<{ projectId: string }>()
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()
  const [performanceText, setPerformanceText] = useState<string | null>(null)
  const [cmmsText, setCmmsText] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)

  const generateSummary = useDailyPerformanceSummary()

  const handleGenerateSummary = useCallback(async () => {
    if (!stats) return

    setIsGenerating(true)
    try {
      const response = await generateSummary.mutateAsync(stats)
      setPerformanceText(response.summary)
      setCmmsText(response.cmms_tickets_activity ?? null)
    } catch (error) {
      console.error('Failed to generate AI summary:', error)
      setPerformanceText('Unable to generate performance summary at this time.')
      setCmmsText(null)
    } finally {
      setIsGenerating(false)
    }
  }, [stats, generateSummary])

  useEffect(() => {
    setPerformanceText(null)
    setCmmsText(null)
  }, [
    stats?.date,
    stats?.project_id,
    stats?.cmms_period_start,
    stats?.cmms_period_end,
  ])

  useEffect(() => {
    if (stats && !isLoading && !performanceText && !isGenerating) {
      handleGenerateSummary()
    }
  }, [stats, isLoading, performanceText, isGenerating, handleGenerateSummary])

  const cardBgColor =
    colorScheme === 'dark' ? theme.colors.dark[6] : theme.colors.gray[0]
  const borderColor =
    colorScheme === 'dark' ? theme.colors.dark[4] : theme.colors.gray[3]
  const labelColor = colorScheme === 'dark' ? theme.colors.gray[5] : 'dimmed'

  return (
    <Card
      withBorder
      p="md"
      radius="md"
      style={{
        backgroundColor: cardBgColor,
        borderColor: borderColor,
        minHeight: '140px',
      }}
    >
      <Group justify="space-between" align="center" mb="sm">
        <Group align="center" gap="xs">
          <IconBrain size="1rem" stroke={1.5} />
          <Title order={5}>Aria Performance Summary</Title>
        </Group>
        <ActionIcon
          variant="subtle"
          size="sm"
          onClick={handleGenerateSummary}
          loading={isGenerating}
          disabled={!stats}
        >
          <IconRefresh size="1rem" />
        </ActionIcon>
      </Group>

      <Box>
        {!stats ? (
          <Text c="dimmed" size="sm">
            {!hasSelectedDate ? (
              'Select a date to generate AI performance summary'
            ) : !hasBudgetedSeries ? (
              <>
                No budgeted series available. Upload a budgeted series in{' '}
                <Link
                  to={`/projects/${projectId}/settings?tab=pv-budgeted`}
                  style={{ textDecoration: 'underline' }}
                >
                  Settings
                </Link>{' '}
                to generate AI performance summary
              </>
            ) : (
              'Select a date to generate AI performance summary'
            )}
          </Text>
        ) : isLoading ? (
          <Group align="center" gap="xs">
            <Loader size="sm" />
            <Text size="sm" c="dimmed">
              Loading performance data...
            </Text>
          </Group>
        ) : isGenerating ? (
          <Group align="center" gap="xs">
            <Loader size="sm" />
            <Text size="sm" c="dimmed">
              Generating AI summary...
            </Text>
          </Group>
        ) : performanceText ? (
          <Stack gap="sm">
            <Box>
              <Text
                size="xs"
                c={labelColor}
                tt="uppercase"
                fw={700}
                mb={6}
                style={{ letterSpacing: '0.04em' }}
              >
                Performance
              </Text>
              <Text size="sm" style={{ lineHeight: 1.6 }}>
                {performanceText}
              </Text>
            </Box>
            {cmmsText ? (
              <>
                <Divider color={borderColor} />
                <Box>
                  <Text
                    size="xs"
                    c={labelColor}
                    tt="uppercase"
                    fw={700}
                    mb={6}
                    style={{ letterSpacing: '0.04em' }}
                  >
                    CMMS tickets activity
                  </Text>
                  <Text size="sm" style={{ lineHeight: 1.6 }}>
                    {cmmsText}
                  </Text>
                </Box>
              </>
            ) : null}
          </Stack>
        ) : (
          <Text c="dimmed" size="sm">
            Click refresh to generate AI summary
          </Text>
        )}
      </Box>
    </Card>
  )
}

export default AICard
