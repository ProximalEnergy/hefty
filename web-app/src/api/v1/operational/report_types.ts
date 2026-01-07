import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'ReportType'
const URL_REPORT_TYPE = '/v1/operational/report-types/{report_type_id}'
const URL_REPORT_TYPES = '/v1/operational/report-types'

type ReportType = types.components['schemas'][typeof _COMPONENT_NAME]
type getReportType = types.paths[typeof URL_REPORT_TYPE]['get']
type getReportTypePathParams = getReportType['parameters']['path']
type getReportTypes = types.paths[typeof URL_REPORT_TYPES]['get']
type getReportTypesQueryParams = getReportTypes['parameters']['query']

export const useGetReportType = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: getReportTypePathParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL_REPORT_TYPE,
  }

  return useCustomQuery<ReportType>({
    axiosConfig,
    queryName: 'getReportType',
    pathParams,
    queryOptions,
  })
}

export const useGetReportTypes = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams?: getReportTypesQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL_REPORT_TYPES,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<ReportType[]>({
    axiosConfig,
    queryName: 'getReportTypes',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
