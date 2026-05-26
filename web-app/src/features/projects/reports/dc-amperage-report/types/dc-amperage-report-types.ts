import type { DCAmperageDataV2 } from '@/api/v1/analytics/dc_amperage_report'
import type { Project } from '@/api/v1/operational/projects'
import type { DataTimeSeries } from '@/hooks/types'
import type { QueryObserverResult, UseQueryResult } from '@tanstack/react-query'
import type { Shape } from 'plotly.js'

export type DcAmperageReportTab = 'clearsky' | 'analysis'
export type DcAmperageReportNormalization = 'inv' | 'proj'

export type DcAmperageReportContext = {
  projectId: string
  project: Project
  isLoading: boolean
  error: Error | null
}

export type DcAmperageReportPoaTraceOption = {
  key: string
  label: string
  tagId: number | undefined
}

export type DcAmperageReportPoaProcessingResult = {
  plotData: DataTimeSeries[]
  validPoints: number
  shapes: Partial<Shape>[]
  selectedPoaTagIds: number[]
}

export type DcAmperageReportState = {
  start: string | undefined
  end: string | undefined
  resampleRate: string
  setResampleRate: (resampleRate: string) => void
  minPoa: number
  setMinPoa: (minPoa: number) => void
  maxPoaDerivative: number
  setMaxPoaDerivative: (maxPoaDerivative: number) => void
  maxPoaDerivativeStdDev: number
  setMaxPoaDerivativeStdDev: (maxPoaDerivativeStdDev: number) => void
  usePoaDerivative: boolean
  setUsePoaDerivative: (usePoaDerivative: boolean) => void
  usePoaDerivativeStdDev: boolean
  setUsePoaDerivativeStdDev: (usePoaDerivativeStdDev: boolean) => void
  poaTraceOptions: DcAmperageReportPoaTraceOption[]
  selectedPoaTraceKeys: string[]
  setSelectedPoaTraceKeys: (selectedPoaTraceKeys: string[]) => void
  poaProcessingResult: DcAmperageReportPoaProcessingResult
  poaDataQuery: UseQueryResult<DataTimeSeries[], Error>
  reportQuery: UseQueryResult<DCAmperageDataV2, Error>
  hasPopulatedAnalysis: boolean
  generateReport: () => Promise<QueryObserverResult<DCAmperageDataV2, Error>>
  normalization: DcAmperageReportNormalization
  setNormalization: (normalization: DcAmperageReportNormalization) => void
  deviationThreshold: number
  setDeviationThreshold: (deviationThreshold: number) => void
}
