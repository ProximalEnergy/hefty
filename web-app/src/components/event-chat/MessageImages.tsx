import {
  EventMessageImage,
  useGetEventMessageImages,
} from '@/api/v1/operational/event_messages'
import { MessageImagesModal } from '@/components/event-chat/MessageImagesModal'
import {
  Group,
  Image,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { useMemo, useState } from 'react'

interface MessageImagesProps {
  eventId: number
  eventMessageId: number
  projectId: string
  excludeIndices?: number[]
}

export function MessageImages({
  eventId,
  eventMessageId,
  projectId,
  excludeIndices = [],
}: MessageImagesProps) {
  const [opened, setOpened] = useState(false)
  const [selectedImageIndex, setSelectedImageIndex] = useState(0)
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()

  const { data: allImages } = useGetEventMessageImages({
    queryParams: { eventId, eventMessageId, projectId },
    queryOptions: {
      enabled: !!eventMessageId,
    },
  })

  // Filter out excluded indices (images that are rendered inline)
  const images = useMemo(() => {
    if (!allImages || !Array.isArray(allImages)) return []
    return allImages.filter((_, idx) => !excludeIndices.includes(idx))
  }, [allImages, excludeIndices])

  const handleImageClick = (index: number) => {
    setSelectedImageIndex(index)
    setOpened(true)
  }

  if (!images || !Array.isArray(images) || images.length === 0) return null

  return (
    <>
      <Group gap="xs" mt="xs" wrap="wrap">
        {images.map((image: EventMessageImage, index: number) => (
          <Image
            key={image.event_message_image_id}
            src={image.presigned_url}
            alt={image.filename}
            maw={600}
            mah={600}
            fit="contain"
            radius="md"
            style={{ cursor: 'pointer' }}
            onClick={() => handleImageClick(index)}
          />
        ))}
      </Group>

      {images.length > 0 && (
        <MessageImagesModal
          images={images}
          opened={opened}
          onClose={() => setOpened(false)}
          selectedIndex={selectedImageIndex}
          onSelectIndex={setSelectedImageIndex}
          theme={theme}
          colorScheme={colorScheme}
          eventId={eventId}
          projectId={projectId}
        />
      )}
    </>
  )
}
