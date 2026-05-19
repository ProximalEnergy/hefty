import { OnboardingPageHeader } from '@/pages/onboarding/components/OnboardingPageHeader'
import { AppShell, Container, Stack } from '@mantine/core'
import { useParams } from 'react-router'

function Trackers() {
  const { projectId } = useParams<{ projectId: string }>()

  return (
    <AppShell padding={0}>
      <AppShell.Main>
        <Container size="md" py="xl">
          <Stack gap="lg">
            <OnboardingPageHeader
              title="Trackers"
              description="Configure trackers for this project"
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

export default Trackers
