import { useGetUsers } from '@/api/admin'
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
import { useUser } from '@clerk/clerk-react'
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
import { useEffect, useState } from 'react'

const Page = () => {
  // --- User and Company Info ---
  const { user } = useUser()
  const currentUser = useGetUsers({
    queryParams: { user_ids: [user?.id || ''] },
    queryOptions: { enabled: !!user?.id },
  })
  const userCompanyId = currentUser.data?.[0]?.company_id

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
    // Operating window parameters
    setVoltageMppMin(inverterData.voltage_mpp_min)
    setVoltageMppMax(inverterData.voltage_mpp_max)
    setVoltageStartUp(inverterData.voltage_start_up)
    setVoltageMin(inverterData.voltage_min)
    setVoltageMax(inverterData.voltage_max)
    setCurrentMax(inverterData.current_max)

    // Temperature-dependent power characteristics
    if (
      inverterData.power_max_at_reference_temp &&
      inverterData.reference_temp
    ) {
      setNumTempCurvePoints(
        inverterData.power_max_at_reference_temp.length || 1,
      )
      setPowerAtReferenceTemp(inverterData.power_max_at_reference_temp)
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
  const handleManufacturerChange = (value: string | null) => {
    setSelectedManufacturer(value || '')
    setSelectedModel('')
    setSelectedInverterId(null)
    resetFormFields()
  }
  const handleModelChange = (value: string | null) => {
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
      queryParams: {
        ...(userCompanyId ? { company_id: userCompanyId } : {}),
      },
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
  const handleSubmit = async () => {
    try {
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
      // Show error notification
      notifications.show({
        title: 'Error',
        message:
          error instanceof Error
            ? error.message
            : 'Failed to save inverter configuration',
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
                  company's component library.
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
            Add or edit components in your company's component library.
            Equipment can be assigned to specific projects via the projectlevel
            google sheet. If you need access to a project google sheet, please
            contact your Proximal support contact.
          </Text>
          <Text c="dimmed" size="sm" mb="md">
            Choose "Edit Equipment" to modify existing inverter specifications,
            "New Equipment (OND File)" to upload an OND file, or "New Equipment
            (Manual)" to enter your own values.
          </Text>
          <Select
            label="Source"
            data={dataSourceOptions}
            value={dataSource}
            allowDeselect={false}
            style={{ width: '100%' }}
            onChange={(value) => {
              setDataSource(value || '')
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
                    onChange={(event) =>
                      setSelectedManufacturer(event.target.value)
                    }
                    value={selectedManufacturer || ''}
                    style={{ width: '100%' }}
                    description="Parsed from OND file - you can edit if needed"
                  />
                  <TextInput
                    label="Model"
                    required={true}
                    placeholder="Enter model name"
                    onChange={(event) => setSelectedModel(event.target.value)}
                    value={selectedModel || ''}
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
                onChange={(event) =>
                  setSelectedManufacturer(event.target.value)
                }
                value={selectedManufacturer || ''}
                style={{ width: '100%' }}
              />
              <TextInput
                label="Model"
                required={true}
                placeholder="Enter model name"
                onChange={(event) => setSelectedModel(event.target.value)}
                value={selectedModel || ''}
                style={{ width: '100%' }}
              />
            </>
          ) : dataSource === 'proximal' ? (
            <>
              {currentUser.isLoading ? (
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
                  mode. Please use "New (Manual)" or "New (OND File)" to add
                  equipment to your company's inventory.
                </Alert>
              ) : (
                <EquipmentFilter
                  useGetManufacturers={useGetProximalInverterManufacturers}
                  useGetModels={useGetProximalInverterModels}
                  onManufacturerChange={handleManufacturerChange}
                  onModelChange={handleModelChange}
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
                        these specifications, or switch to "New (Manual)" mode.
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setVoltageMppMin(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setVoltageMppMax(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setVoltageMin(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setVoltageMax(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setVoltageStartUp(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setCurrentMax(numValue)
                        }}
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
                              const numValue =
                                typeof value === 'string'
                                  ? parseFloat(value) || 0
                                  : value
                              const newValues = [...referenceTemp]
                              newValues[index] = numValue
                              setReferenceTemp(newValues)
                            }}
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
                              const numValue =
                                typeof value === 'string'
                                  ? parseFloat(value) || 0
                                  : value
                              const newValues = [...powerAtReferenceTemp]
                              newValues[index] = numValue
                              setPowerAtReferenceTemp(newValues)
                            }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setPowerStartUp(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setPowerAcNominal(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setPowerDcNominal(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setVoltageDcNominal(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setNightTare(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setC0(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setC1(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setC2(numValue)
                        }}
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
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setC3(numValue)
                        }}
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
                          const newArray = [...voltageNominalEfficiency]
                          newArray[0] =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value || 0
                          setVoltageNominalEfficiency(newArray)
                        }}
                      />
                    </Grid.Col>
                    <Grid.Col span={4}>
                      <NumberInput
                        label="Medium Reference Voltage (V)"
                        value={voltageNominalEfficiency[1]}
                        min={0}
                        max={2000}
                        onChange={(value) => {
                          const newArray = [...voltageNominalEfficiency]
                          newArray[1] =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value || 0
                          setVoltageNominalEfficiency(newArray)
                        }}
                      />
                    </Grid.Col>
                    <Grid.Col span={4}>
                      <NumberInput
                        label="High Reference Voltage (V)"
                        value={voltageNominalEfficiency[2]}
                        min={0}
                        max={2000}
                        onChange={(value) => {
                          const newArray = [...voltageNominalEfficiency]
                          newArray[2] =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value || 0
                          setVoltageNominalEfficiency(newArray)
                        }}
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
                          handleSubmit()
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
                      handleSubmit()
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
export default Page
