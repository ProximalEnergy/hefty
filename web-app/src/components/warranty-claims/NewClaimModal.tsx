import { useGetUserPermissions } from '@/api/admin'
import { deviceTypeIdsForProjectType } from '@/api/deviceTypeGroups'
import {
  ClaimStatusEnum,
  ClaimSubmissionChannelEnum,
  DeviceTypeEnum,
} from '@/api/enumerations'
import { useGetCompanies } from '@/api/v1/admin/companies'
import { useGetUserSelf } from '@/api/v1/admin/users'
import { requestWarrantyClaimPdfAssist } from '@/api/v1/ai/warranty_claim_pdf_assist'
import {
  fetchClaimEventDataCsv,
  useAddClaimDevice,
  useCreateClaim,
  useCreateClaimConfig,
  useGetClaimById,
  useGetClaimConfigs,
  useGetProjectClaims,
  useSubmitClaim,
  useUploadClaimAttachment,
} from '@/api/v1/operational/claims'
import { useGetDeviceModels } from '@/api/v1/operational/device_models'
import { useUploadProjectDocument } from '@/api/v1/operational/documents'
import { useGetProjectContracts } from '@/api/v1/operational/project/contracts'
import { useGetProjectEvents } from '@/api/v1/operational/project/events'
import { useSelectProject } from '@/api/v1/operational/projects'
import PdfAnnotator, {
  type PdfAnnotatorHandle,
  type PdfAnnotatorState,
} from '@/components/PdfAnnotator'
import { ProjectDocumentUploadButton } from '@/components/ProjectDocumentUploadButton'
import { extractPdfAcroFormFilledFieldsForAssist } from '@/components/pdfAssist'
import DeviceEventSelect from '@/components/warranty-claims/DeviceEventSelect'
import OemConfigForm, {
  getDefaultContactEmailError,
} from '@/components/warranty-claims/OemConfigForm'
import { expandOemDeviceIdsForEventMatching } from '@/components/warranty-claims/constants'
import ClaimEmailFieldRow from '@/components/warranty-claims/new-claim/ClaimEmailFieldRow'
import ClaimGisMapPdf, {
  type ClaimGisMapPdfHandle,
  isWarrantyClaimGisMapFilename,
} from '@/components/warranty-claims/new-claim/ClaimGisMapPdf'
import {
  type DeviceEntry,
  deviceNameForWarrantyAssist,
} from '@/components/warranty-claims/new-claim/devices'
import {
  CLAIM_EMAIL_LABEL_COL_W,
  buildClaimSubmissionEmailHtml,
  buildDefaultClaimEmailBody,
  buildDefaultClaimEmailSubject,
  parseEmailAddressList,
} from '@/components/warranty-claims/new-claim/email'
import { useGetDevicesV2, useUpdateDeviceSerialNumber } from '@/hooks/api'
import CreateContractModal from '@/pages/projects/contracts/CreateContractModal'
import {
  getDeviceModelImagePublicUrl,
  getDeviceModelImageUrl,
} from '@/utils/cdn'
import { triggerDownloadFromLocalFile } from '@/utils/triggerDownload'
import { useAuth, useUser } from '@clerk/react'
import {
  ActionIcon,
  Alert,
  Anchor,
  Box,
  Button,
  Checkbox,
  Group,
  Image,
  List,
  Loader,
  Modal,
  Paper,
  Progress,
  Radio,
  Select,
  Stack,
  Stepper,
  Switch,
  Table,
  Text,
  TextInput,
  Textarea,
  Tooltip,
  useComputedColorScheme,
} from '@mantine/core'
import { Dropzone } from '@mantine/dropzone'
import { useDisclosure } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import {
  IconCheck,
  IconDownload,
  IconEdit,
  IconExternalLink,
  IconFile,
  IconPlus,
  IconSparkles,
  IconTrash,
  IconUpload,
  IconX,
} from '@tabler/icons-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

interface Props {
  projectId: string
  opened: boolean
  onClose: () => void
  draftClaimId?: number | null
}

const LEGACY_FILLED_CLAIM_PDF_FILENAME = 'warranty-claim-form-filled.pdf'
const FILLED_CLAIM_PDF_FILENAME_PATTERN =
  /^warranty-claim-(?:\d+|pending)-\d{4}-\d{2}-\d{2}-form-filled\.pdf$/
const PREVIOUS_CLAIM_EXAMPLE_MAX_CHARS = 2000
const AI_ASSIST_STEPS = [
  'Checking provided inputs',
  'Collecting project and user information',
  'Learning from previously submitted claims',
  'Collecting event timeseries data',
  'Filling in form',
]
const AI_ASSIST_STEP_BASE_MS = 1200
const AI_ASSIST_FIRST_STEPS_MULTIPLIER = 2.5
const AI_ASSIST_STEP_JITTER_MS = 2000
const AI_ASSIST_MIN_STEP_MS = 500
const CLAIM_ATTACHMENT_MAX_SIZE_BYTES = 40 * 1024 ** 2
const CLAIM_EMAIL_SUBJECT_HINT =
  'Includes OEM and claim id; new drafts show ' +
  '(pending) until the claim is saved.'
const CLAIM_EMAIL_BODY_TOOLTIP =
  'Plain-text body sent to the OEM; edit to match your process.'
const GIS_MAP_PDF_READY_RETRY_COUNT = 10
const GIS_MAP_PDF_READY_RETRY_MS = 250

function buildFilledClaimPdfFilename(claimId: number | null): string {
  const claimPart = claimId == null ? 'pending' : String(claimId)
  const datePart = new Date().toISOString().slice(0, 10)
  return `warranty-claim-${claimPart}-${datePart}-form-filled.pdf`
}

function isFilledClaimPdfFilename(filename: string): boolean {
  return (
    filename === LEGACY_FILLED_CLAIM_PDF_FILENAME ||
    FILLED_CLAIM_PDF_FILENAME_PATTERN.test(filename)
  )
}

type EventCsvStatus =
  | { status: 'pending' }
  | { status: 'complete'; filename: string }
  | { status: 'error'; message: string }

type ClaimPdfDraft = {
  fileUrl: string
  state: PdfAnnotatorState
}

function userHasProjectPermission(
  permissions: ReturnType<typeof useGetUserPermissions>['data'],
  nameShort: string,
) {
  return permissions?.some((p) => p.name_short === nameShort) ?? false
}

function formatIssueDateForAssist(value: string): string {
  if (!value.trim()) return ''
  return value.slice(0, 10)
}

function getAncestorDeviceIds(device: {
  device_id: number
  device_id_path?: string | null
  parent_device_id?: number | null
}): number[] {
  const pathIds = device.device_id_path
    ?.split('.')
    .map((id) => Number(id))
    .filter((id) => Number.isFinite(id) && id !== device.device_id)

  if (pathIds?.length) return pathIds
  return device.parent_device_id != null ? [device.parent_device_id] : []
}

