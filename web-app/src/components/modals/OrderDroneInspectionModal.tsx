import { useGetCompanies, useGetUserSelf } from '@/api/admin'
import {
  DroneInspectionOrderRequest,
  DroneProvider,
  useOrderDroneInspection,
} from '@/api/v1/operational/drone_integrations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useUser } from '@clerk/clerk-react'
import {
  Alert,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { DatePickerInput } from '@mantine/dates'
import { useForm } from '@mantine/form'
import { IconMail } from '@tabler/icons-react'
import React, { useMemo, useState } from 'react'

interface OrderDroneInspectionModalProps {
  opened: boolean
  onClose: () => void
  projectId: string
  currentProvider?: DroneProvider | null
}

interface FormValues {
  timing: string
  timingType: 'specific_date' | 'week' | 'month' | 'quarter'
  specificDate?: string
  week?: string
  month?: string
  quarter?: string
}

// Provider email mapping
const PROVIDER_EMAILS: Record<number, string> = {
  0: 'sales@zeitview.com', // Zeitview
  // Add more providers as needed
}

const TIMING_OPTIONS = [
  { value: 'specific_date', label: 'Specific Date' },
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Month' },
  { value: 'quarter', label: 'Quarter' },
]

const WEEK_OPTIONS = [
  { value: 'next_week', label: 'Next Week' },
  { value: 'week_of_jan_1', label: 'Week of Jan 1' },
  { value: 'week_of_jan_8', label: 'Week of Jan 8' },
  { value: 'week_of_jan_15', label: 'Week of Jan 15' },
  { value: 'week_of_jan_22', label: 'Week of Jan 22' },
  { value: 'week_of_jan_29', label: 'Week of Jan 29' },
  // Add more weeks as needed
]

const MONTH_OPTIONS = [
  { value: 'january', label: 'January' },
  { value: 'february', label: 'February' },
  { value: 'march', label: 'March' },
  { value: 'april', label: 'April' },
  { value: 'may', label: 'May' },
  { value: 'june', label: 'June' },
  { value: 'july', label: 'July' },
  { value: 'august', label: 'August' },
  { value: 'september', label: 'September' },
  { value: 'october', label: 'October' },
  { value: 'november', label: 'November' },
  { value: 'december', label: 'December' },
]

const QUARTER_OPTIONS = [
  { value: 'q1', label: 'Q1 (Jan-Mar)' },
  { value: 'q2', label: 'Q2 (Apr-Jun)' },
  { value: 'q3', label: 'Q3 (Jul-Sep)' },
  { value: 'q4', label: 'Q4 (Oct-Dec)' },
]

export const OrderDroneInspectionModal: React.FC<
  OrderDroneInspectionModalProps
> = ({ opened, onClose, projectId, currentProvider }) => {
  const { data: self } = useGetUserSelf({})
  const { user: clerkUser } = useUser()
  const { data: project } = useSelectProject(projectId!)
  const { data: companies } = useGetCompanies({
    queryParams: { company_ids: self?.company_id ? [self.company_id] : [] },
    queryOptions: { enabled: !!self?.company_id },
  })
  const orderDroneInspection = useOrderDroneInspection()
  const [error, setError] = useState<string | null>(null)

  // Clear error when modal opens
  React.useEffect(() => {
    if (opened) {
      setError(null)
    }
  }, [opened])

  const form = useForm<FormValues>({
    initialValues: {
      timing: '',
      timingType: 'specific_date',
      specificDate: '',
      week: '',
      month: '',
      quarter: '',
    },
    validate: {
      timingType: (value) => (value ? null : 'Timing type is required'),
      specificDate: (value, values) => {
        if (values.timingType === 'specific_date' && !value) {
          return 'Specific date is required'
        }
        return null
      },
      week: (value, values) => {
        if (values.timingType === 'week' && !value) {
          return 'Week selection is required'
        }
        return null
      },
      month: (value, values) => {
        if (values.timingType === 'month' && !value) {
          return 'Month selection is required'
        }
        return null
      },
      quarter: (value, values) => {
        if (values.timingType === 'quarter' && !value) {
          return 'Quarter selection is required'
        }
        return null
      },
    },
  })

  const providerEmail = useMemo(() => {
    if (!currentProvider) return null
    return PROVIDER_EMAILS[currentProvider.drone_provider_id] || null
  }, [currentProvider])

  const companyName = useMemo(() => {
    return companies?.[0]?.name_long || 'N/A'
  }, [companies])

  const handleSubmit = form.onSubmit(async (values) => {
    if (
      !clerkUser?.emailAddresses?.[0]?.emailAddress ||
      !project?.name_long ||
      !providerEmail
    ) {
      return
    }

    // Format timing based on type
    let timingText = ''
    switch (values.timingType) {
      case 'specific_date':
        timingText = values.specificDate || ''
        break
      case 'week':
        timingText =
          WEEK_OPTIONS.find((w) => w.value === values.week)?.label || ''
        break
      case 'month':
        timingText =
          MONTH_OPTIONS.find((m) => m.value === values.month)?.label || ''
        break
      case 'quarter':
        timingText =
          QUARTER_OPTIONS.find((q) => q.value === values.quarter)?.label || ''
        break
    }

    try {
      setError(null) // Clear any previous errors

      const request: DroneInspectionOrderRequest = {
        project_id: projectId,
        provider_email: providerEmail,
        timing: timingText,
      }

      await orderDroneInspection.mutateAsync(request)
      // Close modal on success
      onClose()
    } catch (error) {
      console.error('Failed to send drone inspection order:', error)
      setError('Failed to send email. Please try again.')
    }
  })

  const handleTimingTypeChange = (value: string | null) => {
    if (value) {
      form.setFieldValue('timingType', value as FormValues['timingType'])
      // Clear other timing fields
      form.setFieldValue('specificDate', '')
      form.setFieldValue('week', '')
      form.setFieldValue('month', '')
      form.setFieldValue('quarter', '')
    }
  }

  if (!self || !project) {
    return null
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group>
          <IconMail size={20} />
          <Title order={3}>Request New Drone Inspection</Title>
        </Group>
      }
      size="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            This will send an email request to{' '}
            {currentProvider?.name_long || 'the drone provider'} and copy you
            and orders@proximal.energy.
          </Text>

          {error && (
            <Alert color="red" title="Error">
              {error}
            </Alert>
          )}

          <TextInput
            label="Customer"
            value={companyName}
            readOnly
            styles={{ input: { cursor: 'not-allowed' } }}
          />

          <TextInput
            label="Site"
            value={project.name_long}
            readOnly
            styles={{ input: { cursor: 'not-allowed' } }}
          />

          <TextInput
            label="Scope"
            value="Full site inspection"
            readOnly
            styles={{ input: { cursor: 'not-allowed' } }}
          />

          <TextInput
            label="Inspection Type"
            value="Module Advanced"
            readOnly
            styles={{ input: { cursor: 'not-allowed' } }}
          />

          <Select
            label="Timing Type"
            placeholder="Select timing type"
            data={TIMING_OPTIONS}
            value={form.values.timingType}
            onChange={handleTimingTypeChange}
            required
          />

          {form.values.timingType === 'specific_date' && (
            <DatePickerInput
              label="Specific Date"
              placeholder="Select date"
              value={
                form.values.specificDate
                  ? new Date(form.values.specificDate)
                  : null
              }
              onChange={(date) =>
                form.setFieldValue(
                  'specificDate',
                  date ? date.toISOString().split('T')[0] : '',
                )
              }
              required
            />
          )}

          {form.values.timingType === 'week' && (
            <Select
              label="Week"
              placeholder="Select week"
              data={WEEK_OPTIONS}
              value={form.values.week}
              onChange={(value) => form.setFieldValue('week', value || '')}
              required
            />
          )}

          {form.values.timingType === 'month' && (
            <Select
              label="Month"
              placeholder="Select month"
              data={MONTH_OPTIONS}
              value={form.values.month}
              onChange={(value) => form.setFieldValue('month', value || '')}
              required
            />
          )}

          {form.values.timingType === 'quarter' && (
            <Select
              label="Quarter"
              placeholder="Select quarter"
              data={QUARTER_OPTIONS}
              value={form.values.quarter}
              onChange={(value) => form.setFieldValue('quarter', value || '')}
              required
            />
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              leftSection={<IconMail size={16} />}
              loading={orderDroneInspection.isPending}
            >
              Send Request
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  )
}
