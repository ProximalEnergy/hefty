import { useGetUserSelf } from '@/api/admin'
import {
  useCreateCalendarEvent,
  useGetCalendarEventCategories,
} from '@/api/v1/operational/calendar'
import { useGetProjectDocuments } from '@/api/v1/operational/documents'
import {
  useAnalyzeContractDocument,
  useCreateContract,
  useGetContractCategories,
} from '@/api/v1/operational/project/contracts'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useCreateCompany } from '@/hooks/api'
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Grid,
  Group,
  HoverCard,
  Modal,
  ScrollArea,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { DateInput } from '@mantine/dates'
import { notifications } from '@mantine/notifications'
import {
  IconFileText,
  IconPlus,
  IconSearch,
  IconTrash,
} from '@tabler/icons-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'

import PdfViewer, { PdfViewerHandle } from '../../../components/PdfViewer'
import { StreamingText } from '../../../components/StreamingText'

// Contract categories from the database models
// const CONTRACT_CATEGORIES = [ ... ]

interface ContractDate {
  id: string
  title: string
  date: Date | null
  description: string
}

interface SourceReference {
  location?: string
  quoted_text?: string
}

interface SourceReferences {
  contract_category?: SourceReference
  counterparty_name?: SourceReference
  execution_date?: SourceReference
  term_start_date?: SourceReference
  term_end_date?: SourceReference
  counter_contact_addressee?: SourceReference
  counter_contact_address?: SourceReference
  counter_contact_email?: SourceReference
  contract_summary?: SourceReference
}

interface CreateContractModalProps {
  opened: boolean
  onClose: () => void
}

