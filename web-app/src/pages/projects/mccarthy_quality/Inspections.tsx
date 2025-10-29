import { PageLoader } from '@/components/Loading'
import { useGetInspections } from '@/hooks/api'
import { Anchor, Paper, Stack, Text } from '@mantine/core'
import { useParams } from 'react-router'

export default function Inspections() {
  const { projectId } = useParams()

  const inspections = useGetInspections({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  if (!inspections.data) {
    return <PageLoader />
  }

  return (
    <Stack p="md" gap="md">
      {inspections.data.slice(0, 25).map((inspection) => (
        <Paper key={inspection.id} p="md" withBorder>
          <Text size="lg" fw={700}>
            {inspection.inspection}
          </Text>
          <Text>ID: {inspection.id}</Text>
          {inspection.date && <Text>Date: {inspection.date.slice(0, 10)}</Text>}
          <Text>Status: {inspection.status}</Text>
          <Anchor
            href={`https://app.procore.com/2000024/project/checklists/lists/${inspection.id}`}
            target="_blank"
          >
            Procore
          </Anchor>
        </Paper>
      ))}
    </Stack>
  )
}
