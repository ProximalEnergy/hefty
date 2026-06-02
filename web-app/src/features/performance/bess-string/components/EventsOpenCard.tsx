import { Card, Group, HoverCard, Skeleton, Stack, Text } from '@mantine/core'
import { IconExclamationCircle } from '@tabler/icons-react'

import { statGridCardStyle } from '@/features/performance/bess-string/utils/stat-grid-card-style'
import type {
  ActiveEventsHoverSection,
  StatsData,
} from '@/features/performance/bess-string/types/bess-string-realtime'

type EventsOpenCardProps = {
  isLoading: boolean
  stats: StatsData
  sections: ActiveEventsHoverSection[]
  onClick: () => void
  onNavigateEvent: (eventId: number) => void
}

export const EventsOpenCard = ({
  isLoading,
  stats,
  sections,
  onClick,
  onNavigateEvent,
}: EventsOpenCardProps) => {
  const hasHoverContent = sections.some((section) => section.count > 0)

  return (
    <HoverCard
      width={360}
      shadow="md"
      openDelay={300}
      closeDelay={100}
      disabled={isLoading}
    >
      <HoverCard.Target>
        <Card
          withBorder
          p="md"
          radius="md"
          style={statGridCardStyle({ cursor: 'pointer' })}
          onClick={onClick}
        >
          <Group justify="space-between" wrap="nowrap" gap="xs">
            <Text size="sm" c="dimmed" lineClamp={1}>
              Active Events
            </Text>
            <IconExclamationCircle
              size="1.2rem"
              stroke={1.5}
              style={{ flexShrink: 0 }}
            />
          </Group>
          <Text fz={32} fw={700} mt={15} component="div">
            {isLoading ? (
              <Skeleton height={32} width="60%" />
            ) : stats.totalEventsCount === 0 ? (
              <Group gap="xs" align="center" wrap="nowrap">
                <div
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    flexShrink: 0,
                    backgroundColor: 'green',
                  }}
                />
                <Text component="span" fz={32} fw={700} truncate>
                  0
                </Text>
              </Group>
            ) : (
              stats.totalEventsCount
            )}
          </Text>
          <Text size="sm" c="dimmed" mt={5} lineClamp={1} component="div">
            {isLoading ? (
              <Skeleton height={16} width="80%" />
            ) : (
              <>
                ${stats.dailyRevenueLoss} daily loss
                {stats.dailyEventLossEnergyMWh > 0 && (
                  <> · {stats.dailyEventLossEnergyMWh.toFixed(1)} MWh</>
                )}
              </>
            )}
          </Text>
        </Card>
      </HoverCard.Target>
      <HoverCard.Dropdown>
        <Stack gap="xs">
          <Text fw={600} size="sm">
            Active Events
          </Text>
          <Text size="xs" c="dimmed">
            Open-event overview by device type. Click to view all events.
          </Text>
          {hasHoverContent
            ? sections.map((section) => (
                <Stack key={section.label} gap={2}>
                  <Text fw={600} size="sm">
                    {section.label} ({section.count})
                  </Text>
                  {section.count > 0 ? (
                    <>
                      {section.events.map((event) => (
                        <Text
                          key={`${section.label}-${event.eventId}`}
                          size="xs"
                          lineClamp={1}
                          style={{ cursor: 'pointer' }}
                          onClick={() => onNavigateEvent(event.eventId)}
                        >
                          {event.label}
                        </Text>
                      ))}
                      {section.remainingCount > 0 && (
                        <Text
                          size="xs"
                          c="dimmed"
                          style={{ cursor: 'pointer' }}
                          onClick={onClick}
                        >
                          +{section.remainingCount} more (click to view)
                        </Text>
                      )}
                    </>
                  ) : (
                    <Text size="xs" c="dimmed">
                      No open events
                    </Text>
                  )}
                </Stack>
              ))
            : sections.map((section) => (
                <Text key={section.label} size="xs" c="dimmed">
                  {section.label}: 0
                </Text>
              ))}
        </Stack>
      </HoverCard.Dropdown>
    </HoverCard>
  )
}
