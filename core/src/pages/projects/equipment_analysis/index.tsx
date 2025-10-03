import { useGetProject } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import { Box, Stack, Tabs, Title } from '@mantine/core'
import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

// Import all equipment analysis components
import EquipmentAnalysisBESS from './bess/page'
import EquipmentAnalysisBESSPCS from './bess_pcs/page'
import EquipmentAnalysisCircuit from './circuit/page'
import EquipmentAnalysisMetStation from './met_station/page'
import EquipmentAnalysisPVDCCombiner from './pv_dc_combiner/page'
import EquipmentAnalysisPVPCS from './pv_pcs/page'
import EquipmentAnalysisSingleLineDiagram from './single_line_diagram/SnapshotSLD'
import EquipmentAnalysisSystem from './system/page'
import EquipmentAnalysisTracker from './tracker/page'

interface TabConfig {
  value: string
  label: string
  component: React.ComponentType
  requiresPV?: boolean
  requiresBESS?: boolean
  requiresMetStations?: boolean
  requiresPVDCCombiners?: boolean
  requiresTrackers?: boolean
  requiresBESSBlocks?: boolean
  requiresBESSEnclosures?: boolean
  requiresBESSPCSs?: boolean
}

const tabConfigs: TabConfig[] = [
  {
    value: 'system',
    label: 'System',
    component: EquipmentAnalysisSystem,
  },
  {
    value: 'single-line-diagram',
    label: 'Single Line Diagram',
    component: EquipmentAnalysisSingleLineDiagram,
    requiresBESS: true,
  },
  {
    value: 'circuit',
    label: 'Circuit',
    component: EquipmentAnalysisCircuit,
  },
  {
    value: 'pv-pcs',
    label: 'PV PCS',
    component: EquipmentAnalysisPVPCS,
    requiresPV: true,
  },
  {
    value: 'pv-dc-combiner',
    label: 'PV DC Combiner',
    component: EquipmentAnalysisPVDCCombiner,
    requiresPVDCCombiners: true,
    requiresPV: true,
  },
  {
    value: 'tracker',
    label: 'Tracker',
    component: EquipmentAnalysisTracker,
    requiresPV: true,
    requiresTrackers: true,
  },
  {
    value: 'bess',
    label: 'BESS DC',
    component: EquipmentAnalysisBESS,
    requiresBESS: true,
  },
  {
    value: 'bess-pcs',
    label: 'BESS PCS',
    component: EquipmentAnalysisBESSPCS,
    requiresBESS: true,
    requiresBESSPCSs: true,
  },
  {
    value: 'met-station',
    label: 'Met Station',
    component: EquipmentAnalysisMetStation,
    requiresMetStations: true,
  },
]

export default function EquipmentAnalysis() {
  const { projectId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<string | null>(null)

  const project = useGetProject({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { deep: true },
    queryOptions: { enabled: !!projectId },
  })

  // Filter tabs based on project capabilities
  const availableTabs = tabConfigs.filter((tab) => {
    if (!project.data) return true

    // Remove PV tabs if project doesn't have PV
    if (tab.requiresPV && project.data.project_type_id === 2) return false

    // Remove BESS tabs if project doesn't have BESS components
    if (
      tab.requiresBESS &&
      !project.data.has_bess_blocks &&
      !project.data.has_bess_enclosures &&
      !project.data.has_bess_pcss
    )
      return false

    // Remove specific component tabs if project doesn't have them
    if (tab.requiresMetStations && !project.data.has_met_stations) return false
    if (tab.requiresPVDCCombiners && !project.data.has_pv_dc_combiners)
      return false
    if (tab.requiresTrackers && !project.data.has_trackers) return false
    if (tab.requiresBESSBlocks && !project.data.has_bess_blocks) return false
    if (tab.requiresBESSEnclosures && !project.data.has_bess_enclosures)
      return false
    if (tab.requiresBESSPCSs && !project.data.has_bess_pcss) return false

    return true
  })

  // Set initial active tab from URL params or default to first available
  useEffect(() => {
    const tabFromUrl = searchParams.get('tab')
    if (tabFromUrl && availableTabs.some((tab) => tab.value === tabFromUrl)) {
      setActiveTab(tabFromUrl)
    } else if (availableTabs.length > 0 && !activeTab) {
      setActiveTab(availableTabs[0].value)
    }
  }, [searchParams, availableTabs, activeTab])

  // Handle tab changes
  const handleTabChange = (value: string | null) => {
    if (value) {
      setActiveTab(value)
      // Clear date parameters when switching tabs and only keep the tab parameter
      setSearchParams({ tab: value })
    }
  }

  // Handle legacy routes - redirect to tab format
  useEffect(() => {
    const currentPath = window.location.pathname
    const equipmentAnalysisPath = `/projects/${projectId}/equipment-analysis`

    if (currentPath !== equipmentAnalysisPath) {
      // Extract the tab from the current path
      const pathSegments = currentPath.split('/')
      const equipmentIndex = pathSegments.indexOf('equipment-analysis')
      if (equipmentIndex !== -1 && equipmentIndex < pathSegments.length - 1) {
        const potentialTab = pathSegments[equipmentIndex + 1]
        const matchingTab = availableTabs.find(
          (tab) => tab.value === potentialTab,
        )
        if (matchingTab) {
          navigate(`${equipmentAnalysisPath}?tab=${potentialTab}`, {
            replace: true,
          })
          return
        }
      }
    }
  }, [projectId, navigate, availableTabs])

  if (project.isLoading) {
    return <PageLoader />
  }

  if (!project.data || availableTabs.length === 0) {
    return (
      <Box p="md">
        <Title order={1}>Current Day</Title>
        <p>No equipment analysis options available for this project.</p>
      </Box>
    )
  }

  return (
    <Stack h="100%">
      <Box px="md" pt="md">
        <Title order={1}>Current Day</Title>
      </Box>

      <Tabs
        value={activeTab}
        onChange={handleTabChange}
        h="100%"
        style={{ display: 'flex', flexDirection: 'column' }}
      >
        <Tabs.List px="md">
          {availableTabs.map((tab) => (
            <Tabs.Tab key={tab.value} value={tab.value}>
              {tab.label}
            </Tabs.Tab>
          ))}
        </Tabs.List>

        {availableTabs.map((tab) => (
          <Tabs.Panel
            key={tab.value}
            value={tab.value}
            style={{
              flex: 1,
              overflow: 'hidden',
              display: activeTab === tab.value ? 'flex' : 'none',
              flexDirection: 'column',
            }}
          >
            <Box style={{ flex: 1, overflow: 'auto' }}>
              <tab.component />
            </Box>
          </Tabs.Panel>
        ))}
      </Tabs>
    </Stack>
  )
}
