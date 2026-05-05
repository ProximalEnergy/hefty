import {
  useCreateApiKeyMutation,
  useDeleteApiKeyMutation,
  useGetApiKey,
} from '@/api/v1/admin/api_key'
import {
  ActionIcon,
  Button,
  Group,
  Paper,
  Stack,
  Text,
  Title,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { useClipboard } from '@mantine/hooks'
import { IconClipboard, IconClipboardCheck } from '@tabler/icons-react'

const APIKey = () => {
  const { data, isLoading, error } = useGetApiKey({})
  const createMutation = useCreateApiKeyMutation()
  const deleteMutation = useDeleteApiKeyMutation()

  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('dark')
  const clipboard = useClipboard({ timeout: 1000 })

  if (isLoading) {
    return <div>Loading...</div>
  }

  if (error) {
    return <div>Error: {error.message}</div>
  }

  if (!data) {
    return <div>No data</div>
  }

  return (
    <>
      {data.api_key === null ? (
        <Group>
          <Button onClick={() => createMutation.mutate()}>
            Generate API Key
          </Button>
        </Group>
      ) : (
        <Group>
          <Paper
            p="xs"
            bg={
              computedColorScheme === 'dark'
                ? theme.colors.dark[5]
                : theme.colors.gray[2]
            }
          >
            <Group justify="space-between" gap="xs">
              <Text style={{ wordBreak: 'break-all' }}>{data.api_key}</Text>
              <ActionIcon
                onClick={() => clipboard.copy(data.api_key)}
                color={clipboard.copied ? 'green' : undefined}
              >
                {clipboard.copied ? (
                  <IconClipboardCheck size={18} />
                ) : (
                  <IconClipboard size={18} />
                )}
              </ActionIcon>
            </Group>
          </Paper>
          <Button h="100%" color="red" onClick={() => deleteMutation.mutate()}>
            Delete API Key
          </Button>
        </Group>
      )}
    </>
  )
}

const Api = () => {
  return (
    <Stack p="md" h="100%">
      <Title order={1}>API</Title>
      <Title order={3}>API Key</Title>
      <APIKey />
      <Title order={3}>Client Library</Title>
      <Text>
        A Python client library is available to easily query data from the API.
        Documentation will be available soon.
      </Text>
    </Stack>
  )
}

export default Api
