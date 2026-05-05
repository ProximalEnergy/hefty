import { ProjectTypeEnum } from '@/api/enumerations'
import { Project } from '@/api/v1/operational/projects'
import CustomCard from '@/components/CustomCard'
import { EventSummary } from '@/hooks/types'
import { hasMappableEventLocation } from '@/pages/projects/events/ProjectEventOverlayLayers'
import { AdaptiveGisMap } from '@/pages/projects/gis/adaptive-gis'
import AdaptiveGisBESS from '@/pages/projects/gis/adaptive-gis-bess'
import { Badge, Box, Group, List, Stack, Text } from '@mantine/core'

interface ProjectEventsMapProps {
  events: EventSummary[]
  eventMarkersLoading?: boolean
  project: Project | undefined
  /** Events page: map sits in a 40% column next to the table. */
  sideBySideLayout?: boolean
}

const ProjectEventsMap = ({
  events,
  eventMarkersLoading = false,
  project,
  sideBySideLayout = false,
}: ProjectEventsMapProps) => {
  const unmappedCount = events.filter(
    (event) => !hasMappableEventLocation(event),
  ).length
  const isBess = project?.project_type_id === ProjectTypeEnum.BESS

  return (
    <CustomCard
      title="Event Map"
      fill
      bodyStyle={{ height: 'auto' }}
      info={
        <Stack gap="xs">
          <Text fw={600}>Using the map</Text>
          <Text size="sm">
            This is the same project performance map as the homepage, with event
            locations drawn on top. Only events with coordinates appear; the
            unmapped badge counts events that have no map position.
          </Text>
          <List spacing={4} withPadding size="sm">
            <List.Item>
              <Text size="sm">
                <Text span fw={500}>
                  Event types:
                </Text>{' '}
                Open map settings (cog) and use{' '}
                <Text span fw={500}>
                  Event types on map
                </Text>{' '}
                to show or hide markers by device type (only types that appear
                in the current event list are listed). Preferences are saved per
                project, separately for this map and the project home map.
              </Text>
            </List.Item>
            <List.Item>
              <Text size="sm">
                <Text span fw={500}>
                  Zoom:
                </Text>{' '}
                Zoom out to see clusters (one marker per group with an event
                count). Zoom in to split clusters into individual triangular
                markers.
              </Text>
            </List.Item>
          </List>

          <Text fw={600}>Events color scale</Text>
          <Text size="sm">
            Open events use upward-pointing triangles. Color encodes{' '}
            <Text span fw={500}>
              estimated daily financial loss
            </Text>{' '}
            (USD per day): warmer{' '}
            <Text span fw={500} c="red.7">
              red
            </Text>{' '}
            for lower daily loss, through to{' '}
            <Text span fw={500} c="violet.7">
              violet
            </Text>{' '}
            for higher daily loss. The gradient is built for the range from $0
            to $100/day; losses above that still use the strongest violet
            bucket.
          </Text>
          <Text size="sm">
            Marker icons step in{' '}
            <Text span fw={500}>
              $10/day
            </Text>{' '}
            bands (for example $0–9.99, $10–19.99, …, $100 and over). Cluster
            markers use the{' '}
            <Text span fw={500}>
              sum
            </Text>{' '}
            of member events&apos; daily financial losses for that same scale.
            Larger cluster icons mean more events grouped at that location.
          </Text>
          <Text size="sm">
            <Text span fw={500}>
              Closed
            </Text>{' '}
            events use{' '}
            <Text span fw={500} c="gray.7">
              gray
            </Text>{' '}
            triangles with a white checkmark; open events keep the alert-style
            mark inside the triangle.
          </Text>
        </Stack>
      }
      headerChildren={
        <Group gap="xs">
          <Badge variant="light">{events.length} events</Badge>
          {unmappedCount > 0 ? (
            <Badge color="gray" variant="light">
              {unmappedCount} unmapped
            </Badge>
          ) : null}
        </Group>
      }
    >
      <Box h={sideBySideLayout ? 440 : 420} miw={0} w="100%">
        {isBess ? (
          <AdaptiveGisBESS
            eventSummaries={events}
            eventMarkersLoading={eventMarkersLoading}
            forceShowEvents
            disableEventToggle
          />
        ) : (
          <AdaptiveGisMap
            eventSummaries={events}
            eventMarkersLoading={eventMarkersLoading}
            forceShowEvents
            disableEventToggle
          />
        )}
      </Box>
    </CustomCard>
  )
}

export default ProjectEventsMap
