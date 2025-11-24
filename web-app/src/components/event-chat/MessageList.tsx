import {
  Avatar,
  Group,
  MantineTheme,
  Paper,
  ScrollArea,
  Stack,
  Text,
} from '@mantine/core'
import { IconLock, IconUsers } from '@tabler/icons-react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import utc from 'dayjs/plugin/utc'
import { useEffect, useRef, useState } from 'react'

import { EditMessageForm } from './EditMessageForm'
import {
  MessageBodyWithImages,
  MessageReactions,
  MessageToolbar,
  QuotedMessage,
} from './index'

dayjs.extend(utc)
dayjs.extend(relativeTime)

interface Message {
  event_message_id: number
  user_id: string
  body: string
  created_at: string
  edited_at?: string | null
  deleted_at?: string | null
  private: boolean
  parent_message_id?: number | null
  parentMessage?: Message | undefined
  event_id: number
}

interface MessageListProps {
  messages: Message[]
  isLoading: boolean
  eventId: number
  projectId: string
  userIdToName: Map<string, string>
  userIdToImageUrl: Map<string, string>
  currentUserId: string | undefined
  isCurrentUser: (userId: string) => boolean
  getUserInitials: (name: string) => string
  formatTimestamp: (date: string) => string
  formatEditedTimestamp: (date: string) => string
  hoveredMessageId: number | null
  setHoveredMessageId: (id: number | null) => void
  editingMessageId: number | null
  editMessageValue: string
  setEditMessageValue: (value: string) => void
  editInlineImages: Array<{
    id: string
    file?: File
    position: number
    preview: string
    imageId?: string
    placeholderIndex?: number
  }>
  setEditInlineImages: (
    updater: (
      prev: Array<{
        id: string
        file?: File
        position: number
        preview: string
        imageId?: string
        placeholderIndex?: number
      }>,
    ) => Array<{
      id: string
      file?: File
      position: number
      preview: string
      imageId?: string
      placeholderIndex?: number
    }>,
  ) => void
  handleUpdateMessage: () => void
  handleCancelEdit: () => void
  updateMessagePending: boolean
  addReactionMessageId: number | null
  setAddReactionMessageId: (id: number | null) => void
  handleReactionClick: (
    messageId: number,
    reactionType: string,
    event: React.MouseEvent,
  ) => void
  handleReplyClick: (
    messageId: number,
    parentUserName: string,
    messageBody: string,
  ) => void
  handleEditClick: (messageId: number) => void
  handleDeleteClick: (messageId: number) => void
  emojiReactions: Array<{ emoji: string; type: string; label: string }>
  colorScheme: string
  theme: MantineTheme
  borderColor: string
  animatingMessageIds: Set<number>
  commonEmojis: string[]
  emojiPickerOpen: boolean
  setEmojiPickerOpen: (open: boolean) => void
  user?: { id: string; hasImage?: boolean; imageUrl?: string }
  onScrollToMessage?: (messageId: number) => void
  setMessageRef?: (messageId: number, element: HTMLDivElement | null) => void
  reactionsByMessageId: Map<
    number,
    | Array<{
        reaction_id: number
        event_message_id: number
        user_id: string
        reaction_type: string
        created_at: string
      }>
    | undefined
  >
}

