import { useGetUserSelf } from '@/api/v1/admin/users'
import {
  PVModule,
  PVModuleFromPAN,
  useCreateOrUpdatePVModuleMutation,
  useGetPVModuleDetails,
  useGetPVModuleIdsByManufacturerAndModel,
  useGetProximalPVModuleManufacturers,
  useGetProximalPVModuleModels,
  useParsePANfileMutation,
} from '@/api/v1/operational/pv_modules'
import {
  useGetCECPVModuleIdsByManufacturerAndModel,
  useGetCECPVModuleInProximalFormat,
  useGetCECPVModuleManufacturers,
  useGetCECPVModuleModels,
} from '@/api/v1/operational/pv_modules_cec'
import EquipmentFilter from '@/components/EquipmentFilter'
import { PageTitle } from '@/components/PageTitle'
import ConfirmationModal from '@/components/modals/ConfirmationModal'
import {
  Alert,
  Button,
  Center,
  Container,
  Divider,
  FileInput,
  Grid,
  Group,
  Loader,
  NumberInput,
  Paper,
  Select,
  Space,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconCheck,
  IconRefresh,
  IconUpload,
} from '@tabler/icons-react'
import axios from 'axios'
import { useEffect, useMemo, useRef, useState } from 'react'

const FIELD_LABELS: Record<string, string> = {
  half_cut: 'Half Cut',
  frame_overhang: 'Frame Overhang',
  alpha_isc: 'Alpha Isc (Absolute)',
  alpha_isc_relative: 'Alpha Isc (Relative)',
  beta_voc: 'Beta Voc (Absolute)',
  beta_voc_relative: 'Beta Voc (Relative)',
}

type ValidationIssue = {
  loc?: Array<string | number>
  msg?: string
}

const formatFieldLabel = (field: string) => {
  if (FIELD_LABELS[field]) {
    return FIELD_LABELS[field]
  }

  return field
    .split('_')
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(' ')
}

const getSubmitErrorMessage = (error: unknown) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail as unknown

    if (error.response?.status === 422) {
      if (Array.isArray(detail)) {
        const issues = detail
          .map((item) => item as ValidationIssue)
          .filter(
            (item) => Array.isArray(item.loc) && typeof item.msg === 'string',
          )
          .map((item) => {
            const locParts = item.loc
              ?.filter((locPart) => typeof locPart === 'string')
              .filter((locPart) => locPart !== 'body')
            const field = locParts?.[locParts.length - 1]
            const fieldLabel =
              typeof field === 'string' ? formatFieldLabel(field) : 'Request'
            return `${fieldLabel}: ${item.msg}`
          })

        if (issues.length > 0) {
          return `Validation failed: ${issues.join(' | ')}`
        }
      }

      if (typeof detail === 'string') {
        return `Validation failed: ${detail}`
      }

      return 'Validation failed. Check required fields and value formats.'
    }

    if (typeof detail === 'string') {
      return detail
    }
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Failed to save module configuration'
}

const getPANUploadErrorMessage = (error: unknown) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail as unknown

    if (typeof detail === 'string' && detail.trim().length > 0) {
      return detail
    }

    if (Array.isArray(detail)) {
      const issues = detail
        .map((item) => {
          if (typeof item === 'string') {
            return item
          }

          if (item && typeof item === 'object') {
            const issue = item as ValidationIssue
            return typeof issue.msg === 'string' ? issue.msg : null
          }

          return null
        })
        .filter((item): item is string => Boolean(item))

      if (issues.length > 0) {
        return issues.join(' | ')
      }
    }
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message
  }

  return 'Failed to upload PAN file'
}

