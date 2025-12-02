import { useGetUserType } from '@/api/admin'
import { ProjectTypeEnum } from '@/api/enumerations'
import { useGetProjectTypes } from '@/api/v1/operational/project_types'
import {
  ProjectUpdate,
  useSelectProject,
  useUpdateProject,
} from '@/api/v1/operational/projects'
import {
  Alert,
  Button,
  Divider,
  Grid,
  Group,
  Loader,
  NumberInput,
  Select,
  Stack,
  TextInput,
  Title,
  useComputedColorScheme,
} from '@mantine/core'
import { DateInput } from '@mantine/dates'
import { useForm } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import { IconCheck, IconInfoCircle, IconX } from '@tabler/icons-react'
import { useEffect } from 'react'

interface ProjectInfoProps {
  projectId: string
}

// Common US timezones used in the system
const TIMEZONE_OPTIONS = [
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Chicago', label: 'Central Time (CT)' },
  { value: 'America/Denver', label: 'Mountain Time (MT)' },
  { value: 'America/Phoenix', label: 'Mountain Time - Arizona (MST)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
  { value: 'America/Detroit', label: 'Eastern Time - Detroit (ET)' },
  { value: 'America/Anchorage', label: 'Alaska Time (AKT)' },
  { value: 'Pacific/Honolulu', label: 'Hawaii Time (HST)' },
  { value: 'UTC', label: 'Coordinated Universal Time (UTC)' },
]

// US ISOs (Independent System Operators)
const US_ISO_OPTIONS = [
  { value: 'CAISO', label: 'CAISO (California Independent System Operator)' },
  { value: 'ERCOT', label: 'ERCOT (Electric Reliability Council of Texas)' },
  { value: 'ISO-NE', label: 'ISO-NE (ISO New England)' },
  { value: 'MISO', label: 'MISO (Midcontinent Independent System Operator)' },
  { value: 'NYISO', label: 'NYISO (New York Independent System Operator)' },
  { value: 'PJM', label: 'PJM (PJM Interconnection)' },
  { value: 'SPP', label: 'SPP (Southwest Power Pool)' },
  { value: 'HECO', label: 'HECO (Hawaii Electric Company)' },
  { value: 'Other', label: 'Other' },
]

export default function ProjectInfo({ projectId }: ProjectInfoProps) {
  const { data: project, isLoading } = useSelectProject(projectId!)

  const updateProject = useUpdateProject()
  const { data: userType } = useGetUserType({})

  const { data: projectTypes } = useGetProjectTypes({})
  const computedColorScheme = useComputedColorScheme()

  // Check if user is admin or superadmin
  const isUserAdmin =
    userType?.name_short === 'admin' || userType?.name_short === 'superadmin'

  // Check if user is superadmin
  const isUserSuperadmin = userType?.name_short === 'superadmin'

  // Helper function to get read-only input styles for proper dark mode support
  const getReadOnlyStyles = () => ({
    input: {
      color:
        computedColorScheme === 'dark'
          ? 'var(--mantine-color-gray-0)'
          : 'var(--mantine-color-gray-9)',
      cursor: 'not-allowed',
    },
  })

  // Create a map of project type IDs to project type names
  const projectTypeMap =
    projectTypes?.reduce(
      (acc, type) => {
        acc[type.project_type_id] = type.name_long
        return acc
      },
      {} as Record<number, string>,
    ) || {}

  const form = useForm<ProjectUpdate>({
    initialValues: {
      address: '',
      elevation: undefined,
      time_zone: '',
      ppa: undefined,
      poi: undefined,
      capacity_dc: undefined,
      capacity_ac: undefined,
      capacity_bess_power_ac: undefined,
      capacity_bess_energy_bol_dc: undefined,
      interconnecting_utility: '',
      interconnecting_substation: '',
      interconnecting_voltage: undefined,
      interconnecting_iso: '',
      interconnecting_node_code: '',
      cod: undefined,
      commencement_of_construction_date: undefined,
      financial_close_date: undefined,
      notice_to_proceed_date: undefined,
      mechanical_completion_date: undefined,
      substantial_completion_date: undefined,
      interconnection_approval_date: undefined,
      performance_test_completion_date: undefined,
      placed_in_service_date: undefined,
      first_realtime_data_received_date: undefined,
      first_data_backfilled_date: undefined,
    },
  })

  // Helper to parse YYYY-MM-DD into a local Date to avoid TZ shifts
  const parseLocalDate = (s?: string | null) =>
    s ? new Date(`${s}T00:00:00`) : undefined

  // Update form values when project data loads
  useEffect(() => {
    if (project) {
      form.setValues({
        address: project.address || '',
        elevation: project.elevation || undefined,
        time_zone: project.time_zone || '',
        ppa: project.ppa
          ? { rate: project.ppa.rate, type: project.ppa.type || 'flat_rate' }
          : undefined,
        poi: project.poi || undefined,
        capacity_dc: project.capacity_dc || undefined,
        capacity_ac: project.capacity_ac || undefined,
        capacity_bess_power_ac: project.capacity_bess_power_ac || undefined,
        capacity_bess_energy_bol_dc:
          project.capacity_bess_energy_bol_dc || undefined,
        interconnecting_utility: project.interconnecting_utility || '',
        interconnecting_substation: project.interconnecting_substation || '',
        interconnecting_voltage: project.interconnecting_voltage || undefined,
        interconnecting_iso: project.interconnecting_iso || '',
        interconnecting_node_code: project.interconnecting_node_code || '',
        cod: parseLocalDate(project.cod),
        commencement_of_construction_date: parseLocalDate(
          project.commencement_of_construction_date,
        ),
        financial_close_date: parseLocalDate(project.financial_close_date),
        notice_to_proceed_date: parseLocalDate(project.notice_to_proceed_date),
        mechanical_completion_date: parseLocalDate(
          project.mechanical_completion_date,
        ),
        substantial_completion_date: parseLocalDate(
          project.substantial_completion_date,
        ),
        interconnection_approval_date: parseLocalDate(
          project.interconnection_approval_date,
        ),
        performance_test_completion_date: parseLocalDate(
          project.performance_test_completion_date,
        ),
        placed_in_service_date: parseLocalDate(project.placed_in_service_date),
        first_realtime_data_received_date: parseLocalDate(
          project.first_realtime_data_received_date,
        ),
        first_data_backfilled_date: parseLocalDate(
          project.first_data_backfilled_date,
        ),
      })
    }
  }, [project]) // eslint-disable-line react-hooks/exhaustive-deps
  // NOTE: At the time of writing, `form` was included in the dependency array which caused infinite re-renders. This page probably needs to be refactored to use a more stable solution. See https://v7.mantine.dev/form/recipes/#set-initial-values-with-async-request for an example on how to set the form with initial values from an async request.

  const handleSubmit = (values: ProjectUpdate) => {
    // Only allow admins to submit changes
    if (!isUserAdmin) {
      notifications.show({
        title: 'Access Denied',
        message: 'Only administrators can update project information',
        color: 'red',
        icon: <IconX size={16} />,
      })
      return
    }

    // Filter out empty strings and convert Date objects to strings for API
    const updateData = Object.fromEntries(
      Object.entries(values)
        .filter(
          ([, value]) => value !== '' && value !== null && value !== undefined,
        )
        .map(([key, value]) => {
          if (value instanceof Date) {
            return [key, value.toISOString().split('T')[0]]
          }

          return [key, value]
        }),
    ) as Partial<ProjectUpdate>

    updateProject.mutate(
      { projectId, projectData: updateData },
      {
        onSuccess: () => {
          notifications.show({
            title: 'Success',
            message: 'Project information updated successfully',
            color: 'green',
            icon: <IconCheck size={16} />,
          })
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: 'Failed to update project information',
            color: 'red',
            icon: <IconX size={16} />,
          })
          console.error('Update error:', error)
        },
      },
    )
  }

  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '200px',
        }}
      >
        <Loader size="lg" />
      </div>
    )
  }

  if (!project) {
    return <div>Project not found</div>
  }

  return (
    <Stack gap="md" mt="md">
      {!isUserAdmin && (
        <Alert
          icon={<IconInfoCircle size={16} />}
          title="Read-Only Access"
          color="blue"
        >
          You don&apos;t have permission to edit project information. Please
          contact an administrator to make changes to this project.
        </Alert>
      )}
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="lg">
          <Title order={3} mb="md">
            Project Information
          </Title>

          <Grid>
            <Grid.Col span={6}>
              <Title order={4} mb="md">
                General
              </Title>
              <Stack gap="md">
                <Grid>
                  <Grid.Col span={6}>
                    <TextInput
                      label="Project Name"
                      placeholder="Enter project name"
                      readOnly
                      value={project?.name_long || ''}
                      styles={getReadOnlyStyles()}
                    />
                  </Grid.Col>
                  <Grid.Col span={6}>
                    <TextInput
                      label="Project Type"
                      placeholder="Project type"
                      readOnly
                      value={
                        project?.project_type?.name_long ||
                        projectTypeMap[project?.project_type_id || 0] ||
                        'Unknown'
                      }
                      styles={getReadOnlyStyles()}
                    />
                  </Grid.Col>
                </Grid>
                <TextInput
                  label="Address"
                  placeholder="Enter project address"
                  readOnly={!isUserSuperadmin}
                  {...form.getInputProps('address')}
                  styles={!isUserSuperadmin ? getReadOnlyStyles() : undefined}
                />
                <NumberInput
                  label="Elevation (m)"
                  placeholder="Enter elevation"
                  decimalScale={1}
                  readOnly={!isUserSuperadmin}
                  {...form.getInputProps('elevation')}
                  styles={!isUserSuperadmin ? getReadOnlyStyles() : undefined}
                />
                <Select
                  label="Time Zone"
                  placeholder="Select time zone"
                  data={TIMEZONE_OPTIONS}
                  readOnly={!isUserSuperadmin}
                  {...form.getInputProps('time_zone')}
                  styles={!isUserSuperadmin ? getReadOnlyStyles() : undefined}
                />
                {(project.project_type_id === ProjectTypeEnum.PV ||
                  project.project_type_id === ProjectTypeEnum.PVS) && (
                  <NumberInput
                    label="PV PPA Price ($/MWh)"
                    placeholder="Enter PV PPA price"
                    decimalScale={2}
                    readOnly={!isUserAdmin}
                    value={form.values.ppa?.rate ?? undefined}
                    onChange={(val) => {
                      if (!isUserAdmin) return
                      form.setFieldValue('ppa', {
                        rate: Number(val) || 0,
                        type: 'flat_rate',
                      })
                    }}
                    styles={!isUserAdmin ? getReadOnlyStyles() : undefined}
                  />
                )}
              </Stack>
            </Grid.Col>

            <Grid.Col span={6}>
              <Title order={4} mb="md">
                Capacity
              </Title>
              <Stack gap="md">
                <NumberInput
                  label="POI Capacity (MW)"
                  placeholder="Enter POI capacity"
                  decimalScale={2}
                  readOnly={!isUserSuperadmin}
                  {...form.getInputProps('poi')}
                  styles={!isUserSuperadmin ? getReadOnlyStyles() : undefined}
                />
                {(project.project_type_id === ProjectTypeEnum.PV ||
                  project.project_type_id === ProjectTypeEnum.PVS) && (
                  <NumberInput
                    label="PV DC Capacity (MW)"
                    placeholder="Enter DC capacity"
                    decimalScale={2}
                    readOnly={!isUserSuperadmin}
                    {...form.getInputProps('capacity_dc')}
                    styles={!isUserSuperadmin ? getReadOnlyStyles() : undefined}
                  />
                )}
                {(project.project_type_id === ProjectTypeEnum.PV ||
                  project.project_type_id === ProjectTypeEnum.PVS) && (
                  <NumberInput
                    label="PV AC Capacity (MW)"
                    placeholder="Enter AC capacity"
                    decimalScale={2}
                    readOnly={!isUserSuperadmin}
                    {...form.getInputProps('capacity_ac')}
                    styles={!isUserSuperadmin ? getReadOnlyStyles() : undefined}
                  />
                )}
                {(project.project_type_id === ProjectTypeEnum.BESS ||
                  project.project_type_id === ProjectTypeEnum.PVS) && (
                  <NumberInput
                    label="BESS Power AC (MW)"
                    placeholder="Enter BESS power capacity"
                    decimalScale={2}
                    readOnly={!isUserSuperadmin}
                    {...form.getInputProps('capacity_bess_power_ac')}
                    styles={!isUserSuperadmin ? getReadOnlyStyles() : undefined}
                  />
                )}
                {(project.project_type_id === ProjectTypeEnum.BESS ||
                  project.project_type_id === ProjectTypeEnum.PVS) && (
                  <NumberInput
                    label="BESS Energy BOL DC (MWh)"
                    placeholder="Enter BESS energy capacity"
                    decimalScale={2}
                    readOnly={!isUserSuperadmin}
                    {...form.getInputProps('capacity_bess_energy_bol_dc')}
                    styles={!isUserSuperadmin ? getReadOnlyStyles() : undefined}
                  />
                )}
              </Stack>
            </Grid.Col>
          </Grid>

          <Divider my="lg" />

          <Title order={4} mb="md">
            Interconnection Details
          </Title>
          <Grid>
            <Grid.Col span={6}>
              <Select
                label="Interconnecting ISO"
                placeholder="Select interconnecting ISO"
                data={US_ISO_OPTIONS}
                readOnly={!isUserAdmin}
                {...form.getInputProps('interconnecting_iso')}
                styles={!isUserAdmin ? getReadOnlyStyles() : undefined}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="Interconnecting Utility"
                placeholder="Enter interconnecting utility"
                readOnly={!isUserAdmin}
                {...form.getInputProps('interconnecting_utility')}
                styles={!isUserAdmin ? getReadOnlyStyles() : undefined}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="Interconnecting Substation"
                placeholder="Enter interconnecting substation"
                readOnly={!isUserAdmin}
                {...form.getInputProps('interconnecting_substation')}
                styles={!isUserAdmin ? getReadOnlyStyles() : undefined}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <NumberInput
                label="Interconnecting Voltage (kV)"
                placeholder="Enter interconnecting voltage"
                decimalScale={1}
                readOnly={!isUserAdmin}
                {...form.getInputProps('interconnecting_voltage')}
                styles={!isUserAdmin ? getReadOnlyStyles() : undefined}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="Interconnecting Node Code"
                placeholder="Enter interconnecting node code"
                readOnly={!isUserAdmin}
                {...form.getInputProps('interconnecting_node_code')}
                styles={!isUserAdmin ? getReadOnlyStyles() : undefined}
              />
            </Grid.Col>
          </Grid>

          <Divider my="lg" />

          <Title order={4} mb="md">
            Project Milestones
          </Title>
          <Grid>
            <Grid.Col span={6}>
              <DateInput
                label="Commencement of Construction"
                placeholder="Select date"
                valueFormat="YYYY-MM-DD"
                readOnly={!isUserAdmin}
                {...form.getInputProps('commencement_of_construction_date')}
                styles={!isUserAdmin ? getReadOnlyStyles() : undefined}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <DateInput
                label="Financial Close"
                placeholder="Select date"
                valueFormat="YYYY-MM-DD"
                readOnly={!isUserAdmin}
                {...form.getInputProps('financial_close_date')}
                styles={!isUserAdmin ? getReadOnlyStyles() : undefined}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <DateInput
                label="Notice to Proceed"
                placeholder="Select date"
                valueFormat="YYYY-MM-DD"
                readOnly={!isUserAdmin}
                {...form.getInputProps('notice_to_proceed_date')}
                styles={
                  !isUserAdmin
                    ? {
                        input: {
                          backgroundColor: 'var(--mantine-color-gray-1)',
                          cursor: 'not-allowed',
                        },
                      }
                    : undefined
                }
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <DateInput
                label="Mechanical Completion"
                placeholder="Select date"
                valueFormat="YYYY-MM-DD"
                readOnly={!isUserAdmin}
                {...form.getInputProps('mechanical_completion_date')}
                styles={
                  !isUserAdmin
                    ? {
                        input: {
                          backgroundColor: 'var(--mantine-color-gray-1)',
                          cursor: 'not-allowed',
                        },
                      }
                    : undefined
                }
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <DateInput
                label="Substantial Completion"
                placeholder="Select date"
                valueFormat="YYYY-MM-DD"
                readOnly={!isUserAdmin}
                {...form.getInputProps('substantial_completion_date')}
                styles={
                  !isUserAdmin
                    ? {
                        input: {
                          backgroundColor: 'var(--mantine-color-gray-1)',
                          cursor: 'not-allowed',
                        },
                      }
                    : undefined
                }
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <DateInput
                label="Interconnection Approval"
                placeholder="Select date"
                valueFormat="YYYY-MM-DD"
                readOnly={!isUserAdmin}
                {...form.getInputProps('interconnection_approval_date')}
                styles={
                  !isUserAdmin
                    ? {
                        input: {
                          backgroundColor: 'var(--mantine-color-gray-1)',
                          cursor: 'not-allowed',
                        },
                      }
                    : undefined
                }
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <DateInput
                label="Performance Test Completion"
                placeholder="Select date"
                valueFormat="YYYY-MM-DD"
                readOnly={!isUserAdmin}
                {...form.getInputProps('performance_test_completion_date')}
                styles={
                  !isUserAdmin
                    ? {
                        input: {
                          backgroundColor: 'var(--mantine-color-gray-1)',
                          cursor: 'not-allowed',
                        },
                      }
                    : undefined
                }
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <DateInput
                label="Commercial Operation Date"
                placeholder="Select date"
                valueFormat="YYYY-MM-DD"
                readOnly={!isUserAdmin}
                {...form.getInputProps('cod')}
                styles={
                  !isUserAdmin
                    ? {
                        input: {
                          backgroundColor: 'var(--mantine-color-gray-1)',
                          cursor: 'not-allowed',
                        },
                      }
                    : undefined
                }
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <DateInput
                label="Placed in Service"
                placeholder="Select date"
                valueFormat="YYYY-MM-DD"
                readOnly={!isUserAdmin}
                {...form.getInputProps('placed_in_service_date')}
                styles={
                  !isUserAdmin
                    ? {
                        input: {
                          backgroundColor: 'var(--mantine-color-gray-1)',
                          cursor: 'not-allowed',
                        },
                      }
                    : undefined
                }
              />
            </Grid.Col>
            {isUserSuperadmin && (
              <>
                <Grid.Col span={6}>
                  <DateInput
                    label="First Realtime Data"
                    placeholder="Select date"
                    valueFormat="YYYY-MM-DD"
                    readOnly={!isUserAdmin}
                    {...form.getInputProps('first_realtime_data_received_date')}
                    styles={
                      !isUserAdmin
                        ? {
                            input: {
                              backgroundColor: 'var(--mantine-color-gray-1)',
                              cursor: 'not-allowed',
                            },
                          }
                        : undefined
                    }
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <DateInput
                    label="First Data Backfilled"
                    placeholder="Select date"
                    valueFormat="YYYY-MM-DD"
                    readOnly={!isUserAdmin}
                    {...form.getInputProps('first_data_backfilled_date')}
                    styles={
                      !isUserAdmin
                        ? {
                            input: {
                              backgroundColor: 'var(--mantine-color-gray-1)',
                              cursor: 'not-allowed',
                            },
                          }
                        : undefined
                    }
                  />
                </Grid.Col>
              </>
            )}
          </Grid>

          {isUserAdmin && (
            <Group justify="flex-start" mt="lg" mb="xl">
              <Button type="submit" loading={updateProject.isPending}>
                Save Changes
              </Button>
            </Group>
          )}
        </Stack>
      </form>
    </Stack>
  )
}
