import { useGetCompanies } from '@/api/v1/admin/companies'
import { useGetProjectTypes } from '@/api/v1/operational/project_types'
import { ProjectCreate, useCreateProject } from '@/api/v1/operational/projects'
import {
  ActionIcon,
  AppShell,
  Button,
  Container,
  Group,
  NumberInput,
  Paper,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core'
import { DateInput } from '@mantine/dates'
import { useForm } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import { IconArrowLeft } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'

interface CreateProjectForm {
  project_name: string
  project_type: string
  company_id: string
  address: string
  latitude: number
  longitude: number
  elevation: number
  interconnection_limit: number
  capacity_dc: number
  capacity_ac: number
  battery_capacity_dc: number
  battery_capacity_ac: number
  /** @mantine/dates 8+ uses YYYY-MM-DD strings from DateInput onChange */
  commercial_operations_date: Date | string
  ppa_rate: number
}

function dateValueToIsoDateOnly(value: Date | string): string {
  const parsed = dayjs(value)
  if (!parsed.isValid()) {
    throw new TypeError('Invalid commercial operations date')
  }
  return parsed.format('YYYY-MM-DD')
}

function CreateProject() {
  const navigate = useNavigate()
  const [isGeocoding, setIsGeocoding] = useState(false)
  const { data: companies = [], isLoading: isLoadingCompanies } =
    useGetCompanies()
  const { data: projectTypes = [], isLoading: isLoadingProjectTypes } =
    useGetProjectTypes()
  const createProjectMutation = useCreateProject()

  const form = useForm<CreateProjectForm>({
    initialValues: {
      project_name: '',
      project_type: '',
      company_id: '',
      address: '',
      latitude: 0,
      longitude: 0,
      elevation: 0, // overwritten in api call
      interconnection_limit: 0,
      capacity_dc: 0,
      capacity_ac: 0,
      battery_capacity_dc: 0,
      battery_capacity_ac: 0,
      commercial_operations_date: new Date(),
      ppa_rate: 30,
    },
    validate: {
      project_name: (value) => {
        if (value.length < 1) return 'Project name is required'
        if (!/^[a-zA-Z0-9\s]+$/.test(value))
          return 'Project name must contain only alphanumeric characters and spaces'
        return null
      },
      project_type: (value) => (!value ? 'Project type is required' : null),
      address: (value) => (value.length < 1 ? 'Address is required' : null),
      latitude: (value) => {
        if (value < -90 || value > 90)
          return 'Latitude must be between -90 and 90'
        return null
      },
      longitude: (value) => {
        if (value < -180 || value > 180)
          return 'Longitude must be between -180 and 180'
        return null
      },
      interconnection_limit: (value) =>
        value <= 0 ? 'Interconnection limit must be greater than 0' : null,
      capacity_dc: (value) => {
        const projectType = form.values.project_type
        if (projectType === 'pv' || projectType === 'pv+s') {
          return value <= 0 ? 'PV DC capacity must be greater than 0' : null
        }
        return null
      },
      capacity_ac: (value) => {
        const projectType = form.values.project_type
        if (projectType === 'pv' || projectType === 'pv+s') {
          return value <= 0 ? 'PV AC capacity must be greater than 0' : null
        }
        return null
      },
      battery_capacity_dc: (value) => {
        const projectType = form.values.project_type
        if (projectType === 'bess' || projectType === 'pv+s') {
          return value <= 0
            ? 'Battery DC capacity must be greater than 0'
            : null
        }
        return null
      },
      battery_capacity_ac: (value) => {
        const projectType = form.values.project_type
        if (projectType === 'bess' || projectType === 'pv+s') {
          return value <= 0
            ? 'Battery AC capacity must be greater than 0'
            : null
        }
        return null
      },
      commercial_operations_date: (value) =>
        !value ? 'Commercial operations date is required' : null,
      ppa_rate: (value) =>
        value <= 0 ? 'PPA rate must be greater than 0' : null,
    },
  })

  const handleCreateProjectSubmit = (values: CreateProjectForm) => {
    // Map form values to API structure
    const projectData: ProjectCreate = {
      project_type_id: getProjectTypeId(values.project_type),
      name_long: values.project_name,
      address: values.address,
      elevation: values.elevation,
      time_zone: 'America/New_York', // Default timezone - could be made configurable
      poi: values.interconnection_limit,
      capacity_dc: values.capacity_dc || null,
      capacity_ac: values.capacity_ac || null,
      capacity_bess_power_ac: values.battery_capacity_ac || null,
      capacity_bess_energy_bol_dc: values.battery_capacity_dc || null,
      ppa: values.ppa_rate ? { rate: values.ppa_rate } : null,
      cod: dateValueToIsoDateOnly(values.commercial_operations_date),
      latitude: values.latitude,
      longitude: values.longitude,
    }

    createProjectMutation.mutate(projectData, {
      onSuccess: () => {
        notifications.show({
          title: 'Success',
          message: 'Project created successfully!',
          color: 'green',
        })
        navigate('/portfolio')
      },
      onError: (error) => {
        notifications.show({
          title: 'Error',
          message: 'Failed to create project. Please try again.',
          color: 'red',
        })
        console.error('Error creating project:', error)
      },
    })
  }

  // Helper function to map project type string to ID
  const getProjectTypeId = (projectTypeString: string): number => {
    const typeMap: Record<string, string> = {
      pv: 'pv',
      bess: 'bess',
      'pv+s': 'pvs', // Note: backend uses 'pvs' for PV+Storage
    }
    const mappedType = typeMap[projectTypeString] || projectTypeString
    const projectType = projectTypes.find(
      (type) => type.name_short === mappedType,
    )
    return projectType?.project_type_id || 1 // Default to 1 if not found
  }

  const geocodeAddress = useCallback(
    async (address: string) => {
      if (!address.trim()) return

      setIsGeocoding(true)
      try {
        const response = await fetch(
          `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(
            address,
          )}.json?access_token=${import.meta.env.VITE_MAPBOX_TOKEN}&limit=1`,
        )
        const data = await response.json()

        if (data.features && data.features.length > 0) {
          const [longitude, latitude] = data.features[0].center
          form.setFieldValue('latitude', latitude)
          form.setFieldValue('longitude', longitude)
        }
      } catch (error) {
        console.error('Geocoding error:', error)
      } finally {
        setIsGeocoding(false)
      }
    },
    [form],
  )

  const handleAddressChange = useCallback(
    (value: string) => {
      form.setFieldValue('address', value)
      if (value.trim()) {
        // Debounce geocoding
        const timeoutId = setTimeout(() => {
          geocodeAddress(value)
        }, 1000)
        return () => clearTimeout(timeoutId)
      }
    },
    [form, geocodeAddress],
  )

  const projectTypeOptions = useMemo(() => {
    if (!projectTypes.length) {
      return [
        { value: 'pv', label: 'PV' },
        { value: 'bess', label: 'Battery' },
        { value: 'pv+s', label: 'PV & Battery' },
      ]
    }
    return projectTypes.map((type) => ({
      value: type.name_short === 'pvs' ? 'pv+s' : type.name_short,
      label: type.name_long,
    }))
  }, [projectTypes])

  const companyOptions = useMemo(
    () =>
      companies
        .map((company) => ({
          value: company.company_id,
          label: company.name_long || company.name_short,
        }))
        .sort((a, b) => a.label.localeCompare(b.label)),
    [companies],
  )

  return (
    <AppShell padding={0}>
      <AppShell.Main>
        <Container size="md" py="xl">
          <Stack gap="lg">
            {/* Header */}
            <Group gap="md" justify="space-between">
              <Group gap="md">
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  size="lg"
                  onClick={() => navigate('/portfolio')}
                >
                  <Tooltip label="Back to Portfolio Home">
                    <IconArrowLeft size={20} />
                  </Tooltip>
                </ActionIcon>
                <div>
                  <Title order={1}>Create New Project</Title>
                  <Text c="dimmed">
                    Create a new project within the Platform. Project will be
                    created with a status of &quot;Currently Onboarding&quot;
                  </Text>
                </div>
              </Group>
            </Group>

            {/* Form */}
            <Paper p="xl" withBorder>
              <form
                onSubmit={form.onSubmit(handleCreateProjectSubmit, () => {
                  notifications.show({
                    title: 'Validation Error',
                    message:
                      'Please fix the errors in the form before submitting.',
                    color: 'red',
                  })
                })}
              >
                <Stack gap="md">
                  <Title order={3}>Project Details</Title>

                  <TextInput
                    label="Project Name"
                    description="For example:  Solar Project 4"
                    placeholder="Enter project name"
                    required
                    {...form.getInputProps('project_name')}
                  />

                  <Select
                    label="Project Type"
                    description="Select which generation technologies are used at this project"
                    placeholder="Select project type"
                    data={projectTypeOptions}
                    disabled={isLoadingProjectTypes}
                    required
                    {...form.getInputProps('project_type')}
                  />

                  <Select
                    label="Project Owner (Company)"
                    description="Select the company that owns this project (optional)"
                    placeholder="Select project owner"
                    data={companyOptions}
                    searchable
                    clearable
                    disabled={isLoadingCompanies}
                    {...form.getInputProps('company_id')}
                  />

                  <Title order={4} mt="md">
                    Location Information
                  </Title>

                  <TextInput
                    label="Address"
                    description="Project address"
                    placeholder="Enter project address"
                    required
                    {...form.getInputProps('address')}
                    onChange={(event) =>
                      handleAddressChange(event.currentTarget.value)
                    }
                    rightSection={
                      isGeocoding ? <Text size="xs">Loading...</Text> : null
                    }
                  />

                  <Group grow>
                    <NumberInput
                      label="Latitude"
                      placeholder="Enter latitude"
                      min={-90}
                      max={90}
                      step={0.000001}
                      decimalScale={6}
                      required
                      {...form.getInputProps('latitude')}
                    />
                    <NumberInput
                      label="Longitude"
                      placeholder="Enter longitude"
                      min={-180}
                      max={180}
                      step={0.000001}
                      decimalScale={6}
                      required
                      {...form.getInputProps('longitude')}
                    />
                  </Group>

                  <Title order={4} mt="md">
                    Technical Specifications
                  </Title>

                  <NumberInput
                    label="Interconnection Limit (MW)"
                    description="Enter the maximum power that can be exported to the grid"
                    placeholder="Enter interconnection limit"
                    min={0}
                    step={0.1}
                    decimalScale={2}
                    required
                    {...form.getInputProps('interconnection_limit')}
                  />

                  {(form.values.project_type === 'pv' ||
                    form.values.project_type === 'pv+s') && (
                    <Group grow>
                      <NumberInput
                        label="PV Capacity DC (MW)"
                        description="Enter the nameplate DC capacity of the PV system"
                        placeholder="Enter PV DC capacity"
                        min={0}
                        step={0.1}
                        decimalScale={2}
                        required
                        {...form.getInputProps('capacity_dc')}
                      />
                      <NumberInput
                        label="PV Capacity AC (MW)"
                        description="Enter the nameplate AC capacity of the PV system"
                        placeholder="Enter PV AC capacity"
                        min={0}
                        step={0.1}
                        decimalScale={2}
                        required
                        {...form.getInputProps('capacity_ac')}
                      />
                    </Group>
                  )}

                  {(form.values.project_type === 'bess' ||
                    form.values.project_type === 'pv+s') && (
                    <Group grow>
                      <NumberInput
                        label="Battery Capacity DC (MWh)"
                        description="Enter the nameplate DC capacity of the battery system"
                        placeholder="Enter battery DC capacity"
                        min={0}
                        step={0.1}
                        decimalScale={2}
                        required
                        {...form.getInputProps('battery_capacity_dc')}
                      />
                      <NumberInput
                        label="Battery Capacity AC (MW)"
                        description="Enter the nameplate AC capacity of the battery system"
                        placeholder="Enter battery AC capacity"
                        min={0}
                        step={0.1}
                        decimalScale={2}
                        required
                        {...form.getInputProps('battery_capacity_ac')}
                      />
                    </Group>
                  )}

                  <DateInput
                    label="Commercial Operations Date"
                    description="Select the date when the project will start commercial operations. This can be changed at a later time."
                    placeholder="Select commercial operations date"
                    required
                    {...form.getInputProps('commercial_operations_date')}
                  />

                  <Title order={4} mt="md">
                    Financial Information
                  </Title>

                  <NumberInput
                    label="PPA Rate ($/MW)"
                    description="Flat Power Purchase Agreement rate in dollars per MW"
                    placeholder="Enter PPA rate"
                    min={0}
                    step={0.01}
                    decimalScale={2}
                    required
                    {...form.getInputProps('ppa_rate')}
                  />

                  <Group justify="flex-end" mt="xl">
                    <Button
                      variant="subtle"
                      onClick={() => navigate('/portfolio')}
                      disabled={createProjectMutation.isPending}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      loading={createProjectMutation.isPending}
                    >
                      Create Project
                    </Button>
                  </Group>
                </Stack>
              </form>
            </Paper>
          </Stack>
        </Container>
      </AppShell.Main>
    </AppShell>
  )
}

export default CreateProject
