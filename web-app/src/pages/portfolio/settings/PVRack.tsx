import { useGetUsers } from '@/api/admin'
import {
  PVRackings,
  useCreateOrUpdatePVRackingMutation,
  useGetPVRackingIdsByManufacturerAndModel,
  useGetProximalPVRackDetails,
  useGetProximalPVRackManufacturers,
  useGetProximalPVRackModels,
} from '@/api/v1/operational/pv_racks'
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
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconCheck,
} from '@tabler/icons-react'
import { UseQueryOptions } from '@tanstack/react-query'
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
  ]
  const [dataSource, setDataSource] = useState<string>(
    dataSourceOptions[0].value,
  )
  const [modalOpened, setModalOpened] = useState(false)

  // --- State ---
  const [selectedManufacturer, setSelectedManufacturer] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [selectedRackingId, setSelectedRackingId] = useState<number | null>(
    null,
  )
  const [rackingTypeId] = useState<number>(1) // Default to 1
  const [maxRotationAngle, setMaxRotationAngle] = useState<number>(60)
  const [minRotationAngle, setMinRotationAngle] = useState<number>(-60)
  const [windStowAngle, setWindStowAngle] = useState<number>(60)
  const [windStowThreshold, setWindStowThreshold] = useState<number>(49.17)
  const [hailStowAngle, setHailStowAngle] = useState<number>(60)
  const [snowStowAngle, setSnowStowAngle] = useState<number>(60)
  const [formSubmitting, setFormSubmitting] = useState<boolean>(false)

  // --- Handlers  ---
  const handleManufacturerChange = (value: string | null) => {
    setSelectedManufacturer(value || '')
    setSelectedModel('')
    setSelectedRackingId(null)
  }

  const handleModelChange = (value: string | null) => {
    setSelectedModel(value || '')
    // When changing models on manual mode, don't reset fields
    if (dataSource === 'manual') {
      return
    }
    // Reset fields until data loads
    setMaxRotationAngle(0)
    setMinRotationAngle(0)
    setWindStowAngle(0)
    setWindStowThreshold(0)
    setHailStowAngle(0)
    setSnowStowAngle(0)
    // Reset the racking ID when model changes
    setSelectedRackingId(null)
  }

  // --- Create wrapper hooks for EquipmentFilter ---
  const useWrappedGetManufacturers = ({
    queryParams = {},
    queryOptions = {},
  }: {
    queryParams?: object
    queryOptions?: Partial<UseQueryOptions>
  }) => {
    return useGetProximalPVRackManufacturers({
      queryParams: {
        ...queryParams,
        ...(dataSource === 'proximal' && userCompanyId
          ? { company_id: userCompanyId }
          : {}),
      },
      queryOptions: {
        ...queryOptions,
        enabled: dataSource === 'proximal' ? !!userCompanyId : true,
      },
    })
  }

  const useWrappedGetModels = ({
    queryParams = {},
    queryOptions = {},
  }: {
    queryParams?: { manufacturer?: string | null }
    queryOptions?: Partial<UseQueryOptions>
  }) => {
    return useGetProximalPVRackModels({
      queryParams: {
        ...queryParams,
        ...(dataSource === 'proximal' && userCompanyId
          ? { company_id: userCompanyId }
          : {}),
      },
      queryOptions: {
        ...queryOptions,
        enabled:
          dataSource === 'proximal'
            ? !!userCompanyId && queryOptions?.enabled !== false
            : queryOptions?.enabled !== false,
      },
    })
  }

  // --- API Calls with Company Filtering ---
  const { data: manufacturers, isLoading: isLoadingManufacturers } =
    useWrappedGetManufacturers({
      queryOptions: {
        enabled: dataSource === 'proximal' && !!userCompanyId,
      },
    })

  // First fetch racking ID based on manufacturer and model
  const {
    data: rackingIdData,
    isLoading: isLoadingRackingId,
    error: rackingIdError,
  } = useGetPVRackingIdsByManufacturerAndModel({
    queryParams: {
      manufacturers: selectedManufacturer ? [selectedManufacturer] : [],
      models: selectedModel ? [selectedModel] : [],
      ...(dataSource === 'proximal' && userCompanyId
        ? { company_id: userCompanyId }
        : {}),
    },
    queryOptions: {
      enabled:
        dataSource !== 'manual' &&
        !!selectedManufacturer &&
        !!selectedModel &&
        (dataSource !== 'proximal' || !!userCompanyId),
    },
  })

  // Handle successful racking ID lookup
  useEffect(() => {
    if (rackingIdData && rackingIdData.length > 0) {
      if (rackingIdData[0] !== null) {
        setSelectedRackingId(rackingIdData[0])
      } else {
        setSelectedRackingId(null)
      }
    }
  }, [rackingIdData])

  // Create or Update PV Racking mutation
  const createOrUpdatePVRackingMutation = useCreateOrUpdatePVRackingMutation()

  // Form submission handler
  const handleSubmit = async () => {
    try {
      setFormSubmitting(true)

      // Create the racking data object
      const rackingData: PVRackings = {
        racking_id: selectedRackingId || null, // Use null for new racks to let database generate ID
        racking_type_id: rackingTypeId,
        manufacturer: selectedManufacturer,
        model: selectedModel,

        max_rotation_angle: maxRotationAngle,
        min_rotation_angle: minRotationAngle,
        wind_stow_angle: windStowAngle,
        wind_stow_threshold: windStowThreshold,
        hail_stow_angle: hailStowAngle,
        snow_stow_angle: snowStowAngle,
      }

      // Call the mutation
      const result =
        await createOrUpdatePVRackingMutation.mutateAsync(rackingData)

      // Update the racking ID if this was a new creation
      if (!selectedRackingId && result.racking_id) {
        setSelectedRackingId(result.racking_id)
      }

      // Show success notification
      notifications.show({
        title: selectedRackingId ? 'Rack Updated' : 'Rack Created',
        message: `Successfully ${selectedRackingId ? 'updated' : 'created'} PV rack configuration for ${selectedManufacturer} - ${selectedModel}`,
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
            : 'Failed to save rack configuration',
        color: 'red',
      })
    } finally {
      setFormSubmitting(false)
    }
  }

  // Then fetch rack details using the racking ID
  const {
    data: rackDetails,
    isLoading: isLoadingRackDetails,
    error: rackDetailsError,
  } = useGetProximalPVRackDetails({
    queryParams: {
      racking_ids: selectedRackingId ? [selectedRackingId] : [],
      ...(dataSource === 'proximal' && userCompanyId
        ? { company_id: userCompanyId }
        : {}),
    },
    queryOptions: {
      enabled:
        dataSource !== 'manual' &&
        !!selectedRackingId &&
        (dataSource !== 'proximal' || !!userCompanyId),
    },
  })

  // Handle successful rack details fetch
  useEffect(() => {
    if (rackDetails && rackDetails.length > 0) {
      const rackData = rackDetails[0]
      setMaxRotationAngle(rackData.max_rotation_angle)
      setMinRotationAngle(rackData.min_rotation_angle)
      setWindStowAngle(rackData.wind_stow_angle)
      setWindStowThreshold(rackData.wind_stow_threshold)
      setHailStowAngle(rackData.hail_stow_angle)
      setSnowStowAngle(rackData.snow_stow_angle)
    }
  }, [rackDetails])

  // Check if no equipment is available in edit mode
  const noEquipmentAvailable =
    dataSource === 'proximal' &&
    !isLoadingManufacturers &&
    manufacturers &&
    manufacturers.length === 0

  return (
    <Container size="lg" p="md" style={{ width: '100%' }}>
      <Paper withBorder p="md" radius="md" component="form">
        <Stack>
          <PageTitle
            info={
              <Stack>
                <Text>
                  This page allows you to manage the PV racks in your
                  company&apos;s component library.
                </Text>
                <Text>
                  You can add new racks by entering the parameters manually. You
                  can also edit existing racks.
                </Text>
              </Stack>
            }
          >
            PV Racks
          </PageTitle>
          <Text c="dimmed" size="sm" mb="md">
            Add or edit components in your company&apos;s component library.
            Equipment can be assigned to specific projects via the projectlevel
            google sheet. If you need access to a project google sheet, please
            contact your Proximal support contact.
          </Text>
          <Text c="dimmed" size="sm" mb="md">
            Choose &quot;Edit Equipment&quot; to modify existing rack
            specifications, or &quot;New Equipment (Manual)&quot; to enter your
            own values.
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
              setSelectedRackingId(null)
              setMaxRotationAngle(60)
              setMinRotationAngle(-60)
              setWindStowAngle(60)
              setWindStowThreshold(49.17)
              setHailStowAngle(60)
              setSnowStowAngle(60)
            }}
            clearable={false}
            required={true}
          />

          {/* Show message when no equipment is available in edit mode */}
          {noEquipmentAvailable && (
            <Alert
              icon={<IconAlertCircle size="1rem" />}
              title="No Equipment Available"
              color="orange"
              mt="md"
            >
              No PV rack equipment is available for your company in edit mode.
              Please use &quot;New (Manual)&quot; to add equipment to your
              company&apos;s inventory.
            </Alert>
          )}

          {/* Conditional Rendering based on Data Source */}
          {dataSource === 'manual' ? (
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
              />
              <TextInput
                label="Model"
                required={true}
                placeholder="Enter model name"
                onChange={(event) => setSelectedModel(event.target.value)}
                value={selectedModel || ''}
              />
            </>
          ) : dataSource === 'proximal' && !noEquipmentAvailable ? (
            <>
              <EquipmentFilter
                useGetManufacturers={useWrappedGetManufacturers}
                useGetModels={useWrappedGetModels}
                onManufacturerChange={handleManufacturerChange}
                onModelChange={handleModelChange}
                initialManufacturer={selectedManufacturer}
                initialModel={selectedModel}
                company_id={userCompanyId}
                key={dataSource}
              />
            </>
          ) : null}
        </Stack>

        {/* Conditional Rendering based on Model */}
        {selectedModel === '' || noEquipmentAvailable ? null : (
          <>
            <Space h={25}></Space>
            <Divider></Divider>
            <Space h={25}></Space>
            {rackingIdError ? (
              <Alert
                icon={<IconAlertCircle size="1rem" />}
                title="Error looking up racking ID"
                color="red"
                mb="md"
                withCloseButton
              >
                {rackingIdError instanceof Error
                  ? rackingIdError.message
                  : 'Failed to lookup racking ID. Please try again.'}
              </Alert>
            ) : rackDetailsError ? (
              <Alert
                icon={<IconAlertCircle size="1rem" />}
                title="Error loading rack details"
                color="red"
                mb="md"
                withCloseButton
              >
                {rackDetailsError instanceof Error
                  ? rackDetailsError.message
                  : 'Failed to load rack details. Please try again.'}
              </Alert>
            ) : (isLoadingRackingId || isLoadingRackDetails) &&
              dataSource !== 'manual' ? (
              <Center p="xl">
                <Loader size="md" />
                <Text ml="md">Loading rack details...</Text>
              </Center>
            ) : (
              // Only render the form fields when details are loaded or in manual mode
              (dataSource === 'manual' ||
                (rackDetails && rackDetails.length > 0)) && (
                <>
                  <Grid>
                    <Grid.Col span={6}>
                      <NumberInput
                        label="Maximum Rotation Angle (degrees)"
                        placeholder="Enter maximum rotation angle"
                        step={1.0}
                        max={90}
                        min={0}
                        value={maxRotationAngle}
                        onChange={(value: string | number) => {
                          // Convert the value to a number before passing to setState
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setMaxRotationAngle(numValue)
                        }}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Minimum Rotation Angle (degrees)"
                        placeholder="Enter minimum rotation angle"
                        step={1.0}
                        max={0}
                        min={-90}
                        value={minRotationAngle}
                        onChange={(value: string | number) => {
                          // Convert the value to a number before passing to setState
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setMinRotationAngle(numValue)
                        }}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Wind Stow Angle (degrees)"
                        placeholder="Enter wind stow angle"
                        step={1.0}
                        max={90}
                        min={0}
                        value={windStowAngle}
                        onChange={(value: string | number) => {
                          // Convert the value to a number before passing to setState
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setWindStowAngle(numValue)
                        }}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Wind Stow Threshold (m/s)"
                        placeholder="Enter wind stow threshold"
                        step={1.0}
                        min={0}
                        value={windStowThreshold}
                        onChange={(value: string | number) => {
                          // Convert the value to a number before passing to setState
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setWindStowThreshold(numValue)
                        }}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Hail Stow Angle (degrees)"
                        placeholder="Enter hail stow angle"
                        step={1.0}
                        max={90}
                        min={0}
                        value={hailStowAngle}
                        onChange={(value: string | number) => {
                          // Convert the value to a number before passing to setState
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setHailStowAngle(numValue)
                        }}
                      />
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <NumberInput
                        label="Snow Stow Angle (degrees)"
                        placeholder="Enter snow stow angle"
                        step={1.0}
                        max={90}
                        min={0}
                        value={snowStowAngle}
                        onChange={(value: string | number) => {
                          // Convert the value to a number before passing to setState
                          const numValue =
                            typeof value === 'string'
                              ? parseFloat(value) || 0
                              : value
                          setSnowStowAngle(numValue)
                        }}
                      />
                    </Grid.Col>
                  </Grid>

                  {/* Form Submit Button */}
                  <Group style={{ justifyContent: 'flex-end' }} mt="xl">
                    <Button
                      onClick={() => {
                        if (selectedRackingId) {
                          setModalOpened(true)
                        } else {
                          handleSubmit()
                        }
                      }}
                      loading={formSubmitting}
                      disabled={!selectedManufacturer || !selectedModel}
                      color={selectedRackingId ? 'orange' : 'blue'}
                      leftSection={
                        selectedRackingId ? (
                          <IconAlertTriangle size={16} />
                        ) : undefined
                      }
                    >
                      {selectedRackingId ? 'Update Rack' : 'Create Rack'}
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
                    message="Updating this rack will affect the expected energy model for all projects that use it. Are you sure you want to continue?"
                  />
                </>
              )
            )}
            {/* Display a message when no data is found for selected equipment */}
            {!isLoadingRackingId &&
              !isLoadingRackDetails &&
              ((rackingIdData &&
                rackingIdData.length > 0 &&
                rackingIdData[0] === null) ||
                !rackDetails ||
                (rackDetails && rackDetails.length === 0)) &&
              dataSource !== 'manual' && (
                <Alert
                  icon={<IconAlertCircle size="1rem" />}
                  title="No data found"
                  color="blue"
                  mt="md"
                  withCloseButton
                >
                  No rack details found for the selected manufacturer and model
                  in your company&apos;s inventory. You can enter values
                  manually by switching to &quot;New (Manual)&quot; mode or
                  select a different model.
                </Alert>
              )}
          </>
        )}
      </Paper>
    </Container>
  )
}

export default Page
