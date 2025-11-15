import {
  useBulkUpdateReportInstances,
  useGetReportTypes,
} from '@/api/v1/operational/report_instances'
import { useGetProjectReportInstances } from '@/hooks/api'
import {
  Button,
  Group,
  Loader,
  Modal,
  ScrollArea,
  Stack,
  Switch,
  Text,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useEffect, useMemo, useState } from 'react'

interface ReportInstancesConfigModalProps {
  opened: boolean
  onClose: () => void
  projectId: string
}

export const ReportInstancesConfigModal = ({
  opened,
  onClose,
  projectId,
}: ReportInstancesConfigModalProps) => {
  const reportTypes = useGetReportTypes({})
  const reportInstances = useGetProjectReportInstances({
    pathParams: { projectId },
    queryParams: { deep: true },
  })
  const updateMutation = useBulkUpdateReportInstances()

  // Initialize visibility state from existing report instances
  const initialVisibility = useMemo(() => {
    if (!reportInstances.data || !reportTypes.data) {
      return {}
    }

    const visibility: Record<number, boolean> = {}

    // Start with all report types as not visible
    reportTypes.data.forEach((reportType) => {
      visibility[reportType.report_type_id] = false
    })

    // Update with existing instances
    reportInstances.data.forEach((instance) => {
      visibility[instance.report_type_id] = instance.is_visible
    })

    return visibility
  }, [reportInstances.data, reportTypes.data])

  // State to track which report types are visible
  const [reportVisibility, setReportVisibility] = useState<
    Record<number, boolean>
  >(() => initialVisibility)

  // Reset state when modal opens or data changes
  useEffect(() => {
    if (opened && Object.keys(initialVisibility).length > 0) {
      setReportVisibility(initialVisibility)
    }
  }, [opened, initialVisibility])

  const handleToggle = (reportTypeId: number) => {
    setReportVisibility((prev) => ({
      ...prev,
      [reportTypeId]: !prev[reportTypeId],
    }))
  }

  const handleSave = async () => {
    if (!reportTypes.data) return

    const reportInstancesData = reportTypes.data.map((reportType) => ({
      report_type_id: reportType.report_type_id,
      is_visible: reportVisibility[reportType.report_type_id] || false,
    }))

    try {
      await updateMutation.mutateAsync({
        projectId,
        data: {
          report_instances: reportInstancesData,
        },
      })

      notifications.show({
        title: 'Success',
        message: 'Report instances updated successfully',
        color: 'green',
      })

      onClose()
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to update report instances',
        color: 'red',
      })
    }
  }

  const isLoading = reportTypes.isLoading || reportInstances.isLoading

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={<Title order={3}>Configure Report Instances</Title>}
      size="lg"
    >
      {isLoading ? (
        <Group justify="center" p="xl">
          <Loader />
        </Group>
      ) : (
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Enable or disable report types for this project. Only enabled
            reports will be visible to users.
          </Text>

          <ScrollArea h={400}>
            <Stack gap="sm">
              {reportTypes.data?.map((reportType) => (
                <Group key={reportType.report_type_id} justify="space-between">
                  <Text fw={500}>{reportType.name_long}</Text>
                  <Switch
                    checked={
                      reportVisibility[reportType.report_type_id] || false
                    }
                    onChange={() => handleToggle(reportType.report_type_id)}
                  />
                </Group>
              ))}
            </Stack>
          </ScrollArea>

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={handleSave} loading={updateMutation.isPending}>
              Save
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  )
}
