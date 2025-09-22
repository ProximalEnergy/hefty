import { Center, Stack, Text } from '@mantine/core'
import { IconAlertTriangle, IconChartBarOff } from '@tabler/icons-react'
import { DefaultError } from '@tanstack/react-query'

export const PageError = ({
  error,
  text,
}: {
  error?: DefaultError
  text?: string
}) => {
  let message
  if (error !== undefined) {
    if (error.response) {
      message = error.response.data.detail
    } else {
      message = error.message
    }
  }

  if (text !== undefined) {
    message = text
  }

  // If message is not undefined and is not a string, set it to a default message
  if (
    message !== undefined &&
    typeof message !== 'string' &&
    text !== undefined
  ) {
    message = 'An error occurred'
  }

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <Center h="100%" w="100%">
        <Stack align="center">
          <IconAlertTriangle size={48} />
          {message && <Text>{message}</Text>}
        </Stack>
      </Center>
    </div>
  )
}

export const NoData = ({ text }: { text?: string }) => {
  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <Center h="100%" w="100%">
        <Stack align="center">
          <IconChartBarOff size={48} />
          {text ? <Text>{text}</Text> : <Text>No data</Text>}
        </Stack>
      </Center>
    </div>
  )
}
