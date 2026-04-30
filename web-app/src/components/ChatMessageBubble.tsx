import { determineTextColor } from '@/utils/colors'
import {
  Group,
  Paper,
  Text,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import React from 'react'

interface ChatMessageBubbleProps {
  isUserMessage: boolean
  contentHtml: { __html: string }
  contextElements?: React.ReactNode
  maxWidth?: number | string
  paperColor?: string
}

export function ChatMessageBubble({
  isUserMessage,
  contentHtml,
  contextElements,
  maxWidth,
  paperColor,
}: ChatMessageBubbleProps) {
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()

  const userTextColor = determineTextColor(theme.colors[theme.primaryColor][7])

  return (
    <Group w="100%" justify={isUserMessage ? 'flex-end' : 'flex-start'}>
      <Paper
        p="xs"
        maw={maxWidth}
        color={paperColor}
        style={{
          backgroundColor: isUserMessage
            ? theme.colors[theme.primaryColor][7]
            : colorScheme === 'dark'
              ? theme.colors.dark[7]
              : theme.colors.gray[1],
        }}
      >
        <Text
          size="sm"
          c={
            isUserMessage
              ? userTextColor
              : colorScheme === 'dark'
                ? theme.colors.dark[0]
                : theme.colors.dark[7]
          }
          dangerouslySetInnerHTML={contentHtml}
        />
        {contextElements}
      </Paper>
    </Group>
  )
}