export default function NewClaimModal({
  projectId,
  opened,
  onClose,
  draftClaimId = null,
}: Props) {
  const [step, setStep] = useState(0)
  const [selectedConfigId, setSelectedConfigId] = useState<number | null>(null)
  const [createdClaimId, setCreatedClaimId] = useState<number | null>(null)
  const [summary, setSummary] = useState('')
  const [selectedDevices, setSelectedDevices] = useState<DeviceEntry[]>([])
  const [selectedEventIds, setSelectedEventIds] = useState<number[]>([])
  const [includeRecentlyClosed, setIncludeRecentlyClosed] = useState(false)
  const [showAllDevices, setShowAllDevices] = useState(false)
  const [showAddDeviceControls, setShowAddDeviceControls] = useState(false)
  const eventsAutoPopulatedRef = useRef<string | null>(null)
  const [deviceTypeFilter, setDeviceTypeFilter] = useState<string | null>(null)
  const [deviceSearch, setDeviceSearch] = useState<string | null>(null)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [, setEventCsvStatuses] = useState<Record<number, EventCsvStatus>>({})
  const [ccEmails, setCcEmails] = useState('')
  const [toEmails, setToEmails] = useState('')
  const [bccEmails, setBccEmails] = useState('')
  const [reviewEmailSubject, setReviewEmailSubject] = useState('')
  const [reviewEmailBody, setReviewEmailBody] = useState('')
  const [savingDraft, setSavingDraft] = useState(false)
  const [submittingClaim, setSubmittingClaim] = useState(false)
  const [generatingGisMapPdf, setGeneratingGisMapPdf] = useState(false)
  const submittedDeviceIdsRef = useRef<Set<number>>(new Set())
  const eventCsvControllersRef = useRef<Map<number, AbortController>>(new Map())
  const eventCsvFileNamesRef = useRef<Map<number, string>>(new Map())
  const requestedEventCsvIdsRef = useRef<Set<number>>(new Set())
  const selectedEventIdsForCsvRef = useRef<Set<number>>(new Set())
  const [createContractModalOpened, createContractModalHandlers] =
    useDisclosure(false)
  const uploadProjectDocument = useUploadProjectDocument()
  const userPermissions = useGetUserPermissions({
    pathParams: { projectId },
    queryOptions: { enabled: opened },
  })
  const userSelf = useGetUserSelf({
    queryOptions: { enabled: opened },
  })
  const { data: companiesForUser } = useGetCompanies({
    queryParams: {
      company_ids: userSelf.data?.company_id
        ? [userSelf.data.company_id]
        : undefined,
    },
    queryOptions: {
      enabled: opened && !!userSelf.data?.company_id,
    },
  })
  const { user } = useUser()
  const { getToken } = useAuth()
  const pdfAnnotatorRef = useRef<PdfAnnotatorHandle>(null)
  const gisMapPdfRef = useRef<ClaimGisMapPdfHandle>(null)
  const [claimPdfDraft, setClaimPdfDraft] = useState<ClaimPdfDraft | null>(null)
  const [aiAssistLoading, setAiAssistLoading] = useState(false)
  const [aiAssistStepIndex, setAiAssistStepIndex] = useState(0)
  const [overlayAssistReplaceOpen, setOverlayAssistReplaceOpen] =
    useState(false)
  const lastAutoAssistKeyRef = useRef<string | null>(null)
  const reviewCcDefaultAppliedRef = useRef(false)
  const [previousClaimPdfText, setPreviousClaimPdfText] = useState('')
  const [previousClaimExampleLoading, setPreviousClaimExampleLoading] =
    useState(false)
  const computedColorScheme = useComputedColorScheme('light')
  const isDarkMode = computedColorScheme === 'dark'

  useEffect(() => {
    if (!aiAssistLoading) {
      setAiAssistStepIndex(0)
      return
    }
    if (aiAssistStepIndex >= AI_ASSIST_STEPS.length - 1) return

    const baseDuration =
      aiAssistStepIndex < 3
        ? AI_ASSIST_STEP_BASE_MS * AI_ASSIST_FIRST_STEPS_MULTIPLIER
        : AI_ASSIST_STEP_BASE_MS
    const jitter = (Math.random() * 2 - 1) * AI_ASSIST_STEP_JITTER_MS
    const duration = Math.max(AI_ASSIST_MIN_STEP_MS, baseDuration + jitter)
    const timeoutId = window.setTimeout(() => {
      setAiAssistStepIndex((prev) =>
        Math.min(prev + 1, AI_ASSIST_STEPS.length - 1),
      )
    }, duration)
    return () => window.clearTimeout(timeoutId)
  }, [aiAssistLoading, aiAssistStepIndex])

  // New/edit config form
  const [showNewConfig, setShowNewConfig] = useState(false)
  const [editingConfigId, setEditingConfigId] = useState<number | null>(null)
  const [configJustCreated, setConfigJustCreated] = useState<string | null>(
    null,
  )
  const [newConfigChannel, setNewConfigChannel] = useState<string>(
    ClaimSubmissionChannelEnum.EMAIL,
  )
  const [newConfigContact, setNewConfigContact] = useState('')
  const newConfigContactError = getDefaultContactEmailError(newConfigContact)
  const [newConfigPortal, setNewConfigPortal] = useState('')
  const [newConfigCounterpartyId, setNewConfigCounterpartyId] = useState<
    string | null
  >(null)

  const project = useSelectProject(projectId)
  const projectTypeId = project.data?.project_type_id

  const { data: draftClaim } = useGetClaimById({
    pathParams: {
      projectId,
      claimId: String(draftClaimId ?? ''),
    },
    queryOptions: { enabled: opened && !!draftClaimId },
  })

  useEffect(() => {
    if (!opened) {
      lastAutoAssistKeyRef.current = null
      setOverlayAssistReplaceOpen(false)
      submittedDeviceIdsRef.current = new Set()
      eventCsvControllersRef.current.forEach((controller) => controller.abort())
      eventCsvControllersRef.current.clear()
      eventCsvFileNamesRef.current.clear()
      requestedEventCsvIdsRef.current.clear()
      selectedEventIdsForCsvRef.current.clear()
      setEventCsvStatuses({})
    }
  }, [opened])

  useEffect(() => {
    setSelectedEventIds([])
    setToEmails('')
    eventsAutoPopulatedRef.current = null
  }, [selectedConfigId])

  const uploadDocError = uploadProjectDocument.error
  const resetUploadDoc = uploadProjectDocument.reset
  useEffect(() => {
    if (!uploadDocError) return
    notifications.show({
      id: 'new-claim-doc-upload-error',
      title: 'Upload Error',
      message: uploadDocError.response?.data.detail,
      color: 'red',
    })
    resetUploadDoc()
  }, [uploadDocError, resetUploadDoc])

  useEffect(() => {
    if (!draftClaim || !opened) return
    setCreatedClaimId(draftClaim.claim_id)
    setSelectedConfigId(draftClaim.claim_config_id)
    setSummary(draftClaim.summary ?? '')
    setSelectedDevices(
      draftClaim.devices.map((d) => ({
        device_id: d.device_id,
        device_name: d.device_name ?? `Device ${d.device_id}`,
        device_model_id: null,
        device_serial_number: null,
        oem_serial_number: d.oem_serial_number ?? '',
        oem_part_number: d.oem_part_number ?? '',
        notes: d.notes ?? '',
        event_id: d.event_id ?? null,
      })),
    )
  }, [draftClaim, opened])

  const { data: configs } = useGetClaimConfigs({
    pathParams: { projectId },
    queryOptions: { enabled: opened },
  })
  const hasConfigs = !!configs && configs.length > 0

  const { data: projectClaims } = useGetProjectClaims({
    pathParams: { projectId },
    queryOptions: { enabled: opened && !!selectedConfigId },
  })

  const claimIdsByEventId = useMemo(() => {
    const map = new Map<number, number[]>()
    for (const claim of projectClaims ?? []) {
      for (const eventId of claim.claim_event_ids ?? []) {
        map.set(eventId, [...(map.get(eventId) ?? []), claim.claim_id])
      }
    }
    return map
  }, [projectClaims])

  const { data: contracts } = useGetProjectContracts({
    pathParams: { projectId },
    queryOptions: { enabled: opened },
  })

  const deviceTypeIds = useMemo(() => {
    if (deviceTypeFilter) return [Number(deviceTypeFilter)]
    return deviceTypeIdsForProjectType(projectTypeId)
  }, [deviceTypeFilter, projectTypeId])

  const availableDeviceTypes = useMemo(() => {
    const types = deviceTypeIdsForProjectType(projectTypeId)
    const nameMap = Object.entries(DeviceTypeEnum)
    return types
      .map((id) => {
        const entry = nameMap.find(([, v]) => v === id)
        return entry
          ? { value: String(id), label: entry[0].replace(/_/g, ' ') }
          : null
      })
      .filter(Boolean) as { value: string; label: string }[]
  }, [projectTypeId])

  const { data: devices } = useGetDevicesV2({
    pathParams: { projectId },
    filters: { device_type_ids: deviceTypeIds },
    queryOptions: { enabled: opened && step === 2 },
  })

  // Project-wide device list (unfiltered by deviceTypeFilter) used to pick a
  // sensible default device type once the OEM is chosen in step 0.
  const allBaseDeviceTypeIds = useMemo(
    () => deviceTypeIdsForProjectType(projectTypeId),
    [projectTypeId],
  )

  const {
    data: allProjectDevicesForOemDefault,
    isLoading: allProjectDevicesForOemDefaultLoading,
  } = useGetDevicesV2({
    pathParams: { projectId },
    filters: { device_type_ids: allBaseDeviceTypeIds },
    queryOptions: { enabled: opened && !!selectedConfigId },
  })

  const allProjectDeviceModelIds = useMemo(() => {
    if (!allProjectDevicesForOemDefault) return []
    return Array.from(
      new Set(
        allProjectDevicesForOemDefault
          .map((d) => d.device_model_id)
          .filter((id): id is number => id != null),
      ),
    )
  }, [allProjectDevicesForOemDefault])

  const {
    data: allProjectDeviceModels,
    isLoading: allProjectDeviceModelsLoading,
  } = useGetDeviceModels({
    queryParams: { device_model_ids: allProjectDeviceModelIds },
    queryOptions: {
      enabled: opened && allProjectDeviceModelIds.length > 0,
    },
  })

  useEffect(() => {
    if (!devices?.length) return
    setSelectedDevices((prev) =>
      prev.map((selected) => {
        if (selected.device_model_id != null) return selected
        const source = devices.find((d) => d.device_id === selected.device_id)
        if (!source) return selected
        return {
          ...selected,
          device_model_id: source.device_model_id ?? null,
        }
      }),
    )
  }, [devices])

  const selectedDeviceModelIds = useMemo(
    () =>
      Array.from(
        new Set(
          selectedDevices
            .map((d) => d.device_model_id)
            .filter((id): id is number => id != null),
        ),
      ),
    [selectedDevices],
  )

  const { data: selectedDeviceModels } = useGetDeviceModels({
    queryParams: { device_model_ids: selectedDeviceModelIds },
    queryOptions: {
      enabled: opened && selectedDeviceModelIds.length > 0,
    },
  })

  const selectedDeviceModelById = useMemo(
    () =>
      new Map(
        (selectedDeviceModels ?? []).map((model) => [
          model.device_model_id,
          model,
        ]),
      ),
    [selectedDeviceModels],
  )

  const selectedDeviceIdsForAssist = useMemo(
    () => selectedDevices.map((d) => d.device_id),
    [selectedDevices],
  )

  const { data: devicesDeepForAssist, isFetching: loadingDeepForAssist } =
    useGetDevicesV2({
      pathParams: { projectId },
      filters: {
        device_ids: selectedDeviceIdsForAssist,
        deep: true,
      },
      queryOptions: {
        enabled: opened && selectedDeviceIdsForAssist.length > 0,
      },
    })

  const {
    data: selectedDeviceEventsForAssist,
    isFetching: loadingEventsForAssist,
  } = useGetProjectEvents({
    pathParams: { projectId },
    queryParams: {
      device_ids: selectedDeviceIdsForAssist,
    },
    queryOptions: {
      enabled: opened && selectedDeviceIdsForAssist.length > 0,
    },
  })

  const deviceDetailByIdForAssist = useMemo(
    () => new Map((devicesDeepForAssist ?? []).map((d) => [d.device_id, d])),
    [devicesDeepForAssist],
  )

  const selectedDeviceAncestorIdsForAssist = useMemo(() => {
    const ids = new Set<number>()
    for (const selectedDevice of selectedDevices) {
      const device = deviceDetailByIdForAssist.get(selectedDevice.device_id)
      if (!device) continue
      getAncestorDeviceIds(device).forEach((id) => ids.add(id))
    }
    return Array.from(ids)
  }, [deviceDetailByIdForAssist, selectedDevices])

  const {
    data: selectedDeviceAncestorDetails,
    isFetching: loadingDeviceAncestorsForAssist,
  } = useGetDevicesV2({
    pathParams: { projectId },
    filters: {
      device_ids: selectedDeviceAncestorIdsForAssist,
    },
    queryOptions: {
      enabled: opened && selectedDeviceAncestorIdsForAssist.length > 0,
    },
  })

  useEffect(() => {
    if (!devicesDeepForAssist?.length) return
    setSelectedDevices((prev) => {
      let changed = false
      const next = prev.map((selected) => {
        const source = deviceDetailByIdForAssist.get(selected.device_id)
        if (!source) return selected

        const serial = source.serial_number?.trim() || null
        const shouldPrefill = !selected.oem_serial_number.trim() && !!serial
        if (selected.device_serial_number === serial && !shouldPrefill) {
          return selected
        }

        changed = true
        return {
          ...selected,
          device_serial_number: serial,
          oem_serial_number: shouldPrefill
            ? serial
            : selected.oem_serial_number,
        }
      })
      return changed ? next : prev
    })
  }, [deviceDetailByIdForAssist, devicesDeepForAssist])

  const createClaimConfig = useCreateClaimConfig()
  const createClaim = useCreateClaim()
  const addDevice = useAddClaimDevice()
  const updateDeviceSerialNumber = useUpdateDeviceSerialNumber()
  const uploadAttachment = useUploadClaimAttachment()
  const submitClaim = useSubmitClaim()

  const selectedConfig = useMemo(
    () => configs?.find((c) => c.claim_config_id === selectedConfigId) ?? null,
    [configs, selectedConfigId],
  )

  const lastFiledClaim = useMemo(() => {
    if (!selectedConfigId || !projectClaims) return null
    const currentClaimIds = new Set(
      [createdClaimId, draftClaimId].filter((id): id is number => id != null),
    )
    return (
      projectClaims
        .filter((claim) => claim.claim_config_id === selectedConfigId)
        .filter((claim) => claim.status !== ClaimStatusEnum.DRAFT)
        .filter((claim) => !currentClaimIds.has(claim.claim_id))
        .sort((a, b) => {
          const aTime = a.updated_at ?? a.created_at ?? ''
          const bTime = b.updated_at ?? b.created_at ?? ''
          return bTime.localeCompare(aTime)
        })[0] ?? null
    )
  }, [createdClaimId, draftClaimId, projectClaims, selectedConfigId])

  const {
    data: lastFiledClaimDetail,
    isFetching: loadingLastFiledClaimDetail,
  } = useGetClaimById({
    pathParams: {
      projectId,
      claimId: String(lastFiledClaim?.claim_id ?? ''),
    },
    queryOptions: { enabled: opened && !!lastFiledClaim },
  })

  const isLastFiledClaimDetailForCurrentProject = useMemo(() => {
    if (!lastFiledClaim || !lastFiledClaimDetail || !projectClaims) return false
    if (lastFiledClaimDetail.claim_id !== lastFiledClaim.claim_id) return false
    return projectClaims.some(
      (claim) => claim.claim_id === lastFiledClaimDetail.claim_id,
    )
  }, [lastFiledClaim, lastFiledClaimDetail, projectClaims])

  useEffect(() => {
    let cancelled = false
    setPreviousClaimPdfText('')
    setPreviousClaimExampleLoading(false)
    if (!isLastFiledClaimDetailForCurrentProject) return

    const filledPdfAttachments = (lastFiledClaimDetail?.attachments ?? [])
      .filter(
        (attachment) =>
          isFilledClaimPdfFilename(attachment.filename) && !!attachment.url,
      )
      .sort((a, b) => {
        const aTime = a.uploaded_at ?? ''
        const bTime = b.uploaded_at ?? ''
        return bTime.localeCompare(aTime)
      })
    if (filledPdfAttachments.length === 0) return

    setPreviousClaimExampleLoading(true)
    const loadPreviousClaimFields = async () => {
      for (const attachment of filledPdfAttachments) {
        try {
          const text = await extractPdfAcroFormFilledFieldsForAssist(
            attachment.url!,
            {
              maxChars: PREVIOUS_CLAIM_EXAMPLE_MAX_CHARS,
            },
          )
          if (text.trim()) {
            if (!cancelled) setPreviousClaimPdfText(text)
            return
          }
        } catch {
          /* try the next matching attachment */
        }
      }
      if (!cancelled) setPreviousClaimPdfText('')
    }

    loadPreviousClaimFields().finally(() => {
      if (!cancelled) setPreviousClaimExampleLoading(false)
    })

    return () => {
      cancelled = true
    }
  }, [
    isLastFiledClaimDetailForCurrentProject,
    lastFiledClaimDetail?.attachments,
  ])

  // Pick the device type (most-common) on this project whose device models
  // belong to the selected OEM's company, used as the default for step 1.
  const oemDefaultDeviceTypeId = useMemo(() => {
    if (
      !selectedConfig ||
      !allProjectDevicesForOemDefault ||
      !allProjectDeviceModels
    ) {
      return null
    }
    const counterpartyId = selectedConfig.counterparty_company_id
    const modelById = new Map(
      allProjectDeviceModels.map((m) => [m.device_model_id, m]),
    )
    const typeCounts = new Map<number, number>()
    for (const dev of allProjectDevicesForOemDefault) {
      if (dev.device_model_id == null) continue
      const m = modelById.get(dev.device_model_id)
      if (!m || m.company_id !== counterpartyId) continue
      typeCounts.set(
        m.device_type_id,
        (typeCounts.get(m.device_type_id) ?? 0) + 1,
      )
    }
    if (typeCounts.size === 0) return null
    let bestId: number | null = null
    let bestCount = -1
    for (const [tid, count] of typeCounts) {
      if (count > bestCount) {
        bestId = tid
        bestCount = count
      }
    }
    return bestId
  }, [selectedConfig, allProjectDevicesForOemDefault, allProjectDeviceModels])

  // Device-model groups for the OEM, summarized at the top of the claim-form
  // step. Pulls every model in the project whose company matches the selected
  // OEM, plus the number of project devices using it and how many of those are
  // currently selected for this claim. This gives the user (and the AI fill)
  // immediate brand/model context for the equipment under warranty.
  const oemDeviceModelGroups = useMemo(() => {
    if (
      !selectedConfig ||
      !allProjectDevicesForOemDefault ||
      !allProjectDeviceModels
    ) {
      return []
    }
    const norm = (v: string | null | undefined) =>
      (v ?? '').trim().toLowerCase()
    const counterpartyId = norm(selectedConfig.counterparty_company_id)
    const matchingModels = allProjectDeviceModels.filter(
      (m) => norm(m.company_id) === counterpartyId,
    )
    if (matchingModels.length === 0) return []
    const selectedIdSet = new Set(selectedDevices.map((d) => d.device_id))
    const groups = new Map<
      number,
      {
        model: (typeof matchingModels)[number]
        projectCount: number
        selectedCount: number
      }
    >()
    for (const m of matchingModels) {
      groups.set(m.device_model_id, {
        model: m,
        projectCount: 0,
        selectedCount: 0,
      })
    }
    for (const dev of allProjectDevicesForOemDefault) {
      if (dev.device_model_id == null) continue
      const entry = groups.get(dev.device_model_id)
      if (!entry) continue
      entry.projectCount += 1
      if (selectedIdSet.has(dev.device_id)) {
        entry.selectedCount += 1
      }
    }
    return Array.from(groups.values()).filter((g) => g.projectCount > 0)
  }, [
    selectedConfig,
    allProjectDevicesForOemDefault,
    allProjectDeviceModels,
    selectedDevices,
  ])

  // Set of device_model_ids that belong to the selected OEM. Used to default-
  // filter the device picker on the Devices step to OEM-owned devices only.
  const oemDeviceModelIdSet = useMemo(() => {
    if (!selectedConfig || !allProjectDeviceModels) return null
    const norm = (v: string | null | undefined) =>
      (v ?? '').trim().toLowerCase()
    const counterpartyId = norm(selectedConfig.counterparty_company_id)
    return new Set(
      allProjectDeviceModels
        .filter((m) => norm(m.company_id) === counterpartyId)
        .map((m) => m.device_model_id),
    )
  }, [selectedConfig, allProjectDeviceModels])

  // Device IDs for the "Events" step: OEM-owned devices plus related BESS
  // equipment when the OEM supplies PCS or DC enclosure (see constants).
  const oemDeviceIds = useMemo(() => {
    if (!allProjectDevicesForOemDefault || !oemDeviceModelIdSet) return []
    return expandOemDeviceIdsForEventMatching(
      oemDeviceModelIdSet,
      allProjectDevicesForOemDefault,
    )
  }, [allProjectDevicesForOemDefault, oemDeviceModelIdSet])

  const recentlyClosedSinceIso = useMemo(() => {
    const d = new Date()
    d.setDate(d.getDate() - 90)
    return d.toISOString()
  }, [])

  const { data: oemEvents, isLoading: oemEventsLoading } = useGetProjectEvents({
    pathParams: { projectId },
    queryParams: {
      device_ids: oemDeviceIds,
      open: includeRecentlyClosed ? false : true,
      ...(includeRecentlyClosed
        ? { time_end_gte: recentlyClosedSinceIso }
        : {}),
    },
    queryOptions: {
      enabled: opened && step === 1 && oemDeviceIds.length > 0,
    },
  })

  const oemEventById = useMemo(
    () => new Map((oemEvents ?? []).map((e) => [e.event_id, e])),
    [oemEvents],
  )
  const oemDeviceLookupLoading =
    selectedConfig != null &&
    (allProjectDevicesForOemDefaultLoading ||
      allProjectDevicesForOemDefault == null ||
      (allProjectDeviceModelIds.length > 0 &&
        (allProjectDeviceModelsLoading || allProjectDeviceModels == null)))
  const eventsForDeviceSelectByDeviceId = useMemo(() => {
    const byDeviceId = new Map<number, NonNullable<typeof oemEvents>>()
    const seenEventIds = new Set<number>()

    for (const event of [
      ...(oemEvents ?? []),
      ...(selectedDeviceEventsForAssist ?? []),
    ]) {
      if (seenEventIds.has(event.event_id)) continue
      seenEventIds.add(event.event_id)
      byDeviceId.set(event.device_id, [
        ...(byDeviceId.get(event.device_id) ?? []),
        event,
      ])
    }

    return byDeviceId
  }, [oemEvents, selectedDeviceEventsForAssist])

  const eventByIdForAssist = useMemo(
    () =>
      new Map(
        [...(oemEvents ?? []), ...(selectedDeviceEventsForAssist ?? [])].map(
          (e) => [e.event_id, e],
        ),
      ),
    [oemEvents, selectedDeviceEventsForAssist],
  )

  const selectedEventIdsForAssist = useMemo(() => {
    const ids = [
      ...selectedEventIds,
      ...selectedDevices.map((d) => d.event_id),
    ].filter((id): id is number => id != null)
    return Array.from(new Set(ids))
  }, [selectedEventIds, selectedDevices])

  useEffect(() => {
    selectedEventIdsForCsvRef.current = new Set(selectedEventIdsForAssist)
  }, [selectedEventIdsForAssist])

  useEffect(() => {
    if (!opened) return
    const selectedIds = new Set(selectedEventIdsForAssist)
    const removedFileNames: string[] = []

    for (const [eventId, controller] of eventCsvControllersRef.current) {
      if (selectedIds.has(eventId)) continue
      controller.abort()
      eventCsvControllersRef.current.delete(eventId)
    }
    for (const [eventId, filename] of eventCsvFileNamesRef.current) {
      if (selectedIds.has(eventId)) continue
      removedFileNames.push(filename)
      eventCsvFileNamesRef.current.delete(eventId)
    }
    for (const eventId of Array.from(requestedEventCsvIdsRef.current)) {
      if (!selectedIds.has(eventId)) {
        requestedEventCsvIdsRef.current.delete(eventId)
      }
    }
    if (removedFileNames.length > 0) {
      setUploadedFiles((prev) =>
        prev.filter((file) => !removedFileNames.includes(file.name)),
      )
    }
    setEventCsvStatuses((prev) => {
      const next: Record<number, EventCsvStatus> = {}
      for (const eventId of selectedIds) {
        if (prev[eventId]) next[eventId] = prev[eventId]
      }
      return next
    })

    for (const eventId of selectedEventIdsForAssist) {
      if (requestedEventCsvIdsRef.current.has(eventId)) continue
      requestedEventCsvIdsRef.current.add(eventId)
      const controller = new AbortController()
      eventCsvControllersRef.current.set(eventId, controller)
      setEventCsvStatuses((prev) => ({
        ...prev,
        [eventId]: { status: 'pending' },
      }))

      void (async () => {
        try {
          const token = await getToken({ template: 'default' })
          if (!token) throw new Error('Could not get a session token')
          const file = await fetchClaimEventDataCsv({
            token,
            projectId,
            eventId,
            signal: controller.signal,
          })
          if (!selectedEventIdsForCsvRef.current.has(eventId)) return
          const previousName = eventCsvFileNamesRef.current.get(eventId)
          eventCsvFileNamesRef.current.set(eventId, file.name)
          setUploadedFiles((prev) => [
            ...prev.filter(
              (existing) =>
                existing.name !== file.name && existing.name !== previousName,
            ),
            file,
          ])
          setEventCsvStatuses((prev) => ({
            ...prev,
            [eventId]: { status: 'complete', filename: file.name },
          }))
        } catch (error) {
          if (controller.signal.aborted) return
          if (!selectedEventIdsForCsvRef.current.has(eventId)) return
          const message =
            error instanceof Error ? error.message : 'Failed to fetch CSV'
          setEventCsvStatuses((prev) => ({
            ...prev,
            [eventId]: { status: 'error', message },
          }))
        } finally {
          eventCsvControllersRef.current.delete(eventId)
        }
      })()
    }
  }, [getToken, opened, projectId, selectedEventIdsForAssist])

  const claimEventsForAssist = useMemo(
    () =>
      selectedEventIdsForAssist
        .map((eventId) => eventByIdForAssist.get(eventId))
        .filter((event) => event != null)
        .map((event) => {
          const failureMode =
            event.failure_mode?.name_long ??
            event.failure_mode?.name_short ??
            ''
          const rootCause =
            event.root_cause?.name_long ?? event.root_cause?.name_short ?? ''
          return {
            event_id: event.event_id,
            device_id: event.device_id,
            time_start: event.time_start,
            time_end: event.time_end ?? '',
            failure_mode: failureMode,
            root_cause: rootCause,
          }
        }),
    [selectedEventIdsForAssist, eventByIdForAssist],
  )

  // Auto-populate selectedDevices from selected events when entering the
  // Devices step. Dedupe by device_id; if a device row already exists without
  // an event_id, attach the chosen event_id. Don't clobber user-edited fields.
  useEffect(() => {
    if (step !== 2) return
    if (selectedEventIds.length === 0) return
    if (oemEvents == null) return
    const key = [...selectedEventIds].sort((a, b) => a - b).join(',')
    if (eventsAutoPopulatedRef.current === key) return
    eventsAutoPopulatedRef.current = key

    setSelectedDevices((prev) => {
      const byDeviceId = new Map(prev.map((d) => [d.device_id, d]))
      for (const eventId of selectedEventIds) {
        const ev = oemEventById.get(eventId)
        if (!ev) continue
        const existing = byDeviceId.get(ev.device_id)
        if (existing) {
          if (existing.event_id == null) {
            byDeviceId.set(ev.device_id, { ...existing, event_id: eventId })
          }
          continue
        }
        const eventDevice = ev.device as
          | (typeof ev.device & { serial_number?: string | null })
          | null
          | undefined
        const serialNumber = eventDevice?.serial_number ?? null
        byDeviceId.set(ev.device_id, {
          device_id: ev.device_id,
          device_name:
            ev.device_name_full ||
            ev.device?.name_long ||
            ev.device?.name_short ||
            `Device ${ev.device_id}`,
          device_model_id: ev.device?.device_model_id ?? null,
          device_serial_number: serialNumber,
          oem_serial_number: serialNumber ?? '',
          oem_part_number: '',
          notes: '',
          event_id: eventId,
        })
      }
      return Array.from(byDeviceId.values())
    })
  }, [step, selectedEventIds, oemEvents, oemEventById])

  // Tracks which config id we last auto-applied a default device type for, and
  // the value we applied — so we don't override an explicit user override and
  // don't re-apply repeatedly for the same OEM.
  const oemDefaultAppliedRef = useRef<{
    configId: number
    value: string
  } | null>(null)

  useEffect(() => {
    if (!selectedConfigId || oemDefaultDeviceTypeId == null) return
    if (oemDefaultAppliedRef.current?.configId === selectedConfigId) return
    if (
      deviceTypeFilter != null &&
      oemDefaultAppliedRef.current?.value !== deviceTypeFilter
    ) {
      return
    }
    const value = String(oemDefaultDeviceTypeId)
    setDeviceTypeFilter(value)
    oemDefaultAppliedRef.current = { configId: selectedConfigId, value }
  }, [selectedConfigId, oemDefaultDeviceTypeId, deviceTypeFilter])

  const matchedContract = useMemo(() => {
    if (!selectedConfig || !contracts) return null
    const counterId = selectedConfig.counterparty_company_id
    return contracts.find((c) =>
      c.company_id_counter === counterId &&
      (c.category_name_short ?? '').endsWith('warranty_claim_form'),
    )
  }, [selectedConfig, contracts])
  const hasMatchedClaimFormPdf = !!matchedContract?.document_url

  const deviceOptions = useMemo(() => {
    if (!devices) return []
    const selectedIds = new Set(selectedDevices.map((d) => d.device_id))
    const oemFilter = !showAllDevices && oemDeviceModelIdSet
    return devices
      .filter((d: { device_id: number; device_model_id: number | null }) => {
        if (selectedIds.has(d.device_id)) return false
        if (oemFilter) {
          if (d.device_model_id == null) return false
          if (!oemDeviceModelIdSet.has(d.device_model_id)) return false
        }
        return true
      })
      .map(
        (d: {
          device_id: number
          name_short: string | null
          name_long: string | null
        }) => ({
          value: String(d.device_id),
          label: d.name_long || d.name_short || `Device ${d.device_id}`,
        }),
      )
  }, [devices, selectedDevices, showAllDevices, oemDeviceModelIdSet])

  const handleAddDevice = useCallback(
    (val: string | null) => {
      if (!val || !devices) return
      const id = Number(val)
      const dev = devices.find((d: { device_id: number }) => d.device_id === id)
      if (!dev) return
      setSelectedDevices((prev) => [
        ...prev,
        {
          device_id: id,
          device_name: dev.name_long || dev.name_short || `Device ${id}`,
          device_model_id: dev.device_model_id ?? null,
          device_serial_number: dev.serial_number ?? null,
          oem_serial_number: dev.serial_number ?? '',
          oem_part_number: '',
          notes: '',
          event_id: null,
        },
      ])
      setDeviceSearch(null)
      setShowAddDeviceControls(false)
    },
    [devices],
  )

  const handleRemoveDevice = useCallback((deviceId: number) => {
    setSelectedDevices((prev) => prev.filter((d) => d.device_id !== deviceId))
  }, [])

  const updateDeviceField = useCallback(
    (deviceId: number, field: keyof DeviceEntry, value: string) => {
      setSelectedDevices((prev) =>
        prev.map((d) =>
          d.device_id === deviceId ? { ...d, [field]: value } : d,
        ),
      )
    },
    [],
  )

  const handleEditConfig = useCallback(() => {
    if (!selectedConfig) return
    setNewConfigCounterpartyId(selectedConfig.counterparty_company_id)
    setNewConfigChannel(selectedConfig.default_submission_channel)
    setNewConfigContact(selectedConfig.default_contact ?? '')
    setNewConfigPortal(selectedConfig.portal_url ?? '')
    setEditingConfigId(selectedConfig.claim_config_id)
    setShowNewConfig(true)
    setConfigJustCreated(null)
  }, [selectedConfig])

  const handleCreateConfig = async () => {
    if (!newConfigCounterpartyId) return
    if (newConfigContactError) return
    const contact = newConfigContact.trim()
    try {
      const res = await createClaimConfig.mutateAsync({
        projectId,
        data: {
          counterparty_company_id: newConfigCounterpartyId,
          default_submission_channel: newConfigChannel,
          default_contact: contact || undefined,
          portal_url: newConfigPortal || undefined,
        },
      })
      setSelectedConfigId(res.data.claim_config_id)
      setConfigJustCreated(res.data.counterparty_name || 'New OEM')
      setShowNewConfig(false)
    } catch {
      notifications.show({
        title: 'Error',
        message: 'Failed to create claim config',
        color: 'red',
      })
    }
  }

  const createFilledPdfFile = useCallback(
    async (claimId: number | null) => {
      const annot = pdfAnnotatorRef.current
      if (!matchedContract?.document_url || !annot?.isReady()) {
        return null
      }

      const bytes = await annot.exportFilledPdf()
      const arrayBuffer = bytes.buffer.slice(
        bytes.byteOffset,
        bytes.byteOffset + bytes.byteLength,
      ) as ArrayBuffer
      return new File([arrayBuffer], buildFilledClaimPdfFilename(claimId), {
        type: 'application/pdf',
      })
    },
    [matchedContract?.document_url],
  )

  const addFilledPdfToAttachments = useCallback(async () => {
    const pdfFile = await createFilledPdfFile(createdClaimId ?? draftClaimId)
    if (!pdfFile) return
    setUploadedFiles((prev) => [
      ...prev.filter((file) => !isFilledClaimPdfFilename(file.name)),
      pdfFile,
    ])
  }, [createFilledPdfFile, createdClaimId, draftClaimId])

  const filesWithAutoSavedPdf = async (claimId: number | null) => {
    const pdfFile = await createFilledPdfFile(claimId)
    if (!pdfFile) return uploadedFiles
    return [
      ...uploadedFiles.filter((file) => !isFilledClaimPdfFilename(file.name)),
      pdfFile,
    ]
  }

  const createGisMapPdfFile = useCallback(
    async (claimId?: number | null) => {
      if (selectedDevices.length === 0) return null

      for (
        let attempt = 0;
        attempt < GIS_MAP_PDF_READY_RETRY_COUNT;
        attempt += 1
      ) {
        await new Promise((resolve) => window.requestAnimationFrame(resolve))
        const file =
          (await gisMapPdfRef.current?.createPdfFile(claimId)) ?? null
        if (file) return file

        await new Promise((resolve) =>
          window.setTimeout(resolve, GIS_MAP_PDF_READY_RETRY_MS),
        )
      }

      return null
    },
    [selectedDevices.length],
  )

  const addGisMapPdfToAttachments = useCallback(async () => {
    setGeneratingGisMapPdf(true)
    try {
      const mapPdfFile = await createGisMapPdfFile()
      if (!mapPdfFile) {
        notifications.show({
          title: 'GIS map not ready',
          message: 'Try returning to this step or saving the claim again.',
          color: 'yellow',
        })
        return
      }
      setUploadedFiles((prev) => [
        ...prev.filter((file) => !isWarrantyClaimGisMapFilename(file.name)),
        mapPdfFile,
      ])
    } finally {
      setGeneratingGisMapPdf(false)
    }
  }, [createGisMapPdfFile])

  const persistMissingDeviceSerialNumbers = async () => {
    const updatedDeviceIds: number[] = []
    for (const dev of selectedDevices) {
      const serialNumber = dev.oem_serial_number.trim()
      if (!serialNumber || dev.device_serial_number?.trim()) continue

      await updateDeviceSerialNumber.mutateAsync({
        projectId,
        deviceId: dev.device_id,
        serialNumber,
      })
      updatedDeviceIds.push(dev.device_id)
    }

    if (updatedDeviceIds.length === 0) return
    const updatedIdSet = new Set(updatedDeviceIds)
    setSelectedDevices((prev) =>
      prev.map((dev) =>
        updatedIdSet.has(dev.device_id)
          ? { ...dev, device_serial_number: dev.oem_serial_number.trim() }
          : dev,
      ),
    )
  }

  const handleSaveDraft = async ({
    includeGisMapPdf = false,
  }: {
    includeGisMapPdf?: boolean
  } = {}): Promise<number | null> => {
    if (!selectedConfigId) return null
    setSavingDraft(true)
    try {
      let filesForUpload = uploadedFiles
      await persistMissingDeviceSerialNumbers()
      let claimId = createdClaimId
      if (!claimId) {
        const res = await createClaim.mutateAsync({
          projectId,
          data: {
            claim_config_id: selectedConfigId,
            summary: summary || undefined,
          },
        })
        claimId = res.data.claim_id
        setCreatedClaimId(claimId)
      }

      filesForUpload = await filesWithAutoSavedPdf(claimId)
      setUploadedFiles(filesForUpload)

      // Combine server-side devices (from refetched draft) with the in-memory
      // set of devices we've POSTed during this session to avoid duplicate
      // POSTs across repeated "Save as Draft" presses (the cached draftClaim
      // may not reflect the latest additions yet).
      const alreadyPostedIds = new Set<number>([
        ...(draftClaim?.devices ?? []).map((d) => d.device_id),
        ...submittedDeviceIdsRef.current,
      ])
      for (const dev of selectedDevices) {
        if (alreadyPostedIds.has(dev.device_id)) continue
        await addDevice.mutateAsync({
          projectId,
          claimId: claimId!,
          data: {
            device_id: dev.device_id,
            oem_serial_number: dev.oem_serial_number || undefined,
            oem_part_number: dev.oem_part_number || undefined,
            notes: dev.notes || undefined,
            event_id: dev.event_id ?? undefined,
          },
        })
        submittedDeviceIdsRef.current.add(dev.device_id)
      }

      if (
        includeGisMapPdf ||
        filesForUpload.some((file) => isWarrantyClaimGisMapFilename(file.name))
      ) {
        const mapPdfFile = await createGisMapPdfFile(claimId)
        if (mapPdfFile) {
          filesForUpload = [
            ...filesForUpload.filter(
              (file) => !isWarrantyClaimGisMapFilename(file.name),
            ),
            mapPdfFile,
          ]
          setUploadedFiles(filesForUpload)
        }
      }

      for (const file of filesForUpload) {
        await uploadAttachment.mutateAsync({
          projectId,
          claimId: claimId!,
          file,
        })
      }

      notifications.show({
        title: 'Draft saved',
        message: `Claim #${claimId} saved as draft`,
        color: 'green',
      })
      return claimId
    } catch {
      notifications.show({
        title: 'Error',
        message: 'Failed to save draft',
        color: 'red',
      })
      return null
    } finally {
      setSavingDraft(false)
    }
  }

  const handleSubmitClaim = async () => {
    const claimId = await handleSaveDraft({ includeGisMapPdf: true })
    if (!claimId) return
    setSubmittingClaim(true)
    try {
      await submitClaim.mutateAsync({
        projectId,
        claimId,
        data: {
          email_subject: reviewEmailSubject.trim() || undefined,
          email_body: reviewEmailBody.trim() || undefined,
          to_emails: parseEmailAddressList(toEmails),
          cc_emails: parseEmailAddressList(ccEmails),
          bcc_emails: parseEmailAddressList(bccEmails),
        },
      })
      notifications.show({
        title: 'Claim submitted',
        message: 'The warranty claim has been submitted',
        color: 'green',
      })
      resetAndClose()
    } catch {
      notifications.show({
        title: 'Error',
        message: 'Failed to submit claim',
        color: 'red',
      })
    }
    setSubmittingClaim(false)
  }

  const resetAndClose = () => {
    createContractModalHandlers.close()
    setStep(0)
    setSelectedConfigId(null)
    setCreatedClaimId(null)
    setSummary('')
    setSelectedDevices([])
    setSelectedEventIds([])
    setIncludeRecentlyClosed(false)
    setShowAllDevices(false)
    setShowAddDeviceControls(false)
    eventsAutoPopulatedRef.current = null
    eventCsvControllersRef.current.forEach((controller) => controller.abort())
    eventCsvControllersRef.current.clear()
    eventCsvFileNamesRef.current.clear()
    requestedEventCsvIdsRef.current.clear()
    selectedEventIdsForCsvRef.current.clear()
    setEventCsvStatuses({})
    setUploadedFiles([])
    setCcEmails('')
    setToEmails('')
    reviewCcDefaultAppliedRef.current = false
    setBccEmails('')
    setReviewEmailSubject('')
    setReviewEmailBody('')
    setClaimPdfDraft(null)
    setGeneratingGisMapPdf(false)
    setShowNewConfig(false)
    setEditingConfigId(null)
    setConfigJustCreated(null)
    setOverlayAssistReplaceOpen(false)
    setDeviceTypeFilter(null)
    oemDefaultAppliedRef.current = null
    onClose()
  }

  const projectName = project.data?.name_long ?? 'the project'
  const isEmailSubmission =
    selectedConfig?.default_submission_channel ===
      ClaimSubmissionChannelEnum.EMAIL ||
    selectedConfig?.default_submission_channel ===
      ClaimSubmissionChannelEnum.HYBRID

  const oemName = selectedConfig?.counterparty_name ?? 'OEM'
  const effectiveClaimId = createdClaimId ?? draftClaimId ?? null
  const userEmail = user?.primaryEmailAddress?.emailAddress ?? ''
  const userFullName = user?.fullName ?? ''
  const companyDisplayName =
    companiesForUser?.[0]?.name_long ?? companiesForUser?.[0]?.name_short ?? ''
  const emailSenderDisplay = [userFullName, companyDisplayName]
    .filter(Boolean)
    .join(', ')

  const reviewEmailPreviewHtml = useMemo(
    () =>
      buildClaimSubmissionEmailHtml({
        text: reviewEmailBody.trim() || '(Message is empty - add text above.)',
        projectName,
        claimId: effectiveClaimId,
        counterpartyName: oemName,
        senderCompany: companyDisplayName,
        attachmentNames: uploadedFiles.map((file) => file.name),
        toAddressesDisplay:
          toEmails.trim() || selectedConfig?.default_contact?.trim() || null,
      }),
    [
      companyDisplayName,
      effectiveClaimId,
      oemName,
      projectName,
      reviewEmailBody,
      selectedConfig?.default_contact,
      toEmails,
      uploadedFiles,
    ],
  )

  const todayDateDisplay = useMemo(
    () =>
      new Date().toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      }),
    [],
  )

  const firstIssueDateDisplay = useMemo(() => {
    const [firstStart] = claimEventsForAssist
      .map((event) => event.time_start)
      .filter(Boolean)
      .sort()
    return firstStart ? formatIssueDateForAssist(firstStart) : ''
  }, [claimEventsForAssist])

  const previousClaimExample = useMemo(() => {
    if (!isLastFiledClaimDetailForCurrentProject) return {}
    if (!previousClaimPdfText.trim()) return {}
    return {
      filled_fields: previousClaimPdfText,
    }
  }, [isLastFiledClaimDetailForCurrentProject, previousClaimPdfText])

  const claimAssistContext = useMemo(() => {
    const devicesForAssist = selectedDevices.map((d) => {
      const device = deviceDetailByIdForAssist.get(d.device_id)
      const model = selectedDeviceModelById.get(d.device_model_id ?? -1)
      return {
        device_name: deviceNameForWarrantyAssist(
          d.device_id,
          d.device_name,
          device,
        ),
        device_brand: model?.brand ?? '',
        device_model: model?.model ?? '',
        oem_serial_number: d.oem_serial_number,
        oem_part_number: d.oem_part_number,
        notes: d.notes,
        event_id: d.event_id,
      }
    })

    return {
      project: {
        address: project.data?.address ?? '',
        elevation: project.data?.elevation ?? null,
      },
      project_name: projectName,
      company_name: companyDisplayName,
      user_first_name: user?.firstName ?? '',
      user_last_name: user?.lastName ?? '',
      user_email: userEmail,
      claim_id_display:
        effectiveClaimId != null ? String(effectiveClaimId) : '',
      phone: '',
      summary,
      external_reference: draftClaim?.external_reference ?? '',
      oem_name: oemName,
      today_date_display: todayDateDisplay,
      declaration_date_display: todayDateDisplay,
      first_issue_date_display: firstIssueDateDisplay,
      previous_claim_example: previousClaimExample,
      events: claimEventsForAssist,
      devices: devicesForAssist,
    }
  }, [
    project.data,
    projectName,
    companyDisplayName,
    user?.firstName,
    user?.lastName,
    userEmail,
    effectiveClaimId,
    summary,
    draftClaim?.external_reference,
    oemName,
    todayDateDisplay,
    firstIssueDateDisplay,
    previousClaimExample,
    claimEventsForAssist,
    selectedDevices,
    selectedDeviceModelById,
    deviceDetailByIdForAssist,
  ])

  const claimPdfAssistKey = useMemo(() => {
    if (!matchedContract?.document_url) return null
    return JSON.stringify({
      document_url: matchedContract.document_url,
      claim_context: claimAssistContext,
    })
  }, [matchedContract?.document_url, claimAssistContext])

  const executeClaimPdfAiAssist = useCallback(async () => {
    const annot = pdfAnnotatorRef.current
    if (!annot || !annot.isReady()) {
      notifications.show({
        title: 'PDF not ready',
        message:
          'Wait for the claim form PDF to finish loading, then try again.',
        color: 'yellow',
      })
      return
    }
    const token = await getToken({ template: 'default' })
    if (!token) {
      notifications.show({
        title: 'Sign in required',
        message: 'Could not get a session token for AI assist.',
        color: 'red',
      })
      return
    }
    setAiAssistLoading(true)
    try {
      if (annot.hasAcroForm()) {
        const fields = annot.getAcroFieldSpecs().filter((field) => field.name)
        if (fields.length === 0) {
          notifications.show({
            title: 'No fields',
            message: 'No AcroForm text fields detected on this PDF.',
            color: 'yellow',
          })
          return
        }
        const res = await requestWarrantyClaimPdfAssist(token, {
          body: {
            mode: 'acro',
            claim_context: claimAssistContext,
            acro_fields: fields.map((field) => ({
              field_name: field.name,
              field_type: field.type,
              page: field.page,
              x: field.x,
              y: field.y,
              width: field.width,
              height: field.height,
              rect: field.rect,
              existing_value: field.value,
              nearby_label: field.label ?? null,
              nearby_label_source: field.labelSource ?? null,
            })),
          },
        })
        const vals = res.acro_values ?? {}
        if (Object.keys(vals).length === 0) {
          notifications.show({
            title: 'No suggestions',
            message: 'The model did not return field values to apply.',
            color: 'blue',
          })
          return
        }
        annot.mergeAcroValues(vals)
        notifications.show({
          title: 'Form prefilled',
          message: 'Review and edit fields, then save the PDF when ready.',
          color: 'green',
        })
      } else {
        const pages = await annot.renderPageImagesForAssist(5)
        if (pages.length === 0) {
          notifications.show({
            title: 'PDF not ready',
            message: 'Could not rasterize pages for AI placement.',
            color: 'red',
          })
          return
        }
        const res = await requestWarrantyClaimPdfAssist(token, {
          body: {
            mode: 'vision',
            claim_context: claimAssistContext,
            pages,
          },
        })
        const list = res.annotations ?? []
        if (list.length === 0) {
          notifications.show({
            title: 'No placements',
            message:
              'The model did not suggest text positions. Try the Text tool.',
            color: 'blue',
          })
          return
        }
        annot.clearOverlayAnnotations()
        annot.addAnnotations(
          list.map((a) => ({
            page: a.page,
            x: a.x,
            y: a.y,
            text: a.text,
            fontSize: a.font_size,
          })),
        )
        notifications.show({
          title: 'Suggestions added',
          message:
            'Drag and edit overlays to align with the form, then save the PDF.',
          color: 'green',
        })
      }
    } catch (e: unknown) {
      let msg = 'AI assist failed'
      if (e && typeof e === 'object' && 'response' in e) {
        const r = (e as { response?: { data?: { detail?: unknown } } }).response
        if (r?.data?.detail != null) {
          msg = String(r.data.detail)
        }
      } else if (e instanceof Error) {
        msg = e.message
      }
      notifications.show({
        title: 'AI assist failed',
        message: msg,
        color: 'red',
      })
    } finally {
      setAiAssistLoading(false)
    }
  }, [claimAssistContext, getToken])

  const runClaimPdfAiAssistFromButton = useCallback(() => {
    const annot = pdfAnnotatorRef.current
    if (!annot || !annot.isReady()) {
      notifications.show({
        title: 'PDF not ready',
        message:
          'Wait for the claim form PDF to finish loading, then try again.',
        color: 'yellow',
      })
      return
    }
    if (!annot.hasAcroForm() && annot.hasOverlayAnnotations()) {
      setOverlayAssistReplaceOpen(true)
      return
    }
    void executeClaimPdfAiAssist()
  }, [executeClaimPdfAiAssist])

  const persistClaimPdfDraft = useCallback(() => {
    const state = pdfAnnotatorRef.current?.getState()
    if (!state || !matchedContract?.document_url) return
    setClaimPdfDraft({ fileUrl: matchedContract.document_url, state })
  }, [matchedContract?.document_url])

  const confirmOverlayAssistReplace = useCallback(() => {
    setOverlayAssistReplaceOpen(false)
    pdfAnnotatorRef.current?.clearOverlayAnnotations()
    void executeClaimPdfAiAssist()
  }, [executeClaimPdfAiAssist])

  useEffect(() => {
    if (!opened || step !== 3 || !claimPdfAssistKey) return
    if (aiAssistLoading) return
    if (
      selectedDeviceIdsForAssist.length > 0 &&
      (loadingDeepForAssist || loadingEventsForAssist)
    ) {
      return
    }
    if (
      lastFiledClaim &&
      (loadingLastFiledClaimDetail || previousClaimExampleLoading)
    ) {
      return
    }
    if (lastAutoAssistKeyRef.current === claimPdfAssistKey) return

    let cancelled = false
    let timeoutId: number | null = null

    const maybeRunAssist = () => {
      if (cancelled) return
      const annot = pdfAnnotatorRef.current
      if (!annot?.isReady()) {
        timeoutId = window.setTimeout(maybeRunAssist, 250)
        return
      }
      if (lastAutoAssistKeyRef.current === claimPdfAssistKey) return
      lastAutoAssistKeyRef.current = claimPdfAssistKey
      void executeClaimPdfAiAssist()
    }

    maybeRunAssist()

    return () => {
      cancelled = true
      if (timeoutId != null) {
        window.clearTimeout(timeoutId)
      }
    }
  }, [
    opened,
    step,
    claimPdfAssistKey,
    aiAssistLoading,
    executeClaimPdfAiAssist,
    selectedDeviceIdsForAssist.length,
    loadingDeepForAssist,
    loadingEventsForAssist,
    lastFiledClaim,
    loadingLastFiledClaimDetail,
    previousClaimExampleLoading,
  ])

  const populateReviewEmailDefaults = useCallback(() => {
    setReviewEmailSubject(
      buildDefaultClaimEmailSubject(effectiveClaimId, oemName, projectName),
    )
    setReviewEmailBody(
      buildDefaultClaimEmailBody(
        oemName,
        projectName,
        summary,
        selectedDevices,
        uploadedFiles.length,
        userFullName,
        companyDisplayName,
      ),
    )
    setToEmails(selectedConfig?.default_contact?.trim() ?? '')
    if (!reviewCcDefaultAppliedRef.current && userEmail.trim()) {
      setCcEmails((prev) => {
        const existingEmails = parseEmailAddressList(prev)
        const alreadyCc = existingEmails.some(
          (email) => email.toLowerCase() === userEmail.trim().toLowerCase(),
        )
        if (alreadyCc) return prev
        return [...existingEmails, userEmail.trim()].join(', ')
      })
      reviewCcDefaultAppliedRef.current = true
    }
  }, [
    effectiveClaimId,
    oemName,
    projectName,
    summary,
    selectedDevices,
    uploadedFiles.length,
    userEmail,
    userFullName,
    companyDisplayName,
    selectedConfig?.default_contact,
  ])

  const goToStep = useCallback(
    (next: number) => {
      if (step === 3 && next !== 3) {
        persistClaimPdfDraft()
      }
      if (step === 3 && next > 3) {
        void addFilledPdfToAttachments()
      }
      if (next === 5 && step !== 5) {
        populateReviewEmailDefaults()
      }
      setStep(next)
    },
    [
      step,
      persistClaimPdfDraft,
      populateReviewEmailDefaults,
      addFilledPdfToAttachments,
    ],
  )

  useEffect(() => {
    if (step !== 4) return
    if (
      loadingDeepForAssist ||
      loadingEventsForAssist ||
      loadingDeviceAncestorsForAssist
    ) {
      return
    }
    void addGisMapPdfToAttachments()
  }, [
    step,
    loadingDeepForAssist,
    loadingEventsForAssist,
    loadingDeviceAncestorsForAssist,
    addGisMapPdfToAttachments,
  ])

  useEffect(() => {
    const id = createdClaimId ?? draftClaimId
    if (id == null || step !== 5) return
    setReviewEmailSubject((prev) =>
      prev.includes('(pending)') ? prev.replace('(pending)', `#${id}`) : prev,
    )
  }, [createdClaimId, draftClaimId, step])

  const canProceed = (s: number) => {
    if (s === 0) return !!selectedConfigId
    return true
  }

  const canCreateProjectDocuments =
    userHasProjectPermission(userPermissions.data, 'create:documents') ||
    (userSelf.data?.user_type_id ?? 3) <= 2
  const aiAssistProgressValue =
    ((aiAssistStepIndex + 1) / AI_ASSIST_STEPS.length) * 100
  const previousStep = Math.max(0, step - 1)
  const nextStep = step + 1
  const handleBackClick = () => goToStep(previousStep)
  const handleNextClick = () => goToStep(nextStep)

  return (
    <>
      <ClaimGisMapPdf
        ref={gisMapPdfRef}
        enabled={opened && selectedDevices.length > 0}
        projectName={projectName}
        claimId={effectiveClaimId}
        oemName={oemName}
        summary={summary}
        selectedDevices={selectedDevices}
        selectedDeviceDetails={devicesDeepForAssist ?? []}
        selectedDeviceAncestorDetails={selectedDeviceAncestorDetails ?? []}
        selectedEvents={selectedDeviceEventsForAssist ?? []}
        siteDevices={allProjectDevicesForOemDefault ?? []}
        projectPolygon={project.data?.polygon ?? null}
      />
      <Modal
        opened={opened}
        onClose={resetAndClose}
        title={draftClaimId ? 'Edit Draft Claim' : 'Submit New Warranty Claim'}
        size={900}
      >
        <Stepper
          active={step}
          onStepClick={(nextStep) => {
            if (nextStep === 0 || selectedConfigId != null) {
              goToStep(nextStep)
            }
          }}
          size="xs"
        >
          {/* Step 0: Select OEM */}
          <Stepper.Step label="OEM">
            <Stack gap="md" mt="md">
              {hasConfigs && !showNewConfig && (
                <>
                  <Stack gap={6}>
                    <Text size="sm" fw={500}>
                      Select OEM / Counterparty
                    </Text>
                    <Text size="xs" c="dimmed">
                      Choose an OEM you&apos;ve previously configured for this
                      project
                    </Text>
                    <Radio.Group
                      value={
                        selectedConfigId != null ? String(selectedConfigId) : ''
                      }
                      onChange={(v) =>
                        setSelectedConfigId(v ? Number(v) : null)
                      }
                    >
                      <Stack gap="xs" mt="xs">
                        {configs?.map((c) => (
                          <Radio
                            key={c.claim_config_id}
                            value={String(c.claim_config_id)}
                            label={
                              c.counterparty_name ||
                              `Config #${c.claim_config_id}`
                            }
                          />
                        ))}
                      </Stack>
                    </Radio.Group>
                  </Stack>
                  {selectedConfig && (
                    <Stack
                      gap={6}
                      p="md"
                      style={{
                        border: `1px solid var(--mantine-color-${
                          isDarkMode ? 'dark-4' : 'gray-3'
                        })`,
                        borderRadius: 8,
                        background: `var(--mantine-color-${
                          isDarkMode ? 'dark-6' : 'gray-0'
                        })`,
                      }}
                    >
                      <Group justify="space-between">
                        <Text size="md" fw={600}>
                          {selectedConfig.counterparty_name}
                        </Text>
                        <ActionIcon
                          variant="subtle"
                          size="sm"
                          onClick={handleEditConfig}
                        >
                          <IconEdit size={14} />
                        </ActionIcon>
                      </Group>
                      <Text size="sm" c="dimmed">
                        Channel: {selectedConfig.default_submission_channel}
                        {selectedConfig.default_contact &&
                          ` · Contact: ${selectedConfig.default_contact}`}
                        {selectedConfig.portal_url &&
                          ` · Portal: ${selectedConfig.portal_url}`}
                      </Text>
                      {configJustCreated && (
                        <Text size="xs" c="green">
                          Configuration saved successfully.
                        </Text>
                      )}
                    </Stack>
                  )}
                  {!configJustCreated && (
                    <Button
                      variant="subtle"
                      size="xs"
                      onClick={() => {
                        setEditingConfigId(null)
                        setNewConfigCounterpartyId(null)
                        setNewConfigChannel(ClaimSubmissionChannelEnum.EMAIL)
                        setNewConfigContact('')
                        setNewConfigPortal('')
                        setShowNewConfig(true)
                      }}
                    >
                      + Add new OEM configuration
                    </Button>
                  )}
                </>
              )}

              {(!hasConfigs || showNewConfig) && (
                <Stack
                  gap="sm"
                  p="sm"
                  style={{
                    border: '1px solid var(--mantine-color-gray-3)',
                    borderRadius: 8,
                  }}
                >
                  <Text fw={500} size="sm">
                    {editingConfigId
                      ? 'Edit OEM Configuration'
                      : hasConfigs
                        ? 'New OEM Configuration'
                        : 'Set up OEM Configuration'}
                  </Text>
                  {!hasConfigs && (
                    <Text size="xs" c="dimmed">
                      No OEM configurations exist for this project yet. Add one
                      to get started.
                    </Text>
                  )}
                  <OemConfigForm
                    values={{
                      counterpartyId: newConfigCounterpartyId,
                      channel: newConfigChannel,
                      contact: newConfigContact,
                      portal: newConfigPortal,
                    }}
                    onChange={(next) => {
                      setNewConfigCounterpartyId(next.counterpartyId)
                      setNewConfigChannel(next.channel)
                      setNewConfigContact(next.contact)
                      setNewConfigPortal(next.portal)
                    }}
                  />
                  <Group>
                    <Button
                      size="xs"
                      onClick={handleCreateConfig}
                      loading={createClaimConfig.isPending}
                      disabled={Boolean(newConfigContactError)}
                    >
                      Save Config
                    </Button>
                    {hasConfigs && (
                      <Button
                        size="xs"
                        variant="subtle"
                        onClick={() => setShowNewConfig(false)}
                      >
                        Cancel
                      </Button>
                    )}
                  </Group>
                </Stack>
              )}
            </Stack>
          </Stepper.Step>

          {/* Step 1: Events (optional) */}
          <Stepper.Step label="Events" allowStepSelect={!!selectedConfigId}>
            <Stack gap="md" mt="md">
              <Stack gap={4}>
                <Text size="sm" fw={500}>
                  Select related event(s) for this claim (optional)
                </Text>
                <Text size="xs" c="dimmed">
                  Events on devices supplied by {oemName}. Selecting events
                  auto-fills the affected devices on the next step. Skip to add
                  devices manually.
                </Text>
              </Stack>

              <Group justify="space-between" wrap="wrap">
                <Switch
                  label="Include recently closed events (last 90 days)"
                  size="sm"
                  checked={includeRecentlyClosed}
                  onChange={(e) =>
                    setIncludeRecentlyClosed(e.currentTarget.checked)
                  }
                />
                {selectedEventIds.length > 0 && (
                  <Button
                    size="xs"
                    variant="subtle"
                    onClick={() => setSelectedEventIds([])}
                  >
                    Clear selection ({selectedEventIds.length})
                  </Button>
                )}
              </Group>

              {oemDeviceLookupLoading ? (
                <Group gap="sm">
                  <Loader size="xs" />
                  <Text size="sm" c="dimmed">
                    Loading Events for {oemName}…
                  </Text>
                </Group>
              ) : oemDeviceIds.length === 0 ? (
                <Alert variant="light" color="gray">
                  No devices on this project are linked to {oemName}. Continue
                  to add devices manually.
                </Alert>
              ) : oemEventsLoading ? (
                <Group gap="sm">
                  <Loader size="xs" />
                  <Text size="sm" c="dimmed">
                    Loading events for {oemName}…
                  </Text>
                </Group>
              ) : !oemEvents || oemEvents.length === 0 ? (
                <Alert variant="light" color="gray">
                  No{' '}
                  {includeRecentlyClosed ? 'open or recently closed' : 'open'}{' '}
                  events found on {oemName} devices. Continue to add devices
                  manually.
                </Alert>
              ) : (
                <Table withTableBorder>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th w={40} />
                      <Table.Th w={70}>Event</Table.Th>
                      <Table.Th>Device</Table.Th>
                      <Table.Th>Failure mode</Table.Th>
                      <Table.Th w={120}>Warranty claim</Table.Th>
                      <Table.Th w={170}>Time</Table.Th>
                      <Table.Th w={80}>Status</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {[...oemEvents]
                      .sort((a, b) =>
                        a.time_start < b.time_start
                          ? 1
                          : a.time_start > b.time_start
                            ? -1
                            : 0,
                      )
                      .map((ev) => {
                        const checked = selectedEventIds.includes(ev.event_id)
                        const startYmd = ev.time_start.slice(0, 10)
                        const endYmd = ev.time_end
                          ? ev.time_end.slice(0, 10)
                          : null
                        const range = endYmd
                          ? startYmd === endYmd
                            ? startYmd
                            : `${startYmd} → ${endYmd}`
                          : `${startYmd} → ongoing`
                        const deviceLabel =
                          ev.device_name_full ||
                          ev.device?.name_long ||
                          ev.device?.name_short ||
                          `Device ${ev.device_id}`
                        const relatedClaimIds =
                          claimIdsByEventId.get(ev.event_id) ?? []
                        return (
                          <Table.Tr
                            key={ev.event_id}
                            style={{ cursor: 'pointer' }}
                            onClick={() => {
                              setSelectedEventIds((prev) =>
                                prev.includes(ev.event_id)
                                  ? prev.filter((i) => i !== ev.event_id)
                                  : [...prev, ev.event_id],
                              )
                              eventsAutoPopulatedRef.current = null
                            }}
                          >
                            <Table.Td>
                              <Checkbox
                                checked={checked}
                                onChange={() => {}}
                                aria-label={`Select event ${ev.event_id}`}
                              />
                            </Table.Td>
                            <Table.Td>
                              <Text size="sm">#{ev.event_id}</Text>
                            </Table.Td>
                            <Table.Td>
                              <Text size="sm">{deviceLabel}</Text>
                            </Table.Td>
                            <Table.Td>
                              <Text size="sm">
                                {ev.failure_mode?.name_long ?? '—'}
                              </Text>
                            </Table.Td>
                            <Table.Td>
                              <Text
                                size="sm"
                                c={
                                  relatedClaimIds.length > 0 ? 'red' : 'dimmed'
                                }
                              >
                                {relatedClaimIds.length > 0
                                  ? relatedClaimIds
                                      .map((claimId) => `#${claimId}`)
                                      .join(', ')
                                  : '—'}
                              </Text>
                            </Table.Td>
                            <Table.Td>
                              <Text size="xs" c="dimmed">
                                {range}
                              </Text>
                            </Table.Td>
                            <Table.Td>
                              <Text
                                size="xs"
                                c={ev.time_end ? 'dimmed' : 'green'}
                              >
                                {ev.time_end ? 'Closed' : 'Open'}
                              </Text>
                            </Table.Td>
                          </Table.Tr>
                        )
                      })}
                  </Table.Tbody>
                </Table>
              )}

              <TextInput
                label="Claim Summary"
                description="Short description of the issue being claimed"
                placeholder="e.g. Inverter failure — Unit #14"
                value={summary}
                onChange={(e) => setSummary(e.currentTarget.value)}
              />
            </Stack>
          </Stepper.Step>

          {/* Step 2: Device Lookup */}
          <Stepper.Step label="Devices" allowStepSelect={!!selectedConfigId}>
            <Stack gap="md" mt="md">
              {selectedConfig && (
                <Paper withBorder p="sm" radius="md">
                  {!allProjectDevicesForOemDefault ||
                  !allProjectDeviceModels ? (
                    <Group gap="sm">
                      <Loader size="xs" />
                      <Text size="sm" c="dimmed">
                        Loading device models for {oemName}…
                      </Text>
                    </Group>
                  ) : oemDeviceModelGroups.length === 0 ? (
                    <Text size="sm" c="dimmed">
                      No device models on this project are linked to {oemName}.
                    </Text>
                  ) : (
                    <Group gap="lg" wrap="wrap">
                      {oemDeviceModelGroups.map(
                        ({ model, projectCount, selectedCount }) => (
                          <Group
                            key={model.device_model_id}
                            gap="sm"
                            wrap="nowrap"
                            align="center"
                          >
                            <Image
                              src={getDeviceModelImageUrl(
                                model.device_model_id,
                              )}
                              fallbackSrc={getDeviceModelImagePublicUrl(
                                model.device_model_id,
                              )}
                              alt={`${model.brand} ${model.model}`}
                              w={48}
                              h={48}
                              fit="contain"
                              radius="sm"
                              style={{ flexShrink: 0 }}
                            />
                            <Stack gap={0}>
                              <Text size="sm" fw={600}>
                                {model.brand}
                              </Text>
                              <Text size="xs" c="dimmed">
                                {model.model}
                              </Text>
                              <Text size="xs" c="dimmed">
                                {selectedCount > 0
                                  ? `${selectedCount} selected · ${projectCount} on site`
                                  : `${projectCount} on site`}
                              </Text>
                            </Stack>
                          </Group>
                        ),
                      )}
                    </Group>
                  )}
                </Paper>
              )}
              {selectedDevices.length > 0 && (
                <Table withTableBorder>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Device</Table.Th>
                      <Table.Th w={240}>Related event</Table.Th>
                      <Table.Th>Serial #</Table.Th>
                      <Table.Th>Part #</Table.Th>
                      <Table.Th>Notes</Table.Th>
                      <Table.Th w={40} />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {selectedDevices.map((d) => (
                      <Table.Tr key={d.device_id}>
                        <Table.Td>
                          <Text size="sm">{d.device_name}</Text>
                        </Table.Td>
                        <Table.Td>
                          <DeviceEventSelect
                            projectId={projectId}
                            deviceId={d.device_id}
                            value={d.event_id}
                            initialEvents={
                              eventsForDeviceSelectByDeviceId.get(
                                d.device_id,
                              ) ?? []
                            }
                            onChange={(eventId) =>
                              setSelectedDevices((prev) =>
                                prev.map((row) =>
                                  row.device_id === d.device_id
                                    ? { ...row, event_id: eventId }
                                    : row,
                                ),
                              )
                            }
                          />
                        </Table.Td>
                        <Table.Td>
                          <TextInput
                            size="xs"
                            placeholder="OEM serial"
                            value={d.oem_serial_number}
                            onChange={(e) =>
                              updateDeviceField(
                                d.device_id,
                                'oem_serial_number',
                                e.currentTarget.value,
                              )
                            }
                          />
                        </Table.Td>
                        <Table.Td>
                          <TextInput
                            size="xs"
                            placeholder="Part number"
                            value={d.oem_part_number}
                            onChange={(e) =>
                              updateDeviceField(
                                d.device_id,
                                'oem_part_number',
                                e.currentTarget.value,
                              )
                            }
                          />
                        </Table.Td>
                        <Table.Td>
                          <TextInput
                            size="xs"
                            placeholder="Notes"
                            value={d.notes}
                            onChange={(e) =>
                              updateDeviceField(
                                d.device_id,
                                'notes',
                                e.currentTarget.value,
                              )
                            }
                          />
                        </Table.Td>
                        <Table.Td>
                          <ActionIcon
                            color="red"
                            variant="subtle"
                            size="sm"
                            onClick={() => handleRemoveDevice(d.device_id)}
                          >
                            <IconTrash size={14} />
                          </ActionIcon>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}

              {selectedDevices.length === 0 && (
                <Alert variant="light" color="gray">
                  No devices selected yet. Select related events in the previous
                  step or add a device manually.
                </Alert>
              )}

              {!showAddDeviceControls && (
                <Group justify="flex-end">
                  <Button
                    size="xs"
                    variant="light"
                    leftSection={<IconPlus size={14} />}
                    onClick={() => setShowAddDeviceControls(true)}
                  >
                    {selectedDevices.length > 0
                      ? 'Add another device'
                      : 'Add device'}
                  </Button>
                </Group>
              )}

              {showAddDeviceControls && (
                <Stack gap="xs">
                  <Group>
                    <Select
                      label="Filter by device type"
                      description="Narrow the device list by type"
                      placeholder="All types"
                      data={availableDeviceTypes}
                      value={deviceTypeFilter}
                      onChange={setDeviceTypeFilter}
                      clearable
                      style={{ flex: 1 }}
                    />
                    <Select
                      label="Search and add device"
                      description="Select devices affected by this claim"
                      placeholder="Search devices..."
                      data={deviceOptions}
                      value={deviceSearch}
                      onChange={handleAddDevice}
                      searchable
                      clearable
                      style={{ flex: 2 }}
                    />
                  </Group>
                  {oemDeviceModelIdSet && oemDeviceModelIdSet.size > 0 && (
                    <Checkbox
                      size="xs"
                      label={`Show devices from all OEMs (default: ${oemName} only)`}
                      checked={showAllDevices}
                      onChange={(e) =>
                        setShowAllDevices(e.currentTarget.checked)
                      }
                    />
                  )}
                </Stack>
              )}
            </Stack>
          </Stepper.Step>

          {/* Step 3: Warranty Claim Form PDF */}
          <Stepper.Step label="Claim Form" allowStepSelect={!!selectedConfigId}>
            <Stack gap="md" mt="md">
              {!hasMatchedClaimFormPdf && (
                <>
                  <List type="ordered" size="sm" c="dimmed" spacing="xs">
                    <List.Item>
                      Upload the OEM warranty claim PDF form to this project
                      (blank or filled).
                    </List.Item>
                    <List.Item>
                      Open <strong>Create new contract</strong>, pick that PDF,
                      run analysis, and save it with a <strong>warranty</strong>{' '}
                      contract category so it is treated as your warranty claim
                      form. When the contract OEM matches the OEM for this
                      claim, the form appears in the section below.
                    </List.Item>
                  </List>
                  <Group align="flex-start" wrap="wrap">
                    <ProjectDocumentUploadButton
                      projectId={projectId}
                      uploadMutation={uploadProjectDocument}
                      disabled={!canCreateProjectDocuments}
                      buttonLabel="Upload warranty claim PDF"
                    />
                    <Button
                      leftSection={<IconPlus size={16} />}
                      variant="light"
                      onClick={createContractModalHandlers.open}
                    >
                      Create new contract
                    </Button>
                  </Group>
                </>
              )}
              {matchedContract ? (
                <>
                  {matchedContract.document_url ? (
                    <Stack gap="sm">
                      <Group justify="space-between" align="flex-start">
                        <Button
                          size="xs"
                          variant="light"
                          leftSection={<IconSparkles size={16} />}
                          loading={aiAssistLoading}
                          disabled={
                            (selectedDeviceIdsForAssist.length > 0 &&
                              (loadingDeepForAssist ||
                                loadingEventsForAssist)) ||
                            (lastFiledClaim != null &&
                              (loadingLastFiledClaimDetail ||
                                previousClaimExampleLoading))
                          }
                          onClick={() => void runClaimPdfAiAssistFromButton()}
                        >
                          Auto-fill with AI
                        </Button>
                      </Group>
                      {aiAssistLoading && (
                        <Paper
                          p="md"
                          radius="md"
                          withBorder
                          bg="var(--mantine-color-blue-light)"
                        >
                          <Stack gap="sm">
                            <Group align="flex-start" gap="md" wrap="nowrap">
                              <Loader type="dots" size="sm" />
                              <Stack gap={6} style={{ flex: 1, minWidth: 0 }}>
                                <Text size="sm" fw={600}>
                                  Filling your warranty claim form…
                                </Text>
                                <Text size="xs" c="dimmed">
                                  The AI is working through the claim context,
                                  timeseries data, and OEM PDF fields. This
                                  usually takes a few seconds — please keep this
                                  step open.
                                </Text>
                              </Stack>
                            </Group>
                            <Progress
                              value={aiAssistProgressValue}
                              striped
                              animated
                              radius="xl"
                              size="sm"
                            />
                            <Stack gap={4}>
                              {AI_ASSIST_STEPS.map((label, index) => {
                                const isComplete = index < aiAssistStepIndex
                                const isActive = index === aiAssistStepIndex

                                return (
                                  <Group
                                    key={label}
                                    gap="xs"
                                    wrap="nowrap"
                                    c={isActive ? 'blue' : undefined}
                                    opacity={isComplete || isActive ? 1 : 0.55}
                                  >
                                    {isComplete ? (
                                      <IconCheck size={14} />
                                    ) : isActive ? (
                                      <Loader size={12} type="oval" />
                                    ) : (
                                      <Box
                                        w={12}
                                        h={12}
                                        style={{
                                          borderRadius: 999,
                                          border:
                                            '1px solid var(--mantine-color-gray-5)',
                                        }}
                                      />
                                    )}
                                    <Text size="xs" fw={isActive ? 600 : 400}>
                                      {label}
                                    </Text>
                                  </Group>
                                )
                              })}
                            </Stack>
                          </Stack>
                        </Paper>
                      )}
                      <PdfAnnotator
                        ref={pdfAnnotatorRef}
                        fileUrl={matchedContract.document_url}
                        initialState={
                          claimPdfDraft?.fileUrl ===
                          matchedContract.document_url
                            ? claimPdfDraft.state
                            : null
                        }
                      />
                    </Stack>
                  ) : (
                    <Text size="sm" c="dimmed">
                      No PDF document attached to this contract.
                    </Text>
                  )}
                </>
              ) : (
                <Alert variant="light" color="yellow">
                  No Warranty Claim Form contract found for the selected OEM.
                  Upload the PDF and add it as a contract to enable autofill.
                </Alert>
              )}
            </Stack>
          </Stepper.Step>

          {/* Step 4: Attachments */}
          <Stepper.Step
            label="Attachments"
            allowStepSelect={!!selectedConfigId}
          >
            <Stack gap="md" mt="md">
              <Dropzone
                onDrop={(files) =>
                  setUploadedFiles((prev) => [...prev, ...files])
                }
                onReject={() =>
                  notifications.show({
                    title: 'Upload rejected',
                    message: 'One or more files were rejected',
                    color: 'red',
                  })
                }
                maxSize={CLAIM_ATTACHMENT_MAX_SIZE_BYTES}
              >
                <Group
                  justify="center"
                  gap="xl"
                  mih={120}
                  style={{ pointerEvents: 'none' }}
                >
                  <Dropzone.Accept>
                    <IconUpload size={40} stroke={1.5} />
                  </Dropzone.Accept>
                  <Dropzone.Reject>
                    <IconX size={40} stroke={1.5} />
                  </Dropzone.Reject>
                  <Dropzone.Idle>
                    <IconFile size={40} stroke={1.5} />
                  </Dropzone.Idle>
                  <div>
                    <Text size="lg" inline>
                      Drag files here or click to select
                    </Text>
                    <Text size="sm" c="dimmed" inline mt={7}>
                      Max 40 MB per file
                    </Text>
                  </div>
                </Group>
              </Dropzone>

              {generatingGisMapPdf && (
                <Group gap="xs">
                  <Loader size="xs" />
                  <Text size="sm" c="dimmed">
                    Generating GIS map PDF...
                  </Text>
                </Group>
              )}

              {uploadedFiles.length > 0 && (
                <Stack gap="xs">
                  {uploadedFiles.map((f, i) => (
                    <Group key={`${f.name}-${i}`} justify="space-between">
                      <Text size="sm">{f.name}</Text>
                      <Group gap={4} wrap="nowrap">
                        <ActionIcon
                          variant="subtle"
                          size="sm"
                          aria-label={`Download ${f.name}`}
                          onClick={() => triggerDownloadFromLocalFile(f)}
                        >
                          <IconDownload size={14} />
                        </ActionIcon>
                        <ActionIcon
                          color="red"
                          variant="subtle"
                          size="sm"
                          aria-label={`Remove ${f.name}`}
                          onClick={() =>
                            setUploadedFiles((prev) =>
                              prev.filter((_, idx) => idx !== i),
                            )
                          }
                        >
                          <IconTrash size={14} />
                        </ActionIcon>
                      </Group>
                    </Group>
                  ))}
                </Stack>
              )}

              <Anchor
                href={`/projects/${projectId}/data-browsing`}
                target="_blank"
                size="sm"
              >
                <Group component="span" gap={4} wrap="nowrap">
                  <span>Attach additional timeseries data</span>
                  <IconExternalLink size={14} />
                </Group>
              </Anchor>
            </Stack>
          </Stepper.Step>

          {/* Step 5: Preview & Submit */}
          <Stepper.Step label="Review" allowStepSelect={!!selectedConfigId}>
            <Stack gap="md" mt="md">
              {isEmailSubmission ? (
                <Stack gap="md">
                  <Stack gap="xs">
                    <Group gap="md" grow align="flex-start">
                      <ClaimEmailFieldRow
                        label="From"
                        fieldId="claim-email-from"
                      >
                        <TextInput
                          readOnly
                          disabled
                          value={emailSenderDisplay || '(sender unavailable)'}
                        />
                      </ClaimEmailFieldRow>
                      <ClaimEmailFieldRow
                        label="To"
                        fieldId="claim-email-to"
                        hint={
                          'Primary OEM address(es); add more separated by comma, ' +
                          'space, or semicolon. If empty, the OEM default from the ' +
                          'claim configuration is used when sending.'
                        }
                      >
                        <TextInput
                          value={toEmails}
                          onChange={(e) => setToEmails(e.currentTarget.value)}
                          placeholder={
                            selectedConfig?.default_contact?.trim() ||
                            'OEM email address(es)'
                          }
                        />
                      </ClaimEmailFieldRow>
                    </Group>
                    <Group gap="md" grow align="flex-start">
                      <ClaimEmailFieldRow
                        label="Cc"
                        fieldId="claim-email-cc"
                        hint="Comma, space, or semicolon separated."
                      >
                        <TextInput
                          value={ccEmails}
                          onChange={(e) => setCcEmails(e.currentTarget.value)}
                          placeholder="Optional CC addresses"
                        />
                      </ClaimEmailFieldRow>
                      <ClaimEmailFieldRow
                        label="Bcc"
                        fieldId="claim-email-bcc"
                        hint="Comma, space, or semicolon separated."
                      >
                        <TextInput
                          value={bccEmails}
                          onChange={(e) => setBccEmails(e.currentTarget.value)}
                          placeholder="Optional BCC addresses"
                        />
                      </ClaimEmailFieldRow>
                    </Group>
                    <ClaimEmailFieldRow
                      label="Subject"
                      fieldId="claim-email-subject"
                      hint={CLAIM_EMAIL_SUBJECT_HINT}
                    >
                      <TextInput
                        value={reviewEmailSubject}
                        onChange={(e) =>
                          setReviewEmailSubject(e.currentTarget.value)
                        }
                      />
                    </ClaimEmailFieldRow>
                  </Stack>

                  <Group gap="sm" align="flex-start" wrap="nowrap">
                    <Text
                      component="label"
                      htmlFor="claim-email-message"
                      size="sm"
                      fw={500}
                      style={{
                        width: CLAIM_EMAIL_LABEL_COL_W,
                        flexShrink: 0,
                        paddingTop: 6,
                      }}
                    >
                      Message
                    </Text>
                    <Box style={{ flex: 1, minWidth: 0 }}>
                      <Tooltip
                        label={CLAIM_EMAIL_BODY_TOOLTIP}
                        multiline
                        w={300}
                        position="top-start"
                      >
                        <Textarea
                          id="claim-email-message"
                          placeholder="Email body"
                          rows={5}
                          value={reviewEmailBody}
                          onChange={(e) =>
                            setReviewEmailBody(e.currentTarget.value)
                          }
                        />
                      </Tooltip>
                    </Box>
                  </Group>

                  <Text fw={600} size="sm">
                    Preview
                  </Text>
                  <Paper withBorder radius="md" style={{ overflow: 'hidden' }}>
                    <iframe
                      title="Warranty claim email preview"
                      srcDoc={reviewEmailPreviewHtml}
                      style={{
                        width: '100%',
                        height: 360,
                        border: 0,
                        display: 'block',
                      }}
                    />
                  </Paper>
                </Stack>
              ) : (
                <Stack gap="sm">
                  <Text fw={500}>Claim Summary</Text>
                  <Alert variant="light" color="blue">
                    This claim will be submitted via{' '}
                    <strong>
                      {selectedConfig?.default_submission_channel ??
                        ClaimSubmissionChannelEnum.PORTAL}
                    </strong>
                    .
                    {selectedConfig?.portal_url && (
                      <>
                        {' '}
                        Portal:{' '}
                        <Anchor
                          href={selectedConfig.portal_url}
                          target="_blank"
                          size="sm"
                        >
                          {selectedConfig.portal_url}
                        </Anchor>
                      </>
                    )}
                  </Alert>
                  <Table withTableBorder>
                    <Table.Tbody>
                      <Table.Tr>
                        <Table.Td fw={500}>OEM</Table.Td>
                        <Table.Td>
                          {selectedConfig?.counterparty_name ?? '—'}
                        </Table.Td>
                      </Table.Tr>
                      <Table.Tr>
                        <Table.Td fw={500}>Summary</Table.Td>
                        <Table.Td>{summary || '—'}</Table.Td>
                      </Table.Tr>
                      <Table.Tr>
                        <Table.Td fw={500}>Devices</Table.Td>
                        <Table.Td>{selectedDevices.length} device(s)</Table.Td>
                      </Table.Tr>
                      <Table.Tr>
                        <Table.Td fw={500}>Attachments</Table.Td>
                        <Table.Td>{uploadedFiles.length} file(s)</Table.Td>
                      </Table.Tr>
                    </Table.Tbody>
                  </Table>
                </Stack>
              )}
              {(uploadedFiles.length > 0 || generatingGisMapPdf) && (
                <Stack gap="xs" mt="md">
                  <Text fw={600} size="sm">
                    Attachments ({uploadedFiles.length}
                    {generatingGisMapPdf ? ', generating GIS map...' : ''})
                  </Text>
                  <Text size="xs" c="dimmed">
                    Download copies here before submit if you want to review
                    them locally.
                  </Text>
                  {uploadedFiles.map((f, i) => (
                    <Group
                      key={`review-attach-${f.name}-${i}`}
                      justify="space-between"
                    >
                      <Text size="sm">{f.name}</Text>
                      <ActionIcon
                        variant="subtle"
                        size="sm"
                        aria-label={`Download ${f.name}`}
                        onClick={() => triggerDownloadFromLocalFile(f)}
                      >
                        <IconDownload size={14} />
                      </ActionIcon>
                    </Group>
                  ))}
                </Stack>
              )}
            </Stack>
          </Stepper.Step>

          <Stepper.Completed>
            <Stack align="center" mt="xl" gap="sm">
              <Text>Claim submitted successfully!</Text>
              <Text size="sm" c="dimmed" ta="center" maw={420}>
                Open this claim from the warranty list to download attachments
                anytime.
              </Text>
            </Stack>
          </Stepper.Completed>
        </Stepper>

        {step <= 5 && (
          <Group justify="space-between" mt="xl">
            <Button
              variant="default"
              onClick={handleBackClick}
              disabled={step === 0}
            >
              Back
            </Button>
            <Group>
              {step === 5 && (
                <>
                  <Button
                    variant="light"
                    onClick={() => void handleSaveDraft()}
                    loading={savingDraft}
                    disabled={submittingClaim}
                  >
                    Save as Draft
                  </Button>
                  <Button
                    onClick={handleSubmitClaim}
                    loading={submittingClaim}
                    disabled={savingDraft}
                  >
                    Submit Claim
                  </Button>
                </>
              )}
              {step < 5 && (
                <Button
                  onClick={handleNextClick}
                  disabled={
                    !canProceed(step) || (step === 4 && generatingGisMapPdf)
                  }
                >
                  Next
                </Button>
              )}
            </Group>
          </Group>
        )}
      </Modal>
      <Modal
        opened={overlayAssistReplaceOpen}
        onClose={() => setOverlayAssistReplaceOpen(false)}
        title="Replace AI text on the form?"
        size="md"
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            Running auto-fill again will delete every text overlay on this flat
            PDF, then run AI to place new text. This does not apply to fillable
            (AcroForm) fields.
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button
              variant="default"
              onClick={() => setOverlayAssistReplaceOpen(false)}
            >
              Cancel
            </Button>
            <Button onClick={confirmOverlayAssistReplace}>
              Delete overlays and run AI
            </Button>
          </Group>
        </Stack>
      </Modal>
      <CreateContractModal
        opened={createContractModalOpened}
        onClose={createContractModalHandlers.close}
      />
    </>
  )
}
