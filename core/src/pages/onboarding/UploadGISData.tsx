import { AppShell, Container, Stack } from '@mantine/core'
import { useParams } from 'react-router-dom'

import { OnboardingPageHeader } from './components/OnboardingPageHeader'

function UploadGISData() {
  const { projectId } = useParams<{ projectId: string }>()

  return (
    <AppShell padding={0}>
      <AppShell.Main>
        <Container size="md" py="xl">
          <Stack gap="lg">
            <OnboardingPageHeader
              title="Upload GIS Data"
              description="This page is currently under development."
              projectId={projectId}
            />
          </Stack>
        </Container>
      </AppShell.Main>
    </AppShell>
  )
}

export default UploadGISData
