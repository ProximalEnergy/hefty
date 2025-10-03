import { useCustomQuery } from '@/hooks/api'
import * as types from '@/hooks/types'
import { UseQueryOptions } from '@tanstack/react-query'

export const useGetEventsSummary = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    device_ids?: number[]
    device_type_ids?: number[]
    start?: string
    end?: string
    open?: boolean
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/get-events-summary`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<types.EventSummary[]>({
    axiosConfig,
    queryName: 'getEventsTwo',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

export const useGetEventDevices = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/event-devices`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<types.EventDeviceInfo>({
    axiosConfig,
    queryName: 'getEventDevices',
    pathParams,
    queryParams: {},
    queryOptions: queryOptions,
  })
}

export const useGetEventTraceTags = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    device_id: number
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/event-trace-tags`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<types.Tag[]>({
    axiosConfig,
    queryName: 'getEventTraceTags',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

export const useGetCountOpenEvents = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/count-open`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<number>({
    axiosConfig,
    queryName: 'getCountOpenEvents',
    pathParams,
    queryParams: {},
    queryOptions: queryOptions,
  })
}
