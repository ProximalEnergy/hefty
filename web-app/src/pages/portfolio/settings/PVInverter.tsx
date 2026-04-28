import { useGetUserSelf } from '@/api/v1/admin/users'
import {
  Inverter,
  useCreateInverterMutation,
  useGetInverterIdsByManufacturerAndModel,
  useGetInverters,
  useGetProximalInverterManufacturers,
  useGetProximalInverterModels,
  useParseOndFileMutation,
} from '@/api/v1/operational/pv_inverters'
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
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconCheck,
  IconUpload,
} from '@tabler/icons-react'
import axios from 'axios'
import { useEffect, useState } from 'react'

import { formatFieldLabel } from './fieldLabels'

const FIELD_LABELS: Record<string, string> = {
  voltage_mpp_min: 'Minimum MPP Voltage',
  voltage_mpp_max: 'Maximum MPP Voltage',
  voltage_start_up: 'Startup Voltage',
  voltage_min: 'Minimum Voltage',
  voltage_max: 'Maximum Voltage',
  current_max: 'Maximum Current',
  power_max_at_reference_temp: 'Power at Reference Temperature',
  power_at_reference_temp: 'Power at Reference Temperature',
  reference_temp: 'Reference Temperature',
  voltage_nominal_efficiency: 'Nominal Efficiency Voltage',
  efficiency_at_low_voltage: 'Low-Voltage Efficiency Curve',
  efficiency_at_mid_voltage: 'Mid-Voltage Efficiency Curve',
  efficiency_at_high_voltage: 'High-Voltage Efficiency Curve',
  power_start_up: 'Startup Power',
  power_ac_nominal: 'Nominal AC Power',
  power_dc_nominal: 'Nominal DC Power',
  voltage_dc_nominal: 'Nominal DC Voltage',
  c0: 'C0',
  c1: 'C1',
  c2: 'C2',
  c3: 'C3',
  night_tare: 'Night Tare',
}

type ValidationIssue = {
  loc?: Array<string | number>
  msg?: string
}

type InverterWithLegacyPowerKey = Inverter & {
  power_at_reference_temp?: number[]
}

type SubmitErrorResult = {
  message: string
  fieldErrors: Record<string, string>
}

const getSubmitErrorResult = (error: unknown): SubmitErrorResult => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail as unknown

    if (error.response?.status === 422) {
      if (Array.isArray(detail)) {
        const fieldErrors: Record<string, string> = {}
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
              typeof field === 'string'
                ? formatFieldLabel(field, FIELD_LABELS)
                : 'Request'
            if (
              typeof field === 'string' &&
              typeof item.msg === 'string' &&
              !fieldErrors[field]
            ) {
              fieldErrors[field] = item.msg
            }
            return `${fieldLabel}: ${item.msg}`
          })

        if (issues.length > 0) {
          return {
            message: `Validation failed: ${issues.join(' | ')}`,
            fieldErrors,
          }
        }
      }

      if (typeof detail === 'string') {
        return {
          message: `Validation failed: ${detail}`,
          fieldErrors: {},
        }
      }

      return {
        message: 'Validation failed. Check required fields and value formats.',
        fieldErrors: {},
      }
    }

    if (typeof detail === 'string') {
      return { message: detail, fieldErrors: {} }
    }
  }

  if (error instanceof Error) {
    return { message: error.message, fieldErrors: {} }
  }

  return {
    message: 'Failed to save inverter configuration',
    fieldErrors: {},
  }
}

const isNonPositive = (value: number) => !Number.isFinite(value) || value <= 0

