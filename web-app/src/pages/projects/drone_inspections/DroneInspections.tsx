import { useGetUserSelf } from '@/api/v1/admin/users'
import {
  DroneInspection,
  DroneIntegration,
  DronePermission,
  DroneProvider,
  useGetDroneAnomalies,
  useGetDroneInspections,
  useGetDroneIntegrations,
  useGetDronePermissions,
  useGetDroneProviders,
  useSyncZeitviewAnomalies,
  useSyncZeitviewInspections,
} from '@/api/v1/operational/drone_integrations'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { OrderDroneInspectionModal } from '@/components/modals/OrderDroneInspectionModal'
import { StatsGrid } from '@/components/stats/StatsGrid'
import { getCompanyLogoUrl } from '@/utils/cdn'
import {
  ActionIcon,
  Badge,
  Box,
  Card,
  Grid,
  Group,
  Image,
  Loader,
  ScrollArea,
  Stack,
  Text,
  Timeline,
  Title,
  Tooltip,
  useMantineColorScheme,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import {
  IconAlertTriangle,
  IconDrone,
  IconPlus,
  IconRefresh,
} from '@tabler/icons-react'
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router'

import DroneAnomaliesTable from './DroneAnomaliesTable'
import DroneInspectionsMap from './DroneInspectionsMap'

const DroneInspections: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const { colorScheme } = useMantineColorScheme()
  const { data: integrations, isLoading: integrationsLoading } =
    useGetDroneIntegrations()
  const { data: permissions, isLoading: permissionsLoading } =
    useGetDronePermissions()
  const { data: providers, isLoading: providersLoading } =
    useGetDroneProviders()

  const self = useGetUserSelf({})
  const [orderModalOpened, { open: openOrderModal, close: closeOrderModal }] =
    useDisclosure(false)

  const timelineRef = useRef<HTMLDivElement>(null)
  const itemRefs = useRef<(HTMLDivElement | null)[]>([])
  const syncedAnomalyInspections = useRef<Set<string>>(new Set())

  const currentIntegration = React.useMemo(() => {
    if (!integrations || !projectId) return null
    return integrations.find(
      (i: DroneIntegration) => i.project_id === projectId,
    )
  }, [integrations, projectId])

  const currentProvider = React.useMemo(() => {
    if (!providers || !currentIntegration) return null
    return providers.find(
      (p: DroneProvider) =>
        p.drone_provider_id === currentIntegration.drone_provider_id,
    )
  }, [providers, currentIntegration])

  // Function to get provider logo URL based on theme
  const getProviderLogoUrl = (providerName: string): string | null => {
    const name = providerName.toLowerCase()
    if (name.includes('zeitview')) {
      const logoFilename =
        colorScheme === 'dark' ? 'logo_zeitview_white.png' : 'logo_zeitview.png'
      return getCompanyLogoUrl(logoFilename)
    }
    // Add more providers as needed
    return null
  }

  const hasPermission = React.useMemo(() => {
    if (!integrations || !permissions || !self.data || !projectId) {
      return false
    }
    const companyId = self.data.company_id
    if (!companyId) {
      return false
    }
    return permissions.some(
      (p: DronePermission) =>
        p.company_id === companyId &&
        integrations.some(
          (i: DroneIntegration) =>
            i.drone_integration_id === p.drone_integration_id &&
            i.project_id === projectId &&
            p.can_view,
        ),
    )
  }, [integrations, permissions, self.data, projectId])

  const {
    data: inspections,
    isLoading: inspectionsLoading,
    refetch: refetchInspections,
  } = useGetDroneInspections({
    pathParams: { projectId: projectId! },
    queryOptions: { enabled: !!projectId },
  })

  const {
    refetch: syncInspections,
    isFetching: isSyncingInspections,
    isSuccess: isSyncInspectionsSuccess,
  } = useSyncZeitviewInspections(projectId, {
    enabled: false,
  })

  // Auto-sync when no inspections found locally
  useEffect(() => {
    if (
      hasPermission &&
      !inspectionsLoading &&
      inspections &&
      inspections.length === 0 &&
      !isSyncingInspections
    ) {
      syncInspections()
    }
  }, [
    hasPermission,
    inspectionsLoading,
    inspections,
    isSyncingInspections,
    syncInspections,
  ])

  useEffect(() => {
    if (isSyncInspectionsSuccess) {
      refetchInspections()
    }
  }, [isSyncInspectionsSuccess, refetchInspections])

  const sortedInspections = useMemo(() => {
    return (inspections || [])
      .slice()
      .sort(
        (a, b) =>
          new Date(b.inspection_time).getTime() -
          new Date(a.inspection_time).getTime(),
      )
  }, [inspections])

  const [selectedInspection, setSelectedInspection] =
    useState<DroneInspection | null>(null)

  useEffect(() => {
    if (sortedInspections && sortedInspections.length > 0) {
      // Always set to the latest inspection (first in sorted array)
      queueMicrotask(() => setSelectedInspection(sortedInspections[0]))
    }
  }, [sortedInspections])

  const {
    data: anomalies,
    isLoading: anomaliesLoading,
    refetch: refetchAnomalies,
  } = useGetDroneAnomalies({
    pathParams: {
      projectId: projectId!,
      inspectionId: selectedInspection?.inspection_uuid ?? '',
    },
    queryOptions: {
      enabled: !!projectId && !!selectedInspection?.inspection_uuid,
    },
  })

  const {
    refetch: syncAnomalies,
    isFetching: isSyncingAnomalies,
    isSuccess: isSyncAnomaliesSuccess,
  } = useSyncZeitviewAnomalies(projectId, selectedInspection?.inspection_uuid, {
    enabled: false,
  })

  useEffect(() => {
    if (isSyncAnomaliesSuccess) {
      refetchAnomalies()
    }
  }, [isSyncAnomaliesSuccess, refetchAnomalies])

  // Auto-sync anomalies when no anomalies found for selected inspection
  useEffect(() => {
    const inspectionId = selectedInspection?.inspection_uuid
    if (
      hasPermission &&
      !anomaliesLoading &&
      anomalies &&
      anomalies.length === 0 &&
      !isSyncingAnomalies &&
      inspectionId &&
      !syncedAnomalyInspections.current.has(inspectionId)
    ) {
      syncedAnomalyInspections.current.add(inspectionId)
      syncAnomalies()
    }
  }, [
    hasPermission,
    anomaliesLoading,
    anomalies,
    isSyncingAnomalies,
    selectedInspection,
    syncAnomalies,
  ])

  if (
    integrationsLoading ||
    permissionsLoading ||
    providersLoading ||
    self.isLoading ||
    inspectionsLoading ||
    (hasPermission &&
      inspections &&
      inspections.length === 0 &&
      isSyncingInspections)
  ) {
    return <PageLoader />
  }

  return (
    <Stack p="md">
      <Group justify="space-between" align="center">
        <PageTitle
          info={
            <Text>
              This page displays drone inspection data for the project. Select
              an inspection from the timeline to view details and anomalies.
            </Text>
          }
        >
          Drone Inspections
        </PageTitle>
        {currentProvider && (
          <Group>
            <Text size="sm" c="dimmed">
              Powered by
            </Text>
            {getProviderLogoUrl(currentProvider.name_long) && (
              <Image
                src={getProviderLogoUrl(currentProvider.name_long)!}
                alt={`${currentProvider.name_long} logo`}
                h={36}
                fit="contain"
              />
            )}
          </Group>
        )}
      </Group>
      {!hasPermission ? (
        <Stack gap="md">
          <Card
            withBorder
            p="lg"
            style={{ backgroundColor: '#fff3cd', borderColor: '#ffeaa7' }}
          >
            <Group gap="sm">
              <IconAlertTriangle size={24} color="#856404" />
              <div>
                <Text size="md" fw={600} c="#856404">
                  Drone Integration Required
                </Text>
                <Text size="sm" c="#856404" mt={4}>
                  This project does not have a drone integration set up. Please
                  use the feedback button in the bottom left to reach out to the
                  Proximal team to set up a drone integration for this project.
                </Text>
              </div>
            </Group>
          </Card>
          <Card withBorder p="lg">
            <Stack gap="md">
              <Text size="md" fw={600}>
                Available Drone Inspection Providers
              </Text>
              <Group gap="lg">
                {providers && providers.length > 0
                  ? providers.map((provider) => {
                      const logoUrl = getProviderLogoUrl(provider.name_long)
                      return (
                        logoUrl && (
                          <Image
                            key={provider.drone_provider_id}
                            src={logoUrl}
                            alt={`${provider.name_long} logo`}
                            h={40}
                            fit="contain"
                          />
                        )
                      )
                    })
                  : getProviderLogoUrl('Zeitview') && (
                      <Image
                        src={getProviderLogoUrl('Zeitview')!}
                        alt="Zeitview logo"
                        h={40}
                        fit="contain"
                      />
                    )}
              </Group>
              <Text size="sm" c="dimmed">
                Other drone inspection providers can be integrated as well.
                Please contact us through the feedback button to discuss
                integration options.
              </Text>
            </Stack>
          </Card>
        </Stack>
      ) : sortedInspections && sortedInspections.length > 0 ? (
        <Stack>
          <Grid>
            <Grid.Col span={{ base: 12, md: 9 }}>
              {selectedInspection && (
                <Card
                  shadow="sm"
                  radius="md"
                  withBorder
                  key={selectedInspection.inspection_uuid}
                  style={{
                    position: 'relative',
                    overflow: 'hidden',
                    height: '800px',
                  }}
                >
                  {/* Map as Background */}
                  {anomalies ? (
                    <Box
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        zIndex: 0,
                      }}
                    >
                      <DroneInspectionsMap
                        anomalies={anomalies}
                        inspectionTime={selectedInspection.inspection_time}
                      />
                    </Box>
                  ) : (
                    <Box
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        zIndex: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: 'var(--mantine-color-gray-0)',
                      }}
                    >
                      <Stack align="center" gap="md">
                        <Loader size="lg" />
                      </Stack>
                    </Box>
                  )}

                  {/* Frosted Glass Gradient - Multiple Layers */}
                  <Box
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: '200px',
                      zIndex: 1,
                      pointerEvents: 'none',
                    }}
                  >
                    {/* Layer 1: 10px blur (top) */}
                    <Box
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        height: '50px',
                        background: 'rgba(255, 255, 255, 0.1)',
                        backdropFilter: 'blur(10px)',
                        WebkitBackdropFilter: 'blur(10px)',
                      }}
                    />
                    {/* Layer 2: 8px blur */}
                    <Box
                      style={{
                        position: 'absolute',
                        top: '50px',
                        left: 0,
                        right: 0,
                        height: '30px',
                        background: 'rgba(255, 255, 255, 0.08)',
                        backdropFilter: 'blur(8px)',
                        WebkitBackdropFilter: 'blur(8px)',
                      }}
                    />
                    {/* Layer 3: 6px blur */}
                    <Box
                      style={{
                        position: 'absolute',
                        top: '80px',
                        left: 0,
                        right: 0,
                        height: '30px',
                        background: 'rgba(255, 255, 255, 0.06)',
                        backdropFilter: 'blur(6px)',
                        WebkitBackdropFilter: 'blur(6px)',
                      }}
                    />
                    {/* Layer 4: 4px blur */}
                    <Box
                      style={{
                        position: 'absolute',
                        top: '110px',
                        left: 0,
                        right: 0,
                        height: '30px',
                        background: 'rgba(255, 255, 255, 0.04)',
                        backdropFilter: 'blur(4px)',
                        WebkitBackdropFilter: 'blur(4px)',
                      }}
                    />
                    {/* Layer 5: 2px blur */}
                    <Box
                      style={{
                        position: 'absolute',
                        top: '140px',
                        left: 0,
                        right: 0,
                        height: '30px',
                        background: 'rgba(255, 255, 255, 0.02)',
                        backdropFilter: 'blur(2px)',
                        WebkitBackdropFilter: 'blur(2px)',
                      }}
                    />
                    {/* Layer 6: 0px blur (bottom) */}
                    <Box
                      style={{
                        position: 'absolute',
                        top: '170px',
                        left: 0,
                        right: 0,
                        height: '30px',
                        background: 'rgba(255, 255, 255, 0)',
                        backdropFilter: 'blur(0px)',
                        WebkitBackdropFilter: 'blur(0px)',
                      }}
                    />
                  </Box>

                  {/* Dynamic Gradient Overlay */}
                  <Box
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: '200px', // Adjust this to end below StatsGrid
                      background:
                        colorScheme === 'dark'
                          ? 'linear-gradient(to bottom, rgba(37, 38, 43, 0.9) 0%, rgba(37, 38, 43, 0.7) 50%, rgba(37, 38, 43, 0) 100%)'
                          : 'linear-gradient(to bottom, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.7) 50%, rgba(255, 255, 255, 0) 100%)',
                      zIndex: 1,
                      pointerEvents: 'none',
                    }}
                  />

                  {/* Content Overlay */}
                  <Stack style={{ position: 'relative', zIndex: 2 }}>
                    <Group justify="space-between">
                      <Title order={3}>
                        {currentProvider?.name_long} Inspection:{' '}
                        {new Date(
                          selectedInspection.inspection_time,
                        ).toLocaleDateString()}
                      </Title>
                      {selectedInspection.service_tier && (
                        <Badge color="pink">
                          {selectedInspection.service_tier}
                        </Badge>
                      )}
                    </Group>

                    {/* Stats Grid */}
                    <div
                      style={{
                        display: 'contents',
                      }}
                    >
                      <style>{`
                          .drone-stats-grid .mantine-SimpleGrid-root {
                            grid-template-columns: repeat(3, 1fr) !important;
                          }
                          .drone-stats-grid .mantine-Text-root[data-fz="32"] {
                            font-size: 1.125rem !important;
                          }
                          .drone-stats-grid [style*="font-size: calc(2rem"] {
                            font-size: 1.5rem !important;
                          }
                        `}</style>
                      <div className="drone-stats-grid">
                        <StatsGrid
                          data={[
                            {
                              title: 'DC Power Loss',
                              icon: 'pcs',
                              value: `${selectedInspection.total_power_loss_kw?.toFixed(2)} kW (${selectedInspection.total_power_loss_percent?.toFixed(2)}%)`,
                              description:
                                'Total DC power loss identified during inspection',
                            },
                            {
                              title: 'Affected Modules',
                              icon: 'events',
                              value:
                                selectedInspection.total_affected_modules?.toString() ||
                                '0',
                              description:
                                'Number of modules with detected anomalies',
                            },
                            {
                              title: 'Remediation Recommended',
                              icon: 'events',
                              value:
                                anomalies
                                  ?.filter(
                                    (a) =>
                                      a.remediation_category ===
                                      'Remediation Recommended',
                                  )
                                  .length.toString() ?? '0',
                              description:
                                'Anomalies that require immediate attention and remediation',
                            },
                          ]}
                        />
                      </div>
                    </div>
                  </Stack>
                </Card>
              )}
            </Grid.Col>

            <Grid.Col span={{ base: 12, md: 3 }}>
              <Stack h="100%" flex={1}>
                <Card h="800px" withBorder radius="md">
                  <Stack h="100%" flex={1}>
                    <Group justify="space-between">
                      <Title order={3}>Inspection History</Title>
                      {hasPermission && (
                        <Tooltip label="Sync Inspections with Zeitview">
                          <ActionIcon
                            size="sm"
                            onClick={() => syncInspections()}
                            loading={isSyncingInspections}
                          >
                            <IconRefresh />
                          </ActionIcon>
                        </Tooltip>
                      )}
                    </Group>
                    <ScrollArea h="100%" scrollbars="y" scrollbarSize={8}>
                      <div style={{ position: 'relative' }}>
                        <Timeline
                          ref={timelineRef}
                          bulletSize={24}
                          lineWidth={2}
                        >
                          <Tooltip
                            label="Click to view order form"
                            position="right"
                          >
                            <Timeline.Item
                              key="order-flyover"
                              title={
                                <Text
                                  fw={600}
                                  c="var(--mantine-primary-color-light-color)"
                                >
                                  Request New Inspection...
                                </Text>
                              }
                              bullet={<IconPlus size={12} />}
                              color="green"
                              lineVariant="dashed"
                              style={{
                                cursor: 'pointer',
                                paddingTop: '12px',
                                paddingBottom: '12px',
                                marginTop: '5px',
                              }}
                              onClick={openOrderModal}
                            >
                              <Text size="xs" c="dimmed">
                                Click to request a new inspection for this
                                project
                              </Text>
                            </Timeline.Item>
                          </Tooltip>

                          {sortedInspections.map((inspection, index) => (
                            <Timeline.Item
                              ref={(el) => {
                                itemRefs.current[index] = el
                              }}
                              key={inspection.inspection_uuid}
                              title={
                                <Text
                                  fw={
                                    selectedInspection?.inspection_uuid ===
                                    inspection.inspection_uuid
                                      ? 600
                                      : 500
                                  }
                                  style={{
                                    color:
                                      selectedInspection?.inspection_uuid ===
                                      inspection.inspection_uuid
                                        ? 'var(--mantine-primary-color-light-color)'
                                        : undefined,
                                  }}
                                >
                                  {new Date(
                                    inspection.inspection_time,
                                  ).toLocaleDateString(undefined, {
                                    year: 'numeric',
                                    month: 'long',
                                    day: 'numeric',
                                  })}
                                </Text>
                              }
                              bullet={
                                selectedInspection?.inspection_uuid ===
                                inspection.inspection_uuid ? (
                                  <IconDrone size={12} />
                                ) : undefined
                              }
                              style={{
                                cursor: 'pointer',
                                paddingTop: '12px',
                                paddingBottom: '12px',
                                marginTop: '5px',
                                backgroundColor:
                                  selectedInspection?.inspection_uuid ===
                                  inspection.inspection_uuid
                                    ? 'var(--mantine-primary-color-light)'
                                    : undefined,
                                transition: 'background-color 0.4s ease',
                              }}
                              onClick={() => setSelectedInspection(inspection)}
                            >
                              <Text
                                size="xs"
                                mt={4}
                                fw={
                                  selectedInspection?.inspection_uuid ===
                                  inspection.inspection_uuid
                                    ? 500
                                    : 400
                                }
                              >
                                {inspection.total_power_loss_kw?.toFixed(2)} kW
                                (
                                {inspection.total_power_loss_percent?.toFixed(
                                  2,
                                )}
                                %) DC Power Loss
                              </Text>
                              <Text
                                size="xs"
                                mt={4}
                                fw={
                                  selectedInspection?.inspection_uuid ===
                                  inspection.inspection_uuid
                                    ? 500
                                    : 400
                                }
                              >
                                {inspection.total_affected_modules} modules
                                affected
                              </Text>
                            </Timeline.Item>
                          ))}
                        </Timeline>
                      </div>
                    </ScrollArea>
                  </Stack>
                </Card>
              </Stack>
            </Grid.Col>
          </Grid>

          {/* Anomaly Table - Full Width Card */}
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between" mb="lg">
              <Title order={4}>Anomalies</Title>
              <Tooltip label="Sync Anomalies with Zeitview">
                <ActionIcon
                  size="sm"
                  onClick={() => syncAnomalies()}
                  loading={isSyncingAnomalies}
                >
                  <IconRefresh />
                </ActionIcon>
              </Tooltip>
            </Group>
            {anomaliesLoading ? (
              <PageLoader />
            ) : anomalies && anomalies.length > 0 ? (
              <DroneAnomaliesTable
                anomalies={anomalies}
                inspectionId={selectedInspection?.inspection_uuid}
              />
            ) : (
              <Text size="sm" c="dimmed">
                No anomalies found for this inspection.
              </Text>
            )}
          </Card>
        </Stack>
      ) : (
        <Text>No inspections found.</Text>
      )}

      {/* Order New Inspection Modal */}
      {projectId && (
        <OrderDroneInspectionModal
          opened={orderModalOpened}
          onClose={closeOrderModal}
          projectId={projectId}
          currentProvider={currentProvider}
        />
      )}
    </Stack>
  )
}

export default DroneInspections
