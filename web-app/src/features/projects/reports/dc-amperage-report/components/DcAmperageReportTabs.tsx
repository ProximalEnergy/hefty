import { HoverCard, Tabs as MantineTabs, Text } from '@mantine/core'
import type { ReactNode } from 'react'
import type { DcAmperageReportTab } from '@/features/projects/reports/dc-amperage-report/types/dc-amperage-report-types'

const ANALYSIS_DISABLED_MESSAGE =
  'Complete an analysis from the Clearsky tab to view results.'

type DcAmperageReportTabsProps = {
  value: DcAmperageReportTab
  onChange: (value: string | null) => void
  hasPopulatedAnalysis: boolean
  clearskyView: ReactNode
  analysisView: ReactNode
}

export function DcAmperageReportTabs({
  value,
  onChange,
  hasPopulatedAnalysis,
  clearskyView,
  analysisView,
}: DcAmperageReportTabsProps) {
  return (
    <MantineTabs
      value={value}
      onChange={onChange}
      keepMounted={false}
      h="100%"
      style={{
        display: 'flex',
        flex: 1,
        flexDirection: 'column',
        minHeight: 0,
      }}
    >
      <MantineTabs.List>
        <MantineTabs.Tab value="clearsky">Clearsky</MantineTabs.Tab>
        <AnalysisTab hasPopulatedAnalysis={hasPopulatedAnalysis} />
      </MantineTabs.List>
      <MantineTabs.Panel
        value="clearsky"
        pt="md"
        style={{ flex: 1, minHeight: 0 }}
      >
        {clearskyView}
      </MantineTabs.Panel>
      <MantineTabs.Panel
        value="analysis"
        pt="md"
        style={{ flex: 1, minHeight: 0 }}
      >
        {analysisView}
      </MantineTabs.Panel>
    </MantineTabs>
  )
}

type AnalysisTabProps = {
  hasPopulatedAnalysis: boolean
}

function AnalysisTab({ hasPopulatedAnalysis }: AnalysisTabProps) {
  if (hasPopulatedAnalysis) {
    return <MantineTabs.Tab value="analysis">Analysis</MantineTabs.Tab>
  }

  return (
    <HoverCard withArrow shadow="md" position="bottom">
      <HoverCard.Target>
        <span>
          <MantineTabs.Tab value="analysis" disabled>
            Analysis
          </MantineTabs.Tab>
        </span>
      </HoverCard.Target>
      <HoverCard.Dropdown>
        <Text size="sm">{ANALYSIS_DISABLED_MESSAGE}</Text>
      </HoverCard.Dropdown>
    </HoverCard>
  )
}
