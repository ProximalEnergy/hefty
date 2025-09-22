import { useGetKPIInstances } from '@/api/v1/operational/kpi_instances'
import { KPIType } from '@/api/v1/operational/kpi_types'
import { useDeleteKPIAlert, useGetKPIAlerts } from '@/hooks/api'
import { KPIAlertProps } from '@/hooks/types'
import {
  Box,
  Button,
  Group,
  LoadingOverlay,
  Modal,
  Paper,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconEdit, IconTrash } from '@tabler/icons-react'
import { useState } from 'react'
import { useParams } from 'react-router-dom'

import ProjectKPIAlertModal from './ProjectKPIAlertModal'

const ProjectKPIExistingAlerts = ({
  kpi_type_id,
}: {
  kpi_type_id?: number
}) => {
  const { projectId } = useParams()

  const comparisonOptions = [
    { value: 'gte', label: 'Greater than or equal to' },
    { value: 'gt', label: 'Greater than' },
    { value: 'eq', label: 'Exactly' },
    { value: 'lt', label: 'Less than' },
    { value: 'lte', label: 'Less than or equal to' },
  ]
  const { mutate: confirmDelete } = useDeleteKPIAlert()

  const [
    deletionModalOpened,
    { open: openDeletionModal, close: closeDeletionModal },
  ] = useDisclosure(false)
  const [selectedKPIForDeletion, setSelectedKPIForDeletion] =
    useState<KPIAlertProps>()
  const [editModalOpened, { open: openEditModal, close: closeEditModal }] =
    useDisclosure(false)
  const [selectedKPIForEdit, setSelectedKPIForEdit] = useState<KPIAlertProps>()

  const { data: alertData, isLoading: alertLoading } = useGetKPIAlerts({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { kpi_type_id: kpi_type_id },
  })

  const handleEdit = (selected_alert: KPIAlertProps) => {
    setSelectedKPIForEdit(selected_alert)
    openEditModal()
  }
  const handleDelete = (selected_alert: KPIAlertProps) => {
    setSelectedKPIForDeletion(selected_alert)
    openDeletionModal()
  }
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

  const data = (instanceData?.map((item) => item.kpi_type) ?? []) as KPIType[]

  const getKPIInfo = (kpi_type_id: string | null) => {
    const kpi = data.find((item) => item.kpi_type_id.toString() === kpi_type_id)
    return kpi
      ? { name_long: kpi.name_long, unit: kpi.unit }
      : { name_long: 'Unknown', unit: '' }
  }
  const handleSuccessfulUpdate = () => {
    closeEditModal()
  }

  const isLoading = alertLoading || instanceLoading

  return (
    <Box pos="relative">
      <Paper withBorder p="xs" radius="md">
        <LoadingOverlay visible={isLoading} />
        <Title order={3}>Your Alerts:</Title>
        <Stack>
          {alertData?.map((alert) => {
            const kpiInfo = getKPIInfo(alert.config.kpi_type_id)
            const comparison_func = comparisonOptions.find(
              (item) => item.value === alert.config.comparison,
            )?.label

            return (
              <Paper key={alert.kpi_alert_id} withBorder p="xs" radius="sm">
                <Modal
                  opened={deletionModalOpened}
                  onClose={closeDeletionModal}
                  title={`Delete alert "${selectedKPIForDeletion?.config.alert_name}"?`}
                  centered
                >
                  <Stack align="center">
                    <Text>Warning: this action cannot be undone.</Text>
                    <Group>
                      <Button onClick={closeDeletionModal}>Cancel</Button>
                      <Button
                        onClick={() => {
                          confirmDelete({
                            project_id: projectId ?? '',
                            alert_id:
                              selectedKPIForDeletion?.kpi_alert_id ?? -1,
                          })
                          closeDeletionModal()
                        }}
                      >
                        Delete
                      </Button>
                    </Group>
                  </Stack>
                </Modal>
                {selectedKPIForEdit && (
                  <ProjectKPIAlertModal
                    opened={editModalOpened}
                    onClose={closeEditModal}
                    alert={selectedKPIForEdit}
                    onSuccessfulUpdate={handleSuccessfulUpdate} // Add this line
                  />
                )}
                <Group justify="space-between">
                  <Text>
                    <strong>{alert.config.alert_name}</strong>
                  </Text>
                  <Group>
                    <Button size="compact-xs" onClick={() => handleEdit(alert)}>
                      <IconEdit size={20} />
                    </Button>
                    <Button
                      size="compact-xs"
                      onClick={() => handleDelete(alert)}
                    >
                      <IconTrash size={20} />
                    </Button>
                  </Group>
                </Group>
                <Text>
                  Alerting when <em>{kpiInfo.name_long}</em> is{' '}
                  {comparison_func?.toLowerCase()}{' '}
                  {/* If kpiInfo unit is percent, multiply the value by 100.
                          Advanced logic is for type handling. */}
                  {kpiInfo.unit === '%'
                    ? typeof alert.config.threshold_value === 'number'
                      ? alert.config.threshold_value * 100
                      : alert.config.threshold_value
                        ? parseFloat(alert.config.threshold_value) * 100
                        : alert.config.threshold_value
                    : alert.config.threshold_value}
                  {kpiInfo.unit === 'deg' ? '°' : kpiInfo.unit} during{' '}
                  {alert.config.duration_value?.toLowerCase()}.
                </Text>
                <Text>
                  <strong>Notify:</strong> {alert.config.notify ? 'Yes' : 'No'}
                </Text>
              </Paper>
            )
          })}
        </Stack>
      </Paper>
    </Box>
  )
}

export default ProjectKPIExistingAlerts
