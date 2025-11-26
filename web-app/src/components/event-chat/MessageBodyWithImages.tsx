import { useGetEventMessageImages } from '@/api/v1/operational/event_messages'
import { Image, MantineTheme, Paper, Stack, Text } from '@mantine/core'
import { useState } from 'react'

import { MessageImages } from './MessageImages'
import { MessageImagesModal } from './MessageImagesModal'
import { formatMessageBody } from './utils'

interface MessageBodyWithImagesProps {
  body: string
  eventId: number
  eventMessageId: number
  projectId: string
  colorScheme: string
  isCurrentUserMessage: boolean
  theme: MantineTheme
}

export function MessageBodyWithImages({
  body,
  eventId,
  eventMessageId,
  projectId,
  colorScheme,
  isCurrentUserMessage,
  theme,
}: MessageBodyWithImagesProps) {
  const [openedImageModal, setOpenedImageModal] = useState(false)
  const [selectedImageIndex, setSelectedImageIndex] = useState(0)
  const { data: images } = useGetEventMessageImages({
    queryParams: { eventId, eventMessageId, projectId },
    queryOptions: {
      enabled: !!eventMessageId,
    },
  })

  // Parse body for image placeholders [IMG:index]
  const imagePlaceholderRegex = /\[IMG:(\d+)\]/g
  const parts: Array<{
    type: 'text' | 'image'
    content: string
    index?: number
  }> = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  // Reset regex lastIndex
  imagePlaceholderRegex.lastIndex = 0

  while ((match = imagePlaceholderRegex.exec(body)) !== null) {
    // Add text before placeholder
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: body.slice(lastIndex, match.index),
      })
    }

    // Add image placeholder
    const imageIndex = parseInt(match[1], 10)
    parts.push({
      type: 'image',
      content: match[0],
      index: imageIndex,
    })

    lastIndex = imagePlaceholderRegex.lastIndex
  }

  // Add remaining text
  if (lastIndex < body.length) {
    parts.push({
      type: 'text',
      content: body.slice(lastIndex),
    })
  }

  // If no placeholders found, return original formatted body
  if (parts.length === 0 || parts.every((p) => p.type === 'text')) {
    return (
      <Text
        size="md"
        c={
          isCurrentUserMessage && colorScheme === 'dark' ? 'gray.0' : undefined
        }
        style={{
          wordBreak: 'break-word',
          lineHeight: 1.5,
          whiteSpace: 'pre-wrap',
        }}
      >
        {formatMessageBody(
          body,
          colorScheme,
          isCurrentUserMessage,
          theme.primaryColor,
        )}
      </Text>
    )
  }

  // Get images array (sorted by upload order)
  const imagesArray = images && Array.isArray(images) ? images : []

  return (
    <Stack gap="xs">
      <Stack gap="xs">
        {parts.map((part, idx) => {
          if (part.type === 'text') {
            return (
              <Text
                key={`text-${idx}`}
                size="md"
                c={
                  isCurrentUserMessage && colorScheme === 'dark'
                    ? 'gray.0'
                    : undefined
                }
                style={{
                  wordBreak: 'break-word',
                  lineHeight: 1.5,
                  whiteSpace: 'pre-wrap',
                  display: 'block',
                  width: '100%',
                }}
              >
                {formatMessageBody(
                  part.content,
                  colorScheme,
                  isCurrentUserMessage,
                  theme.primaryColor,
                )}
              </Text>
            )
          } else {
            // Render image if available
            const imageIndex = part.index ?? -1
            const image = imagesArray[imageIndex]

            if (image) {
              // Find the actual index in the full images array for modal
              const actualIndexInAllImages = imagesArray.findIndex(
                (img) =>
                  img.event_message_image_id === image.event_message_image_id,
              )
              return (
                <Paper
                  key={`img-${idx}-${imageIndex}`}
                  p={4}
                  style={{
                    position: 'relative',
                    border: `1px solid ${
                      colorScheme === 'dark'
                        ? theme.colors.dark[4]
                        : theme.colors.gray[3]
                    }`,
                    borderRadius: theme.radius.sm,
                    display: 'block',
                    width: 'fit-content',
                  }}
                >
                  <Image
                    src={image.presigned_url}
                    alt={image.filename}
                    maw={600}
                    mah={600}
                    fit="contain"
                    radius="sm"
                    style={{ cursor: 'pointer' }}
                    onClick={() => {
                      if (actualIndexInAllImages >= 0) {
                        setSelectedImageIndex(actualIndexInAllImages)
                        setOpenedImageModal(true)
                      }
                    }}
                  />
                </Paper>
              )
            }
            return null
          }
        })}
      </Stack>
      {/* Display any remaining images that don't have placeholders (pending images) */}
      {imagesArray.length >
        parts.filter((p) => p.type === 'image' && p.index !== undefined)
          .length && (
        <MessageImages
          eventId={eventId}
          eventMessageId={eventMessageId}
          projectId={projectId}
          excludeIndices={parts
            .filter((p) => p.type === 'image' && p.index !== undefined)
            .map((p) => p.index!)
            .filter((idx) => idx >= 0 && idx < imagesArray.length)}
        />
      )}
      {/* Image modal for inline images */}
      {imagesArray.length > 0 && (
        <MessageImagesModal
          images={imagesArray}
          opened={openedImageModal}
          onClose={() => setOpenedImageModal(false)}
          selectedIndex={selectedImageIndex}
          onSelectIndex={setSelectedImageIndex}
          theme={theme}
          colorScheme={colorScheme}
          eventId={eventId}
          projectId={projectId}
        />
      )}
    </Stack>
  )
}
