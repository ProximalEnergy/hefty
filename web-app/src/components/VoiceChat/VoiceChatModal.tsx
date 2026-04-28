import {
  useCreateVoiceChatSession,
  useEnsureVectorStore,
} from '@/api/v1/ai/voice-chat'
import { baseURL } from '@/urlConfig'
import { useAuth, useUser } from '@clerk/react'
import {
  ActionIcon,
  Badge,
  Box,
  Group,
  Image,
  Modal,
  Paper,
  Stack,
  Text,
  Tooltip,
  useMantineTheme,
} from '@mantine/core'
import type { RealtimeSession } from '@openai/agents-realtime'
import { tool } from '@openai/agents-realtime'
import {
  IconChevronDown,
  IconChevronUp,
  IconMicrophone,
  IconMicrophoneOff,
  IconPhone,
  IconPhoneOff,
  IconVolume,
  IconVolumeOff,
} from '@tabler/icons-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { z } from 'zod'

interface ContractData {
  contract_id: number
  project_id: string
  document_id?: string | null
  name_long?: string | null
  name_short?: string | null
  category_name_long?: string | null
  execution_date?: string | null
  contract_summary?: string | null
  openai_vector_store_id?: string | null
  vector_store_id?: string | null
  openai_file_id?: string | null
}

interface ContractSearchResult {
  text?: string | null
  score?: number | string | null
  [key: string]: unknown
}

type VoiceChatSession = RealtimeSession & {
  mute?: (shouldMute: boolean) => void
  disconnect?: () => Promise<void> | void
  close?: () => Promise<void> | void
  end?: () => Promise<void> | void
  stop?: () => Promise<void> | void
  connection?: { close?: () => void }
}

interface VoiceChatModalProps {
  opened: boolean
  onClose: () => void
  contractData?: ContractData
}

