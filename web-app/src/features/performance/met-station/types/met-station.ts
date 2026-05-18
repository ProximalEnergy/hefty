import type { Project } from '@/api/v1/operational/projects'
import type { Device } from '@/hooks/types'

export type MetStationTab = 'realtime' | 'current-day' | 'long-term'

export type MetStationContext = {
  projectId: string
  project: Project | undefined
  devices: Device[] | undefined
  isSuperadmin: boolean
  isLoading: boolean
  error: unknown | null
}
