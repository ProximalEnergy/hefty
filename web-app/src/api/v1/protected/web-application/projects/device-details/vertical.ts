import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface QueryParams {
  device_ids: number[]
  start: string
  end: string
}

interface DeviceDetailsVertical {
  times: string[]
  data: {
    name: string
    values: number[]
    device_id: number
  }[]
  layout: {
    y_axis_label: string
  }
}

export const useGetDeviceDetailsVertical = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: QueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/device-details/vertical`,
  }

  const defaultQueryOptions = {
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  }

  return useCustomQuery<DeviceDetailsVertical>({
    axiosConfig,
    queryName: 'getDeviceDetailsVertical',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

interface DeviceTree {
  id: number
  label: string
  device_ids: number[]
  initially_requested: boolean
}

interface ControllerResponse {
  device_technology: string
  device_tree: DeviceTree[]
}

export const useGetDeviceDetailsVerticalController = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string; device_id: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/device-details/vertical/controller/${pathParams.device_id}`,
  }

  const defaultQueryOptions = {
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  }

  return useCustomQuery<ControllerResponse>({
    axiosConfig,
    queryName: 'getDeviceDetailsVerticalController',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
