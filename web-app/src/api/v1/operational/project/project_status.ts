import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'StatusTimeSeries'
const URL = '/v1/operational/projects/{project_id}/status/time-series'

type StatusTimeSeries = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']
type getPathParams = get['parameters']['path']

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

// Leaving this here for the interfaces - we'll need this soon enough but it's out of scope for now.
// interface DeviceStatusEntry {
//   time: string
//   status: string
//   status_type: string
// }

// interface DeviceStatuses {
//   device_id?: number
//   statuses: DeviceStatusEntry[]
// }

// export const useGetLastKnownStatuses = ({
//   pathParams,
//   queryParams,
//   queryOptions = {},
// }: {
//   pathParams: getPathParams
//   queryParams?: getQueryParams
//   queryOptions?: Partial<UseQueryOptions>
// }) => {
//   const axiosConfig = {
//     url: `/v1/operational/projects/${pathParams.project_id}/status/last-known-statuses`,
//   }

//   const defaultQueryOptions: Partial<UseQueryOptions> = {
//     refetchOnWindowFocus: false,
//     staleTime: 30000, // 30 seconds
//   }

//   return useCustomQuery<DeviceStatuses[]>({
//     axiosConfig,
//     queryName: 'getLastKnownStatuses',
//     pathParams,
//     queryParams,
//     queryOptions: { ...defaultQueryOptions, ...queryOptions },
//   })
// }
