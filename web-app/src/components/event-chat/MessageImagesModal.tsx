import {
  EventMessageImage,
  useGetEventMessageImageUrl,
} from '@/api/v1/operational/event_messages'
import {
  ActionIcon,
  Group,
  Image,
  Loader,
  MantineTheme,
  Modal,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core'
import {
  IconChevronLeft,
  IconChevronRight,
  IconDownload,
  IconX,
  IconZoomIn,
  IconZoomOut,
  IconZoomReset,
} from '@tabler/icons-react'
import { useEffect, useRef, useState } from 'react'

interface MessageImagesModalProps {
  images: EventMessageImage[]
  opened: boolean
  onClose: () => void
  selectedIndex: number
  onSelectIndex: (index: number) => void
  theme: MantineTheme
  colorScheme: string
  eventId: number
  projectId: string
}

export function MessageImagesModal({
  images,
  opened,
  onClose,
  selectedIndex,
  onSelectIndex,
  theme,
  colorScheme,
  eventId,
  projectId,
}: MessageImagesModalProps) {
  const [zoom, setZoom] = useState(1)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [isDownloading, setIsDownloading] = useState(false)
  const imageContainerRef = useRef<HTMLDivElement>(null)
  const getImageUrl = useGetEventMessageImageUrl()

  const selectedImage = images[selectedIndex]

  const handleMessageImagesPrevious = () => {
    if (selectedIndex > 0) {
      onSelectIndex(selectedIndex - 1)
      setZoom(1)
      setPosition({ x: 0, y: 0 })
    }
  }

  const handleMessageImagesNext = () => {
    if (selectedIndex < images.length - 1) {
      onSelectIndex(selectedIndex + 1)
      setZoom(1)
      setPosition({ x: 0, y: 0 })
    }
  }

  const handleMessageImagesDownload = async () => {
    if (!selectedImage || isDownloading) return

    setIsDownloading(true)
    try {
      const downloadData = await getImageUrl.mutateAsync({
        eventId,
        imageId: selectedImage.event_message_image_id,
        projectId,
      })

      const iframe = document.createElement('iframe')
      iframe.style.display = 'none'
      iframe.src = downloadData.presigned_url
      document.body.appendChild(iframe)

      setTimeout(() => {
        if (document.body.contains(iframe)) {
          document.body.removeChild(iframe)
        }
        setIsDownloading(false)
      }, 3000)
    } catch (error) {
      console.error('Failed to download image:', error)
      setIsDownloading(false)
    }
  }

  const handleZoomIn = () => {
    setZoom((prev) => Math.min(prev + 0.25, 5))
  }

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(prev - 0.25, 0.5))
  }

  const handleZoomReset = () => {
    setZoom(1)
    setPosition({ x: 0, y: 0 })
  }

  const handleMessageImagesMouseDown = (e: React.MouseEvent) => {
    if (zoom > 1) {
      setIsDragging(true)
      setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y })
    }
  }

  const handleMessageImagesMouseMove = (e: React.MouseEvent) => {
    if (isDragging && zoom > 1) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      })
    }
  }

  const handleMessageImagesMouseUp = () => {
    setIsDragging(false)
  }

  const handleMessageImagesWheel = (e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault()
      const delta = e.deltaY > 0 ? -0.1 : 0.1
      setZoom((prev) => Math.max(0.5, Math.min(5, prev + delta)))
    }
  }

  useEffect(() => {
    if (!opened || !images) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'ArrowLeft') {
        event.preventDefault()
        if (selectedIndex > 0) {
          onSelectIndex(selectedIndex - 1)
        }
      } else if (event.key === 'ArrowRight') {
        event.preventDefault()
        if (selectedIndex < images.length - 1) {
          onSelectIndex(selectedIndex + 1)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [opened, selectedIndex, images, onSelectIndex])

  if (!selectedImage) return null

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="100%"
      centered
      padding={0}
      withCloseButton={false}
      fullScreen
      styles={{
        body: { padding: 0, height: '100%' },
        content: {
          backgroundColor:
            colorScheme === 'dark' ? theme.colors.dark[7] : theme.white,
          height: '100vh',
          maxHeight: '100vh',
        },
        inner: {
          padding: 0,
        },
      }}
    >
      <Stack gap={0}>
        {/* Header */}
        <Group
          justify="space-between"
          p="md"
          style={{
            borderBottom: `1px solid ${
              colorScheme === 'dark'
                ? theme.colors.dark[4]
                : theme.colors.gray[3]
            }`,
          }}
        >
          <Text size="sm" c="dimmed" fw={500}>
            {selectedImage.filename}
          </Text>
          <Group gap="xs">
            <Tooltip label="Download image">
              <ActionIcon
                variant="subtle"
                color="gray"
                onClick={handleMessageImagesDownload}
                disabled={isDownloading}
              >
                {isDownloading ? (
                  <Loader size={16} color="gray" />
                ) : (
                  <IconDownload size={18} />
                )}
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Zoom out">
              <ActionIcon
                variant="subtle"
                color="gray"
                onClick={handleZoomOut}
                disabled={zoom <= 0.5}
              >
                <IconZoomOut size={18} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Zoom Reset">
              <ActionIcon
                variant="subtle"
                color="gray"
                onClick={handleZoomReset}
                disabled={zoom === 1}
              >
                <IconZoomReset size={18} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Zoom in">
              <ActionIcon
                variant="subtle"
                color="gray"
                onClick={handleZoomIn}
                disabled={zoom >= 5}
              >
                <IconZoomIn size={18} />
              </ActionIcon>
            </Tooltip>
            <ActionIcon variant="subtle" color="gray" onClick={onClose}>
              <IconX size={18} />
            </ActionIcon>
          </Group>
        </Group>

        {/* Image container */}
        <div style={{ position: 'relative', width: '100%' }}>
          {images.length > 1 && selectedIndex > 0 && (
            <ActionIcon
              variant="filled"
              color="gray"
              size="xl"
              radius="xl"
              style={{
                position: 'absolute',
                left: 16,
                top: '50%',
                transform: 'translateY(-50%)',
                zIndex: 10,
                opacity: 0.8,
              }}
              onClick={handleMessageImagesPrevious}
            >
              <IconChevronLeft size={24} />
            </ActionIcon>
          )}

          <div
            ref={imageContainerRef}
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              height: 'calc(100vh - 140px)',
              padding: '2rem',
              backgroundColor:
                colorScheme === 'dark'
                  ? theme.colors.dark[8]
                  : theme.colors.gray[0],
              overflow: 'hidden',
              cursor: zoom > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default',
            }}
            onMouseDown={handleMessageImagesMouseDown}
            onMouseMove={handleMessageImagesMouseMove}
            onMouseUp={handleMessageImagesMouseUp}
            onMouseLeave={handleMessageImagesMouseUp}
            onWheel={handleMessageImagesWheel}
          >
            <div
              style={{
                transform: `translate(${position.x}px, ${position.y}px) scale(${zoom})`,
                transition: isDragging ? 'none' : 'transform 0.1s ease-out',
                transformOrigin: 'center center',
                maxWidth: '100%',
                maxHeight: '100%',
              }}
            >
              <Image
                src={selectedImage.presigned_url}
                alt={selectedImage.filename}
                maw="100%"
                mah="100%"
                fit="contain"
                style={{
                  maxHeight: 'calc(100vh - 140px)',
                  userSelect: 'none',
                  pointerEvents: 'none',
                }}
              />
            </div>
          </div>

          {images.length > 1 && selectedIndex < images.length - 1 && (
            <ActionIcon
              variant="filled"
              color="gray"
              size="xl"
              radius="xl"
              style={{
                position: 'absolute',
                right: 16,
                top: '50%',
                transform: 'translateY(-50%)',
                zIndex: 10,
                opacity: 0.8,
              }}
              onClick={handleMessageImagesNext}
            >
              <IconChevronRight size={24} />
            </ActionIcon>
          )}
        </div>

        {/* Footer */}
        {images.length > 1 && (
          <Group
            justify="center"
            p="md"
            style={{
              borderTop: `1px solid ${
                colorScheme === 'dark'
                  ? theme.colors.dark[4]
                  : theme.colors.gray[3]
              }`,
            }}
          >
            <Text size="sm" c="dimmed">
              {selectedIndex + 1} of {images.length}
            </Text>
          </Group>
        )}
      </Stack>
    </Modal>
  )
}
