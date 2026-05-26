import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { Stack } from '@mantine/core'
import { useEffect } from 'react'
import { useParams } from 'react-router'
import { DcAmperageReportTabs } from '@/features/projects/reports/dc-amperage-report/components/DcAmperageReportTabs'
import { useDcAmperageReportContext } from '@/features/projects/reports/dc-amperage-report/hooks/use-dc-amperage-report-context'
import { useDcAmperageReportState } from '@/features/projects/reports/dc-amperage-report/hooks/use-dc-amperage-report-state'
import { useDcAmperageReportTab } from '@/features/projects/reports/dc-amperage-report/hooks/use-dc-amperage-report-tab'
import { DcAmperageReportAnalysisView } from '@/features/projects/reports/dc-amperage-report/views/DcAmperageReportAnalysisView'
import { DcAmperageReportClearskyView } from '@/features/projects/reports/dc-amperage-report/views/DcAmperageReportClearskyView'
import type {
  DcAmperageReportContext,
  DcAmperageReportTab,
} from '@/features/projects/reports/dc-amperage-report/types/dc-amperage-report-types'

export function DcAmperageReportRoute() {
  const { projectId } = useParams()
  const context = useDcAmperageReportContext({ projectId: projectId ?? '' })
  const { activeTab, setActiveTab } = useDcAmperageReportTab()

  if (context.isLoading) {
    return <PageLoader />
  }

  if (context.error !== null) {
    return <PageError text="Error loading DC amperage report" />
  }

  if (context.project === undefined || context.project === null) {
    return <PageError text="Project not found" />
  }

  return (
    <DcAmperageReportLoadedRoute
      context={{ ...context, project: context.project }}
      activeTab={activeTab}
      setActiveTab={setActiveTab}
    />
  )
}

type DcAmperageReportLoadedRouteProps = {
  context: DcAmperageReportContext
  activeTab: DcAmperageReportTab
  setActiveTab: (value: string | null) => void
}

function DcAmperageReportLoadedRoute({
  context,
  activeTab,
  setActiveTab,
}: DcAmperageReportLoadedRouteProps) {
  const reportState = useDcAmperageReportState({ context })

  useEffect(() => {
    if (!reportState.hasPopulatedAnalysis && activeTab === 'analysis') {
      setActiveTab('clearsky')
    }
  }, [activeTab, reportState.hasPopulatedAnalysis, setActiveTab])

  const handleGenerateDcAmperageReport = () => {
    if (reportState.poaProcessingResult.validPoints === 0) {
      return
    }

    void reportState.generateReport().then((result) => {
      if (result.data) {
        setActiveTab('analysis')
      }
    })
  }

  return (
    <Stack p="md" h="100%">
      <PageTitle>DC Amperage Report</PageTitle>
      <DcAmperageReportTabs
        value={activeTab}
        onChange={setActiveTab}
        hasPopulatedAnalysis={reportState.hasPopulatedAnalysis}
        clearskyView={
          <DcAmperageReportClearskyView
            reportState={reportState}
            onGenerateReport={handleGenerateDcAmperageReport}
          />
        }
        analysisView={
          <DcAmperageReportAnalysisView reportState={reportState} />
        }
      />
    </Stack>
  )
}
