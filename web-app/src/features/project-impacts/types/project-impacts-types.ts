import type { Project } from '@/api/v1/operational/projects'

export type ProjectImpactsTab = 'events' | 'issues'

export type ProjectImpactsContext = {
  projectId: string
  project: Project | undefined
  isLoading: boolean
  error: unknown | null
}

export type RootCause = {
  root_cause_id: number
  device_type_id: number
  name_long: string
  name_full?: string
}

export type StatusTimeSeriesTrace = {
  alert?: (boolean | null)[]
  name?: string | null
  x: string[]
  y: (string | null)[]
}
