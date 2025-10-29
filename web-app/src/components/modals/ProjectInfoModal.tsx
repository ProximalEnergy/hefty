import { useGetUserType } from '@/api/admin'
import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import { useGetOMContractorScopes } from '@/api/v1/operational/project/om_contractors'
import { useGetProjectTypes } from '@/api/v1/operational/project_types'
import { Project } from '@/api/v1/operational/projects'
import RequiresUserType from '@/components/admin/RequiresUserType'
import {
  Button,
  Card,
  Divider,
  Grid,
  Group,
  Modal,
  ScrollArea,
  Stack,
  Tabs,
  Text,
  Timeline,
  Title,
  useComputedColorScheme,
} from '@mantine/core'
import { useNavigate, useParams } from 'react-router'

interface ProjectInfoModalProps {
  opened: boolean
  onClose: () => void
  projectData?: Project | null
}

export default function ProjectInfoModal({
  opened,
  onClose,
  projectData,
}: ProjectInfoModalProps) {
  const navigate = useNavigate()
  const { projectId } = useParams()
  const userType = useGetUserType({})
  const { data: projectTypes } = useGetProjectTypes({})
  const { data: deviceTypes } = useGetDeviceTypes({
    queryOptions: { enabled: !!projectId },
  })
  const computedColorScheme = useComputedColorScheme()

  const isUserAdmin =
    userType.data?.user_type_id === 2 || userType.data?.user_type_id === 1

  const isUserSuperadmin = userType.data?.user_type_id === 1

  // Helper function to get icon styling for dark mode support
  const getIconStyle = () => ({
    filter:
      computedColorScheme === 'dark' ? 'invert(1) brightness(0.8)' : 'none',
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

  // Helper to format dates for display
  const formatDate = (dateString?: string | null) => {
    if (!dateString) return 'Not set'
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    } catch {
      return 'Invalid date'
    }
  }

  // Helper to format PPA rate
  const formatPPARate = (ppa?: { rate?: number; type?: string } | null) => {
    if (!ppa?.rate) return 'Not set'
    return `$${ppa.rate.toFixed(2)}/MWh (${ppa.type || 'flat_rate'})`
  }

  // Helper to convert device type IDs to names
  const formatDeviceTypeIds = (deviceTypeIds: number[]) => {
    if (!deviceTypes || deviceTypeIds.length === 0) return 'None'
    const names = deviceTypeIds
      .map((id) => {
        const deviceType = deviceTypes.find((dt) => dt.device_type_id === id)
        return deviceType?.name_long || `Device Type ${id}`
      })
      .join(', ')
    return names || 'None'
  }

  // Helper to get milestone data with dates for sorting
  const getMilestones = () => {
    const milestones = [
      {
        id: 'financial_close',
        title: 'Financial Close',
        bullet: '💰',
        date: projectData?.financial_close_date,
      },
      {
        id: 'notice_to_proceed',
        title: 'Notice to Proceed',
        bullet: '📋',
        date: projectData?.notice_to_proceed_date,
      },
      {
        id: 'commencement_of_construction',
        title: 'Commencement of Construction',
        bullet: '🏗️',
        date: projectData?.commencement_of_construction_date,
      },
      {
        id: 'mechanical_completion',
        title: 'Mechanical Completion',
        bullet: '🔧',
        date: projectData?.mechanical_completion_date,
      },
      {
        id: 'substantial_completion',
        title: 'Substantial Completion',
        bullet: '✅',
        date: projectData?.substantial_completion_date,
      },
      {
        id: 'interconnection_approval',
        title: 'Interconnection Approval',
        bullet: '🔌',
        date: projectData?.interconnection_approval_date,
      },
      {
        id: 'performance_test_completion',
        title: 'Performance Test Completion',
        bullet: '🧪',
        date: projectData?.performance_test_completion_date,
      },
      {
        id: 'placed_in_service',
        title: 'Placed in Service',
        bullet: '⚡',
        date: projectData?.placed_in_service_date,
      },
      {
        id: 'commercial_operation',
        title: 'Commercial Operation Date',
        bullet: '🚀',
        date: projectData?.cod,
      },
    ]

    // Add admin-only milestones
    if (isUserAdmin) {
      milestones.push(
        {
          id: 'first_realtime_data',
          title: 'First Realtime Data',
          bullet: '📊',
          date: projectData?.first_realtime_data_received_date,
        },
        {
          id: 'first_data_backfilled',
          title: 'First Data Backfilled',
          bullet: '📈',
          date: projectData?.first_data_backfilled_date,
        },
      )
    }

    // Sort by date, with null/undefined dates at the end
    return milestones.sort((a, b) => {
      if (!a.date && !b.date) return 0
      if (!a.date) return 1
      if (!b.date) return -1
      return new Date(a.date).getTime() - new Date(b.date).getTime()
    })
  }

  const handleEditProject = () => {
    onClose()
    navigate(`/projects/${projectId}/settings?tab=project-info`)
  }

  // Equipment info for the equipment tab (keeping existing structure)
  const equipmentInfo = {
    ppcScada: {
      provider: 'Merit Controls',
    },
    substationTransformer: {
      hvVoltage: '345 kV',
      mvVoltage: '34.5 kV',
      windingConfiguration: 'Delta-Wye',
      impedance: '8.5%',
    },
    bessMvt: {
      mv: '34.5 kV',
      lv: '480 V',
      windingConfiguration: 'Delta-Wye',
      impedance: '6.0%',
    },
    mvSwitchgear: {
      specification: '34.5 kV, 2000A, 40 kA',
    },
    bessPcs: {
      temperatureDeratingCurve: 'Available',
      altitudeDeratingCurve: 'Available',
      voltageDeratingCurve: 'Available',
      pqCurve: 'Available',
    },
    batteryContainer: {
      modelBrand: 'Tesla Megapack 2',
      stringQuantityPerContainer: '4',
      moduleQuantityPerString: '25',
      cellQuantityPerModule: '12',
      parallelSerialConfiguration: '4S25P12S',
      stringSpec: '25 modules in series',
      cellSpec: '12 cells in series per module',
      cooling: 'Liquid Cooled',
    },
  }

  // O&M Contractor Scopes
  const omContractors = useGetOMContractorScopes({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: { enabled: !!projectId },
  })

  const handleManageOM = () => {
    onClose()
    navigate(`/projects/${projectId}/settings?tab=om-contractors`)
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Text size="xl" fw={600}>
          Project Information
        </Text>
      }
      size="xl"
    >
      <Tabs defaultValue="project">
        <Tabs.List>
          <Tabs.Tab value="project">General</Tabs.Tab>
          {isUserSuperadmin && <Tabs.Tab value="equipment">Equipment</Tabs.Tab>}
          <Tabs.Tab value="om-contractors">O&M Contractors</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="project" pt="md">
          <ScrollArea h={600}>
            <Stack gap="md">
              <Card withBorder p="md">
                <Stack gap="lg">
                  <Group justify="space-between" align="center">
                    <Title order={3} mb={0}>
                      Project Information
                    </Title>
                    <RequiresUserType requiredUserType="admin" silent>
                      <Button
                        variant="light"
                        size="sm"
                        onClick={handleEditProject}
                      >
                        Edit
                      </Button>
                    </RequiresUserType>
                  </Group>

                  <Grid>
                    <Grid.Col span={6}>
                      <Title order={4} mb="md">
                        General
                      </Title>
                      <Stack gap="md">
                        <Group justify="space-between">
                          <Text size="sm" c="dimmed">
                            Project Name:
                          </Text>
                          <Text size="sm" fw={500}>
                            {projectData?.name_long || 'Not set'}
                          </Text>
                        </Group>
                        <Group justify="space-between">
                          <Text size="sm" c="dimmed">
                            Project Type:
                          </Text>
                          <Text size="sm" fw={500}>
                            {projectData?.project_type?.name_long ||
                              projectTypeMap[
                                projectData?.project_type_id || 0
                              ] ||
                              'Not set'}
                          </Text>
                        </Group>
                        <Group justify="space-between">
                          <Text size="sm" c="dimmed">
                            Address:
                          </Text>
                          <Text size="sm" fw={500}>
                            {projectData?.address || 'Not set'}
                          </Text>
                        </Group>
                        <Group justify="space-between">
                          <Text size="sm" c="dimmed">
                            Elevation:
                          </Text>
                          <Text size="sm" fw={500}>
                            {projectData?.elevation
                              ? `${projectData.elevation} m`
                              : 'Not set'}
                          </Text>
                        </Group>
                        <Group justify="space-between">
                          <Text size="sm" c="dimmed">
                            Time Zone:
                          </Text>
                          <Text size="sm" fw={500}>
                            {projectData?.time_zone || 'Not set'}
                          </Text>
                        </Group>
                        {(projectData?.project_type_id === 1 ||
                          projectData?.project_type_id === 3) && (
                          <Group justify="space-between">
                            <Text size="sm" c="dimmed">
                              PV PPA Price:
                            </Text>
                            <Text size="sm" fw={500}>
                              {formatPPARate(projectData?.ppa)}
                            </Text>
                          </Group>
                        )}
                      </Stack>
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <Title order={4} mb="md">
                        Capacity
                      </Title>
                      <Stack gap="md">
                        <Group justify="space-between">
                          <Text size="sm" c="dimmed">
                            POI Capacity:
                          </Text>
                          <Text size="sm" fw={500}>
                            {projectData?.poi
                              ? `${projectData.poi} MW`
                              : 'Not set'}
                          </Text>
                        </Group>
                        {(projectData?.project_type_id === 1 ||
                          projectData?.project_type_id === 3) && (
                          <>
                            <Group justify="space-between">
                              <Text size="sm" c="dimmed">
                                PV DC Capacity:
                              </Text>
                              <Text size="sm" fw={500}>
                                {projectData?.capacity_dc
                                  ? `${projectData.capacity_dc} MW`
                                  : 'Not set'}
                              </Text>
                            </Group>
                            <Group justify="space-between">
                              <Text size="sm" c="dimmed">
                                PV AC Capacity:
                              </Text>
                              <Text size="sm" fw={500}>
                                {projectData?.capacity_ac
                                  ? `${projectData.capacity_ac} MW`
                                  : 'Not set'}
                              </Text>
                            </Group>
                          </>
                        )}
                        {(projectData?.project_type_id === 2 ||
                          projectData?.project_type_id === 3) && (
                          <>
                            <Group justify="space-between">
                              <Text size="sm" c="dimmed">
                                BESS Power AC:
                              </Text>
                              <Text size="sm" fw={500}>
                                {projectData?.capacity_bess_power_ac
                                  ? `${projectData.capacity_bess_power_ac} MW`
                                  : 'Not set'}
                              </Text>
                            </Group>
                            <Group justify="space-between">
                              <Text size="sm" c="dimmed">
                                BESS Energy BOL DC:
                              </Text>
                              <Text size="sm" fw={500}>
                                {projectData?.capacity_bess_energy_bol_dc
                                  ? `${projectData.capacity_bess_energy_bol_dc} MWh`
                                  : 'Not set'}
                              </Text>
                            </Group>
                          </>
                        )}
                      </Stack>
                    </Grid.Col>
                  </Grid>

                  <Divider my="lg" />

                  <Title order={4} mb="md">
                    Interconnection Details
                  </Title>
                  <Stack gap="md">
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Interconnecting ISO:
                      </Text>
                      <Text size="sm" fw={500}>
                        {projectData?.interconnecting_iso || 'Not set'}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Interconnecting Utility:
                      </Text>
                      <Text size="sm" fw={500}>
                        {projectData?.interconnecting_utility || 'Not set'}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Interconnecting Substation:
                      </Text>
                      <Text size="sm" fw={500}>
                        {projectData?.interconnecting_substation || 'Not set'}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Interconnecting Voltage:
                      </Text>
                      <Text size="sm" fw={500}>
                        {projectData?.interconnecting_voltage
                          ? `${projectData.interconnecting_voltage} kV`
                          : 'Not set'}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Interconnecting Node Code:
                      </Text>
                      <Text size="sm" fw={500}>
                        {projectData?.interconnecting_node_code || 'Not set'}
                      </Text>
                    </Group>
                  </Stack>

                  <Divider my="lg" />

                  <Title order={4} mb="md">
                    Project Milestones
                  </Title>
                  <Timeline active={-1} bulletSize={24} lineWidth={2}>
                    {getMilestones().map((milestone) => (
                      <Timeline.Item
                        key={milestone.id}
                        bullet={milestone.bullet}
                        title={milestone.title}
                      >
                        <Text size="sm" c="dimmed">
                          {formatDate(milestone.date)}
                        </Text>
                      </Timeline.Item>
                    ))}
                  </Timeline>
                </Stack>
              </Card>
            </Stack>
          </ScrollArea>
        </Tabs.Panel>

        {isUserSuperadmin && (
          <Tabs.Panel value="equipment" pt="md">
            <ScrollArea h={600}>
              <Stack gap="md">
                <Card withBorder p="md">
                  <Stack gap="lg">
                    <Title order={3} mb="md">
                      Equipment Summary
                    </Title>

                    <Group gap="xs" mb="md">
                      <img
                        src="/icon-substation.svg"
                        alt="PPC/SCADA"
                        width={20}
                        height={20}
                        style={getIconStyle()}
                      />
                      <Title order={4} mb={0}>
                        PPC/SCADA
                      </Title>
                    </Group>
                    <Stack gap="md">
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Provider:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.ppcScada.provider}
                        </Text>
                      </Group>
                    </Stack>

                    <Divider my="lg" />

                    <Group gap="xs" mb="md">
                      <img
                        src="/icon-substation.svg"
                        alt="Substation Transformer"
                        width={20}
                        height={20}
                        style={getIconStyle()}
                      />
                      <Title order={4} mb={0}>
                        Substation Transformer
                      </Title>
                    </Group>
                    <Stack gap="md">
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          HV Voltage:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.substationTransformer.hvVoltage}
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          MV Voltage:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.substationTransformer.mvVoltage}
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Winding Configuration:
                        </Text>
                        <Text size="sm" fw={500}>
                          {
                            equipmentInfo.substationTransformer
                              .windingConfiguration
                          }
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Impedance:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.substationTransformer.impedance}
                        </Text>
                      </Group>
                    </Stack>

                    <Divider my="lg" />

                    <Group gap="xs" mb="md">
                      <img
                        src="/icon_bess_mvt.svg"
                        alt="BESS MVT"
                        width={20}
                        height={20}
                        style={getIconStyle()}
                      />
                      <Title order={4} mb={0}>
                        BESS MVT
                      </Title>
                    </Group>
                    <Stack gap="md">
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          MV:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.bessMvt.mv}
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          LV:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.bessMvt.lv}
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Winding Configuration:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.bessMvt.windingConfiguration}
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Impedance:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.bessMvt.impedance}
                        </Text>
                      </Group>
                    </Stack>

                    <Divider my="lg" />

                    <Group gap="xs" mb="md">
                      <img
                        src="/icon-substation.svg"
                        alt="MV Switchgear"
                        width={20}
                        height={20}
                        style={getIconStyle()}
                      />
                      <Title order={4} mb={0}>
                        MV Switchgear
                      </Title>
                    </Group>
                    <Stack gap="md">
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Specification:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.mvSwitchgear.specification}
                        </Text>
                      </Group>
                    </Stack>

                    <Divider my="lg" />

                    <Group gap="xs" mb="md">
                      <img
                        src="/icon_bess_pcs.svg"
                        alt="BESS PCS"
                        width={20}
                        height={20}
                        style={getIconStyle()}
                      />
                      <Title order={4} mb={0}>
                        BESS PCS
                      </Title>
                    </Group>
                    <Stack gap="md">
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Temperature Derating Curve:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.bessPcs.temperatureDeratingCurve}
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Altitude Derating Curve:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.bessPcs.altitudeDeratingCurve}
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Voltage Derating Curve:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.bessPcs.voltageDeratingCurve}
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          PQ Curve:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.bessPcs.pqCurve}
                        </Text>
                      </Group>
                    </Stack>

                    <Divider my="lg" />

                    <Group gap="xs" mb="md">
                      <img
                        src="/icon_bess_module.svg"
                        alt="Battery Container"
                        width={20}
                        height={20}
                        style={getIconStyle()}
                      />
                      <Title order={4} mb={0}>
                        Battery Container
                      </Title>
                    </Group>
                    <Stack gap="md">
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Model/Brand:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.batteryContainer.modelBrand}
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          String Quantity Per Container:
                        </Text>
                        <Text size="sm" fw={500}>
                          {
                            equipmentInfo.batteryContainer
                              .stringQuantityPerContainer
                          }
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Module Quantity Per String:
                        </Text>
                        <Text size="sm" fw={500}>
                          {
                            equipmentInfo.batteryContainer
                              .moduleQuantityPerString
                          }
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Cell Quantity Per Module:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.batteryContainer.cellQuantityPerModule}
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Parallel/Serial Configuration:
                        </Text>
                        <Text size="sm" fw={500}>
                          {
                            equipmentInfo.batteryContainer
                              .parallelSerialConfiguration
                          }
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          String Spec:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.batteryContainer.stringSpec}
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Cell Spec:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.batteryContainer.cellSpec}
                        </Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Cooling:
                        </Text>
                        <Text size="sm" fw={500}>
                          {equipmentInfo.batteryContainer.cooling}
                        </Text>
                      </Group>
                    </Stack>
                  </Stack>
                </Card>
              </Stack>
            </ScrollArea>
          </Tabs.Panel>
        )}

        <Tabs.Panel value="om-contractors" pt="md">
          <ScrollArea h={600}>
            <Stack gap="md">
              <Card withBorder p="md">
                <Stack gap="lg">
                  <Group justify="space-between" align="center">
                    <Title order={3} mb={0}>
                      O&M Contractor Summary
                    </Title>
                    <Button variant="light" size="sm" onClick={handleManageOM}>
                      Manage
                    </Button>
                  </Group>

                  {omContractors.isLoading ? (
                    <Text size="sm" c="dimmed">
                      Loading...
                    </Text>
                  ) : (omContractors.data || []).length === 0 ? (
                    <Text size="sm" c="dimmed">
                      No O&M contractor scopes found.
                    </Text>
                  ) : (
                    <Stack gap="md">
                      {(omContractors.data || []).map((scope) => (
                        <Card
                          key={scope.om_contractor_scope_id}
                          withBorder
                          p="md"
                        >
                          <Stack gap="sm">
                            <Group justify="space-between">
                              <Text size="sm" c="dimmed">
                                Company:
                              </Text>
                              <Text size="sm" fw={500}>
                                {scope.company_name_long ||
                                  scope.company_name_short ||
                                  scope.company_id}
                              </Text>
                            </Group>
                            <Group justify="space-between">
                              <Text size="sm" c="dimmed">
                                Addressee:
                              </Text>
                              <Text size="sm" fw={500}>
                                {scope.contractor_addressee || 'Not set'}
                              </Text>
                            </Group>
                            <Group justify="space-between">
                              <Text size="sm" c="dimmed">
                                Email:
                              </Text>
                              <Text size="sm" fw={500}>
                                {scope.contractor_email || 'Not set'}
                              </Text>
                            </Group>
                            <Group justify="space-between">
                              <Text size="sm" c="dimmed">
                                Phone:
                              </Text>
                              <Text size="sm" fw={500}>
                                {scope.contractor_phone || 'Not set'}
                              </Text>
                            </Group>
                            {scope.scope_json?.device_type_ids && (
                              <Group justify="space-between">
                                <Text size="sm" c="dimmed">
                                  Device Types In Scope:
                                </Text>
                                <Text size="sm" fw={500}>
                                  {formatDeviceTypeIds(
                                    scope.scope_json.device_type_ids,
                                  )}
                                </Text>
                              </Group>
                            )}
                          </Stack>
                        </Card>
                      ))}
                    </Stack>
                  )}
                </Stack>
              </Card>
            </Stack>
          </ScrollArea>
        </Tabs.Panel>
      </Tabs>
    </Modal>
  )
}