export function MessageList({
  messages,
  isLoading,
  eventId,
  projectId,
  userIdToName,
  userIdToImageUrl,
  currentUserId,
  isCurrentUser,
  getUserInitials,
  formatTimestamp,
  formatEditedTimestamp,
  hoveredMessageId,
  setHoveredMessageId,
  editingMessageId,
  editMessageValue,
  setEditMessageValue,
  editInlineImages,
  setEditInlineImages,
  handleUpdateMessage,
  handleCancelEdit,
  updateMessagePending,
  addReactionMessageId,
  setAddReactionMessageId,
  handleReactionClick,
  handleReplyClick,
  handleEditClick,
  handleDeleteClick,
  emojiReactions,
  colorScheme,
  theme,
  borderColor,
  animatingMessageIds,
  commonEmojis,
  emojiPickerOpen,
  setEmojiPickerOpen,
  user,
  onScrollToMessage,
  setMessageRef,
  reactionsByMessageId,
}: MessageListProps) {
  const [highlightedMessageId, setHighlightedMessageId] = useState<
    number | null
  >(null)

  // Handle highlighting when a message is scrolled to
  useEffect(() => {
    if (highlightedMessageId) {
      const timeout = setTimeout(() => {
        setHighlightedMessageId(null)
      }, 2000) // Highlight for 2 seconds
      return () => clearTimeout(timeout)
    }
  }, [highlightedMessageId])

  const handleParentMessageClick = (messageId: number) => {
    if (onScrollToMessage) {
      onScrollToMessage(messageId)
      setHighlightedMessageId(messageId)
    }
  }
  const viewportRef = useRef<HTMLDivElement>(null)

  return (
    <ScrollArea
      viewportRef={viewportRef}
      style={{ flex: 1, minHeight: 0 }}
      p="md"
    >
      <Stack gap="md" style={{ paddingBottom: '2rem' }}>
        {isLoading ? (
          <Text c="dimmed" size="sm" ta="center" py="xl">
            Loading messages...
          </Text>
        ) : messages && messages.length > 0 ? (
          messages.map((message, index) => {
            const userName =
              userIdToName.get(message.user_id) || `User ${message.user_id}`
            const isCurrentUserMessage = isCurrentUser(message.user_id)
            const initials = getUserInitials(userName)
            const isFirstMessage = index === 0

            const parentMessage = message.parentMessage
            const parentUserName = parentMessage
              ? userIdToName.get(parentMessage.user_id) ||
                `User ${parentMessage.user_id}`
              : undefined

            const isHighlighted =
              highlightedMessageId === message.event_message_id

            return (
              <Group
                ref={(el) => setMessageRef?.(message.event_message_id, el)}
                key={message.event_message_id}
                align="flex-start"
                gap="sm"
                wrap="nowrap"
                className={
                  animatingMessageIds.has(message.event_message_id)
                    ? 'message-animate-in'
                    : ''
                }
                style={{
                  position: 'relative',
                  width: '100%',
                  backgroundColor: isHighlighted
                    ? colorScheme === 'dark'
                      ? theme.colors[theme.primaryColor][9]
                      : theme.colors[theme.primaryColor][0]
                    : 'transparent',
                  borderRadius: theme.radius.md,
                  padding: isHighlighted ? theme.spacing.xs : 0,
                  transition: 'background-color 0.3s ease, padding 0.3s ease',
                }}
              >
                {!isCurrentUserMessage && (
                  <Avatar
                    src={userIdToImageUrl.get(message.user_id) || undefined}
                    alt={userName}
                    size={message.parent_message_id ? 'sm' : 'md'}
                    radius="xl"
                  >
                    {initials}
                  </Avatar>
                )}
                <Stack
                  gap={4}
                  style={{
                    flex: 1,
                    minWidth: 0,
                    alignItems: isCurrentUserMessage
                      ? 'flex-end'
                      : 'flex-start',
                  }}
                >
                  {!isCurrentUserMessage && (
                    <Group gap="xs" wrap="nowrap" align="center">
                      <Text size="md" fw={500} style={{ lineHeight: 1.2 }}>
                        {userName}
                      </Text>
                      <Group gap={4} wrap="nowrap" align="center">
                        <Text size="sm" c="dimmed" style={{ lineHeight: 1.2 }}>
                          {formatTimestamp(message.created_at)}
                        </Text>
                        {message.edited_at && (
                          <Text
                            size="sm"
                            c="dimmed"
                            style={{
                              lineHeight: 1.2,
                              fontStyle: 'italic',
                              cursor: 'help',
                            }}
                            title={`Edited ${formatEditedTimestamp(message.edited_at)}`}
                          >
                            edited
                          </Text>
                        )}
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                          }}
                          title={
                            message.private
                              ? 'Your colleagues'
                              : 'Companies with project access'
                          }
                        >
                          {message.private ? (
                            <IconLock size={14} style={{ opacity: 0.6 }} />
                          ) : (
                            <IconUsers size={14} style={{ opacity: 0.6 }} />
                          )}
                        </span>
                      </Group>
                    </Group>
                  )}
                  {isCurrentUserMessage && (
                    <Group
                      gap="xs"
                      wrap="nowrap"
                      align="center"
                      style={{ justifyContent: 'flex-end' }}
                    >
                      <Group gap={4} wrap="nowrap" align="center">
                        <Text size="sm" c="dimmed" style={{ lineHeight: 1.2 }}>
                          {formatTimestamp(message.created_at)}
                        </Text>
                        {message.edited_at && (
                          <Text
                            size="sm"
                            c="dimmed"
                            style={{
                              lineHeight: 1.2,
                              fontStyle: 'italic',
                              cursor: 'help',
                            }}
                            title={`Edited ${formatEditedTimestamp(message.edited_at)}`}
                          >
                            edited
                          </Text>
                        )}
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                          }}
                          title={
                            message.private
                              ? 'Your colleagues'
                              : 'Users with access to this project'
                          }
                        >
                          {message.private ? (
                            <IconLock size={14} style={{ opacity: 0.6 }} />
                          ) : (
                            <IconUsers size={14} style={{ opacity: 0.6 }} />
                          )}
                        </span>
                      </Group>
                    </Group>
                  )}
                  {editingMessageId === message.event_message_id ? (
                    <EditMessageForm
                      editMessageValue={editMessageValue}
                      setEditMessageValue={setEditMessageValue}
                      editInlineImages={editInlineImages}
                      setEditInlineImages={setEditInlineImages}
                      onUpdate={handleUpdateMessage}
                      onCancel={handleCancelEdit}
                      isPending={updateMessagePending}
                      colorScheme={colorScheme}
                      theme={theme}
                      commonEmojis={commonEmojis}
                      borderColor={borderColor}
                      emojiPickerOpen={emojiPickerOpen}
                      setEmojiPickerOpen={setEmojiPickerOpen}
                    />
                  ) : (
                    <Paper
                      p="sm"
                      onMouseEnter={() =>
                        setHoveredMessageId(message.event_message_id)
                      }
                      onMouseLeave={() => setHoveredMessageId(null)}
                      style={{
                        backgroundColor:
                          hoveredMessageId === message.event_message_id
                            ? isCurrentUserMessage
                              ? colorScheme === 'dark'
                                ? theme.colors[theme.primaryColor][6]
                                : theme.colors[theme.primaryColor][1]
                              : colorScheme === 'dark'
                                ? theme.colors.dark[6]
                                : theme.colors.gray[2]
                            : isCurrentUserMessage
                              ? colorScheme === 'dark'
                                ? theme.colors[theme.primaryColor][7]
                                : theme.colors[theme.primaryColor][0]
                              : colorScheme === 'dark'
                                ? theme.colors.dark[7]
                                : theme.colors.gray[1],
                        borderRadius: theme.radius.md,
                        maxWidth: '80%',
                        position: 'relative',
                        transition: 'background-color 0.2s ease',
                      }}
                    >
                      {hoveredMessageId === message.event_message_id &&
                        !message.deleted_at && (
                          <MessageToolbar
                            messageId={message.event_message_id}
                            isFirstMessage={isFirstMessage}
                            isCurrentUserMessage={isCurrentUserMessage}
                            addReactionMessageId={addReactionMessageId}
                            onSetAddReactionMessageId={setAddReactionMessageId}
                            onSetHoveredMessageId={setHoveredMessageId}
                            handleReactionClick={handleReactionClick}
                            handleReplyClick={handleReplyClick}
                            handleEditClick={handleEditClick}
                            handleDeleteClick={handleDeleteClick}
                            userName={userName}
                            messageBody={message.body}
                            emojiReactions={emojiReactions}
                            colorScheme={colorScheme}
                            theme={theme}
                          />
                        )}
                      <Stack gap="xs">
                        {parentMessage && parentUserName && (
                          <QuotedMessage
                            parentMessageBody={parentMessage.body}
                            parentUserName={parentUserName}
                            parentMessageDeleted={!!parentMessage.deleted_at}
                            parentMessageId={parentMessage.event_message_id}
                            onParentMessageClick={handleParentMessageClick}
                            colorScheme={colorScheme}
                            theme={theme}
                          />
                        )}
                        {message.deleted_at ? (
                          <Text size="md" style={{ fontStyle: 'italic' }}>
                            This message was deleted.
                          </Text>
                        ) : (
                          <MessageBodyWithImages
                            body={message.body}
                            eventId={eventId}
                            eventMessageId={message.event_message_id}
                            projectId={projectId}
                            colorScheme={colorScheme}
                            isCurrentUserMessage={isCurrentUserMessage}
                            theme={theme}
                          />
                        )}
                      </Stack>
                    </Paper>
                  )}
                  {editingMessageId !== message.event_message_id &&
                    !message.deleted_at && (
                      <MessageReactions
                        messageId={message.event_message_id}
                        projectId={projectId}
                        userIdToName={userIdToName}
                        currentUserId={currentUserId}
                        isCurrentUserMessage={isCurrentUserMessage}
                        handleReactionClick={handleReactionClick}
                        colorScheme={colorScheme}
                        theme={theme}
                        reactions={reactionsByMessageId.get(
                          message.event_message_id,
                        )}
                      />
                    )}
                </Stack>
                {isCurrentUserMessage && (
                  <Avatar
                    src={
                      isCurrentUserMessage && user?.hasImage
                        ? user.imageUrl
                        : undefined
                    }
                    alt={userName}
                    size={message.parent_message_id ? 'sm' : 'md'}
                    radius="xl"
                  >
                    {initials}
                  </Avatar>
                )}
              </Group>
            )
          })
        ) : (
          <Text c="dimmed" size="sm" ta="center" py="xl">
            No messages yet. Start the conversation!
          </Text>
        )}
      </Stack>
    </ScrollArea>
  )
}
