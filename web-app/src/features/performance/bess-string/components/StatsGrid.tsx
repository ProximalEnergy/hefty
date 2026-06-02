import { SimpleGrid } from '@mantine/core'

import { CMMSTicketsCard } from '@/features/performance/bess-string/components/CMMSTicketsCard'
import { DataStatusCard } from '@/features/performance/bess-string/components/DataStatusCard'
import { EventsOpenCard } from '@/features/performance/bess-string/components/EventsOpenCard'
import { MaintenanceCard } from '@/features/performance/bess-string/components/MaintenanceCard'
import { RealtimeBalanceScoreCard } from '@/features/performance/bess-string/components/RealtimeBalanceScoreCard'
import { StringPowerCard } from '@/features/performance/bess-string/components/StringPowerCard'
import type {
  ActiveEventsHoverSection,
  NextMaintenanceData,
  StatsData,
} from '@/features/performance/bess-string/types/bess-string-realtime'

type StatsGridProps = {
  realtimeLoading: boolean
  eventsLoading: boolean
  cmmsLoading: boolean
  hasCMMSIntegration: boolean
  maintenanceLoading: boolean
  stats: StatsData
  powerSubtitle: string
  activeEventsHoverSections: ActiveEventsHoverSection[]
  nextPreventativeMaintenance: NextMaintenanceData | null
  onNavigateDataAvailability: () => void
  onNavigateEvents: () => void
  onNavigateEvent: (eventId: number) => void
  onNavigateCMMS: () => void
  onNavigateCalendar: () => void
  onDataStatusHoverChange: (isHovered: boolean) => void
}

export const StatsGrid = ({
  realtimeLoading,
  eventsLoading,
  cmmsLoading,
  hasCMMSIntegration,
  maintenanceLoading,
  stats,
  powerSubtitle,
  activeEventsHoverSections,
  nextPreventativeMaintenance,
  onNavigateDataAvailability,
  onNavigateEvents,
  onNavigateEvent,
  onNavigateCMMS,
  onNavigateCalendar,
  onDataStatusHoverChange,
}: StatsGridProps) => (
  <SimpleGrid cols={{ base: 1, xs: 2, sm: 3, md: 6 }}>
    <StringPowerCard
      isLoading={realtimeLoading}
      stats={stats}
      subtitle={powerSubtitle}
    />
    <RealtimeBalanceScoreCard isLoading={realtimeLoading} stats={stats} />
    <DataStatusCard
      isLoading={realtimeLoading}
      stats={stats}
      onClick={onNavigateDataAvailability}
      onHoverChange={onDataStatusHoverChange}
    />
    <EventsOpenCard
      isLoading={eventsLoading}
      stats={stats}
      sections={activeEventsHoverSections}
      onClick={onNavigateEvents}
      onNavigateEvent={onNavigateEvent}
    />
    <CMMSTicketsCard
      isLoading={cmmsLoading}
      hasIntegration={hasCMMSIntegration}
      stats={stats}
      onClick={onNavigateCMMS}
    />
    <MaintenanceCard
      isLoading={maintenanceLoading}
      nextPreventativeMaintenance={nextPreventativeMaintenance}
      onClick={onNavigateCalendar}
    />
  </SimpleGrid>
)
