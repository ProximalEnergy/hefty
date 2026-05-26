import { ReportTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetDCAmperageReportV2 } from '@/api/v1/analytics/dc_amperage_report'
import { useGetDataTimeSeriesV3 } from '@/api/v1/operational/project/project_data'
import { useValidateDateRange } from '@/components/datepicker/utils'
import { useProjectFilter } from '@/hooks/custom'
import { useEffect, useMemo, useState } from 'react'
import type {
  DcAmperageReportContext,
  DcAmperageReportNormalization,
  DcAmperageReportState,
} from '@/features/projects/reports/dc-amperage-report/types/dc-amperage-report-types'
import {
  buildPoaTraceOptions,
  hasPopulatedAnalysisData,
  processPoaData,
  parseResampleRateMinutes,
} from '@/features/projects/reports/dc-amperage-report/utils/dc-amperage-report-utils'

type UseDcAmperageReportStateProps = {
  context: DcAmperageReportContext
}

export function useDcAmperageReportState({
  context,
}: UseDcAmperageReportStateProps): DcAmperageReportState {
  useProjectFilter({
    reportTypeId: ReportTypeEnum.DC_AMPERAGE,
  })

  const [resampleRate, setResampleRate] = useState('5min')
  const [minPoa, setMinPoa] = useState(600)
  const [maxPoaDerivative, setMaxPoaDerivative] = useState(1)
  const [maxPoaDerivativeStdDev, setMaxPoaDerivativeStdDev] = useState(1)
  const [usePoaDerivative, setUsePoaDerivative] = useState(true)
  const [usePoaDerivativeStdDev, setUsePoaDerivativeStdDev] = useState(true)
  const [selectedPoaTraceKeys, setSelectedPoaTraceKeys] = useState<string[]>([])
  const [normalization, setNormalization] =
    useState<DcAmperageReportNormalization>('inv')
  const [deviationThreshold, setDeviationThreshold] = useState(5)

  const { start, end } = useValidateDateRange({
    maxDays: 1,
    timeZone: context.project.time_zone,
  })

  const startQuery = useMemo(() => {
    return start?.tz(context.project.time_zone, true).toISOString()
  }, [context.project.time_zone, start])

  const endQuery = useMemo(() => {
    return end?.tz(context.project.time_zone, true).toISOString()
  }, [context.project.time_zone, end])

  const poaDataQuery = useGetDataTimeSeriesV3({
    pathParams: { projectId: context.projectId },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.MET_STATION_POA],
      start: startQuery,
      end: endQuery,
      interval: resampleRate,
    },
    queryOptions: {
      enabled:
        context.projectId.length > 0 &&
        startQuery !== undefined &&
        endQuery !== undefined,
    },
  })

  const poaTraceOptions = useMemo(() => {
    return buildPoaTraceOptions(poaDataQuery.data ?? [])
  }, [poaDataQuery.data])

  useEffect(() => {
    setSelectedPoaTraceKeys((currentTraceKeys) => {
      const availableTraceKeys = new Set(
        poaTraceOptions.map((traceOption) => traceOption.key),
      )
      const selectedAvailableTraceKeys = currentTraceKeys.filter((traceKey) =>
        availableTraceKeys.has(traceKey),
      )

      if (selectedAvailableTraceKeys.length > 0) {
        return selectedAvailableTraceKeys
      }

      return poaTraceOptions.map((traceOption) => traceOption.key)
    })
  }, [poaTraceOptions])

  const poaProcessingResult = useMemo(() => {
    return processPoaData({
      poaData: poaDataQuery.data ?? [],
      selectedPoaTraceKeys,
      minPoa,
      maxPoaDerivative,
      maxPoaDerivativeStdDev,
      usePoaDerivative,
      usePoaDerivativeStdDev,
      resampleRate,
      timezone: context.project.time_zone,
    })
  }, [
    poaDataQuery.data,
    selectedPoaTraceKeys,
    minPoa,
    maxPoaDerivative,
    maxPoaDerivativeStdDev,
    usePoaDerivative,
    usePoaDerivativeStdDev,
    resampleRate,
    context.project.time_zone,
  ])

  const reportQuery = useGetDCAmperageReportV2({
    pathParams: { projectId: context.projectId },
    queryParams: {
      start: startQuery ?? '',
      min_poa: minPoa,
      max_poa_1d: maxPoaDerivative,
      max_poa_std: maxPoaDerivativeStdDev,
      rolling_window: Math.max(
        1,
        Math.round(60 / parseResampleRateMinutes(resampleRate)),
      ),
      use_poa_1d: usePoaDerivative,
      use_poa_std: usePoaDerivativeStdDev,
      resample_rate: resampleRate,
      poa_tag_ids: poaProcessingResult.selectedPoaTagIds,
    },
    queryOptions: {
      enabled: false,
    },
  })
  const hasPopulatedAnalysis = hasPopulatedAnalysisData(reportQuery.data)

  return {
    start: startQuery,
    end: endQuery,
    resampleRate,
    setResampleRate,
    minPoa,
    setMinPoa,
    maxPoaDerivative,
    setMaxPoaDerivative,
    maxPoaDerivativeStdDev,
    setMaxPoaDerivativeStdDev,
    usePoaDerivative,
    setUsePoaDerivative,
    usePoaDerivativeStdDev,
    setUsePoaDerivativeStdDev,
    poaTraceOptions,
    selectedPoaTraceKeys,
    setSelectedPoaTraceKeys,
    poaProcessingResult,
    poaDataQuery,
    reportQuery,
    hasPopulatedAnalysis,
    generateReport: reportQuery.refetch,
    normalization,
    setNormalization,
    deviationThreshold,
    setDeviationThreshold,
  }
}
