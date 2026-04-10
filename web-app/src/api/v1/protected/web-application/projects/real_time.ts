import { useCustomQuery, useCustomQueryArrow } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

interface RealTimeData {
  device_ids: number[]
  device_names: string[]
  device_names_x: string[]
  device_names_y: string[]
  traces: {
    name: string
    name_short: string
    sensor_type_id: number
    values: (number | null)[]
    times: string[]
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
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.ONE_MINUTE,
  }

  return useCustomQuery<RealTimeData>({
    axiosConfig,
    queryName: 'getRealTimeByDeviceTypeID',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
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

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.ONE_MINUTE,
  }

  return useCustomQueryArrow({
    axiosConfig,
    queryName: 'getDataAvailabilityV2',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
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
    url: `/v1/operational/projects/${pathParams.projectId}/data-timeseries-last`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.ONE_MINUTE,
  }

  return useCustomQuery<DataTimeSeriesLast[]>({
    axiosConfig,
    queryName: 'getDataTimeseriesLast',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

interface ExpectedPowerByDeviceType {
  device_ids: number[]
  expected_power: Record<number, number | null>
}

export const useGetExpectedPowerByDeviceTypeID = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: {
    projectId: string
    deviceTypeId: number
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/real-time/${pathParams.deviceTypeId}/expected-power`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.THIRTY_SECONDS, // 25 seconds
  }

  return useCustomQuery<ExpectedPowerByDeviceType>({
    axiosConfig,
    queryName: 'getExpectedPowerByDeviceTypeID',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
