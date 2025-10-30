import { AppShell, Container, Stack } from '@mantine/core'
import { useParams } from 'react-router'

import { OnboardingPageHeader } from '../components/OnboardingPageHeader'

function Combiners() {
  const { projectId } = useParams<{ projectId: string }>()

  return (
    <AppShell padding={0}>
      <AppShell.Main>
        <Container size="md" py="xl">
          <Stack gap="lg">
            <OnboardingPageHeader
              title="Combiners"
              description="Configure combiners for this project"
              projectId={projectId}
              backPath={`/onboarding/${projectId}/devices`}
              backTooltip="Back to Device Overview"
            />
          </Stack>
        </Container>
      </AppShell.Main>
    </AppShell>
  )
}

export default Combiners
