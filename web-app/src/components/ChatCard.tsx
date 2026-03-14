import { ProjectTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useAuth, useUser } from '@clerk/react'
import {
  ActionIcon,
  Box,
  Button,
  Group,
  Loader,
  MantineColorScheme,
  MantineTheme,
  Paper,
  ScrollArea,
  Stack,
  Text,
  Textarea,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconSend } from '@tabler/icons-react'
import MarkdownIt from 'markdown-it'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router'
import { v4 as uuidv4 } from 'uuid'

interface Context {
  metadata: {
    page: number
    source: string
  }
  page_content: string
  type: string
}

export interface IStep {
  id: string
  role: string
  type: 'user_message' | 'bot_message' | 'image' | 'loader'
  content: string
  createdAt: string
  context?: Context[]
}

const INITIAL_QUESTION_OPTIONS: {
  question: string
  type: 'pv' | 'bess' | null
}[] = [
  {
    question:
      'Can you group events for the last 30 days by failure mode and display their cumulative losses?',
    type: 'pv',
  },
  { question: 'Which PV module is used in the project?', type: 'pv' },
  {
    question:
      'Our last inverter inspection was on 4/3/2024, when is the next one due?',
    type: null,
  },
  {
    question: 'What is the emergency shutdown procedure of the project?',
    type: null,
  },
  {
    question: 'What was the average project meter power between 2-3pm today?',
    type: null,
  },
  {
    question: "Plot yesterday's project active power meter output",
    type: null,
  },
  {
    question: 'What type of battery is used in the project?',
    type: 'bess',
  },
]

const environment = import.meta.env.VITE_ENVIRONMENT
const chatUrlOverride = import.meta.env.VITE_CHAT_WS_URL?.trim()

let url: string
if (chatUrlOverride) {
  url = chatUrlOverride
} else if (
  environment === 'PRODUCTION' ||
  environment === 'STAGING' ||
  environment === 'SANDBOX'
) {
  url = 'wss://chat.proximal.energy/ws'
} else {
  url = 'ws://127.0.0.1:8001/ws'
}

