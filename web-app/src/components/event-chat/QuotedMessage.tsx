import { formatMessageBody } from '@/components/event-chat/utils'
import { Group, MantineTheme, Paper, Stack, Text } from '@mantine/core'

interface QuotedMessageProps {
  parentMessageBody: string
  parentUserName: string
  parentMessageDeleted?: boolean
  parentMessageId?: number
  onParentMessageClick?: (messageId: number) => void
  colorScheme: string
  theme: MantineTheme
}

export function QuotedMessage({
  parentMessageBody,
  parentUserName,
  parentMessageDeleted = false,
  parentMessageId,
  onParentMessageClick,
  colorScheme,
  theme,
}: QuotedMessageProps) {
  // Replace image placeholders [IMG:0], [IMG:1], etc. with "[image]" and add newline after
  const processedBody = parentMessageBody.replace(/\[IMG:\d+\]/g, '[image]\n')

  const handleQuotedMessageClick = () => {
    if (parentMessageId && onParentMessageClick) {
      onParentMessageClick(parentMessageId)
    }
  }

  const isClickable = !!parentMessageId && !!onParentMessageClick

  return (
    <Paper
      p="xs"
      onClick={isClickable ? handleQuotedMessageClick : undefined}
      style={{
        backgroundColor:
          colorScheme === 'dark' ? theme.colors.dark[6] : theme.white,
        borderRadius: theme.radius.sm,
        cursor: isClickable ? 'pointer' : 'default',
        transition: 'all 0.2s ease',
      }}
      onMouseEnter={(e) => {
        if (isClickable) {
          e.currentTarget.style.backgroundColor =
            colorScheme === 'dark' ? theme.colors.dark[5] : theme.colors.gray[0]
        }
      }}
      onMouseLeave={(e) => {
        if (isClickable) {
          e.currentTarget.style.backgroundColor =
            colorScheme === 'dark' ? theme.colors.dark[6] : theme.white
        }
      }}
    >
      <Stack gap={2}>
        <Group gap="xs" wrap="nowrap">
          <Text size="xl" c="dimmed" style={{ fontStyle: 'italic' }}>
            &quot;
          </Text>
          <Text size="md" fw={500} c="dimmed" style={{ fontStyle: 'italic' }}>
            {parentUserName}
          </Text>
        </Group>
        {parentMessageDeleted ? (
          <Text
            size="md"
            style={{
              fontStyle: 'italic',
            }}
          >
            This message was deleted.
          </Text>
        ) : (
          <Text
            size="md"
            c="dimmed"
            style={{
              fontStyle: 'italic',
              wordBreak: 'break-word',
              lineHeight: 1.4,
              whiteSpace: 'pre-wrap',
            }}
          >
            {formatMessageBody(
              processedBody,
              colorScheme,
              false,
              theme.primaryColor,
            )}
          </Text>
        )}
      </Stack>
    </Paper>
  )
}
