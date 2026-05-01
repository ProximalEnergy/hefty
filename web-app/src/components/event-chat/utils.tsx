import { ReactionTypeEnum } from '@/api/enumerations'
import { Text } from '@mantine/core'
import React from 'react'

// Constants for image validation
const MAX_IMAGE_SIZE_MB = 10
export const MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
export const ALLOWED_IMAGE_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
]

// Helper function to get reaction emoji
export function getReactionEmoji(reactionType: string): string {
  const emojiMap: Record<string, string> = {
    [ReactionTypeEnum.THUMBS_UP]: '👍',
    [ReactionTypeEnum.THUMBS_DOWN]: '👎',
    [ReactionTypeEnum.EYES]: '👀',
    [ReactionTypeEnum.QUESTION_MARK]: '❓',
    [ReactionTypeEnum.HEART]: '❤️',
    [ReactionTypeEnum.LAUGHING]: '😂',
    [ReactionTypeEnum.SURPRISED]: '😮',
    [ReactionTypeEnum.SAD]: '😢',
    [ReactionTypeEnum.ANGRY]: '😡',
    [ReactionTypeEnum.FIRE]: '🔥',
    [ReactionTypeEnum.PARTY]: '🎉',
    [ReactionTypeEnum.CHECK]: '✅',
    [ReactionTypeEnum.CLAP]: '👏',
    [ReactionTypeEnum.HUNDRED]: '💯',
    [ReactionTypeEnum.ROCKET]: '🚀',
    [ReactionTypeEnum.LIGHTBULB]: '💡',
    [ReactionTypeEnum.STAR]: '⭐',
    [ReactionTypeEnum.TARGET]: '🎯',
    [ReactionTypeEnum.PRAY]: '🙏',
  }
  return emojiMap[reactionType] || reactionType
}

// Format inline text with bold, italic, and mentions
function formatInlineText(
  text: string,
  mentionColor: string,
  keyPrefix: string,
): React.ReactNode {
  const parts: React.ReactNode[] = []
  let lastIndex = 0
  let keyIndex = 0

  // Combined regex to match: **bold**, *italic*, __bold__, _italic_, ++underline++, @mentions
  // Order matters: ** before * (bold before italic), __ before _ (bold before italic), ++ before + (underline before other)
  const formatRegex =
    /(\*\*([^*]+)\*\*|__([^_]+)__|\*([^*]+)\*|_([^_\s][^_]*[^_\s])_|\+\+([^+]+)\+\+|@(\w+(?:\s+\w+)?)(?=\s|$|[.,!?;:]))/g

  let match: RegExpExecArray | null

  while ((match = formatRegex.exec(text)) !== null) {
    // Add text before match
    if (match.index > lastIndex) {
      const textKey = `${keyPrefix}-text-${keyIndex}`
      parts.push(
        <span key={textKey}>{text.substring(lastIndex, match.index)}</span>,
      )
    }

    const key = `${keyPrefix}-${keyIndex++}`

    // Check which format matched
    if (match[1] && match[1].startsWith('**') && match[1].endsWith('**')) {
      // Bold: **text**
      parts.push(
        <Text key={key} span fw={700} style={{ display: 'inline' }}>
          {match[2]}
        </Text>,
      )
    } else if (
      match[1] &&
      match[1].startsWith('__') &&
      match[1].endsWith('__')
    ) {
      // Bold: __text__
      parts.push(
        <Text key={key} span fw={700} style={{ display: 'inline' }}>
          {match[3]}
        </Text>,
      )
    } else if (match[1] && match[1].startsWith('*') && match[1].endsWith('*')) {
      // Italic: *text*
      parts.push(
        <Text key={key} span style={{ fontStyle: 'italic', display: 'inline' }}>
          {match[4]}
        </Text>,
      )
    } else if (match[1] && match[1].startsWith('_') && match[1].endsWith('_')) {
      // Italic: _text_
      parts.push(
        <Text key={key} span style={{ fontStyle: 'italic', display: 'inline' }}>
          {match[5]}
        </Text>,
      )
    } else if (
      match[1] &&
      match[1].startsWith('++') &&
      match[1].endsWith('++')
    ) {
      // Underline: ++text++
      parts.push(
        <Text
          key={key}
          span
          style={{ textDecoration: 'underline', display: 'inline' }}
        >
          {match[6]}
        </Text>,
      )
    } else if (match[1] && match[1].startsWith('@')) {
      // Mention: @username
      parts.push(
        <Text
          key={key}
          span
          c={mentionColor}
          fw={600}
          style={{ display: 'inline' }}
        >
          {match[0]}
        </Text>,
      )
    }

    lastIndex = formatRegex.lastIndex
  }

  // Add remaining text
  if (lastIndex < text.length) {
    const remainingKey = `${keyPrefix}-text-${keyIndex}`
    parts.push(<span key={remainingKey}>{text.substring(lastIndex)}</span>)
  }

  return <>{parts.length > 0 ? parts : text}</>
}

// Format message body to highlight mentions, bold, italic, and lists
export function formatMessageBody(
  body: string,
  colorScheme?: string,
  isCurrentUserMessage?: boolean,
  primaryColor?: string,
): React.ReactNode {
  const parts: React.ReactNode[] = []
  const lines = body.split('\n')
  const color = primaryColor || 'blue'
  const mentionColor =
    isCurrentUserMessage && colorScheme === 'dark' ? `${color}.2` : `${color}.6`

  lines.forEach((line, lineIndex) => {
    if (lineIndex > 0) {
      parts.push(<br key={`br-${lineIndex}`} />)
    }

    // Check if line is a list item
    const bulletMatch = line.match(/^([-*])\s+(.+)$/)
    const numberedMatch = line.match(/^(\d+)[.)]\s+(.+)$/)

    if (bulletMatch) {
      // Bullet list item
      const listItemContent = bulletMatch[2]
      parts.push(
        <Text key={`bullet-${lineIndex}`} span style={{ display: 'inline' }}>
          {'• '}
        </Text>,
      )
      parts.push(
        <React.Fragment key={`content-${lineIndex}`}>
          {formatInlineText(
            listItemContent,
            mentionColor,
            `content-${lineIndex}`,
          )}
        </React.Fragment>,
      )
    } else if (numberedMatch) {
      // Numbered list item
      const number = numberedMatch[1]
      const listItemContent = numberedMatch[2]
      parts.push(
        <Text key={`number-${lineIndex}`} span style={{ display: 'inline' }}>
          {number}.{' '}
        </Text>,
      )
      parts.push(
        <React.Fragment key={`content-num-${lineIndex}`}>
          {formatInlineText(
            listItemContent,
            mentionColor,
            `content-${lineIndex}`,
          )}
        </React.Fragment>,
      )
    } else {
      // Regular line - parse formatting and mentions
      parts.push(
        <React.Fragment key={`line-${lineIndex}`}>
          {formatInlineText(line, mentionColor, `line-${lineIndex}`)}
        </React.Fragment>,
      )
    }
  })

  return <>{parts.length > 0 ? parts : body}</>
}

// Helper function to generate unique image IDs
export const generateImageId = () => {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substr(2, 9)
  return `inline-${timestamp}-${random}`
}
