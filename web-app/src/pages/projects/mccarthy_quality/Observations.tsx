import { PageLoader } from '@/components/Loading'
import { useGetObservations } from '@/hooks/api'
import { Paper, Stack, Text } from '@mantine/core'
import { Link, useParams } from 'react-router-dom'

export default function Observations() {
  const { projectId } = useParams()

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
          <Link
            to={`https://app.procore.com/2000024/project/observations/items/${observation.id}`}
            target="_blank"
            style={{ color: 'inherit' }}
          >
            Procore
          </Link>
        </Paper>
      ))}
    </Stack>
  )
}