const PVInverterSettings = () => {
  // --- User and Company Info ---
  const self = useGetUserSelf({})
  const userCompanyId = self.data?.company_id

  // --- Data Source ---
  const dataSourceOptions = [
    { value: 'proximal', label: 'Edit' },
    { value: 'manual', label: 'New (Manual)' },
    { value: 'ond', label: 'New (OND File)' },
  ]
  const [dataSource, setDataSource] = useState<string>(
    dataSourceOptions[0].value,
  )
  const [modalOpened, setModalOpened] = useState(false)
  // --- State ---
  // Add this to your existing state variables (around line 45)
  const [selectedManufacturer, setSelectedManufacturer] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [selectedInverterId, setSelectedInverterId] = useState<number | null>(
    null,
  )
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [ondFile, setOndFile] = useState<File | null>(null)
  const [ondUploadError, setOndUploadError] = useState<string | null>(null)
  const [formSubmitting, setFormSubmitting] = useState<boolean>(false)
  // --- Inverter Parameters State ---
  // Operating window parameters
  const [voltageMppMin, setVoltageMppMin] = useState<number>(0)
  const [voltageMppMax, setVoltageMppMax] = useState<number>(0)
  const [voltageStartUp, setVoltageStartUp] = useState<number>(0)
  const [voltageMin, setVoltageMin] = useState<number>(0)
  const [voltageMax, setVoltageMax] = useState<number>(0)
  const [currentMax, setCurrentMax] = useState<number>(0)
  // Temperature-dependent power characteristics
  const [numTempPowerCurvePoints, setNumTempCurvePoints] = useState<number>(1)
  const [powerAtReferenceTemp, setPowerAtReferenceTemp] = useState<number[]>([
    0,
  ])
  const [referenceTemp, setReferenceTemp] = useState<number[]>([25])
  // Inverter efficiency reference parameters
  const [numLowVoltagePoints, setNumLowVoltagePoints] = useState<number>(1)
  const [numMidVoltagePoints, setNumMidVoltagePoints] = useState<number>(1)
  const [numHighVoltagePoints, setNumHighVoltagePoints] = useState<number>(1)
  const [voltageNominalEfficiency, setVoltageNominalEfficiency] = useState<
    number[]
  >([0])
  const [efficiencyAtLowVoltage, setEfficiencyAtLowVoltage] = useState<
    number[][]
  >([[0, 0]])
  const [efficiencyAtMidVoltage, setEfficiencyAtMidVoltage] = useState<
    number[][]
  >([[0, 0]])
  const [efficiencyAtHighVoltage, setEfficiencyAtHighVoltage] = useState<
    number[][]
  >([[0, 0]])
  // Inverter efficiency parameters
  const [powerStartUp, setPowerStartUp] = useState<number>(0)
  const [powerAcNominal, setPowerAcNominal] = useState<number>(0)
  const [powerDcNominal, setPowerDcNominal] = useState<number>(0)
  const [voltageDcNominal, setVoltageDcNominal] = useState<number>(0)
  const [c0, setC0] = useState<number>(0)
  const [c1, setC1] = useState<number>(0)
  const [c2, setC2] = useState<number>(0)
  const [c3, setC3] = useState<number>(0)
  const [nightTare, setNightTare] = useState<number>(0)

  // Set inverter parameters from data object
  const setInverterParameters = (inverterData: Inverter) => {
    const inverterDataWithLegacyKey = inverterData as InverterWithLegacyPowerKey
    const parsedPowerAtReferenceTemp =
      inverterDataWithLegacyKey.power_max_at_reference_temp ??
      inverterDataWithLegacyKey.power_at_reference_temp

    // Operating window parameters
    setVoltageMppMin(inverterData.voltage_mpp_min)
    setVoltageMppMax(inverterData.voltage_mpp_max)
    setVoltageStartUp(inverterData.voltage_start_up)
    setVoltageMin(inverterData.voltage_min)
    setVoltageMax(inverterData.voltage_max)
    setCurrentMax(inverterData.current_max)

    // Temperature-dependent power characteristics
    if (parsedPowerAtReferenceTemp && inverterData.reference_temp) {
      setNumTempCurvePoints(parsedPowerAtReferenceTemp.length || 1)
      setPowerAtReferenceTemp(parsedPowerAtReferenceTemp)
      setReferenceTemp(inverterData.reference_temp)
    }
    // Inverter efficiency reference parameters
    if (inverterData.voltage_nominal_efficiency) {
      setVoltageNominalEfficiency(inverterData.voltage_nominal_efficiency)
    }
    if (inverterData.efficiency_at_low_voltage) {
      setEfficiencyAtLowVoltage(inverterData.efficiency_at_low_voltage)
      setNumLowVoltagePoints(inverterData.efficiency_at_low_voltage.length || 1)
    }
    if (inverterData.efficiency_at_mid_voltage) {
      setEfficiencyAtMidVoltage(inverterData.efficiency_at_mid_voltage)
      setNumMidVoltagePoints(inverterData.efficiency_at_mid_voltage.length || 1)
    }
    if (inverterData.efficiency_at_high_voltage) {
      setEfficiencyAtHighVoltage(inverterData.efficiency_at_high_voltage)
      setNumHighVoltagePoints(
        inverterData.efficiency_at_high_voltage.length || 1,
      )
    }
    // Inverter efficiency parameters
    setPowerStartUp(inverterData.power_start_up)
    setPowerAcNominal(inverterData.power_ac_nominal)
    setPowerDcNominal(inverterData.power_dc_nominal)
    setVoltageDcNominal(inverterData.voltage_dc_nominal)
    setC0(inverterData.c0)
    setC1(inverterData.c1)
    setC2(inverterData.c2)
    setC3(inverterData.c3)
    setNightTare(inverterData.night_tare)
  }
  // Reset all form fields
  const resetFormFields = () => {
    // Operating window parameters
    setVoltageMppMin(0)
    setVoltageMppMax(0)
    setVoltageStartUp(0)
    setVoltageMin(0)
    setVoltageMax(0)
    setCurrentMax(0)
    // Temperature-dependent power characteristics
    setNumTempCurvePoints(1)
    setPowerAtReferenceTemp([0])
    setReferenceTemp([25])
    // Inverter efficiency reference parameters
    setNumLowVoltagePoints(1)
    setNumMidVoltagePoints(1)
    setNumHighVoltagePoints(1)
    setVoltageNominalEfficiency([0, 0, 0])
    setEfficiencyAtLowVoltage([[0, 0]])
    setEfficiencyAtMidVoltage([[0, 0]])
    setEfficiencyAtHighVoltage([[0, 0]])
    // Inverter efficiency parameters
    setPowerStartUp(0)
    setPowerAcNominal(0)
    setPowerDcNominal(0)
    setVoltageDcNominal(0)
    setC0(0)
    setC1(0)
    setC2(0)
    setC3(0)
    setNightTare(0)
  }

  const clearFieldError = (field: string) => {
    setFieldErrors((prev) => {
      const aliasField =
        field === 'power_max_at_reference_temp'
          ? 'power_at_reference_temp'
          : field
      if (!prev[field] && !prev[aliasField]) {
        return prev
      }
      const next = { ...prev }
      delete next[field]
      delete next[aliasField]
      return next
    })
  }

  const clientFieldErrors: Record<string, string | undefined> = {
    manufacturer: selectedManufacturer.trim()
      ? undefined
      : 'Manufacturer is required',
    model: selectedModel.trim() ? undefined : 'Model is required',
    voltage_mpp_min: isNonPositive(voltageMppMin)
      ? 'Minimum MPP Voltage must be greater than 0'
      : undefined,
    voltage_mpp_max: isNonPositive(voltageMppMax)
      ? 'Maximum MPP Voltage must be greater than 0'
      : undefined,
    voltage_min: isNonPositive(voltageMin)
      ? 'Minimum Voltage must be greater than 0'
      : undefined,
    voltage_max: isNonPositive(voltageMax)
      ? 'Maximum Voltage must be greater than 0'
      : undefined,
    voltage_start_up: isNonPositive(voltageStartUp)
      ? 'Start-up Voltage must be greater than 0'
      : undefined,
    current_max: isNonPositive(currentMax)
      ? 'Maximum Current must be greater than 0'
      : undefined,
    power_start_up: isNonPositive(powerStartUp)
      ? 'Start-up Power must be greater than 0'
      : undefined,
    power_ac_nominal: isNonPositive(powerAcNominal)
      ? 'AC Nominal Power must be greater than 0'
      : undefined,
    power_dc_nominal: isNonPositive(powerDcNominal)
      ? 'DC Nominal Power must be greater than 0'
      : undefined,
    voltage_dc_nominal: isNonPositive(voltageDcNominal)
      ? 'DC Nominal Voltage must be greater than 0'
      : undefined,
    power_max_at_reference_temp: powerAtReferenceTemp.some(isNonPositive)
      ? 'All power values must be greater than 0'
      : undefined,
    voltage_nominal_efficiency:
      voltageNominalEfficiency.length < 3 ||
      voltageNominalEfficiency.some(isNonPositive)
        ? 'All reference voltages must be greater than 0'
        : undefined,
    // Curve-point validation is handled by backend; pre-submit aggregate checks
    // caused noisy false positives across all rows.
    efficiency_at_low_voltage: undefined,
    efficiency_at_mid_voltage: undefined,
    efficiency_at_high_voltage: undefined,
  }

  const getFieldError = (field: string) => {
    const aliasField =
      field === 'power_max_at_reference_temp'
        ? 'power_at_reference_temp'
        : field
    return (
      fieldErrors[field] || fieldErrors[aliasField] || clientFieldErrors[field]
    )
  }
  // --- Helper Functions ---
  const resizeEfficiencyArray = (currentArray: number[][], newSize: number) => {
    if (newSize > currentArray.length) {
      return [
        ...currentArray,
        ...Array(newSize - currentArray.length).fill([0, 0]),
      ]
    } else if (newSize < currentArray.length) {
      return currentArray.slice(0, newSize)
    }
    return currentArray
  }

  // --- Handlers  ---
  const handlePvInverterManufacturerChange = (value: string | null) => {
    setFieldErrors((prev) => {
      if (!prev.manufacturer) {
        return prev
      }
      const next = { ...prev }
      delete next.manufacturer
      return next
    })
    setSelectedManufacturer(value || '')
    setSelectedModel('')
    setSelectedInverterId(null)
    resetFormFields()
  }
  const handlePvInverterModelChange = (value: string | null) => {
    setFieldErrors((prev) => {
      if (!prev.model) {
        return prev
      }
      const next = { ...prev }
      delete next.model
      return next
    })
    setSelectedModel(value || '')
    // When changing models on manual mode, don't reset fields
    if (dataSource === 'manual') {
      return
    }
    // Reset fields until data loads
    resetFormFields()
    // Reset the inverter ID when model changes
    setSelectedInverterId(null)
  }
  // Fetch inverter ID based on manufacturer and model
  const {
    data: inverterIdData,
    isLoading: isLoadingInverterId,
    error: inverterIdError,
  } = useGetInverterIdsByManufacturerAndModel({
    queryParams: {
      manufacturers: selectedManufacturer ? [selectedManufacturer] : [],
      models: selectedModel ? [selectedModel] : [],
    },
    queryOptions: {
      enabled:
        dataSource !== 'manual' &&
        dataSource !== 'ond' &&
        !!selectedManufacturer &&
        !!selectedModel,
    },
  })
  // Handle successful inverter ID lookup
  useEffect(() => {
    if (inverterIdData && inverterIdData.length > 0) {
      if (inverterIdData[0] !== null) {
        setSelectedInverterId(inverterIdData[0])
      } else {
        setSelectedInverterId(null)
        // Show notification that no existing inverter was found
        if (
          dataSource === 'proximal' &&
          selectedManufacturer &&
          selectedModel
        ) {
          notifications.show({
            title: 'No Existing Inverter Found',
            message: `No existing inverter found for ${selectedManufacturer} - ${selectedModel}. Please use "New (Manual)" or "New (OND File)" to create a new inverter.`,
            color: 'orange',
          })
        }
      }
    } else if (inverterIdData && inverterIdData.length === 0) {
      setSelectedInverterId(null)
      // Show notification that no existing inverter was found
      if (dataSource === 'proximal' && selectedManufacturer && selectedModel) {
        notifications.show({
          title: 'No Existing Inverter Found',
          message: `No existing inverter found for ${selectedManufacturer} - ${selectedModel}. Please use "New (Manual)" or "New (OND File)" to create a new inverter.`,
          color: 'orange',
        })
      }
    }
  }, [inverterIdData, dataSource, selectedManufacturer, selectedModel])
  // Fetch inverter details using the inverter ID
  const inverterQueryEnabled =
    dataSource !== 'manual' &&
    dataSource !== 'ond' &&
    selectedInverterId !== null
  const {
    data: inverterDetails,
    isLoading: isLoadingInverterDetails,
    error: inverterDetailsError,
  } = useGetInverters({
    queryParams: {
      inverter_ids: selectedInverterId !== null ? [selectedInverterId] : [],
    },
    queryOptions: {
      enabled: inverterQueryEnabled,
    },
  })
  // Handle successful inverter details fetch
  useEffect(() => {
    if (inverterDetails && inverterDetails.length > 0) {
      const inverterData = inverterDetails[0]
      setInverterParameters(inverterData)
    }
  }, [inverterDetails])

  // --- Fetch Manufacturers for no equipment check ---
  const { data: manufacturers, isLoading: isLoadingManufacturers } =
    useGetProximalInverterManufacturers({
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
  // Handle OND file upload
  const parseOndFileMutation = useParseOndFileMutation()
  const handleOndFileUpload = async (fileToUpload: File) => {
    if (!fileToUpload) {
      // Check the passed argument
      setOndUploadError('Please select an OND file to upload')
      return
    }
    try {
      setOndUploadError(null)
      // Call the mutation to upload and parse the OND file
      const inverterDetailsFromOND =
        await parseOndFileMutation.mutateAsync(fileToUpload)
      // Update all the form fields with the parsed data
      if (inverterDetailsFromOND) {
        // Set manufacturer and model
        setSelectedManufacturer(inverterDetailsFromOND.manufacturer || '')
        setSelectedModel(inverterDetailsFromOND.model || '')
        // Set all inverter parameters
        setInverterParameters(inverterDetailsFromOND)
        // Show success notification
        notifications.show({
          title: 'OND File Processed',
          message: `Successfully extracted inverter data for ${inverterDetailsFromOND.manufacturer} - ${inverterDetailsFromOND.model}`,
          color: 'green',
          icon: <IconCheck size="1.1rem" />,
        })
      }
    } catch (error) {
      console.error('Error processing OND file:', error)
      setOndUploadError(
        error instanceof Error
          ? error.message
          : 'Failed to process OND file. Please check file format and try again.',
      )
    } finally {
      // Upload process complete
    }
  }
  // Form submission handler
  // Create or Update Inverter mutation
  const createInverterMutation = useCreateInverterMutation()
  const handlePvInverterSubmit = async () => {
    try {
      setFieldErrors({})
      setFormSubmitting(true)
      // Determine if we're updating an existing inverter or creating a new one
      const isUpdating =
        dataSource === 'proximal' && selectedInverterId !== null

      // Create the inverter data object
      const inverterData: Inverter = {
        inverter_id: selectedInverterId,
        company_id: userCompanyId || '',
        manufacturer: selectedManufacturer,
        model: selectedModel,
        voltage_mpp_min: voltageMppMin,
        voltage_mpp_max: voltageMppMax,
        voltage_start_up: voltageStartUp,
        voltage_min: voltageMin,
        voltage_max: voltageMax,
        current_max: currentMax,
        power_max_at_reference_temp: powerAtReferenceTemp,
        reference_temp: referenceTemp,
        voltage_nominal_efficiency: voltageNominalEfficiency,
        efficiency_at_low_voltage: efficiencyAtLowVoltage,
        efficiency_at_mid_voltage: efficiencyAtMidVoltage,
        efficiency_at_high_voltage: efficiencyAtHighVoltage,
        power_start_up: powerStartUp,
        power_ac_nominal: powerAcNominal,
        power_dc_nominal: powerDcNominal,
        voltage_dc_nominal: voltageDcNominal,
        c0: c0,
        c1: c1,
        c2: c2,
        c3: c3,
        night_tare: nightTare,
        device_model_id: null,
      }
      // Call the mutation
      const result = await createInverterMutation.mutateAsync(inverterData)
      // Update the inverter ID if this was a new creation
      if (!isUpdating && result.inverter_id) {
        setSelectedInverterId(result.inverter_id)
      }
      // Show success notification
      notifications.show({
        title: isUpdating ? 'Inverter Updated' : 'Inverter Created',
        message: `Successfully ${isUpdating ? 'updated' : 'created'} PV inverter configuration for ${selectedManufacturer} - ${selectedModel}`,
        color: 'green',
        icon: <IconCheck size="1.1rem" />,
      })
    } catch (error) {
      const submitError = getSubmitErrorResult(error)
      setFieldErrors(submitError.fieldErrors)
      // Show error notification
      notifications.show({
        title: 'Error',
        message: submitError.message,
        color: 'red',
      })
    } finally {
      setFormSubmitting(false)
    }
  }
  return (
    <Container size="lg" p="md" style={{ width: '100%' }}>
      <Paper withBorder p="md" radius="md" component="form">
        <Stack>
          <PageTitle
            info={
              <Stack>
                <Text>
                  This page allows you to manage the PV inverters in your
                  company&apos;s component library.
                </Text>
                <Text>
                  You can add new inverters by uploading an OND file or by
                  entering the parameters manually. You can also edit existing
                  inverters.
                </Text>
              </Stack>
            }
          >
            PV Inverters
          </PageTitle>
          <Text c="dimmed" size="sm" mb="md">
            Add or edit components in your company&apos;s component library.
            Equipment can be assigned to specific projects via the projectlevel
            google sheet. If you need access to a project google sheet, please
            contact your Proximal support contact.
          </Text>
          <Text c="dimmed" size="sm" mb="md">
            Choose &quot;Edit Equipment&quot; to modify existing inverter
            specifications, &quot;New Equipment (OND File)&quot; to upload an
            OND file, or &quot;New Equipment (Manual)&quot; to enter your own
            values.
          </Text>
          <Select
            label="Source"
            data={dataSourceOptions}
            value={dataSource}
            allowDeselect={false}
            style={{ width: '100%' }}
            onChange={(value) => {
              setDataSource(value || '')
              setFieldErrors({})
              setSelectedManufacturer('')
              setSelectedModel('')
              setSelectedInverterId(null)
              setOndFile(null)
              setOndUploadError(null)
              resetFormFields()
            }}
            clearable={false}
            required={true}
          />
          {/* Conditional Rendering based on Data Source */}
          {dataSource === 'ond' ? (
            <>
              {/* OND File Upload */}
              <FileInput
                label="Upload OND File"
                placeholder="Click to select OND file"
                accept=".ond,.OND"
                leftSection={<IconUpload size="1rem" />}
                value={ondFile}
                onChange={(value) => {
                  setOndFile(value)
                  if (value) handleOndFileUpload(value)
                }}
                error={ondUploadError}
                required={true}
                style={{ width: '100%' }}
              />
              {ondUploadError && (
                <Alert
                  icon={<IconAlertCircle size="1rem" />}
                  title="Error processing OND file"
                  color="red"
                  mt="sm"
                  withCloseButton
                >
                  {ondUploadError}
                </Alert>
              )}

              {/* Show manufacturer and model fields if OND file has been processed */}
              {selectedManufacturer && selectedModel && (
                <>
                  <TextInput
                    label="Manufacturer"
                    required={true}
                    placeholder="Enter manufacturer name"
                    onChange={(event) => {
                      clearFieldError('manufacturer')
                      setSelectedManufacturer(event.target.value)
                    }}
                    value={selectedManufacturer || ''}
                    error={getFieldError('manufacturer')}
                    style={{ width: '100%' }}
                    description="Parsed from OND file - you can edit if needed"
                  />
                  <TextInput
                    label="Model"
                    required={true}
                    placeholder="Enter model name"
                    onChange={(event) => {
                      clearFieldError('model')
                      setSelectedModel(event.target.value)
                    }}
                    value={selectedModel || ''}
                    error={getFieldError('model')}
                    style={{ width: '100%' }}
                    description="Parsed from OND file - you can edit if needed"
                  />
                </>
              )}
            </>
          ) : dataSource === 'manual' ? (
            <>
              {/* Manual Input Fields */}
              <TextInput
                label="Manufacturer"
                required={true}
                placeholder="Enter manufacturer name"
                onChange={(event) => {
                  clearFieldError('manufacturer')
                  setSelectedManufacturer(event.target.value)
                }}
                value={selectedManufacturer || ''}
                error={getFieldError('manufacturer')}
                style={{ width: '100%' }}
              />
              <TextInput
                label="Model"
                required={true}
                placeholder="Enter model name"
                onChange={(event) => {
                  clearFieldError('model')
                  setSelectedModel(event.target.value)
                }}
                value={selectedModel || ''}
                error={getFieldError('model')}
                style={{ width: '100%' }}
              />
            </>
          ) : dataSource === 'proximal' ? (
            <>
              {self.isLoading ? (
                <Center p="xl">
                  <Loader size="md" />
                  <Text ml="md">Loading user data...</Text>
                </Center>
              ) : !userCompanyId ? (
                <Alert
                  icon={<IconAlertCircle size="1rem" />}
                  title="Company Information Required"
                  color="orange"
                  mb="md"
                >
                  Unable to load company information. Please contact support if
                  this issue persists.
                </Alert>
              ) : noEquipmentAvailable ? (
                <Alert
                  icon={<IconAlertCircle size="1rem" />}
                  title="No Equipment Available"
                  color="orange"
                  mt="md"
                >
                  No PV inverter equipment is available for your company in edit
                  mode. Please use &quot;New (Manual)&quot; or &quot;New (OND
                  File)&quot; to add equipment to your company&apos;s inventory.
                </Alert>
              ) : (
                <EquipmentFilter
                  useGetManufacturers={useGetProximalInverterManufacturers}
                  useGetModels={useGetProximalInverterModels}
                  onManufacturerChange={handlePvInverterManufacturerChange}
                  onModelChange={handlePvInverterModelChange}
                  initialManufacturer={selectedManufacturer}
                  initialModel={selectedModel}
                  company_id={userCompanyId}
                  key={dataSource}
                />
              )}
            </>
          ) : null}
        </Stack>
        {/* Conditional Rendering based on Model or OND Upload */}
        {selectedModel === '' ||
        !selectedManufacturer ||
        noEquipmentAvailable ? null : (
          <>
            <Space h={25}></Space>
            <Divider></Divider>
            <Space h={25}></Space>
            {inverterIdError ? (
              <Alert
                icon={<IconAlertCircle size="1rem" />}
                title="Error looking up inverter ID"
                color="red"
                mb="md"
                withCloseButton
              >
                {inverterIdError instanceof Error
                  ? inverterIdError.message
                  : 'Failed to lookup inverter ID. Please try again.'}
              </Alert>
            ) : inverterDetailsError ? (
              <Alert
                icon={<IconAlertCircle size="1rem" />}
                title="Error loading inverter details"
                color="red"
                mb="md"
                withCloseButton
              >
                {inverterDetailsError instanceof Error
                  ? inverterDetailsError.message
                  : 'Failed to load inverter details. Please try again.'}
              </Alert>
            ) : (isLoadingInverterId || isLoadingInverterDetails) &&
              dataSource !== 'manual' &&
              dataSource !== 'ond' ? (
              <Center p="xl">
                <Loader size="md" />
                <Text ml="md">Loading inverter details...</Text>
              </Center>
            ) : (
              // Only render the form fields when details are loaded or in manual/ond mode
              (dataSource === 'manual' ||
                dataSource === 'ond' ||
                (inverterDetails && inverterDetails.length > 0) ||
                (dataSource === 'proximal' &&
                  selectedInverterId === null &&
                  selectedManufacturer &&
                  selectedModel)) && (
                <>
                  {dataSource === 'proximal' &&
                    selectedInverterId === null &&
                    selectedManufacturer &&
                    selectedModel && (
                      <Alert
                        icon={<IconAlertCircle size="1rem" />}
                        title="Creating New Inverter"
                        color="blue"
                        mb="md"
                      >
                        No existing inverter found for {selectedManufacturer} -{' '}
                        {selectedModel}. You can create a new inverter with
                        these specifications, or switch to &quot;New
                        (Manual)&quot; mode.
                      </Alert>
                    )}
                  <Title order={3} mt="md">
                    Operating Window Parameters
                  </Title>
                  <Grid mt="sm">
                    <Grid.Col span={6}>
                      <NumberInput
                        label="Minimum MPP Voltage (V)"
                        description="Minimum voltage the inverter can search for PV maximum power point"
                        placeholder="Enter minimum MPP voltage"
                        value={voltageMppMin}
                        onChange={(value: string | number) => {
                          clearFieldError('voltage_mpp_min')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setVoltageMppMin(numValue)
                        }}
                        error={getFieldError('voltage_mpp_min')}
                        required
                      />
                    </Grid.Col>
                    <Grid.Col span={6}>
                      <NumberInput
                        label="Maximum MPP Voltage (V)"
                        description="Maximum voltage the inverter can search for PV maximum power point"
                        placeholder="Enter maximum MPP voltage"
                        value={voltageMppMax}
                        onChange={(value: string | number) => {
                          clearFieldError('voltage_mpp_max')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setVoltageMppMax(numValue)
                        }}
                        error={getFieldError('voltage_mpp_max')}
                        required
                      />
                    </Grid.Col>
                    <Grid.Col span={6}>
                      <NumberInput
                        label="Minimum Voltage (V)"
                        description="Minimum voltage of the inverter to stay online"
                        placeholder="Enter minimum voltage"
                        value={voltageMin}
                        onChange={(value: string | number) => {
                          clearFieldError('voltage_min')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setVoltageMin(numValue)
                        }}
                        error={getFieldError('voltage_min')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                    <Grid.Col span={6}>
                      <NumberInput
                        label="Maximum Voltage (V)"
                        description="Maximum voltage of the inverter to stay online"
                        placeholder="Enter maximum voltage"
                        value={voltageMax}
                        onChange={(value: string | number) => {
                          clearFieldError('voltage_max')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setVoltageMax(numValue)
                        }}
                        error={getFieldError('voltage_max')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                    <Grid.Col span={6}>
                      <NumberInput
                        label="Start-up Voltage (V)"
                        description="Voltage at which the inverter starts up, generally >= Minimum Voltage"
                        placeholder="Enter start-up voltage"
                        value={voltageStartUp}
                        onChange={(value: string | number) => {
                          clearFieldError('voltage_start_up')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setVoltageStartUp(numValue)
                        }}
                        error={getFieldError('voltage_start_up')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                    <Grid.Col span={6}>
                      <NumberInput
                        label="Maximum Current (A)"
                        description="Maximum current the inverter can safely handle"
                        placeholder="Enter maximum current"
                        value={currentMax}
                        onChange={(value: string | number) => {
                          clearFieldError('current_max')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setCurrentMax(numValue)
                        }}
                        error={getFieldError('current_max')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                  </Grid>
                  <Title order={3} mt="xl">
                    Temperature-Dependent Max Power Curve
                  </Title>
                  <Text size="sm" c="dimmed" mb="md">
                    Specify how many temperature-power points to include in the
                    curve. Sometimes this value cannot be parsed from OND file
                    and must be found in datasheet and entered manually.
                  </Text>
                  <Grid mb="md">
                    <Grid.Col span={12}>
                      <NumberInput
                        label="Number of Temperature-Power Points"
                        description="How many points to include in the temperature-power curve"
                        placeholder="Enter number of points"
                        value={numTempPowerCurvePoints}
                        onChange={(value: string | number) => {
                          const numValue =
                            typeof value === 'string'
                              ? parseInt(value) || 1
                              : Math.max(1, value)
                          // Update number of points
                          setNumTempCurvePoints(numValue)
                          // Resize arrays if needed
                          if (numValue > referenceTemp.length) {
                            // Add new elements
                            setReferenceTemp([
                              ...referenceTemp,
                              ...Array(numValue - referenceTemp.length).fill(
                                25,
                              ),
                            ])
                            setPowerAtReferenceTemp([
                              ...powerAtReferenceTemp,
                              ...Array(
                                numValue - powerAtReferenceTemp.length,
                              ).fill(0),
                            ])
                          } else if (numValue < referenceTemp.length) {
                            // Remove extra elements
                            setReferenceTemp(referenceTemp.slice(0, numValue))
                            setPowerAtReferenceTemp(
                              powerAtReferenceTemp.slice(0, numValue),
                            )
                          }
                        }}
                        min={1}
                        max={10}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                  </Grid>
                  {/* Dynamic inputs for temperature and power */}
                  {Array.from({ length: numTempPowerCurvePoints }).map(
                    (_, index) => (
                      <Grid key={`temp-power-point-${index}`} mb="sm">
                        <Grid.Col span={6}>
                          <NumberInput
                            label={`Reference Temperature ${index + 1} (°C)`}
                            description="Temperature at which power derating will occur"
                            placeholder="Enter temperature"
                            value={referenceTemp[index] || 0}
                            onChange={(value: string | number) => {
                              clearFieldError('reference_temp')
                              const numValue =
                                typeof value === 'string'
                                  ? parseFloat(value) || 0
                                  : value
                              const newValues = [...referenceTemp]
                              newValues[index] = numValue
                              setReferenceTemp(newValues)
                            }}
                            error={getFieldError('reference_temp')}
                            required
                            style={{ width: '100%' }}
                          />
                        </Grid.Col>
                        <Grid.Col span={6}>
                          <NumberInput
                            label={`Power Max at Reference Temp ${index + 1} (W)`}
                            description="Maximum power output at reference temperature"
                            placeholder="Enter power value"
                            value={powerAtReferenceTemp[index] || 0}
                            onChange={(value: string | number) => {
                              clearFieldError('power_max_at_reference_temp')
                              const numValue =
                                typeof value === 'string'
                                  ? parseFloat(value) || 0
                                  : value
                              const newValues = [...powerAtReferenceTemp]
                              newValues[index] = numValue
                              setPowerAtReferenceTemp(newValues)
                            }}
                            error={getFieldError('power_max_at_reference_temp')}
                            required
                            style={{ width: '100%' }}
                          />
                        </Grid.Col>
                      </Grid>
                    ),
                  )}
                  <Title order={3} mt="xl">
                    Inverter Efficiency Parameters
                  </Title>
                  <Grid>
                    <Grid.Col span={4}>
                      <NumberInput
                        label="Start-up Power (W)"
                        placeholder="Enter start-up power"
                        value={powerStartUp}
                        onChange={(value: string | number) => {
                          clearFieldError('power_start_up')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setPowerStartUp(numValue)
                        }}
                        error={getFieldError('power_start_up')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                    <Grid.Col span={4}>
                      <NumberInput
                        label="AC Nominal Power (W)"
                        placeholder="Enter AC nominal power"
                        value={powerAcNominal}
                        onChange={(value: string | number) => {
                          clearFieldError('power_ac_nominal')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setPowerAcNominal(numValue)
                        }}
                        error={getFieldError('power_ac_nominal')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                    <Grid.Col span={4}>
                      <NumberInput
                        label="DC Nominal Power (W)"
                        placeholder="Enter DC nominal power"
                        value={powerDcNominal}
                        onChange={(value: string | number) => {
                          clearFieldError('power_dc_nominal')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setPowerDcNominal(numValue)
                        }}
                        error={getFieldError('power_dc_nominal')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                    <Grid.Col span={4}>
                      <NumberInput
                        label="DC Nominal Voltage (V)"
                        placeholder="Enter DC nominal voltage"
                        value={voltageDcNominal}
                        onChange={(value: string | number) => {
                          clearFieldError('voltage_dc_nominal')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setVoltageDcNominal(numValue)
                        }}
                        error={getFieldError('voltage_dc_nominal')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                    <Grid.Col span={6}>
                      <NumberInput
                        label="Night Tare (W)"
                        placeholder="Enter night tare"
                        value={nightTare}
                        onChange={(value: string | number) => {
                          clearFieldError('night_tare')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setNightTare(numValue)
                        }}
                        error={getFieldError('night_tare')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                  </Grid>
                  <Title order={3} mt="xl">
                    Efficiency Coefficients
                  </Title>
                  <Text size="sm" c="dimmed" mb="md">
                    Calculated coefficients for the Sandia Inverter Efficiency
                    model. If you do not know what these are, please upload an
                    OND file instead. If you upload an OND file, Proximal will
                    calculate these parameters automatically.
                  </Text>
                  <Grid>
                    <Grid.Col span={3}>
                      <NumberInput
                        label="C0"
                        placeholder="Enter C0 coefficient"
                        value={c0}
                        onChange={(value: string | number) => {
                          clearFieldError('c0')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setC0(numValue)
                        }}
                        error={getFieldError('c0')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                    <Grid.Col span={3}>
                      <NumberInput
                        label="C1"
                        placeholder="Enter C1 coefficient"
                        value={c1}
                        onChange={(value: string | number) => {
                          clearFieldError('c1')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setC1(numValue)
                        }}
                        error={getFieldError('c1')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                    <Grid.Col span={3}>
                      <NumberInput
                        label="C2"
                        placeholder="Enter C2 coefficient"
                        value={c2}
                        onChange={(value: string | number) => {
                          clearFieldError('c2')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setC2(numValue)
                        }}
                        error={getFieldError('c2')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                    <Grid.Col span={3}>
                      <NumberInput
                        label="C3"
                        placeholder="Enter C3 coefficient"
                        value={c3}
                        onChange={(value: string | number) => {
                          clearFieldError('c3')
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setC3(numValue)
                        }}
                        error={getFieldError('c3')}
                        required
                        style={{ width: '100%' }}
                      />
                    </Grid.Col>
                  </Grid>
                  <Title order={3} mt="xl">
                    Efficiency Reference Parameters
                  </Title>
                  <Text size="sm" c="dimmed" mb="md">
                    Define the three reference voltages for efficiency curves
                    and specify the number of efficiency curve points. Each
                    curve point represents a [DC Power Input, AC Power Output]
                    pair at each voltage level.
                  </Text>
                  <Grid>
                    <Grid.Col span={4}>
                      <NumberInput
                        label="Low Reference Voltage (V)"
                        value={voltageNominalEfficiency[0]}
                        min={0}
                        max={2000}
                        onChange={(value) => {
                          clearFieldError('voltage_nominal_efficiency')
                          const newArray = [...voltageNominalEfficiency]
                          newArray[0] =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value || 0
                          setVoltageNominalEfficiency(newArray)
                        }}
                        error={getFieldError('voltage_nominal_efficiency')}
                      />
                    </Grid.Col>
                    <Grid.Col span={4}>
                      <NumberInput
                        label="Medium Reference Voltage (V)"
                        value={voltageNominalEfficiency[1]}
                        min={0}
                        max={2000}
                        onChange={(value) => {
                          clearFieldError('voltage_nominal_efficiency')
                          const newArray = [...voltageNominalEfficiency]
                          newArray[1] =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value || 0
                          setVoltageNominalEfficiency(newArray)
                        }}
                        error={getFieldError('voltage_nominal_efficiency')}
                      />
                    </Grid.Col>
                    <Grid.Col span={4}>
                      <NumberInput
                        label="High Reference Voltage (V)"
                        value={voltageNominalEfficiency[2]}
                        min={0}
                        max={2000}
                        onChange={(value) => {
                          clearFieldError('voltage_nominal_efficiency')
                          const newArray = [...voltageNominalEfficiency]
                          newArray[2] =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value || 0
                          setVoltageNominalEfficiency(newArray)
                        }}
                        error={getFieldError('voltage_nominal_efficiency')}
                      />
                    </Grid.Col>
                    <Grid.Col span={12}>
                      {/* Individual controls for each voltage level */}
                      <Grid>
                        <Grid.Col span={4}>
                          <NumberInput
                            label="Low Voltage Points"
                            description="Number of points for low voltage curve"
                            placeholder="Points"
                            value={numLowVoltagePoints}
                            min={1}
                            max={20}
                            onChange={(value: string | number) => {
                              const numValue =
                                typeof value === 'string'
                                  ? parseInt(value) || 1
                                  : Math.max(1, value)
                              setNumLowVoltagePoints(numValue)

                              // Resize array if needed
                              setEfficiencyAtLowVoltage((prev) =>
                                resizeEfficiencyArray(prev, numValue),
                              )
                            }}
                          />
                        </Grid.Col>
                        <Grid.Col span={4}>
                          <NumberInput
                            label="Mid Voltage Points"
                            description="Number of points for mid voltage curve"
                            placeholder="Points"
                            value={numMidVoltagePoints}
                            min={1}
                            max={20}
                            onChange={(value: string | number) => {
                              const numValue =
                                typeof value === 'string'
                                  ? parseInt(value) || 1
                                  : Math.max(1, value)
                              setNumMidVoltagePoints(numValue)

                              // Resize array if needed
                              setEfficiencyAtMidVoltage((prev) =>
                                resizeEfficiencyArray(prev, numValue),
                              )
                            }}
                          />
                        </Grid.Col>
                        <Grid.Col span={4}>
                          <NumberInput
                            label="High Voltage Points"
                            description="Number of points for high voltage curve"
                            placeholder="Points"
                            value={numHighVoltagePoints}
                            min={1}
                            max={20}
                            onChange={(value: string | number) => {
                              const numValue =
                                typeof value === 'string'
                                  ? parseInt(value) || 1
                                  : Math.max(1, value)
                              setNumHighVoltagePoints(numValue)

                              // Resize array if needed
                              setEfficiencyAtHighVoltage((prev) =>
                                resizeEfficiencyArray(prev, numValue),
                              )
                            }}
                          />
                        </Grid.Col>
                      </Grid>
                    </Grid.Col>
                  </Grid>
                  <Grid>
                    <Grid.Col span={4}>
                      <Text size="sm" fw={500} mb="xs" c="blue">
                        Low Voltage ({voltageNominalEfficiency[0] || 0}V)
                      </Text>
                    </Grid.Col>
                    <Grid.Col span={4}>
                      <Text size="sm" fw={500} mb="xs" c="orange">
                        Medium Voltage ({voltageNominalEfficiency[1] || 0}
                        V)
                      </Text>
                    </Grid.Col>
                    <Grid.Col span={4}>
                      <Text size="sm" fw={500} mb="xs" c="red">
                        High Voltage ({voltageNominalEfficiency[2] || 0}V)
                      </Text>
                    </Grid.Col>
                  </Grid>
                  {/* Render separate sections for each voltage level */}
                  <div>
                    {/* Low Voltage Section */}
                    <Text size="lg" fw={600} mb="md" c="blue">
                      Low Voltage ({voltageNominalEfficiency[0] || 0}V)
                      Efficiency Points
                    </Text>
                    {Array.from({ length: numLowVoltagePoints }).map(
                      (_, index) => (
                        <Grid key={`low-voltage-point-${index}`} mb="md">
                          <Grid.Col span={12}>
                            <Text size="sm" fw={500} mb="xs">
                              Point {index + 1}
                            </Text>
                            <Grid>
                              <Grid.Col span={6}>
                                <NumberInput
                                  label="DC Power (W)"
                                  placeholder="DC power input"
                                  value={
                                    efficiencyAtLowVoltage[index]?.[0] || 0
                                  }
                                  onChange={(value: string | number) => {
                                    clearFieldError('efficiency_at_low_voltage')
                                    const numValue =
                                      typeof value === 'string'
                                        ? parseFloat(value) || 0
                                        : value
                                    const newValues = [
                                      ...efficiencyAtLowVoltage,
                                    ]
                                    if (!newValues[index]) {
                                      newValues[index] = [0, 0]
                                    }
                                    newValues[index][0] = numValue
                                    setEfficiencyAtLowVoltage(newValues)
                                  }}
                                  error={getFieldError(
                                    'efficiency_at_low_voltage',
                                  )}
                                  required
                                />
                              </Grid.Col>
                              <Grid.Col span={6}>
                                <NumberInput
                                  label="AC Power (W)"
                                  placeholder="AC power output"
                                  value={
                                    efficiencyAtLowVoltage[index]?.[1] || 0
                                  }
                                  onChange={(value: string | number) => {
                                    clearFieldError('efficiency_at_low_voltage')
                                    const numValue =
                                      typeof value === 'string'
                                        ? parseFloat(value) || 0
                                        : value
                                    const newValues = [
                                      ...efficiencyAtLowVoltage,
                                    ]
                                    if (!newValues[index]) {
                                      newValues[index] = [0, 0]
                                    }
                                    newValues[index][1] = numValue
                                    setEfficiencyAtLowVoltage(newValues)
                                  }}
                                  error={getFieldError(
                                    'efficiency_at_low_voltage',
                                  )}
                                  required
                                />
                              </Grid.Col>
                            </Grid>
                          </Grid.Col>
                        </Grid>
                      ),
                    )}

                    {/* Mid Voltage Section */}
                    <Text size="lg" fw={600} mb="md" c="orange" mt="xl">
                      Medium Voltage ({voltageNominalEfficiency[1] || 0}V)
                      Efficiency Points
                    </Text>
                    {Array.from({ length: numMidVoltagePoints }).map(
                      (_, index) => (
                        <Grid key={`mid-voltage-point-${index}`} mb="md">
                          <Grid.Col span={12}>
                            <Text size="sm" fw={500} mb="xs">
                              Point {index + 1}
                            </Text>
                            <Grid>
                              <Grid.Col span={6}>
                                <NumberInput
                                  label="DC Power (W)"
                                  placeholder="DC power input"
                                  value={
                                    efficiencyAtMidVoltage[index]?.[0] || 0
                                  }
                                  onChange={(value: string | number) => {
                                    clearFieldError('efficiency_at_mid_voltage')
                                    const numValue =
                                      typeof value === 'string'
                                        ? parseFloat(value) || 0
                                        : value
                                    const newValues = [
                                      ...efficiencyAtMidVoltage,
                                    ]
                                    if (!newValues[index]) {
                                      newValues[index] = [0, 0]
                                    }
                                    newValues[index][0] = numValue
                                    setEfficiencyAtMidVoltage(newValues)
                                  }}
                                  error={getFieldError(
                                    'efficiency_at_mid_voltage',
                                  )}
                                  required
                                />
                              </Grid.Col>
                              <Grid.Col span={6}>
                                <NumberInput
                                  label="AC Power (W)"
                                  placeholder="AC power output"
                                  value={
                                    efficiencyAtMidVoltage[index]?.[1] || 0
                                  }
                                  onChange={(value: string | number) => {
                                    clearFieldError('efficiency_at_mid_voltage')
                                    const numValue =
                                      typeof value === 'string'
                                        ? parseFloat(value) || 0
                                        : value
                                    const newValues = [
                                      ...efficiencyAtMidVoltage,
                                    ]
                                    if (!newValues[index]) {
                                      newValues[index] = [0, 0]
                                    }
                                    newValues[index][1] = numValue
                                    setEfficiencyAtMidVoltage(newValues)
                                  }}
                                  error={getFieldError(
                                    'efficiency_at_mid_voltage',
                                  )}
                                  required
                                />
                              </Grid.Col>
                            </Grid>
                          </Grid.Col>
                        </Grid>
                      ),
                    )}

                    {/* High Voltage Section */}
                    <Text size="lg" fw={600} mb="md" c="red" mt="xl">
                      High Voltage ({voltageNominalEfficiency[2] || 0}V)
                      Efficiency Points
                    </Text>
                    {Array.from({ length: numHighVoltagePoints }).map(
                      (_, index) => (
                        <Grid key={`high-voltage-point-${index}`} mb="md">
                          <Grid.Col span={12}>
                            <Text size="sm" fw={500} mb="xs">
                              Point {index + 1}
                            </Text>
                            <Grid>
                              <Grid.Col span={6}>
                                <NumberInput
                                  label="DC Power (W)"
                                  placeholder="DC power input"
                                  value={
                                    efficiencyAtHighVoltage[index]?.[0] || 0
                                  }
                                  onChange={(value: string | number) => {
                                    clearFieldError(
                                      'efficiency_at_high_voltage',
                                    )
                                    const numValue =
                                      typeof value === 'string'
                                        ? parseFloat(value) || 0
                                        : value
                                    const newValues = [
                                      ...efficiencyAtHighVoltage,
                                    ]
                                    if (!newValues[index]) {
                                      newValues[index] = [0, 0]
                                    }
                                    newValues[index][0] = numValue
                                    setEfficiencyAtHighVoltage(newValues)
                                  }}
                                  error={getFieldError(
                                    'efficiency_at_high_voltage',
                                  )}
                                  required
                                />
                              </Grid.Col>
                              <Grid.Col span={6}>
                                <NumberInput
                                  label="AC Power (W)"
                                  placeholder="AC power output"
                                  value={
                                    efficiencyAtHighVoltage[index]?.[1] || 0
                                  }
                                  onChange={(value: string | number) => {
                                    clearFieldError(
                                      'efficiency_at_high_voltage',
                                    )
                                    const numValue =
                                      typeof value === 'string'
                                        ? parseFloat(value) || 0
                                        : value
                                    const newValues = [
                                      ...efficiencyAtHighVoltage,
                                    ]
                                    if (!newValues[index]) {
                                      newValues[index] = [0, 0]
                                    }
                                    newValues[index][1] = numValue
                                    setEfficiencyAtHighVoltage(newValues)
                                  }}
                                  error={getFieldError(
                                    'efficiency_at_high_voltage',
                                  )}
                                  required
                                />
                              </Grid.Col>
                            </Grid>
                          </Grid.Col>
                        </Grid>
                      ),
                    )}
                  </div>
                  {/* Form Submit Button */}
                  <Group style={{ justifyContent: 'flex-end' }} mt="xl">
                    <Button
                      onClick={() => {
                        if (
                          dataSource === 'proximal' &&
                          selectedInverterId !== null
                        ) {
                          setModalOpened(true)
                        } else {
                          handlePvInverterSubmit()
                        }
                      }}
                      loading={formSubmitting}
                      disabled={!selectedManufacturer || !selectedModel}
                      color={
                        dataSource === 'proximal' && selectedInverterId !== null
                          ? 'orange'
                          : 'blue'
                      }
                      leftSection={
                        dataSource === 'proximal' &&
                        selectedInverterId !== null ? (
                          <IconAlertTriangle size={16} />
                        ) : undefined
                      }
                    >
                      {dataSource === 'proximal' && selectedInverterId !== null
                        ? 'Update Inverter'
                        : 'Create Inverter'}
                    </Button>
                  </Group>
                  <ConfirmationModal
                    opened={modalOpened}
                    onClose={() => setModalOpened(false)}
                    onConfirm={() => {
                      handlePvInverterSubmit()
                      setModalOpened(false)
                    }}
                    title="Confirm Update"
                    message="Updating this inverter will affect the expected energy model for all projects that use it. Are you sure you want to continue?"
                  />
                </>
              )
            )}
            {/* Display a message when no data is found */}
            {!isLoadingInverterId &&
              !isLoadingInverterDetails &&
              ((inverterIdData &&
                inverterIdData.length > 0 &&
                inverterIdData[0] === null) ||
                !inverterDetails ||
                (inverterDetails && inverterDetails.length === 0)) &&
              dataSource === 'proximal' && (
                <Alert
                  icon={<IconAlertCircle size="1rem" />}
                  title="No data found"
                  color="blue"
                  mt="md"
                  withCloseButton
                >
                  No inverter details found for the selected manufacturer and
                  model. You can enter values manually or select a different
                  model.
                </Alert>
              )}
          </>
        )}
      </Paper>
    </Container>
  )
}
export default PVInverterSettings
