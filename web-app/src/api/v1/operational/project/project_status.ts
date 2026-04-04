import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'StatusTimeSeries'
const URL = '/v1/operational/projects/{project_id}/status/time-series-js'
const LAST_KNOWN_STATUSES_URL =
  '/v1/operational/projects/{project_id}/status/last-known-statuses'

type StatusTimeSeries = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']
type getPathParams = get['parameters']['path']
type DeviceStatus = types.components['schemas']['DeviceStatus']
type getLastKnownStatuses = types.paths[typeof LAST_KNOWN_STATUSES_URL]['get']
type getLastKnownStatusesQueryParams =
  getLastKnownStatuses['parameters']['query']

export const useGetStatusTimeSeries = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: getPathParams
  queryParams: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<StatusTimeSeries[]>({
    axiosConfig,
    queryName: 'getStatusTimeSeries',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetLastKnownStatuses = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: getPathParams
  queryParams?: getLastKnownStatusesQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: LAST_KNOWN_STATUSES_URL,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 30000,
  }

  return useCustomQuery<DeviceStatus[]>({
    axiosConfig,
    queryName: 'getLastKnownStatuses',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
