import { ProjectTypeEnum } from '@/api/enumerations'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { useProjectFilter } from '@/hooks/custom'
import { Stack } from '@mantine/core'
import { useParams } from 'react-router'

import { useEquipmentAnalysisTab } from '../../../../pages/projects/equipment_analysis/useEquipmentAnalysisTab'
import { PvInverterHeader } from '../components/PvInverterHeader'
import { PvInverterTabs } from '../components/PvInverterTabs'
import { usePvInverterContext } from '../hooks/use-pv-inverter-context'
import { PvInverterDayView } from '../views/PvInverterDayView'
import { PvInverterLongTermView } from '../views/PvInverterLongTermView'
import { PvInverterRealTimeView } from '../views/PvInverterRealTimeView'

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
