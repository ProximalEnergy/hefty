import { ActionIcon, Group, Text, Title, Tooltip } from '@mantine/core'
import { IconArrowLeft } from '@tabler/icons-react'
import { useNavigate } from 'react-router'

interface OnboardingPageHeaderProps {
  title: string
  description: string
  projectId?: string
  backPath?: string
  backTooltip?: string
}

export function OnboardingPageHeader({
  title,
  description,
  projectId,
  backPath = '/portfolio?tab=onboarding',
  backTooltip = 'Back to Portfolio Home',
}: OnboardingPageHeaderProps) {
  const navigate = useNavigate()

  return (
    <Group gap="md" justify="space-between">
      <Group gap="md">
        <ActionIcon
          variant="subtle"
          color="gray"
          size="lg"
          onClick={() => navigate(backPath)}
        >
          <Tooltip label={backTooltip}>
            <IconArrowLeft size={20} />
          </Tooltip>
        </ActionIcon>
        <div>
          <Title order={1}>{title}</Title>
          <Text c="dimmed">
            {description}
            {projectId && ` for Project ID: ${projectId}`}
          </Text>
        </div>
      </Group>
    </Group>
  )
}
