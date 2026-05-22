import { ReactionTypeEnum } from '@/api/enumerations'
import {
  ActionIcon,
  Group,
  MantineTheme,
  Menu,
  Paper,
  Popover,
  Tooltip,
} from '@mantine/core'
import {
  IconDots,
  IconEdit,
  IconMessageReply,
  IconMoodPlus,
  IconTrash,
} from '@tabler/icons-react'

interface EmojiReaction {
  emoji: string
  type: string
  label: string
}

interface MessageToolbarProps {
  messageId: number
  isFirstMessage: boolean
  isCurrentUserMessage: boolean
  addReactionMessageId: number | null
  onSetAddReactionMessageId: (id: number | null) => void
  onSetHoveredMessageId: (id: number | null) => void
  handleReactionClick: (
    messageId: number,
    reactionType: string,
    event: React.MouseEvent,
  ) => void
  handleReplyClick: (
    messageId: number,
    userName: string,
    messageBody: string,
  ) => void
  handleEditClick?: (messageId: number) => void
  handleDeleteClick?: (messageId: number) => void
  userName: string
  messageBody: string
  emojiReactions: EmojiReaction[]
  colorScheme: string
  theme: MantineTheme
}

export function MessageToolbar({
  messageId,
  isFirstMessage,
  isCurrentUserMessage,
  addReactionMessageId,
  onSetAddReactionMessageId,
  onSetHoveredMessageId,
  handleReactionClick,
  handleReplyClick,
  handleEditClick,
  handleDeleteClick,
  userName,
  messageBody,
  emojiReactions,
  colorScheme,
  theme,
}: MessageToolbarProps) {
  const borderColor =
    colorScheme === 'dark' ? theme.colors.dark[4] : theme.colors.gray[3]
  const toolbarPosition = isCurrentUserMessage
    ? ({ right: 0 } as const)
    : ({ left: 0 } as const)
  const popoverPosition = isCurrentUserMessage ? 'top-end' : 'top-start'

  return (
    <Paper
      p="xs"
      style={
        {
          position: 'absolute',
          ...(isFirstMessage ? { bottom: -30 } : { top: -30 }),
          ...toolbarPosition,
          boxShadow: theme.shadows.sm,
          border: `1px solid ${borderColor}`,
          zIndex: 10,
          display: 'flex',
          gap: '4px',
          alignItems: 'center',
        } as React.CSSProperties
      }
    >
      {/* Standard Reactions */}
      <ActionIcon
        variant="subtle"
        size="sm"
        onClick={(e) =>
          handleReactionClick(messageId, ReactionTypeEnum.THUMBS_UP, e)
        }
        title="👍 Thumbs up"
      >
        👍
      </ActionIcon>
      <ActionIcon
        variant="subtle"
        size="sm"
        onClick={(e) =>
          handleReactionClick(messageId, ReactionTypeEnum.EYES, e)
        }
        title="👀 Looking"
      >
        👀
      </ActionIcon>
      <ActionIcon
        variant="subtle"
        size="sm"
        onClick={(e) =>
          handleReactionClick(messageId, ReactionTypeEnum.QUESTION_MARK, e)
        }
        title="❓ Question"
      >
        ❓
      </ActionIcon>

      {/* Actions */}
      <Popover
        position={popoverPosition}
        withArrow
        shadow="md"
        withinPortal
        opened={addReactionMessageId === messageId}
        onChange={(opened) =>
          onSetAddReactionMessageId(opened ? messageId : null)
        }
      >
        <Popover.Target>
          <ActionIcon
            variant="subtle"
            size="sm"
            title="Add reaction"
            onClick={(e) => {
              e.stopPropagation()
              onSetAddReactionMessageId(
                addReactionMessageId === messageId ? null : messageId,
              )
            }}
          >
            <IconMoodPlus size={16} />
          </ActionIcon>
        </Popover.Target>
        <Popover.Dropdown>
          <Paper p="xs" style={{ maxWidth: 300 }}>
            <Group gap="xs" style={{ flexWrap: 'wrap' }}>
              {emojiReactions.map((reaction) => (
                <Tooltip
                  key={reaction.type}
                  label={reaction.label}
                  position="top"
                >
                  <ActionIcon
                    variant="subtle"
                    size="lg"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleReactionClick(messageId, reaction.type, e)
                      onSetAddReactionMessageId(null)
                      onSetHoveredMessageId(null)
                    }}
                    style={{
                      fontSize: '1.5rem',
                      width: 36,
                      height: 36,
                    }}
                  >
                    {reaction.emoji}
                  </ActionIcon>
                </Tooltip>
              ))}
            </Group>
          </Paper>
        </Popover.Dropdown>
      </Popover>
      <ActionIcon
        variant="subtle"
        size="sm"
        onClick={(e) => {
          e.stopPropagation()
          handleReplyClick(messageId, userName, messageBody)
        }}
        title="Reply"
      >
        <IconMessageReply size={16} />
      </ActionIcon>

      {/* Other Options Menu - Only for current user's messages */}
      {isCurrentUserMessage && (
        <Menu
          shadow="md"
          width={150}
          position="top-end"
          withArrow
          withinPortal
          offset={5}
        >
          <Menu.Target>
            <ActionIcon
              variant="subtle"
              size="sm"
              onClick={(e) => e.stopPropagation()}
              title="More options"
            >
              <IconDots size={16} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item
              leftSection={<IconEdit size={16} />}
              onClick={(e) => {
                e.stopPropagation()
                handleEditClick?.(messageId)
              }}
            >
              Edit
            </Menu.Item>
            <Menu.Item
              leftSection={<IconTrash size={16} />}
              color="red"
              onClick={(e) => {
                e.stopPropagation()
                handleDeleteClick?.(messageId)
              }}
            >
              Delete
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      )}
    </Paper>
  )
}
