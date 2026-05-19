import { ProjectTypeEnum } from '@/api/enumerations'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { PvInverterHeader } from '@/features/performance/pv-inverter/components/PvInverterHeader'
import { PvInverterTabs } from '@/features/performance/pv-inverter/components/PvInverterTabs'
import { usePvInverterContext } from '@/features/performance/pv-inverter/hooks/use-pv-inverter-context'
import { PvInverterDayView } from '@/features/performance/pv-inverter/views/PvInverterDayView'
import { PvInverterLongTermView } from '@/features/performance/pv-inverter/views/PvInverterLongTermView'
import { PvInverterRealTimeView } from '@/features/performance/pv-inverter/views/PvInverterRealTimeView'
import { useProjectFilter } from '@/hooks/custom'
import { useEquipmentAnalysisTab } from '@/pages/projects/equipment_analysis/useEquipmentAnalysisTab'
import { Stack } from '@mantine/core'
import { useParams } from 'react-router'

export function PvInverterRoute() {
  useProjectFilter({
    projectTypes: [ProjectTypeEnum.PV, ProjectTypeEnum.PVS],
  })

  const { projectId } = useParams()
  const context = usePvInverterContext({ projectId })
  const { activeTab, setTab } = useEquipmentAnalysisTab({
    isSuperadmin: context.isSuperadmin,
  })

  if (context.isLoading) {
    return <PageLoader />
  }

  if (context.error !== null) {
    return <PageError text="Error loading PV inverter data" />
  }

  if (context.project === undefined || context.project === null) {
    return <PageError text="Project not found" />
  }

  return (
    <Stack p="md" h="100%">
      <PageTitle>PV Inverter Performance</PageTitle>
      <PvInverterHeader context={context} />
      <PvInverterTabs
        value={activeTab}
        onChange={setTab}
        isSuperadmin={context.isSuperadmin}
      >
        {activeTab === 'realtime' && <PvInverterRealTimeView />}
        {activeTab === 'current-day' && <PvInverterDayView context={context} />}
        {activeTab === 'long-term' && context.isSuperadmin && (
          <PvInverterLongTermView />
        )}
      </PvInverterTabs>
    </Stack>
  )
}
