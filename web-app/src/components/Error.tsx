import { Center, Stack, Text } from '@mantine/core'
import { IconAlertTriangle, IconChartBarOff } from '@tabler/icons-react'
import type { DefaultError } from '@tanstack/react-query'

export const getPageErrorMessage = (error?: DefaultError | null) => {
  if (!error) {
    return undefined
  }

  const detail: unknown = error.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const firstDetail = detail[0] as { msg?: unknown }
    if (typeof firstDetail.msg === 'string') {
      return firstDetail.msg
    }
  }

  return error.message || 'An error occurred'
}

export const PageError = ({
  error,
  text,
}: {
  error?: DefaultError
  text?: string
}) => {
  const message = text ?? getPageErrorMessage(error)

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <Center h="100%" w="100%">
        <Stack align="center">
          <IconAlertTriangle size={48} />
          {message && <Text component="div">{message}</Text>}
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
          {text ? <Text component="div">{text}</Text> : <Text>No data</Text>}
        </Stack>
      </Center>
    </div>
  )
}
