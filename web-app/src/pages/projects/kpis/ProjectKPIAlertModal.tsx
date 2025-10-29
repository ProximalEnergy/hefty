import { useGetKPIInstances } from '@/api/v1/operational/kpi_instances'
import { useUpdateKPIAlert } from '@/hooks/api'
import {
  KPIAlertProps,
  KPIInstanceProps,
  statisticOptions,
} from '@/hooks/types'
import {
  Box,
  Button,
  Checkbox,
  Group,
  LoadingOverlay,
  Modal,
  NumberInput,
  Paper,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router'

interface ProjectKPIAlertModalProps {
  opened: boolean
  onClose: () => void
  alert: KPIAlertProps
  onSuccessfulUpdate: () => void // Add this line
}

const comparisonOptions = [
  { value: 'gte', label: 'Greater than or equal to' },
  { value: 'gt', label: 'Greater than' },
  { value: 'eq', label: 'Exactly' },
  { value: 'lt', label: 'Less than' },
  { value: 'lte', label: 'Less than or equal to' },
]

const dateOptions = ['Yesterday', 'Last 7 days']

const ProjectKPIAlertModal = ({
  opened,
  onClose,
  alert,
  onSuccessfulUpdate, // Add this line
}: ProjectKPIAlertModalProps) => {
  const [statisticDisabled, setStatisticDisabled] = useState<boolean>(false)
  const { projectId } = useParams<{ projectId: string }>()
  const { mutate } = useUpdateKPIAlert()
  const [thresholdSuffix, setThresholdSuffix] = useState<string | null>('')
  const [loadState, setLoadState] = useState<boolean>(false)
  const { data: instanceData } = useGetKPIInstances({
    queryParams: {
      project_ids: [projectId ?? '-1'],
      deep: true,
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  const data = (instanceData?.map((item) => item.kpi_type) ??
    []) as KPIInstanceProps[]

  const kpiOptions = data?.map((item) => ({
    value: item.kpi_type_id.toString(),
    label: item.name_long,
  }))
  const form = useForm({
    initialValues: {
      kpi_alert_id: alert.kpi_alert_id,
      alert_name: alert.config.alert_name,
      kpi_type_id: alert.config.kpi_type_id,
      statistic: alert.config.statistic,
      comparison: alert.config.comparison,
      threshold_value: alert.config.threshold_value,
      duration_value: alert.config.duration_value,
      notify: alert.config.notify,
    },
  })
  useEffect(() => {
    form.setFieldValue('kpi_alert_id', alert.kpi_alert_id)
    form.setFieldValue('alert_name', alert.config.alert_name)
    form.setFieldValue('kpi_type_id', alert.config.kpi_type_id)
    form.setFieldValue('statistic', alert.config.statistic)
    handleKpiChange(alert.config.kpi_type_id)
    form.setFieldValue('comparison', alert.config.comparison)

    // Multiply threshold_value by 100 if the KPI's unit is "%"
    const selectedKpi = data?.find(
      (item) => item.kpi_type_id.toString() === alert.config.kpi_type_id,
    )
    const thresholdValue =
      selectedKpi?.unit === '%'
        ? Number(alert.config.threshold_value) * 100
        : alert.config.threshold_value
    form.setFieldValue('threshold_value', thresholdValue)

    form.setFieldValue('duration_value', alert.config.duration_value)
    form.setFieldValue('notify', alert.config.notify)
  }, [opened, alert])

  // This is some duplicated code from ProjectKPIAlerts.tsx, but I'm not sure how to avoid it
  const handleKpiChange = (value: any) => {
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
    if (selectedKpi?.device_type_id === 1) {
      setStatisticDisabled(true)
      form.setFieldValue('statistic', null)
    } else {
      setStatisticDisabled(false)
    }
  }

  const handleSubmit = (values: any) => {
    values.project_id = projectId ?? '-1'
    if (thresholdSuffix === '%') {
      values.threshold_value =
        typeof values.threshold_value === 'number'
          ? values.threshold_value / 100
          : null
    }
    setLoadState(true)
    mutate(values, {
      onSuccess: () => {
        onSuccessfulUpdate() // Call this on successful update
      },
      onSettled: () => {
        setLoadState(false)
      },
    })
  }
  return (
    <Modal.Root opened={opened} onClose={onClose} size="xl">
      <Modal.Overlay />

      <Modal.Content>
        <Modal.Header>
          <Modal.Title>
            <Text size="xl" fw={700}>
              Edit KPI Alert
            </Text>
          </Modal.Title>
          <Modal.CloseButton />
        </Modal.Header>
        <Modal.Body>
          <Box pos="relative">
            <LoadingOverlay visible={loadState} />

            <Paper p="sm" radius="md" w="100%">
              <form onSubmit={form.onSubmit(handleSubmit)}>
                <Stack>
                  <Text size="lg">Alert Name</Text>
                  <TextInput
                    placeholder="Enter alert name..."
                    required
                    value={form.getValues().alert_name}
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
                    checked={form.getValues().notify}
                    {...form.getInputProps('notify')}
                  />
                  <Button type="submit">Update</Button>
                </Stack>
              </form>
            </Paper>
          </Box>
        </Modal.Body>
      </Modal.Content>
    </Modal.Root>
  )
}

export default ProjectKPIAlertModal
