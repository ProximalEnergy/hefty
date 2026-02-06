import { useGetUsers } from '@/api/v1/admin/users'
import {
  useGetEventMessageReactions,
  useToggleEventMessageReaction,
} from '@/api/v1/operational/event_message_reactions'
import {
  useCreateEventMessage,
  useDeleteEventMessage,
  useGetEventChatMuteStatus,
  useGetEventMessageImages,
  useGetEventMessages,
  useToggleEventChatMute,
  useUpdateEventMessage,
  useUploadEventMessageImage,
} from '@/api/v1/operational/event_messages'
import { formatRelativeTime } from '@/utils/relativeTime'
import { useUser } from '@clerk/clerk-react'
import {
  Badge,
  Group,
  Select,
  Stack,
  Text,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { FileWithPath } from '@mantine/dropzone'
import { IconChevronDown } from '@tabler/icons-react'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { MessageInput, MessageList, MuteToggle } from './event-chat'

dayjs.extend(utc)

interface EventChatProps {
  eventId: number
  projectId: string
}

export function EventChat({ eventId, projectId }: EventChatProps) {
  const { user } = useUser()
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()
  const [hoveredMessageId, setHoveredMessageId] = useState<number | null>(null)
  const [replyingTo, setReplyingTo] = useState<number | null>(null)
  const [editingMessageId, setEditingMessageId] = useState<number | null>(null)
  const [editMessageValue, setEditMessageValue] = useState<string>('')
  const [addReactionMessageId, setAddReactionMessageId] = useState<
    number | null
  >(null)
  const [emojiPickerOpen, setEmojiPickerOpen] = useState(false)
  const [pendingImages, setPendingImages] = useState<FileWithPath[]>([])
  // Inline images: array of { id: string, file: File, position: number }
  const [inlineImages, setInlineImages] = useState<
    Array<{ id: string; file: File; position: number; preview: string }>
  >([])
  // Edit inline images: array of { id: string, file?: File, position: number, preview: string, imageId?: string }
  // New images have `file` and `preview` (from URL.createObjectURL)
  // Existing images have `presigned_url` as `preview` and `imageId` (from API), no `file`
  const [editInlineImages, setEditInlineImages] = useState<
    Array<{
      id: string
      file?: File
      position: number
      preview: string
      imageId?: string // For existing images from API
      placeholderIndex?: number // Original placeholder index for existing images
    }>
  >([])
  // Message visibility: false = visible to all companies, true = only your company
  // Load from localStorage, default to false (public)
  const visibilityKey = 'event-chat-visibility-preference'
  const [savedVisibilityPreference, setSavedVisibilityPreference] = useState(
    () => {
      const saved = localStorage.getItem(visibilityKey)
      return saved === 'true'
    },
  )
  // localStorage key for draft
  const draftKey = `event-chat-draft-${eventId}`

  // Check for mute=true URL parameter and auto-mute if present
  const toggleMuteHook = useToggleEventChatMute()
  const { data: muteStatus } = useGetEventChatMuteStatus(
    eventId,
    projectId || '',
  )
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('mute') === 'true' && muteStatus && !muteStatus.muted) {
      // Auto-mute if URL has mute=true and conversation is not already muted
      if (projectId) {
        toggleMuteHook.mutate({ eventId, projectId })
      }
      // Remove the mute parameter from URL
      params.delete('mute')
      const newUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ''}`
      window.history.replaceState({}, '', newUrl)
    }
  }, [eventId, projectId, muteStatus, toggleMuteHook])

  // Load draft from localStorage using lazy initialization
  const [inputValue, setInputValue] = useState(() => {
    const savedDraft = localStorage.getItem(draftKey)
    return savedDraft || ''
  })
  const [cursorPosition, setCursorPosition] = useState(0)

  // Save draft to localStorage when inputValue changes (debounced)
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (inputValue.trim()) {
        localStorage.setItem(draftKey, inputValue)
      } else {
        localStorage.removeItem(draftKey)
      }
    }, 500) // Debounce by 500ms

    return () => clearTimeout(timeoutId)
  }, [inputValue, draftKey])

  // Extended emoji reactions
  const emojiReactions = [
    { emoji: '👍', type: 'thumbs_up', label: 'Thumbs up' },
    { emoji: '👀', type: 'eyes', label: 'Eyes' },
    { emoji: '❓', type: 'question_mark', label: 'Question' },
    { emoji: '❤️', type: 'heart', label: 'Heart' },
    { emoji: '😂', type: 'laughing', label: 'Laughing' },
    { emoji: '😮', type: 'surprised', label: 'Surprised' },
    { emoji: '😢', type: 'sad', label: 'Sad' },
    { emoji: '😡', type: 'angry', label: 'Angry' },
    { emoji: '🔥', type: 'fire', label: 'Fire' },
    { emoji: '🎉', type: 'party', label: 'Party' },
    { emoji: '✅', type: 'check', label: 'Check' },
    { emoji: '👏', type: 'clap', label: 'Clap' },
    { emoji: '💯', type: 'hundred', label: '100' },
    { emoji: '🚀', type: 'rocket', label: 'Rocket' },
    { emoji: '💡', type: 'lightbulb', label: 'Lightbulb' },
    { emoji: '⭐', type: 'star', label: 'Star' },
    { emoji: '🎯', type: 'target', label: 'Target' },
    { emoji: '🙏', type: 'pray', label: 'Pray' },
  ]

  const { data: messages, isLoading } = useGetEventMessages({
    queryParams: {
      event_id: eventId,
      project_id: projectId,
    },
    queryOptions: {
      enabled: !!eventId && eventId > 0,
    },
  })

  // Fetch all reactions for the event in one batch call
  const { data: allReactions } = useGetEventMessageReactions({
    queryParams: {
      event_id: eventId,
      project_id: projectId,
    },
    queryOptions: {
      enabled: !!eventId && eventId > 0,
    },
  })

  // Create a map from message_id to reactions for quick lookup
  const reactionsByMessageId = useMemo(() => {
    if (!allReactions) {
      return new Map<
        number,
        Array<{
          reaction_id: number
          event_message_id: number
          user_id: string
          reaction_type: string
          created_at: string
        }>
      >()
    }
    const map = new Map<
      number,
      Array<{
        reaction_id: number
        event_message_id: number
        user_id: string
        reaction_type: string
        created_at: string
      }>
    >()
    allReactions.forEach((reaction) => {
      if (!map.has(reaction.event_message_id)) {
        map.set(reaction.event_message_id, [])
      }
      map.get(reaction.event_message_id)!.push(reaction)
    })
    return map
  }, [allReactions])

  // Check if replying to a private message
  const repliedToMessage = messages?.find(
    (m) => m.event_message_id === replyingTo,
  )
  const isReplyingToPrivateMessage = repliedToMessage?.private === true

  // Save visibility preference to localStorage whenever it changes (but not when forced by reply)
  useEffect(() => {
    if (!isReplyingToPrivateMessage) {
      localStorage.setItem(visibilityKey, String(savedVisibilityPreference))
    }
  }, [savedVisibilityPreference, isReplyingToPrivateMessage, visibilityKey])

  // Extract unique user_ids from messages to fetch user names for display
  const userIds = useMemo(() => {
    if (!messages) return []
    return Array.from(new Set(messages.map((m) => m.user_id)))
  }, [messages])

  // Fetch users for message display
  const { data: users, isLoading: isLoadingUsers } = useGetUsers({
    queryParams: { user_ids: userIds, include_image_urls: true },
    queryOptions: {
      enabled: userIds.length > 0,
    },
  })

  // Track if we've ever successfully loaded both messages and users (to distinguish initial load from new messages)
  const hasLoadedBothRef = useRef(false)
  useEffect(() => {
    // Mark as loaded once we have messages loaded AND (no users needed OR users loaded)
    const messagesLoaded = messages && !isLoading
    const usersNotNeeded = userIds.length === 0
    const usersLoaded = userIds.length > 0 ? users && !isLoadingUsers : true

    if (messagesLoaded && (usersNotNeeded || usersLoaded)) {
      hasLoadedBothRef.current = true
    }
  }, [messages, users, isLoading, isLoadingUsers, userIds.length])

  // Only show loading on initial load - wait for both messages and users to load
  // Once both have loaded at least once, show new messages immediately even if users are still loading
  const isInitialLoad =
    !hasLoadedBothRef.current &&
    (isLoading || (userIds.length > 0 && isLoadingUsers))

  // Create a map from user_id to name_long
  const userIdToName = useMemo(() => {
    const m = new Map<string, string>()
    ;(users || []).forEach((u) => m.set(u.user_id, u.name_long))
    return m
  }, [users])

  // Create a map from user_id to image_url
  const userIdToImageUrl = useMemo(() => {
    const m = new Map<string, string>()
    ;(users || []).forEach((u) => {
      if (u.image_url) {
        m.set(u.user_id, u.image_url)
      }
    })
    return m
  }, [users])

  // Helper function to get user initials
  const getUserInitials = (name: string): string => {
    const parts = name.split(' ')
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
    }
    return name[0]?.toUpperCase() || '?'
  }

  // Helper function to format timestamp creatively
  const formatTimestamp = (date: string): string => {
    const now = dayjs()
    const messageDate = dayjs.utc(date).local()
    const diffInDays = now.diff(messageDate, 'day')

    // Less than 24 hours ago: relative format
    if (diffInDays < 1) {
      return formatRelativeTime(messageDate.toDate()).relative
    }

    // Less than 3 days ago: "Day, Time" format (e.g., "Thursday, 4:56pm")
    if (diffInDays < 3) {
      return messageDate.format('dddd, h:mm A')
    }

    // Older than 3 days: Standard format
    return messageDate.format('MMM D, YYYY h:mm A')
  }

  // Helper function to format edited timestamp for tooltip
  const formatEditedTimestamp = (date: string): string => {
    const editedDate = dayjs.utc(date).local()
    return editedDate.format('MMM D, YYYY h:mm A')
  }

  // Helper function to check if message is from current user
  const isCurrentUser = (userId: string): boolean => {
    return user?.id === userId
  }

  const [sortOrder, setSortOrder] = useState<'most_recent' | 'oldest'>(
    'most_recent',
  )

  // Sort messages based on sort order
  const sortedMessages = useMemo(() => {
    if (!messages) return []
    const sorted = [...messages]
    if (sortOrder === 'most_recent') {
      return sorted.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      )
    } else {
      return sorted.sort(
        (a, b) =>
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      )
    }
  }, [messages, sortOrder])

  // Track previously seen message IDs for animation
  const previousMessageIdsRef = useRef<Set<number>>(new Set())
  const [animatingMessageIds, setAnimatingMessageIds] = useState<Set<number>>(
    new Set(),
  )
  const timeoutRef = useRef<number | null>(null)
  const clearTimeoutRef = useRef<number | null>(null)

  // Flatten messages and sort chronologically
  const organizedMessages = useMemo(() => {
    if (!sortedMessages) return []

    // Create a map of ALL messages by ID for quick lookup (including deleted parent messages)
    const messageMap = new Map<number, (typeof sortedMessages)[0]>()
    sortedMessages.forEach((message) => {
      messageMap.set(message.event_message_id, message)
    })

    // Return all messages with parent info attached
    return sortedMessages.map((message) => ({
      ...message,
      parentMessage: message.parent_message_id
        ? messageMap.get(message.parent_message_id)
        : undefined,
    }))
  }, [sortedMessages])

  // Track new messages and trigger animation
  useEffect(() => {
    if (!organizedMessages || organizedMessages.length === 0) return

    const currentMessageIds = new Set(
      organizedMessages.map((m) => m.event_message_id),
    )

    // Identify new messages (ones we haven't seen before)
    const newIds = new Set<number>()
    currentMessageIds.forEach((id) => {
      if (!previousMessageIdsRef.current.has(id)) {
        newIds.add(id)
      }
    })

    // Update animating message IDs if there are new messages
    // Using setTimeout to defer state update and avoid linter warning
    if (newIds.size > 0) {
      // Clear any existing timeouts
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current)
      }
      if (clearTimeoutRef.current !== null) {
        clearTimeout(clearTimeoutRef.current)
      }
      // Update ref first
      previousMessageIdsRef.current = currentMessageIds
      // Defer state update to next tick
      timeoutRef.current = window.setTimeout(() => {
        setAnimatingMessageIds(newIds)
        // Clear the animation flag after animation completes
        clearTimeoutRef.current = window.setTimeout(() => {
          setAnimatingMessageIds(new Set())
          clearTimeoutRef.current = null
        }, 900) // Slightly longer than animation duration
        timeoutRef.current = null
      }, 0)
      return () => {
        if (timeoutRef.current !== null) {
          clearTimeout(timeoutRef.current)
          timeoutRef.current = null
        }
        if (clearTimeoutRef.current !== null) {
          clearTimeout(clearTimeoutRef.current)
          clearTimeoutRef.current = null
        }
      }
    }

    // Update ref even if no new messages
    previousMessageIdsRef.current = currentMessageIds
  }, [organizedMessages])

  const createMessage = useCreateEventMessage()
  const updateMessage = useUpdateEventMessage()
  const deleteMessage = useDeleteEventMessage()
  const toggleReaction = useToggleEventMessageReaction()
  const uploadImage = useUploadEventMessageImage()

  // Helper function to handle reaction click
  const handleReactionClick = (
    messageId: number,
    reactionType: string,
    event: React.MouseEvent,
  ) => {
    event.stopPropagation()
    toggleReaction.mutate({
      event_message_id: messageId,
      reaction_type: reactionType,
      project_id: projectId,
      event_id: eventId, // Pass event_id for batch query cache update
    })
  }

  // Strip quoted portion from reply message body
  const stripQuotedPreview = (
    text: string,
  ): {
    cleaned: string
    offset: number
  } => {
    // Pattern: @username "quoted text..." \n actual reply
    // Match @mention followed by space, quote, quoted content, closing quote, optional space, and newline
    const mentionQuotePattern = /@[^"]+\s+"[^"]*"\s*\n/
    const match = text.match(mentionQuotePattern)
    const offset = match ? match.index! + match[0].length : 0
    const cleaned = text.replace(mentionQuotePattern, '').trim()
    const trimOffset =
      text.replace(mentionQuotePattern, '').length - cleaned.length
    return { cleaned, offset: offset - trimOffset }
  }

  const handleSendMessage = async () => {
    if (
      (!inputValue.trim() &&
        pendingImages.length === 0 &&
        inlineImages.length === 0) ||
      !user?.id ||
      createMessage.isPending
    )
      return

    // If replying, strip out the quoted preview portion
    let messageBody: string
    let positionOffset = 0
    if (replyingTo) {
      const result = stripQuotedPreview(inputValue)
      messageBody = result.cleaned
      positionOffset = result.offset
    } else {
      // Adjust image positions if messageBody was trimmed (positions are relative to inputValue)
      // Calculate the offset if the start was trimmed
      const trimStartOffset = inputValue.length - inputValue.trimStart().length
      positionOffset = trimStartOffset
      messageBody = inputValue.trim()
    }

    // Insert image placeholders for inline images at their positions
    // Sort inline images by position (descending) to insert from end to start
    const sortedInlineImages = [...inlineImages].sort(
      (a, b) => b.position - a.position,
    )
    sortedInlineImages.forEach((img, index) => {
      // Use a unique placeholder that won't conflict with user text
      // Format: [IMG:index] where index is the order of insertion
      const placeholder = `[IMG:${sortedInlineImages.length - 1 - index}]`
      // Adjust position for trimming/quote removal, but ensure we don't go negative
      const adjustedPosition = Math.max(0, img.position - positionOffset)

      // Check if there's a newline before the image position in the original inputValue
      // We need to preserve newlines that were added before images
      const originalPos = img.position
      const hasNewlineBefore =
        originalPos > 0 && inputValue[originalPos - 1] === '\n'

      // If there was a newline before the image, ensure it's preserved
      // Check if the newline is already in messageBody at adjustedPosition - 1
      const needsNewlineBeforePlaceholder =
        hasNewlineBefore &&
        (adjustedPosition === 0 || messageBody[adjustedPosition - 1] !== '\n')

      if (needsNewlineBeforePlaceholder) {
        // Insert newline before placeholder
        messageBody =
          messageBody.slice(0, adjustedPosition) +
          '\n' +
          placeholder +
          messageBody.slice(adjustedPosition)
      } else {
        // Insert placeholder at position (newline should already be there)
        messageBody =
          messageBody.slice(0, adjustedPosition) +
          placeholder +
          messageBody.slice(adjustedPosition)
      }
    })

    // Append placeholders for pending images (uploaded via Dropzone) at the end
    // These come after inline images in the upload order
    if (pendingImages.length > 0) {
      const pendingPlaceholders = pendingImages
        .map((_, index) => `[IMG:${sortedInlineImages.length + index}]`)
        .join('\n')
      // Add newline before pending images if message body has content
      if (messageBody.trim()) {
        messageBody = messageBody + '\n' + pendingPlaceholders
      } else {
        messageBody = pendingPlaceholders
      }
    }

    // Don't send if only quoted portion remains and no images
    if (!messageBody && pendingImages.length === 0 && inlineImages.length === 0)
      return

    // Create message first
    // When replying to a private message, always use private; otherwise use saved preference
    const messagePrivacy = isReplyingToPrivateMessage
      ? true
      : savedVisibilityPreference
    createMessage.mutate(
      {
        event_id: eventId,
        body: messageBody || ' ',
        parent_message_id: replyingTo,
        project_id: projectId,
        private: messagePrivacy,
      },
      {
        onSuccess: async (newMessage) => {
          // Upload inline images in order (sorted by position)
          const sortedInlineImagesForUpload = [...inlineImages].sort(
            (a, b) => a.position - b.position,
          )

          // Upload all images in order: first inline images (by position), then pending images
          const allImages = [
            ...sortedInlineImagesForUpload.map((img) => ({
              file: img.file,
              isInline: true,
            })),
            ...pendingImages.map((file) => ({
              file,
              isInline: false,
            })),
          ]

          if (allImages.length > 0) {
            try {
              // Upload sequentially to maintain order
              for (const { file } of allImages) {
                await uploadImage.mutateAsync({
                  eventId,
                  eventMessageId: newMessage.event_message_id,
                  file,
                  projectId,
                })
              }
            } catch (error) {
              console.error('Failed to upload images:', error)
            }
          }

          // Clean up inline image previews
          inlineImages.forEach((img) => {
            URL.revokeObjectURL(img.preview)
          })

          setInputValue('')
          setPendingImages([])
          setInlineImages([])
          setReplyingTo(null)
          // Clear draft from localStorage
          localStorage.removeItem(draftKey)
        },
      },
    )
  }

  const handleEditClick = (messageId: number) => {
    const message = organizedMessages.find(
      (m) => m.event_message_id === messageId,
    )
    if (message) {
      setEditingMessageId(messageId)
      setEditMessageValue(message.body)
      // Clear any existing edit inline images (revoke preview URLs for new images)
      editInlineImages.forEach((img) => {
        if (img.file) {
          // Only revoke if it's a new image (has file)
          URL.revokeObjectURL(img.preview)
        }
      })
      setEditInlineImages([])
    }
  }

  // Fetch images for the message being edited
  const { data: editMessageImages } = useGetEventMessageImages({
    queryParams: {
      eventId,
      eventMessageId: editingMessageId || 0,
      projectId,
    },
    queryOptions: {
      enabled: !!editingMessageId,
    },
  })

  // Parse existing image placeholders and create editInlineImages entries
  useEffect(() => {
    if (
      !editingMessageId ||
      !editMessageValue ||
      !editMessageImages ||
      !Array.isArray(editMessageImages) ||
      editInlineImages.length > 0
    )
      return

    // Parse image placeholders from editMessageValue
    const imagePlaceholderRegex = /\[IMG:(\d+)\]/g
    const existingImages: Array<{
      id: string
      position: number
      preview: string
      imageId?: string
      placeholderIndex?: number
    }> = []
    const placeholderMatches: Array<{
      match: string
      index: number
      imageIndex: number
    }> = []

    let match: RegExpExecArray | null
    imagePlaceholderRegex.lastIndex = 0

    while ((match = imagePlaceholderRegex.exec(editMessageValue)) !== null) {
      const imageIndex = parseInt(match[1], 10)
      const placeholderPosition = match.index
      const placeholderText = match[0]
      const imagesArray = editMessageImages as Array<{
        event_message_image_id: string
        presigned_url: string
      }>
      const image = imagesArray[imageIndex]

      if (image) {
        existingImages.push({
          id: `existing-${image.event_message_image_id}`,
          position: placeholderPosition,
          preview: image.presigned_url,
          imageId: image.event_message_image_id,
          placeholderIndex: imageIndex, // Store original placeholder index
        })
        placeholderMatches.push({
          match: placeholderText,
          index: placeholderPosition,
          imageIndex,
        })
      }
    }

    // Remove placeholders from editMessageValue and adjust positions
    if (placeholderMatches.length > 0) {
      // Remove placeholders and adjust positions
      const adjustedImages = existingImages.map((img) => {
        // Count how many placeholder characters were removed before this image
        let removedBefore = 0
        for (const pm of placeholderMatches) {
          if (pm.index < img.position) {
            removedBefore += pm.match.length
          }
        }
        return {
          ...img,
          position: img.position - removedBefore,
        }
      })

      // Remove all placeholders from the text
      const cleanedValue = editMessageValue.replace(/\[IMG:\d+\]/g, '')

      // Set cleaned value and adjusted images (defer to avoid cascading renders)
      setTimeout(() => {
        setEditMessageValue(cleanedValue)
        setEditInlineImages(adjustedImages)
      }, 0)
    } else {
      // No images found, but still set empty array to mark as processed
      setTimeout(() => {
        setEditInlineImages([])
      }, 0)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingMessageId, editMessageValue, editMessageImages])

  const handleCancelEdit = () => {
    // Clean up edit inline image previews
    editInlineImages.forEach((img) => {
      URL.revokeObjectURL(img.preview)
    })
    setEditInlineImages([])
    setEditingMessageId(null)
    setEditMessageValue('')
  }

  const handleUpdateMessage = () => {
    if (
      !editingMessageId ||
      (!editMessageValue.trim() && editInlineImages.length === 0) ||
      updateMessage.isPending
    )
      return

    const message = organizedMessages.find(
      (m) => m.event_message_id === editingMessageId,
    )
    if (!message) return

    // Renumber placeholders sequentially (0, 1, 2...) based on the order they appear in the message
    // This ensures that when images are deleted, the remaining images are renumbered correctly
    let messageBody = editMessageValue.trim()
    const sortedEditInlineImages = [...editInlineImages].sort(
      (a, b) => a.position - b.position, // Sort by position (ascending) to get order in message
    )

    // Insert placeholders sequentially starting from 0
    // Insert from right to left (descending position) to avoid position shifts
    let placeholderIndex = 0
    const placeholders: Array<{ position: number; placeholder: string }> = []
    sortedEditInlineImages.forEach((img) => {
      placeholders.push({
        position: img.position,
        placeholder: `[IMG:${placeholderIndex}]`,
      })
      placeholderIndex++
    })

    // Insert placeholders from right to left
    placeholders
      .sort((a, b) => b.position - a.position)
      .forEach(({ position, placeholder }) => {
        messageBody =
          messageBody.slice(0, position) +
          placeholder +
          messageBody.slice(position)
      })

    // Collect image IDs in the same order as placeholders (for existing images only)
    const imageIds: string[] = []
    sortedEditInlineImages.forEach((img) => {
      if (img.imageId) {
        // Only include existing images (those with imageId)
        imageIds.push(img.imageId)
      }
    })

    updateMessage.mutate(
      {
        event_message_id: editingMessageId,
        body: messageBody || ' ',
        project_id: projectId,
        // Always send image_ids array (empty array means delete all existing images)
        image_ids: imageIds,
      },
      {
        onSuccess: async () => {
          // Upload only new edit inline images (those with file property)
          const newImages = editInlineImages.filter((img) => img.file)
          if (newImages.length > 0) {
            try {
              const sortedNewImagesForUpload = [...newImages].sort(
                (a, b) => a.position - b.position,
              )

              for (const img of sortedNewImagesForUpload) {
                if (img.file) {
                  await uploadImage.mutateAsync({
                    eventId: message.event_id,
                    eventMessageId: editingMessageId,
                    file: img.file,
                    projectId,
                  })
                }
              }
            } catch (error) {
              console.error('Failed to upload edit images:', error)
            }
          }

          // Clean up edit inline image previews (only for new images)
          editInlineImages.forEach((img) => {
            if (img.file) {
              // Only revoke if it's a new image (has file)
              URL.revokeObjectURL(img.preview)
            }
          })
          setEditInlineImages([])
          setEditingMessageId(null)
          setEditMessageValue('')
        },
      },
    )
  }

  const handleDeleteClick = (messageId: number) => {
    const message = organizedMessages.find(
      (m) => m.event_message_id === messageId,
    )
    if (!message || deleteMessage.isPending) return

    deleteMessage.mutate({
      event_message_id: messageId,
      event_id: message.event_id,
      project_id: projectId,
    })
  }

  const handleReplyClick = useCallback(
    (messageId: number, parentUserName: string, messageBody: string) => {
      // Save current draft before starting reply (so we can restore it on cancel)
      if (inputValue.trim()) {
        localStorage.setItem(draftKey, inputValue)
      }
      setReplyingTo(messageId)
      // Extract short portion of message (first 80 chars, or until newline)
      const previewLength = 80
      const firstLine = messageBody.split('\n')[0]
      const hasMoreLines = messageBody.includes('\n')
      const isLonger = firstLine.length > previewLength
      const messagePreview = firstLine.substring(0, previewLength).trim()
      const ellipsis = hasMoreLines || isLonger ? '...' : ''
      // Pre-fill input with @mention and message preview, then move to next line
      const replyText = `@${parentUserName} "${messagePreview}${ellipsis}" \n`
      setInputValue(replyText)
      // Cursor position will be set by the useEffect in MessageInput component
      // which handles focusing and scrolling when replyingTo changes
    },
    [inputValue, draftKey],
  )

  const handleCancelReply = useCallback(() => {
    setReplyingTo(null)
    setInputValue('')
  }, [])

  // Common emojis for picker
  const commonEmojis = [
    '😀',
    '😃',
    '😄',
    '😁',
    '😅',
    '😆',
    '😊',
    '😇',
    '🙂',
    '🙃',
    '😉',
    '😌',
    '😍',
    '🥰',
    '😘',
    '😗',
    '😙',
    '😚',
    '😋',
    '😛',
    '😝',
    '😜',
    '🤪',
    '🤨',
    '🧐',
    '🤓',
    '😎',
    '🤩',
    '🥳',
    '😏',
    '😒',
    '😞',
    '😔',
    '😟',
    '😕',
    '🙁',
    '☹️',
    '😣',
    '😖',
    '😫',
    '😩',
    '🥺',
    '😢',
    '😭',
    '😤',
    '😠',
    '😡',
    '🤬',
    '🤯',
    '😳',
    '🥵',
    '🥶',
    '😱',
    '😨',
    '😰',
    '😥',
    '😓',
    '🤗',
    '🤔',
    '🤭',
    '🤫',
    '🤥',
    '😶',
    '😐',
    '😑',
    '😬',
    '🙄',
    '😯',
    '😦',
    '😧',
    '😮',
    '😲',
    '🥱',
    '😴',
    '🤤',
    '😪',
    '😵',
    '🤐',
    '🥴',
    '🤢',
    '👍',
    '👎',
    '👌',
    '✌️',
    '🤞',
    '🤟',
    '🤘',
    '🤙',
    '👏',
    '🙌',
    '👐',
    '🤲',
    '🤝',
    '🙏',
    '✍️',
    '💪',
    '🦾',
    '🦿',
    '🦵',
    '🦶',
    '❤️',
    '🧡',
    '💛',
    '💚',
    '💙',
    '💜',
    '🖤',
    '🤍',
    '🤎',
    '💔',
    '❤️‍🔥',
    '❤️‍🩹',
    '💕',
    '💞',
    '💓',
    '💗',
    '💖',
    '💘',
    '💝',
    '💟',
    '✅',
    '❌',
    '⭕',
    '❎',
    '💯',
    '🔴',
    '🟠',
    '🟡',
    '🟢',
    '🔵',
    '🟣',
    '⚫',
    '⚪',
    '🟤',
    '🔥',
    '💥',
    '💢',
    '💫',
    '⭐',
    '🌟',
    '✨',
    '💫',
    '💨',
    '💦',
    '💧',
    '🎉',
    '🎊',
    '🎈',
    '🎁',
    '🏆',
    '🥇',
    '🥈',
    '🥉',
    '🎖️',
    '⭐',
    '💎',
    '👑',
    '🎯',
    '🎪',
    '🎬',
    '🎨',
    '🎭',
    '🎤',
    '🎧',
    '🎼',
    '🎹',
    '🥁',
    '🎷',
    '🎺',
    '🎸',
    '🎻',
    '🎲',
    '🎯',
    '🎮',
    '🎰',
    '🚀',
    '✈️',
    '🛫',
    '🛬',
    '🛸',
    '💺',
    '🚁',
    '🚂',
    '🚃',
    '🚄',
    '🚅',
    '🚆',
    '🚇',
    '🚈',
    '🚉',
    '🚊',
    '🚝',
    '🚞',
    '🚟',
    '🚠',
    '🚡',
    '⛵',
    '🚤',
    '🛥️',
    '🛳️',
    '⛴️',
    '🚢',
    '⚓',
    '⛽',
    '🚧',
    '🚦',
    '🚥',
    '🗺️',
    '🗿',
    '🗽',
    '🗼',
    '🏰',
    '🏯',
    '🏟️',
    '🎡',
    '🎢',
    '🎠',
    '⛲',
    '⛱️',
    '🏖️',
    '🏝️',
    '🏜️',
    '🌋',
    '⛰️',
    '🏔️',
    '🗻',
    '🏕️',
    '⛺',
    '🏠',
    '🏡',
    '🏘️',
    '🏚️',
    '🏗️',
    '🏭',
    '🏢',
    '🏬',
    '🏣',
    '🏤',
    '🏥',
    '🏦',
    '🏨',
    '🏪',
    '🏫',
    '🏩',
    '💒',
    '🏛️',
    '⛪',
    '🕌',
    '🕍',
    '🕋',
    '⛩️',
    '🛤️',
    '🛣️',
    '🗾',
    '🎑',
    '🏞️',
    '🌅',
    '🌄',
    '🌠',
    '🎇',
    '🎆',
    '🌇',
    '🌆',
    '🏙️',
    '🌃',
    '🌌',
    '🌉',
    '🌁',
    '🌐',
    '🌏',
    '🌍',
    '🌎',
    '🌑',
    '🌒',
    '🌓',
    '🌔',
    '🌕',
    '🌖',
    '🌗',
    '🌘',
    '🌙',
    '🌚',
    '🌛',
    '🌜',
    '🌡️',
    '☀️',
    '🌝',
    '🌞',
    '⭐',
    '🌟',
    '💫',
    '✨',
    '⚡',
    '☄️',
    '💥',
    '🔥',
    '🌪️',
    '🌈',
    '☂️',
    '☔',
    '⚡',
    '❄️',
    '☃️',
    '⛄',
    '🌊',
    '💧',
    '💦',
    '☔',
    '☂️',
    '🌂',
  ]

  const borderColor =
    colorScheme === 'dark' ? theme.colors.dark[4] : theme.colors.gray[3]

  // Create refs map for messages to enable scrolling
  const messageRefsMap = useRef<Map<number, HTMLDivElement>>(new Map())

  // Function to set a message ref
  const setMessageRef = useCallback(
    (messageId: number, element: HTMLDivElement | null) => {
      if (element) {
        messageRefsMap.current.set(messageId, element)
      } else {
        messageRefsMap.current.delete(messageId)
      }
    },
    [],
  )

  // Function to scroll to a message
  const handleScrollToMessage = useCallback((messageId: number) => {
    const element = messageRefsMap.current.get(messageId)
    if (element) {
      element.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
    }
  }, [])

  return (
    <>
      <style>{`
        @keyframes slideInFade {
          from {
            opacity: 0;
            transform: translateY(-10px) scale(0.95);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        .message-animate-in {
          animation: slideInFade 1.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
      `}</style>
      <Stack
        gap={0}
        h="100%"
        style={{ display: 'flex', flexDirection: 'column' }}
      >
        <MessageInput
          eventId={eventId}
          projectId={projectId}
          replyingTo={replyingTo}
          inputValue={inputValue}
          setInputValue={setInputValue}
          cursorPosition={cursorPosition}
          setCursorPosition={setCursorPosition}
          inlineImages={inlineImages}
          setInlineImages={setInlineImages}
          pendingImages={pendingImages}
          setPendingImages={setPendingImages}
          onSendMessage={handleSendMessage}
          onCancelReply={handleCancelReply}
          isPending={createMessage.isPending}
          savedVisibilityPreference={savedVisibilityPreference}
          setSavedVisibilityPreference={setSavedVisibilityPreference}
          isReplyingToPrivateMessage={isReplyingToPrivateMessage}
          draftKey={draftKey}
          commonEmojis={commonEmojis}
        />

        {/* Comments Header */}
        <Group
          justify="space-between"
          p="md"
          style={{ borderBottom: `1px solid ${borderColor}` }}
        >
          <Group gap="xs">
            <Text size="lg" fw={600}>
              Comments
            </Text>
            {organizedMessages && organizedMessages.length > 0 && (
              <Badge size="lg" variant="filled" color="orange">
                {organizedMessages.length}
              </Badge>
            )}
          </Group>
          <Group gap="xs">
            <MuteToggle eventId={eventId} projectId={projectId} />
            <Select
              value={sortOrder}
              onChange={(value) =>
                setSortOrder(value as 'most_recent' | 'oldest')
              }
              data={[
                { value: 'most_recent', label: 'Most recent' },
                { value: 'oldest', label: 'Oldest first' },
              ]}
              rightSection={<IconChevronDown size={16} />}
              size="sm"
              style={{ width: 150 }}
            />
          </Group>
        </Group>

        <MessageList
          messages={organizedMessages}
          isLoading={isInitialLoad}
          eventId={eventId}
          projectId={projectId}
          userIdToName={userIdToName}
          userIdToImageUrl={userIdToImageUrl}
          currentUserId={user?.id}
          isCurrentUser={isCurrentUser}
          getUserInitials={getUserInitials}
          formatTimestamp={formatTimestamp}
          formatEditedTimestamp={formatEditedTimestamp}
          hoveredMessageId={hoveredMessageId}
          setHoveredMessageId={setHoveredMessageId}
          editingMessageId={editingMessageId}
          onScrollToMessage={handleScrollToMessage}
          setMessageRef={setMessageRef}
          editMessageValue={editMessageValue}
          setEditMessageValue={setEditMessageValue}
          editInlineImages={editInlineImages}
          setEditInlineImages={setEditInlineImages}
          handleUpdateMessage={handleUpdateMessage}
          handleCancelEdit={handleCancelEdit}
          updateMessagePending={updateMessage.isPending}
          addReactionMessageId={addReactionMessageId}
          setAddReactionMessageId={setAddReactionMessageId}
          reactionsByMessageId={reactionsByMessageId}
          handleReactionClick={handleReactionClick}
          handleReplyClick={handleReplyClick}
          handleEditClick={handleEditClick}
          handleDeleteClick={handleDeleteClick}
          emojiReactions={emojiReactions}
          colorScheme={colorScheme}
          theme={theme}
          borderColor={borderColor}
          animatingMessageIds={animatingMessageIds}
          commonEmojis={commonEmojis}
          emojiPickerOpen={emojiPickerOpen}
          setEmojiPickerOpen={setEmojiPickerOpen}
          user={
            user
              ? {
                  id: user.id,
                  hasImage: user.hasImage,
                  imageUrl: user.imageUrl,
                }
              : undefined
          }
        />
      </Stack>
    </>
  )
}
