import {
  ALLOWED_IMAGE_TYPES,
  MAX_IMAGE_SIZE_BYTES,
  generateImageId,
} from '@/components/event-chat/utils'
import {
  ActionIcon,
  Button,
  Group,
  Image,
  MantineTheme,
  Paper,
  Popover,
  ScrollArea,
  Stack,
  Textarea,
} from '@mantine/core'
import {
  IconBold,
  IconItalic,
  IconMoodPlus,
  IconUnderline,
  IconX,
} from '@tabler/icons-react'
import { useRef } from 'react'

interface EditMessageFormProps {
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
  onUpdate: () => void
  onCancel: () => void
  isPending: boolean
  colorScheme: string
  theme: MantineTheme
  commonEmojis: string[]
  borderColor: string
  emojiPickerOpen: boolean
  setEmojiPickerOpen: (open: boolean) => void
}

export function EditMessageForm({
  editMessageValue,
  setEditMessageValue,
  editInlineImages,
  setEditInlineImages,
  onUpdate,
  onCancel,
  isPending,
  colorScheme,
  theme,
  commonEmojis,
  borderColor,
  emojiPickerOpen,
  setEmojiPickerOpen,
}: EditMessageFormProps) {
  const editTextareaRef = useRef<HTMLTextAreaElement>(null)

  const handleEditPaste = async (
    event: React.ClipboardEvent<HTMLTextAreaElement>,
  ) => {
    const items = event.clipboardData?.items
    if (!items) return

    for (let i = 0; i < items.length; i++) {
      const item = items[i]
      if (item.type.indexOf('image') !== -1) {
        event.preventDefault()
        const file = item.getAsFile()
        if (file && file.size <= MAX_IMAGE_SIZE_BYTES) {
          if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
            console.warn('Invalid image type:', file.type)
            return
          }

          const preview = URL.createObjectURL(file)
          const imageId = generateImageId()

          const lastEditImagePosition =
            editInlineImages.length > 0
              ? Math.max(...editInlineImages.map((img) => img.position))
              : -1
          const textareaCursorPos = editTextareaRef.current?.selectionStart || 0
          let actualCursorPos =
            lastEditImagePosition >= 0
              ? lastEditImagePosition + textareaCursorPos
              : textareaCursorPos

          const textBeforeCursor = editMessageValue.slice(0, actualCursorPos)
          const textAfterCursor = editMessageValue.slice(actualCursorPos)
          // Prepend with newline if there's text before and it doesn't end with newline
          const needsNewlineBefore =
            actualCursorPos > 0 && !textBeforeCursor.endsWith('\n')
          const needsNewlineAfter = true

          let positionOffset = 0
          let newEditMessageValue = editMessageValue
          if (needsNewlineBefore || needsNewlineAfter) {
            if (needsNewlineBefore) {
              newEditMessageValue = textBeforeCursor + '\n' + textAfterCursor
              actualCursorPos += 1
              positionOffset += 1
            }
            if (needsNewlineAfter) {
              const beforePart = newEditMessageValue.slice(
                0,
                actualCursorPos + 1,
              )
              const afterPart = newEditMessageValue.slice(actualCursorPos + 1)
              newEditMessageValue = beforePart + '\n' + afterPart
              positionOffset += 1
            }
            setEditMessageValue(newEditMessageValue)
          }

          const imagePosition = actualCursorPos

          const newEditInlineImage = {
            id: imageId,
            file,
            position: imagePosition,
            preview,
          }

          setEditInlineImages((prev) => {
            const updated = prev.map((img) =>
              img.position >= actualCursorPos
                ? {
                    ...img,
                    position: img.position + positionOffset + 1,
                  }
                : img,
            )
            return [...updated, newEditInlineImage].sort(
              (a, b) => a.position - b.position,
            )
          })

          setTimeout(() => {
            if (editTextareaRef.current) {
              editTextareaRef.current.focus()
              editTextareaRef.current.setSelectionRange(0, 0)
            }
          }, 0)
        }
        break
      }
    }
  }

  const removeEditInlineImage = (imageId: string) => {
    setEditInlineImages((prev) => {
      const image = prev.find((img) => img.id === imageId)
      if (!image) return prev

      if (image.file) {
        URL.revokeObjectURL(image.preview)
      }

      return prev.filter((img) => img.id !== imageId)
    })
  }

  const wrapEditSelection = (before: string, after: string) => {
    if (!editTextareaRef.current) return

    const textarea = editTextareaRef.current
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const selectedText = editMessageValue.substring(start, end)
    const textBefore = editMessageValue.substring(0, start)
    const textAfter = editMessageValue.substring(end)

    const newValue = `${textBefore}${before}${selectedText}${after}${textAfter}`
    setEditMessageValue(newValue)

    setTimeout(() => {
      if (editTextareaRef.current) {
        const newCursorPos = selectedText
          ? start + before.length + selectedText.length + after.length
          : start + before.length
        editTextareaRef.current.focus()
        editTextareaRef.current.setSelectionRange(newCursorPos, newCursorPos)
      }
    }, 0)
  }

  const handleEditBoldClick = () => {
    wrapEditSelection('**', '**')
  }

  const handleEditItalicClick = () => {
    wrapEditSelection('*', '*')
  }

  const handleEditUnderlineClick = () => {
    wrapEditSelection('++', '++')
  }

  const handleEditKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (event.ctrlKey || event.metaKey) {
      if (event.key === 'b') {
        event.preventDefault()
        handleEditBoldClick()
        return
      }
      if (event.key === 'i') {
        event.preventDefault()
        handleEditItalicClick()
        return
      }
      if (event.key === 'u') {
        event.preventDefault()
        handleEditUnderlineClick()
        return
      }
    }
  }

  const sortedEditImages = [...editInlineImages].sort(
    (a, b) => a.position - b.position,
  )

  const renderEditContent = () => {
    if (sortedEditImages.length === 0) {
      return (
        <Textarea
          ref={editTextareaRef}
          value={editMessageValue}
          onChange={(e) => setEditMessageValue(e.target.value)}
          onPaste={handleEditPaste}
          onKeyDown={handleEditKeyDown}
          placeholder="Edit your message..."
          minRows={1}
          maxRows={10}
          autosize
          disabled={isPending}
          styles={{
            input: {
              border: 'none',
              backgroundColor: 'transparent',
              padding: 0,
            },
          }}
        />
      )
    }

    const parts: Array<
      | {
          type: 'text'
          content: string
          startPos: number
          endPos: number
        }
      | {
          type: 'image'
          content: {
            id: string
            preview: string
            file?: File
            imageId?: string
          }
          position: number
        }
    > = []

    let currentPos = 0
    sortedEditImages.forEach((img) => {
      if (currentPos < img.position) {
        parts.push({
          type: 'text',
          content: editMessageValue.slice(currentPos, img.position),
          startPos: currentPos,
          endPos: img.position,
        })
      }

      parts.push({
        type: 'image',
        content: {
          id: img.id,
          preview: img.preview,
          file: img.file,
          imageId: img.imageId,
        },
        position: img.position,
      })

      currentPos = img.position
    })

    if (currentPos < editMessageValue.length) {
      parts.push({
        type: 'text',
        content: editMessageValue.slice(currentPos),
        startPos: currentPos,
        endPos: editMessageValue.length,
      })
    }

    const lastImagePosition =
      sortedEditImages.length > 0
        ? Math.max(...sortedEditImages.map((img) => img.position))
        : -1
    const textAfterLastImage =
      lastImagePosition >= 0
        ? editMessageValue.slice(lastImagePosition)
        : editMessageValue

    return (
      <Stack gap="xs">
        <Stack gap="xs">
          {parts.map((part, idx) => {
            if (part.type === 'text') {
              if (part.endPos <= lastImagePosition) {
                return (
                  <Textarea
                    key={`text-${idx}`}
                    placeholder="Edit your message..."
                    value={part.content}
                    onChange={(e) => {
                      const newSegmentText = e.target.value
                      const lengthDiff =
                        newSegmentText.length - part.content.length
                      const newEditMessageValue =
                        editMessageValue.slice(0, part.startPos) +
                        newSegmentText +
                        editMessageValue.slice(part.endPos)
                      setEditMessageValue(newEditMessageValue)

                      if (lengthDiff !== 0) {
                        setEditInlineImages((prev) =>
                          prev.map((img) =>
                            img.position >= part.endPos
                              ? {
                                  ...img,
                                  position: img.position + lengthDiff,
                                }
                              : img,
                          ),
                        )
                      }
                    }}
                    onPaste={handleEditPaste}
                    onKeyDown={handleEditKeyDown}
                    minRows={1}
                    maxRows={4}
                    autosize
                    disabled={isPending}
                    styles={{
                      input: {
                        border: 'none',
                        padding: 0,
                        backgroundColor: 'transparent',
                      },
                    }}
                  />
                )
              }
              return null
            } else {
              const img = part.content
              return (
                <Paper
                  key={`img-${img.id}`}
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
                    src={img.preview}
                    alt="Pasted image"
                    maw={400}
                    mah={400}
                    fit="contain"
                    radius="sm"
                  />
                  <ActionIcon
                    size="xs"
                    variant="filled"
                    color="red"
                    style={{
                      position: 'absolute',
                      top: 4,
                      right: 4,
                    }}
                    onClick={() => removeEditInlineImage(img.id)}
                  >
                    <IconX size={12} />
                  </ActionIcon>
                </Paper>
              )
            }
          })}
        </Stack>

        <Textarea
          ref={editTextareaRef}
          placeholder="Edit your message..."
          value={textAfterLastImage}
          onChange={(e) => {
            const newTextAfterLastImage = e.target.value
            const newEditMessageValue =
              lastImagePosition >= 0
                ? editMessageValue.slice(0, lastImagePosition) +
                  newTextAfterLastImage
                : newTextAfterLastImage
            setEditMessageValue(newEditMessageValue)
          }}
          onPaste={handleEditPaste}
          onKeyDown={handleEditKeyDown}
          minRows={1}
          maxRows={10}
          autosize
          disabled={isPending}
          styles={{
            input: {
              border: 'none',
              padding: 0,
              backgroundColor: 'transparent',
            },
          }}
        />
      </Stack>
    )
  }

  return (
    <Paper
      p="sm"
      style={{
        backgroundColor:
          colorScheme === 'dark'
            ? theme.colors[theme.primaryColor][7]
            : theme.colors[theme.primaryColor][0],
        borderRadius: theme.radius.md,
        maxWidth: '80%',
        position: 'relative',
        border: `1px solid ${
          colorScheme === 'dark'
            ? theme.colors[theme.primaryColor][5]
            : theme.colors[theme.primaryColor][3]
        }`,
      }}
    >
      <Stack gap="xs">
        {renderEditContent()}
        <Group gap="xs" wrap="nowrap">
          <ActionIcon
            variant="subtle"
            size="sm"
            color="gray"
            onClick={handleEditBoldClick}
            title="Bold (Ctrl+B)"
            style={{ cursor: 'pointer' }}
          >
            <IconBold size={18} />
          </ActionIcon>
          <ActionIcon
            variant="subtle"
            size="sm"
            color="gray"
            onClick={handleEditItalicClick}
            title="Italic (Ctrl+I)"
            style={{ cursor: 'pointer' }}
          >
            <IconItalic size={18} />
          </ActionIcon>
          <ActionIcon
            variant="subtle"
            size="sm"
            color="gray"
            onClick={handleEditUnderlineClick}
            title="Underline (Ctrl+U)"
            style={{ cursor: 'pointer' }}
          >
            <IconUnderline size={18} />
          </ActionIcon>
          <div
            style={{
              width: 1,
              height: 20,
              backgroundColor: borderColor,
              margin: '0 4px',
            }}
          />
          <Popover
            position="top-start"
            withArrow
            shadow="md"
            opened={emojiPickerOpen}
            onChange={setEmojiPickerOpen}
          >
            <Popover.Target>
              <ActionIcon
                variant="subtle"
                size="sm"
                color="gray"
                onClick={(e) => {
                  e.stopPropagation()
                  setEmojiPickerOpen(!emojiPickerOpen)
                }}
                title="Add emoji"
              >
                <IconMoodPlus size={18} />
              </ActionIcon>
            </Popover.Target>
            <Popover.Dropdown>
              <Paper p="xs" style={{ maxWidth: 320, maxHeight: 300 }}>
                <ScrollArea h={280}>
                  <Group gap="xs" style={{ flexWrap: 'wrap' }}>
                    {commonEmojis.map((emoji, index) => (
                      <ActionIcon
                        key={index}
                        variant="subtle"
                        size="lg"
                        onClick={(e) => {
                          e.stopPropagation()
                          if (editTextareaRef.current) {
                            const textarea = editTextareaRef.current
                            const start = textarea.selectionStart
                            const end = textarea.selectionEnd
                            const textBefore = editMessageValue.substring(
                              0,
                              start,
                            )
                            const textAfter = editMessageValue.substring(end)
                            const newValue = `${textBefore}${emoji}${textAfter}`
                            setEditMessageValue(newValue)
                            setTimeout(() => {
                              if (editTextareaRef.current) {
                                const newCursorPos = start + emoji.length
                                editTextareaRef.current.focus()
                                editTextareaRef.current.setSelectionRange(
                                  newCursorPos,
                                  newCursorPos,
                                )
                              }
                            }, 0)
                          }
                          setEmojiPickerOpen(false)
                        }}
                        style={{
                          fontSize: '1.5rem',
                          width: 36,
                          height: 36,
                          cursor: 'pointer',
                        }}
                        title={emoji}
                      >
                        {emoji}
                      </ActionIcon>
                    ))}
                  </Group>
                </ScrollArea>
              </Paper>
            </Popover.Dropdown>
          </Popover>
        </Group>
        <Group gap="xs" justify="flex-end" mt="xs">
          <Button size="sm" variant="subtle" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={onUpdate}
            disabled={!editMessageValue.trim() || isPending}
            loading={isPending}
            color="orange"
            variant="filled"
          >
            Update
          </Button>
        </Group>
      </Stack>
    </Paper>
  )
}
