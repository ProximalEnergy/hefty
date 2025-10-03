import { useGetProjectContracts } from '@/api/v1/operational/project/contracts'
import { PageLoader } from '@/components/Loading'
import {
  Button,
  Container,
  Divider,
  Group,
  Paper,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import dayjs from 'dayjs'
import { useNavigate, useParams } from 'react-router-dom'

const ProjectContract = () => {
  const { projectId, contractId } = useParams()
  const navigate = useNavigate()

  const { data: contracts, isLoading } = useGetProjectContracts({
    pathParams: { projectId: projectId || '-1' },
  })

  const handleNavigateToContracts = () => {
    navigate(`/projects/${projectId}/contracts`)
  }

  if (isLoading) return <PageLoader />

  const contract = contracts?.find((c) => c.contract_id === Number(contractId))

  if (!contract) {
    return (
      <Container fluid pt="md">
        <Text>Contract not found.</Text>
      </Container>
    )
  }

  const documentUrl =
    contract.document_url ||
    (contract.s3_key
      ? `https://proximal-am-documents.s3.amazonaws.com/${contract.s3_key}`
      : null)

  return (
    <Container fluid pt="md">
      <Stack p="sm">
        <Group justify="space-between" align="center">
          <Title order={1}>Contract Details</Title>
          <Button variant="light" size="sm" onClick={handleNavigateToContracts}>
            View all Contracts
          </Button>
        </Group>

        <Paper withBorder p="md">
          <Group justify="space-between" mb="md">
            <Stack gap="xs">
              <Text fw={500} size="lg">
                Counterparty
              </Text>
              <Text>{contract.name_long}</Text>
            </Stack>
            <Stack gap="xs">
              <Text fw={500} size="lg">
                Execution Date
              </Text>
              <Text>
                {dayjs(contract.execution_date).format('MMMM D, YYYY')}
              </Text>
            </Stack>
          </Group>
          <Divider my="md" />

          {/* PDF Viewer */}
          <Stack>
            <Title order={2}>Contract Document</Title>
            {documentUrl ? (
              <iframe
                src={documentUrl}
                style={{
                  width: '100%',
                  height: '800px',
                  border: 'none',
                }}
                title="Contract PDF Viewer"
              />
            ) : (
              <Text>No document available at this url: {documentUrl}</Text>
            )}
          </Stack>
        </Paper>
      </Stack>
    </Container>
  )
}

export default ProjectContract
