import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

const _COMPONENT_NAME = 'app__interfaces__SensorType'
const URL = '/v1/operational/sensor-types'

export type SensorType = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']

export const useGetSensorTypes = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
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
        url: `${baseURL}/v1/operational/sensor-types`,
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
