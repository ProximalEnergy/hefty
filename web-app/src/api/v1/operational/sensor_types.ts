import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

export interface SensorType {
  sensor_type_id: number
  device_type_id: number
  name_short: string
  name_long: string
  name_metric: string
  unit: string | null
  description: string | null
}

export const useGetSensorTypes = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/sensor-types/`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<SensorType[]>({
    axiosConfig,
    queryName: 'getSensorTypes',
    pathParams: {},
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useCreateSensorTypeMutation = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (sensorType: SensorType) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/operational/sensor-types/`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: sensorType,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getSensorTypes'] })
    },
  })
}

export const useUpdateSensorTypeMutation = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      sensorTypeId,
      sensorType,
    }: {
      sensorTypeId: number
      sensorType: SensorType
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'put',
        url: `${baseURL}/v1/operational/sensor-types/${sensorTypeId}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: sensorType,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getSensorTypes'] })
    },
  })
}
