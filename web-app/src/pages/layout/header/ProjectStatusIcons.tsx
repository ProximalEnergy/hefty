import { ProjectTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { DataStatusContainer } from '@/pages/layout/header/DataStatus'
import { StatusIconWrapper } from '@/pages/layout/header/StatusIconWrapper'
import { RealtimeEnergyAvailabilityGauge } from '@/pages/projects/components/RealtimeEnergyAvailabilityGauge'
import { RealtimePIGauge } from '@/pages/projects/components/RealtimePIGauge'
import { RealtimePowerAvailabilityGauge } from '@/pages/projects/components/RealtimePowerAvailabilityGauge'
import { useCurtailmentStatus } from '@/pages/projects/hooks/useCurtailmentStatus'
import { useRealtimeEnergyAvailability } from '@/pages/projects/hooks/useRealtimeEnergyAvailability'
import { useRealtimePerformanceIndex } from '@/pages/projects/hooks/useRealtimePerformanceIndex'
import { useRealtimePowerAvailability } from '@/pages/projects/hooks/useRealtimePowerAvailability'
import { useTrackerStowStatus } from '@/pages/projects/hooks/useTrackerStowStatus'
import { ActionIcon, Group, Tooltip } from '@mantine/core'
import { IconAlertTriangle, IconWind } from '@tabler/icons-react'
import { useNavigate, useParams } from 'react-router'

export const ProjectStatusIcons = () => {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const project = useSelectProject(projectId)

  const isPV =
    project.data?.project_type_id === ProjectTypeEnum.PV ||
    project.data?.project_type_id === ProjectTypeEnum.PVS

  const hasStorage =
    project.data?.project_type_id === ProjectTypeEnum.BESS ||
    project.data?.project_type_id === ProjectTypeEnum.PVS

  const { isCurtailed, isLoading: curtailLoading } = useCurtailmentStatus(
    projectId,
    project.data?.poi,
    isPV,
  )

  const { isHighStow, isLoading: stowLoading } = useTrackerStowStatus(
    projectId,
    project.data?.has_trackers,
  )

  const {
    performanceIndexPct,
    isLoading: piLoading,
    isNighttime,
  } = useRealtimePerformanceIndex(
    projectId,
    project.data?.project_type_id,
    project.data?.has_expected_energy_integration,
    project.data?.name_short,
  )

  const {
    powerAvailabilityPct,
    availablePowerMw,
    ratedCapacityMw,
    numPcsUnits,
    maxPcsCapacityMw,
    isLoading: paLoading,
  } = useRealtimePowerAvailability(
    projectId,
    project.data?.project_type_id,
    project.data?.poi,
  )

  const {
    energyAvailabilityPct,
    availableStrings,
    totalStrings,
    isLoading: eaLoading,
  } = useRealtimeEnergyAvailability(projectId, project.data?.project_type_id)

  if (!projectId || project.isLoading) return null

  return (
    <Group gap={16}>
      <DataStatusContainer />
      {!curtailLoading && isCurtailed === true && (
        <StatusIconWrapper label="CURTAIL" color="red">
          <Tooltip label="Project power is being curtailed">
            <ActionIcon
              variant="subtle"
              color="red"
              size="sm"
              onClick={() =>
                navigate(
                  `/projects/${projectId}/equipment-analysis/system?tab=realtime`,
                )
              }
            >
              <IconAlertTriangle size={16} />
            </ActionIcon>
          </Tooltip>
        </StatusIconWrapper>
      )}
      {!stowLoading && isHighStow === true && (
        <StatusIconWrapper label="STOW" color="red">
          <Tooltip label=">20% of tracker zones in stow mode">
            <ActionIcon
              variant="subtle"
              color="orange"
              size="sm"
              onClick={() =>
                navigate(
                  `/projects/${projectId}/equipment-analysis/tracker?tab=realtime`,
                )
              }
            >
              <IconWind size={16} />
            </ActionIcon>
          </Tooltip>
        </StatusIconWrapper>
      )}
      {isPV && project.data?.has_expected_energy_integration && (
        <StatusIconWrapper
          label="PV-PI"
          color={
            (performanceIndexPct ?? 0) >= 90
              ? 'green'
              : (performanceIndexPct ?? 0) >= 70
                ? 'yellow'
                : 'red'
          }
        >
          <RealtimePIGauge
            value={performanceIndexPct}
            isLoading={piLoading}
            isNighttime={isNighttime}
            onClick={() =>
              navigate(
                `/projects/${projectId}/equipment-analysis/system?tab=realtime`,
              )
            }
          />
        </StatusIconWrapper>
      )}
      {hasStorage && project.data?.poi != null && (
        <StatusIconWrapper
          label="POWER"
          color={
            (powerAvailabilityPct ?? 0) >= 90
              ? 'green'
              : (powerAvailabilityPct ?? 0) >= 70
                ? 'yellow'
                : 'red'
          }
        >
          <RealtimePowerAvailabilityGauge
            value={powerAvailabilityPct}
            availablePowerMw={availablePowerMw}
            ratedCapacityMw={ratedCapacityMw}
            numPcsUnits={numPcsUnits}
            maxPcsCapacityMw={maxPcsCapacityMw}
            isLoading={paLoading}
            onClick={() =>
              navigate(
                `/projects/${projectId}/equipment-analysis/system?tab=realtime`,
              )
            }
          />
        </StatusIconWrapper>
      )}
      {hasStorage && (
        <StatusIconWrapper
          label="ENERGY"
          color={
            (energyAvailabilityPct ?? 0) >= 90
              ? 'green'
              : (energyAvailabilityPct ?? 0) >= 70
                ? 'yellow'
                : 'red'
          }
        >
          <RealtimeEnergyAvailabilityGauge
            value={energyAvailabilityPct}
            availableStrings={availableStrings}
            totalStrings={totalStrings}
            isLoading={eaLoading}
            onClick={() =>
              navigate(
                `/projects/${projectId}/equipment-analysis/system?tab=realtime`,
              )
            }
          />
        </StatusIconWrapper>
      )}
    </Group>
  )
}
