import { Card } from '@mantine/core'
import EventGISCard from '@/components/EventGISCard'

type EventGISProps = {
  deviceId: number
}

export function EventGIS({ deviceId }: EventGISProps) {
  return (
    <Card withBorder w="100%" h="100%" p={0} radius="md">
      <EventGISCard animateToDevice deviceId={deviceId.toString()} />
    </Card>
  )
}
