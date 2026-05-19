import { EventMessageReaction } from '@/api/v1/operational/event_message_reactions'
import { getReactionEmoji } from '@/components/event-chat/utils'
import { Group, MantineTheme, Paper, Text, Tooltip } from '@mantine/core'
import { useMemo } from 'react'

interface MessageReactionsProps {
  messageId: number
  projectId: string
  userIdToName: Map<string, string>
  currentUserId: string | undefined
  isCurrentUserMessage: boolean
  handleReactionClick: (
    messageId: number,
    reactionType: string,
    event: React.MouseEvent,
  ) => void
  colorScheme: string
  theme: MantineTheme
  reactions?: EventMessageReaction[]
}

export function MessageReactions({
  messageId,
  projectId: _projectId,
  userIdToName,
  currentUserId,
  isCurrentUserMessage,
  handleReactionClick,
  colorScheme,
  theme,
  reactions,
}: MessageReactionsProps) {
  // Group reactions by type
  const reactionsByType = useMemo(() => {
    if (!reactions) return new Map<string, EventMessageReaction[]>()
    const map = new Map<string, EventMessageReaction[]>()
    reactions.forEach((reaction) => {
      if (!map.has(reaction.reaction_type)) {
        map.set(reaction.reaction_type, [])
      }
      map.get(reaction.reaction_type)!.push(reaction)
    })
    return map
  }, [reactions])

  // Check if current user has reacted with each type
  const userReactions = useMemo(() => {
    if (!reactions || !currentUserId) return new Set<string>()
    return new Set(
      reactions
        .filter((r) => r.user_id === currentUserId)
        .map((r) => r.reaction_type),
    )
  }, [reactions, currentUserId])

  if (reactionsByType.size === 0) return null

  return (
    <Group
      gap={4}
      style={{
        marginTop: 4,
        justifyContent: isCurrentUserMessage ? 'flex-end' : 'flex-start',
      }}
    >
      {Array.from(reactionsByType.entries()).map(([type, typeReactions]) => {
        const hasUserReaction = userReactions.has(type)
        const reactionNames = typeReactions
          .map((r) => userIdToName.get(r.user_id) || `User ${r.user_id}`)
          .join(', ')

        return (
          <Tooltip
            key={type}
            label={reactionNames}
            position="top"
            withArrow
            multiline
            style={{ maxWidth: 200 }}
          >
            <Paper
              p={4}
              style={{
                backgroundColor: hasUserReaction
                  ? colorScheme === 'dark'
                    ? theme.colors[theme.primaryColor][8]
                    : theme.colors[theme.primaryColor][1]
                  : colorScheme === 'dark'
                    ? theme.colors.dark[7]
                    : theme.colors.gray[0],
                borderRadius: theme.radius.md,
                border: hasUserReaction
                  ? `1px solid ${
                      colorScheme === 'dark'
                        ? theme.colors[theme.primaryColor][6]
                        : theme.colors[theme.primaryColor][3]
                    }`
                  : `1px solid ${
                      colorScheme === 'dark'
                        ? theme.colors.dark[4]
                        : theme.colors.gray[3]
                    }`,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
              onClick={(e) => handleReactionClick(messageId, type, e)}
              onMouseDown={(e) => e.stopPropagation()}
            >
              <Text size="sm">{getReactionEmoji(type)}</Text>
              <Text
                size="xs"
                c={
                  colorScheme === 'dark'
                    ? theme.colors.dark[9]
                    : theme.colors.dark[7]
                }
              >
                {typeReactions.length}
              </Text>
            </Paper>
          </Tooltip>
        )
      })}
    </Group>
  )
}