export function ChatCard({
  messages,
  setMessages,
  firstQuestionAsked,
  setFirstQuestionAsked,
}: {
  messages: IStep[]
  setMessages: React.Dispatch<React.SetStateAction<IStep[]>>
  firstQuestionAsked: boolean
  setFirstQuestionAsked: React.Dispatch<React.SetStateAction<boolean>>
}) {
  const { projectId } = useParams<{ projectId: string }>()
  const { user } = useUser()
  const [inputValue, setInputValue] = useState('')
  const [isLoading] = useState(false)
  const viewportRef = useRef<HTMLDivElement>(null)
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()
  const ws = useRef<WebSocket | null>(null)
  const { getToken } = useAuth()

  const project = useSelectProject(projectId!)

  const markdown = useMemo(() => new MarkdownIt(), [])

  const renderMarkdown = (content: string) => {
    const renderedContent = markdown.render(content)
    const styledContent = renderedContent
      .replace(/<p>/g, '<p style="margin: 0">')
      .replace(
        /<code>/g,
        '<code style="color: white; font-size: 0.875em; background-color: #333333; padding: 2px 4px; border-radius: 4px;">',
      )
      .replace(
        /<pre>/g,
        '<pre style="color: white; font-size: 0.875em; background-color: #333333; padding: 10px; border-radius: 4px; overflow-x: auto;">',
      )
      .replace(
        // Add style to images to set max width:
        /<img/g,
        '<img style="width: 100%; height: auto;"',
      )
    return { __html: styledContent }
  }

  useEffect(() => {
    ws.current = new WebSocket(url)
    ws.current.onmessage = (event) => {
      try {
        const messageData = JSON.parse(event.data)

        setMessages((msgs) => {
          const lastMessage = msgs[msgs.length - 1]
          if (messageData.type === 'text') {
            if (lastMessage && lastMessage.role === 'bot') {
              const updatedLastMessage = {
                ...lastMessage,
                content: lastMessage.content + messageData.content,
              }
              return [...msgs.slice(0, -1), updatedLastMessage]
            } else {
              const botMessage: IStep = {
                id: uuidv4(),
                role: 'bot',
                type: 'bot_message',
                content: messageData.content,
                createdAt: new Date().toISOString(),
              }
              return [...msgs, botMessage]
            }
          } else if (messageData.type === 'image') {
            const updatedLastMessage = {
              ...lastMessage,
              content:
                lastMessage.content +
                `![Output Image](data:image/png;base64,${messageData.content})`,
            }
            return [...msgs.slice(0, -1), updatedLastMessage]
          } else if (messageData.type === 'loader') {
            const loaderMessage: IStep = {
              id: uuidv4(),
              role: 'bot',
              type: 'loader',
              content: `${messageData.content}`,
              createdAt: new Date().toISOString(),
            }
            return [...msgs, loaderMessage]
          }
          return msgs // Ensure msgs is always returned
        })
      } catch (error) {
        console.error(
          'Failed to parse WebSocket message:',
          error,
          'Raw data:',
          event.data,
        )
        notifications.show({
          title: 'Chat Error',
          message:
            'Received an unexpected message from the server. Please try again.',
          color: 'red',
        })
      }
    }

    return () => {
      ws.current?.close()
    }
  }, [setMessages])

  useEffect(() => {
    if (viewportRef.current) {
      viewportRef.current.scrollTo({
        top: viewportRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [messages])

  if (!user?.id) return null
  if (!projectId) return null

  const handleQuestionSelect = (question: string) => {
    handleSendMessage(question)
  }

  if (!project.data) return null

  const InitialQuestionButtons = () => {
    return (
      <Stack align="flex-start">
        {INITIAL_QUESTION_OPTIONS.filter((question) => {
          if (project.data?.project_type_id === ProjectTypeEnum.PV) {
            return question.type !== 'bess'
          } else if (project.data?.project_type_id === ProjectTypeEnum.BESS) {
            return question.type !== 'pv'
          } else {
            return true
          }
        }).map((question, index) => (
          <Button
            key={index}
            onClick={() => handleQuestionSelect(question.question)}
            variant="outline"
            size="xs"
          >
            {question.question}
          </Button>
        ))}
      </Stack>
    )
  }

  const handleSendMessage = async (message: string) => {
    const token = await getToken({ template: 'default' })

    if (message) {
      setFirstQuestionAsked(true)
      const userMessage: IStep = {
        id: uuidv4(),
        role: 'user',
        type: 'user_message',
        content: message,
        createdAt: new Date().toISOString(),
      }

      setMessages((msgs) => [...msgs, userMessage])
      setInputValue('')

      const payload = {
        message,
        chat_history: messages.map((msg) => msg.content),
        project_id: projectId,
        user_id: user.id,
        token: token,
        session_id: projectId,
      }

      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify(payload))
      } else {
        setTimeout(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify(payload))
          } else {
            console.error(
              'WebSocket is not open. readyState:',
              ws.current?.readyState,
            )
          }
        }, 500)
      }
    }
  }

  const ContextButtons = ({
    context,
    colorScheme,
    theme,
  }: {
    context: Context[]
    colorScheme: MantineColorScheme
    theme: MantineTheme
  }) => {
    const [activeIndex, setActiveIndex] = useState<number | null>(null)

    const getFilename = (source: string) => {
      const parts = source.split('/')
      return parts[parts.length - 1]
    }

    const toggleActiveIndex = (index: number) => {
      if (activeIndex === index) {
        setActiveIndex(null)
      } else {
        setActiveIndex(index)
      }
    }

    const referenceDetailStyle = {
      color:
        colorScheme === 'dark' ? theme.colors.dark[0] : theme.colors.gray[7],
      fontWeight: 'bold',
    }

    return (
      <>
        <Group pt="sm" justify="space-between">
          {context.map((_, index) => (
            <Button
              key={index}
              size="xs"
              variant={activeIndex === index ? 'filled' : 'outline'}
              onClick={() => toggleActiveIndex(index)}
              style={{
                backgroundColor:
                  activeIndex === index
                    ? colorScheme === 'dark'
                      ? theme.colors.dark[5]
                      : theme.colors.gray[2]
                    : 'transparent',
                color:
                  colorScheme === 'dark'
                    ? theme.colors.dark[0]
                    : theme.colors.gray[7],
                border: `1px solid ${
                  colorScheme === 'dark'
                    ? theme.colors.dark[4]
                    : theme.colors.gray[4]
                }`,
              }}
            >
              {`Ref. ${index + 1}`}
            </Button>
          ))}
        </Group>
        {activeIndex !== null && (
          <Box mt="xs">
            <Text size="xs" style={referenceDetailStyle}>
              {`Page ${context[activeIndex].metadata.page} of ${getFilename(
                context[activeIndex].metadata.source,
              )}`}
            </Text>
            <Text
              size="xs"
              c={
                colorScheme === 'dark'
                  ? theme.colors.dark[0]
                  : theme.colors.gray[7]
              }
            >
              {context[activeIndex].page_content}
            </Text>
          </Box>
        )}
      </>
    )
  }

  const renderMessage = (message: IStep) => {
    const isUserMessage = message.type === 'user_message'
    function determineTextColor(hex: string) {
      const sanitizedHex = hex.replace(/^#/, '')

      const bigint = parseInt(sanitizedHex, 16)
      const r = (bigint >> 16) & 255
      const g = (bigint >> 8) & 255
      const b = bigint & 255

      const linearize = (value: number): number => {
        const normalizedValue = value / 255 // Normalize to 0-1
        return normalizedValue <= 0.03928
          ? normalizedValue / 12.92
          : Math.pow((normalizedValue + 0.055) / 1.055, 2.4)
      }

      const rLin = linearize(r)
      const gLin = linearize(g)
      const bLin = linearize(b)

      const luminance = 0.2126 * rLin + 0.7152 * gLin + 0.0722 * bLin

      return luminance > 0.179 ? 'black' : 'white'
    }

    const userTextColor = determineTextColor(
      theme.colors[theme.primaryColor][7],
    )
    const contextElements =
      message.context && message.context.length > 0 ? (
        <ContextButtons
          context={message.context}
          colorScheme={colorScheme}
          theme={theme}
        />
      ) : null

    return (
      <Group
        key={message.id}
        w="100%"
        justify={isUserMessage ? 'flex-end' : 'flex-start'}
      >
        <Paper
          p="xs"
          maw={600}
          color={theme.primaryColor}
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
            dangerouslySetInnerHTML={renderMarkdown(message.content)}
          />
          {contextElements}
        </Paper>
      </Group>
    )
  }

  return (
    <Stack p="md" h={400} w={700} justify="space-between">
      {!firstQuestionAsked ? (
        <InitialQuestionButtons />
      ) : (
        <ScrollArea w="100%" flex={1} viewportRef={viewportRef}>
          <Stack w="100%" gap="sm">
            {messages.map(renderMessage)}
            {isLoading && (
              <div
                style={{
                  position: 'absolute',
                  bottom: 10,
                  left: '50%',
                  transform: 'translateX(-50%)',
                }}
              >
                <Loader size="sm" />
              </div>
            )}
          </Stack>
        </ScrollArea>
      )}
      <Textarea
        placeholder="Ask anything about this asset..."
        autosize
        value={inputValue}
        onChange={(event) => setInputValue(event.currentTarget.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            handleSendMessage(inputValue)
          }
        }}
        minRows={1}
        maxRows={4}
        rightSection={
          <ActionIcon
            disabled={inputValue.length === 0}
            size="sm"
            variant="transparent"
          >
            <IconSend
              onClick={() => handleSendMessage(inputValue)}
              width={'100%'}
            />
          </ActionIcon>
        }
        w="100%"
        autoFocus
      />
    </Stack>
  )
}
