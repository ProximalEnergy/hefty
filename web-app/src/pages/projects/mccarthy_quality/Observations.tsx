import { PageLoader } from '@/components/Loading'
import { useGetObservations } from '@/hooks/api'
import { Anchor, Paper, Stack, Text } from '@mantine/core'
import { useParams } from 'react-router'

export default function Observations() {
  const { projectId } = useParams<{ projectId: string }>()

  const observations = useGetObservations({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  if (!observations.data) {
    return <PageLoader />
  }

  return (
    <Stack p="md" gap="md">
      {observations.data.slice(0, 25).map((observation) => (
        <Paper key={observation.id} p="md" withBorder>
          <Text size="lg" fw={700}>
            {observation.type}
          </Text>
          <Text>{observation.description}</Text>
          <Text>ID: {observation.id}</Text>
          {observation.created && (
            <Text>Date: {observation.created.slice(0, 10)}</Text>
          )}
          <Text>Status: {observation.status}</Text>
          <Anchor
            href={`https://app.procore.com/2000024/project/observations/items/${observation.id}`}
            target="_blank"
          >
            Procore
          </Anchor>
        </Paper>
      ))}
    </Stack>
  )
}
