import { EventChat as SharedEventChat } from '@/components/EventChat'

type EventChatProps = {
  eventId: number
  projectId: string
}

export function EventChatShim({ eventId, projectId }: EventChatProps) {
  return <SharedEventChat eventId={eventId} projectId={projectId} />
}
