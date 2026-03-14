import { components } from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/react'
import { UseQueryOptions, useMutation } from '@tanstack/react-query'
import axios from 'axios'

export type KPITypeInstance = components['schemas']['KPITypeInstance']
export type KPIInstanceColumn = components['schemas']['KPIInstanceColumn']
type KPIInstanceData = {
  rows: KPITypeInstance[]
  columns: Record<string, KPIInstanceColumn>
  data: Record<string, boolean>
}

const URL = '/v1/protected/kpi-instances/'
const UPSERT_URL = '/v1/protected/kpi-instances/upsert'
const DELETE_URL = '/v1/protected/kpi-instances/delete'

export const useGetKPIInstances = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
} = {}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 60, // 1 hour
  }

  return useCustomQuery<KPIInstanceData>({
    axiosConfig,
    queryName: 'getKPIInstances',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useUpsertKPIInstances = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async (data: Record<string, boolean>) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}${UPSERT_URL}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data,
      })
    },
  })
}

export const useDeleteKPIInstances = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async (keys: string[]) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}${DELETE_URL}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: keys,
      })
    },
  })
}
