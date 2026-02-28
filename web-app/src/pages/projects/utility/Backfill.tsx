import { useSelectProject } from '@/api/v1/operational/projects'
// Import an icon for the success message

import { useSubmitBackfill } from '@/api/v1/protected/pv-expected-energy/backfill/backfill'
// Ensure this import path is correct and points to the React component
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import {
  Alert,
  Button,
  Container,
  Paper,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { IconCheck } from '@tabler/icons-react'
// Import Dayjs and necessary plugins
import dayjs, { Dayjs } from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useEffect } from 'react'
import { useParams } from 'react-router'

// --- Form options ---
const singleDiodeModelOptions = [
  { value: 'DESOTO', label: 'Desoto' },
  { value: 'PVWATTS', label: 'PVWatts' },
  { value: 'PVSYST', label: 'PVSYST' },
]
const soilingOptions = [
  { value: 'measured', label: 'Measured' },
  { value: 'none', label: 'None' },
]
const degradationOptions = [
  { value: 'none', label: 'None' },
  { value: 'warranted', label: 'Warranted' },
]
const wiringOptions = [
  { value: 'target_stc', label: 'Target STC' },
  { value: 'fixed', label: 'Fixed' },
]

// Extend dayjs with plugins
dayjs.extend(utc)
dayjs.extend(timezone)

// Define the type for the form values
interface BackfillFormValues {
  project_id: string
  project_name_short: string | undefined
  energy_model_version: string
  simulation_start: Dayjs | null // Use Dayjs type
  simulation_end: Dayjs | null // Use Dayjs type
  single_diode_model: string
  soiling: string
  degradation: string
  dc_wiring_to_combiner: string
  dc_wiring_to_inverter: string
  use_poa_only: boolean
  use_median_irr_sensor: boolean
}

