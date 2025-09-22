import { useCustomQuery, useCustomQueryArrow } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export interface RealTimeData {
  device_ids: number[]
  device_names: string[]
  device_names_x: string[]
  device_names_y: string[]
  traces: {
    name: string
    values: (number | null)[]
  }[]
}

export interface DataTimeSeriesLast {
  tag_id: number
  time: string
  value_integer: number | null
  value_bigint: number | null
  value_real: number | null
  value_double: number | null
  value_boolean: boolean | null
  value_text: string | null
}

export interface DataAvailability {
  tag_id: number
  time: string
  age: number
  sensor_type_id?: number
  device_id: number
  device_type_id: number
  device_name: string
  max_age: number
  stale: boolean
  age_pct: number
}

export const useGetRealTimeByDeviceTypeID = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: {
    projectId: string
    deviceTypeId: number
  }
  queryParams: {
    sensor_type_ids: number[]
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/real-time/${pathParams.deviceTypeId}`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<RealTimeData>({
    axiosConfig,
    queryName: 'getRealTimeByDeviceTypeID',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

export const useGetDataAvailabilityV2 = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: {
    projectId: string
  }
  queryParams: {
    device_type_ids?: number[]
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/device-details/data-availability-v2`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQueryArrow({
    axiosConfig,
    queryName: 'getDataAvailabilityV2',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

export const useGetDataTimeseriesLast = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: {
    projectId: string
  }
  queryParams: {
    device_type_ids?: number[]
    sensor_type_ids?: number[]
    device_ids?: number[]
    tag_ids?: number[]
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/data-last-updated/data-timeseries-last/`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<DataTimeSeriesLast[]>({
    axiosConfig,
    queryName: 'getDataTimeseriesLast',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

export const useGetDataAvailability = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: {
    projectId: string
  }
  queryParams: {
    device_type_ids?: number[]
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/device-details/data-availability`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<DataAvailability[]>({
    axiosConfig,
    queryName: 'getDataAvailability',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}