const Page = () => {
  // --- User and Company Info ---
  const self = useGetUserSelf({})
  const userCompanyId = self.data?.company_id

  // --- Data Source ---
  const dataSourceOptions = [
    { value: 'proximal', label: 'Edit' },
    { value: 'pan', label: 'New (PAN File)' },
    { value: 'cec', label: 'New (CEC Database)' },
    { value: 'manual', label: 'New (Manual)' },
  ]
  const [dataSource, setDataSource] = useState<string>(
    dataSourceOptions[0].value,
  )
  const [modalOpened, setModalOpened] = useState(false)

  // --- State for PAN Upload ---
  const [panFile, setPanFile] = useState<File | null>(null)
  const [panUploadError, setPanUploadError] = useState<string | null>(null)
  const [uploadedPANData, setUploadedPANData] =
    useState<PVModuleFromPAN | null>(null)

  // --- State for EquipmentFilter (not part of the form) ---
  const [selectedManufacturer, setSelectedManufacturer] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [selectedModuleId, setSelectedModuleId] = useState<
    number | number[] | null
  >(null)
  const [formSubmitting, setFormSubmitting] = useState<boolean>(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [hasManualEdits, setHasManualEdits] = useState<boolean>(false)

  // -- Parse PAN file ---
  // 2. Add the populateFormWithPANData function (place this before your useEffect hooks)
  const populateFormWithPANData = (panData: PVModuleFromPAN) => {
    form.setValues({
      technology: panData.technology || 'c_Si',
      bifacialityFactor:
        panData.bifaciality_factor !== null &&
        panData.bifaciality_factor !== undefined
          ? panData.bifaciality_factor
          : 0.0,
      pmax: panData.pmax || 400,
      isc: panData.isc || 10,
      voc: panData.voc || 40,
      imp: panData.imp || 9.5,
      vmp: panData.vmp || 38,
      gammaPmax: panData.gamma_pmax || -0.4,
      alphaIscRelative: '', // PAN files typically provide absolute values
      betaVocRelative: '',
      alphaIsc: panData.alpha_isc || 0.005,
      betaVoc: panData.beta_voc || -0.12,
      warrantedDegradationRate: form.values.warrantedDegradationRate, // Keep existing or default
      warrantedDegradationInitial: form.values.warrantedDegradationInitial, // Keep existing or default
      length: panData.length || 1700,
      width: panData.width || 1000,
      frameOverhang: form.values.frameOverhang, // Keep existing or default
      hasArCoating: form.values.hasArCoating, // Keep existing or default
      cellsInSeries: panData.cells_in_series || 72,
      cellsInParallel: panData.cells_in_parallel || 1,
      photocurrent: panData.photocurrent || 10.2,
      diodeSaturationCurrent: panData.diode_saturation_current || 1e-10,
      rSeries: panData.r_series || 0.3,
      rShunt: panData.r_shunt || 500,
      rShunt0: panData.r_shunt_0 || panData.r_shunt || 500,
      rShuntExponent: panData.r_shunt_exponent || 5.5,
      diodeIdealityFactor: panData.diode_ideality_factor || 1.2,
      diodeIdealityFactorTempCoefficient:
        panData.diode_ideality_factor_temp_coefficient || 0.0,
      modifiedIdealityFactor: panData.modified_ideality_factor || 1.2,
      eg: panData.eg || 1.12,
      degdt: panData.degdt || -0.0002,
      family: form.values.family, // Keep existing or default
      halfCut: form.values.halfCut, // Keep existing or default
    })

    // Set manufacturer and model from PAN data
    setSelectedModel(panData.model || '')
    setSelectedManufacturer(panData.manufacturer || '')
    setSelectedModuleId(null)
  }

  const parsePANfileMutation = useParsePANfileMutation({
    onSuccess: (data) => {
      setUploadedPANData(data)
      setPanUploadError(null)
      setHasManualEdits(false) // Reset manual edits flag
      populateFormWithPANData(data)
      notifications.show({
        title: 'PAN File Parsed Successfully',
        message: 'Module data has been loaded from the PAN file',
        color: 'green',
        icon: <IconCheck size="1.1rem" />,
      })
    },
    onError: (error) => {
      const errorMessage = getPANUploadErrorMessage(error)

      setUploadedPANData(null)
      setPanUploadError(errorMessage)

      notifications.show({
        title: 'Upload Error',
        message: errorMessage,
        color: 'red',
      })
    },
  })

  const handlePANFileUpload = (file: File | null) => {
    if (!file) return

    setPanFile(file)
    setPanUploadError(null)
    setSelectedModuleId(null)
    setUploadedPANData(null)

    // Parse the PAN file
    parsePANfileMutation.mutate(file)
  }

  // --- Initialize Mantine Form ---
  const form = useForm<{
    technology: string
    bifacialityFactor: number
    pmax: number
    isc: number
    voc: number
    imp: number
    vmp: number
    gammaPmax: number
    alphaIscRelative: number | '' | null | undefined
    betaVocRelative: number | '' | null | undefined
    alphaIsc: number | '' | null | undefined
    betaVoc: number | '' | null | undefined
    warrantedDegradationRate: number
    warrantedDegradationInitial: number
    length: number
    width: number
    frameOverhang: number
    hasArCoating: boolean
    cellsInSeries: number
    cellsInParallel: number
    photocurrent: number
    diodeSaturationCurrent: number
    rSeries: number
    rShunt: number
    rShunt0: number
    rShuntExponent: number
    diodeIdealityFactor: number
    diodeIdealityFactorTempCoefficient: number
    modifiedIdealityFactor: number
    eg: number
    degdt: number
    family: string
    halfCut: boolean
  }>({
    initialValues: {
      technology: 'c_Si',
      bifacialityFactor: 0.0,
      pmax: 400,
      isc: 10,
      voc: 40,
      imp: 9.5,
      vmp: 38,
      gammaPmax: -0.4,
      alphaIscRelative: '',
      betaVocRelative: '',
      alphaIsc: 0.005,
      betaVoc: -0.12,
      warrantedDegradationRate: NaN,
      warrantedDegradationInitial: NaN,
      length: 1700,
      width: 1000,
      frameOverhang: 25,
      hasArCoating: true,
      cellsInSeries: 72,
      cellsInParallel: 1,
      photocurrent: 10.2,
      diodeSaturationCurrent: 1e-10,
      rSeries: 0.3,
      rShunt: 500,
      rShunt0: 500,
      rShuntExponent: 5.5,
      diodeIdealityFactor: 1.2,
      diodeIdealityFactorTempCoefficient: 0.0,
      modifiedIdealityFactor: 1.2,
      eg: 1.12,
      degdt: -0.0002,
      family: 'None',
      halfCut: false,
    },

    validate: {
      pmax: (value) => (value <= 0 ? 'Maximum Power must be positive' : null),
      isc: (value) =>
        value <= 0 ? 'Short-circuit Current must be positive' : null,
      voc: (value) =>
        value <= 0 ? 'Open-circuit Voltage must be positive' : null,
      imp: (value) =>
        value <= 0 ? 'Current at Maximum Power must be positive' : null,
      vmp: (value) =>
        value <= 0 ? 'Voltage at Maximum Power must be positive' : null,
      width: (value) => (value <= 0 ? 'Width must be positive' : null),
      length: (value) => (value <= 0 ? 'Length must be positive' : null),
      warrantedDegradationRate: (value) =>
        value <= 0
          ? 'Warranted degradation rate must be positive'
          : value > 100
            ? 'Warranted degradation rate cannot exceed 100%'
            : null,
      warrantedDegradationInitial: (value) =>
        value <= 0
          ? 'Initial warranted degradation must be positive'
          : value > 100
            ? 'Initial warranted degradation cannot exceed 100%'
            : null,
      frameOverhang: (value) =>
        value <= 0 ? 'Frame overhang must be positive' : null,
      cellsInSeries: (value) =>
        value <= 0 ? 'Cells in series must be positive' : null,
      cellsInParallel: (value) =>
        value <= 0 ? 'Cells in Parallel must be positive' : null,
      rSeries: (value) =>
        value <= 0 ? 'Series resistance must be positive' : null,
      rShunt: (value) =>
        value <= 0 ? 'Shunt resistance must be positive' : null,
      rShunt0: (value) =>
        value <= 0 ? 'Zero-irradiance shunt resistance must be positive' : null,
      rShuntExponent: (value) =>
        value <= 0 ? 'Shunt exponent must be positive' : null,
      diodeIdealityFactor: (value) =>
        value <= 0 ? 'Diode ideality factor must be positive' : null,
      photocurrent: (value) =>
        value <= 0 ? 'Photocurrent must be positive' : null,
      eg: (value) => (value <= 0 ? 'Bandgap energy must be positive' : null),
      alphaIsc: (value, values) => {
        // Check if both are effectively empty (null, undefined, or empty string)
        if (
          (value === null || value === undefined || value === '') &&
          (values.alphaIscRelative === null ||
            values.alphaIscRelative === undefined ||
            values.alphaIscRelative === '')
        ) {
          return 'Either Absolute or Relative Isc temperature coefficient must be provided'
        }
        return null
      },
      alphaIscRelative: (value, values) => {
        // Check if both are effectively empty (null, undefined, or empty string)
        if (
          (value === null || value === undefined || value === '') &&
          (values.alphaIsc === null ||
            values.alphaIsc === undefined ||
            values.alphaIsc === '')
        ) {
          return 'Either Absolute or Relative Isc temperature coefficient must be provided'
        }
        return null
      },
      betaVoc: (value, values) => {
        // Check if both are effectively empty (null, undefined, or empty string)
        if (
          (value === null || value === undefined || value === '') &&
          (values.betaVocRelative === null ||
            values.betaVocRelative === undefined ||
            values.betaVocRelative === '')
        ) {
          return 'Either Absolute or Relative Voc temperature coefficient must be provided'
        }
        return null
      },
      betaVocRelative: (value, values) => {
        // Check if both are effectively empty (null, undefined, or empty string)
        if (
          (value === null || value === undefined || value === '') &&
          (values.betaVoc === null ||
            values.betaVoc === undefined ||
            values.betaVoc === '')
        ) {
          return 'Either Absolute or Relative Voc temperature coefficient must be provided'
        }
        return null
      },
    },
  })

  // --- Handlers  ---
  const handleManufacturerChange = (value: string | null) => {
    setSelectedManufacturer(value || '')
    setSelectedModel('')
    setSelectedModuleId(null)
  }

  const handleModelChange = (value: string | null) => {
    setSelectedModel(value || '')
    if (dataSource === 'manual') {
      return
    } else {
      // Reset the module ID when model changes
      setSelectedModuleId(null)
      setHasManualEdits(false)
      resetModuleFields()
    }
  }

  const resetModuleFields = () => {
    form.reset()
  }

  const clearForm = () => {
    // Reset all form fields to initial values
    form.reset()

    // Reset all selection states except data source
    setSelectedManufacturer('')
    setSelectedModel('')
    setSelectedModuleId(null)
    setHasManualEdits(false)

    // Reset PAN file related states
    setPanFile(null)
    setPanUploadError(null)
    setUploadedPANData(null)

    // Clear validation errors
    setValidationError(null)
  }

  // Custom wrapper for form input props that tracks manual edits
  const getInputPropsWithTracking = (
    fieldName: string,
    options?: { type?: 'checkbox' },
  ) => {
    const inputProps = form.getInputProps(fieldName, options)
    const originalOnChange = inputProps.onChange

    return {
      ...inputProps,
      onChange: (
        event: Parameters<NonNullable<typeof originalOnChange>>[0],
      ) => {
        setHasManualEdits(true)
        if (originalOnChange) {
          originalOnChange(event)
        }
      },
    }
  }

  // --- Determine which hooks to use based on dataSource ---
  const getManufacturersHook =
    dataSource === 'cec'
      ? useGetCECPVModuleManufacturers
      : useGetProximalPVModuleManufacturers
  const getModelsHook =
    dataSource === 'cec'
      ? useGetCECPVModuleModels
      : useGetProximalPVModuleModels

  // Get module IDs hook based on data source
  const getModuleIdsHook =
    dataSource === 'cec'
      ? useGetCECPVModuleIdsByManufacturerAndModel
      : useGetPVModuleIdsByManufacturerAndModel

  // First fetch module ID based on manufacturer and model
  const {
    data: moduleIdData,
    isLoading: isLoadingModuleId,
    error: moduleIdError,
  } = getModuleIdsHook({
    queryParams: {
      manufacturers: selectedManufacturer ? [selectedManufacturer] : [],
      models: selectedModel ? [selectedModel] : [],
    },
    queryOptions: {
      enabled:
        dataSource !== 'manual' &&
        dataSource !== 'pan' &&
        !!selectedManufacturer &&
        !!selectedModel,
    },
  })

  // Handle successful module ID lookup
  useEffect(() => {
    if (moduleIdData && moduleIdData.length > 0) {
      if (moduleIdData[0] !== null) {
        setSelectedModuleId(moduleIdData[0])
        setHasManualEdits(false) // Reset manual edits flag when new module is loaded
      } else {
        setSelectedModuleId(null)
      }
    }
  }, [moduleIdData])

  // Fetch CEC module details in proximal format for CEC data source
  const {
    data: cecModuleDetails,
    isLoading: isLoadingCECModuleDetails,
    error: cecModuleDetailsError,
  } = useGetCECPVModuleInProximalFormat({
    queryParams: {
      cec_pv_module_id:
        typeof selectedModuleId === 'number' ? selectedModuleId : undefined,
    },
    queryOptions: {
      enabled:
        dataSource === 'cec' &&
        typeof selectedModuleId === 'number' &&
        selectedModuleId > 0,
    },
  })

  // Fetch regular module details for proximal data source

  const {
    data: proximalModuleDetails,
    isLoading: isLoadingProximalModuleDetails,
    error: proximalModuleDetailsError,
  } = useGetPVModuleDetails({
    queryParams: {
      pv_module_ids:
        typeof selectedModuleId === 'number'
          ? [selectedModuleId]
          : Array.isArray(selectedModuleId)
            ? selectedModuleId
            : [],
    },
    queryOptions: {
      enabled:
        dataSource === 'proximal' &&
        ((typeof selectedModuleId === 'number' && selectedModuleId > 0) ||
          (Array.isArray(selectedModuleId) && selectedModuleId.length > 0)),
    },
  })

  // --- Fetch Manufacturers for no equipment check ---
  const { data: manufacturers, isLoading: isLoadingManufacturers } =
    useGetProximalPVModuleManufacturers({
      queryParams: userCompanyId ? { company_id: userCompanyId } : {},
      queryOptions: {
        enabled: dataSource === 'proximal' && !!userCompanyId,
      },
    })

  // Check if no equipment is available in edit mode
  const noEquipmentAvailable =
    dataSource === 'proximal' &&
    !isLoadingManufacturers &&
    manufacturers &&
    manufacturers.length === 0

  // Combine the loading and error states
  const isLoadingModuleDetails =
    isLoadingCECModuleDetails || isLoadingProximalModuleDetails
  const moduleDetailsError = cecModuleDetailsError || proximalModuleDetailsError

  const autoPopulateModuleData = useMemo(() => {
    if (dataSource === 'cec') {
      return cecModuleDetails ?? null
    }

    if (
      dataSource === 'proximal' &&
      proximalModuleDetails &&
      proximalModuleDetails.length > 0
    ) {
      return proximalModuleDetails[0]
    }

    return null
  }, [cecModuleDetails, dataSource, proximalModuleDetails])

  const autoPopulateModuleSignature = useMemo(() => {
    if (!autoPopulateModuleData) {
      return null
    }

    return [
      dataSource,
      selectedModuleId ?? '',
      autoPopulateModuleData.manufacturer,
      autoPopulateModuleData.model,
      autoPopulateModuleData.pmax,
    ].join('|')
  }, [autoPopulateModuleData, dataSource, selectedModuleId])

  const lastAppliedModuleSignature = useRef<string | null>(null)

  useEffect(() => {
    if (hasManualEdits) {
      lastAppliedModuleSignature.current = null
    }
  }, [hasManualEdits])

  // Auto-populate once per loaded module signature to avoid render loops.
  useEffect(() => {
    if (
      hasManualEdits ||
      !autoPopulateModuleData ||
      !autoPopulateModuleSignature
    ) {
      return
    }

    if (lastAppliedModuleSignature.current === autoPopulateModuleSignature) {
      return
    }

    lastAppliedModuleSignature.current = autoPopulateModuleSignature

    const moduleData = autoPopulateModuleData

    form.setValues({
      technology: moduleData.technology,
      bifacialityFactor: moduleData.bifaciality_factor,
      pmax: moduleData.pmax,
      isc: moduleData.isc,
      voc: moduleData.voc,
      imp: moduleData.imp,
      vmp: moduleData.vmp,
      gammaPmax: moduleData.gamma_pmax,
      alphaIscRelative:
        moduleData.alpha_isc_relative === null
          ? undefined
          : typeof moduleData.alpha_isc_relative === 'string'
            ? parseFloat(moduleData.alpha_isc_relative) || ''
            : moduleData.alpha_isc_relative,
      betaVocRelative:
        moduleData.beta_voc_relative === null
          ? undefined
          : typeof moduleData.beta_voc_relative === 'string'
            ? parseFloat(moduleData.beta_voc_relative) || ''
            : moduleData.beta_voc_relative,
      alphaIsc:
        moduleData.alpha_isc === null
          ? undefined
          : typeof moduleData.alpha_isc === 'string'
            ? parseFloat(moduleData.alpha_isc) || ''
            : moduleData.alpha_isc,
      betaVoc:
        moduleData.beta_voc === null
          ? undefined
          : typeof moduleData.beta_voc === 'string'
            ? parseFloat(moduleData.beta_voc) || ''
            : moduleData.beta_voc,
      warrantedDegradationRate: moduleData.warranted_degradation_rate,
      warrantedDegradationInitial: moduleData.warranted_degradation_initial,
      length: moduleData.length,
      width: moduleData.width,
      frameOverhang: moduleData.frame_overhang,
      hasArCoating: moduleData.has_ar_coating,
      cellsInSeries: moduleData.cells_in_series,
      cellsInParallel: moduleData.cells_in_parallel,
      photocurrent: moduleData.photocurrent,
      diodeSaturationCurrent: moduleData.diode_saturation_current,
      rSeries: moduleData.r_series,
      rShunt: moduleData.r_shunt,
      rShunt0: moduleData.r_shunt_0 ?? moduleData.r_shunt,
      rShuntExponent: moduleData.r_shunt_exponent ?? 5.5,
      diodeIdealityFactor: moduleData.diode_ideality_factor ?? 1.2,
      diodeIdealityFactorTempCoefficient:
        moduleData.diode_ideality_factor_temp_coefficient ?? 0.0,
      modifiedIdealityFactor: moduleData.modified_ideality_factor,
      eg: moduleData.eg,
      degdt: moduleData.degdt,
      family: moduleData.family,
      halfCut: moduleData.half_cut ?? false,
    })
  }, [
    autoPopulateModuleData,
    autoPopulateModuleSignature,
    form,
    hasManualEdits,
  ])

  // Create or Update PV Module mutation
  const createOrUpdatePVModuleMutation = useCreateOrUpdatePVModuleMutation()

  // Form submission handler
  const handleSubmit = async (values: typeof form.values) => {
    // Clear any validation error when form is submitted successfully
    setValidationError(null)
    try {
      setFormSubmitting(true)

      if (!userCompanyId) {
        throw new Error('Company ID is required')
      }

      const isExistingCompanyModule =
        dataSource === 'proximal' &&
        typeof selectedModuleId === 'number' &&
        selectedModuleId > 0

      // CEC lookup IDs are not company pv_module_id values.
      const normalizedModuleId: number | null = isExistingCompanyModule
        ? Array.isArray(selectedModuleId)
          ? (selectedModuleId[0] ?? null)
          : selectedModuleId
        : null

      // Create the module data object
      const moduleData: PVModule = {
        company_id: userCompanyId,
        pv_module_id: normalizedModuleId,
        manufacturer: selectedManufacturer,
        model: selectedModel,
        technology: values.technology,
        bifaciality_factor: values.bifacialityFactor,
        pmax: values.pmax,
        isc: values.isc,
        voc: values.voc,
        imp: values.imp,
        vmp: values.vmp,
        gamma_pmax: values.gammaPmax,
        alpha_isc_relative:
          values.alphaIscRelative === undefined ||
          values.alphaIscRelative === ''
            ? null
            : values.alphaIscRelative,
        beta_voc_relative:
          values.betaVocRelative === undefined || values.betaVocRelative === ''
            ? null
            : values.betaVocRelative,
        alpha_isc:
          values.alphaIsc === undefined || values.alphaIsc === ''
            ? null
            : values.alphaIsc,
        beta_voc:
          values.betaVoc === undefined || values.betaVoc === ''
            ? null
            : values.betaVoc,
        warranted_degradation_rate: values.warrantedDegradationRate,
        warranted_degradation_initial: values.warrantedDegradationInitial,
        length: values.length,
        width: values.width,
        frame_overhang: values.frameOverhang,
        has_ar_coating: values.hasArCoating,
        cells_in_series: values.cellsInSeries,
        cells_in_parallel: values.cellsInParallel,
        photocurrent: values.photocurrent,
        diode_saturation_current: values.diodeSaturationCurrent,
        r_series: values.rSeries,
        r_shunt: values.rShunt,
        r_shunt_0: values.rShunt0,
        r_shunt_exponent: values.rShuntExponent,
        diode_ideality_factor: values.diodeIdealityFactor,
        diode_ideality_factor_temp_coefficient:
          values.diodeIdealityFactorTempCoefficient,
        modified_ideality_factor: values.modifiedIdealityFactor,
        eg: values.eg,
        degdt: values.degdt,
        data_source: dataSource,
        family: values.family,
        half_cut: values.halfCut ?? false,
      }

      // Call the mutation
      const result =
        await createOrUpdatePVModuleMutation.mutateAsync(moduleData)

      // Update the module ID if this was a new creation
      if (!isExistingCompanyModule && result.pv_module_id) {
        if (dataSource === 'cec') {
          setDataSource('proximal')
        }
        setSelectedModuleId(result.pv_module_id)
        setHasManualEdits(false)
      }

      // Show success notification
      notifications.show({
        title: isExistingCompanyModule ? 'Module Updated' : 'Module Created',
        message: `Successfully ${
          isExistingCompanyModule ? 'updated' : 'created'
        } PV module for ${selectedManufacturer} - ${selectedModel}`,
        color: 'green',
        icon: <IconCheck size="1.1rem" />,
      })
    } catch (error) {
      const errorMessage = getSubmitErrorMessage(error)
      setValidationError(errorMessage)

      notifications.show({
        title: 'Error Saving Module',
        message: errorMessage,
        color: 'red',
      })
    } finally {
      setFormSubmitting(false)
    }
  }

  const isUpdate =
    dataSource === 'proximal' &&
    typeof selectedModuleId === 'number' &&
    selectedModuleId > 0

  const technologyOptions = [
    { value: 'c-Si', label: 'Crystalline Silicon (c-Si)' },
    { value: 'CdTe', label: 'Cadmium Telluride (CdTe)' },
    { value: 'CIGS', label: 'CIGS' },
    { value: 'a-Si', label: 'Amorphous Silicon (a-Si)' },
  ]

  return (
    <Container size="lg" p="md" style={{ width: '100%' }}>
      <Paper
        withBorder
        p="md"
        radius="md"
        component="form"
        onSubmit={form.onSubmit(handleSubmit, (_validationErrors) => {
          // Clear any previous validation error message
          setValidationError(
            'Please check the form above for missing or values which are not allowed',
          )
        })}
      >
        <Stack>
          <PageTitle
            info={
              <Stack>
                <Text>
                  This page allows you to manage the PV modules in your
                  company&apos;s component library.
                </Text>
                <Text>
                  You can add new modules by uploading a PAN file, importing
                  from the CEC database, or by entering the parameters manually.
                  You can also edit existing modules.
                </Text>
              </Stack>
            }
          >
            PV Modules
          </PageTitle>
          <Text c="dimmed" size="sm" mb="md">
            Add or edit components in your company&apos;s component library.
            Equipment can be assigned to specific projects via the projectlevel
            google sheet. If you need access to a project google sheet, please
            contact your Proximal support contact.
          </Text>
          <Text c="dimmed" size="sm" mb="md">
            Choose &quot;Edit Equipment&quot; to modify existing module
            specifications, &quot;CEC Database&quot; to load from CEC database,
            or &quot;New Equipment (Manual)&quot; to enter your own values.
          </Text>
          <Select
            label="Source"
            data={dataSourceOptions}
            value={dataSource}
            allowDeselect={false}
            onChange={(value) => {
              setDataSource(value || '')
              setSelectedManufacturer('')
              setSelectedModel('')
              setSelectedModuleId(null)
              setHasManualEdits(false)
              resetModuleFields()
              setPanFile(null)
              setPanUploadError(null)
              setUploadedPANData(null)
            }}
            clearable={false}
            required={true}
          />

          {/* Conditional Rendering based on Data Source */}
          {dataSource === 'manual' ? (
            <></>
          ) : dataSource === 'proximal' || dataSource === 'cec' ? (
            <>
              {dataSource === 'proximal' && noEquipmentAvailable ? (
                <Alert
                  icon={<IconAlertCircle size="1rem" />}
                  title="No Equipment Available"
                  color="orange"
                  mt="md"
                >
                  No PV module equipment is available for your company in edit
                  mode. Please use &quot;New (CEC Database)&quot; or &quot;New
                  (Manual)&quot; to add equipment to your company&apos;s
                  inventory.
                </Alert>
              ) : (
                <EquipmentFilter
                  useGetManufacturers={getManufacturersHook}
                  useGetModels={getModelsHook}
                  onManufacturerChange={handleManufacturerChange}
                  onModelChange={handleModelChange}
                  initialManufacturer={selectedManufacturer}
                  initialModel={selectedModel}
                  company_id={userCompanyId}
                  key={dataSource}
                />
              )}
            </>
          ) : dataSource === 'pan' ? (
            <>
              {/* PAN File Upload */}
              <FileInput
                label="Upload PAN File"
                placeholder="Click to select PAN file"
                accept=".pan,.PAN"
                leftSection={<IconUpload size="1rem" />}
                value={panFile}
                onChange={(value) => {
                  setPanFile(value)
                  if (value) handlePANFileUpload(value)
                }}
                error={panUploadError}
                required={true}
                style={{ width: '100%' }}
              />
              {panUploadError && (
                <Alert
                  icon={<IconAlertCircle size="1rem" />}
                  title="Error processing PAN file"
                  color="red"
                  mt="sm"
                  withCloseButton
                >
                  {panUploadError}
                </Alert>
              )}
            </>
          ) : null}
        </Stack>

        {/* Show Manufacturer/Model inputs for manual mode or PAN mode only */}
        {(dataSource === 'manual' || dataSource === 'pan') && (
          <Stack mt="md">
            <TextInput
              label="Manufacturer"
              required
              placeholder="Enter or edit manufacturer name"
              value={selectedManufacturer}
              onChange={(event) =>
                setSelectedManufacturer(event.currentTarget.value)
              }
            />
            <TextInput
              label="Model"
              required
              placeholder="Enter or edit model name"
              value={selectedModel}
              onChange={(event) => setSelectedModel(event.currentTarget.value)}
            />
          </Stack>
        )}

        {/* Conditional Rendering based on Model */}
        {selectedModel === '' ||
        (dataSource === 'proximal' && noEquipmentAvailable) ? null : (
          <>
            <Space h={25}></Space>
            <Divider></Divider>
            <Space h={25}></Space>
            {moduleIdError ? (
              <Alert
                icon={<IconAlertCircle size="1rem" />}
                title="Error looking up module ID"
                color="red"
                mb="md"
                withCloseButton
              >
                {moduleIdError instanceof Error
                  ? moduleIdError.message
                  : 'Failed to lookup module ID. Please try again.'}
              </Alert>
            ) : moduleDetailsError ? (
              <Alert
                icon={<IconAlertCircle size="1rem" />}
                title="Error loading module details"
                color="red"
                mb="md"
                withCloseButton
              >
                {moduleDetailsError instanceof Error
                  ? moduleDetailsError.message
                  : 'Failed to load module details. Please try again.'}
              </Alert>
            ) : (isLoadingModuleId || isLoadingModuleDetails) &&
              dataSource !== 'manual' ? (
              <Center p="xl">
                <Loader size="md" />
                <Text ml="md">Loading module details...</Text>
              </Center>
            ) : (
              // Only render the form fields when details are loaded or in manual mode
              (dataSource === 'manual' ||
                (dataSource === 'cec' && cecModuleDetails) ||
                (dataSource === 'pan' && uploadedPANData) ||
                (dataSource === 'proximal' &&
                  proximalModuleDetails &&
                  proximalModuleDetails.length > 0)) && (
                <>
                  <Grid>
                    <Grid.Col span={6}>
                      <Select
                        label="Technology"
                        description="Cell Material"
                        data={technologyOptions}
                        {...getInputPropsWithTracking('technology')}
                        clearable={false}
                        required={true}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <TextInput
                        label="Family"
                        description="For Example: Series 7"
                        placeholder="Enter module family"
                        {...getInputPropsWithTracking('family')}
                      />
                    </Grid.Col>

                    <Grid.Col span={12}>
                      <Title order={4} mt="md">
                        Electrical Characteristics
                      </Title>
                      <Divider my="sm" />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Maximum Power (Pmax) (W)"
                        placeholder="Enter maximum power"
                        step={1.0}
                        min={0}
                        {...getInputPropsWithTracking('pmax')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Short-circuit Current (Isc) (A)"
                        placeholder="Enter short-circuit current"
                        step={0.1}
                        min={0}
                        decimalScale={3}
                        {...getInputPropsWithTracking('isc')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Open-circuit Voltage (Voc) (V)"
                        placeholder="Enter open-circuit voltage"
                        step={0.1}
                        min={0}
                        decimalScale={12}
                        {...getInputPropsWithTracking('voc')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Current at Maximum Power (Imp) (A)"
                        placeholder="Enter Imp"
                        step={0.1}
                        min={0}
                        decimalScale={6}
                        {...getInputPropsWithTracking('imp')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Voltage at Maximum Power (Vmp) (V)"
                        placeholder="Enter Vmp"
                        step={0.1}
                        min={0}
                        decimalScale={3}
                        {...getInputPropsWithTracking('vmp')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Bifaciality Factor"
                        placeholder="Enter bifaciality factor"
                        step={0.01}
                        min={0}
                        max={1}
                        decimalScale={3}
                        {...getInputPropsWithTracking('bifacialityFactor')}
                      />
                    </Grid.Col>

                    <Grid.Col span={12}>
                      <Title order={4} mt="md">
                        Temperature Coefficients
                      </Title>
                      <Divider my="sm" />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Temperature Coefficient of Pmax (%/°C)"
                        placeholder="Enter coefficient"
                        step={0.01}
                        decimalScale={3}
                        {...getInputPropsWithTracking('gammaPmax')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}></Grid.Col>
                    <Grid.Col span={6}>
                      <NumberInput
                        label="Absolute Temperature Coefficient of Isc (A/°C)"
                        description="If absolute temperature coefficient of Isc is given, then relative is not needed"
                        placeholder="Enter coefficient"
                        step={0.001}
                        decimalScale={5}
                        {...getInputPropsWithTracking('alphaIsc')}
                      />
                    </Grid.Col>
                    <Grid.Col span={6}>
                      <NumberInput
                        label="Relative Temperature Coefficient of Isc (%/°C)"
                        description="If relative temperature coefficient of Isc is given then absolute is not needed, if both are provided, relative is ignored"
                        placeholder="Enter coefficient"
                        step={0.01}
                        decimalScale={3}
                        {...getInputPropsWithTracking('alphaIscRelative')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Absolute Temperature Coefficient of Voc (V/°C)"
                        description="If absolute temperature coefficient of Voc is given then relative is not needed"
                        placeholder="Enter coefficient"
                        step={0.001}
                        decimalScale={5}
                        {...getInputPropsWithTracking('betaVoc')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Relative Temperature Coefficient of Voc (%/°C)"
                        description="If relative temperature coefficient of Voc is given then absolute is not needed, if both are provided, relative is ignored"
                        placeholder="Enter coefficient"
                        step={0.01}
                        decimalScale={3}
                        {...getInputPropsWithTracking('betaVocRelative')}
                      />
                    </Grid.Col>
                    <Grid.Col span={12}>
                      <Title order={4} mt="md">
                        Degradation
                      </Title>
                      <Divider my="sm" />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Annual Warranted Degradation Rate (%)"
                        description="Not stored in PAN files.  Usually <=0.5%"
                        placeholder="Enter degradation rate"
                        step={0.1}
                        min={0}
                        decimalScale={2}
                        {...getInputPropsWithTracking(
                          'warrantedDegradationRate',
                        )}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Initial Warranted Degradation (%)"
                        description="Not stored in PAN files.  Usually ~2.0%"
                        placeholder="Enter initial degradation"
                        step={0.1}
                        min={0}
                        decimalScale={2}
                        {...getInputPropsWithTracking(
                          'warrantedDegradationInitial',
                        )}
                      />
                    </Grid.Col>

                    <Grid.Col span={12}>
                      <Title order={4} mt="md">
                        Physical Characteristics
                      </Title>
                      <Divider my="sm" />
                    </Grid.Col>

                    <Grid.Col span={4}>
                      <NumberInput
                        label="Length (m)"
                        description="The longer side of the module."
                        placeholder="Enter length"
                        step={1}
                        min={0}
                        {...getInputPropsWithTracking('length')}
                      />
                    </Grid.Col>

                    <Grid.Col span={4}>
                      <NumberInput
                        label="Width (m)"
                        description="The shorter side of the module."
                        placeholder="Enter width"
                        step={1}
                        min={0}
                        {...getInputPropsWithTracking('width')}
                      />
                    </Grid.Col>

                    <Grid.Col span={4}>
                      <NumberInput
                        label="Frame Overhang (m)"
                        description="Not stored in PAN files."
                        placeholder="Enter frame overhang"
                        step={1}
                        min={0}
                        {...getInputPropsWithTracking('frameOverhang')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <Switch
                        label="Has Anti-Reflective Coating"
                        {...getInputPropsWithTracking('hasArCoating', {
                          type: 'checkbox',
                        })}
                        mt="md"
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <Switch
                        label="Half-Cut Cells"
                        {...getInputPropsWithTracking('halfCut', {
                          type: 'checkbox',
                        })}
                        mt="md"
                      />
                    </Grid.Col>

                    <Grid.Col span={12}>
                      <Title order={4} mt="md">
                        Module Design
                      </Title>
                      <Divider my="sm" />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Cells in Series"
                        description="Number of cells in series"
                        placeholder="Enter number of cells"
                        step={1}
                        min={0}
                        {...getInputPropsWithTracking('cellsInSeries')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Cells in Parallel"
                        description="Number of cells in parallel"
                        placeholder="Enter number of cells"
                        step={1}
                        min={0}
                        {...getInputPropsWithTracking('cellsInParallel')}
                      />
                    </Grid.Col>

                    <Grid.Col span={12}>
                      <Title order={4} mt="md">
                        Single Diode Model Parameters
                      </Title>
                      <Divider my="sm" />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Photocurrent (A)"
                        placeholder="Enter photocurrent"
                        step={0.1}
                        decimalScale={3}
                        {...getInputPropsWithTracking('photocurrent')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Diode Saturation Current (A)"
                        placeholder="This field may not display very small values < 1e-19"
                        step={1e-12}
                        decimalScale={20}
                        fixedDecimalScale={true}
                        {...getInputPropsWithTracking('diodeSaturationCurrent')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Series Resistance (Ω)"
                        placeholder="Enter series resistance"
                        step={0.01}
                        min={0}
                        decimalScale={3}
                        {...getInputPropsWithTracking('rSeries')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Shunt Resistance (Ω)"
                        placeholder="Enter shunt resistance"
                        step={1}
                        min={0}
                        {...getInputPropsWithTracking('rShunt')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Zero-Irradiance Shunt Resistance (Ω)"
                        placeholder="Enter zero-irradiance shunt resistance"
                        step={1}
                        min={0}
                        {...getInputPropsWithTracking('rShunt0')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Shunt Resistance Exponent"
                        placeholder="Enter shunt resistance exponent"
                        step={0.1}
                        min={0}
                        decimalScale={3}
                        {...getInputPropsWithTracking('rShuntExponent')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Diode Ideality Factor"
                        placeholder="Enter diode ideality factor"
                        step={0.01}
                        min={0}
                        decimalScale={3}
                        {...getInputPropsWithTracking('diodeIdealityFactor')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Diode Ideality Temp Coefficient"
                        placeholder="Enter diode ideality temp coefficient"
                        step={0.0001}
                        decimalScale={6}
                        {...getInputPropsWithTracking(
                          'diodeIdealityFactorTempCoefficient',
                        )}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Modified Ideality Factor"
                        placeholder="Enter modified ideality factor"
                        step={0.01}
                        min={0}
                        decimalScale={3}
                        {...getInputPropsWithTracking('modifiedIdealityFactor')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Bandgap Energy (eV)"
                        placeholder="Enter bandgap energy"
                        step={0.01}
                        min={0}
                        decimalScale={3}
                        {...getInputPropsWithTracking('eg')}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Delta Eg over Delta Temperature"
                        placeholder="Enter degdt"
                        step={0.0001}
                        decimalScale={6}
                        {...getInputPropsWithTracking('degdt')}
                      />
                    </Grid.Col>
                  </Grid>

                  {/* Form Submit Button */}
                  <Group style={{ justifyContent: 'space-between' }} mt="xl">
                    {validationError && (
                      <Alert
                        icon={<IconAlertCircle size="1rem" />}
                        title="Validation Error"
                        color="red"
                        withCloseButton
                        onClose={() => setValidationError(null)}
                      >
                        {validationError}
                      </Alert>
                    )}
                    <Group ml="auto">
                      <Button
                        variant="outline"
                        color="gray"
                        leftSection={<IconRefresh size={16} />}
                        onClick={clearForm}
                        disabled={formSubmitting}
                      >
                        Clear
                      </Button>
                      <Button
                        onClick={() => {
                          if (isUpdate) {
                            setModalOpened(true)
                          } else {
                            form.onSubmit(handleSubmit)()
                          }
                        }}
                        loading={formSubmitting}
                        disabled={
                          dataSource !== 'pan' &&
                          (!selectedManufacturer || !selectedModel)
                        }
                        color={isUpdate ? 'orange' : 'blue'}
                        leftSection={
                          isUpdate ? <IconAlertTriangle size={16} /> : undefined
                        }
                      >
                        {isUpdate ? 'Update Module' : 'Create Module'}
                      </Button>
                    </Group>
                  </Group>
                  <ConfirmationModal
                    opened={modalOpened}
                    onClose={() => setModalOpened(false)}
                    onConfirm={() => {
                      form.onSubmit(handleSubmit)()
                      setModalOpened(false)
                    }}
                    title="Confirm Update"
                    message="Updating this module will affect the expected energy model for all projects that use it. Are you sure you want to continue?"
                  />
                </>
              )
            )}
            {/* Display a message when no data is found */}
            {!isLoadingModuleId &&
              !isLoadingModuleDetails &&
              ((dataSource !== 'pan' &&
                moduleIdData &&
                moduleIdData.length > 0 &&
                moduleIdData[0] === null) ||
                (dataSource === 'cec' && !cecModuleDetails) ||
                (dataSource === 'proximal' &&
                  (!proximalModuleDetails ||
                    proximalModuleDetails.length === 0))) &&
              dataSource !== 'manual' && (
                <Alert
                  icon={<IconAlertCircle size="1rem" />}
                  title="No data found"
                  color="blue"
                  mt="md"
                  withCloseButton
                >
                  No module details found for the selected manufacturer and
                  model. You can enter values manually or select a different
                  model.
                </Alert>
              )}{' '}
          </>
        )}
      </Paper>
    </Container>
  )
}

export default Page