const VoiceChatModal = ({
  opened,
  onClose,
  contractData,
}: VoiceChatModalProps) => {
  const theme = useMantineTheme()

  const { getToken } = useAuth()
  const { user } = useUser()
  const createVoiceChatSession = useCreateVoiceChatSession()
  const ensureVectorStore = useEnsureVectorStore()

  const [isConnected, setIsConnected] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(true)
  const [isCalling, setIsCalling] = useState(false)
  const [isGatheringDocument, setIsGatheringDocument] = useState(true)
  const [isDisconnected, setIsDisconnected] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [aiResponse, setAiResponse] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [session, setSession] = useState<VoiceChatSession | null>(null)
  const [contractSearchResults, setContractSearchResults] = useState<
    ContractSearchResult[]
  >([])
  const [showContractReferences, setShowContractReferences] = useState(false)
  const [expandedExcerpts, setExpandedExcerpts] = useState<Set<number>>(
    new Set(),
  )
  const [cachedVectorStoreId, setCachedVectorStoreId] = useState<string | null>(
    null,
  )
  const vectorStoreIdRef = useRef<string | null>(null)
  const ensureVectorStoreInFlightRef = useRef<Promise<string | null> | null>(
    null,
  )

  // Reset cache when the contract changes to avoid stale vector store reuse
  useEffect(() => {
    const incomingId =
      contractData?.openai_vector_store_id ??
      contractData?.vector_store_id ??
      null

    // Clear any in-flight ensure from previous contract
    ensureVectorStoreInFlightRef.current = null

    // Reset cached ids for the new contract
    vectorStoreIdRef.current = incomingId
    setCachedVectorStoreId(incomingId)
  }, [
    contractData?.contract_id,
    contractData?.document_id,
    contractData?.openai_file_id,
    contractData?.openai_vector_store_id,
    contractData?.vector_store_id,
  ])

  const transcriptRef = useRef<HTMLDivElement>(null)
  const tokenCacheRef = useRef<{ token: string; expires: number } | null>(null)

  const getCachedToken = async (): Promise<string> => {
    // Always get a fresh token to avoid expiration issues
    const token = await getToken({ template: 'default', skipCache: true })
    if (!token) {
      throw new Error('Failed to get authentication token')
    }

    return token
  }

  const resolveVectorStoreId = useCallback(async (): Promise<string | null> => {
    if (vectorStoreIdRef.current) return vectorStoreIdRef.current
    if (ensureVectorStoreInFlightRef.current) {
      return ensureVectorStoreInFlightRef.current
    }

    const existing =
      cachedVectorStoreId ??
      contractData?.openai_vector_store_id ??
      contractData?.vector_store_id ??
      null
    if (existing) {
      vectorStoreIdRef.current = existing
      setCachedVectorStoreId((prev) => prev ?? existing)
      return existing
    }

    if (!contractData?.openai_file_id) return null

    const promise = ensureVectorStore
      .mutateAsync({
        openai_file_id: contractData.openai_file_id,
        name: 'aria-knowledge',
      })
      .then((vs) => {
        const id = vs.vector_store_id ?? null
        vectorStoreIdRef.current = id
        setCachedVectorStoreId(id)
        ensureVectorStoreInFlightRef.current = null
        return id
      })
      .catch((err) => {
        ensureVectorStoreInFlightRef.current = null
        throw err
      })

    ensureVectorStoreInFlightRef.current = promise
    return promise
  }, [
    cachedVectorStoreId,
    contractData?.openai_file_id,
    contractData?.openai_vector_store_id,
    contractData?.vector_store_id,
    ensureVectorStore,
  ])

  const createPreview = (text: string, maxLength: number = 200): string => {
    const normalizedText = text.replace(/\n{2,}/g, '\n').trim()
    if (normalizedText.length <= maxLength) return normalizedText

    // Find the last complete sentence within the limit
    const truncated = normalizedText.substring(0, maxLength)
    const lastSentenceEnd = Math.max(
      truncated.lastIndexOf('.'),
      truncated.lastIndexOf('!'),
      truncated.lastIndexOf('?'),
    )

    if (lastSentenceEnd > maxLength * 0.5) {
      return truncated.substring(0, lastSentenceEnd + 1)
    }

    return truncated + '...'
  }

  const toggleExcerptExpansion = (index: number) => {
    setExpandedExcerpts((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(index)) {
        newSet.delete(index)
      } else {
        newSet.add(index)
      }
      return newSet
    })
  }

  const isContractSearchResultArray = (
    value: unknown,
  ): value is ContractSearchResult[] =>
    Array.isArray(value) &&
    value.every((item) => item !== null && typeof item === 'object')

  const searchContractContent = async (
    query: string,
  ): Promise<ContractSearchResult[]> => {
    if (!contractData?.document_id) {
      return []
    }

    // Resolve or create the vector store ID once
    let vectorStoreId: string | null = null
    try {
      vectorStoreId = await resolveVectorStoreId()
    } catch (e) {
      console.error('Failed to resolve vector store:', e)
      return []
    }

    if (!vectorStoreId) {
      return []
    }

    // Create an AbortController for timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 second timeout

    try {
      const token = await getCachedToken()
      const url =
        `${baseURL}/v1/operational/projects/${contractData.project_id}` +
        `/documents/search-contract/${contractData.document_id}` +
        `?query=${encodeURIComponent(query)}` +
        `&vector_store_id=${encodeURIComponent(vectorStoreId)}`

      // Show contract references panel when making the search request
      setShowContractReferences(true)

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (response.ok) {
        const data: unknown = await response.json()

        if (
          typeof data === 'object' &&
          data !== null &&
          'search_results' in data
        ) {
          const { search_results: searchResults } = data as {
            search_results?: unknown
          }
          if (isContractSearchResultArray(searchResults)) {
            return searchResults
          }
        }

        // Handle empty results
        return []
      } else if (response.status === 401) {
        // Force a completely fresh token from Clerk
        const newToken = await getToken({
          template: 'default',
          skipCache: true,
        })

        if (newToken) {
          // Create a new AbortController for the retry to avoid conflicts
          const retryController = new AbortController()
          const retryTimeoutId = setTimeout(
            () => retryController.abort(),
            30000,
          ) // 30 second timeout for retry

          try {
            const retryResponse = await fetch(url, {
              method: 'POST',
              headers: {
                Authorization: `Bearer ${newToken}`,
              },
              signal: retryController.signal,
            })

            clearTimeout(retryTimeoutId)

            if (retryResponse.ok) {
              const retryData: unknown = await retryResponse.json()
              if (
                typeof retryData === 'object' &&
                retryData !== null &&
                'search_results' in retryData
              ) {
                const { search_results: retryResults } = retryData as {
                  search_results?: unknown
                }
                if (isContractSearchResultArray(retryResults)) {
                  return retryResults
                }
              }
            }
          } catch (retryError) {
            clearTimeout(retryTimeoutId)
            if (
              retryError instanceof Error &&
              retryError.name === 'AbortError'
            ) {
              console.error(
                '❌ Contract search retry timed out after 30 seconds:',
                retryError,
              )
            } else {
              console.error('❌ Failed to retry contract search:', retryError)
            }
          }
        }
        return []
      } else {
        const errorText = await response.text()
        console.error(
          '❌ Failed to search contract:',
          response.status,
          response.statusText,
          errorText,
        )
        return []
      }
    } catch (error) {
      // Ensure timeout is cleared in all error paths
      clearTimeout(timeoutId)

      if (error instanceof Error && error.name === 'AbortError') {
        console.error('❌ Contract search timed out after 30 seconds:', error)
      } else {
        console.error('❌ Failed to search contract:', error)
      }
      return []
    }
  }

  // Define the contract search tool using the correct format for RealtimeAgent
  const searchContractTool = tool({
    name: 'search_contract',
    description: [
      'Search for relevant information in the contract document.',
      'Use this tool when users ask questions about contract terms, clauses,',
      'obligations, or any contract details.',
    ].join(' '),
    parameters: z.object({
      query: z
        .string()
        .describe('The search query to find relevant contract information'),
    }),
    execute: async ({ query }: { query: string }) => {
      try {
        const searchResults = await searchContractContent(query)

        if (searchResults && Array.isArray(searchResults)) {
          // Update the UI with search results
          setContractSearchResults(searchResults)
          setExpandedExcerpts(new Set()) // Reset expanded state for new results

          // Show the contract references panel with animation
          setShowContractReferences(true)

          // Return formatted results for the agent
          return JSON.stringify({
            success: true,
            query,
            results: searchResults,
            message: `Found relevant contract information for: ${query}`,
          })
        } else {
          return JSON.stringify({
            success: false,
            query,
            results: '',
            message: `No relevant information found for: ${query}`,
          })
        }
      } catch (error) {
        console.error('❌ Tool execution error:', error)
        return JSON.stringify({
          success: false,
          query,
          results: '',
          message: `Error searching contract: ${error}`,
        })
      }
    },
  })

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
    }
  }, [transcript])

  const initializeVoiceChat = useCallback(async () => {
    try {
      // Dynamically import the OpenAI Agents SDK
      const { RealtimeAgent, RealtimeSession } =
        await import('@openai/agents-realtime')

      const contractType = contractData?.category_name_long || 'Unknown'
      const counterpartyName = contractData?.name_long || 'Unknown'
      const executionDate = contractData?.execution_date || 'Unknown'
      const contractSummary = contractData?.contract_summary || 'Unknown'
      const greetingName = user?.firstName || 'there'
      const greetingCounterparty = contractData?.name_long || 'the counterparty'

      const contractContext = contractData
        ? [
            'You are Aria, a helpful AI assistant with expertise in contract analysis.',
            'You also focus on energy project management.',
            '',
            'You are helping a user understand a contract with the following details:',
            `- Contract Type: ${contractType}`,
            `- Counterparty: ${counterpartyName}`,
            `- Execution Date: ${executionDate}`,
            `- Contract Summary: ${contractSummary}`,
            '',
            'IMPORTANT: Greet the user by name and invite contract questions.',
            [
              'Say:',
              `"Hi ${greetingName},`,
              `how can I help you with this ${greetingCounterparty} contract?"`,
            ].join(' '),
            '',
            'Use the search_contract tool to find information inside the document.',
            'Run it whenever users ask about contract terms, clauses, or obligations.',
            'Launch the search first so you can cite referenced excerpts.',
            '',
            'Your role is to:',
            '1. Greet the user by name and prompt them for contract questions.',
            "2. After each question, say you're searching the document.",
            '   Immediately start the search_contract tool.',
            '3. Answer with the concise result first, then add a brief explanation.',
            '4. Explain technical language and legal concepts in plain words.',
            '',
            'Always use the search_contract tool for specific contract details.',
            'Speak quickly and professionally like an experienced attorney.',
            'Keep answers short.',
          ].join('\n')
        : [
            'You are Aria, a helpful AI assistant with expertise in contract analysis.',
            'However, you cannot access the contract, so you do not know its details.',
            'Tell the user that something must have gone wrong.',
          ].join('\n')

      try {
        await resolveVectorStoreId()
      } catch (e) {
        console.error('Failed ensuring vector store:', e)
      }

      const newAgent = new RealtimeAgent({
        name: 'Aria',
        voice: 'sage',
        instructions: contractContext,
        tools: [searchContractTool],
      })

      const newSession = new RealtimeSession(newAgent, {
        model: 'gpt-realtime',
      })

      setSession(newSession as VoiceChatSession)
    } catch (err) {
      console.error('Failed to initialize voice chat:', err)
      setError('Failed to initialize voice chat. Please try again.')
    }
  }, [contractData, user, searchContractTool, resolveVectorStoreId])

  useEffect(() => {
    if (opened && !session) {
      // Simulate document gathering time
      const timer = setTimeout(() => {
        setIsGatheringDocument(false)
        initializeVoiceChat()
      }, 2000) // 2 second delay

      return () => clearTimeout(timer)
    }
  }, [opened, session, initializeVoiceChat])

  const connectToSession = useCallback(async () => {
    if (!session) return

    try {
      setIsCalling(true)
      setIsDisconnected(false)
      setError(null)

      // Get client secret from backend
      const response = await createVoiceChatSession.mutateAsync({
        model: 'gpt-realtime',
      })
      const clientSecret = response.client_secret

      await session.connect({ apiKey: clientSecret })

      setIsConnected(true)
      setIsCalling(false)
      setError(null)

      // Start listening by default when connected (unless muted)
      if (!isListening) {
        setIsListening(true)

        // Use the mute method to unmute (start listening)
        if (typeof session.mute === 'function') {
          session.mute(false) // false = unmute (start listening)
        } else {
          console.error('❌ No mute method found on session during connect')
        }
      }
    } catch (err) {
      console.error('Failed to connect to session:', err)
      setIsCalling(false)
      setError(
        'Failed to connect to voice chat. Please check your connection and try again.',
      )
    }
  }, [session, createVoiceChatSession, isListening])

  // Auto-connect when session is ready
  useEffect(() => {
    if (
      session &&
      !isGatheringDocument &&
      !isConnected &&
      !isCalling &&
      !isDisconnected
    ) {
      connectToSession()
    }
  }, [
    session,
    isGatheringDocument,
    isConnected,
    isCalling,
    isDisconnected,
    connectToSession,
  ])

  const disconnectFromSession = useCallback(async () => {
    if (!session) return

    try {
      // Stop listening first
      if (typeof session.mute === 'function') {
        session.mute(true) // true = mute (stop listening)
      } else {
        console.error('❌ No mute method found on session during disconnect')
      }

      // Then disconnect
      if (typeof session.disconnect === 'function') {
        await session.disconnect()
      } else if (typeof session.close === 'function') {
        await session.close()
      } else if (typeof session.end === 'function') {
        await session.end()
      } else if (typeof session.stop === 'function') {
        await session.stop()
      } else if (
        session.connection &&
        typeof session.connection.close === 'function'
      ) {
        session.connection.close()
      }
    } catch (err) {
      console.error('Failed to disconnect:', err)
    } finally {
      setIsConnected(false)
      setIsListening(false)
      setIsSpeaking(false)
      setIsCalling(false)
      setIsDisconnected(true)
      setTranscript('')
      setAiResponse('')
      setContractSearchResults([])
      setShowContractReferences(false)
      setExpandedExcerpts(new Set())
      tokenCacheRef.current = null // Clear token cache
      // Don't clear the session - keep it for reconnection
    }
  }, [session])

  const toggleListening = () => {
    if (!isConnected || !session) return

    try {
      if (isListening) {
        // Stop listening (mute)
        setIsListening(false)

        // Use the mute method to mute (stop listening)
        if (typeof session.mute === 'function') {
          session.mute(true) // true = mute (stop listening)
        } else {
          console.error('❌ No mute method found on session')
        }
      } else {
        // Start listening (unmute)
        setIsListening(true)

        // Use the mute method to unmute (start listening)
        if (typeof session.mute === 'function') {
          session.mute(false) // false = unmute (start listening)
        } else {
          console.error('❌ No mute method found on session')
        }
      }
    } catch (err) {
      console.error('Failed to toggle listening:', err)
    }
  }

  const toggleAudio = () => {
    // Toggle audio output
    setIsSpeaking(!isSpeaking)
  }

  const handleReconnect = async () => {
    setIsDisconnected(false) // Reset disconnected state
    if (!session) {
      // If no session exists, reinitialize
      await initializeVoiceChat()
    } else {
      // Reconnect to existing session (which should have the vector store setup)
      await connectToSession()
    }

    // Turn speaker back on after reconnecting
    setIsSpeaking(true)
  }

  const handleVoiceChatModalClose = () => {
    disconnectFromSession()
    setSession(null) // Clear session when modal is closed
    onClose()
  }

  useEffect(() => {
    return () => {
      if (session) {
        disconnectFromSession()
      }
    }
  }, [session, disconnectFromSession])

  return (
    <>
      <style>
        {`
          @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
          }

          @keyframes slideInFromRight {
            0% {
              transform: translateX(100%);
              opacity: 0;
            }
            100% {
              transform: translateX(0);
              opacity: 1;
            }
          }

          .contract-references-panel {
            animation: slideInFromRight 0.5s ease-out;
          }
        `}
      </style>
      <Modal
        opened={opened}
        onClose={handleVoiceChatModalClose}
        title={
          <Group gap="sm">
            <Text fw={600}>Contract Chat</Text>
            {isConnected && (
              <Badge color="green" variant="light" size="sm">
                Connected
              </Badge>
            )}
          </Group>
        }
        size={showContractReferences ? 'xl' : 'sm'}
        styles={{
          title: { flex: 1 },
        }}
      >
        <Box style={{ display: 'flex', gap: '16px' }}>
          <Box
            style={{
              width: showContractReferences ? '50%' : '100%',
              flexShrink: 0,
            }}
          >
            <Paper
              p={0}
              withBorder
              style={{ position: 'relative', overflow: 'hidden' }}
            >
              {/* Aria's Image */}
              <Image
                src="/Aria_CallScreen.png"
                alt="Aria"
                style={{ width: '100%', height: '400px', objectFit: 'cover' }}
              />

              {/* Overlay Content */}
              <Box
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: [
                    'linear-gradient(to bottom, rgba(0,0,0,0.3) 0%,',
                    'rgba(0,0,0,0.7) 100%)',
                  ].join(' '),
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  padding: '20px',
                }}
              >
                {/* Top Status */}
                <Box style={{ textAlign: 'center', marginTop: '20px' }}>
                  {isGatheringDocument && (
                    <Text
                      size="lg"
                      fw={600}
                      c="white"
                      style={{
                        animation: 'pulse 1s ease-in-out infinite',
                      }}
                    >
                      Gathering Document...
                    </Text>
                  )}
                  {isCalling && !isGatheringDocument && (
                    <Text size="lg" fw={600} c="white">
                      Calling Aria...
                    </Text>
                  )}
                  {isConnected &&
                    !isCalling &&
                    !isGatheringDocument &&
                    !isDisconnected && (
                      <Text size="lg" fw={600} c="white">
                        Connected
                      </Text>
                    )}
                  {isDisconnected && (
                    <>
                      <Text size="lg" fw={600} c="white">
                        Disconnected
                      </Text>
                      <Text size="md" fw={600} c="white">
                        Press the green call button below to reconnect.
                      </Text>
                    </>
                  )}
                  {!isConnected &&
                    !isCalling &&
                    !isGatheringDocument &&
                    !isDisconnected && (
                      <Text size="lg" fw={600} c="white">
                        Ready to Call
                      </Text>
                    )}
                </Box>

                {/* Bottom Controls */}
                <Box
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '20px',
                  }}
                >
                  {/* Speaker Button (Left) */}
                  <Tooltip label={isSpeaking ? 'Speaker On' : 'Speaker Off'}>
                    <ActionIcon
                      size="xl"
                      radius="xl"
                      variant="filled"
                      color={isSpeaking ? 'green' : 'gray'}
                      onClick={toggleAudio}
                      style={{
                        backgroundColor: isSpeaking
                          ? theme.colors.green[6]
                          : theme.colors.gray[6],
                        opacity: 0.9,
                      }}
                    >
                      {isSpeaking ? (
                        <IconVolume size={24} />
                      ) : (
                        <IconVolumeOff size={24} />
                      )}
                    </ActionIcon>
                  </Tooltip>

                  {/* End Call / Reconnect Button (Center) */}
                  {isDisconnected ? (
                    <Tooltip label="Reconnect">
                      <ActionIcon
                        size="xl"
                        radius="xl"
                        variant="filled"
                        color="green"
                        onClick={handleReconnect}
                        style={{
                          backgroundColor: theme.colors.green[6],
                          opacity: 0.9,
                        }}
                      >
                        <IconPhone size={24} />
                      </ActionIcon>
                    </Tooltip>
                  ) : (
                    <Tooltip label="End Call">
                      <ActionIcon
                        size="xl"
                        radius="xl"
                        variant="filled"
                        color="red"
                        onClick={disconnectFromSession}
                        style={{
                          backgroundColor: theme.colors.red[6],
                          opacity: 0.9,
                        }}
                      >
                        <IconPhoneOff size={24} />
                      </ActionIcon>
                    </Tooltip>
                  )}

                  {/* Mute Button (Right) */}
                  <Tooltip label={isListening ? 'Mute' : 'Unmute'}>
                    <ActionIcon
                      size="xl"
                      radius="xl"
                      variant="filled"
                      color={isListening ? 'gray' : 'red'}
                      onClick={toggleListening}
                      disabled={!isConnected}
                      style={{
                        backgroundColor: isListening
                          ? theme.colors.gray[6]
                          : theme.colors.red[6],
                        opacity: isConnected ? 0.9 : 0.5,
                      }}
                    >
                      {isListening ? (
                        <IconMicrophone size={24} />
                      ) : (
                        <IconMicrophoneOff size={24} />
                      )}
                    </ActionIcon>
                  </Tooltip>
                </Box>
              </Box>

              {/* Error Display */}
              {error && (
                <Box style={{ padding: '20px' }}>
                  <Text size="sm" c="red" ta="center">
                    {error}
                  </Text>
                </Box>
              )}
            </Paper>
          </Box>

          {showContractReferences && (
            <Box style={{ width: '50%' }} className="contract-references-panel">
              <Paper p="md" withBorder>
                <Stack gap="sm">
                  <Text size="sm" fw={600}>
                    Contract References
                  </Text>
                  <Box
                    style={{
                      minHeight: '360px',
                      maxHeight: '520px',
                      overflowY: 'auto',
                    }}
                  >
                    {contractSearchResults &&
                    contractSearchResults.length > 0 ? (
                      <Stack gap="md">
                        {contractSearchResults.map((res, idx: number) => {
                          const rawScore =
                            typeof res.score === 'number'
                              ? res.score
                              : Number.parseFloat(
                                  res.score !== null && res.score !== undefined
                                    ? String(res.score)
                                    : '0',
                                )
                          const relevance = Number.isFinite(rawScore)
                            ? rawScore.toFixed(2)
                            : 'N/A'
                          const fullText =
                            typeof res.text === 'string'
                              ? res.text.replace(/\n{2,}/g, '\n').trim()
                              : ''
                          const isExpanded = expandedExcerpts.has(idx)
                          const displayText = isExpanded
                            ? fullText
                            : createPreview(fullText)
                          const needsExpansion = fullText.length > 200

                          return (
                            <Box key={idx}>
                              <Group
                                justify="space-between"
                                align="flex-start"
                                mb="xs"
                              >
                                <Text
                                  fw={600}
                                  size="sm"
                                  style={{ flex: 1 }}
                                >{`Excerpt ${idx + 1} (Relevance: ${relevance})`}</Text>
                                {needsExpansion && (
                                  <ActionIcon
                                    variant="subtle"
                                    size="sm"
                                    onClick={() => toggleExcerptExpansion(idx)}
                                    style={{ flexShrink: 0 }}
                                  >
                                    {isExpanded ? (
                                      <IconChevronUp size={16} />
                                    ) : (
                                      <IconChevronDown size={16} />
                                    )}
                                  </ActionIcon>
                                )}
                              </Group>
                              <Text
                                size="sm"
                                style={{ whiteSpace: 'pre-wrap' }}
                              >
                                {displayText}
                              </Text>
                            </Box>
                          )
                        })}
                      </Stack>
                    ) : (
                      <Text size="sm" c="dimmed">
                        When Aria cites sources, they will appear here.
                      </Text>
                    )}
                  </Box>

                  {aiResponse && (
                    <Paper p="sm" withBorder>
                      <Text size="sm" fw={500} mb={4}>
                        Aria&apos;s Response
                      </Text>
                      <Text size="sm">{aiResponse}</Text>
                    </Paper>
                  )}
                </Stack>
              </Paper>
            </Box>
          )}
        </Box>
      </Modal>
    </>
  )
}

export default VoiceChatModal
