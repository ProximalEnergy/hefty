import { Button, Stack, Text, rem } from '@mantine/core'
import { IconBoltOff } from '@tabler/icons-react'
import { useNavigate } from 'react-router'

interface FallbackComponentProps {
  resetError: () => void
}

export function FallbackComponent({ resetError }: FallbackComponentProps) {
  const navigate = useNavigate()

  const handleGoHome = () => {
    // Use the navigate function to change the URL
    navigate('/')
    resetError()
  }

  return (
    <Stack h="100vh" w="100vw" align="center" justify="center">
      <IconBoltOff
        style={{ width: rem(160), height: rem(160) }}
        stroke={1}
        color="var(--mantine-color-red-filled)"
      />
      <Text ta="center">
        Oops! It looks like an error occurred on our side. Please reach out to{' '}
        <a href="mailto:support@proximal.energy" style={{ color: 'inherit' }}>
          support@proximal.energy
        </a>{' '}
        if this issue continues.
      </Text>
      <Button variant="default" onClick={handleGoHome}>
        Back to Home
      </Button>
    </Stack>
  )
}
