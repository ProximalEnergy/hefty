import { useGetCompanyUsers } from '@/api/operational'
import { useGetCompanies } from '@/api/v1/admin/companies'
import { useGetAllCompanyProjectsForProject } from '@/api/v1/admin/company_projects'
import {
  ActionIcon,
  Avatar,
  Button,
  Combobox,
  Group,
  Image,
  Menu,
  Paper,
  Popover,
  ScrollArea,
  Stack,
  Text,
  Textarea,
  Tooltip,
  useCombobox,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { Dropzone, FileWithPath, IMAGE_MIME_TYPE } from '@mantine/dropzone'
import {
  IconAt,
  IconBold,
  IconItalic,
  IconLock,
  IconMoodPlus,
  IconPhoto,
  IconUnderline,
  IconUsers,
  IconX,
} from '@tabler/icons-react'
import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  ALLOWED_IMAGE_TYPES,
  MAX_IMAGE_SIZE_BYTES,
  generateImageId,
} from './utils'

interface MessageInputProps {
  eventId: number
  projectId?: string
  replyingTo: number | null
  inputValue: string
  setInputValue: (value: string) => void
  cursorPosition: number
  setCursorPosition: (pos: number) => void
  inlineImages: Array<{
    id: string
    file: File
    position: number
    preview: string
  }>
  setInlineImages: (
    updater: (
      prev: Array<{
        id: string
        file: File
        position: number
        preview: string
      }>,
    ) => Array<{ id: string; file: File; position: number; preview: string }>,
  ) => void
  pendingImages: FileWithPath[]
  setPendingImages: (images: FileWithPath[]) => void
  onSendMessage: () => void
  onCancelReply: () => void
  isPending: boolean
  savedVisibilityPreference: boolean
  setSavedVisibilityPreference: (value: boolean) => void
  isReplyingToPrivateMessage: boolean
  draftKey: string
  commonEmojis: string[]
}