const Page = () => {
  const { projectId } = useParams<{ projectId: string }>()

  const { data: project } = useSelectProject(projectId!)

  // --- Get date values from the hook used by AdvancedDatePicker ---
  // start and end should be Dayjs objects or null
  const { start, end } = useValidateDateRange({})

  const form = useForm<BackfillFormValues>({
    initialValues: {
      project_id: projectId || '',
      project_name_short: undefined, // Initialize later
      energy_model_version: 'live',
      simulation_start: null, // Initialize as null
      simulation_end: null, // Initialize as null
      single_diode_model: 'DESOTO',
      soiling: 'measured',
      degradation: 'none',
      dc_wiring_to_combiner: 'target_stc',
      dc_wiring_to_inverter: 'target_stc',
      use_poa_only: false,
      use_median_irr_sensor: false,
    },
    validate: {
      energy_model_version: (value) =>
        !value ? 'Energy model version is required' : null,
      // Validation now correctly checks the form's date state
      simulation_start: (value) =>
        !value ? 'Simulation start date is required' : null,
      simulation_end: (value, values) =>
        !value
          ? 'Simulation end date is required'
          : // Use Dayjs comparison. isBefore checks if the first date is strictly before the second.
            values.simulation_start && value.isBefore(values.simulation_start)
            ? 'End date must be on or after start date'
            : null,
    },
  })

  // --- Synchronize Date Picker State with Form State ---
  useEffect(() => {
    // When 'start' from the hook changes, update the form field
    if (form.values.simulation_start !== start) {
      form.setFieldValue('simulation_start', start)
    }
    // oxlint-disable-next-line react/exhaustive-deps
  }, [start?.valueOf()]) // Removed form.setFieldValue from deps, useEffect dependency logic handles this

  useEffect(() => {
    // When 'end' from the hook changes, update the form field
    if (form.values.simulation_end !== end) {
      form.setFieldValue('simulation_end', end)
    }
    // oxlint-disable-next-line react/exhaustive-deps
  }, [end?.valueOf()]) // Removed form.setFieldValue from deps

  // Update project name when project data arrives
  useEffect(() => {
    if (project?.name_short) {
      form.setFieldValue('project_name_short', project.name_short)
    }
    // oxlint-disable-next-line react/exhaustive-deps
  }, [project?.name_short]) // Removed form.setFieldValue from deps

  // --- Get mutation state including isLoading and isSuccess ---
  const {
    mutate: submitBackfill,
    isError,
    error,
    isSuccess, // Get success status
  } = useSubmitBackfill()

  // Define the submission handler
  const handleSubmit = (values: BackfillFormValues) => {
    if (!values.project_id) {
      console.error('ProjectId is missing!')
      return
    }
    if (!project?.time_zone) {
      console.error(
        'Project timezone is missing! Cannot format dates correctly.',
      )
      form.setErrors({
        simulation_start:
          'Project configuration incomplete (missing timezone).',
      })
      return
    }

    let formattedStartDate: string | undefined = undefined
    let formattedEndDate: string | undefined = undefined

    if (values.simulation_start) {
      formattedStartDate = values.simulation_start
        .tz(project.time_zone, true) // true = keepLocalTime
        .toISOString()
    } else {
      console.error('Form submitted with null start date despite validation.')
      form.setErrors({ simulation_start: 'Start date is required.' })
      return // Prevent submission
    }

    if (values.simulation_end) {
      formattedEndDate = values.simulation_end
        .tz(project.time_zone, true) // true = keepLocalTime
        .toISOString()
    } else {
      console.error('Form submitted with null end date despite validation.')
      form.setErrors({ simulation_end: 'End date is required.' })
      return // Prevent submission
    }

    // Construct the payload using form values
    const payload = {
      project_id: values.project_id,
      project_name_short: values.project_name_short,
      energy_model_version: values.energy_model_version,
      single_diode_model: values.single_diode_model,
      simulation_start: formattedStartDate,
      simulation_end: formattedEndDate,
      soiling: values.soiling,
      degradation: values.degradation,
      dc_wiring_to_combiner: values.dc_wiring_to_combiner,
      dc_wiring_to_inverter: values.dc_wiring_to_inverter,
      use_poa_only: values.use_poa_only,
      use_median_irr_sensor: values.use_median_irr_sensor,
    }

    // The mutation hook will handle setting isSuccess, isLoading, etc.
    submitBackfill(payload) // Pass only the expected payload structure
  }

  return (
    <Container size="xs" p="md" style={{ width: '100%' }}>
      <Paper
        withBorder
        p="md"
        radius="md"
        component="form"
        onSubmit={form.onSubmit(handleSubmit, (validationErrors) => {
          console.error('--- Validation Failed ---')
          console.error('Validation Errors:', validationErrors)
          if (
            validationErrors.simulation_start ||
            validationErrors.simulation_end
          ) {
            console.error('Date validation failed. Form values:', form.values)
          }
        })}
      >
        <Stack>
          <Title order={1}>Expected Power Backfill</Title>

          <AdvancedDatePicker
            includeClearButton={false}
            includeTodayInDateRange
            width="100%"
            defaultRange="past-week"
          />

          {/* Display validation errors for dates */}
          {form.errors.simulation_start && (
            <Text c="red" size="sm" mt="-xs" mb="xs">
              {form.errors.simulation_start}
            </Text>
          )}
          {form.errors.simulation_end && (
            <Text c="red" size="sm" mt="-xs" mb="xs">
              {form.errors.simulation_end}
            </Text>
          )}

          <TextInput
            required
            label="Energy Model Version"
            description="live or 0.9.3+"
            placeholder="Enter energy model version"
            {...form.getInputProps('energy_model_version')}
          />
          <Select
            label="Single Diode Model"
            data={singleDiodeModelOptions}
            {...form.getInputProps('single_diode_model')}
          />
          <Select
            label="Soiling"
            data={soilingOptions}
            {...form.getInputProps('soiling')}
          />
          <Select
            label="Degradation"
            data={degradationOptions}
            {...form.getInputProps('degradation')}
          />
          <Select
            label="DC Wiring to Combiner"
            description="Fixed: Serrano --- Target STC: All others"
            data={wiringOptions}
            {...form.getInputProps('dc_wiring_to_combiner')}
          />
          <Select
            label="DC Wiring to Inverter"
            description="Fixed: Serrano --- Target STC: All others"
            data={wiringOptions}
            {...form.getInputProps('dc_wiring_to_inverter')}
          />
          <Switch
            label="Use POA Only"
            description="Use POA only for calculations"
            checked={form.values.use_poa_only}
            onChange={(event) =>
              form.setFieldValue('use_poa_only', event.currentTarget.checked)
            }
          />
          <Switch
            label="Use Median Irradiance Sensor"
            description="Use median irradiance sensor for calculations"
            checked={form.values.use_median_irr_sensor}
            onChange={(event) =>
              form.setFieldValue(
                'use_median_irr_sensor',
                event.currentTarget.checked,
              )
            }
          />

          {/* Submit Button with Loading State */}
          <Button type="submit">Submit Backfill Job</Button>

          {/* --- Success Message --- */}
          {isSuccess && (
            <Alert
              icon={<IconCheck size="1rem" />}
              title="Success!"
              color="green"
              mt="md"
            >
              Backfill job has been submitted asynchronously. Async failures
              will be captured in logs.
            </Alert>
          )}

          {/* --- Error Message --- */}
          {isError && error && (
            <Alert title="Error" color="red" mt="md">
              Error submitting backfill:{' '}
              {error instanceof Error
                ? error.message
                : 'An unknown error occurred.'}
            </Alert>
          )}
        </Stack>
      </Paper>
    </Container>
  )
}

export default Page
