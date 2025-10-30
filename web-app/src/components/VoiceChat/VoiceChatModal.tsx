import {
  useCreateVoiceChatSession,
  useEnsureVectorStore,
} from '@/api/v1/ai/voice-chat'
import { baseURL } from '@/urlConfig'
import { useAuth, useUser } from '@clerk/clerk-react'
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
import { useEffect, useRef, useState } from 'react'
import { z } from 'zod'

interface VoiceChatModalProps {
  opened: boolean
  onClose: () => void
  contractData?: any
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
  const [session, setSession] = useState<any>(null)
  const [contractSearchResults, setContractSearchResults] = useState<any[]>([])
  const [showContractReferences, setShowContractReferences] = useState(false)
  const [expandedExcerpts, setExpandedExcerpts] = useState<Set<number>>(
    new Set(),
  )
  const [cachedVectorStoreId, setCachedVectorStoreId] = useState<string | null>(
    null,
  )

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

  useEffect(() => {
    if (opened && !session) {
      // Simulate document gathering time
      const timer = setTimeout(() => {
        setIsGatheringDocument(false)
        initializeVoiceChat()
      }, 2000) // 2 second delay

      return () => clearTimeout(timer)
    }
  }, [opened])

  const searchContractContent = async (query: string): Promise<any[]> => {
    if (!contractData?.document_id) {
      return []
    }

    // Get the vector store ID from cache, contract data, or ensure we have one
    let vectorStoreId =
      cachedVectorStoreId ||
      contractData?.openai_vector_store_id ||
      contractData?.vector_store_id

    // If we don't have a vector store ID, try to ensure one exists
    if (!vectorStoreId && contractData?.openai_file_id) {
      try {
        const vs = await ensureVectorStore.mutateAsync({
          openai_file_id: contractData.openai_file_id,
          name: 'aria-knowledge',
        })
        vectorStoreId = vs.vector_store_id
        // Cache the vector store ID for future searches
        setCachedVectorStoreId(vectorStoreId)
      } catch (e) {
        console.error('Failed to ensure vector store:', e)
        return []
      }
    }

    if (!vectorStoreId) {
      return []
    }

    // Create an AbortController for timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 second timeout

    try {
      const token = await getCachedToken()
      const url = `${baseURL}/v1/operational/projects/${contractData.project_id}/documents/search-contract/${contractData.document_id}?query=${encodeURIComponent(query)}&vector_store_id=${encodeURIComponent(vectorStoreId)}`

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
        const data = await response.json()

        // Return raw results for UI formatting
        if (
          Array.isArray(data.search_results) &&
          data.search_results.length > 0
        ) {
          return data.search_results
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
              const retryData = await retryResponse.json()
              if (
                Array.isArray(retryData.search_results) &&
                retryData.search_results.length > 0
              ) {
                return retryData.search_results
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
    description:
      'Search for relevant information in the contract document. Use this tool when users ask questions about contract terms, clauses, obligations, or any contract details.',
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

  const initializeVoiceChat = async () => {
    try {
      // Dynamically import the OpenAI Agents SDK
      const { RealtimeAgent, RealtimeSession } = await import(
        '@openai/agents-realtime'
      )

      const contractContext = contractData
        ? `
        You are Aria, a helpful AI assistant specializing in contract analysis and energy project management.

        You are helping a user understand a contract with the following details:
        - Contract Type: ${contractData.category_name_long || 'Unknown'}
        - Counterparty: ${contractData.name_long || 'Unknown'}
        - Execution Date: ${contractData.execution_date || 'Unknown'}
        - Contract Summary: ${contractData.contract_summary ? contractData.contract_summary : 'Unknown'}

        IMPORTANT: Greet the user by saying something like: "Hi ${user?.firstName || 'there'}, how can I help you with this ${contractData.name_long || 'the counterparty'} contract?".

        You have access to a search_contract tool that can find relevant information in the contract document. When users ask questions about contract terms, clauses, obligations, or any contract details, you should automatically use the search_contract tool to find the relevant information first, then provide a comprehensive answer based on the search results.

        Your role is to:
        1. Greet the user by name and ask about their contract questions
        2. When a user finishes asking their question, respond immediately by saying that you're searching through the document to help answer their question. While you do that, already initiate your search_contract tool and say that you'll show any related paragraphs where you found the information in the Contract References box.
        3. Answer questions about contract terms, obligations, and requirements based on the search results. If a one word answer is enough, just answer that immediately and then elaborate briefly.
        4. Explain technical language and legal concepts in simple terms

        Always use the search_contract tool when users ask about specific contract details. .
        Speak quickly and professionally, like an experienced attorney. But keep your answers short - if someone wants to know a small detail about the contract, just answer that immediately and then elaborate briefly.
      `
        : `
        You are Aria, a helpful AI assistant specializing in contract analysis and energy project management.
        However, you do not know anything about the contract the user wants to know about because you don't have access to it. Tell the user something must've gone wrong.
      `

      let vectorStoreId: string | undefined =
        contractData?.openai_vector_store_id || contractData?.vector_store_id

      // If we have a file id but no vector store id, request one from backend
      if (!vectorStoreId && contractData?.openai_file_id) {
        try {
          const vs = await ensureVectorStore.mutateAsync({
            openai_file_id: contractData.openai_file_id,
            name: 'aria-knowledge',
          })
          vectorStoreId = vs.vector_store_id
        } catch (e) {
          console.error('Failed ensuring vector store:', e)
        }
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

      setSession(newSession)
    } catch (err) {
      console.error('Failed to initialize voice chat:', err)
      setError('Failed to initialize voice chat. Please try again.')
    }
  }

  const connectToSession = async () => {
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
        const s = session as any
        if (typeof s.mute === 'function') {
          s.mute(false) // false = unmute (start listening)
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
  }

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
  }, [session, isGatheringDocument, isConnected, isCalling, isDisconnected])

  const disconnectFromSession = async () => {
    if (!session) return

    try {
      const s: any = session

      // Stop listening first
      if (typeof s.mute === 'function') {
        s.mute(true) // true = mute (stop listening)
      } else {
        console.error('❌ No mute method found on session during disconnect')
      }

      // Then disconnect
      if (typeof s.disconnect === 'function') {
        await s.disconnect()
      } else if (typeof s.close === 'function') {
        await s.close()
      } else if (typeof s.end === 'function') {
        await s.end()
      } else if (typeof s.stop === 'function') {
        await s.stop()
      } else if (s.connection && typeof s.connection.close === 'function') {
        s.connection.close()
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
      setCachedVectorStoreId(null) // Clear cached vector store ID
      tokenCacheRef.current = null // Clear token cache
      // Don't clear the session - keep it for reconnection
    }
  }

  const toggleListening = () => {
    if (!isConnected || !session) return

    try {
      if (isListening) {
        // Stop listening (mute)
        setIsListening(false)

        // Use the mute method to mute (stop listening)
        const s = session as any
        if (typeof s.mute === 'function') {
          s.mute(true) // true = mute (stop listening)
        } else {
          console.error('❌ No mute method found on session')
        }
      } else {
        // Start listening (unmute)
        setIsListening(true)

        // Use the mute method to unmute (start listening)
        const s = session as any
        if (typeof s.mute === 'function') {
          s.mute(false) // false = unmute (start listening)
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

  const handleClose = () => {
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
  }, [])

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
        onClose={handleClose}
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
                  background:
                    'linear-gradient(to bottom, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.7) 100%)',
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
                        animation: 'pulse 1.5s ease-in-out infinite',
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
                    <Text size="lg" fw={600} c="white">
                      Disconnected...
                    </Text>
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
                        {contractSearchResults.map((res: any, idx: number) => {
                          const score =
                            typeof res.score === 'number'
                              ? res.score
                              : parseFloat(res.score || '0')
                          const relevance = Number.isFinite(score)
                            ? score.toFixed(2)
                            : 'N/A'
                          const fullText = (res.text || '')
                            .replace(/\n{2,}/g, '\n')
                            .trim()
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
