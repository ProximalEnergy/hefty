import { DeviceTypeEnum } from '@/api/enumerations'
import { useGetKPIInstances } from '@/api/v1/operational/kpi_instances'
import { PageLoader } from '@/components/Loading'
import { useAddKPIAlert } from '@/hooks/api'
import {
  KPIInstanceProps,
  StatisticType,
  statisticOptions,
} from '@/hooks/types'
import {
  Button,
  Checkbox,
  Container,
  Group,
  Modal,
  NumberInput,
  Paper,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { useDisclosure } from '@mantine/hooks'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import ProjectKPIExistingAlerts from './ProjectKPIExistingAlerts'

interface alertProps {
  project_id: string
  alert_name: string
  comparison: string | null
  duration_value: string | null
  kpi_type_id: string | null
  statistic: StatisticType | null
  notify: boolean
  threshold_value: number | null | string
  triggered: boolean | null
}

const comparisonOptions = [
  { value: 'gte', label: 'Greater than or equal to' },
  { value: 'gt', label: 'Greater than' },
  { value: 'eq', label: 'Exactly' },
  { value: 'lt', label: 'Less than' },
  { value: 'lte', label: 'Less than or equal to' },
]

const dateOptions = ['Yesterday', 'Last 7 days']

const ProjectKPIAlerts = () => {
  const navigate = useNavigate()

  const { projectId } = useParams<{ projectId: string }>()
  const { mutate } = useAddKPIAlert()

  const [statisticDisabled, setStatisticDisabled] = useState<boolean>(false)

  const [thresholdSuffix, setThresholdSuffix] = useState<string | null>('')

  const [submissionModalTitle, setSubmissionModalTitle] = useState('')
  const [
    submissionModalOpened,
    { open: openSubmissionModal, close: closeSubmissionModal },
  ] = useDisclosure(false)

  const { data: instanceData, isLoading: instanceLoading } = useGetKPIInstances(
    {
      queryParams: {
        project_ids: [projectId ?? '-1'],
        deep: true,
      },
      queryOptions: {
        enabled: !!projectId,
      },
    },
  )

  const data = (instanceData?.map((item) => item.kpi_type) ??
    []) as KPIInstanceProps[]

  const kpiOptions = data?.map((item) => ({
    value: item.kpi_type_id.toString(),
    label: item.name_long,
  }))

  const form = useForm<alertProps>({
    initialValues: {
      project_id: projectId ?? '',
      alert_name: '',
      kpi_type_id: '',
      statistic: null,
      comparison: null,
      threshold_value: '',
      duration_value: null,
      notify: false,
      triggered: false,
    },

    validate: {
      alert_name: (value) => (value ? null : 'Alert name is required'),
      kpi_type_id: (value) => (value ? null : 'KPI is required'),
      comparison: (value) => (value ? null : 'Comparison operator is required'),
      threshold_value: (value) => (value ? null : 'Numeric value is required'),
      duration_value: (value) => (value ? null : 'Over value is required'),
    },
  })

  const handleKpiChange = (value: string | null) => {
    form.setFieldValue('kpi_type_id', value ?? null)
    const selectedKpi = data?.find(
      (item) => item.kpi_type_id.toString() === value,
    )
    if (selectedKpi?.unit === '%') {
      setThresholdSuffix('%')
    } else if (selectedKpi?.unit === 'MWh') {
      setThresholdSuffix(' MWh')
    } else if (selectedKpi?.unit === 'deg') {
      setThresholdSuffix('°')
    } else {
      setThresholdSuffix(null)
    }

    // If the KPI is a project level KPI, disable the statistic dropdown
    if (selectedKpi?.device_type_id === DeviceTypeEnum.PROJECT) {
      setStatisticDisabled(true)
      form.setFieldValue('statistic', null)
    } else {
      setStatisticDisabled(false)
    }
  }

  const handleStatisticChange = (value: string | null) => {
    const statisticValue =
      value && statisticOptions.some((option) => option.value === value)
        ? (value as StatisticType)
        : null

    form.setFieldValue('statistic', statisticValue)
    handleKpiChange(form.getValues().kpi_type_id)
    if (statisticValue === 'count') {
      setThresholdSuffix(null)
    }
    if (statisticValue === 'available_data') {
      setThresholdSuffix('%')
    }
  }

  const handleSubmit = (values: alertProps) => {
    values.project_id = projectId ?? '-1'
    if (thresholdSuffix === '%') {
      values.threshold_value =
        typeof values.threshold_value === 'number'
          ? values.threshold_value / 100
          : null
    }
    mutate(values, {
      onSuccess: () => {
        setSubmissionModalTitle('Submission Successful')
        openSubmissionModal()
        form.reset()
      },
      onError: () => {
        setSubmissionModalTitle('Submission Error')
        openSubmissionModal()
      },
    })
  }

  if (instanceLoading) return <PageLoader />

  return (
    <Container fluid>
      <Modal
        opened={submissionModalOpened}
        onClose={() => closeSubmissionModal()}
        title={submissionModalTitle}
        centered
      >
        <Stack align="center">
          <Text>
            {submissionModalTitle === 'Submission Successful'
              ? 'Your alert was successfully created!'
              : 'There was an error creating your alert. Please try again.'}
          </Text>
          <Group>
            <Button onClick={() => closeSubmissionModal()}>Close</Button>
            <Button onClick={() => navigate(-1)}>Return</Button>
          </Group>
        </Stack>
      </Modal>

      <Group align="flex-start" pt="sm">
        <Paper withBorder p="sm" radius="md" w="65%">
          <form onSubmit={form.onSubmit(handleSubmit)}>
            <Stack>
              <Title order={2}>New KPI Alert</Title>
              <Text size="lg">Alert Name</Text>
              <TextInput
                placeholder="Enter alert name..."
                required
                {...form.getInputProps('alert_name')}
              />
              <Text size="lg">I would like to be alerted when:</Text>
              <Group gap="md" grow>
                <Select
                  label="KPI"
                  placeholder="Select KPI..."
                  data={kpiOptions}
                  required
                  {...form.getInputProps('kpi_type_id')}
                  onChange={handleKpiChange}
                />

                <Select
                  label="Statistic"
                  placeholder="Select statistic..."
                  data={statisticOptions}
                  disabled={statisticDisabled}
                  clearable
                  {...form.getInputProps('statistic')}
                  onChange={handleStatisticChange}
                />

                <Select
                  label="Is"
                  placeholder="Select Operation..."
                  data={comparisonOptions}
                  required
                  {...form.getInputProps('comparison')}
                />

                <NumberInput
                  label="Threshold"
                  required
                  suffix={thresholdSuffix ?? ''}
                  {...form.getInputProps('threshold_value')}
                />
                <Select
                  label="During"
                  placeholder="Select Days..."
                  data={dateOptions}
                  required
                  {...form.getInputProps('duration_value')}
                />
              </Group>
              <Checkbox
                label="Notify via email"
                {...form.getInputProps('notify')}
              />
              <Button type="submit">Submit</Button>
            </Stack>
          </form>
        </Paper>
        <Stack w="30%">
          <ProjectKPIExistingAlerts />
        </Stack>
      </Group>
    </Container>
  )
}

export default ProjectKPIAlerts
