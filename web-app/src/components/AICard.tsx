import type { DailyPerformanceStats } from '@/api/v1/ai/daily_performance_summary'
import { useDailyPerformanceSummary } from '@/hooks/useDailyPerformanceSummary'
import {
  ActionIcon,
  Box,
  Card,
  Group,
  Loader,
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
  const [summary, setSummary] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)

  const generateSummary = useDailyPerformanceSummary()

  const handleGenerateSummary = useCallback(async () => {
    if (!stats) return

    setIsGenerating(true)
    try {
      const response = await generateSummary.mutateAsync(stats)
      setSummary(response.summary)
    } catch (error) {
      console.error('Failed to generate AI summary:', error)
      setSummary('Unable to generate performance summary at this time.')
    } finally {
      setIsGenerating(false)
    }
  }, [stats, generateSummary])

  // Auto-generate summary when stats change and data is fully loaded
  useEffect(() => {
    if (stats && !isLoading && !summary && !isGenerating) {
      handleGenerateSummary()
    }
  }, [stats, isLoading, summary, isGenerating, handleGenerateSummary])

  const cardBgColor =
    colorScheme === 'dark' ? theme.colors.dark[6] : theme.colors.gray[0]
  const borderColor =
    colorScheme === 'dark' ? theme.colors.dark[4] : theme.colors.gray[3]

  return (
    <Card
      withBorder
      p="md"
      radius="md"
      style={{
        backgroundColor: cardBgColor,
        borderColor: borderColor,
        minHeight: '120px',
        maxHeight: '150px',
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
        ) : summary ? (
          <Text size="md" style={{ lineHeight: 1.4 }}>
            {summary}
          </Text>
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
