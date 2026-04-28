import { useGetProjectReportInstances } from '@/api/v1/operational/project/report_instances'
import { useBulkUpdateReportInstances } from '@/api/v1/operational/report_instances'
import { useGetReportTypes } from '@/api/v1/operational/report_types'
import {
  Button,
  Group,
  Loader,
  Modal,
  ScrollArea,
  SegmentedControl,
  Stack,
  Text,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMemo, useState } from 'react'

interface ReportInstancesConfigModalProps {
  opened: boolean
  onClose: () => void
  projectId: string
}

type ReportInstanceState = 'off' | 'invisible' | 'visible'

export const ReportInstancesConfigModal = ({
  opened,
  onClose,
  projectId,
}: ReportInstancesConfigModalProps) => {
  const reportTypes = useGetReportTypes({})
  const reportInstances = useGetProjectReportInstances({
    pathParams: { project_id: projectId },
    queryParams: { deep: true },
  })
  const updateMutation = useBulkUpdateReportInstances()

  // Initialize state from existing report instances
  const initialStates = useMemo(() => {
    if (!reportInstances.data || !reportTypes.data) {
      return {}
    }

    const states: Record<number, ReportInstanceState> = {}

    // Start with all report types as "off"
    reportTypes.data.forEach((reportType) => {
      states[reportType.report_type_id] = 'off'
    })

    // Update with existing instances
    reportInstances.data.forEach((instance) => {
      states[instance.report_type_id] = instance.is_visible
        ? 'visible'
        : 'invisible'
    })

    return states
  }, [reportInstances.data, reportTypes.data])

  const [reportStates, setReportStates] = useState<Record<
    number,
    ReportInstanceState
  > | null>(null)

  const currentStates = reportStates ?? initialStates

  const handleReportInstancesModalClose = () => {
    setReportStates(null)
    onClose()
  }

  const handleStateChange = (
    reportTypeId: number,
    value: ReportInstanceState,
  ) => {
    setReportStates((prev) => {
      const base = prev ?? initialStates
      return {
        ...base,
        [reportTypeId]: value,
      }
    })
  }

  const handleReportInstancesConfigSave = async () => {
    if (!reportTypes.data) return

    // Calculate delta: only include instances that changed
    const reportInstancesToUpdate: Array<{
      report_type_id: number
      is_visible: boolean
    }> = []
    const reportTypeIdsToDelete: number[] = []

    reportTypes.data.forEach((reportType) => {
      const reportTypeId = reportType.report_type_id
      const initialState = initialStates[reportTypeId]
      const currentState = currentStates[reportTypeId]

      // Only process if state changed
      if (initialState !== currentState) {
        if (currentState === 'off') {
          // If changed to "off", add to deletion list (only if it existed before)
          if (initialState !== 'off') {
            reportTypeIdsToDelete.push(reportTypeId)
          }
        } else {
          // If changed to "invisible" or "visible", add to update list
          reportInstancesToUpdate.push({
            report_type_id: reportTypeId,
            is_visible: currentState === 'visible',
          })
        }
      }
    })

    try {
      await updateMutation.mutateAsync({
        project_id: projectId,
        data: {
          report_instances: reportInstancesToUpdate,
          report_type_ids_to_delete:
            reportTypeIdsToDelete.length > 0 ? reportTypeIdsToDelete : null,
        },
      })

      notifications.show({
        title: 'Success',
        message: 'Report instances updated successfully',
        color: 'green',
      })

      handleReportInstancesModalClose()
    } catch (error) {
      console.error('Failed to update report instances', error)
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
      onClose={handleReportInstancesModalClose}
      title="Configure Report Instances"
      size="lg"
    >
      {isLoading ? (
        <Group justify="center" p="xl">
          <Loader />
        </Group>
      ) : (
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Configure report types for this project. Set reports to
            &quot;Off&quot; to remove them, &quot;Invisible&quot; to hide from
            non-superadmin users, or &quot;Visible&quot; to show to all users.
          </Text>

          <ScrollArea h={400}>
            <Stack gap="sm">
              {reportTypes.data?.map((reportType) => (
                <Group
                  key={reportType.report_type_id}
                  justify="space-between"
                  align="center"
                >
                  <Text fw={500}>{reportType.name_long}</Text>
                  <SegmentedControl
                    value={currentStates[reportType.report_type_id] || 'off'}
                    onChange={(value) =>
                      handleStateChange(
                        reportType.report_type_id,
                        value as ReportInstanceState,
                      )
                    }
                    data={[
                      { label: 'Off', value: 'off' },
                      { label: 'Invisible', value: 'invisible' },
                      { label: 'Visible', value: 'visible' },
                    ]}
                  />
                </Group>
              ))}
            </Stack>
          </ScrollArea>

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={handleReportInstancesModalClose}>
              Cancel
            </Button>
            <Button
              onClick={handleReportInstancesConfigSave}
              loading={updateMutation.isPending}
            >
              Save
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  )
}