function MessageInput({
  eventId: _eventId,
  projectId,
  replyingTo,
  inputValue,
  setInputValue,
  cursorPosition,
  setCursorPosition,
  inlineImages,
  setInlineImages,
  pendingImages,
  setPendingImages,
  onSendMessage,
  onCancelReply,
  isPending,
  savedVisibilityPreference,
  setSavedVisibilityPreference,
  isReplyingToPrivateMessage,
  draftKey,
  commonEmojis,
}: MessageInputProps) {
  void _eventId // eventId is required by interface but not used
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()
  const [mentionQuery, setMentionQuery] = useState<string | null>(null)
  const [emojiPickerOpen, setEmojiPickerOpen] = useState(false)
  const [imageUploadOpen, setImageUploadOpen] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const messagePrivate = isReplyingToPrivateMessage
    ? true
    : savedVisibilityPreference

  // Fetch all company users for mentions
  const { data: companyUsers } = useGetCompanyUsers({})

  // Get companies with access to this project (for event chat visibility dropdown)
  const { data: companyProjects } = useGetAllCompanyProjectsForProject({
    pathParams: { project_id: projectId || '' },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  // Get company details for companies with project access
  const companyIds = companyProjects?.map((cp) => cp.company_id) || []
  const { data: allCompanies } = useGetCompanies({
    queryParams: {
      company_ids: companyIds.length > 0 ? companyIds : undefined,
    },
    queryOptions: {
      enabled: companyIds.length > 0,
    },
  })

  // Filter out Proximal from the displayed list
  const companies = useMemo(() => {
    if (!allCompanies) return []
    return allCompanies.filter((c) => c.name_short.toLowerCase() !== 'proximal')
  }, [allCompanies])

  // Filter users based on mention query
  const filteredUsers = useMemo(() => {
    if (!mentionQuery || !companyUsers) return []

    const query = mentionQuery.toLowerCase().trim()
    if (!query) {
      return (companyUsers || []).map((u) => ({
        value: u.user_id,
        label: u.name_long,
      }))
    }

    return (companyUsers || [])
      .filter((u) => {
        const name = u.name_long.toLowerCase()
        const nameParts = name.split(/\s+/)
        return (
          nameParts.some((part) => part.startsWith(query)) ||
          name.includes(query)
        )
      })
      .map((u) => ({
        value: u.user_id,
        label: u.name_long,
      }))
  }, [mentionQuery, companyUsers])

  const combobox = useCombobox({
    onDropdownClose: () => {
      combobox.resetSelectedOption()
      setMentionQuery(null)
    },
    opened: mentionQuery !== null && filteredUsers.length > 0,
  })

  const backgroundColor =
    colorScheme === 'dark' ? theme.colors.dark[7] : theme.colors.gray[0]
  const borderColor =
    colorScheme === 'dark' ? theme.colors.dark[4] : theme.colors.gray[3]

  // Detect @ mentions in input - memoized to avoid recreation
  const detectMention = useCallback((text: string, cursorPos: number) => {
    const textBeforeCursor = text.slice(0, cursorPos)
    const lastAtIndex = textBeforeCursor.lastIndexOf('@')

    if (lastAtIndex === -1) {
      return null
    }

    const textAfterAt = textBeforeCursor.slice(lastAtIndex + 1)
    if (textAfterAt.includes(' ') || textAfterAt.includes('\n')) {
      return null
    }

    return {
      start: lastAtIndex,
      query: textAfterAt,
    }
  }, [])

  const handleInputChange = useCallback(
    (event: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = event.target.value
      const newCursorPos = event.target.selectionStart

      // Update state immediately for responsive UI
      setInputValue(newValue)
      setCursorPosition(newCursorPos)

      // Defer mention detection to avoid blocking the input
      requestAnimationFrame(() => {
        const mention = detectMention(newValue, newCursorPos)
        if (mention) {
          setMentionQuery(mention.query)
          combobox.openDropdown()
        } else {
          setMentionQuery(null)
          combobox.closeDropdown()
        }
      })
    },
    [detectMention, combobox, setInputValue, setCursorPosition],
  )

  const handlePaste = useCallback(
    async (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
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

            const lastImagePosition =
              inlineImages.length > 0
                ? Math.max(...inlineImages.map((img) => img.position))
                : -1
            const textareaCursorPos = textareaRef.current?.selectionStart || 0
            let actualCursorPos =
              lastImagePosition >= 0
                ? lastImagePosition + textareaCursorPos
                : textareaCursorPos

            const textBeforeCursor = inputValue.slice(0, actualCursorPos)
            const textAfterCursor = inputValue.slice(actualCursorPos)
            // Prepend with newline if there's text before and it doesn't end with newline
            const needsNewlineBefore =
              actualCursorPos > 0 && !textBeforeCursor.endsWith('\n')
            const needsNewlineAfter =
              textAfterCursor.length > 0 && !textAfterCursor.startsWith('\n')

            let positionOffset = 0
            if (needsNewlineBefore || needsNewlineAfter) {
              let newInputValue = inputValue
              if (needsNewlineBefore) {
                newInputValue = textBeforeCursor + '\n' + textAfterCursor
                actualCursorPos += 1
                positionOffset += 1
              }
              if (needsNewlineAfter) {
                const beforePart = newInputValue.slice(0, actualCursorPos + 1)
                const afterPart = newInputValue.slice(actualCursorPos + 1)
                newInputValue = beforePart + '\n' + afterPart
                positionOffset += 1
              }
              setInputValue(newInputValue)
            }

            const newInlineImage = {
              id: imageId,
              file,
              position: actualCursorPos,
              preview,
            }

            setInlineImages((prev) => {
              const updated = prev.map((img) =>
                img.position >= actualCursorPos
                  ? {
                      ...img,
                      position: img.position + positionOffset + 1,
                    }
                  : img,
              )
              return [...updated, newInlineImage].sort(
                (a, b) => a.position - b.position,
              )
            })

            setTimeout(() => {
              if (textareaRef.current) {
                textareaRef.current.focus()
                textareaRef.current.setSelectionRange(
                  textareaCursorPos,
                  textareaCursorPos,
                )
                setCursorPosition(actualCursorPos)
              }
            }, 0)
          }
          break
        }
      }
    },
    [
      inlineImages,
      inputValue,
      setInputValue,
      setInlineImages,
      setCursorPosition,
    ],
  )

  const removeInlineImage = useCallback(
    (imageId: string) => {
      setInlineImages((prev) => {
        const image = prev.find((img) => img.id === imageId)
        if (!image) return prev

        URL.revokeObjectURL(image.preview)

        return prev
          .filter((img) => img.id !== imageId)
          .map((img) =>
            img.position > image.position
              ? { ...img, position: img.position - 1 }
              : img,
          )
      })
    },
    [setInlineImages],
  )

  const handleTextareaClick = useCallback(
    (event: React.MouseEvent<HTMLTextAreaElement>) => {
      const target = event.target as HTMLTextAreaElement
      const lastImagePosition =
        inlineImages.length > 0
          ? Math.max(...inlineImages.map((img) => img.position))
          : -1
      const actualCursorPos =
        lastImagePosition >= 0
          ? lastImagePosition + target.selectionStart
          : target.selectionStart
      setCursorPosition(actualCursorPos)

      const mention = detectMention(inputValue, actualCursorPos)
      if (mention) {
        setMentionQuery(mention.query)
        combobox.openDropdown()
      } else {
        setMentionQuery(null)
        combobox.closeDropdown()
      }
    },
    [inputValue, inlineImages, detectMention, combobox, setCursorPosition],
  )

  const handleInsertMention = useCallback(
    (userName: string) => {
      const mention = detectMention(inputValue, cursorPosition)
      if (!mention) return

      const beforeMention = inputValue.slice(0, mention.start)
      const afterCursor = inputValue.slice(cursorPosition)
      const newValue = `${beforeMention}@${userName} ${afterCursor}`

      setInputValue(newValue)
      setMentionQuery(null)
      combobox.closeDropdown()

      setTimeout(() => {
        if (textareaRef.current) {
          const newCursorPos = mention.start + userName.length + 2
          const lastImagePosition =
            inlineImages.length > 0
              ? Math.max(...inlineImages.map((img) => img.position))
              : -1
          const newTextareaPos =
            lastImagePosition >= 0
              ? newCursorPos - lastImagePosition
              : newCursorPos
          textareaRef.current.setSelectionRange(newTextareaPos, newTextareaPos)
          setCursorPosition(newCursorPos)
        }
      }, 0)
    },
    [
      inputValue,
      cursorPosition,
      inlineImages,
      detectMention,
      combobox,
      setInputValue,
      setCursorPosition,
    ],
  )

  const wrapSelection = useCallback(
    (before: string, after: string) => {
      if (!textareaRef.current) return

      const textarea = textareaRef.current
      const lastImagePosition =
        inlineImages.length > 0
          ? Math.max(...inlineImages.map((img) => img.position))
          : -1
      const textareaStart = textarea.selectionStart
      const textareaEnd = textarea.selectionEnd
      const start =
        lastImagePosition >= 0
          ? lastImagePosition + textareaStart
          : textareaStart
      const end =
        lastImagePosition >= 0 ? lastImagePosition + textareaEnd : textareaEnd

      const selectedText = inputValue.substring(start, end)
      const textBefore = inputValue.substring(0, start)
      const textAfter = inputValue.substring(end)

      const newValue = `${textBefore}${before}${selectedText}${after}${textAfter}`
      setInputValue(newValue)

      setTimeout(() => {
        if (textareaRef.current) {
          const newCursorPos = selectedText
            ? start + before.length + selectedText.length + after.length
            : start + before.length
          const newTextareaPos =
            lastImagePosition >= 0
              ? newCursorPos - lastImagePosition
              : newCursorPos
          textarea.focus()
          textarea.setSelectionRange(newTextareaPos, newTextareaPos)
          setCursorPosition(newCursorPos)
        }
      }, 0)
    },
    [inputValue, inlineImages, setInputValue, setCursorPosition],
  )

  const handleBoldClick = useCallback(() => {
    wrapSelection('**', '**')
  }, [wrapSelection])

  const handleItalicClick = useCallback(() => {
    wrapSelection('*', '*')
  }, [wrapSelection])

  const handleUnderlineClick = useCallback(() => {
    wrapSelection('++', '++')
  }, [wrapSelection])

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.ctrlKey || event.metaKey) {
        if (event.key === 'b') {
          event.preventDefault()
          handleBoldClick()
          return
        }
        if (event.key === 'i') {
          event.preventDefault()
          handleItalicClick()
          return
        }
        if (event.key === 'u') {
          event.preventDefault()
          handleUnderlineClick()
          return
        }
      }

      if (mentionQuery !== null && filteredUsers.length > 0) {
        if (event.key === 'ArrowDown') {
          event.preventDefault()
          combobox.selectNextOption()
          return
        }
        if (event.key === 'ArrowUp') {
          event.preventDefault()
          combobox.selectPreviousOption()
          return
        }
        if (event.key === 'Enter' || event.key === 'Tab') {
          if (event.key === 'Enter' && event.shiftKey) {
            return
          }
          const selectedIndex = combobox.selectedOptionIndex
          if (
            selectedIndex !== null &&
            selectedIndex >= 0 &&
            selectedIndex < filteredUsers.length
          ) {
            event.preventDefault()
            const user = filteredUsers[selectedIndex]
            if (user) {
              handleInsertMention(user.label)
            }
          }
          return
        }
        if (event.key === 'Escape') {
          event.preventDefault()
          setMentionQuery(null)
          combobox.closeDropdown()
          return
        }
      }

      if (event.key === 'Enter' && !event.shiftKey) {
        if (mentionQuery === null) {
          event.preventDefault()
          onSendMessage()
        }
      }
    },
    [
      mentionQuery,
      filteredUsers,
      combobox,
      handleBoldClick,
      handleItalicClick,
      handleUnderlineClick,
      handleInsertMention,
      onSendMessage,
    ],
  )

  const insertEmoji = useCallback(
    (emoji: string) => {
      if (!textareaRef.current) return

      const textarea = textareaRef.current
      const lastImagePosition =
        inlineImages.length > 0
          ? Math.max(...inlineImages.map((img) => img.position))
          : -1
      const textareaStart = textarea.selectionStart
      const textareaEnd = textarea.selectionEnd
      const start =
        lastImagePosition >= 0
          ? lastImagePosition + textareaStart
          : textareaStart
      const end =
        lastImagePosition >= 0 ? lastImagePosition + textareaEnd : textareaEnd

      const textBefore = inputValue.substring(0, start)
      const textAfter = inputValue.substring(end)

      const newValue = `${textBefore}${emoji}${textAfter}`
      setInputValue(newValue)

      setTimeout(() => {
        if (textareaRef.current) {
          const newCursorPos = start + emoji.length
          const newTextareaPos =
            lastImagePosition >= 0
              ? newCursorPos - lastImagePosition
              : newCursorPos
          textarea.focus()
          textarea.setSelectionRange(newTextareaPos, newTextareaPos)
          setCursorPosition(newCursorPos)
        }
      }, 0)

      setEmojiPickerOpen(false)
    },
    [inputValue, inlineImages, setInputValue, setCursorPosition],
  )

  // Focus and scroll to textarea when replying
  useEffect(() => {
    if (replyingTo) {
      // Use setTimeout to ensure the DOM has updated with the new inputValue
      const timeoutId = setTimeout(() => {
        // Find the textarea - either the main one (textareaRef) or the last one after images
        let textarea: HTMLTextAreaElement | null = textareaRef.current

        // If we have inline images, find the last textarea (after all images)
        if (!textarea && inlineImages.length > 0) {
          const allTextareas = document.querySelectorAll(
            'textarea[placeholder*="comment"]',
          )
          if (allTextareas.length > 0) {
            textarea = allTextareas[
              allTextareas.length - 1
            ] as HTMLTextAreaElement
          }
        }

        if (textarea) {
          // Calculate cursor position at end of text (after quoted preview)
          // The reply text format is: @username "preview..." \n
          // We want cursor right after the newline

          // If there are inline images, we need to calculate position relative to textAfterLastImage
          const lastImagePosition =
            inlineImages.length > 0
              ? Math.max(...inlineImages.map((img) => img.position))
              : -1

          let cursorPos: number
          if (lastImagePosition >= 0) {
            // Text after last image starts at lastImagePosition
            // Cursor should be at the end of the text after the last image
            const textAfterLastImage = inputValue.slice(lastImagePosition)
            cursorPos = textAfterLastImage.length
          } else {
            // No images, cursor at end of full inputValue
            cursorPos = inputValue.length
          }

          // Set cursor to end of text
          textarea.setSelectionRange(cursorPos, cursorPos)
          textarea.focus()

          // Scroll textarea into view smoothly
          textarea.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
      }, 10)

      return () => clearTimeout(timeoutId)
    }
  }, [replyingTo, inputValue, inlineImages])

  // Render inline images and text
  const renderInputContent = useCallback(() => {
    const sortedImages = [...inlineImages].sort(
      (a, b) => a.position - b.position,
    )

    if (sortedImages.length === 0) {
      return (
        <Textarea
          ref={textareaRef}
          placeholder={replyingTo ? 'Reply to comment...' : 'Add comment...'}
          value={inputValue}
          onChange={handleInputChange}
          onPaste={handlePaste}
          onKeyDown={handleKeyDown}
          onClick={handleTextareaClick}
          onSelect={(e: React.SyntheticEvent<HTMLTextAreaElement>) => {
            const target = e.target as HTMLTextAreaElement
            setCursorPosition(target.selectionStart)
          }}
          minRows={1}
          maxRows={4}
          autosize
          disabled={isPending}
          size="md"
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

    const parts: Array<
      | {
          type: 'text'
          content: string
          startPos: number
          endPos: number
        }
      | {
          type: 'image'
          content: { id: string; preview: string; file: File }
          position: number
        }
    > = []

    let currentPos = 0
    sortedImages.forEach((img) => {
      if (currentPos < img.position) {
        parts.push({
          type: 'text',
          content: inputValue.slice(currentPos, img.position),
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
        },
        position: img.position,
      })

      currentPos = img.position
    })

    if (currentPos < inputValue.length) {
      parts.push({
        type: 'text',
        content: inputValue.slice(currentPos),
        startPos: currentPos,
        endPos: inputValue.length,
      })
    }

    const lastImagePosition =
      sortedImages.length > 0
        ? Math.max(...sortedImages.map((img) => img.position))
        : -1
    const textAfterLastImage =
      lastImagePosition >= 0 ? inputValue.slice(lastImagePosition) : inputValue

    return (
      <Stack gap="xs">
        <Stack gap="xs">
          {parts.map((part, idx) => {
            if (part.type === 'text') {
              if (part.endPos <= lastImagePosition) {
                return (
                  <Textarea
                    key={`text-${idx}`}
                    placeholder={
                      replyingTo ? 'Reply to comment...' : 'Add comment...'
                    }
                    value={part.content}
                    onChange={(e) => {
                      const newSegmentText = e.target.value
                      const lengthDiff =
                        newSegmentText.length - part.content.length
                      const newInputValue =
                        inputValue.slice(0, part.startPos) +
                        newSegmentText +
                        inputValue.slice(part.endPos)
                      setInputValue(newInputValue)

                      if (lengthDiff !== 0) {
                        setInlineImages((prev) =>
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

                      const newCursorPos =
                        part.startPos + e.target.selectionStart
                      setCursorPosition(newCursorPos)

                      const mention = detectMention(newInputValue, newCursorPos)
                      if (mention) {
                        setMentionQuery(mention.query)
                        combobox.openDropdown()
                      } else {
                        setMentionQuery(null)
                        combobox.closeDropdown()
                      }
                    }}
                    onPaste={handlePaste}
                    onKeyDown={handleKeyDown}
                    onClick={(e) => {
                      const target = e.target as HTMLTextAreaElement
                      const newCursorPos = part.startPos + target.selectionStart
                      setCursorPosition(newCursorPos)

                      const mention = detectMention(inputValue, newCursorPos)
                      if (mention) {
                        setMentionQuery(mention.query)
                        combobox.openDropdown()
                      } else {
                        setMentionQuery(null)
                        combobox.closeDropdown()
                      }
                    }}
                    onSelect={(
                      e: React.SyntheticEvent<HTMLTextAreaElement>,
                    ) => {
                      const target = e.target as HTMLTextAreaElement
                      const newCursorPos = part.startPos + target.selectionStart
                      setCursorPosition(newCursorPos)
                    }}
                    minRows={1}
                    maxRows={4}
                    autosize
                    disabled={isPending}
                    size="md"
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
                    onClick={() => removeInlineImage(img.id)}
                  >
                    <IconX size={12} />
                  </ActionIcon>
                </Paper>
              )
            }
          })}
        </Stack>

        <Textarea
          ref={textareaRef}
          placeholder={replyingTo ? 'Reply to comment...' : 'Add more text...'}
          value={textAfterLastImage}
          onChange={(e) => {
            const newTextAfterLastImage = e.target.value
            const newInputValue =
              lastImagePosition >= 0
                ? inputValue.slice(0, lastImagePosition) + newTextAfterLastImage
                : newTextAfterLastImage
            setInputValue(newInputValue)
            const newCursorPos =
              lastImagePosition >= 0
                ? lastImagePosition + e.target.selectionStart
                : e.target.selectionStart
            setCursorPosition(newCursorPos)

            const mention = detectMention(newInputValue, newCursorPos)
            if (mention) {
              setMentionQuery(mention.query)
              combobox.openDropdown()
            } else {
              setMentionQuery(null)
              combobox.closeDropdown()
            }
          }}
          onPaste={handlePaste}
          onKeyDown={handleKeyDown}
          onClick={handleTextareaClick}
          onSelect={(e: React.SyntheticEvent<HTMLTextAreaElement>) => {
            const target = e.target as HTMLTextAreaElement
            const newCursorPos =
              lastImagePosition >= 0
                ? lastImagePosition + target.selectionStart
                : target.selectionStart
            setCursorPosition(newCursorPos)
          }}
          minRows={1}
          maxRows={4}
          autosize
          disabled={isPending}
          size="md"
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
  }, [
    inlineImages,
    inputValue,
    replyingTo,
    handleInputChange,
    handlePaste,
    handleKeyDown,
    handleTextareaClick,
    setCursorPosition,
    detectMention,
    combobox,
    isPending,
    removeInlineImage,
    colorScheme,
    theme,
    setInlineImages,
    setInputValue,
  ])

  const handleOptionSubmit = useCallback(
    (value: string) => {
      const user = filteredUsers.find((u) => u.value === value)
      if (user) {
        handleInsertMention(user.label)
      }
    },
    [filteredUsers, handleInsertMention],
  )

  return (
    <Paper
      p={0}
      style={{
        borderBottom: `1px solid ${borderColor}`,
        backgroundColor,
        borderRadius: theme.radius.md,
        boxShadow: theme.shadows.sm,
      }}
    >
      <Combobox store={combobox} onOptionSubmit={handleOptionSubmit}>
        <Combobox.Target>
          <Stack gap="sm" p="md">
            <Paper
              p="md"
              style={{
                border: `1px solid ${
                  colorScheme === 'dark'
                    ? theme.colors.dark[4]
                    : theme.colors.gray[3]
                }`,
                borderRadius: theme.radius.md,
                backgroundColor:
                  colorScheme === 'dark'
                    ? theme.colors.dark[8]
                    : theme.colors.gray[0],
                minHeight: '60px',
              }}
            >
              <Stack gap="xs">{renderInputContent()}</Stack>
            </Paper>
            <Group justify="space-between" align="center" wrap="nowrap">
              <Group gap="xs" wrap="nowrap">
                <ActionIcon
                  variant="subtle"
                  size="sm"
                  color="gray"
                  onClick={handleBoldClick}
                  title="Bold (Ctrl+B)"
                  style={{ cursor: 'pointer' }}
                >
                  <IconBold size={18} />
                </ActionIcon>
                <ActionIcon
                  variant="subtle"
                  size="sm"
                  color="gray"
                  onClick={handleItalicClick}
                  title="Italic (Ctrl+I)"
                  style={{ cursor: 'pointer' }}
                >
                  <IconItalic size={18} />
                </ActionIcon>
                <ActionIcon
                  variant="subtle"
                  size="sm"
                  color="gray"
                  onClick={handleUnderlineClick}
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
                      style={{ cursor: 'pointer' }}
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
                                insertEmoji(emoji)
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
                <Popover
                  width={300}
                  position="top"
                  withArrow
                  shadow="md"
                  opened={imageUploadOpen}
                  onChange={setImageUploadOpen}
                >
                  <Popover.Target>
                    <ActionIcon
                      variant="subtle"
                      size="sm"
                      color="gray"
                      title="Add image"
                      onClick={(e) => {
                        e.stopPropagation()
                        setImageUploadOpen(!imageUploadOpen)
                      }}
                      style={{ cursor: 'pointer' }}
                    >
                      <IconPhoto size={18} />
                    </ActionIcon>
                  </Popover.Target>
                  <Popover.Dropdown>
                    <Stack gap="xs">
                      <Text size="sm" fw={500}>
                        Add Image
                      </Text>
                      <Text size="xs" c="dimmed">
                        You can paste images (Ctrl+V Windows, Command+V Mac)
                        directly in the input field OR you can upload them here
                        as an attachment to your message.
                      </Text>
                      {pendingImages.length === 0 ? (
                        <Dropzone
                          onDrop={(files) => {
                            setPendingImages(files.slice(0, 5))
                          }}
                          accept={IMAGE_MIME_TYPE}
                          maxSize={10 * 1024 * 1024}
                          multiple
                          maxFiles={5}
                        >
                          <Group
                            justify="center"
                            gap="xl"
                            mih={50}
                            style={{ pointerEvents: 'none' }}
                          >
                            <Dropzone.Accept>
                              <Text size="sm">Drop images here</Text>
                            </Dropzone.Accept>
                            <Dropzone.Reject>
                              <Text size="sm" c="red">
                                Invalid file type or too large
                              </Text>
                            </Dropzone.Reject>
                            <Dropzone.Idle>
                              <Text size="sm" c="dimmed">
                                Drag images here or click to select
                              </Text>
                            </Dropzone.Idle>
                          </Group>
                        </Dropzone>
                      ) : (
                        <Stack gap="xs">
                          {pendingImages.map((file, index) => (
                            <Group key={index} justify="space-between">
                              <Text size="sm" truncate style={{ flex: 1 }}>
                                {file.name}
                              </Text>
                              <ActionIcon
                                size="sm"
                                variant="subtle"
                                color="red"
                                onClick={() => {
                                  setPendingImages(
                                    pendingImages.filter((_, i) => i !== index),
                                  )
                                }}
                              >
                                <IconX size={16} />
                              </ActionIcon>
                            </Group>
                          ))}
                          <Button
                            size="xs"
                            variant="subtle"
                            onClick={() => setPendingImages([])}
                          >
                            Clear all
                          </Button>
                        </Stack>
                      )}
                      <Text size="xs" c="dimmed">
                        Max 5 images, 10MB each
                      </Text>
                    </Stack>
                  </Popover.Dropdown>
                </Popover>
                <ActionIcon
                  variant="subtle"
                  size="sm"
                  color="gray"
                  title="Mention user"
                  onClick={(e) => {
                    e.stopPropagation()
                    const lastImagePosition =
                      inlineImages.length > 0
                        ? Math.max(...inlineImages.map((img) => img.position))
                        : -1
                    const textareaCursorPos =
                      textareaRef.current?.selectionStart || 0
                    const actualCursorPos =
                      lastImagePosition >= 0
                        ? lastImagePosition + textareaCursorPos
                        : textareaCursorPos
                    const newValue = `${inputValue.slice(
                      0,
                      actualCursorPos,
                    )}@${inputValue.slice(actualCursorPos)}`
                    setInputValue(newValue)
                    setTimeout(() => {
                      const newCursorPos = actualCursorPos + 1
                      const newTextareaPos =
                        lastImagePosition >= 0
                          ? newCursorPos - lastImagePosition
                          : newCursorPos
                      textareaRef.current?.setSelectionRange(
                        newTextareaPos,
                        newTextareaPos,
                      )
                      textareaRef.current?.focus()
                      setCursorPosition(newCursorPos)
                      const mention = detectMention(newValue, newCursorPos)
                      if (mention) {
                        setMentionQuery(mention.query)
                        combobox.openDropdown()
                      }
                    }, 0)
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  <IconAt size={18} />
                </ActionIcon>
              </Group>
              <Group gap="xs" wrap="nowrap">
                {replyingTo && (
                  <Button
                    variant="subtle"
                    size="sm"
                    onClick={() => {
                      onCancelReply()
                      localStorage.removeItem(draftKey)
                    }}
                  >
                    Cancel
                  </Button>
                )}
                <Menu
                  shadow="md"
                  width={300}
                  position="top-end"
                  disabled={isReplyingToPrivateMessage}
                >
                  <Menu.Target>
                    <Tooltip
                      label={
                        isReplyingToPrivateMessage
                          ? "You can't post non-private when replying to a private message"
                          : messagePrivate
                            ? 'Your colleagues'
                            : `Companies with project access`
                      }
                      position="top"
                      withArrow
                    >
                      <ActionIcon
                        variant="subtle"
                        size="lg"
                        disabled={isReplyingToPrivateMessage}
                        style={{
                          border: `1px solid ${
                            colorScheme === 'dark'
                              ? theme.colors.dark[4]
                              : theme.colors.gray[3]
                          }`,
                          opacity: isReplyingToPrivateMessage ? 0.6 : 1,
                        }}
                      >
                        {messagePrivate ? (
                          <IconLock
                            size={18}
                            style={{
                              color:
                                colorScheme === 'dark'
                                  ? theme.colors.orange[4]
                                  : theme.colors.orange[6],
                            }}
                          />
                        ) : (
                          <IconUsers
                            size={18}
                            style={{
                              color:
                                colorScheme === 'dark'
                                  ? theme.colors.orange[4]
                                  : theme.colors.orange[6],
                            }}
                          />
                        )}
                      </ActionIcon>
                    </Tooltip>
                  </Menu.Target>
                  <Menu.Dropdown>
                    <Menu.Item
                      leftSection={<IconLock size={16} />}
                      onClick={() => setSavedVisibilityPreference(true)}
                      style={{
                        backgroundColor: messagePrivate
                          ? colorScheme === 'dark'
                            ? theme.colors.dark[6]
                            : theme.colors.gray[1]
                          : 'transparent',
                      }}
                    >
                      <Stack gap={2}>
                        <Text size="sm" fw={500}>
                          Visible to your colleagues
                        </Text>
                        <Text size="xs" c="dimmed">
                          Only users from your company can see this message
                        </Text>
                      </Stack>
                    </Menu.Item>
                    <Menu.Item
                      leftSection={<IconUsers size={16} />}
                      onClick={() => setSavedVisibilityPreference(false)}
                      style={{
                        backgroundColor: !messagePrivate
                          ? colorScheme === 'dark'
                            ? theme.colors.dark[6]
                            : theme.colors.gray[1]
                          : 'transparent',
                      }}
                    >
                      <Stack gap={2}>
                        <Text size="sm" fw={500}>
                          Companies with project access
                        </Text>
                        <Text size="xs" c="dimmed">
                          {companies && companies.length > 0
                            ? `Visible to: ${companies.map((c) => c.name_long).join(', ')}`
                            : 'Companies with project access'}
                        </Text>
                      </Stack>
                    </Menu.Item>
                  </Menu.Dropdown>
                </Menu>
                <Button
                  size="sm"
                  onClick={onSendMessage}
                  disabled={
                    (!inputValue.trim() && pendingImages.length === 0) ||
                    isPending
                  }
                  loading={isPending}
                  color="orange"
                  variant="filled"
                >
                  Submit
                </Button>
              </Group>
            </Group>
          </Stack>
        </Combobox.Target>

        {mentionQuery !== null && filteredUsers.length > 0 && (
          <Combobox.Dropdown>
            <Combobox.Options>
              {filteredUsers.length === 0 ? (
                <Combobox.Empty>No users found</Combobox.Empty>
              ) : (
                filteredUsers.map((user) => (
                  <Combobox.Option value={user.value} key={user.value}>
                    <Group gap="xs">
                      <Avatar size="sm" radius="xl">
                        {user.label
                          .split(' ')
                          .map((n) => n[0])
                          .join('')
                          .toUpperCase()
                          .slice(0, 2)}
                      </Avatar>
                      <Text size="sm">{user.label}</Text>
                    </Group>
                  </Combobox.Option>
                ))
              )}
            </Combobox.Options>
          </Combobox.Dropdown>
        )}
      </Combobox>
    </Paper>
  )
}

const MessageInputMemoized = memo(MessageInput)
export { MessageInputMemoized as MessageInput }