// Component to format source references with hover card
const SourceReferenceHoverCard = ({
  sourceReference,
  children,
  onReferenceClick,
}: {
  sourceReference?: SourceReference
  children: React.ReactNode
  onReferenceClick?: (searchText: string) => void
}) => {
  if (
    !sourceReference ||
    (!sourceReference.location && !sourceReference.quoted_text)
  ) {
    return <>{children}</>
  }

  const formatSourceReference = () => {
    const { location, quoted_text } = sourceReference

    return (
      <div style={{ lineHeight: 1.4 }}>
        {location && (
          <div
            style={{
              marginBottom: '8px',
              fontSize: '0.9em',
              color: 'var(--mantine-color-gray-6)',
            }}
          >
            📍 {location}
          </div>
        )}
        {quoted_text && (
          <div
            style={{
              fontStyle: 'italic',
              color: 'var(--mantine-color-blue-6)',
              fontWeight: 500,
              cursor: onReferenceClick ? 'pointer' : 'default',
              textDecoration: onReferenceClick ? 'underline' : 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 8px',
              backgroundColor: 'var(--mantine-color-blue-0)',
              borderRadius: '4px',
              border: '1px solid var(--mantine-color-blue-2)',
            }}
            onClick={() => onReferenceClick?.(quoted_text)}
            title={
              onReferenceClick
                ? 'Click to open PDF and search for this text'
                : undefined
            }
          >
            &quot;{quoted_text}&quot;
            {onReferenceClick && (
              <IconSearch size={12} style={{ opacity: 0.7 }} />
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <HoverCard
      width={400}
      position="top"
      shadow="md"
      openDelay={300}
      closeDelay={1000}
      withArrow
    >
      <HoverCard.Target>{children}</HoverCard.Target>
      <HoverCard.Dropdown>
        <Box p="md">{formatSourceReference()}</Box>
      </HoverCard.Dropdown>
    </HoverCard>
  )
}

const CreateContractModal = ({ opened, onClose }: CreateContractModalProps) => {
  const { projectId } = useParams<{ projectId: string }>()
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('light')
  const isDarkMode = computedColorScheme === 'dark'
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null)
  const [contractCategory, setContractCategory] = useState<string | null>(null)
  const [counterpartyName, setCounterpartyName] = useState('')
  const [executionDate, setExecutionDate] = useState<Date | null>(null)
  const [termStartDate, setTermStartDate] = useState<Date | null>(null)
  const [termEndDate, setTermEndDate] = useState<Date | null>(null)
  const [counterContactAddressee, setCounterContactAddressee] = useState('')
  const [counterContactEmail, setCounterContactEmail] = useState('')
  const [counterContactAddress, setCounterContactAddress] = useState('')
  const [contractSummary, setContractSummary] = useState('')
  const [contractDates, setContractDates] = useState<ContractDate[]>([])
  const [analysisCompleted, setAnalysisCompleted] = useState(false)
  const [sourceReferences, setSourceReferences] = useState<SourceReferences>({})
  const [storeOnCalendar, setStoreOnCalendar] = useState(true)
  const pdfRef = useRef<PdfViewerHandle | null>(null)

  const { data: documents, isLoading } = useGetProjectDocuments({
    pathParams: { projectId: projectId || '-1' },
  })

  const { data: project } = useSelectProject(projectId!)

  const { data: currentUser } = useGetUserSelf({})

  const { data: categories, isLoading: categoriesLoading } =
    useGetContractCategories()
  const categoryOptions = (categories || []).map((c) => ({
    value: c.name_short,
    label: c.name_long,
  }))

  // Calendar hooks
  const createCalendarEvent = useCreateCalendarEvent()
  const { data: calendarCategories } = useGetCalendarEventCategories({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  // Helper function to map backend category response to dropdown value
  const mapBackendCategoryToValue = (
    backendCategory: string,
  ): string | null => {
    if (!backendCategory || !categories || categories.length === 0) {
      console.warn('No categories available for mapping:', {
        backendCategory,
        categories,
      })
      return null
    }

    // First try exact match
    const exactMatch = categories.find(
      (cat) => cat.name_long === backendCategory,
    )
    if (exactMatch) {
      return exactMatch.name_short
    }

    // If no exact match, try partial match (in case AI returns something slightly different)
    const partialMatch = categories.find(
      (cat) =>
        backendCategory.includes(cat.name_long) ||
        cat.name_long.includes(backendCategory),
    )
    if (partialMatch) {
      return partialMatch.name_short
    }

    // If still no match, try to find by common variations
    const normalizedBackend = backendCategory
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '')
    const normalizedMatch = categories.find((cat) => {
      const normalizedLabel = cat.name_long
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '')
      return (
        normalizedLabel.includes(normalizedBackend) ||
        normalizedBackend.includes(normalizedLabel)
      )
    })
    if (normalizedMatch) {
      return normalizedMatch.name_short
    }

    // Last resort: try to match against short names
    const shortNameMatch = categories.find((cat) => {
      const normalizedShort = cat.name_short
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '')
      const normalizedInput = backendCategory
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '')
      return (
        normalizedShort.includes(normalizedInput) ||
        normalizedInput.includes(normalizedShort)
      )
    })
    if (shortNameMatch) {
      return shortNameMatch.name_short
    }

    // If no match found, return null
    return null
  }

  // Auto-analyze document when selected
  useEffect(() => {
    if (
      selectedDocument &&
      !analyzeContract.isPending &&
      !analysisCompleted &&
      categories
    ) {
      // Reset analysis state when selecting a new document
      setAnalysisCompleted(false)
      handleDocumentAnalysis(selectedDocument)
    }
  }, [selectedDocument, categories])

  const createCompany = useCreateCompany()
  const createContract = useCreateContract()
  const analyzeContract = useAnalyzeContractDocument()

  // Function to handle reference clicks and search in PDF
  const handleReferenceClick = (searchText: string) => {
    if (!searchText || !pdfRef.current) return

    // Trigger the fuzzy search
    pdfRef.current.find(searchText)
  }

  const addContractDate = () => {
    const newDate: ContractDate = {
      id: Date.now().toString(),
      title: '',
      date: null,
      description: '',
    }
    setContractDates([...contractDates, newDate])
  }

  const removeContractDate = (id: string) => {
    setContractDates(contractDates.filter((date) => date.id !== id))
  }

  const updateContractDate = (
    id: string,
    field: keyof ContractDate,
    value: any,
  ) => {
    setContractDates(
      contractDates.map((date) =>
        date.id === id ? { ...date, [field]: value } : date,
      ),
    )
  }

  const handleDocumentAnalysis = async (documentId: string) => {
    if (!projectId) return

    try {
      const response = await analyzeContract.mutateAsync({
        projectId,
        documentId,
      })

      if (response.data.success && response.data.analysis) {
        const analysis = response.data.analysis

        // Extract source references for tooltips
        if (analysis.source_references) {
          setSourceReferences(analysis.source_references)
        }

        // Helper function to safely parse dates
        const safeParseDate = (
          dateString: string | null | undefined,
        ): Date | null => {
          if (!dateString || typeof dateString !== 'string') return null

          try {
            // Check if it's a valid date format (YYYY-MM-DD)
            const dateRegex = /^\d{4}-\d{2}-\d{2}$/
            if (!dateRegex.test(dateString)) return null

            const [year, month, day] = dateString.split('-').map(Number)

            // Validate year, month, day ranges
            if (
              year < 1900 ||
              year > 2100 ||
              month < 1 ||
              month > 12 ||
              day < 1 ||
              day > 31
            ) {
              return null
            }

            const date = new Date(year, month - 1, day) // month is 0-indexed

            // Check if the date is valid (handles edge cases like Feb 30)
            if (isNaN(date.getTime())) return null

            return date
          } catch (error) {
            console.warn('Failed to parse date:', dateString, error)
            return null
          }
        }

        // Auto-fill form fields based on LLM analysis

        if (analysis.contract_category) {
          const mappedCategory = mapBackendCategoryToValue(
            analysis.contract_category,
          )

          if (!mappedCategory) {
            console.warn(
              'No category match found. Available categories:',
              categories?.map((c) => `${c.name_short} -> ${c.name_long}`),
            )
          }

          setContractCategory(mappedCategory)
        }

        if (analysis.counterparty_name) {
          setCounterpartyName(analysis.counterparty_name)
        }

        if (analysis.execution_date) {
          const parsedDate = safeParseDate(analysis.execution_date)
          setExecutionDate(parsedDate)
        }

        if (analysis.term_start_date) {
          const parsedDate = safeParseDate(analysis.term_start_date)
          setTermStartDate(parsedDate)
        }

        if (analysis.term_end_date) {
          const parsedDate = safeParseDate(analysis.term_end_date)
          setTermEndDate(parsedDate)
        }

        if (analysis.counter_contact_addressee) {
          setCounterContactAddressee(analysis.counter_contact_addressee)
        }

        if (analysis.counter_contact_email) {
          setCounterContactEmail(analysis.counter_contact_email)
        }

        if (analysis.counter_contact_address) {
          setCounterContactAddress(analysis.counter_contact_address)
        }

        if (analysis.contract_summary) {
          setContractSummary(analysis.contract_summary)
        }
        if (
          analysis.important_dates &&
          Array.isArray(analysis.important_dates)
        ) {
          const formattedDates = analysis.important_dates.map(
            (date: any, index: number) => ({
              id: `ai-generated-${index}`,
              title: date.title || '',
              date: safeParseDate(date.date),
              description: date.description || '',
            }),
          )

          setContractDates(formattedDates)
        } else {
        }
        setAnalysisCompleted(true)

        // Show success notification
        notifications.show({
          title: 'Analysis Complete',
          message:
            'Contract analysis completed successfully! Some fields may need manual review.',
          color: 'green',
        })
      } else {
        // Handle case where analysis failed or returned unexpected data
        console.warn(
          'Contract analysis failed or returned unexpected data:',
          response.data,
        )
        notifications.show({
          title: 'Analysis Warning',
          message:
            "Contract analysis completed but some information couldn't be extracted. Please review and fill in missing details manually.",
          color: 'yellow',
        })
      }
    } catch (error) {
      console.error('Error analyzing contract document:', error)
      // Show user-friendly error message
      notifications.show({
        title: 'Analysis Failed',
        message:
          'Something went wrong analyzing the contract. Please fill in the information yourself.',
        color: 'red',
      })
    }
  }

  const resetForm = () => {
    setSelectedDocument(null)
    setContractCategory(null)
    setCounterpartyName('')
    setExecutionDate(null)
    setTermStartDate(null)
    setTermEndDate(null)
    setCounterContactAddressee('')
    setCounterContactEmail('')
    setCounterContactAddress('')
    setContractSummary('')
    setContractDates([])
    setAnalysisCompleted(false)
    setSourceReferences({})
    setStoreOnCalendar(true)
  }

  // Helper function to create calendar events from contract dates
  const createCalendarEventsFromContractDates = async () => {
    if (!projectId || !storeOnCalendar || contractDates.length === 0) {
      return
    }

    // Get the first available calendar category (or use a default)
    const defaultCategory = calendarCategories?.[0]
    if (!defaultCategory) {
      console.warn('No calendar categories available')
      return
    }

    try {
      // Create calendar events for each contract date
      const calendarPromises = contractDates
        .filter((contractDate) => contractDate.date && contractDate.title)
        .map(async (contractDate) => {
          const startTime = new Date(contractDate.date!)
          const endTime = new Date(contractDate.date!)
          endTime.setDate(endTime.getDate() + 1) // Make it all day by setting end to next day

          return createCalendarEvent.mutateAsync({
            projectId,
            event: {
              title: contractDate.title,
              description:
                contractDate.description ||
                `Contract date: ${contractDate.title}`,
              start_time: startTime.toISOString(),
              end_time: endTime.toISOString(),
              all_day: true,
              calendar_item_category_id: defaultCategory.category_id,
              color: defaultCategory.color_code,
              timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            },
          })
        })

      await Promise.all(calendarPromises)

      notifications.show({
        title: 'Calendar Events Created',
        message: `Successfully added ${contractDates.length} contract dates to the project calendar.`,
        color: 'green',
      })
    } catch (error) {
      console.error('Error creating calendar events:', error)
      notifications.show({
        title: 'Calendar Error',
        message:
          'Failed to create some calendar events. Please check the calendar manually.',
        color: 'yellow',
      })
    }
  }

  const documentOptions =
    documents
      ?.filter((doc) => !doc.contract_name)
      .map((doc) => ({
        value: doc.document_id,
        label: doc.name,
      })) || []

  const handleSubmit = async () => {
    if (
      !selectedDocument ||
      !contractCategory ||
      !counterpartyName ||
      !executionDate ||
      !projectId
    ) {
      // Show error message
      return
    }

    try {
      // Create new company for counterparty
      const companyResponse = await createCompany.mutateAsync({
        name_short: counterpartyName.toLowerCase().replace(/\s+/g, '_'),
        name_long: counterpartyName,
      })

      // Format the dates here before sending to the mutation
      const formattedExecutionDate = executionDate.toISOString().split('T')[0] // YYYY-MM-DD
      const formattedTermStartDate =
        termStartDate?.toISOString().split('T')[0] || null
      const formattedTermEndDate =
        termEndDate?.toISOString().split('T')[0] || null

      // Create contract with new company ID and all fields
      await createContract.mutateAsync({
        project_id: projectId,
        document_id: selectedDocument,
        company_id_provider: currentUser?.company_id!,
        company_id_counter: companyResponse.data.company_id,
        execution_date: formattedExecutionDate,
        contract_category_name_short: contractCategory || undefined,
        term_start_date: formattedTermStartDate,
        term_end_date: formattedTermEndDate,
        counter_contact_addressee: counterContactAddressee || undefined,
        counter_contact_email: counterContactEmail || undefined,
        counter_contact_address: counterContactAddress || undefined,
        contract_summary: contractSummary || undefined,
      })

      // Create calendar events if checkbox is selected and there are contract dates
      if (storeOnCalendar && contractDates.length > 0) {
        await createCalendarEventsFromContractDates()
      }

      resetForm()
      onClose()
    } catch (error) {
      console.error('Error creating contract:', error)
      // Show error message to user
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="Create New Contract"
      size="90%"
      styles={{
        title: { fontSize: '1.5rem', fontWeight: 600 },
        body: { padding: 0 },
      }}
    >
      <Grid gutter={0} style={{ height: '80vh' }}>
        {/* Left Side - Document Selection and PDF Viewer */}
        <Grid.Col span={6} p="md">
          <Stack h="100%">
            {/* Document Selection */}
            <Card withBorder p="md">
              <Title order={4} mb="md">
                Document Selection
              </Title>
              <Stack gap="md">
                {documentOptions.length > 0 ? (
                  <Select
                    label="Select Document"
                    placeholder="Choose a document to analyze"
                    data={documentOptions}
                    value={selectedDocument}
                    onChange={setSelectedDocument}
                    disabled={isLoading}
                    required
                    size="md"
                  />
                ) : (
                  <Stack gap="xs" align="center" py="md">
                    <Text size="sm" c="dimmed" ta="center">
                      No documents available for contract creation
                    </Text>
                    <Text size="sm" c="dimmed" ta="center">
                      Please upload a document first to create a contract
                    </Text>
                    <Button
                      variant="light"
                      color="blue"
                      size="sm"
                      component={Link}
                      to={`/projects/${projectId}/settings`}
                      leftSection={<IconFileText size={16} />}
                    >
                      Go to Settings
                    </Button>
                  </Stack>
                )}
                {selectedDocument && (
                  <Stack gap="xs">
                    {analyzeContract.isPending ? (
                      <StreamingText
                        text="Thanks for requesting my assistance! I'm currently going through the pages to seek out things like contract categories, counterparty information, execution dates, and key terms. I'll fill these in here on the right side of the screen so that you can review and correct them if needed. I'll add my thought process to the input fields so that you can see how I came to my conclusions. I'm scanning through legal language, financial provisions, and operational requirements to extract the most relevant details. This involves parsing through complex contractual language, identifying key performance indicators, and understanding the relationship dynamics between parties. I'm also looking for important dates, contact information, and any special clauses that might affect project operations. This thorough analysis ensures we capture all the essential elements needed for proper contract management and compliance tracking. Please bear with me as I carefully examine each section to provide you with the most accurate and comprehensive contract summary possible."
                        size="sm"
                        c="blue"
                        ta="left"
                        speed={40}
                      />
                    ) : analysisCompleted ? (
                      <StreamingText
                        text="✓ Document analyzed successfully! Fields have been auto-filled."
                        size="sm"
                        c="green"
                        ta="center"
                        speed={60}
                      />
                    ) : (
                      <Text size="sm" c="dimmed" ta="center">
                        Document selected - analysis will begin automatically
                      </Text>
                    )}
                  </Stack>
                )}
              </Stack>
            </Card>

            {/* PDF Viewer or Placeholder */}
            <Card withBorder p="md" style={{ flex: 1 }}>
              {documentOptions.length === 0 ? (
                <Box
                  style={{
                    height: 'calc(100% - 80px)',
                    border: '1px solid #dee2e6',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: isDarkMode
                      ? theme.colors.dark[5]
                      : theme.colors.gray[1],
                  }}
                >
                  <Stack align="center" gap="md">
                    <IconFileText
                      size={80}
                      color={
                        isDarkMode ? theme.colors.dark[2] : theme.colors.gray[5]
                      }
                    />
                    <Text size="lg" c="dimmed" ta="center">
                      No documents available
                    </Text>
                    <Text size="sm" c="dimmed" ta="center">
                      Upload documents in Settings to create contracts
                    </Text>
                  </Stack>
                </Box>
              ) : selectedDocument ? (
                <Box
                  style={{
                    height: 'calc(100% - 80px)',
                    border: '1px solid #dee2e6',
                    borderRadius: '8px',
                    overflow: 'hidden',
                  }}
                >
                  <PdfViewer
                    ref={pdfRef}
                    fileUrl={
                      documents?.find((d) => d.document_id === selectedDocument)
                        ?.url || ''
                    }
                  />
                </Box>
              ) : (
                <Box
                  style={{
                    height: 'calc(100% - 80px)',
                    border: '1px solid #dee2e6',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: isDarkMode
                      ? theme.colors.dark[5]
                      : theme.colors.gray[1],
                  }}
                >
                  <Stack align="center" gap="md">
                    <IconFileText
                      size={80}
                      color={
                        isDarkMode ? theme.colors.dark[2] : theme.colors.gray[5]
                      }
                    />
                    <Text size="lg" c="dimmed" ta="center">
                      Select a document above to preview
                    </Text>
                    <Text size="sm" c="dimmed" ta="center">
                      The preview will appear here once a document is selected
                    </Text>
                  </Stack>
                </Box>
              )}
            </Card>
          </Stack>
        </Grid.Col>

        {/* Right Side - Contract Details Form */}
        <Grid.Col span={6} p="md">
          <ScrollArea h="100%" type="auto">
            <Stack gap="lg">
              <Group justify="space-between" align="center">
                <Title order={3}>Contract Details</Title>
                <Group gap="xs">
                  {selectedDocument && (
                    <Badge
                      color={analysisCompleted ? 'blue' : 'gray'}
                      variant="light"
                      size="sm"
                    >
                      {analysisCompleted ? 'AI Assisted' : 'Manual Entry'}
                    </Badge>
                  )}
                </Group>
              </Group>

              {/* Contract Category and Counterparty Company - Same Row */}
              <Group grow>
                <Stack gap="xs">
                  <SourceReferenceHoverCard
                    sourceReference={sourceReferences.contract_category}
                    onReferenceClick={handleReferenceClick}
                  >
                    <Select
                      label="Contract Category"
                      placeholder={
                        categoriesLoading
                          ? 'Loading categories...'
                          : 'Select contract type'
                      }
                      data={categoryOptions}
                      value={contractCategory}
                      onChange={setContractCategory}
                      required
                      size="md"
                      disabled={categoriesLoading}
                    />
                  </SourceReferenceHoverCard>
                </Stack>
                <SourceReferenceHoverCard
                  sourceReference={sourceReferences.counterparty_name}
                  onReferenceClick={handleReferenceClick}
                >
                  <TextInput
                    label="Counterparty Company Name"
                    value={counterpartyName}
                    onChange={(event) =>
                      setCounterpartyName(event.currentTarget.value)
                    }
                    required
                    size="md"
                  />
                </SourceReferenceHoverCard>
              </Group>

              {/* Execution Date */}
              <SourceReferenceHoverCard
                sourceReference={sourceReferences.execution_date}
                onReferenceClick={handleReferenceClick}
              >
                <DateInput
                  label="Execution Date"
                  placeholder="Select execution date"
                  value={executionDate}
                  onChange={setExecutionDate}
                  required
                  size="md"
                />
              </SourceReferenceHoverCard>

              {/* Contract Summary */}
              <SourceReferenceHoverCard
                sourceReference={sourceReferences.contract_summary}
                onReferenceClick={handleReferenceClick}
              >
                <Textarea
                  label="Contract Summary"
                  value={contractSummary}
                  onChange={(event) =>
                    setContractSummary(event.currentTarget.value)
                  }
                  placeholder="LLM-generated or manual summary of contract terms"
                  size="md"
                  minRows={6}
                  maxRows={24}
                  styles={{
                    input: {
                      minHeight: '100px',
                      height: '100px',
                      resize: 'vertical',
                    },
                  }}
                />
              </SourceReferenceHoverCard>

              {/* Term Dates */}
              <Group grow>
                <SourceReferenceHoverCard
                  sourceReference={sourceReferences.term_start_date}
                  onReferenceClick={handleReferenceClick}
                >
                  <DateInput
                    label="Term Start Date"
                    placeholder="Contract start date"
                    value={termStartDate}
                    onChange={setTermStartDate}
                    size="md"
                  />
                </SourceReferenceHoverCard>
                <SourceReferenceHoverCard
                  sourceReference={sourceReferences.term_end_date}
                  onReferenceClick={handleReferenceClick}
                >
                  <DateInput
                    label="Term End Date"
                    placeholder="Contract end date"
                    value={termEndDate}
                    onChange={setTermEndDate}
                    size="md"
                  />
                </SourceReferenceHoverCard>
              </Group>

              {/* Contact Information */}
              <Card withBorder p="md">
                <Title order={4} mb="md">
                  Counterparty Contact Information
                </Title>
                <Stack gap="md">
                  <SourceReferenceHoverCard
                    sourceReference={sourceReferences.counter_contact_addressee}
                    onReferenceClick={handleReferenceClick}
                  >
                    <TextInput
                      label="Contact Addressee"
                      value={counterContactAddressee}
                      onChange={(event) =>
                        setCounterContactAddressee(event.currentTarget.value)
                      }
                      placeholder="e.g., Legal Department or John Smith"
                      size="md"
                    />
                  </SourceReferenceHoverCard>
                  <SourceReferenceHoverCard
                    sourceReference={sourceReferences.counter_contact_email}
                    onReferenceClick={handleReferenceClick}
                  >
                    <TextInput
                      label="Contact Email"
                      value={counterContactEmail}
                      onChange={(event) =>
                        setCounterContactEmail(event.currentTarget.value)
                      }
                      placeholder="contact@company.com"
                      size="md"
                    />
                  </SourceReferenceHoverCard>
                  <SourceReferenceHoverCard
                    sourceReference={sourceReferences.counter_contact_address}
                    onReferenceClick={handleReferenceClick}
                  >
                    <Textarea
                      label="Contact Address"
                      value={counterContactAddress}
                      onChange={(event) =>
                        setCounterContactAddress(event.currentTarget.value)
                      }
                      placeholder="Full address"
                      size="md"
                      minRows={3}
                    />
                  </SourceReferenceHoverCard>
                </Stack>
              </Card>

              {/* Important Contract Dates */}
              <Card withBorder p="md">
                <Group justify="space-between" mb="md">
                  <Title order={4}>Important Contract Dates</Title>
                  <Button
                    variant="light"
                    size="sm"
                    onClick={addContractDate}
                    leftSection={<IconPlus size={16} />}
                  >
                    Add Date
                  </Button>
                </Group>

                <Stack gap="md">
                  {contractDates.map((contractDate) => (
                    <Card
                      key={contractDate.id}
                      withBorder
                      p="sm"
                      style={{
                        backgroundColor: isDarkMode
                          ? theme.colors.dark[6]
                          : theme.colors.gray[0],
                      }}
                    >
                      <Group justify="space-between" mb="xs">
                        <Text size="sm" fw={500}>
                          Contract Date Entry
                        </Text>
                        <ActionIcon
                          color="red"
                          variant="light"
                          onClick={() => removeContractDate(contractDate.id)}
                        >
                          <IconTrash size={16} />
                        </ActionIcon>
                      </Group>
                      <Stack gap="xs">
                        <TextInput
                          label="Date Title"
                          value={contractDate.title}
                          onChange={(event) =>
                            updateContractDate(
                              contractDate.id,
                              'title',
                              event.currentTarget.value,
                            )
                          }
                          placeholder="e.g., Payment Due, Renewal Option"
                          size="sm"
                        />
                        <DateInput
                          label="Date"
                          value={contractDate.date}
                          onChange={(date) =>
                            updateContractDate(contractDate.id, 'date', date)
                          }
                          placeholder="Select date"
                          size="sm"
                        />
                        <TextInput
                          label="Description"
                          value={contractDate.description}
                          onChange={(event) =>
                            updateContractDate(
                              contractDate.id,
                              'description',
                              event.currentTarget.value,
                            )
                          }
                          placeholder="Description of this date's significance"
                          size="sm"
                        />
                      </Stack>
                    </Card>
                  ))}

                  {contractDates.length === 0 && (
                    <Text c="dimmed" size="sm" ta="center" py="md">
                      No important dates added yet. Click &quot;Add Date&quot;
                      to include key contract milestones.
                    </Text>
                  )}
                </Stack>

                <Checkbox
                  label={`Store these items on the ${project?.name_long || 'Project'} Calendar`}
                  checked={storeOnCalendar}
                  onChange={(event) =>
                    setStoreOnCalendar(event.currentTarget.checked)
                  }
                  mt="md"
                  size="sm"
                />
              </Card>

              {/* Submit Button */}
              <Button
                onClick={handleSubmit}
                loading={createCompany.isPending || createContract.isPending}
                size="lg"
                fullWidth
              >
                Create Contract
              </Button>
            </Stack>
          </ScrollArea>
        </Grid.Col>
      </Grid>
    </Modal>
  )
}

export default CreateContractModal
